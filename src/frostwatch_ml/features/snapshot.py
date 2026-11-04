"""Features of night D from hourly ERA5-Land data at or before 18:00 local (22:00 UTC) of D.

Every value here is read at an hour <= 22:00 UTC of D: the 18:00 snapshot (22 UTC), 15:00
local (19 UTC), the afternoon hours ending 12:00 to 17:00 local (16 to 21 UTC), the 24 hours
ending at 22 UTC, and the previous night window (22 UTC of D-1 to 13 UTC of D).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..prep.physics import magnus_rh, sky_emissivity
from .labels import frost_nights


def snapshot_features(conv: pd.DataFrame, days: pd.DatetimeIndex, cfg: dict) -> pd.DataFrame:
    """Unfitted features for each night in `days` (one row per day, same order)."""
    f = cfg["features"]

    def at(col, hour_utc, day_offset=0):
        when = days + pd.Timedelta(days=day_offset, hours=hour_utc)
        return conv[col].reindex(when).to_numpy()

    snap, h15 = f["snapshot_hour_utc"], f["hour_1500_utc"]
    aft = np.vstack([at("ssrd_wm2", h) for h in f["afternoon_hours_utc"]])
    aft_l = np.vstack([at("strd_wm2", h) for h in f["afternoon_hours_utc"]])
    t18, td18 = at("t2m_c", snap), at("d2m_c", snap)
    tk18, tk15 = at("t2m_k", snap), at("t2m_k", h15)
    emis18 = sky_emissivity(at("strd_wm2", snap), tk18)
    emis15 = sky_emissivity(at("strd_wm2", h15), tk15)
    tp24 = conv["tp_mm"].rolling(24, min_periods=24).sum()

    return pd.DataFrame({
        "night_date": days,
        "t2m_1800_c": t18,
        "d2m_1800_c": td18,
        "dewpoint_depression_1800_c": t18 - td18,
        "rh_1800_pct": magnus_rh(t18, td18),
        "wind_1800_ms": at("wind_ms", snap),
        "sp_1800_hpa": at("sp_hpa", snap),
        "ssrd_1800_wm2": at("ssrd_wm2", snap),
        "strd_1800_wm2": at("strd_wm2", snap),
        "ssrd_afternoon_mean_wm2": aft.mean(axis=0),
        "strd_afternoon_mean_wm2": aft_l.mean(axis=0),
        "skt_1800_c": at("skt_c", snap),
        "stl1_1800_c": at("stl1_c", snap),
        "precip_24h_mm": tp24.reindex(days + pd.Timedelta(hours=snap)).to_numpy(),
        "cooling_rate_1500_1800_c_per_h": (t18 - at("t2m_c", h15)) / 3.0,
        "sky_emissivity_1800": emis18,
        "sky_emissivity_change_1500_1800": emis18 - emis15,
    })


def previous_night(conv: pd.DataFrame, days: pd.DatetimeIndex, cfg: dict) -> pd.DataFrame:
    """Minimum and frost flag of night D-1 (window ends 13:00 UTC of D, before the 18:00 snapshot)."""
    label = frost_nights(conv, cfg)
    prev = label.reindex(days - pd.Timedelta(days=1))
    return pd.DataFrame({"prev_night_tmin_c": prev["tmin_c"].to_numpy(),
                         "prev_night_frost": prev["frost"].to_numpy()})


def calendar(days: pd.DatetimeIndex) -> pd.DataFrame:
    """Day-of-year encodings of D. `doy` is a helper column for fitted statistics, not a feature."""
    doy = pd.Series(days).dt.day_of_year.to_numpy()
    return pd.DataFrame({"doy": doy,
                         "doy_sin": np.sin(2 * np.pi * doy / 365.25),
                         "doy_cos": np.cos(2 * np.pi * doy / 365.25)})
