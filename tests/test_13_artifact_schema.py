"""13. The bundle, the model card and the LR export contain the required keys."""

import json

import pytest

from frostwatch_ml import config
from frostwatch_ml.artifacts import bundle, export_lr, model_card


def test_card_keys_synthetic():
    card = model_card.build_card(model_version="lr-x", model_name="lr", role="production_candidate", params={},
                                 features=["a"], threshold=0.5, metrics_pooled={}, metrics_macro={}, data_hash="0",
                                 features_manifest_sha256="0", split_cfg=config.frost_config()["split"],
                                 calibration=None, label_definition="x")
    assert set(model_card.REQUIRED_KEYS) <= set(card)
    assert card["status"] == "validation metrics only; test pending"
    assert card["attribution"].startswith("Generated using Copernicus Climate Change Service information")


def test_saved_artifacts_keys():
    cards = sorted(config.REPORTS.glob("*/model_card.json"))
    if not cards:
        pytest.skip("no exported artifacts yet")
    for c in cards:
        card = json.loads(c.read_text())
        assert set(model_card.REQUIRED_KEYS) <= set(card), c
        if (config.REPORTS / "final_test_metrics.json").exists():
            assert card["metrics_test"]["pooled"]["n"] > 0 and "test pending" not in card["status"]
            assert card["data"]["test_status"] == "evaluated"
        else:
            assert card["metrics_test"] is None and "test pending" in card["status"]
        meta = json.loads((config.MODELS / card["model_version"] / "bundle_meta.json").read_text())
        assert set(bundle.REQUIRED_KEYS) <= set(meta)
    for e in config.REPORTS.glob("lr-*/lr_export.json"):
        assert set(export_lr.REQUIRED_KEYS) <= set(json.loads(e.read_text()))
