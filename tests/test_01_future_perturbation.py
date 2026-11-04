"""1. Replacing every raw value after 22:00 UTC of D (noise or NaN) must not change any feature of night D,
including the previous-night features. The label may change."""

import numpy as np
import pandas as pd
import pytest

from frostwatch_ml import config
from frostwatch_ml.dataio.cds_reader import ERA5_VARS, read_agera5, read_era5land
from frostwatch_ml.dataio.tables import read_json
from frostwatch_ml.features import fitted, night_table
from frostwatch_ml.prep.units import convert_era5land

CELLS = ["el_alto", "charana", "huanuni"]
N_NIGHTS = 30


def _build(pid, raw, ag, cfg, day, stats):
    df, _ = night_table.build_point_frame(pid, convert_era5land(raw), ag, cfg, days=pd.DatetimeIndex([day]))
    return fitted.apply(df, stats)


@pytest.mark.parametrize("pid", CELLS)
def test_features_ignore_future(pid, features, frost_cfg):
    rng = np.random.default_rng(config.SEED)
    stats = read_json(config.PROCESSED / "fitted_stats.json")
    feats = night_table.feature_columns()
    raw_all = read_era5land(pid)
    ag_all = read_agera5(pid)
    rows = features[(features["point_id"] == pid) & (features["use"] == "labeled")]
    nights = rng.choice(rows["night_date"].to_numpy()[5:-5], size=N_NIGHTS, replace=False)
    label_changed = 0
    for i, d in enumerate(pd.DatetimeIndex(nights)):
        raw = raw_all.loc[d - pd.Timedelta(days=2): d + pd.Timedelta(days=3)].copy()
        raw.attrs.update(raw_all.attrs)
        cut = d + pd.Timedelta(hours=22)
        base = _build(pid, raw, ag_all, frost_cfg, d, stats)
        stored = rows.loc[rows["night_date"] == d, feats].reset_index(drop=True)
        pd.testing.assert_frame_equal(base[feats].reset_index(drop=True), stored, check_dtype=False)

        bad = raw.copy()
        bad.attrs.update(raw.attrs)
        after = bad.index > cut
        for v in ERA5_VARS:
            bad.loc[after, v] = np.nan if i % 2 else rng.normal(300, 50, after.sum()).astype(bad[v].dtype)
        ag = ag_all.copy()
        fut = ag.index >= d
        for col in ag.columns:
            ag.loc[fut, col] = np.nan if i % 2 else rng.uniform(0, 1, int(fut.sum())).astype(ag[col].dtype)
        pert = _build(pid, bad, ag, frost_cfg, d, stats)
        pd.testing.assert_frame_equal(base[feats], pert[feats], check_exact=True)
        if not (pd.isna(base["tmin_c"].iloc[0]) and pd.isna(pert["tmin_c"].iloc[0])) and base["tmin_c"].iloc[0] != pert["tmin_c"].iloc[0]:
            label_changed += 1
    assert label_changed > 0, "perturbation never reached the label window; the test is not effective"
