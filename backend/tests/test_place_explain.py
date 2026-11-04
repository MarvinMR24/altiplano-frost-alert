import datetime as dt
import json

import httpx

from app.config import load_settings
from app.providers.base import CellRecord
from app.schemas import Driver, Reliability
from app.security import RateLimiter
from app.services.place_explain import (
    PlaceExplainer,
    build_place_facts,
    catalog_for,
    template,
    verify,
)
from tests.conftest import login


def rec(day=15, p=0.62, level="high"):
    return CellRecord(point_id="oruro", name="Oruro", lat=-18.0, lon=-67.1, elevation_m=0,
                      night_date=dt.date(2018, 7, day), probability=p, level=level,
                      top_drivers=[Driver(feature="strd_1800_wm2", effect="down", weight=1.5),
                                   Driver(feature="rh_1800_pct", effect="down", weight=0.4)],
                      conditions_1800={"t2m_c": 1.04, "rh_pct": 41.6, "wind_ms": 2.25, "sp_hpa": 640.0},
                      historical_reliability=Reliability(range=(0.5, 0.7), observed_rate=0.58, n=420),
                      model_version="m1", data_source="ERA5-Land reanalysis (Copernicus CDS)")


def facts(lang="es", following=True):
    return build_place_facts(rec(), rec(14, 0.4, "moderate"), rec(16, 0.75, "very_high") if following else None,
                             "producer", lang)


def test_facts_hide_place_date_and_outcome():
    sent = json.dumps(facts().public(), ensure_ascii=False)
    assert "Oruro" not in sent and "2018" not in sent and "-67.1" not in sent
    assert "observed" not in sent and "tmin" not in sent and "640" not in sent  # no pressure term
    assert "{place}" in sent and "{night}" in sent


def test_template_passes_the_verifier_and_handles_no_next_night():
    for lang in ("es", "en", "ay", "qu"):
        for following in (True, False):
            f = facts(lang, following)
            payload = template(f)
            assert verify(payload, f, catalog_for(f)) is None, payload
    assert "75%" in template(facts())["what_next"]
    assert "SENAMHI" in template(facts(following=False))["what_next"]


def test_verifier_rejects_urls_invented_numbers_and_unknown_sources():
    f = facts()
    cat = catalog_for(f)
    good = template(f)
    assert verify({**good, "what_next": "Mañana bajará a -6 grados."}, f, cat) == "number_not_in_facts"
    assert verify({**good, "what_next": "Mire www.ejemplo.com"}, f, cat) == "url_in_text"
    assert verify({**good, "sources": [{"id": "invented", "why": "x"}]}, f, cat) == "sources_not_in_catalog"
    assert verify({**good, "headline": "Pronóstico en tiempo real"}, f, cat) == "banned_phrase"
    assert verify({**good, "what_happened": "Hizo 1 °C y 42% de humedad, riesgo 62%."}, f, cat) is None


def _settings(tmp_path, monkeypatch):
    env = {"BACKEND_VAR_DIR": str(tmp_path / "var"), "SESSION_SECRET": "s" * 40, "MUSE_MOCK": "0",
           "META_API_KEY": "k-test", "META_API_BASE_URL": "https://meta.example/v1"}
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return load_settings()


def _session(tmp_path):
    from app.db import init_db, make_engine
    return init_db(make_engine(f"sqlite:///{tmp_path / 'p.db'}"))()


def _client(replies, seen):
    def handler(request):
        seen.append(json.loads(request.content))
        if not replies:
            return httpx.Response(503)
        return httpx.Response(200, json={"choices": [{"message": {"content": replies.pop(0)}}], "usage": {}})
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_muse_answer_in_aymara_is_filled_cached_and_regenerated_when_data_changes(tmp_path, monkeypatch):
    s = _settings(tmp_path, monkeypatch)
    reply = {"headline": "{place}: juyphi 62%", "what_happened": "{night} arumaxa juyphi utjaspawa.",
             "what_next": "Qhipa arumaxa 75%.", "actions": [{"id": "cover_crops", "text": "Yapu imt'aña."}],
             "sources": [{"id": "senamhi", "why": "Pronóstico uñjañataki."}]}
    seen = []
    ex = PlaceExplainer(s, http=_client([json.dumps(reply), json.dumps(reply)], seen))
    db = _session(tmp_path)
    first = ex.explain_place(db, rec(), None, rec(16, 0.75, "very_high"), "producer", "ay")
    assert first.source == "muse" and first.language == "ay" and not first.cached
    assert first.payload["headline"] == "Oruro: juyphi 62%"
    assert first.payload["what_happened"].startswith("15 de julio de 2018")
    assert first.payload["sources"][0]["url"] == "https://senamhi.gob.bo"
    assert "Oruro" not in json.dumps(seen[0]["messages"], ensure_ascii=False)
    again = ex.explain_place(db, rec(), None, rec(16, 0.75, "very_high"), "producer", "ay")
    assert again.cached and len(seen) == 1
    # New data for the same night (reprocessed) means new facts and a new Muse call.
    ex.explain_place(db, rec(p=0.66), None, rec(16, 0.75, "very_high"), "producer", "ay")
    assert len(seen) == 2


def test_api_error_falls_back_and_is_not_cached(tmp_path, monkeypatch):
    s = _settings(tmp_path, monkeypatch)
    seen = []
    ex = PlaceExplainer(s, http=_client([], seen))
    db = _session(tmp_path)
    out = ex.explain_place(db, rec(), None, None, "resident", "qu")
    assert out.source == "template" and out.language == "es"
    ex.explain_place(db, rec(), None, None, "resident", "qu")
    assert len(seen) == 2  # retried on the next request


def test_user_rate_limit_uses_the_template(tmp_path, monkeypatch):
    s = _settings(tmp_path, monkeypatch)
    seen = []
    limiter = RateLimiter()
    for _ in range(30):
        limiter.allow("explain:u1", 30, 3600)
    out = PlaceExplainer(s, http=_client([], seen)).explain_place(_session(tmp_path), rec(), None, None, "producer",
                                                                  "es", limiter, "u1")
    assert out.source == "template" and not seen


def test_endpoint_requires_auth_and_returns_a_plain_explanation(client, app):
    night = client.get("/nights", headers=login(client, app)).json()["latest"]
    assert client.get(f"/map/oruro/explain?night={night}").status_code == 401
    headers = login(client, app, "b@example.com")
    point = client.get(f"/map?night={night}", headers=headers).json()["cells"][0]["point_id"]
    r = client.get(f"/map/{point}/explain?night={night}&lang=qu", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "template" and body["language"] == "es"  # MUSE_MOCK=1 in tests
    assert body["headline"] and body["what_happened"] and body["what_next"] and body["actions"]
    assert all(s["url"].startswith("https://") for s in body["sources"])
    assert client.get(f"/map/nowhere/explain?night={night}", headers=headers).status_code == 404
