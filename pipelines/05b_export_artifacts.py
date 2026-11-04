"""Export the Round 2 finalists to small, human-readable artifacts in reports/<model_version>/ (git):
model_card.json, metrics_validation.json and .csv, per_cell_metrics.csv, threshold.json, features.json,
reliability_bins.json and .csv, and for the logistic regression lr_export.json and coefficients.csv.
Binaries stay in models/<model_version>/ (DVC). Validation metrics only; test pending.
Mirrors the finalist runs to MLflow with their artifacts (non-fatal).

Run: .venv/bin/python pipelines/05b_export_artifacts.py [--dry-run] [--no-sync]
"""

import joblib
import pandas as pd

from frostwatch_ml import cli, config, runner
from frostwatch_ml.artifacts.export_lr import export_lr
from frostwatch_ml.artifacts.model_card import build_card
from frostwatch_ml.dataio.tables import read_json, write_csv, write_json, write_text
from frostwatch_ml.evaluation import plots
from frostwatch_ml.evaluation.thresholds import reliability_bins
from frostwatch_ml.inference import predict
from frostwatch_ml.models.calibration import apply_platt
from frostwatch_ml.tracking import mlflow_logger


def main() -> None:
    args = cli.parser(__doc__, "configs/model.yaml").parse_args()
    mcfg = config.load_yaml(args.config)
    cand = read_json(config.PROCESSED / "model_candidates.json")
    print("finalists:", {k: v["model_version"] for k, v in cand["finalists"].items()})
    if args.dry_run:
        return
    data = runner.load_model_data()
    if data.data_hash != cand["data_hash"]:
        raise SystemExit("data hash changed since Round 2; rerun Round 2")
    y_val = data.val["frost"].to_numpy(int)
    index_rows, links = [], {}
    for name, f in cand["finalists"].items():
        version = f["model_version"]
        model = joblib.load(config.MODELS / version / "model.joblib")
        cal = f["calibration"]
        prob = apply_platt(model.decision_score(data.val), cal) if cal else model.predict_proba(data.val)
        res = runner.evaluate(model, data, score_val=prob, name=name)
        if abs(res.threshold - f["threshold"]) > 1e-12:
            raise SystemExit(f"{name}: threshold differs from Round 2")
        bins = reliability_bins(y_val, prob, mcfg["reliability_bins"])
        out = config.REPORTS / version
        card = build_card(model_version=version, model_name=name, role=f["role"], params=f["params"], features=data.features,
                          threshold=res.threshold, metrics_pooled=res.pooled, metrics_macro=res.macro, data_hash=data.data_hash,
                          features_manifest_sha256=data.features_manifest_sha256, split_cfg=data.split_cfg,
                          calibration=cal, label_definition=data.label_definition)
        write_json(card, out / "model_card.json")
        write_json({"pooled": res.pooled, "macro_over_cells": res.macro}, out / "metrics_validation.json")
        write_csv(pd.DataFrame({"pooled": res.pooled, "macro_over_cells": res.macro}), out / "metrics_validation.csv")
        write_csv(res.cells, out / "per_cell_metrics.csv")
        write_json({"threshold": res.threshold, "selected_on": "validation", "rule": "maximize F2",
                    "level_cuts": mcfg["level_cuts"], "levels": mcfg["levels"]}, out / "threshold.json")
        write_json({"features": data.features, "source": "configs/features.yaml"}, out / "features.json")
        write_json(bins, out / "reliability_bins.json")
        write_csv(pd.DataFrame(bins), out / "reliability_bins.csv", index=False)
        plots.reliability(pd.DataFrame(bins).dropna(), f"{name} reliability (validation)", out / "figures" / "reliability.png")
        artifacts = [out / "model_card.json", out / "metrics_validation.json", out / "per_cell_metrics.csv",
                     config.MODELS / version / "model.joblib"]
        if f["kind"] == "lr":
            ex = export_lr(model, model_version=version, threshold=res.threshold, calibration=cal,
                           level_cuts=mcfg["level_cuts"], levels=mcfg["levels"], reliability_bins=bins,
                           data_hash=data.data_hash, split_cfg=data.split_cfg)
            write_json(ex, out / "lr_export.json")
            coef = pd.DataFrame({"feature": ex["feature_names"], "std_coefficient": ex["coefficients"],
                                 "train_mean": ex["means"], "train_std": ex["stds"]})
            coef = coef.reindex(coef["std_coefficient"].abs().sort_values(ascending=False).index)
            write_csv(coef, out / "coefficients.csv", index=False)
            served = predict.probability(ex, data.val)
            max_diff = float(abs(served - prob).max())
            if max_diff > 1e-9:
                raise SystemExit(f"serving parity failed: {max_diff}")
            card["serving_parity_max_abs_diff_validation"] = max_diff
            write_json(card, out / "model_card.json")
            artifacts.append(out / "lr_export.json")
        params = {"model": name, "kind": f["kind"], "threshold": res.threshold, "seed": args.seed,
                  "calibrated": cal is not None, **f["params"]}
        tags = {"data_hash": data.data_hash, "features_manifest_sha256": data.features_manifest_sha256,
                "split_definition": str(data.split_cfg), "git_head": mlflow_logger.git_head(), "round": "r2",
                "role": f["role"], "model_version": version, "test_set": "locked, not evaluated"}
        exp = config.EXPERIMENTS / f["run_id"]
        metrics = {f"val_{k}": v for k, v in res.pooled.items() if isinstance(v, float)}
        metrics.update({f"val_macro_{k}": v for k, v in res.macro.items()})
        links[name] = mlflow_logger.log_run(f["run_id"], params, metrics, tags,
                                            [exp / "config.yaml", exp / "metrics.json", *artifacts])
        index_rows.append({"model_version": version, "finalist": name, "role": f["role"], "pr_auc": res.pooled["pr_auc"],
                           "f2": res.pooled["f2"], "macro_pr_auc": res.macro["pr_auc"], "status": card["status"]})
    links_path = config.REPORTS / "mlflow_links.json"
    old = read_json(links_path) if links_path.exists() else {}
    write_json({k: links.get(k) or old.get(k) for k in links}, links_path)  # keep earlier links when MLflow is off
    write_index(index_rows)
    status = mlflow_logger.status()
    print("mlflow:", "ok" if status["enabled"] else f"disabled ({status['reason']})", links)
    cli.finish("05b_export_artifacts", args)


def write_index(rows) -> None:
    lines = ["# reports/", "",
             "Small, human-readable artifacts tracked in git. Binaries (model.joblib) live in models/ and data in data/processed/, both tracked by DVC and stored on DagsHub.",
             "All metrics are on VALIDATION (2010-2017). The test set (2018-2025) is locked: test pending.", "",
             "| folder | content |", "|---|---|",
             "| round1/ | baselines and default models: pooled, macro and per-cell tables, skill vs baselines, PR curves |",
             "| round2/ | LR grid, tree random search, calibration, finalists, LR coefficients, LR vs tree gap |"]
    for r in rows:
        lines.append(f"| {r['model_version']}/ | {r['finalist']} ({r['role']}): model_card.json, metrics_validation, per_cell_metrics, threshold, features, reliability_bins"
                     + (", lr_export.json, coefficients" if r["model_version"].startswith("lr-") else "") + f"; PR-AUC {r['pr_auc']:.4f}, F2 {r['f2']:.4f}, macro PR-AUC {r['macro_pr_auc']:.4f}; {r['status']} |")
    lines += ["| mlflow_links.json | MLflow run links on DagsHub (no credentials) |", ""]
    write_text("\n".join(lines), config.REPORTS / "README.md")


if __name__ == "__main__":
    main()
