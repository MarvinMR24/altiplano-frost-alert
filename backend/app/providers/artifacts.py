"""Reads the ml outputs in artifacts/ (read-only), following docs/artifacts_contract.md:
model_card.json and predictions/<YYYY-MM-DD>.parquet (one row per cell). Every file is
validated; any problem raises ProviderError with a clear message (no silent fallback)."""

from __future__ import annotations

import datetime as dt
import json
import logging
import math
import re
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from .base import CellRecord, DataProvider, ModelCardIn, NightNotFound, ProviderError, cells_by_id, level_for

log = logging.getLogger("frostwatch.artifacts")

NIGHT_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.parquet$")
REQUIRED_COLUMNS = ("point_id", "grid_lat", "grid_lon", "elevation_m", "night_date", "probability", "level",
                    "top_drivers", "conditions_1800", "historical_reliability", "observed_frost",
                    "observed_tmin_c", "model_version", "data_source")
JSON_COLUMNS = ("top_drivers", "conditions_1800", "historical_reliability")
GRID_TOLERANCE_DEG = 0.051


def _missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value)) or value is pd.NA or value is pd.NaT


class ArtifactsProvider(DataProvider):
    name = "artifacts"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._cache: dict[Path, tuple[float, object]] = {}

    @property
    def predictions_dir(self) -> Path:
        return self.root / "predictions"

    def _cached(self, path: Path, loader):
        try:
            mtime = path.stat().st_mtime
        except FileNotFoundError as exc:
            raise ProviderError(f"artifact missing: {path.name}") from exc
        hit = self._cache.get(path)
        if hit and hit[0] == mtime:
            return hit[1]
        value = loader(path)
        self._cache[path] = (mtime, value)
        return value

    def list_nights(self) -> list[dt.date]:
        if not self.predictions_dir.is_dir():
            raise ProviderError(f"artifacts predictions folder missing: {self.predictions_dir}")
        nights = []
        for p in self.predictions_dir.iterdir():
            m = NIGHT_FILE.match(p.name)
            if m:
                try:
                    nights.append(dt.date.fromisoformat(m.group(1)))
                except ValueError:
                    log.warning("ignoring prediction file with an invalid date: %s", p.name)
        return sorted(nights)

    def get_cells(self, night: dt.date) -> list[CellRecord]:
        path = self.predictions_dir / f"{night.isoformat()}.parquet"
        if not path.exists():
            raise NightNotFound(night.isoformat())
        records = self._cached(path, lambda p: self._load_night(p, night))
        card = self.get_model_card()
        bad = {r.model_version for r in records} - {card.model_version}
        if bad:
            raise ProviderError(f"{path.name}: model_version {sorted(bad)} differs from model_card.json ({card.model_version})")
        return records

    def get_model_card(self) -> ModelCardIn:
        return self._cached(self.root / "model_card.json", self._load_card)

    @staticmethod
    def _load_card(path: Path) -> ModelCardIn:
        try:
            return ModelCardIn.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as exc:
            raise ProviderError(f"model_card.json is not valid JSON: {exc.msg} (line {exc.lineno})") from exc
        except ValidationError as exc:
            raise ProviderError(f"model_card.json schema error: {_short(exc)}") from exc

    @staticmethod
    def _load_night(path: Path, night: dt.date) -> list[CellRecord]:
        try:
            df = pd.read_parquet(path)
        except Exception as exc:
            raise ProviderError(f"{path.name}: cannot read parquet ({type(exc).__name__})") from exc
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ProviderError(f"{path.name}: missing columns {missing}")
        extra = sorted(set(df.columns) - set(REQUIRED_COLUMNS))
        if extra:
            log.info("%s: ignoring extra columns %s", path.name, extra)
        if df["point_id"].duplicated().any():
            raise ProviderError(f"{path.name}: duplicated point_id rows")
        known = cells_by_id()
        records = []
        for i, row in enumerate(df.to_dict(orient="records")):
            where = f"{path.name} row {i}"
            pid = row["point_id"]
            if pid not in known:
                raise ProviderError(f"{where}: unknown point_id {pid!r} (the model covers only the 8 cells)")
            cell = known[pid]
            off_lat = abs(float(row["grid_lat"]) - cell.lat)
            off_lon = abs(float(row["grid_lon"]) - cell.lon)
            if off_lat > GRID_TOLERANCE_DEG or off_lon > GRID_TOLERANCE_DEG:
                raise ProviderError(f"{where}: grid cell ({row['grid_lat']}, {row['grid_lon']}) does not match {pid}")
            row_night = pd.Timestamp(row["night_date"]).date()
            if row_night != night:
                raise ProviderError(f"{where}: night_date {row_night} differs from the file name")
            parsed = {}
            for col in JSON_COLUMNS:
                try:
                    parsed[col] = json.loads(row[col]) if isinstance(row[col], str) else row[col]
                except json.JSONDecodeError as exc:
                    raise ProviderError(f"{where}: {col} is not valid JSON") from exc
            observed = None
            if not _missing(row["observed_frost"]):
                if _missing(row["observed_tmin_c"]):
                    raise ProviderError(f"{where}: observed_frost set but observed_tmin_c missing")
                observed = {"frost": bool(row["observed_frost"]), "tmin_c": float(row["observed_tmin_c"])}
            try:
                rec = CellRecord(point_id=pid, name=cell.name, lat=float(row["grid_lat"]), lon=float(row["grid_lon"]),
                                 elevation_m=float(row["elevation_m"]), night_date=row_night,
                                 probability=float(row["probability"]), level=row["level"],
                                 top_drivers=parsed["top_drivers"], conditions_1800=parsed["conditions_1800"],
                                 historical_reliability=parsed["historical_reliability"], observed=observed,
                                 model_version=row["model_version"], data_source=row["data_source"])
            except ValidationError as exc:
                raise ProviderError(f"{where}: schema error: {_short(exc)}") from exc
            if rec.level != level_for(rec.probability):
                raise ProviderError(f"{where}: level {rec.level!r} does not match probability {rec.probability} "
                                    f"(expected {level_for(rec.probability)!r})")
            records.append(rec)
        if not records:
            raise ProviderError(f"{path.name}: no rows")
        return records


def _short(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors()[:3]:
        loc = ".".join(str(x) for x in err["loc"])
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)
