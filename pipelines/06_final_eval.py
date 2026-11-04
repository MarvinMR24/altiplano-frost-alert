"""FINAL test evaluation (guarded stub). Not to be run until the builder decides the final comparison.

It refuses to run without --i-confirm-final, refuses to run twice (reports/final_test_metrics.json is
written only once and never overwritten), and is the only code allowed to load the test split
(frostwatch_ml.leakage.load_test_split).

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
        prob = apply_platt(model.decision_score(test), f["calibration"]) if f["calibration"] else model.predict_proba(test)
        thr = f["threshold"]  # fixed on validation, never re-tuned here
        cells = per_cell(test, y, prob, thr, True)
        out["finalists"][name] = {"model_version": f["model_version"], "pooled": metrics_at(y, prob, thr, True),
                                  "macro_over_cells": macro(cells), "per_cell": cells.reset_index().to_dict(orient="records")}
    write_json(out, OUT)
    print("wrote", OUT.relative_to(config.ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
