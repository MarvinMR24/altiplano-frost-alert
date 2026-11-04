"""Model card (JSON). Says "validation metrics only; test pending" until the final evaluation exists."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

REQUIRED_KEYS = ["model_version", "model_name", "role", "status", "created_utc", "intended_use", "data", "features",
                 "label_definition", "time_convention", "threshold", "metrics_validation", "limitations", "attribution"]
ATTRIBUTION = "Generated using Copernicus Climate Change Service information [2026]."
LIMITATIONS = [
    "Labels come from the same ERA5-Land reanalysis as the features: the model predicts grid frost (0.1 degree cell), which is smoother than frost at a station or in a cold hollow.",
    "ERA5-Land cells are about 9 km; local terrain and cold air pooling are not resolved.",
    "Cloud information is a lagged proxy (AgERA5 24 h mean of the previous day); AgERA5 has its own 0.1 degree grid, which coincides with the ERA5-Land cells for these 8 points but can be offset by up to about 7 km in general.",
    "Frost nights trend down over 1985-2025, so the test years (2018-2025) have a lower base rate than training (1985-2009).",
    "Latitude and the elevation proxy are constants of the 8 training cells: the model is valid only for these 8 cells.",
    "Data is reanalysis (published a few days late), not a live forecast; the model has not been evaluated on forecast inputs.",
    "No confidence intervals are computed; small metric differences may be noise.",
]


def build_card(*, model_version: str, model_name: str, role: str, params: dict, features: list[str], threshold: float,
               metrics_pooled: dict, metrics_macro: dict, data_hash: str, features_manifest_sha256: str,
               split_cfg: dict, calibration: dict | None, label_definition: str, test_metrics: dict | None = None) -> dict[str, Any]:
    return {
        "model_version": model_version,
        "model_name": model_name,
        "role": role,
        "status": "validation metrics only; test pending" if test_metrics is None else "final test evaluation done",
        "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "intended_use": "Probability of radiation frost (2 m temperature <= 0 C) for the coming night at the 8 ERA5-Land cells of the La Paz to Oruro altiplano corridor, for crops, livestock, water pipes, vehicles, road ice and property. Not medical or health advice.",
        "params": params,
        "data": {"source": "ERA5-Land hourly and AgERA5 daily (Copernicus Climate Data Store), reanalysis, not raw satellite imagery",
                 "data_hash": data_hash, "features_manifest_sha256": features_manifest_sha256,
                 "training_years": split_cfg["train"], "validation_years": split_cfg["validation"],
                 "test_years": split_cfg["test"], "test_status": "locked" if test_metrics is None else "evaluated"},
        "features": features,
        "label_definition": label_definition,
        "time_convention": "Local time UTC-4. Night D: 18:00 snapshot at 22:00 UTC of D; label window 22:00 UTC of D to 13:00 UTC of D+1.",
        "threshold": {"value": threshold, "selected_on": "validation", "rule": "maximize F2"},
        "calibration": calibration,
        "metrics_validation": {"pooled": metrics_pooled, "macro_over_cells": metrics_macro},
        "metrics_test": test_metrics,
        "limitations": LIMITATIONS,
        "attribution": ATTRIBUTION,
    }
