"""AgERA5 cloud feature with a one-day lag.

The AgERA5 24 h mean cloud cover of date D covers 00:00 to 00:00 local of D, which includes
hours after 18:00 of D. Night D therefore only uses the value of D-1. The join is by point and
date, never by coordinates.
"""

from __future__ import annotations

import pandas as pd


def cloud_prev_day(agera5: pd.DataFrame, nights: pd.DatetimeIndex) -> pd.Series:
    """cloud_cover_24h of day D-1 for every night D (values aligned to `nights`)."""
    return agera5["cloud_cover_24h"].reindex(nights - pd.Timedelta(days=1))
