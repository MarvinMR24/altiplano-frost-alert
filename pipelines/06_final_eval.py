"""FINAL test evaluation. Run once, by the builder, after every choice is frozen on validation.

It refuses to run without --i-confirm-final, refuses to run twice (reports/final_test_metrics.json is
written only once and never overwritten), and is the only code allowed to load the test split
(frostwatch_ml.leakage.load_test_split).

Scored on the same test rows, with thresholds and calibration fixed on validation:
- LR_best (production) and TREE_best (comparison only), loaded from their bundles;
- the reference baselines majority, climatology, persistence and dew point rule, fitted on training
  rows with their F2 threshold chosen on validation (reference only).

Muse experiment: if data/processed/muse/muse_candidates.json says B passed the pre-declared rule on
validation, B is scored in the same single run on its own feature table (same test rows, threshold
fixed on validation) and the rule is applied again on test. Otherwise only A is evaluated and B is
recorded as "not adopted on validation".

Writes reports/final_test_metrics.json (last, so a crash leaves no half result) and .md, and updates
the model cards in reports/<model_version>/model_card.json. Mirrors to MLflow when credentials exist.

Run (only once): .venv/bin/python pipelines/06_final_eval.py --i-confirm-final [--no-sync]
"""

import argparse
import sys

import joblib
import pandas as pd

from frostwatch_ml import cli, config, leakage, runner
from frostwatch_ml.dataio.tables import read_json, write_json
from frostwatch_ml.evaluation import final
from frostwatch_ml.evaluation.cells import macro, per_cell
from frostwatch_ml.evaluation.metrics import metrics_at
from frostwatch_ml.models.calibration import apply_platt
from frostwatch_ml.tracking import mlflow_logger

OUT = config.REPORTS / "final_test_metrics.json"
OUT_MD = config.REPORTS / "final_test_metrics.md"
MUSE = config.PROCESSED / "muse" / "muse_candidates.json"


def score(model, rows, calibration):
    return apply_platt(model.decision_score(rows), calibration) if calibration else model.predict_proba(rows)


def evaluate_muse_b(test_a: pd.DataFrame, a_pooled: dict) -> dict:
    """Condition B on test, only if it passed the rule on validation."""
    if not MUSE.exists():
        return {"status": "no Muse experiment found; A only"}
    m = read_json(MUSE)
    if not m["adopted_on_validation"]:
        return {"run_id": m["run_id"], "status": "not adopted on validation",
                "gain_validation_pooled": m["gain_validation_pooled"], "final_decision": "ship A"}
    b_df = pd.read_parquet(config.ROOT / m["B"]["features_table"])
    test_b = leakage.load_test_split(b_df, i_confirm_final=True)
    keys = ["point_id", "night_date"]
    if not test_b[keys].equals(test_a[keys]) or not (test_b["frost"].to_numpy() == test_a["frost"].to_numpy()).all():
        raise RuntimeError("B test rows or labels differ from A")
    model = joblib.load(config.ROOT / m["B"]["model_path"])
    y = test_b["frost"].to_numpy(int)
    prob = score(model, test_b, m["B"]["calibration"])
    thr = m["B"]["threshold"]  # fixed on validation, never re-tuned here
    pooled = metrics_at(y, prob, thr, True)
    cells = per_cell(test_b, y, prob, thr, True)
    gain = {k: pooled[k] - a_pooled[k] for k in ("pr_auc", "f2")}
    rule = m["rule"]
    adopt = gain["pr_auc"] >= rule["min_gain_pr_auc"] and gain["f2"] >= rule["min_gain_f2"]
    return {"run_id": m["run_id"], "status": "evaluated (passed on validation)", "pooled": pooled,
            "macro_over_cells": macro(cells), "per_cell": cells.reset_index().to_dict(orient="records"),
            "gain_test_pooled_vs_LR_best": gain, "rule": rule, "final_decision": "adopt B" if adopt else "ship A"}


def update_cards(results: dict, years: list[int]) -> None:
    """Model cards no longer say "test pending"; test metrics sit next to the validation metrics."""
    for name in ("LR_best", "TREE_best"):
        r = results[name]
        path = config.REPORTS / r["model_version"] / "model_card.json"
        card = read_json(path)
        card["status"] = "final test evaluation done (test evaluated once; thresholds fixed on validation)"
        card["data"]["test_status"] = "evaluated"
        card["metrics_test"] = {"years": years, "pooled": r["pooled"], "macro_over_cells": r["macro_over_cells"],
                                "source": "reports/final_test_metrics.json"}
        write_json(card, path)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--i-confirm-final", action="store_true")
    p.add_argument("--no-sync", action="store_true", help="skip dvc status / push / status -c at the end")
    p.add_argument("--seed", type=int, default=config.SEED)
    args = p.parse_args()
    args.dry_run = False
    if not args.i_confirm_final:
        print("refusing to run: pass --i-confirm-final (the test set is evaluated once)")
        return 2
    if OUT.exists():
        print(f"refusing to run: {OUT.relative_to(config.ROOT)} already exists (single use)")
        return 2

    # Everything is frozen on train and validation before the test split is loaded.
    data = runner.load_model_data()
    entries = final.frozen_models(data, args.seed)
    df = pd.read_parquet(config.PROCESSED / "features.parquet")
    test = leakage.load_test_split(df, i_confirm_final=True)
    years = config.frost_config()["split"]["test"]
    print(f"test rows: {len(test)} ({years[0]}-{years[1]}), base rate {test['frost'].astype(float).mean():.4f}")

    results = final.evaluate_frozen(entries, test)
    muse = evaluate_muse_b(test, results["LR_best"]["pooled"])
    base_rates = {"train": float(data.train["frost"].astype(float).mean()),
                  "validation": float(data.val["frost"].astype(float).mean()),
                  "held_out": float(test["frost"].astype(float).mean())}
    out = {"test_years": years, "n_rows": int(len(test)), "base_rates": base_rates, "data_hash": data.data_hash,
           "selection": "every threshold, calibration and fitted statistic frozen on train and validation",
           "finalists": {k: v for k, v in results.items() if k in ("LR_best", "TREE_best")},
           "baselines": {k: v for k, v in results.items() if k not in ("LR_best", "TREE_best")},
           "validation_reference": {e["name"]: {"pooled": e["validation_pooled"], "macro_over_cells": e["validation_macro"]}
                                    for e in entries},
           "muse_condition_b": muse}

    final.write_report(OUT_MD, results, entries, years, base_rates, muse)
    update_cards(results, years)
    write_json(out, OUT)
    print("wrote", OUT.relative_to(config.ROOT), "and", OUT_MD.relative_to(config.ROOT))
    for name in ("LR_best", "TREE_best", "climatology", "persistence"):
        r = results[name]["pooled"]
        print(f"{name:12s} PR-AUC {r['pr_auc']:.4f} F2 {r['f2']:.4f} Brier {r['brier']:.4f} "
              f"accuracy {r['accuracy']:.4f} (majority {r['majority_class_accuracy']:.4f})")

    lr = results["LR_best"]
    url = mlflow_logger.log_run(
        "final-test-LR_best", {"model_version": lr["model_version"], "threshold": lr["threshold"]},
        {f"test_{k}": v for k, v in lr["pooled"].items() if isinstance(v, float)}
        | {f"test_macro_{k}": v for k, v in lr["macro_over_cells"].items()},
        {"data_hash": data.data_hash, "test_set": "evaluated once", "git_head": mlflow_logger.git_head(),
         "muse_condition_b": muse.get("status")},
        [OUT, OUT_MD])
    status = mlflow_logger.status()
    print("mlflow:", url or f"disabled ({status['reason']})")
    cli.finish("06_final_eval", args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
