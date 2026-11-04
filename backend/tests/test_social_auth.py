import datetime as dt
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.social import GOOGLE_ISSUERS, SocialError, verify_id_token
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
    assert client.get("/auth/providers").json() == {"google": False}
    assert TestClient(make_app(**GOOGLE_ENV)).get("/auth/providers").json() == {"google": True}


CID = GOOGLE_ENV["GOOGLE_CLIENT_ID"]


@pytest.mark.parametrize("token", [
    id_token(GOOGLE_ISSUERS[0], "someone-else.apps.googleusercontent.com"),
    id_token("https://evil.example", CID),
    id_token(GOOGLE_ISSUERS[0], CID, minutes=-5),
    id_token(GOOGLE_ISSUERS[0], CID, key=OTHER_KEY),
])
def test_google_id_token_checks_signature_issuer_audience_and_expiry(token):
    with pytest.raises(SocialError):
        verify_id_token(token, lambda _t: KEY.public_key(), [CID], GOOGLE_ISSUERS)


def test_google_id_token_accepts_a_valid_token():
    claims = verify_id_token(id_token(GOOGLE_ISSUERS[1], CID), lambda _t: KEY.public_key(), [CID], GOOGLE_ISSUERS)
    assert claims["email"] == "ana@example.com"


def _google_app(make_app, tokens):
    app = with_keys(make_app(**GOOGLE_ENV))
    sent = []

    def handler(request):
        sent.append(dict(parse_qs(request.content.decode())))
        return httpx.Response(200, json={"id_token": tokens.pop(0), "access_token": "x"})

    app.state.google_http = httpx.Client(transport=httpx.MockTransport(handler))
    return app, sent


def _google_sign_in(c, lang="es"):
    start = c.get("/auth/google/start", params={"redirect": DEEP_LINK, "lang": lang})
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    return c.get("/auth/google/callback", params={"state": state, "code": "auth-code"})


def test_google_links_to_an_existing_unverified_password_account(make_app):
    from fastapi.testclient import TestClient
    app, _ = _google_app(make_app, [id_token(GOOGLE_ISSUERS[0], CID)])
    c = TestClient(app, follow_redirects=False)
    c.post("/auth/register", json={"name": "Ana", "email": "ana@example.com", "password": "secret123"})
    ticket = parse_qs(urlparse(_google_sign_in(c).headers["location"]).query)["ticket"][0]
    r = c.post("/auth/ticket", json={"ticket": ticket})
    assert r.status_code == 200 and r.json()["user"]["email_verified"] is True and r.json()["user"]["name"] == "Ana"
    assert c.post("/auth/login", json={"email": "ana@example.com", "password": "secret123"}).status_code == 200


@pytest.mark.parametrize("token", [
    id_token(GOOGLE_ISSUERS[0], CID, verified=False),
    id_token(GOOGLE_ISSUERS[0], CID, email=None),
    id_token(GOOGLE_ISSUERS[0], CID, key=OTHER_KEY),
])
def test_google_bad_id_token_returns_to_the_app_with_an_error(make_app, token, caplog):
    from fastapi.testclient import TestClient
    app, _ = _google_app(make_app, [token])
    c = TestClient(app, follow_redirects=False)
    with caplog.at_level("DEBUG"):
        r = _google_sign_in(c)
    assert r.status_code == 302 and r.headers["location"] == DEEP_LINK + "?error=failed"
    assert token not in caplog.text and "test-secret" not in caplog.text


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


def test_email_code_login_still_works(sclient, social_app):
    assert sclient.post("/auth/email/request", json={"email": "c@example.com"}).status_code == 204
    r = sclient.post("/auth/email/verify", json={"email": "c@example.com", "code": last_code(social_app)})
    assert r.status_code == 200
