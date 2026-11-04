"""Sessions (JWT HS256, 30 days), login code hashing, password hashing (hashlib.scrypt,
standard library only) and basic in-memory rate limiting."""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque

import jwt

from .config import Settings

ALGORITHM = "HS256"

# Password hashing: scrypt with a random 16 byte salt per user.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32


def hash_password(password: str) -> str:
    """Hash a password. Stored as "scrypt$n$r$p$salt_b64$hash_b64"."""
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P,
                        dklen=_SCRYPT_DKLEN)
    salt_b64 = base64.b64encode(salt).decode()
    hash_b64 = base64.b64encode(dk).decode()
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt_b64}${hash_b64}"


def password_matches(password: str, stored: str | None) -> bool:
    """Compare a password against a stored hash with hmac.compare_digest."""
    if not stored:
        return False
    try:
        name, n, r, p, salt_b64, hash_b64 = stored.split("$")
        if name != "scrypt":
            return False
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(hash_b64.encode())
        dk = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p),
                            dklen=len(expected))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk, expected)


def generate_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def hash_code(settings: Settings, email: str, purpose: str, code: str) -> str:
    msg = f"{email}:{purpose}:{code}".encode()
    return hmac.new(settings.session_secret.encode(), msg, hashlib.sha256).hexdigest()


def code_matches(settings: Settings, email: str, purpose: str, code: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_code(settings, email, purpose, code), stored_hash)


def create_session_token(settings: Settings, user_id: str, now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now(dt.UTC)
    payload = {"sub": user_id, "typ": "session", "iat": int(now.timestamp()),
               "exp": int((now + dt.timedelta(days=settings.session_ttl_days)).timestamp())}
    return jwt.encode(payload, settings.session_secret, algorithm=ALGORITHM)


def decode_session_token(settings: Settings, token: str) -> str | None:
    """User id of a valid session token, or None."""
    try:
        payload = jwt.decode(token, settings.session_secret, algorithms=[ALGORITHM],
                             options={"require": ["sub", "exp", "iat"]})
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "session" or not isinstance(payload.get("sub"), str):
        return None
    return payload["sub"]


class RateLimiter:
    """Sliding-window counter per key, in memory (one process, resets on restart)."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_s: float) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - window_s:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def denied(self, key: str, limit: int, window_s: float) -> bool:
        """True when the key already hit the limit. Records nothing."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - window_s:
                hits.popleft()
            return len(hits) >= limit

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
