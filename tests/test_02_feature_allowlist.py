"""2. Label and identifiers are not features; features are an explicit allowlist with deny patterns."""

import pytest

from frostwatch_ml import config, leakage
from frostwatch_ml.dataio.tables import read_json


def test_allowlist_is_valid_and_matches_table(features):
    feats = leakage.feature_list()
    manifest = read_json(config.PROCESSED / "features_manifest.json")
    assert feats == manifest["feature_columns"]
    for col in ["frost", "tmin_c", "split", "night_date", "point_id", "use"]:
        assert col not in feats
    assert set(feats) <= set(features.columns)
    assert set(features.columns) - set(feats) == {"point_id", "night_date", "split", "use", "frost", "tmin_c"}


@pytest.mark.parametrize("bad", ["tmin_c", "frost", "split", "night_date", "point_id", "year", "night_year",
                                 "row_index", "agera5_tmin_night_c", "label_shifted", "tmin_tonight_c"])
def test_deny_patterns_reject(bad):
    with pytest.raises(leakage.FeatureLeakError):
        leakage.assert_feature_list(["t2m_1800_c", bad])


def test_models_use_allowlist_not_all_columns():
    src = (config.ROOT / "src" / "frostwatch_ml" / "runner.py").read_text()
    assert "leakage.feature_list()" in src
    for p in (config.ROOT / "src" / "frostwatch_ml").rglob("*.py"):
        assert "select_dtypes" not in p.read_text(), f"{p} selects columns by dtype"
