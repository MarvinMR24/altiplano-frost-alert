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


def _base_reply():
    return {"headline": "{place}: riesgo 62%", "what_happened": "La noche del {night} el riesgo fue alto.",
            "what_next": "La noche siguiente fue 75%.", "actions": [{"id": "cover_crops", "text": "Cubra los cultivos."}],
            "sources": [{"id": "senamhi", "why": "Pronóstico oficial."}]}


def _translation(prefix):
    return {"headline": "{place}: juyphi 62%", "what_happened": f"{prefix} {{night}} arumaxa.",
            "what_next": "Qhipa arumaxa 75%.", "actions": ["Yapu imt'aña."], "sources": ["Pronóstico uñjañataki."]}


def test_one_base_explanation_then_translations_per_language(tmp_path, monkeypatch):
    s = _settings(tmp_path, monkeypatch)
    replies = [json.dumps(_base_reply()), json.dumps(_translation("Ay")), json.dumps(_translation("Qu"))]
    seen = []
    ex = PlaceExplainer(s, http=_client(replies, seen))
    db = _session(tmp_path)
    nxt = rec(16, 0.75, "very_high")
    ay = ex.explain_place(db, rec(), None, nxt, "producer", "ay")
    # First request in Aymara: one generation (Spanish base) plus one translation.
    assert len(seen) == 2 and ay.source == "muse" and ay.language == "ay" and ay.translated
    assert ay.payload["headline"] == "Oruro: juyphi 62%"
    assert ay.payload["what_happened"].endswith("15 de julio de 2018 arumaxa.")
    assert ay.payload["sources"][0]["url"] == "https://senamhi.gob.bo"
    sent = json.dumps([m["messages"] for m in seen], ensure_ascii=False)
    assert "Oruro" not in sent and "2018" not in sent
    assert '"language": "ay"' in seen[1]["messages"][1]["content"] and "{place}" in seen[1]["messages"][1]["content"]
    # Spanish reuses the base, Aymara is stored, Quechua costs only one translation.
    es = ex.explain_place(db, rec(), None, nxt, "producer", "es")
    assert es.language == "es" and not es.translated and es.payload["headline"] == "Oruro: riesgo 62%"
    assert ex.explain_place(db, rec(), None, nxt, "producer", "ay").cached and len(seen) == 2
    qu = ex.explain_place(db, rec(), None, nxt, "producer", "qu")
    assert qu.language == "qu" and len(seen) == 3
    # New data for the same night means a new base explanation.
    ex.explain_place(db, rec(p=0.66), None, nxt, "producer", "es")
    assert len(seen) == 4


def test_bad_translation_returns_spanish_and_is_not_requested_again(tmp_path, monkeypatch):
    s = _settings(tmp_path, monkeypatch)
    bad = {**_translation("Ay"), "what_next": "Qhipa arumaxa -9 grados."}
    seen = []
    ex = PlaceExplainer(s, http=_client([json.dumps(_base_reply()), json.dumps(bad)], seen))
    db = _session(tmp_path)
    out = ex.explain_place(db, rec(), None, rec(16, 0.75, "very_high"), "producer", "ay")
    assert out.language == "es" and not out.translated and out.source == "muse"
    again = ex.explain_place(db, rec(), None, rec(16, 0.75, "very_high"), "producer", "ay")
    assert again.language == "es" and len(seen) == 2


def test_template_base_gives_english_template_and_spanish_for_ay(tmp_path, monkeypatch):
    s = _settings(tmp_path, monkeypatch)
    monkeypatch.setenv("MUSE_MOCK", "1")
    s = load_settings()
    ex = PlaceExplainer(s)
    db = _session(tmp_path)
    en = ex.explain_place(db, rec(), None, None, "producer", "en")
    assert en.language == "en" and en.payload["headline"].startswith("Frost:")
    ay = ex.explain_place(db, rec(), None, None, "producer", "ay")
    assert ay.language == "es" and ay.source == "template"


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


def _raw_client(bodies, seen):
    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=bodies.pop(0))
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_empty_reply_from_reasoning_falls_back_without_crashing_and_retries(tmp_path, monkeypatch):
    s = _settings(tmp_path, monkeypatch)
    cut = {"choices": [{"message": {"content": None}, "finish_reason": "length"}],
           "usage": {"completion_tokens": 700, "completion_tokens_details": {"reasoning_tokens": 700}}}
    good = template(facts())
    parts = {"choices": [{"message": {"content": [{"type": "text", "text": json.dumps(good)}]}, "finish_reason": "stop"}]}
    seen = []
    ex = PlaceExplainer(s, http=_raw_client([cut, parts], seen))
    db = _session(tmp_path)
    first = ex.explain_place(db, rec(), rec(14, 0.4, "moderate"), rec(16, 0.75, "very_high"), "producer", "es")
    assert first.source == "template" and not first.cached and first.payload["headline"]
    assert seen[0]["max_tokens"] == s.muse_max_tokens >= 8000
    second = ex.explain_place(db, rec(), rec(14, 0.4, "moderate"), rec(16, 0.75, "very_high"), "producer", "es")
    assert second.source == "muse" and len(seen) == 2  # truncated reply was not stored
    log = [json.loads(x) for x in s.muse_usage_log.read_text().splitlines()]
    assert log[0]["status"] == "place_truncated" and log[0]["reasoning_tokens"] == 700
