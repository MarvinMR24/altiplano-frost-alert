"""Sessions (JWT HS256, 30 days), login code hashing and basic in-memory rate limiting."""

from __future__ import annotations

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

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
