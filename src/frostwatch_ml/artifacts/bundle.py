"""Model bundles: models/<model_version>/model.joblib and bundle_meta.json (DVC-tracked binaries)."""

from __future__ import annotations

import importlib.metadata as md
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib

from .. import config
from ..dataio.tables import sha256_of, write_json

REQUIRED_KEYS = ["model_version", "model_name", "role", "features", "threshold", "calibration", "data_hash",
                 "created_utc", "joblib_sha256", "package_versions"]
PACKAGES = ["numpy", "pandas", "scikit-learn", "xgboost", "lightgbm", "joblib", "pyarrow"]


def model_version(model: str, data_hash: str) -> str:
    """<model>-<YYYYMMDD>-<datahash8>; the date is fixed in configs/model.yaml so reruns are stable."""
    return f"{model}-{config.model_config()['version_date']}-{data_hash[:8]}"


def package_versions() -> dict[str, str]:
    out = {}
    for p in PACKAGES:
        try:
            out[p] = md.version(p)
        except md.PackageNotFoundError:
            out[p] = "not installed"
    return out


def save_bundle(model, *, version: str, role: str, threshold: float, calibration: dict | None, data_hash: str,
                extra: dict | None = None) -> Path:
    folder = config.MODELS / version
    folder.mkdir(parents=True, exist_ok=True)
    tmp = folder / ".model.joblib.tmp"
    joblib.dump(model, tmp)
    tmp.replace(folder / "model.joblib")
    meta: dict[str, Any] = {
        "model_version": version, "model_name": model.name, "role": role, "params": model.params,
        "features": list(getattr(model, "features", [])), "threshold": threshold, "calibration": calibration,
        "data_hash": data_hash, "created_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "joblib_sha256": sha256_of(folder / "model.joblib"), "package_versions": package_versions(),
        **(extra or {}),
    }
    write_json(meta, folder / "bundle_meta.json")
    return folder
