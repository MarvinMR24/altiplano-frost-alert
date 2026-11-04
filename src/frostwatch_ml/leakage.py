"""Leakage guards.

- Features are an explicit allowlist (configs/features.yaml) checked against deny patterns.
- Model code gets rows only through `model_rows`, which refuses the test split.
- The test split loads only through `load_test_split`, which needs an explicit flag AND must be
  called from pipelines/06_final_eval.py; any other caller raises.
- Cross-check columns (AgERA5 night minimum, RH at 15:00) must never appear in the feature table.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pandas as pd

from . import config

FINAL_EVAL_SCRIPT = "pipelines/06_final_eval.py"
MODEL_SPLITS = ("train", "validation")


class TestSetLockedError(RuntimeError):
    """Raised when code other than the final evaluation tries to read the test split."""


class FeatureLeakError(ValueError):
    """Raised when the feature list contains a label, identifier, cross-check or denied column."""


def feature_list() -> list[str]:
    """The allowlist from configs/features.yaml, validated."""
    feats = list(config.features_config()["allowlist"])
    assert_feature_list(feats)
    return feats


def assert_feature_list(feats: list[str]) -> None:
    cfg = config.features_config()
    if len(set(feats)) != len(feats):
        raise FeatureLeakError("duplicate features")
    forbidden = set(cfg["identifier_columns"]) | set(cfg["label_columns"]) | set(cfg["crosscheck_only_columns"])
    bad = sorted(set(feats) & forbidden)
    if bad:
        raise FeatureLeakError(f"forbidden columns in features: {bad}")
    exceptions = set(cfg.get("deny_exceptions", []))
    for f in feats:
        if f in exceptions:
            continue
        for pat in cfg["deny_patterns"]:
            if re.search(pat, f):
                raise FeatureLeakError(f"feature {f!r} matches deny pattern {pat!r}")


def assert_no_crosscheck_columns(df: pd.DataFrame) -> None:
    bad = sorted(set(df.columns) & set(config.features_config()["crosscheck_only_columns"]))
    if bad:
        raise FeatureLeakError(f"cross-check columns found in the feature table: {bad}")


def model_rows(df: pd.DataFrame, split: str) -> pd.DataFrame:
    """Labeled rows of one modeling split. Only 'train' and 'validation' are allowed here."""
    if split == "test":
        raise TestSetLockedError("the test split is locked; it loads only through load_test_split in " + FINAL_EVAL_SCRIPT)
    if split not in MODEL_SPLITS:
        raise ValueError(f"split {split!r} is not a modeling split")
    rows = df[(df["split"] == split) & df["frost"].notna()]
    return rows.reset_index(drop=True)


def load_test_split(df: pd.DataFrame, *, i_confirm_final: bool = False) -> pd.DataFrame:
    """The labeled test rows. Requires i_confirm_final=True and a caller in pipelines/06_final_eval.py."""
    if not i_confirm_final:
        raise TestSetLockedError("load_test_split needs i_confirm_final=True")
    callers = [Path(f.filename).resolve() for f in inspect.stack()[1:]]
    allowed = (config.ROOT / FINAL_EVAL_SCRIPT).resolve()
    if allowed not in callers:
        raise TestSetLockedError(f"load_test_split may only be called from {FINAL_EVAL_SCRIPT}")
    return df[(df["split"] == "test") & df["frost"].notna()].reset_index(drop=True)
