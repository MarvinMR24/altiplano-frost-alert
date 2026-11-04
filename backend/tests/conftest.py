import json
import os
from pathlib import Path

import pandas as pd
import pytest

TEST_ENV = {
    "APP_ENV": "test",
    "SESSION_SECRET": "test-secret-0123456789-0123456789-0123456789",
    "EMAIL_PROVIDER": "console",
    "DATA_PROVIDER": "mock",
    "MUSE_MOCK": "1",
    "META_API_KEY": "",
    "META_API_BASE_URL": "",
}
FIXTURES = Path(__file__).parent / "fixtures"

# app.main builds an app at import time: point it at a throwaway folder first.
os.environ.update(TEST_ENV)
os.environ.setdefault("BACKEND_VAR_DIR", str(Path(__file__).resolve().parents[1] / "var" / "pytest"))


@pytest.fixture
def make_app(tmp_path, monkeypatch):
    from app.config import load_settings
    from app.main import create_app

    def _make(**env):
        values = {**TEST_ENV, "BACKEND_VAR_DIR": str(tmp_path / "var"),
                  "DATABASE_URL": f"sqlite:///{tmp_path / 'test.db'}", **env}
        for key, value in values.items():
            monkeypatch.setenv(key, value)
        return create_app(load_settings())

    return _make


@pytest.fixture
def app(make_app):
    return make_app()


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


def login(client, app, email="user@example.com"):
    """Run the console email code flow; returns the auth headers."""
    assert client.post("/auth/email/request", json={"email": email}).status_code == 204
    code = last_code(app)
    r = client.post("/auth/email/verify", json={"email": email, "code": code})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['session_token']}"}


def last_code(app):
    text = app.state.email_sender.outbox[-1].text
    return next(w.strip(".") for w in text.split() if w.strip(".").isdigit() and len(w.strip(".")) == 6)


def square(lon, lat, half=0.01):
    ring = [[lon - half, lat - half], [lon + half, lat - half], [lon + half, lat + half], [lon - half, lat + half]]
    return {"type": "Polygon", "coordinates": [[*ring, ring[0]]]}


def fixture_rows(**overrides):
    data = json.loads((FIXTURES / "artifacts" / "night_rows.json").read_text())
    rows = []
    for r in data["rows"]:
        p = r["probability"]
        level = "very_high" if p >= 0.7 else "high" if p >= 0.5 else "moderate" if p >= 0.3 else "low"
        rows.append({**r, "night_date": pd.Timestamp(data["night_date"]).date(), "level": level,
                     "top_drivers": json.dumps([{"feature": "strd_1800_wm2", "effect": "down", "weight": 1.5},
                                                {"feature": "sky_emissivity_1800", "effect": "up", "weight": 1.2}]),
                     "conditions_1800": json.dumps({"t2m_c": 1.0}),
                     "historical_reliability": json.dumps({"range": [0.7, 1.0], "observed_rate": 0.8, "n": 10}),
                     "observed_frost": None, "observed_tmin_c": None, "model_version": "fixture-lr-0",
                     "data_source": "FIXTURE", **overrides})
    return rows


@pytest.fixture
def artifacts_dir(tmp_path):
    root = tmp_path / "artifacts"
    (root / "predictions").mkdir(parents=True)
    (root / "model_card.json").write_text((FIXTURES / "artifacts" / "model_card.json").read_text())
    pd.DataFrame(fixture_rows()).to_parquet(root / "predictions" / "2018-07-15.parquet", index=False)
    return root
