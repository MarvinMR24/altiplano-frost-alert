"""Unit conversions for ERA5-Land hourly data. Pure, row-wise: no time boundary involved."""

from __future__ import annotations

import numpy as np
import pandas as pd


def convert_era5land(raw: pd.DataFrame) -> pd.DataFrame:
    """K to C (t2m, d2m, skt, stl1), Pa to hPa (sp), J m-2 per hour to W m-2 (ssrd, strd, divided by
    3600), m to mm (tp), wind speed from u10 and v10. Keeps t2m in K for the emissivity."""
    out = pd.DataFrame(index=raw.index)
    for v in ("t2m", "d2m", "skt", "stl1"):
        out[f"{v}_c"] = raw[v] - 273.15
    out["t2m_k"] = raw["t2m"]
    out["sp_hpa"] = raw["sp"] / 100.0
    out["ssrd_wm2"] = raw["ssrd"] / 3600.0
    out["strd_wm2"] = raw["strd"] / 3600.0
    out["tp_mm"] = raw["tp"] * 1000.0
    out["u10"] = raw["u10"]
    out["v10"] = raw["v10"]
    out["wind_ms"] = np.hypot(raw["u10"], raw["v10"])
    out.attrs.update(raw.attrs)
    return out
