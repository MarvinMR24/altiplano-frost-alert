"""Frozen evaluation used by the single final run (pipelines/06_final_eval.py).

Every model is fixed before any held-out row is seen: the finalists are loaded from their bundles
with the threshold and calibration chosen on validation, and the reference baselines are fitted
on training rows with their F2 threshold chosen on validation. `evaluate_frozen` then scores any
rows without changing a single choice. The functions take rows as an argument and never load a
split themselves, so they can be rehearsed on validation.
"""

from __future__ import annotations

from typing import Any

import joblib
import numpy as np
import pandas as pd

from .. import config, runner
from ..dataio.tables import read_json
from ..models.calibration import apply_platt
from ..models.registry import build
from .cells import MAIN, macro, per_cell, skill
from .metrics import metrics_at
from .reports import md_table

BASELINES = ("majority", "climatology", "persistence", "dewpoint_rule")


def frozen_models(data: runner.ModelData, seed: int) -> list[dict[str, Any]]:
    """Finalists from their bundles and baselines fitted on train; thresholds from validation."""
    cand = read_json(config.PROCESSED / "model_candidates.json")
    out = []
    for name, f in cand["finalists"].items():
        run = read_json(config.EXPERIMENTS / f["run_id"] / "metrics.json")
        out.append({"name": name, "role": f["role"], "model_version": f["model_version"],
                    "model": joblib.load(config.MODELS / f["model_version"] / "model.joblib"),
                    "calibration": f["calibration"], "threshold": f["threshold"], "is_probability": True,
                    "validation_pooled": f["validation_pooled"], "validation_macro": f["validation_macro"],
                    "validation_per_cell": run["validation_per_cell"]})
    for k in BASELINES:
        res = runner.evaluate(build(k, data.features, seed=seed, **({"doy_halfwidth": 7} if k == "climatology" else {})),
                              data, name=k)
        out.append({"name": k, "role": "baseline", "model_version": None, "model": res.model, "calibration": None,
                    "threshold": res.threshold, "is_probability": bool(res.model.is_probability),
                    "validation_pooled": res.pooled, "validation_macro": res.macro,
                    "validation_per_cell": res.cells.reset_index().to_dict(orient="records")})
    return out


def score(entry: dict, rows: pd.DataFrame) -> np.ndarray:
    m = entry["model"]
    if entry["calibration"]:
        return apply_platt(m.decision_score(rows), entry["calibration"])
    return m.predict_proba(rows)


def evaluate_frozen(entries: list[dict], rows: pd.DataFrame) -> dict[str, dict]:
    """Metrics of every frozen model on `rows` at its validation threshold (nothing is refitted)."""
    y = rows["frost"].to_numpy(int)
    out = {}
    for e in entries:
        s = score(e, rows)
        cells = per_cell(rows, y, s, e["threshold"], e["is_probability"])
        out[e["name"]] = {"role": e["role"], "model_version": e["model_version"], "threshold": e["threshold"],
                          "pooled": metrics_at(y, s, e["threshold"], e["is_probability"]),
                          "macro_over_cells": macro(cells), "per_cell": cells.reset_index().to_dict(orient="records")}
    return out


def tables(results: dict[str, dict]) -> dict[str, pd.DataFrame]:
    pooled = pd.DataFrame({k: v["pooled"] for k, v in results.items()}).T[MAIN + ["threshold", "base_rate"]]
    mac = pd.DataFrame({k: v["macro_over_cells"] for k, v in results.items()}).T[MAIN]
    pooled.index.name = mac.index.name = "model"
    return {"pooled": pooled, "macro": mac, "skill_pooled": skill(pooled), "skill_macro": skill(mac)}


def write_report(path, results: dict, entries: list[dict], years: list[int], base_rates: dict, muse: dict) -> None:
    from ..dataio.tables import write_text

    t = tables(results)
    val = {e["name"]: e for e in entries}
    keys = ["pr_auc", "f2", "precision", "recall", "f1", "roc_auc", "brier", "accuracy", "majority_class_accuracy", "base_rate"]
    side = pd.DataFrame({f"{n} ({k})": (val[n]["validation_pooled"] if k == "validation" else results[n]["pooled"])
                         for n in ("LR_best", "TREE_best") for k in ("validation", "held-out test")}).T[keys]
    side.index.name = "model and split"
    mside = pd.DataFrame({f"{n} ({k})": (val[n]["validation_macro"] if k == "validation" else results[n]["macro_over_cells"])
                          for n in ("LR_best", "TREE_best") for k in ("validation", "held-out test")}).T[keys[:-1]]
    mside.index.name = "model and split"
    vcell = pd.DataFrame(val["LR_best"]["validation_per_cell"]).set_index("point_id")
    tcell = pd.DataFrame(results["LR_best"]["per_cell"]).set_index("point_id")
    cells = pd.DataFrame({"base_rate_val": vcell["base_rate"], "base_rate_test": tcell["base_rate"],
                          "pr_auc_val": vcell["pr_auc"], "pr_auc_test": tcell["pr_auc"],
                          "f2_val": vcell["f2"], "f2_test": tcell["f2"], "precision_test": tcell["precision"],
                          "recall_test": tcell["recall"], "f1_test": tcell["f1"], "roc_auc_test": tcell["roc_auc"],
                          "brier_test": tcell["brier"], "accuracy_test": tcell["accuracy"],
                          "majority_acc_test": tcell["majority_class_accuracy"]})
    lr = results["LR_best"]["pooled"]
    lines = [
        "# Final test evaluation (run once)",
        "",
        f"Generated by `pipelines/06_final_eval.py --i-confirm-final`. Test years {years[0]}-{years[1]}, "
        f"{lr['n']} labeled nights over 8 cells. Every model, threshold and fitted statistic was frozen on validation "
        "(2010-2017) before this run; nothing was re-tuned on test. The 2026 out-of-sample nights are not part of any metric.",
        "",
        "Data: ERA5-Land and AgERA5 reanalysis (Copernicus CDS), not raw satellite imagery. Labels come from the same "
        "reanalysis, so the metrics measure agreement with reanalysis frost on a 0.1 degree grid, not station frost.",
        "",
        f"Base rate (share of frost nights): train {base_rates['train']:.3f}, validation {base_rates['validation']:.3f}, "
        f"test {base_rates['held_out']:.3f}. Frost nights trend down over time, so the test years have fewer frost nights "
        "than training. Accuracy is always shown next to the majority-class accuracy of the same rows.",
        "",
        "## Production model (LR_best) and comparison tree, validation vs test (pooled)",
        "",
        md_table(side, 4),
        "",
        "Macro-average over the 8 cells:",
        "",
        md_table(mside, 4),
        "",
        "## All models on test (pooled, thresholds fixed on validation)",
        "",
        md_table(t["pooled"], 4),
        "",
        "Macro-average over the 8 cells:",
        "",
        md_table(t["macro"], 4),
        "",
        "## Skill versus the best baseline on test (climatology or persistence)",
        "",
        "Pooled:",
        "",
        md_table(t["skill_pooled"], 4),
        "",
        "Macro:",
        "",
        md_table(t["skill_macro"], 4),
        "",
        "## LR_best per cell, validation vs test",
        "",
        md_table(cells, 4),
        "",
        "## Muse condition B",
        "",
        f"Status: {muse.get('status')}. Final decision: {muse.get('final_decision', 'ship A')}. "
        "B did not pass the pre-declared rule on validation (PR-AUC and F2 both +0.02), so it was not evaluated on test "
        "(see docs/MuseExperiment.md).",
        "",
        "## Notes",
        "",
        "- The dew point rule is a score, not a probability, so its Brier score is not defined. Persistence is a 0/1 forecast.",
        "- TREE_best is reported for comparison only; LR_best is the production model.",
        "- No confidence intervals are computed; small differences may be noise.",
        "",
    ]
    write_text("\n".join(lines), path)
