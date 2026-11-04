"""FastAPI dependencies: database session, current user, provider and rate limits."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import Settings
from .models import User
from .providers import DataProvider
from .security import decode_session_token

bearer = HTTPBearer(auto_error=False)


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Iterator[Session]:
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


def get_provider_dep(request: Request) -> DataProvider:
    return request.app.state.provider


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit(request: Request) -> None:
    settings: Settings = request.app.state.settings
    if not request.app.state.limiter.allow(f"ip:{client_key(request)}", settings.rate_limit_per_minute, 60):
        raise HTTPException(429, "too many requests")


def auth_rate_limit(request: Request) -> None:
    if not request.app.state.limiter.allow(f"auth:{client_key(request)}", 20, 60):
        raise HTTPException(429, "too many requests")


def optional_user(request: Request, creds: HTTPAuthorizationCredentials | None = Depends(bearer),
                  db: Session = Depends(get_db)) -> User | None:
    if creds is None or creds.scheme.lower() != "bearer":
        return None
    user_id = decode_session_token(request.app.state.settings, creds.credentials)
    if user_id is None:
        raise HTTPException(401, "invalid or expired session")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(401, "invalid or expired session")
    return user


def login_user(request: Request, creds: HTTPAuthorizationCredentials | None = Depends(bearer),
               db: Session = Depends(get_db)) -> User | None:
    """Like optional_user, but a stale token is ignored (a login must not fail because of it)."""
    try:
        return optional_user(request, creds, db)
    except HTTPException:
        return None


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(401, "missing bearer token")
    return user
