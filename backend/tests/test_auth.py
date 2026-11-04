import datetime as dt

from sqlalchemy import select

from app.models import AuthCode
from tests.conftest import last_code, login


def test_health_needs_no_auth(client):
    r = client.get("/health", headers={"ngrok-skip-browser-warning": "1"})
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_email_code_flow_creates_user_once(client, app):
    h = login(client, app, "Ana@Example.com")
    me = client.get("/me", headers={**h, "ngrok-skip-browser-warning": "1"}).json()
    assert me["email"] == "ana@example.com" and me["notification_email"] == "ana@example.com"
    assert me["language"] == "es" and me["onboarded"] is False
    h2 = login(client, app, "ana@example.com")
    assert client.get("/me", headers=h2).json()["id"] == me["id"]


def test_request_always_204_and_code_not_in_response(client, app):
    r = client.post("/auth/email/request", json={"email": "nobody@example.com"})
    assert r.status_code == 204 and r.content == b""


def test_login_ignores_a_stale_token(client, app):
    client.post("/auth/email/request", json={"email": "t@example.com"}, headers={"Authorization": "Bearer stale"})
    r = client.post("/auth/email/verify", json={"email": "t@example.com", "code": last_code(app)},
                    headers={"Authorization": "Bearer stale"})
    assert r.status_code == 200


def test_code_is_stored_hashed(client, app):
    client.post("/auth/email/request", json={"email": "h@example.com"})
    code = last_code(app)
    with app.state.session_factory() as db:
        row = db.scalars(select(AuthCode)).one()
    assert row.code_hash != code and code not in row.code_hash and len(row.code_hash) == 64


def test_every_other_endpoint_requires_bearer(client):
    for method, path in [("get", "/me"), ("get", "/coverage"), ("get", "/nights"), ("get", "/map"),
                         ("get", "/aois"), ("get", "/alerts"), ("get", "/model-card"), ("delete", "/me")]:
        assert getattr(client, method)(path).status_code == 401, path
    assert client.get("/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_code_expires_after_10_minutes(client, app):
    client.post("/auth/email/request", json={"email": "e@example.com"})
    code = last_code(app)
    with app.state.session_factory() as db:
        row = db.scalars(select(AuthCode)).one()
        row.expires_at = dt.datetime.now(dt.UTC) - dt.timedelta(seconds=1)
        db.commit()
    assert client.post("/auth/email/verify", json={"email": "e@example.com", "code": code}).status_code == 400


def test_code_single_use(client, app):
    client.post("/auth/email/request", json={"email": "s@example.com"})
    code = last_code(app)
    assert client.post("/auth/email/verify", json={"email": "s@example.com", "code": code}).status_code == 200
    assert client.post("/auth/email/verify", json={"email": "s@example.com", "code": code}).status_code == 400


def test_at_most_5_attempts_per_code(client, app):
    client.post("/auth/email/request", json={"email": "a@example.com"})
    code = last_code(app)
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert client.post("/auth/email/verify", json={"email": "a@example.com", "code": wrong}).status_code == 400
    assert client.post("/auth/email/verify", json={"email": "a@example.com", "code": code}).status_code == 400


def test_at_most_3_requests_per_hour_per_email(client):
    for _ in range(3):
        assert client.post("/auth/email/request", json={"email": "r@example.com"}).status_code == 204
    assert client.post("/auth/email/request", json={"email": "r@example.com"}).status_code == 429
    assert client.post("/auth/email/request", json={"email": "other@example.com"}).status_code == 204


def test_strict_validation(client):
    assert client.post("/auth/email/request", json={"email": "not-an-email"}).status_code == 422
    r = client.post("/auth/email/request", json={"email": "x@example.com", "extra": 1})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)
    assert client.post("/auth/email/verify", json={"email": "x@example.com", "code": "12ab56"}).status_code == 422


def test_notification_email_change(client, app):
    h = login(client, app, "main@example.com")
    assert client.post("/auth/email/request", json={"email": "alerts@example.com",
                                                     "purpose": "notification_email"}).status_code == 401
    assert client.post("/auth/email/request", json={"email": "alerts@example.com", "purpose": "notification_email"},
                       headers=h).status_code == 204
    code = last_code(app)
    r = client.post("/auth/email/verify", json={"email": "alerts@example.com", "code": code,
                                                "purpose": "notification_email"}, headers=h)
    assert r.status_code == 200 and set(r.json()) == {"user"}
    assert r.json()["user"]["notification_email"] == "alerts@example.com"
    assert r.json()["user"]["email"] == "main@example.com"


def test_ip_rate_limit(make_app):
    from fastapi.testclient import TestClient

    app = make_app(RATE_LIMIT_PER_MINUTE="3")
    c = TestClient(app)
    h = login(c, app)
    codes = [c.get("/me", headers=h).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
