import datetime as dt
import json
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.social import APPLE_ISSUER, GOOGLE_ISSUERS
from tests.conftest import last_code

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
GOOGLE_ENV = {"GOOGLE_CLIENT_ID": "cid.apps.googleusercontent.com", "GOOGLE_CLIENT_SECRET": "test-secret",
              "PUBLIC_BASE_URL": "https://frostwatch.example"}
DEEP_LINK = "exp://192.168.0.91:8081/--/auth/google"


def id_token(iss, aud, email="ana@example.com", verified=True, key=KEY, minutes=5, **extra):
    now = dt.datetime.now(dt.UTC)
    claims = {"iss": iss, "aud": aud, "sub": "provider-sub", "email": email, "email_verified": verified,
              "iat": int(now.timestamp()), "exp": int((now + dt.timedelta(minutes=minutes)).timestamp()), **extra}
    return jwt.encode(claims, key, algorithm="RS256")


def with_keys(app):
    app.state.apple_keys = lambda _token: KEY.public_key()
    app.state.google_keys = lambda _token: KEY.public_key()
    return app


@pytest.fixture
def social_app(make_app):
    return with_keys(make_app())


@pytest.fixture
def sclient(social_app):
    from fastapi.testclient import TestClient
    return TestClient(social_app)


def test_providers_reports_google_only_when_configured(client, make_app):
    from fastapi.testclient import TestClient
    assert client.get("/auth/providers").json() == {"google": False, "apple": True}
    assert TestClient(make_app(**GOOGLE_ENV)).get("/auth/providers").json() == {"google": True, "apple": True}


def test_apple_sign_in_creates_a_verified_user_and_reuses_it(sclient):
    token = id_token(APPLE_ISSUER, "host.exp.Exponent", verified="true")
    r = sclient.post("/auth/apple", json={"identity_token": token, "name": "Rosa", "language": "ay"})
    assert r.status_code == 200, r.text
    user = r.json()["user"]
    assert user["email"] == "ana@example.com" and user["email_verified"] and user["name"] == "Rosa"
    assert user["language"] == "ay" and token not in r.text
    again = sclient.post("/auth/apple", json={"identity_token": token})
    assert again.json()["user"]["id"] == user["id"]


def test_apple_links_to_an_existing_unverified_password_account(sclient, social_app):
    sclient.post("/auth/register", json={"name": "Ana", "email": "ana@example.com", "password": "secret123"})
    r = sclient.post("/auth/apple", json={"identity_token": id_token(APPLE_ISSUER, "host.exp.Exponent")})
    assert r.status_code == 200 and r.json()["user"]["email_verified"] is True
    login = sclient.post("/auth/login", json={"email": "ana@example.com", "password": "secret123"})
    assert login.status_code == 200


@pytest.mark.parametrize("token", [
    id_token(APPLE_ISSUER, "com.someone.else"),
    id_token("https://evil.example", "host.exp.Exponent"),
    id_token(APPLE_ISSUER, "host.exp.Exponent", minutes=-5),
    id_token(APPLE_ISSUER, "host.exp.Exponent", key=OTHER_KEY),
    id_token(APPLE_ISSUER, "host.exp.Exponent", verified="false"),
    id_token(APPLE_ISSUER, "host.exp.Exponent", email=None),
])
def test_apple_rejects_bad_tokens(sclient, token):
    r = sclient.post("/auth/apple", json={"identity_token": token})
    assert r.status_code == 401 and "session_token" not in r.text


def test_google_start_needs_configuration_and_an_app_redirect(sclient, make_app):
    from fastapi.testclient import TestClient
    assert sclient.get("/auth/google/start", params={"redirect": DEEP_LINK}).status_code == 503
    c = TestClient(with_keys(make_app(**GOOGLE_ENV)), follow_redirects=False)
    assert c.get("/auth/google/start", params={"redirect": "https://evil.example/x"}).status_code == 400
    r = c.get("/auth/google/start", params={"redirect": DEEP_LINK, "lang": "qu"})
    assert r.status_code == 302
    url = urlparse(r.headers["location"])
    q = parse_qs(url.query)
    assert url.netloc == "accounts.google.com" and q["client_id"] == [GOOGLE_ENV["GOOGLE_CLIENT_ID"]]
    assert q["redirect_uri"] == ["https://frostwatch.example/auth/google/callback"]
    assert "test-secret" not in r.headers["location"]


def test_google_callback_returns_a_single_use_ticket(make_app):
    from fastapi.testclient import TestClient
    app = with_keys(make_app(**GOOGLE_ENV))
    sent = []

    def handler(request):
        sent.append(dict(parse_qs(request.content.decode())))
        token = id_token(GOOGLE_ISSUERS[0], GOOGLE_ENV["GOOGLE_CLIENT_ID"], email="Luis@Example.com", name="Luis")
        return httpx.Response(200, json={"id_token": token, "access_token": "x"})

    app.state.google_http = httpx.Client(transport=httpx.MockTransport(handler))
    c = TestClient(app, follow_redirects=False)
    start = c.get("/auth/google/start", params={"redirect": DEEP_LINK, "lang": "qu"})
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    cb = c.get("/auth/google/callback", params={"state": state, "code": "auth-code"})
    assert cb.status_code == 302 and cb.headers["location"].startswith(DEEP_LINK + "?ticket=")
    assert sent[0]["client_secret"] == ["test-secret"] and sent[0]["code"] == ["auth-code"]
    ticket = parse_qs(urlparse(cb.headers["location"]).query)["ticket"][0]
    r = c.post("/auth/ticket", json={"ticket": ticket})
    assert r.status_code == 200 and r.json()["user"]["email"] == "luis@example.com"
    assert r.json()["user"]["language"] == "qu" and r.json()["user"]["name"] == "Luis"
    assert c.post("/auth/ticket", json={"ticket": ticket}).status_code == 401  # single use


def test_google_cancel_and_bad_state(make_app):
    from fastapi.testclient import TestClient
    c = TestClient(with_keys(make_app(**GOOGLE_ENV)), follow_redirects=False)
    start = c.get("/auth/google/start", params={"redirect": DEEP_LINK})
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    r = c.get("/auth/google/callback", params={"state": state, "error": "access_denied"})
    assert r.headers["location"] == DEEP_LINK + "?error=cancelled"
    assert c.get("/auth/google/callback", params={"state": "forged", "code": "x"}).status_code == 400


def test_secret_values_not_logged(sclient, caplog):
    token = id_token(APPLE_ISSUER, "host.exp.Exponent")
    with caplog.at_level("DEBUG"):
        sclient.post("/auth/apple", json={"identity_token": token + "x"})
    assert token not in caplog.text and json.dumps(token) not in caplog.text


def test_email_code_login_still_works(sclient, social_app):
    assert sclient.post("/auth/email/request", json={"email": "c@example.com"}).status_code == 204
    r = sclient.post("/auth/email/verify", json={"email": "c@example.com", "code": last_code(social_app)})
    assert r.status_code == 200
