"""Alert dedupe rules: one alert per AOI per night, a re-alert only if the level rises, and at
most 2 alerts per AOI per 24 hours of the night clock (the simulated clock of the processed
night, so replaying old nights back to back is not blocked by wall-clock time)."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Alert
from .risk import LEVEL_ORDER

MAX_PER_24H = 2


def night_clock(night_date: str) -> dt.datetime:
    """18:00 local (UTC-4) of the night, the moment the prediction is made: 22:00 UTC."""
    d = dt.date.fromisoformat(night_date)
    return dt.datetime(d.year, d.month, d.day, 22, 0, tzinfo=dt.UTC)


def _aware(t: dt.datetime) -> dt.datetime:
    return t if t.tzinfo else t.replace(tzinfo=dt.UTC)


def check(db: Session, aoi_id: str, night_date: str, level: str, clock_at: dt.datetime) -> tuple[bool, str]:
    """(allowed, reason)."""
    same_night = db.scalars(select(Alert).where(Alert.aoi_id == aoi_id, Alert.night_date == night_date)).all()
    if same_night:
        top = max(LEVEL_ORDER[a.level] for a in same_night)
        if LEVEL_ORDER[level] <= top:
            return False, "already_alerted"
    window_start = clock_at - dt.timedelta(hours=24)
    recent = [a for a in db.scalars(select(Alert).where(Alert.aoi_id == aoi_id)).all()
              if window_start < _aware(a.clock_at) <= clock_at]
    if len(recent) >= MAX_PER_24H:
        return False, "max_per_24h"
    return True, "re_alert_level_rose" if same_night else "new"
