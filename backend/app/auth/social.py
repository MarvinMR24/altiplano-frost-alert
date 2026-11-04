"""Sign in with Google.

Backend driven OAuth (authorization code flow) so it works in Expo Go: the app
opens /auth/google/start in the system browser, Google returns to /auth/google/callback,
we exchange the code with the client secret, verify the ID token and send the app back to
its deep link with a short, single-use login ticket that it trades for a session.

Accounts are matched by verified email; no provider ids are stored (CLAUDE.md 3.5 store
list). Tokens, codes and tickets are never logged.
"""

from __future__ import annotations

import datetime as dt
import secrets
import threading
from collections.abc import Callable
from urllib.parse import urlencode

import httpx
import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import User

GOOGLE_ISSUERS = ["https://accounts.google.com", "accounts.google.com"]
GOOGLE_KEYS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
STATE_TTL = dt.timedelta(minutes=10)
TICKET_TTL = dt.timedelta(minutes=2)

KeyResolver = Callable[[str], object]


class SocialError(Exception):
    """Sign in failed; the message is safe to return (no token content)."""


_jwk_clients: dict[str, jwt.PyJWKClient] = {}


def remote_keys(url: str) -> KeyResolver:
    """Signing key for a token from the provider's published keys (cached)."""
    client = _jwk_clients.setdefault(url, jwt.PyJWKClient(url, cache_keys=True, lifespan=3600))
    return lambda token: client.get_signing_key_from_jwt(token).key


def verify_id_token(token: str, key_for: KeyResolver, audiences: list[str], issuers: str | list[str]) -> dict:
    try:
        key = key_for(token)
        return jwt.decode(token, key, algorithms=["RS256"], audience=audiences, issuer=issuers,
                          options={"require": ["exp", "iat", "iss", "aud", "sub"]})
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise SocialError(f"invalid identity token ({type(exc).__name__})") from None


def _verified_email(claims: dict) -> str:
    email = claims.get("email")
    verified = claims.get("email_verified")
    if not isinstance(email, str) or "@" not in email:
        raise SocialError("the provider did not share an email")
    if verified not in (True, "true"):
        raise SocialError("the provider email is not verified")
    return email.strip().lower()


def find_or_create_user(db: Session, email: str, name: str | None, language: str) -> User:
    """Existing account with that email, or a new verified one."""
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, notification_email=email, name=(name or None), language=language,
                    email_verified=True)
        db.add(user)
    else:
        # The provider proved the address belongs to this person.
        user.email_verified = True
        if name and not user.name:
            user.name = name
    db.commit()
    return user


# Google -----------------------------------------------------------------------------------

def google_redirect_uri(settings: Settings) -> str:
    return f"{settings.public_base_url}/auth/google/callback"


def allowed_app_redirect(settings: Settings, redirect: str) -> bool:
    return any(redirect.startswith(p) for p in settings.app_redirect_prefixes) and len(redirect) <= 300


def google_start_url(settings: Settings, redirect: str, language: str, now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now(dt.UTC)
    state = jwt.encode({"typ": "google_state", "redirect": redirect, "lang": language,
                        "nonce": secrets.token_urlsafe(12), "exp": int((now + STATE_TTL).timestamp())},
                       settings.session_secret, algorithm="HS256")
    query = {"client_id": settings.google_client_id, "redirect_uri": google_redirect_uri(settings),
             "response_type": "code", "scope": "openid email profile", "state": state,
             "prompt": "select_account"}
    return f"{GOOGLE_AUTH_URL}?{urlencode(query)}"


def read_state(settings: Settings, state: str) -> dict:
    try:
        data = jwt.decode(state, settings.session_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise SocialError("invalid or expired sign in attempt") from None
    if data.get("typ") != "google_state" or not allowed_app_redirect(settings, data.get("redirect", "")):
        raise SocialError("invalid sign in attempt")
    return data


def google_profile(settings: Settings, code: str, http: httpx.Client | None = None,
                   key_for: KeyResolver | None = None) -> tuple[str, str | None]:
    """Exchange the authorization code; returns (verified email, name)."""
    client = http or httpx.Client(timeout=15)
    try:
        resp = client.post(GOOGLE_TOKEN_URL, data={
            "code": code, "client_id": settings.google_client_id, "client_secret": settings.google_client_secret,
            "redirect_uri": google_redirect_uri(settings), "grant_type": "authorization_code"})
    except httpx.HTTPError as exc:
        raise SocialError(f"google unreachable ({type(exc).__name__})") from None
    finally:
        if http is None:
            client.close()
    if resp.status_code != 200 or "id_token" not in resp.json():
        raise SocialError(f"google code exchange failed ({resp.status_code})")
    claims = verify_id_token(resp.json()["id_token"], key_for or remote_keys(GOOGLE_KEYS_URL),
                             [settings.google_client_id], GOOGLE_ISSUERS)
    name = claims.get("name") if isinstance(claims.get("name"), str) else None
    return _verified_email(claims), (name[:80] if name else None)


# Login tickets (Google deep link -> session) ----------------------------------------------

_used_tickets: set[str] = set()
_lock = threading.Lock()


def issue_ticket(settings: Settings, user_id: str, now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now(dt.UTC)
    return jwt.encode({"typ": "login_ticket", "sub": user_id, "jti": secrets.token_urlsafe(16),
                       "exp": int((now + TICKET_TTL).timestamp())}, settings.session_secret, algorithm="HS256")


def redeem_ticket(settings: Settings, ticket: str) -> str:
    """User id of a valid, unused ticket. Each ticket works once."""
    try:
        data = jwt.decode(ticket, settings.session_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise SocialError("invalid or expired ticket") from None
    if data.get("typ") != "login_ticket" or not data.get("jti"):
        raise SocialError("invalid ticket")
    with _lock:
        if data["jti"] in _used_tickets:
            raise SocialError("ticket already used")
        _used_tickets.add(data["jti"])
    return data["sub"]
