"""Serve the exported logistic regression with numpy and pandas only (no sklearn, no pickle).

Input: rows with the 18:00 features of night D (names in lr_export["feature_names"]), computed with
the same code as training. Output per row: probability of frost (t2m <= 0 C from 18:00 of D to 09:00
of D+1 local), level, top drivers (coefficient times standardized value) and the validation
reliability bin.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def load_export(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def log_odds(export: dict, X: pd.DataFrame) -> np.ndarray:
    names = export["feature_names"]
    z = (X[names].to_numpy(dtype=float) - np.asarray(export["means"])) / np.asarray(export["stds"])
    return z @ np.asarray(export["coefficients"]) + export["intercept"]


def probability(export: dict, X: pd.DataFrame) -> np.ndarray:
    lo = log_odds(export, X)
    cal = export.get("calibration")
    if cal:
        return _sigmoid(cal["a"] * lo + cal["b"])
    return _sigmoid(lo)


def level_of(p: float, cuts: list[float], levels: list[str]) -> str:
    return levels[int(np.searchsorted(np.asarray(cuts), p, side="right"))]


def predict(export: dict, X: pd.DataFrame, top_k: int = 3) -> pd.DataFrame:
    """probability, level, alert (p >= validation threshold), top_drivers and reliability bin per row."""
    names = export["feature_names"]
    p = probability(export, X)
    z = (X[names].to_numpy(dtype=float) - np.asarray(export["means"])) / np.asarray(export["stds"])
    contrib = z * np.asarray(export["coefficients"])
    bins = export["reliability_bins"]
    edges = [b["upper"] for b in bins[:-1]]
    rows = []
    for i in range(len(X)):
        order = np.argsort(-np.abs(contrib[i]))[:top_k]
        b = bins[int(np.searchsorted(edges, p[i], side="right"))]
        rows.append({
            "probability": float(p[i]),
            "level": level_of(float(p[i]), export["level_cuts"], export["levels"]),
            "alert": bool(p[i] >= export["threshold"]),
            "top_drivers": [{"feature": names[j], "contribution": float(contrib[i, j]),
                             "direction": "raises risk" if contrib[i, j] > 0 else "lowers risk"} for j in order],
            "reliability_bin": {"lower": b["lower"], "upper": b["upper"], "observed_rate_validation": b["observed_rate"],
                                "count_validation": b["count"]},
        })
    return pd.DataFrame(rows, index=X.index)
