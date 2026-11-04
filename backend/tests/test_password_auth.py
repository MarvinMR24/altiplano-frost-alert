import logging
import sqlite3

from sqlalchemy import select

from app.models import AuthCode, User
from app.services.explain import build_facts, content_language
from app.services.notify_email import alert_email
from tests.conftest import last_code

PW = "secret123"
EXPLANATION = {"headline": "h", "why": "w", "actions": ["a1"], "caveats": ["c1"]}


def register(client, email="new@example.com", password=PW, **kw):
    body = {"name": "Ana", "email": email, "password": password, **kw}
    return client.post("/auth/register", json=body)


def verify_register(client, app, email="new@example.com"):
    return client.post("/auth/email/verify",
                       json={"email": email, "code": last_code(app), "purpose": "register"})


def test_register_then_verify_marks_email_verified(client, app):
    assert register(client, phone="+591 70012345").status_code == 202
    r = verify_register(client, app)
    assert r.status_code == 200
    user = r.json()["user"]
    assert user["email_verified"] is True and user["phone"] == "+591 70012345"
    assert user["name"] == "Ana" and "password_hash" not in r.text
    with app.state.session_factory() as db:
        row = db.scalar(select(User).where(User.email == "new@example.com"))
        assert row.password_hash.startswith("scrypt$") and PW not in row.password_hash


def test_register_twice_updates_unverified_user(client, app):
    assert register(client).status_code == 202
    assert register(client, password="other456", phone="+591 1").status_code == 202
    assert verify_register(client, app).status_code == 200
    r = client.post("/auth/login", json={"email": "new@example.com", "password": "other456"})
    assert r.status_code == 200


def test_register_existing_verified_sends_nothing(client, app):
    assert register(client).status_code == 202
    assert verify_register(client, app).status_code == 200
    sent = len(app.state.email_sender.outbox)
    assert register(client).status_code == 202
    assert len(app.state.email_sender.outbox) == sent


def test_register_resend_code_can_be_verified(client, app):
    assert register(client).status_code == 202
    r = client.post("/auth/email/request", json={"email": "new@example.com", "purpose": "register"})
    assert r.status_code == 204
    assert verify_register(client, app).status_code == 200


def test_register_resend_sends_nothing_for_unknown_or_verified_email(client, app):
    sent = len(app.state.email_sender.outbox)
    r = client.post("/auth/email/request", json={"email": "nobody@example.com", "purpose": "register"})
    assert r.status_code == 204 and len(app.state.email_sender.outbox) == sent
    assert register(client).status_code == 202
    assert verify_register(client, app).status_code == 200
    sent = len(app.state.email_sender.outbox)
    r = client.post("/auth/email/request", json={"email": "new@example.com", "purpose": "register"})
    assert r.status_code == 204 and len(app.state.email_sender.outbox) == sent


def test_register_code_limit_still_returns_202(client):
    statuses = {register(client).status_code for _ in range(6)}
    assert statuses == {202}


def test_login_runs_scrypt_for_unknown_email(client, monkeypatch):
    from app.routers import auth

    calls = []
    real = auth.password_matches
    monkeypatch.setattr(auth, "password_matches", lambda pw, stored: calls.append(stored) or real(pw, stored))
    r = client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong999"})
    assert r.status_code == 401
    assert calls == [auth.DUMMY_PASSWORD_HASH]


def test_login_success_and_wrong_credentials(client, app):
    assert register(client).status_code == 202
    assert verify_register(client, app).status_code == 200
    ok = client.post("/auth/login", json={"email": "new@example.com", "password": PW})
    assert ok.status_code == 200 and "session_token" in ok.json()
    wrong = client.post("/auth/login", json={"email": "new@example.com", "password": "wrong999"})
    unknown = client.post("/auth/login", json={"email": "nobody@example.com", "password": "wrong999"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json() == {"detail": "wrong email or password"}


def test_login_unverified_returns_403_and_sends_new_code(client, app):
    assert register(client).status_code == 202
    sent = len(app.state.email_sender.outbox)
    r = client.post("/auth/login", json={"email": "new@example.com", "password": PW})
    assert r.status_code == 403 and r.json() == {"detail": "email_not_verified"}
    assert len(app.state.email_sender.outbox) == sent + 1
    assert verify_register(client, app).status_code == 200


def test_login_code_marks_email_verified(client, app):
    assert client.post("/auth/email/request", json={"email": "code@example.com"}).status_code == 204
    r = client.post("/auth/email/verify", json={"email": "code@example.com", "code": last_code(app)})
    assert r.status_code == 200 and r.json()["user"]["email_verified"] is True


def test_forgot_and_reset_password(client, app):
    assert register(client).status_code == 202
    assert verify_register(client, app).status_code == 200
    assert client.post("/auth/password/forgot", json={"email": "new@example.com"}).status_code == 202
    code = last_code(app)
    r = client.post("/auth/password/reset",
                    json={"email": "new@example.com", "code": code, "new_password": "brandnew9"})
    assert r.status_code == 200 and "session_token" in r.json()
    assert client.post("/auth/login", json={"email": "new@example.com", "password": "brandnew9"}).status_code == 200
    assert client.post("/auth/login", json={"email": "new@example.com", "password": PW}).status_code == 401


def test_forgot_unknown_email_still_202_without_email(client, app):
    assert client.post("/auth/password/forgot", json={"email": "ghost@example.com"}).status_code == 202
    assert app.state.email_sender.outbox == []


def test_reset_with_wrong_code_fails(client, app):
    assert register(client).status_code == 202
    assert verify_register(client, app).status_code == 200
    assert client.post("/auth/password/forgot", json={"email": "new@example.com"}).status_code == 202
    code = last_code(app)
    wrong = "000000" if code != "000000" else "111111"
    r = client.post("/auth/password/reset",
                    json={"email": "new@example.com", "code": wrong, "new_password": "brandnew9"})
    assert r.status_code == 400


def test_five_failed_logins_then_429(client, app):
    assert register(client).status_code == 202
    assert verify_register(client, app).status_code == 200
    for _ in range(5):
        r = client.post("/auth/login", json={"email": "new@example.com", "password": "wrong999"})
        assert r.status_code == 401
    r = client.post("/auth/login", json={"email": "new@example.com", "password": "wrong999"})
    assert r.status_code == 429
    r = client.post("/auth/login", json={"email": "new@example.com", "password": PW})
    assert r.status_code == 429


def test_password_rules_are_enforced(client):
    for bad in ("short1", "longpassword", "12345678"):
        r = register(client, email=f"{bad}@example.com", password=bad)
        assert r.status_code == 422, bad
    assert register(client, email="badphone@example.com", phone="abc").status_code == 422
    assert register(client, email="okphone@example.com", phone="+591 700 11 222").status_code == 202


def test_secret_values_never_in_logs_or_responses(client, app, caplog):
    sentinel_pw = "S3ntinel-Pw9"
    sentinel_phone = "+591 765 S3NT1N3L"
    with caplog.at_level(logging.INFO):
        bodies = []
        bodies.append(register(client, password=sentinel_pw, phone="+591 76543210").text)
        bodies.append(verify_register(client, app).text)
        bodies.append(client.post("/auth/login", json={"email": "new@example.com",
                                                       "password": sentinel_pw}).text)
        bodies.append(client.post("/auth/password/forgot", json={"email": "new@example.com"}).text)
        bodies.append(client.post("/auth/password/reset", json={"email": "new@example.com", "code": last_code(app),
                                                                "new_password": "other-" + sentinel_pw}).text)
        r = client.post("/auth/login", json={"email": "new@example.com", "password": "other-" + sentinel_pw})
        bodies.append(r.text)
        bodies.append(client.get("/me", headers={"Authorization": f"Bearer {r.json()['session_token']}"}).text)
        bodies.append(client.post("/auth/email/request", json={"email": sentinel_phone}).text)
    logs = caplog.text
    for body in bodies:
        assert sentinel_pw not in body and sentinel_phone not in body
    assert sentinel_pw not in logs and sentinel_phone not in logs
    # The phone that was really registered is returned to its owner but never logged.
    assert "76543210" not in logs


def test_phone_deleted_with_user(client, app):
    assert register(client, phone="+591 70012345").status_code == 202
    token = verify_register(client, app).json()["session_token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/me", headers=h).json()["phone"] == "+591 70012345"
    assert client.delete("/me", headers=h).status_code == 204
    with app.state.session_factory() as db:
        assert db.scalar(select(User).where(User.email == "new@example.com")) is None
        assert db.scalars(select(AuthCode)).all() == []


def test_change_password(client, app):
    assert register(client).status_code == 202
    token = verify_register(client, app).json()["session_token"]
    h = {"Authorization": f"Bearer {token}"}
    bad = client.post("/auth/password/change", json={"current_password": "wrong999",
                                                     "new_password": "changed99"}, headers=h)
    assert bad.status_code == 401
    assert client.post("/auth/password/change", json={"current_password": PW,
                                                      "new_password": "changed99"}, headers=h).status_code == 204
    assert client.post("/auth/login", json={"email": "new@example.com", "password": "changed99"}).status_code == 200
    assert client.post("/auth/password/change", json={"current_password": PW,
                                                      "new_password": "changed99"}).status_code == 401


def test_ay_qu_languages_accepted_and_emails_fall_back_to_spanish(client, app):
    assert register(client, email="ay@example.com", language="ay").status_code == 202
    token = verify_register(client, app, "ay@example.com").json()["session_token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/me", headers=h).json()["language"] == "ay"
    assert client.patch("/me", json={"language": "qu"}, headers=h).json()["language"] == "qu"
    assert content_language("ay") == "es" and content_language("qu") == "es"
    msg = alert_email("to@example.com", language="qu", aoi_name="Chacra", level_label="alto",
                      night_date="2024-08-17", explanation=EXPLANATION, probability_pct=80,
                      cell_name="El Alto", model_version="m", data_source="d", mode="tick",
                      processed_at="2024-08-18 00:00:00")
    assert msg.subject.startswith("Helada:")
    import datetime as dt

    from app.providers.base import CellRecord

    rec = CellRecord(point_id="el_alto", name="El Alto", lat=-16.5, lon=-68.2, elevation_m=4000.0,
                     night_date=dt.date(2024, 8, 17), probability=0.8, level="very_high",
                     top_drivers=[{"feature": "strd_1800_wm2", "effect": "down", "weight": 1.5}],
                     conditions_1800={"t2m_c": 1.0},
                     historical_reliability={"range": [0.7, 1.0], "observed_rate": 0.8, "n": 10},
                     observed=None, model_version="fixture-lr-0", data_source="FIXTURE")
    facts = build_facts(rec, "producer", "ay")
    assert facts.language == "es" and facts.level_label == "muy alto"


def test_migration_adds_columns_to_existing_sqlite_file(tmp_path):
    from app.db import init_db, make_engine

    path = tmp_path / "old.db"
    conn = sqlite3.connect(path)
    conn.execute("""CREATE TABLE users (id VARCHAR(32) PRIMARY KEY, email VARCHAR(254), name VARCHAR(80),
        language VARCHAR(2), profile VARCHAR(16), crops JSON, livestock JSON, default_threshold INTEGER,
        notification_email VARCHAR(254), onboarded BOOLEAN, is_demo BOOLEAN, created_at DATETIME)""")
    conn.execute("INSERT INTO users VALUES ('u1', 'old@example.com', 'Old', 'es', 'producer', '[]', '[]', 50,"
                 " 'old@example.com', 1, 0, '2026-01-01 00:00:00')")
    conn.commit()
    conn.close()
    factory = init_db(make_engine(f"sqlite:///{path}"))
    with factory() as db:
        user = db.scalar(select(User).where(User.email == "old@example.com"))
        assert user is not None and user.name == "Old" and user.onboarded is True
        assert user.email_verified is True and user.phone is None and user.password_hash is None
    # Second run is a no-op.
    init_db(make_engine(f"sqlite:///{path}"))
