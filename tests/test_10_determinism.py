"""10. The same seed gives identical predictions and metrics."""

import numpy as np

from frostwatch_ml import config, leakage
from frostwatch_ml.evaluation.metrics import metrics_at
from frostwatch_ml.models.registry import build


def test_same_seed_same_metrics(features):
    feats = leakage.feature_list()
    tr = leakage.model_rows(features, "train").iloc[::4]
    va = leakage.model_rows(features, "validation").iloc[::4]
    for kind in ("lr", "lightgbm", "xgboost", "random_forest"):
        kw = {"n_estimators": 50} if kind != "lr" else {}
        outs = []
        for _ in range(2):
            m = build(kind, feats, seed=config.SEED, **kw).fit(tr, tr["frost"].to_numpy(int))
            p = m.predict_proba(va)
            outs.append((p, metrics_at(va["frost"].to_numpy(int), p, 0.5, True)))
        np.testing.assert_array_equal(outs[0][0], outs[1][0])
        assert outs[0][1] == outs[1][1], kind
