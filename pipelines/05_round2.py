"""Round 2: tune the logistic regression (grid) and the best Round 1 tree model (random search),
optional sigmoid calibration fitted on training years with a year-grouped CV, and choose the
finalists LR_best (production candidate) and TREE_best (comparison only). Selection by
VALIDATION PR-AUC, then F2. The test set is locked.

Writes models/<version>/ (DVC), data/processed/model_candidates.json (DVC), reports/round2/ (git),
experiments/r2-*/ (git) and docs/model_round2.md.

Run: .venv/bin/python pipelines/05_round2.py [--dry-run] [--no-sync]
"""

import itertools

import numpy as np
import pandas as pd

from frostwatch_ml import cli, config, runner
from frostwatch_ml.artifacts.bundle import model_version, save_bundle
from frostwatch_ml.dataio.tables import write_csv, write_json, write_text
from frostwatch_ml.evaluation import reports
from frostwatch_ml.evaluation.cells import MAIN, skill
from frostwatch_ml.models.calibration import apply_platt, fit_platt_oof
from frostwatch_ml.models.registry import TREES, build

OUT = config.REPORTS / "round2"


def _row(res, **params):
    return {**params, "pr_auc": res.pooled["pr_auc"], "f2": res.pooled["f2"], "roc_auc": res.pooled["roc_auc"],
            "brier": res.pooled["brier"], "threshold": res.threshold,
            "macro_pr_auc": res.macro["pr_auc"], "macro_f2": res.macro["f2"]}


def _best(table: pd.DataFrame) -> pd.Series:
    return table.sort_values(["pr_auc", "f2"], ascending=False, kind="mergesort").iloc[0]


def _draws(space: dict, n: int, seed: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        out.append({k: (v[int(rng.integers(len(v)))]) for k, v in space.items()})
    return out


def main() -> None:
    args = cli.parser(__doc__, "configs/model.yaml").parse_args()
    mcfg = config.load_yaml(args.config)
    r2 = mcfg["round2"]
    data = runner.load_model_data()
    r1 = pd.read_csv(config.REPORTS / "round1" / "comparison_pooled.csv", index_col=0)
    tree_kind = r1.loc[[t for t in TREES if t in r1.index]].sort_values(["pr_auc", "f2"], ascending=False).index[0]
    grid = list(itertools.product(r2["lr_grid"]["C"], r2["lr_grid"]["class_weight"], r2["lr_grid"]["penalty"]))
    print(f"LR grid: {len(grid)} fits; best Round 1 tree: {tree_kind}; random search: {r2['tree_search']['n_draws']} draws")
    if args.dry_run:
        return

    # Logistic regression grid
    lr_rows, lr_res = [], {}
    for C, cw, pen in grid:
        res = runner.evaluate(build("lr", data.features, seed=args.seed, C=C, class_weight=cw, penalty=pen), data)
        key = (C, cw, pen)
        lr_res[key] = res
        lr_rows.append(_row(res, C=C, class_weight=cw or "none", penalty=pen))
    lr_table = pd.DataFrame(lr_rows)
    write_csv(lr_table, OUT / "lr_grid.csv", index=False)
    b = _best(lr_table)
    lr_key = (float(b["C"]), None if b["class_weight"] == "none" else str(b["class_weight"]), str(b["penalty"]))
    lr_best = lr_res[lr_key]
    print("LR_best", lr_key, f"PR-AUC {lr_best.pooled['pr_auc']:.4f} F2 {lr_best.pooled['f2']:.4f}")

    # Tree random search (draw 0 is the Round 1 default)
    space = r2["tree_search"][tree_kind]
    tree_rows, tree_res = [], {}
    for i, params in enumerate([{}] + _draws(space, r2["tree_search"]["n_draws"], args.seed)):
        res = runner.evaluate(build(tree_kind, data.features, seed=args.seed, **params), data)
        tree_res[i] = (params, res)
        tree_rows.append(_row(res, draw=i, **{k: params.get(k, "default") for k in space}))
    tree_table = pd.DataFrame(tree_rows)
    write_csv(tree_table, OUT / "tree_search.csv", index=False)
    tb = int(_best(tree_table)["draw"])
    tree_params, tree_best = tree_res[tb]
    print("TREE_best", tree_kind, "draw", tb, tree_params, f"PR-AUC {tree_best.pooled['pr_auc']:.4f}")

    # Calibration (sigmoid on out-of-fold log-odds, GroupKFold by year on training rows)
    finalists = {}
    cal_rows = []
    lr_params = {"C": lr_key[0], "class_weight": lr_key[1], "penalty": lr_key[2]}
    for role, kind, params, res in [("production_candidate", "lr", lr_params, lr_best),
                                    ("comparison_only", tree_kind, tree_params, tree_best)]:
        cal, chosen = None, res
        if r2["calibration"]["enabled"]:
            cal = fit_platt_oof(lambda k=kind, p=params: build(k, data.features, seed=args.seed, **p),
                                data.train, data.train["frost"].to_numpy(int), n_splits=r2["calibration"]["cv_splits"])
            p_cal = apply_platt(res.model.decision_score(data.val), cal)
            res_cal = runner.evaluate(res.model, data, score_val=p_cal, name=res.name + "_calibrated")
            cal_rows.append({"model": kind, "brier_raw": res.pooled["brier"], "brier_calibrated": res_cal.pooled["brier"],
                             "brier_change": res_cal.pooled["brier"] - res.pooled["brier"],
                             "f2_raw": res.pooled["f2"], "f2_calibrated": res_cal.pooled["f2"], "a": cal["a"], "b": cal["b"]})
            if res_cal.pooled["brier"] < res.pooled["brier"]:
                chosen = res_cal
            else:
                cal = None
        name = "lr" if kind == "lr" else kind
        version = model_version(name, data.data_hash)
        chosen.name = "LR_best" if kind == "lr" else "TREE_best"
        chosen.extra = {"model_version": version, "kind": kind, "params": params, "calibration": cal, "role": role}
        save_bundle(res.model, version=version, role=role, threshold=chosen.threshold, calibration=cal,
                    data_hash=data.data_hash)
        run = runner.record(chosen, data, "r2", kind, {**params, "calibrated": cal is not None}, args.seed, log_mlflow=False)
        finalists[chosen.name] = {"model_version": version, "kind": kind, "role": role, "params": params,
                                  "calibration": cal, "threshold": chosen.threshold, "run_id": run["run_id"],
                                  "validation_pooled": chosen.pooled, "validation_macro": chosen.macro}
    cal_table = pd.DataFrame(cal_rows).set_index("model") if cal_rows else pd.DataFrame()
    if len(cal_table):
        reports.save_table(cal_table, OUT / "calibration", title="Sigmoid calibration, validation Brier change")

    write_json({"data_hash": data.data_hash, "features": data.features, "features_manifest_sha256": data.features_manifest_sha256,
                "split_definition": data.split_cfg, "finalists": finalists}, config.PROCESSED / "model_candidates.json")

    # Comparison with the reference baselines (refit, cheap) on validation
    refs = [runner.evaluate(build(k, data.features, **({"doy_halfwidth": 7} if k == "climatology" else {})), data, name=k)
            for k in ("climatology", "persistence")]
    final_res = {n: f for n, f in finalists.items()}
    pooled = pd.DataFrame({**{r.name: r.pooled for r in refs}, **{n: f["validation_pooled"] for n, f in final_res.items()}}).T[MAIN + ["threshold"]]
    macro_t = pd.DataFrame({**{r.name: r.macro for r in refs}, **{n: f["validation_macro"] for n, f in final_res.items()}}).T[MAIN]
    pooled.index.name = macro_t.index.name = "model"
    reports.save_table(pooled, OUT / "comparison_pooled", title="Round 2 finalists vs baselines, validation, pooled")
    reports.save_table(macro_t, OUT / "comparison_macro", title="Round 2 finalists vs baselines, validation, macro over cells")
    reports.save_table(skill(pooled), OUT / "skill_vs_baselines", title="Round 2, skill vs best baseline (pooled)")
    reports.save_table(skill(macro_t), OUT / "skill_vs_baselines_macro", title="Round 2, skill vs best baseline (macro)")

    lr_model = lr_best.model.estimator
    coefs = pd.DataFrame({"feature": data.features, "std_coefficient": lr_model.named_steps["lr"].coef_.ravel()})
    coefs = coefs.reindex(coefs["std_coefficient"].abs().sort_values(ascending=False).index).reset_index(drop=True)
    write_csv(coefs, OUT / "lr_coefficients.csv", index=False)
    gap = {k: final_res["LR_best"]["validation_pooled"][k] - final_res["TREE_best"]["validation_pooled"][k] for k in ("pr_auc", "f2", "roc_auc", "brier")}
    gap_macro = {k: final_res["LR_best"]["validation_macro"][k] - final_res["TREE_best"]["validation_macro"][k] for k in ("pr_auc", "f2")}
    write_json({"lr_minus_tree_pooled": gap, "lr_minus_tree_macro": gap_macro}, OUT / "gap_lr_vs_tree.json")
    write_finalists_md(finalists, gap, gap_macro, lr_table, tree_table, tree_kind, cal_table, coefs)
    write_doc(finalists, pooled, macro_t, gap, gap_macro, lr_table, tree_table, tree_kind, cal_table, coefs)
    cli.finish("05_round2", args)


def write_finalists_md(finalists, gap, gap_macro, lr_table, tree_table, tree_kind, cal_table, coefs) -> None:
    rows = pd.DataFrame({n: {"model_version": f["model_version"], "role": f["role"], "params": str(f["params"]),
                             "calibrated": f["calibration"] is not None, "threshold": f["threshold"],
                             "pr_auc": f["validation_pooled"]["pr_auc"], "f2": f["validation_pooled"]["f2"],
                             "macro_pr_auc": f["validation_macro"]["pr_auc"], "macro_f2": f["validation_macro"]["f2"]}
                         for n, f in finalists.items()}).T
    rows.index.name = "finalist"
    text = ["# Round 2 finalists (validation only; test pending)", "", reports.md_table(rows, 4), "",
            f"Gap LR_best minus TREE_best, pooled: {', '.join(f'{k} {v:+.4f}' for k, v in gap.items())}; macro: {', '.join(f'{k} {v:+.4f}' for k, v in gap_macro.items())}.", ""]
    write_text("\n".join(text), OUT / "finalists.md")


def write_doc(finalists, pooled, macro_t, gap, gap_macro, lr_table, tree_table, tree_kind, cal_table, coefs) -> None:
    lr_top = lr_table.sort_values(["pr_auc", "f2"], ascending=False).head(8).set_index("C")
    tree_top = tree_table.sort_values(["pr_auc", "f2"], ascending=False).head(8).set_index("draw")
    lines = [
        "# Round 2: tuning and finalists (validation only)",
        "",
        "Generated by `pipelines/05_round2.py`. Fitted on 1985-2009, selected on validation 2010-2017 by PR-AUC then F2; the test set (2018-2025) is locked and was not used. "
        "Labels come from the same ERA5-Land reanalysis as the features. Frost nights trend down over time, so the test base rate is lower than in training; validation already reflects part of that shift.",
        "",
        "## Logistic regression grid (top 8 of " + str(len(lr_table)) + ")",
        reports.md_table(lr_top, 4),
        "",
        f"## {tree_kind} random search (draw 0 = Round 1 default; top 8 of {len(tree_table)})",
        reports.md_table(tree_top, 4),
        "",
        "## Calibration",
        "Sigmoid calibration fitted on out-of-fold log-odds of the training years (GroupKFold by year, 5 folds). It is kept only if it lowers the validation Brier score; it does not change PR-AUC or ROC-AUC (monotonic).",
        "",
        (reports.md_table(cal_table, 4) if len(cal_table) else "Calibration disabled."),
        "",
        "## Finalists vs baselines (validation)",
        "Pooled:",
        "",
        reports.md_table(pooled, 4),
        "",
        "Macro-average over the 8 cells:",
        "",
        reports.md_table(macro_t, 4),
        "",
        f"Gap LR_best minus TREE_best, pooled: {', '.join(f'{k} {v:+.4f}' for k, v in gap.items())}; macro: {', '.join(f'{k} {v:+.4f}' for k, v in gap_macro.items())}.",
        "",
        "## LR_best standardized coefficients (top drivers first)",
        "Coefficient per standard deviation of the feature (training statistics). Positive raises the frost probability. Correlated features share weight, so individual signs should be read with care.",
        "",
        reports.md_table(coefs.set_index("feature"), 4),
        "",
        "LR_best is the production candidate; TREE_best is for comparison only. No confidence intervals are computed; small differences may be noise.",
        "",
    ]
    write_text("\n".join(lines), config.DOCS / "model_round2.md")


if __name__ == "__main__":
    main()
