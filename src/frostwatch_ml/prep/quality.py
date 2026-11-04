"""EDA screening rules that produce the anomaly list. Flags only; nothing is fixed or dropped.
Each rule looks at single hours or consecutive hours of the same series (no future context beyond
the next hour for jumps)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..dataio.cds_reader import ERA5_VARS


def anomalies_for(point_id: str, conv: pd.DataFrame, eda_cfg: dict) -> pd.DataFrame:
    """Rows (point_id, timestamp_utc, field, rule, value) for every flagged hour of one cell."""
    e = eda_cfg
    rows = []

    def add(mask, field, rule):
        idx = conv.index[mask.values]
        rows.append(pd.DataFrame({"point_id": point_id, "timestamp_utc": idx, "field": field,
                                  "rule": rule, "value": conv.loc[idx, field].astype(float).values}))

    add(conv["d2m_c"] > conv["t2m_c"] + e["dewpoint_tolerance_c"], "d2m_c", "dewpoint_above_temperature")
    add(conv["wind_ms"] < 0, "wind_ms", "wind_negative")
    add(conv["ssrd_wm2"] < 0, "ssrd_wm2", "ssrd_negative")
    add(conv["tp_mm"] < 0, "tp_mm", "precipitation_negative")
    night = np.isin(conv.index.hour, e["ssrd_night_hours_utc"])
    add(pd.Series(night, index=conv.index) & (conv["ssrd_wm2"] > e["ssrd_night_max_wm2"]), "ssrd_wm2", "ssrd_at_night")
    lo, hi = e["strd_range_wm2"]
    add((conv["strd_wm2"] < lo) | (conv["strd_wm2"] > hi), "strd_wm2", "strd_out_of_range")
    add((conv["sp_hpa"] - conv["sp_hpa"].median()).abs() > e["sp_max_offset_from_cell_median_hpa"], "sp_hpa", "sp_far_from_cell_median")

    hourly = conv.index.to_series().diff() == pd.Timedelta(hours=1)
    for field, limit in e["max_hourly_jump"].items():
        jump = conv[field].diff().abs()
        add(hourly & (jump > limit), field, "hourly_jump")

    for field in e["stuck_fields"]:
        s = conv[field]
        run_id = (s != s.shift()).cumsum()
        run_len = s.groupby(run_id).transform("size")
        add(run_len >= e["stuck_min_run_hours"], field, "stuck_value")

    return pd.concat(rows, ignore_index=True)


def coverage_for(point_id: str, raw: pd.DataFrame, conv: pd.DataFrame) -> dict:
    """Coverage, gaps, duplicates and NaN counts of one cell."""
    idx = raw.index
    expected = pd.date_range(idx.min(), idx.max(), freq="h")
    steps = idx.to_series().diff().dropna()
    row = {
        "point_id": point_id,
        "first_utc": idx.min(),
        "last_utc": idx.max(),
        "hours": len(idx),
        "expected_hours": len(expected),
        "missing_hours": len(expected.difference(idx)),
        "duplicate_timestamps": int(idx.duplicated().sum()),
        "non_hourly_steps": int((steps != pd.Timedelta(hours=1)).sum()),
        "grid_lat": round(raw.attrs["grid_lat"], 4),
        "grid_lon": round(raw.attrs["grid_lon"], 4),
        "mean_sp_hpa": round(float(conv["sp_hpa"].mean()), 2),
    }
    for v in ERA5_VARS:
        row[f"nan_{v}"] = int(raw[v].isna().sum())
    return row
