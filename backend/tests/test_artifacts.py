import datetime as dt
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.providers.artifacts import ArtifactsProvider
from app.providers.base import ProviderError
from tests.conftest import fixture_rows, login

NIGHT = dt.date(2018, 7, 15)


def _write(root, rows):
    pd.DataFrame(rows).to_parquet(root / "predictions" / "2018-07-15.parquet", index=False)


def test_valid_fixture(artifacts_dir):
    p = ArtifactsProvider(artifacts_dir)
    assert p.list_nights() == [NIGHT]
    cells = p.get_cells(NIGHT)
    assert len(cells) == 8 and {c.level for c in cells} == {"low", "moderate", "high", "very_high"}
    assert cells[0].name == "El Alto" and cells[0].observed is None
    assert p.get_model_card().model_version == "fixture-lr-0"


def test_tmp_files_are_ignored(artifacts_dir):
    (artifacts_dir / "predictions" / ".2018-07-16.parquet.tmp").write_bytes(b"partial")
    assert ArtifactsProvider(artifacts_dir).list_nights() == [NIGHT]


@pytest.mark.parametrize("change,message", [
    (lambda rows: [{k: v for k, v in r.items() if k != "probability"} for r in rows], "missing columns"),
    (lambda rows: [{**r, "level": "low"} for r in rows], "does not match probability"),
    (lambda rows: [{**rows[0], "point_id": "la_paz"}, *rows[1:]], "unknown point_id"),
    (lambda rows: [{**r, "model_version": "other"} for r in rows], "differs from model_card"),
    (lambda rows: [{**r, "top_drivers": "{bad json"} for r in rows], "not valid JSON"),
    (lambda rows: [{**r, "top_drivers": json.dumps([{"feature": "x", "effect": "sideways", "weight": 1}])} for r in rows],
     "schema error"),
    (lambda rows: [{**r, "probability": 1.5, "level": "very_high"} for r in rows], "schema error"),
    (lambda rows: [{**r, "grid_lat": r["grid_lat"] + 1} for r in rows], "does not match"),
    (lambda rows: [{**r, "night_date": dt.date(2018, 7, 14)} for r in rows], "differs from the file name"),
    (lambda rows: [*rows, rows[0]], "duplicated"),
    (lambda rows: [{**r, "observed_frost": True} for r in rows], "observed_tmin_c missing"),
])
def test_schema_errors_fail_clearly(artifacts_dir, change, message):
    _write(artifacts_dir, change(fixture_rows()))
    with pytest.raises(ProviderError, match=message):
        ArtifactsProvider(artifacts_dir).get_cells(NIGHT)


def test_observed_values(artifacts_dir):
    _write(artifacts_dir, fixture_rows(observed_frost=True, observed_tmin_c=-3.2))
    c = ArtifactsProvider(artifacts_dir).get_cells(NIGHT)[0]
    assert c.observed.frost is True and c.observed.tmin_c == -3.2


def test_bad_model_card(artifacts_dir):
    (artifacts_dir / "model_card.json").write_text(json.dumps({"model_version": "x"}))
    with pytest.raises(ProviderError, match=r"model_card\.json schema error"):
        ArtifactsProvider(artifacts_dir).get_model_card()
    (artifacts_dir / "model_card.json").write_text("{")
    with pytest.raises(ProviderError, match="not valid JSON"):
        ArtifactsProvider(artifacts_dir).get_model_card()


def test_api_with_artifacts_provider(make_app, artifacts_dir):
    app = make_app(DATA_PROVIDER="artifacts", ARTIFACTS_DIR=str(artifacts_dir))
    c = TestClient(app)
    h = login(c, app)
    assert c.get("/nights", headers=h).json() == {"latest": "2018-07-15", "available": ["2018-07-15"]}
    m = c.get("/map", headers=h).json()
    assert m["data_source"] == "FIXTURE" and m["model_version"] == "fixture-lr-0" and len(m["cells"]) == 8
    assert c.get("/map?night=2018-07-16", headers=h).status_code == 404
    card = c.get("/model-card", headers=h).json()
    assert card["metrics"]["validation"]["pr_auc"] == 0.5 and card["metrics"]["test"]["pr_auc"] is None
    assert card["test_status"] == "pending"


def test_api_reports_missing_artifacts(make_app, tmp_path):
    app = make_app(DATA_PROVIDER="artifacts", ARTIFACTS_DIR=str(tmp_path / "nothing"))
    c = TestClient(app)
    h = login(c, app)
    r = c.get("/map", headers=h)
    assert r.status_code == 503 and "unavailable" in r.json()["detail"]
