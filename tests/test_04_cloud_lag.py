"""4. cloud_cover_prev_day of night D equals the AgERA5 value of day D-1, never day D."""

import numpy as np
import pandas as pd

from frostwatch_ml import config
from frostwatch_ml.dataio.cds_reader import read_agera5


def test_cloud_lag(features):
    for pid in config.point_ids():
        rows = features[features["point_id"] == pid]
        ag = read_agera5(pid)["cloud_cover_24h"]
        prev = ag.reindex(rows["night_date"] - pd.Timedelta(days=1)).to_numpy()
        same = ag.reindex(rows["night_date"]).to_numpy()
        got = rows["cloud_cover_prev_day"].to_numpy()
        np.testing.assert_array_equal(got, prev)
        ok = ~np.isnan(same)
        assert np.mean(got[ok] == same[ok]) < 0.05, f"{pid}: cloud feature looks like the same-day value"
