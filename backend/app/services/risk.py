"""AOI risk for a night: the cell whose circle contains the AOI centroid; if several do, the
one with the highest probability."""

from __future__ import annotations

from dataclasses import dataclass

from ..providers.base import CellRecord, level_for
from .coverage import candidate_cells, validate_aoi_polygon

LEVEL_ORDER = {"low": 0, "moderate": 1, "high": 2, "very_high": 3}
THRESHOLDS = (30, 50, 70)

__all__ = ["LEVEL_ORDER", "THRESHOLDS", "AoiRisk", "aoi_risk", "level_for", "threshold_reached"]


@dataclass(frozen=True)
class AoiRisk:
    night_date: str
    probability: float
    level: str
    cell_used: str
    distance_km: float
    record: CellRecord


def threshold_reached(probability: float, threshold_pct: int) -> bool:
    if threshold_pct not in THRESHOLDS:
        raise ValueError(f"threshold must be one of {THRESHOLDS}")
    return probability >= threshold_pct / 100.0


def aoi_risk(polygon: dict, cells: list[CellRecord], radius_km: float) -> AoiRisk | None:
    poly = validate_aoi_polygon(polygon, radius_km)
    by_id = {c.point_id: c for c in cells}
    options = [(by_id[pid], d) for pid, d in candidate_cells(poly, radius_km) if pid in by_id]
    if not options:
        return None
    rec, dist = max(options, key=lambda t: (t[0].probability, -t[1]))
    return AoiRisk(night_date=rec.night_date.isoformat(), probability=rec.probability, level=rec.level,
                   cell_used=rec.point_id, distance_km=round(dist, 2), record=rec)
