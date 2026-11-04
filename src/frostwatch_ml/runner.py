"""Fit on training rows, score validation rows, record the run.

Data access goes through leakage.model_rows (train and validation only). Thresholds are chosen on
validation scores. Each run writes experiments/<run_id>/ (config.yaml, metrics.json; git) and
data/processed/predictions/<round>/<run_id>.csv (DVC), and is mirrored to MLflow.
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import yaml

from . import config, leakage
from .artifacts.bundle import package_versions
from .dataio.tables import content_sha256, read_json, sha256_of, write_csv, write_json, write_text
from .evaluation.cells import macro, per_cell
from .evaluation.metrics import metrics_at
from .evaluation.thresholds import best_f2_threshold
from .tracking import mlflow_logger


def _plain(obj: Any) -> Any:
    """Convert numpy scalars and other JSON-able objects to plain Python types."""
    return json.loads(json.dumps(obj, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


@dataclass
class ModelData:
    train: pd.DataFrame
    val: pd.DataFrame
    features: list[str]
    data_hash: str
    features_manifest_sha256: str
    split_cfg: dict
    label_definition: str


@dataclass
class Result:
    name: str
    model: Any
    score_val: np.ndarray
    threshold: float
    pooled: dict
    cells: pd.DataFrame
    macro: dict
    extra: dict = field(default_factory=dict)


def load_model_data() -> ModelData:
    """Train and validation rows of the night table, the feature allowlist and the data hashes."""
    df = pd.read_parquet(config.PROCESSED / "features.parquet")
    leakage.assert_no_crosscheck_columns(df)
    manifest = read_json(config.PROCESSED / "features_manifest.json")
    feats = leakage.feature_list()
    if feats != manifest["feature_columns"]:
        raise leakage.FeatureLeakError("features.yaml allowlist differs from the night table manifest")
    return ModelData(
        train=leakage.model_rows(df, "train"),
        val=leakage.model_rows(df, "validation"),
        features=feats,
        data_hash=content_sha256(df),
        features_manifest_sha256=sha256_of(config.PROCESSED / "features_manifest.json"),
        split_cfg=manifest["split_definition"],
        label_definition=manifest["label_definition"],
    )


def evaluate(model, data: ModelData, score_val: np.ndarray | None = None, name: str | None = None) -> Result:
    """Fit on train (unless score_val is given), choose the F2 threshold on validation, compute metrics."""
    if score_val is None:
        model.fit(data.train, data.train["frost"].to_numpy(dtype=int))
        score_val = model.predict_proba(data.val)
    y_val = data.val["frost"].to_numpy(dtype=int)
    thr, _ = best_f2_threshold(y_val, score_val)
    pooled = metrics_at(y_val, score_val, thr, model.is_probability)
    cells = per_cell(data.val, y_val, score_val, thr, model.is_probability)
    return Result(name or model.name, model, np.asarray(score_val), thr, pooled, cells, macro(cells))


def record(result: Result, data: ModelData, round_name: str, kind: str, params: dict, seed: int,
           extra_artifacts: list | None = None, log_mlflow: bool = True) -> dict:
    """Write experiments/<run_id>/ and the validation predictions, then mirror to MLflow."""
    run_id = f"{round_name}-{result.name}-{data.data_hash[:8]}"
    exp_dir = config.EXPERIMENTS / run_id
    pred_path = config.PREDICTIONS / round_name / f"{run_id}.csv"
    preds = pd.DataFrame({"point_id": data.val["point_id"], "night_date": data.val["night_date"].dt.date,
                          "frost": data.val["frost"].astype(int), "score": result.score_val,
                          "predicted": (result.score_val >= result.threshold).astype(int)})
    write_csv(preds, pred_path, index=False)
    cfg = {"run_id": run_id, "round": round_name, "model": result.name, "kind": kind, "params": params,
           "seed": seed, "features": data.features, "split_definition": data.split_cfg,
           "selection": "fit on train, threshold and comparison on validation; test locked",
           "data_hash": data.data_hash, "features_manifest_sha256": data.features_manifest_sha256,
           "reproduce": f".venv/bin/python pipelines/{'04_round1' if round_name == 'r1' else '05_round2'}.py --no-sync"}
    write_text(yaml.safe_dump(_plain(cfg), sort_keys=False), exp_dir / "config.yaml")
    metrics = {"run_id": run_id, "validation_pooled": result.pooled, "validation_macro_over_cells": result.macro,
               "validation_per_cell": result.cells.reset_index().to_dict(orient="records"),
               "threshold": result.threshold, "is_probability": bool(result.model.is_probability),
               "predictions_val": str(pred_path.relative_to(config.ROOT)), "seed": seed,
               "data_hash": data.data_hash, "package_versions": {**package_versions(), "python": platform.python_version()},
               **result.extra}
    write_json(metrics, exp_dir / "metrics.json")
    url = None
    if log_mlflow:
        flat = {f"val_{k}": v for k, v in result.pooled.items() if isinstance(v, float)}
        flat.update({f"val_macro_{k}": v for k, v in result.macro.items()})
        tags = {"data_hash": data.data_hash, "features_manifest_sha256": data.features_manifest_sha256,
                "split_definition": str(data.split_cfg), "git_head": mlflow_logger.git_head(), "round": round_name,
                "test_set": "locked, not evaluated"}
        url = mlflow_logger.log_run(run_id, {"model": result.name, "kind": kind, "threshold": result.threshold,
                                             "seed": seed, **params}, flat, tags,
                                    [exp_dir / "config.yaml", exp_dir / "metrics.json", *(extra_artifacts or [])])
    return {"run_id": run_id, "mlflow_url": url, "experiment_dir": str(exp_dir.relative_to(config.ROOT))}
