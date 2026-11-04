"""12. inference.predict (numpy and pandas only) reproduces the sklearn probabilities of the logistic
regression within 1e-9 and returns level, top drivers and the reliability bin."""

import json
import subprocess
import sys

import numpy as np

from frostwatch_ml import config, leakage
from frostwatch_ml.artifacts.export_lr import export_lr
from frostwatch_ml.evaluation.thresholds import reliability_bins
from frostwatch_ml.inference import predict
from frostwatch_ml.models.calibration import apply_platt
from frostwatch_ml.models.logistic import make_lr


def _export(m, va, cal):
    p = m.predict_proba(va)
    return export_lr(m, model_version="lr-test-00000000", threshold=0.4, calibration=cal, level_cuts=[0.3, 0.5, 0.7],
                     levels=["none", "low", "medium", "high"], reliability_bins=reliability_bins(va["frost"], p),
                     data_hash="0" * 64, split_cfg=config.frost_config()["split"])


def test_parity_synthetic_fit(features):
    feats = leakage.feature_list()
    tr = leakage.model_rows(features, "train").iloc[::5]
    va = leakage.model_rows(features, "validation").iloc[::5]
    m = make_lr(feats, C=0.3).fit(tr, tr["frost"].to_numpy(int))
    ex = _export(m, va, None)
    np.testing.assert_allclose(predict.probability(ex, va), m.predict_proba(va), rtol=0, atol=1e-9)
    cal = {"a": 0.9, "b": -0.1}
    ex_c = _export(m, va, cal)
    np.testing.assert_allclose(predict.probability(ex_c, va), apply_platt(m.decision_score(va), cal), rtol=0, atol=1e-9)
    out = predict.predict(ex, va.head(5))
    assert {"probability", "level", "alert", "top_drivers", "reliability_bin"} <= set(out.columns)
    assert len(out["top_drivers"].iloc[0]) == 3


def test_parity_exported_finalist(features):
    exports = sorted(config.REPORTS.glob("lr-*/lr_export.json"))
    if not exports:
        import pytest
        pytest.skip("no exported LR yet (run the export stage)")
    import joblib
    ex = json.loads(exports[-1].read_text())
    model = joblib.load(config.MODELS / ex["model_version"] / "model.joblib")
    va = leakage.model_rows(features, "validation")
    sk = model.predict_proba(va) if not ex["calibration"] else apply_platt(model.decision_score(va), ex["calibration"])
    np.testing.assert_allclose(predict.probability(ex, va), sk, rtol=0, atol=1e-9)


def test_predict_module_has_no_sklearn():
    code = "import sys, frostwatch_ml.inference.predict as p; print(any(m.startswith('sklearn') for m in sys.modules))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip()
    assert out == "False"
