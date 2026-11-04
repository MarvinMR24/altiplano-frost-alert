"""9. No feature encodes the year or a time index; latitude and the elevation proxy are cell
constants and the elevation proxy comes from training years only."""

import numpy as np
import pandas as pd

from frostwatch_ml import config, leakage
from frostwatch_ml.dataio.tables import read_json
from frostwatch_ml.prep.physics import elevation_proxy_m


def test_no_year_like_features(features):
    feats = leakage.feature_list()
    train = leakage.model_rows(features, "train")
    year = train["night_date"].dt.year.to_numpy(float)
    corr = {f: abs(np.corrcoef(train[f].to_numpy(float), year)[0, 1]) for f in feats if train[f].std() > 0}
    assert max(corr.values()) < 0.5, corr


def test_cell_constants_from_training(features):
    stats = read_json(config.PROCESSED / "fitted_stats.json")
    assert stats["fitted_on"] == "train"
    for col in config.features_config()["cell_constant_features"]:
        assert (features.groupby("point_id")[col].nunique() == 1).all(), col
    train = features[features["split"] == "train"]
    expected = elevation_proxy_m(train.groupby("point_id")["sp_1800_hpa"].mean())
    got = features.groupby("point_id")["elevation_proxy_m"].first()
    pd.testing.assert_series_equal(got.sort_index(), expected.sort_index(), check_names=False, check_dtype=False, rtol=1e-6)
