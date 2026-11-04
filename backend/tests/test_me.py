from sqlalchemy import func, select

from app.models import Alert, Aoi, AuthCode, Delivery, Device, User
from tests.conftest import login, square


def test_patch_me(client, app):
    h = login(client, app)
    r = client.patch("/me", headers=h, json={"name": "Ana", "language": "en", "profile": "resident",
                                             "crops": ["potato", "quinoa"], "default_threshold": 70, "onboarded": True})
    assert r.status_code == 200
    body = r.json()
    assert body["language"] == "en" and body["crops"] == ["potato", "quinoa"] and body["default_threshold"] == 70
    assert client.patch("/me", headers=h, json={"default_threshold": 40}).status_code == 422
    assert client.patch("/me", headers=h, json={"notification_email": "x@example.com"}).status_code == 422


def test_devices_idempotent(client, app):
    h = login(client, app)
    for _ in range(2):
        assert client.post("/devices", headers=h, json={"expo_push_token": "ExponentPushToken[abc123]"}).status_code == 204
    with app.state.session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Device)) == 1


def test_delete_me_removes_everything(client, app):
    from app.services.alerting import process_night

    h = login(client, app, "del@example.com")
    client.post("/devices", headers=h, json={"expo_push_token": "ExponentPushToken[zzz]"})
    r = client.post("/aois", headers=h, json={"name": "a", "polygon": square(-68.2, -16.5), "threshold": 30,
                                              "channels": {"push": False, "email": True}})
    assert r.status_code == 201
    with app.state.session_factory() as db:
        night = app.state.provider.latest_night()
        process_night(db, settings=app.state.settings, provider=app.state.provider, night=night, mode="tick",
                      email_sender=app.state.email_sender)
        assert db.scalar(select(func.count()).select_from(Alert)) >= 1
    other = login(client, app, "keep@example.com")
    assert client.delete("/me", headers=h).status_code == 204
    assert client.get("/me", headers=h).status_code == 401
    with app.state.session_factory() as db:
        for model in (Alert, Aoi, Device, Delivery):
            assert db.scalar(select(func.count()).select_from(model)) == 0, model
        assert db.scalar(select(func.count()).select_from(AuthCode).where(AuthCode.email == "del@example.com")) == 0
        assert db.scalar(select(func.count()).select_from(User)) == 1
    assert client.get("/me", headers=other).status_code == 200
