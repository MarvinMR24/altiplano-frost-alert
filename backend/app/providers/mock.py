"""Deterministic synthetic data for development. Every record is flagged data_source "MOCK";
none of these numbers come from the model or the reanalysis."""

from __future__ import annotations

import datetime as dt
import random

from ..schemas import Driver, Observed, Reliability
from .base import CellRecord, DataProvider, MetricsIn, ModelCardIn, NightNotFound, level_for, load_cells

MOCK = "MOCK"
MOCK_VERSION = "MOCK"
SEED = 42
NIGHTS = [dt.date(2026, 7, 10) + dt.timedelta(days=i) for i in range(5)]
# One value per level band twice, shuffled per night, so every night shows all four levels.
PROBABILITIES = [0.12, 0.24, 0.36, 0.45, 0.56, 0.64, 0.76, 0.91]
FEATURES = ["strd_1800_wm2", "sky_emissivity_1800", "rh_1800_pct", "doy_cos", "prev_night_tmin_c",
            "afternoon_clearness", "wind_1800_ms", "dewpoint_depression_1800_c"]


class MockProvider(DataProvider):
    name = "mock"

    def list_nights(self) -> list[dt.date]:
        return list(NIGHTS)

    def get_cells(self, night: dt.date) -> list[CellRecord]:
        if night not in NIGHTS:
            raise NightNotFound(str(night))
        idx = NIGHTS.index(night)
        rng = random.Random(SEED + idx)
        probs = PROBABILITIES[:]
        rng.shuffle(probs)
        out = []
        for cell, p in zip(load_cells(), probs, strict=True):
            drivers = []
            for feat in rng.sample(FEATURES, 4):
                drivers.append(Driver(feature=feat, effect=rng.choice(["up", "down"]), weight=round(rng.uniform(0.1, 2.0), 2)))
            lo = min(int(p * 10) / 10, 0.9)
            observed = None
            if idx < len(NIGHTS) - 1:
                observed = Observed(frost=rng.random() < p, tmin_c=round(rng.uniform(-8, 4), 1))
            out.append(CellRecord(
                point_id=cell.point_id, name=cell.name, lat=cell.lat, lon=cell.lon, elevation_m=0.0,
                night_date=night, probability=p, level=level_for(p), top_drivers=drivers,
                conditions_1800={"t2m_c": round(rng.uniform(-2, 10), 1), "d2m_c": round(rng.uniform(-15, -2), 1),
                                 "rh_pct": round(rng.uniform(15, 70), 0), "wind_ms": round(rng.uniform(0.5, 6), 1)},
                historical_reliability=Reliability(range=(lo, round(lo + 0.1, 1)), observed_rate=round(rng.uniform(0, 1), 2),
                                                   n=rng.randint(50, 900)),
                observed=observed, model_version=MOCK_VERSION, data_source=MOCK))
        return out

    def get_model_card(self) -> ModelCardIn:
        empty = MetricsIn()
        return ModelCardIn(model_version=MOCK_VERSION, trained_years=(1985, 2009), n_cells=8,
                           metrics={"validation": empty, "test": None}, data_source=MOCK,
                           limitations=["MOCK data: synthetic values for development only, not model output."])
