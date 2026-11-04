"""FINAL test evaluation (guarded stub). Not to be run until the builder decides the final comparison.

It refuses to run without --i-confirm-final, refuses to run twice (reports/final_test_metrics.json is
written only once and never overwritten), and is the only code allowed to load the test split
(frostwatch_ml.leakage.load_test_split).

Muse experiment: if data/processed/muse/muse_candidates.json says B passed the pre-declared rule on
validation, B is scored in the same single run on its own feature table (same test rows, threshold
fixed on validation) and the rule is applied again on test. Otherwise only A is evaluated and B is
recorded as "not adopted on validation".

Run (only once, by the builder): .venv/bin/python pipelines/06_final_eval.py --i-confirm-final
"""

import argparse
import sys

import joblib
import pandas as pd

from frostwatch_ml import config, leakage
from frostwatch_ml.dataio.tables import read_json, write_json
from frostwatch_ml.evaluation.cells import macro, per_cell
from frostwatch_ml.evaluation.metrics import metrics_at
from frostwatch_ml.models.calibration import apply_platt

OUT = config.REPORTS / "final_test_metrics.json"
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


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--i-confirm-final", action="store_true")
    args = p.parse_args()
    if not args.i_confirm_final:
        print("refusing to run: pass --i-confirm-final (the test set is evaluated once)")
        return 2
    if OUT.exists():
        print(f"refusing to run: {OUT.relative_to(config.ROOT)} already exists (single use)")
        return 2
    df = pd.read_parquet(config.PROCESSED / "features.parquet")
    test = leakage.load_test_split(df, i_confirm_final=True)
    cand = read_json(config.PROCESSED / "model_candidates.json")
    y = test["frost"].to_numpy(int)
    out = {"test_years": config.frost_config()["split"]["test"], "finalists": {}}
    for name, f in cand["finalists"].items():
        model = joblib.load(config.MODELS / f["model_version"] / "model.joblib")
        prob = score(model, test, f["calibration"])
        thr = f["threshold"]  # fixed on validation, never re-tuned here
        cells = per_cell(test, y, prob, thr, True)
        out["finalists"][name] = {"model_version": f["model_version"], "pooled": metrics_at(y, prob, thr, True),
                                  "macro_over_cells": macro(cells), "per_cell": cells.reset_index().to_dict(orient="records")}
    out["muse_condition_b"] = evaluate_muse_b(test, out["finalists"]["LR_best"]["pooled"])
    write_json(out, OUT)
    print("wrote", OUT.relative_to(config.ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
