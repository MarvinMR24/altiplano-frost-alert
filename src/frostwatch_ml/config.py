"""Constants, paths and YAML loading.

Time convention: local time is UTC-4 with no daylight saving. Night D is the local date of
the 18:00 snapshot, which is 22:00 UTC of day D. The label window is 22:00 UTC of D to
13:00 UTC of D+1 (16 hourly values). All settings come from configs/*.yaml.
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


def _find_root() -> Path:
    env = os.environ.get("FROSTWATCH_ROOT")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for parent in [Path.cwd(), *Path.cwd().parents, *here.parents]:
        if (parent / "dvc.yaml").exists() and (parent / "configs").is_dir():
            return parent
    raise RuntimeError("project root not found (set FROSTWATCH_ROOT)")


ROOT: Path = _find_root()
CONFIGS = ROOT / "configs"
RAW_CDS = ROOT / "data" / "raw" / "cds"
RAW_MANIFEST = RAW_CDS / "manifest.json"
PROCESSED = ROOT / "data" / "processed"
SCRATCH = PROCESSED / "scratch" / "unzipped"
PREDICTIONS = PROCESSED / "predictions"
DOCS = ROOT / "docs"
FIGURES = DOCS / "figures"
REPORTS = ROOT / "reports"
MODELS = ROOT / "models"
EXPERIMENTS = ROOT / "experiments"
LOGS = ROOT / "logs" / "model"

SEED = 42
LOCAL_UTC_OFFSET_H = -4
SPLIT_NAMES = ("train", "validation", "test", "out_of_sample_check")


def load_yaml(relpath: str | Path) -> dict[str, Any]:
    """Load a YAML file relative to the project root."""
    return yaml.safe_load((ROOT / relpath).read_text())


@lru_cache(maxsize=1)
def frost_config() -> dict[str, Any]:
    """configs/frost.yaml: label window, feature hours, split years, EDA rules."""
    return load_yaml("configs/frost.yaml")


@lru_cache(maxsize=1)
def features_config() -> dict[str, Any]:
    """configs/features.yaml: the explicit feature allowlist and deny patterns."""
    return load_yaml("configs/features.yaml")


@lru_cache(maxsize=1)
def model_config() -> dict[str, Any]:
    """configs/model.yaml: model grids, version date, level cuts, sync settings."""
    return load_yaml("configs/model.yaml")


def point_ids() -> list[str]:
    """Point ids in the priority order of configs/points.yaml."""
    return [p["id"] for p in load_yaml("configs/points.yaml")["points"]]


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"ts": self.formatTime(record), "level": record.levelname, "logger": record.name,
                   "msg": record.getMessage()}
        payload.update(getattr(record, "fields", {}))
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    """Structured JSON logger writing to logs/model/pipeline.log and to stderr. Never log secrets."""
    logger = logging.getLogger(f"frostwatch.{name}")
    if not logger.handlers:
        LOGS.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(LOGS / "pipeline.log")
        fh.setFormatter(_JsonFormatter())
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
        logger.addHandler(fh)
        logger.addHandler(sh)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_event(logger: logging.Logger, msg: str, **fields: Any) -> None:
    """Log a message with structured fields."""
    logger.info(msg, extra={"fields": fields})
