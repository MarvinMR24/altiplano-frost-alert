"""8. Thresholds and hyperparameters are chosen with validation arrays only; any CV inside train is
grouped by year."""

import inspect

from frostwatch_ml import config
from frostwatch_ml.evaluation import thresholds
from frostwatch_ml.models import calibration


def test_threshold_signatures():
    assert list(inspect.signature(thresholds.best_f2_threshold).parameters) == ["y_val", "score_val"]
    assert list(inspect.signature(thresholds.reliability_bins).parameters)[:2] == ["y_val", "prob_val"]


def test_selection_code_uses_validation():
    src = (config.ROOT / "src" / "frostwatch_ml" / "runner.py").read_text()
    assert "best_f2_threshold(y_val, score_val)" in src
    r2 = (config.ROOT / "pipelines" / "05_round2.py").read_text()
    assert "data.val" in r2 and "data.test" not in r2


def test_cv_grouped_by_year():
    src = inspect.getsource(calibration)
    assert "GroupKFold" in src and "groups=year_groups(train)" in src
    assert "night_date\"].dt.year" in src
