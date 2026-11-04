import datetime as dt
import json

import httpx
from sqlalchemy import func, select

from app.models import Alert, Aoi, Delivery, Device, User
from app.providers.base import level_for
from app.providers.mock import MockProvider
from app.services.alerting import process_night
from tests.conftest import square


class Shifted(MockProvider):
    """Mock with a fixed probability for El Alto, to drive the dedupe rules."""

    def __init__(self, p):
        self.p = p

    def get_cells(self, night):
        cells = super().get_cells(night)
        return [c.model_copy(update={"probability": self.p, "level": level_for(self.p)}) if c.point_id == "el_alto" else c
                for c in cells]


def _push_client(store):
    def handler(request):
        msgs = json.loads(request.content)
        store.extend(msgs)
        return httpx.Response(200, json={"data": [{"status": "ok", "id": f"tk{i}"} for i in range(len(msgs))]})
    return httpx.Client(transport=httpx.MockTransport(handler))


def _seed(app, threshold=30, push=True, email=True, profile="producer"):
    with app.state.session_factory() as db:
        u = User(email="farmer@example.com", notification_email="farmer@example.com", profile=profile)
        db.add(u)
        db.flush()
        db.add(Device(user_id=u.id, expo_push_token="ExponentPushToken[dev1]"))
        db.add(Aoi(user_id=u.id, name="Chacra El Alto", polygon=square(-68.2, -16.5), threshold=threshold,
                   channel_push=push, channel_email=email))
        db.commit()
        return u.id


def _run(app, provider, night=dt.date(2026, 7, 14), store=None, **kw):
    with app.state.session_factory() as db:
        return process_night(db, settings=app.state.settings, provider=provider, night=night, mode="replay",
                             email_sender=app.state.email_sender, push_client=_push_client(store if store is not None else []),
                             **kw)


def _count(app, model):
    with app.state.session_factory() as db:
        return db.scalar(select(func.count()).select_from(model))


def test_alert_created_sent_and_idempotent(app):
    _seed(app)
    pushes = []
    s = _run(app, Shifted(0.62), store=pushes)
    assert len(s.alerts_created) == 1
    assert pushes[0]["data"] == {"alert_id": s.alerts_created[0]} and pushes[0]["title"].startswith("[REPLAY] [MOCK]")
    mail = app.state.email_sender.outbox[-1]
    assert "Chacra El Alto" in mail.subject and "[MOCK]" in mail.subject
    with app.state.session_factory() as db:
        alert = db.get(Alert, s.alerts_created[0])
        assert alert.level == "high" and sorted(alert.channels_sent) == ["email", "push"] and alert.mode == "replay"
        assert {d.channel: d.status for d in db.scalars(select(Delivery)).all()} == {"push": "sent", "email": "sent"}
        assert db.scalars(select(Delivery).where(Delivery.channel == "push")).one().ticket_id == "tk0"
    again = _run(app, Shifted(0.62))
    assert again.alerts_created == [] and again.skipped.get("already_alerted") == 1
    assert _count(app, Alert) == 1 and _count(app, Delivery) == 2


def test_below_threshold_no_alert(app):
    _seed(app, threshold=70)
    s = _run(app, Shifted(0.62))
    assert s.alerts_created == [] and s.skipped == {"below_threshold": 1}


def test_realert_only_when_level_rises_and_max_two_per_24h(app):
    _seed(app)
    assert len(_run(app, Shifted(0.35)).alerts_created) == 1  # moderate
    assert _run(app, Shifted(0.45)).alerts_created == []  # same level
    assert len(_run(app, Shifted(0.55)).alerts_created) == 1  # rose to high
    s = _run(app, Shifted(0.95))  # rose again, but 2 alerts already in 24 h of this night
    assert s.alerts_created == [] and s.skipped == {"max_per_24h": 1}
    # Another night has its own 24 h window.
    assert len(_run(app, Shifted(0.95), night=dt.date(2026, 7, 12)).alerts_created) == 1


def test_dry_run_creates_and_sends_nothing(app):
    _seed(app)
    pushes = []
    s = _run(app, Shifted(0.8), store=pushes, dry_run=True)
    assert s.alerts_created == [] and len(s.would_alert) == 1 and s.would_alert[0]["level"] == "very_high"
    assert pushes == [] and app.state.email_sender.outbox == [] and _count(app, Alert) == 0


def test_channels_respected_and_no_device(app):
    uid = _seed(app, push=True, email=False)
    with app.state.session_factory() as db:
        db.query(Device).filter(Device.user_id == uid).delete()
        db.commit()
    s = _run(app, Shifted(0.8))
    assert s.deliveries == {"push_skipped": 1} and app.state.email_sender.outbox == []


def test_alert_endpoints(client, app):
    from tests.conftest import login

    h = login(client, app, "farmer@example.com")
    aoi = client.post("/aois", headers=h, json={"name": "Chacra", "polygon": square(-68.2, -16.5), "threshold": 30,
                                                "channels": {"push": False, "email": True}}).json()
    s = _run(app, Shifted(0.75))
    alerts = client.get("/alerts", headers=h).json()
    assert [a["id"] for a in alerts] == s.alerts_created and alerts[0]["aoi_id"] == aoi["id"]
    assert alerts[0]["read"] is False and alerts[0]["channels_sent"] == ["email"]
    detail = client.get(f"/alerts/{alerts[0]['id']}", headers=h).json()
    assert detail["level"] == "very_high" and detail["explanation"]["actions"] and detail["driver_groups"]
    assert detail["mode"] == "replay" and detail["data_source"] == "MOCK"
    assert "Test metrics pending" in detail["model_card_summary"]
    assert client.post(f"/alerts/{alerts[0]['id']}/read", headers=h).status_code == 204
    assert client.get("/alerts", headers=h).json()[0]["read"] is True
    other = login(client, app, "other@example.com")
    assert client.get(f"/alerts/{alerts[0]['id']}", headers=other).status_code == 404
