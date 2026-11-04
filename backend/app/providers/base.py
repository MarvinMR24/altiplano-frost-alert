"""DataProvider interface. Predictions are precomputed offline per cell and night; the backend
only reads them. Records follow docs/artifacts_contract.md."""

from __future__ import annotations

import datetime as dt
import json
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..schemas import Driver, Level, Observed, Reliability

CELLS_FILE = Path(__file__).resolve().parents[1] / "data" / "cells.json"
METRIC_KEYS = ("pr_auc", "f2", "precision", "recall", "f1", "roc_auc", "brier", "accuracy", "majority_accuracy")


class ProviderError(RuntimeError):
    """The provider cannot serve data (missing or invalid artifacts)."""


class NightNotFound(LookupError):
    pass


class CellInfo(BaseModel):
    point_id: str
    name: str
    lat: float
    lon: float


@lru_cache(maxsize=1)
def load_cells() -> tuple[CellInfo, ...]:
    data = json.loads(CELLS_FILE.read_text(encoding="utf-8"))
    return tuple(CellInfo(**c) for c in data["cells"])


def cells_by_id() -> dict[str, CellInfo]:
    return {c.point_id: c for c in load_cells()}


class CellRecord(BaseModel):
    """One cell for one night (artifacts contract, predictions/<YYYY-MM-DD>)."""

    model_config = ConfigDict(extra="forbid")
    point_id: str
    name: str
    lat: float
    lon: float
    elevation_m: float
    night_date: dt.date
    probability: float = Field(ge=0, le=1)
    level: Level
    top_drivers: list[Driver]
    conditions_1800: dict[str, float]
    historical_reliability: Reliability
    observed: Observed | None = None
    model_version: str = Field(min_length=1)
    data_source: str = Field(min_length=1)


class MetricsIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    pr_auc: float | None = None
    f2: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    roc_auc: float | None = None
    brier: float | None = None
    accuracy: float | None = None
    majority_accuracy: float | None = None


class ModelCardIn(BaseModel):
    """model_card.json (artifacts contract). Unknown keys are kept but not required."""

    model_config = ConfigDict(extra="allow")
    model_version: str = Field(min_length=1)
    model_type: str = "logistic_regression"
    condition: Literal["A", "B"] | None = None
    trained_years: tuple[int, int]
    validation_years: tuple[int, int] | None = None
    test_years: tuple[int, int] | None = None
    n_cells: int = Field(ge=1, le=8)
    decision_threshold: float | None = Field(default=None, ge=0, le=1)
    metrics: dict[Literal["validation", "test"], MetricsIn | None]
    label_definition: str | None = None
    data_source: str = Field(min_length=1)
    limitations: list[str]


class DataProvider(ABC):
    name: str

    @abstractmethod
    def list_nights(self) -> list[dt.date]:
        """Available nights, ascending."""

    @abstractmethod
    def get_cells(self, night: dt.date) -> list[CellRecord]:
        """One record per cell for that night; raises NightNotFound."""

    @abstractmethod
    def get_model_card(self) -> ModelCardIn:
        """The model card of the served predictions."""

    def latest_night(self) -> dt.date:
        nights = self.list_nights()
        if not nights:
            raise ProviderError("no nights available")
        return nights[-1]


def level_for(p: float) -> Level:
    """Contract levels: low < 0.3 <= moderate < 0.5 <= high < 0.7 <= very_high."""
    if p >= 0.7:
        return "very_high"
    if p >= 0.5:
        return "high"
    if p >= 0.3:
        return "moderate"
    return "low"
