"""16. The final evaluation is rehearsed on VALIDATION rows: the frozen models reproduce the stored
validation metrics exactly (nothing is refitted or re-tuned), the report writer works, and the
script refuses to run without its flag. The held-out split is never loaded here."""

import subprocess
import sys

import pytest

from frostwatch_ml import config, runner
from frostwatch_ml.evaluation import final

KEYS = ["pr_auc", "f2", "precision", "recall", "f1", "roc_auc", "accuracy", "majority_class_accuracy", "threshold"]


@pytest.fixture(scope="module")
def frozen():
    data = runner.load_model_data()
    entries = final.frozen_models(data, config.SEED)
    return data, entries, final.evaluate_frozen(entries, data.val)


def test_frozen_models_reproduce_validation_metrics(frozen):
    _, entries, results = frozen
    assert {e["name"] for e in entries} == {"LR_best", "TREE_best", *final.BASELINES}
    for e in entries:
        got, want = results[e["name"]]["pooled"], e["validation_pooled"]
        for k in KEYS:
            assert got[k] == pytest.approx(want[k], abs=1e-9, nan_ok=True), (e["name"], k)
        assert results[e["name"]]["macro_over_cells"]["pr_auc"] == pytest.approx(e["validation_macro"]["pr_auc"], abs=1e-9)


def test_report_writer_rehearsal(frozen, tmp_path):
    data, entries, results = frozen
    path = tmp_path / "report.md"
    final.write_report(path, results, entries, [2010, 2017], {"train": 0.38, "validation": 0.34, "held_out": 0.34},
                       {"status": "not adopted on validation", "final_decision": "ship A"})
    text = path.read_text()
    assert "LR_best (validation)" in text and "climatology" in text and chr(0x2014) not in text


def test_final_eval_refuses_without_flag():
    r = subprocess.run([sys.executable, str(config.ROOT / "pipelines" / "06_final_eval.py")], capture_output=True, text=True)
    assert r.returncode == 2 and "refusing" in r.stdout


def test_serving_rows_need_the_final_report(features, monkeypatch):
    from frostwatch_ml import leakage
    monkeypatch.setattr(leakage, "FINAL_REPORT", "reports/does_not_exist.json")
    with pytest.raises(leakage.TestSetLockedError):
        leakage.serving_rows(features)


def test_serving_rows_hold_only_held_out_years(features):
    from frostwatch_ml import leakage
    if not (config.ROOT / leakage.FINAL_REPORT).exists():
        pytest.skip("final evaluation not run yet")
    rows = leakage.serving_rows(features)
    lo = config.frost_config()["split"]["validation"][1]
    assert rows["night_date"].dt.year.min() > lo
    assert set(rows["split"]) == set(leakage.SERVING_SPLITS)
