"""Shared fixtures: the saved night table and configs. Tests never evaluate a model on the test split."""

from pathlib import Path

import pandas as pd
import pytest

from frostwatch_ml import config

SRC = config.ROOT / "src" / "frostwatch_ml"
CODE_DIRS = [SRC, config.ROOT / "pipelines", config.ROOT / "tools"]


def code_files() -> list[Path]:
    return sorted(p for d in CODE_DIRS for p in d.rglob("*.py"))


@pytest.fixture(scope="session")
def features() -> pd.DataFrame:
    return pd.read_parquet(config.PROCESSED / "features.parquet")


@pytest.fixture(scope="session")
def crosschecks() -> pd.DataFrame:
    return pd.read_parquet(config.PROCESSED / "crosschecks.parquet")


@pytest.fixture(scope="session")
def frost_cfg() -> dict:
    return config.frost_config()
