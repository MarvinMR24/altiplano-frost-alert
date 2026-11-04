"""Night windows and the frost label.

Label of night D: minimum hourly t2m from 22:00 UTC of D to 13:00 UTC of D+1 (18:00 to 09:00
local, 16 values) at or below the frost threshold. The label uses hours AFTER 18:00 of D by
design; it must never be used as a feature for night D. The previous-night label (window ending
13:00 UTC of D) is available before 18:00 of D.
"""

from __future__ import annotations

import pandas as pd


def night_windows(series: pd.Series, start_hour_utc: int, n_hours: int) -> pd.DataFrame:
    """Group an hourly UTC series into windows that start at start_hour_utc on day D and span
    n_hours. Returns min and count per D (the UTC date of the window start)."""
    shifted = series.index - pd.Timedelta(hours=start_hour_utc)
    in_window = shifted.hour < n_hours
    d = pd.DatetimeIndex(shifted[in_window]).normalize()
    g = pd.Series(series.values[in_window], index=d).groupby(level=0)
    return pd.DataFrame({"min": g.min(), "count": g.count()})


def frost_nights(conv: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """tmin_c and frost per night D; null when the window is incomplete."""
    lw = cfg["label_window"]
    w = night_windows(conv["t2m_c"], lw["start_hour_utc"], lw["n_hours"])
    complete = w["count"] == lw["n_hours"]
    out = pd.DataFrame(index=w.index)
    out.index.name = "night_date"
    out["tmin_c"] = w["min"].where(complete)
    out["frost"] = (out["tmin_c"] <= cfg["frost_threshold_c"]).astype("Int64").where(complete)
    return out
