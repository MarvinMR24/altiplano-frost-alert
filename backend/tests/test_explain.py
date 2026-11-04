import datetime as dt
import json

import httpx
from sqlalchemy import func, select

from app.config import load_settings
from app.models import Explanation
from app.providers.base import CellRecord
from app.schemas import Driver, Reliability
from app.services.explain import Explainer, build_facts, catalog_for, template, verify

REC = CellRecord(point_id="oruro", name="Oruro", lat=-18.0, lon=-67.1, elevation_m=0, night_date=dt.date(2018, 7, 15),
                 probability=0.62, level="high",
                 top_drivers=[Driver(feature="strd_1800_wm2", effect="down", weight=1.5),
                              Driver(feature="rh_1800_pct", effect="down", weight=0.4)],
                 conditions_1800={"t2m_c": 1.0}, historical_reliability=Reliability(range=(0.5, 0.7), observed_rate=0.58, n=420),
                 model_version="m1", data_source="ERA5-Land reanalysis (Copernicus CDS)")


def facts(lang="es", profile="producer"):
    return build_facts(REC, profile, lang)


def test_template_passes_the_verifier_in_both_languages():
    for lang in ("es", "en"):
        for profile in ("producer", "resident"):
            f = facts(lang, profile)
            cat = catalog_for(f)
            payload = template(f, cat)
            assert verify(payload, f, cat) is None, payload
            assert "62%" in payload["why"] and "2018-07-15" in payload["headline"]


def test_verifier_rejects_invented_numbers_and_items():
    f = facts()
    cat = catalog_for(f)
    good = template(f, cat)
    bad = {**good, "why": good["why"] + " Puede bajar a -5 C."}
    assert verify(bad, f, cat) == "number_not_in_facts"
    for text in ("Hubo 7 heladas.", "El 15 de julio.", "Noche del 2018-07-16.", "Bajará 2,5 grados."):
        assert verify({**good, "why": text}, f, cat) == "number_not_in_facts", text
    assert verify({**good, "why": "Probabilidad de 62% para el 2018-07-15, de 420 noches el 58%."}, f, cat) is None
    bad = {**good, "actions": [{"id": "invented", "text": "Encienda fogatas."}]}
    assert verify(bad, f, cat) == "actions_not_in_catalog"
    bad = {**good, "caveats": [c for c in good["caveats"] if c["id"] != "reanalysis"]}
    assert verify(bad, f, cat) == "missing_required_caveat"
    bad = {**good, "headline": "Alerta en tiempo real"}
    assert verify(bad, f, cat) == "banned_phrase"
    assert verify({"headline": "x"}, f, cat) == "schema"


def test_catalog_has_no_health_advice():
    f = facts()
    for lang in ("es", "en"):
        for profile in ("producer", "resident"):
            for level in ("moderate", "high", "very_high"):
                f.language, f.profile, f.level = lang, profile, level
                text = json.dumps(catalog_for(f), ensure_ascii=False).lower()
                for word in ("salud", "health", "médic", "medic", "hipotermia", "hypotherm"):
                    assert word not in text


def _settings(tmp_path, monkeypatch, **env):
    base = {"BACKEND_VAR_DIR": str(tmp_path / "var"), "SESSION_SECRET": "s" * 40, "MUSE_MOCK": "0",
            "META_API_KEY": "k-test", "META_API_BASE_URL": "https://meta.example/v1", "MUSE_MAX_CALLS_PER_RUN": "40"}
    for k, v in {**base, **env}.items():
        monkeypatch.setenv(k, v)
    return load_settings()


def _client(replies, seen):
    def handler(request):
        seen.append(json.loads(request.content))
        content = replies.pop(0)
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}],
                                         "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}})
    return httpx.Client(transport=httpx.MockTransport(handler))


def _session(tmp_path):
    from app.db import init_db, make_engine

    return init_db(make_engine(f"sqlite:///{tmp_path / 'e.db'}"))()


def test_muse_reply_is_used_cached_and_logged(tmp_path, monkeypatch):
    s = _settings(tmp_path, monkeypatch)
    f = facts()
    reply = template(f, catalog_for(f))
    reply["headline"] = "Riesgo alto de helada en Oruro"
    seen = []
    ex = Explainer(s, http=_client([json.dumps(reply)], seen))
    db = _session(tmp_path)
    row = ex.explain(db, f)
    assert row.source == "muse" and row.payload["headline"] == "Riesgo alto de helada en Oruro"
    body = seen[0]
    assert body["model"] == "muse-spark-1.3" and body["temperature"] == 0
    assert body["response_format"] == {"type": "json_object"} and body["max_tokens"] == s.muse_max_tokens
    sent = json.dumps(body["messages"])
    assert "@" not in sent and "-67.1" not in sent and "observed_frost" not in sent and "tmin_c" not in sent
    again = ex.explain(db, facts())
    assert again.id == row.id and ex.calls_made == 1
    usage = [json.loads(x) for x in s.muse_usage_log.read_text().splitlines()]
    assert usage[0]["total_tokens"] == 150 and usage[0]["status"] == "ok"


def test_invalid_json_retries_once_then_template(tmp_path, monkeypatch):
    s = _settings(tmp_path, monkeypatch)
    seen = []
    ex = Explainer(s, http=_client(["not json", "still not"], seen))
    row = ex.explain(_session(tmp_path), facts())
    assert row.source == "template" and row.fallback_reason == "invalid_json" and len(seen) == 2


def test_number_check_failure_falls_back_without_retry(tmp_path, monkeypatch):
    s = _settings(tmp_path, monkeypatch)
    f = facts()
    reply = template(f, catalog_for(f))
    reply["why"] = "La temperatura bajará a -7 grados."
    seen = []
    row = Explainer(s, http=_client([json.dumps(reply)], seen)).explain(_session(tmp_path), f)
    assert row.source == "template" and row.fallback_reason == "number_not_in_facts" and len(seen) == 1
    assert "62%" in row.payload["why"]


def test_muse_mock_never_calls_the_api(tmp_path, monkeypatch):
    s = _settings(tmp_path, monkeypatch, MUSE_MOCK="1")
    seen = []
    db = _session(tmp_path)
    row = Explainer(s, http=_client([], seen)).explain(db, facts())
    assert row.source == "template" and seen == []
    assert db.scalar(select(func.count()).select_from(Explanation)) == 1


def test_max_calls_per_run(tmp_path, monkeypatch):
    s = _settings(tmp_path, monkeypatch, MUSE_MAX_CALLS_PER_RUN="0")
    seen = []
    row = Explainer(s, http=_client([], seen)).explain(_session(tmp_path), facts())
    assert row.fallback_reason == "max_calls_per_run" and seen == []
