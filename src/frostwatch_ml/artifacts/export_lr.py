"""Export a fitted logistic regression to plain JSON (no pickle, no sklearn needed to serve it)."""

from __future__ import annotations

from typing import Any

import numpy as np

REQUIRED_KEYS = ["model_version", "feature_names", "means", "stds", "coefficients", "intercept", "calibration",
                 "threshold", "level_cuts", "levels", "reliability_bins", "data_hash", "training_years",
                 "validation_years", "time_convention"]


def export_lr(model, *, model_version: str, threshold: float, calibration: dict | None, level_cuts: list[float],
              levels: list[str], reliability_bins: list[dict], data_hash: str, split_cfg: dict) -> dict[str, Any]:
    """`model` is a SklearnModel wrapping Pipeline(StandardScaler, LogisticRegression)."""
    scaler = model.estimator.named_steps["scaler"]
    lr = model.estimator.named_steps["lr"]
    return {
        "model_version": model_version,
        "feature_names": list(model.features),
        "means": [float(v) for v in scaler.mean_],
        "stds": [float(v) for v in scaler.scale_],
        "coefficients": [float(v) for v in np.ravel(lr.coef_)],
        "intercept": float(np.ravel(lr.intercept_)[0]),
        "calibration": calibration,
        "threshold": float(threshold),
        "level_cuts": list(level_cuts),
        "levels": list(levels),
        "reliability_bins": reliability_bins,
        "data_hash": data_hash,
        "training_years": split_cfg["train"],
        "validation_years": split_cfg["validation"],
        "time_convention": "Night D = local date (UTC-4) of the 18:00 snapshot (22:00 UTC). Features use data up to 22:00 UTC of D; the probability refers to t2m <= 0 C between 18:00 of D and 09:00 of D+1 local.",
        "params": dict(model.params),
    }
