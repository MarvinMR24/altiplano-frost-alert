"""5. Fitted statistics (clearness percentiles, elevation proxy, LR scaler and coefficients, climatology)
do not change when validation, test and 2026 rows are altered. No imputation is fitted (no missing values)."""

import numpy as np
import pandas as pd

from frostwatch_ml import config, leakage
from frostwatch_ml.features import fitted
from frostwatch_ml.models.baselines import Climatology
from frostwatch_ml.models.logistic import make_lr


def _altered(df):
    out = df.copy()
    other = out["split"] != "train"
    rng = np.random.default_rng(config.SEED)
    for c in leakage.feature_list() + ["sp_1800_hpa", "ssrd_afternoon_mean_wm2"]:
        if pd.api.types.is_integer_dtype(out[c]):
            out.loc[other, c] = pd.array(rng.integers(0, 2, other.sum()), dtype=out[c].dtype)
        else:
            out.loc[other, c] = rng.normal(0, 1000, other.sum()).astype(out[c].dtype)
    out.loc[other, "frost"] = pd.array(rng.integers(0, 2, other.sum()), dtype=out["frost"].dtype)
    return out


def test_fitted_stats_train_only(features, frost_cfg):
    df = features.assign(doy=features["night_date"].dt.day_of_year)
    a = fitted.fit(df, frost_cfg)
    b = fitted.fit(_altered(df), frost_cfg)
    assert a == b
    assert a["fitted_on"] == "train"


def test_scaler_lr_and_climatology_train_only(features):
    feats = leakage.feature_list()
    alt = _altered(features)
    tr_a, tr_b = leakage.model_rows(features, "train"), leakage.model_rows(alt, "train")
    m1 = make_lr(feats).fit(tr_a, tr_a["frost"].to_numpy(int))
    m2 = make_lr(feats).fit(tr_b, tr_b["frost"].to_numpy(int))
    s1, s2 = m1.estimator.named_steps["scaler"], m2.estimator.named_steps["scaler"]
    np.testing.assert_array_equal(s1.mean_, s2.mean_)
    np.testing.assert_array_equal(s1.scale_, s2.scale_)
    np.testing.assert_array_equal(m1.estimator.named_steps["lr"].coef_, m2.estimator.named_steps["lr"].coef_)
    c1 = Climatology().fit(tr_a, tr_a["frost"].to_numpy(int))
    c2 = Climatology().fit(tr_b, tr_b["frost"].to_numpy(int))
    for pid in c1.table_:
        np.testing.assert_array_equal(c1.table_[pid], c2.table_[pid])


def test_no_imputation_needed(features):
    feats = leakage.feature_list()
    for split in ("train", "validation"):
        assert not leakage.model_rows(features, split)[feats].isna().any().any()
    for p in (config.ROOT / "src").rglob("*.py"):
        assert "SimpleImputer" not in p.read_text()
