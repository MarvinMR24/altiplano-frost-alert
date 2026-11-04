"""3. The AgERA5 night minimum and RH at 15:00 exist only in crosschecks.parquet."""

from frostwatch_ml import config, leakage


def test_crosscheck_columns_separate(features, crosschecks):
    xc_cols = config.features_config()["crosscheck_only_columns"]
    assert not set(xc_cols) & set(features.columns)
    assert set(xc_cols) <= set(crosschecks.columns)
    leakage.assert_no_crosscheck_columns(features)
    assert not any("agera5" in c or "rh_15" in c for c in features.columns)
