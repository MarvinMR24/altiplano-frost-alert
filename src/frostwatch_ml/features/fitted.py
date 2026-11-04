"""Statistics fitted on TRAINING years only and applied to every row.

- elevation_proxy_m: standard-atmosphere height from the mean 18:00 surface pressure of each cell
  over training nights.
- afternoon_clearness: afternoon mean ssrd divided by the 95th percentile of that quantity for the
  same cell and a +-7 day day-of-year window over training nights, clipped to [0, 1].

`fit` receives the whole table but selects split == "train" itself, so altering other rows can
never change the fitted values. The result is a plain dict (JSON serializable).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..prep.physics import elevation_proxy_m


def fit(df: pd.DataFrame, cfg: dict) -> dict[str, Any]:
    """Fit on rows with split == 'train' only."""
    f = cfg["features"]
    train = df[df["split"] == "train"]
    mean_sp = train.groupby("point_id")["sp_1800_hpa"].mean()
    hw, q = f["clearness_doy_halfwidth"], f["clearness_percentile"] / 100.0
    p95: dict[str, list[float]] = {}
    for pid, g in train.groupby("point_id"):
        doys, vals = g["doy"].to_numpy(), g["ssrd_afternoon_mean_wm2"].to_numpy()
        ref = []
        for d in range(1, 367):
            dist = np.abs(doys - d)
            dist = np.minimum(dist, 366 - dist)
            ref.append(float(np.nanquantile(vals[dist <= hw], q)))
        p95[pid] = ref
    return {"fitted_on": "train", "mean_sp_hpa": mean_sp.to_dict(), "clearness_p95_by_doy": p95,
            "dtype_sp": str(train["sp_1800_hpa"].dtype), "dtype_ssrd": str(train["ssrd_afternoon_mean_wm2"].dtype),
            "clearness_doy_halfwidth": hw, "clearness_percentile": f["clearness_percentile"]}


def apply(df: pd.DataFrame, stats: dict[str, Any]) -> pd.DataFrame:
    """Add elevation_proxy_m and afternoon_clearness using fitted statistics."""
    # Values are restored in the dtype of the source columns (float32 for ERA5-Land), so the derived
    # features keep the precision they had when computed in memory.
    mean_sp = pd.Series(stats["mean_sp_hpa"], dtype=stats.get("dtype_sp", "float64"))
    df["elevation_proxy_m"] = df["point_id"].map(elevation_proxy_m(mean_sp))
    p95 = np.array([stats["clearness_p95_by_doy"][p][d - 1] for p, d in zip(df["point_id"], df["doy"], strict=True)],
                   dtype=stats.get("dtype_ssrd", "float64"))
    df["afternoon_clearness"] = np.clip(df["ssrd_afternoon_mean_wm2"] / p95, 0, 1)
    return df
