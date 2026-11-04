"""Sign in with Apple and Google (see app/auth/social.py)."""

from __future__ import annotations

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ..auth.social import (
    SocialError,
    allowed_app_redirect,
    apple_email,
    find_or_create_user,
    google_profile,
    google_start_url,
    issue_ticket,
    read_state,
    redeem_ticket,
)
from ..deps import auth_rate_limit, get_db
from ..models import User
from ..schemas import AppleSignInIn, AuthProvidersOut, Language, TicketIn, VerifyOut
from ..security import create_session_token
from ..serializers import user_out

log = logging.getLogger("frostwatch.auth.social")

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(auth_rate_limit)])


def _session(request: Request, user: User) -> VerifyOut:
    return VerifyOut(session_token=create_session_token(request.app.state.settings, user.id), user=user_out(user))


@router.get("/providers", response_model=AuthProvidersOut)
def providers(request: Request) -> AuthProvidersOut:
    return AuthProvidersOut(google=request.app.state.settings.google_enabled, apple=True)


@router.post("/apple", response_model=VerifyOut)
def sign_in_with_apple(body: AppleSignInIn, request: Request, db: Session = Depends(get_db)) -> VerifyOut:
    try:
        email = apple_email(request.app.state.settings, body.identity_token,
                            getattr(request.app.state, "apple_keys", None))
    except SocialError as exc:
        log.info("apple sign in rejected: %s", exc)
        raise HTTPException(401, str(exc)) from None
    return _session(request, find_or_create_user(db, email, body.name, body.language))


@router.get("/google/start")
def google_start(request: Request, redirect: str = Query(max_length=300),
                 lang: Language = Query(default="es")) -> RedirectResponse:
    settings = request.app.state.settings
    if not settings.google_enabled:
        raise HTTPException(503, "google sign in is not configured")
    if not allowed_app_redirect(settings, redirect):
        raise HTTPException(400, "redirect not allowed")
    return RedirectResponse(google_start_url(settings, redirect, lang), status_code=302)


@router.get("/google/callback")
def google_callback(request: Request, state: str = Query(max_length=2048), code: str | None = Query(default=None),
                    error: str | None = Query(default=None), db: Session = Depends(get_db)) -> RedirectResponse:
    settings = request.app.state.settings
    try:
        data = read_state(settings, state)
    except SocialError as exc:
        raise HTTPException(400, str(exc)) from None
    redirect = data["redirect"]
    sep = "&" if "?" in redirect else "?"
    if error or not code:
        # The user closed or refused the Google screen.
        return RedirectResponse(f"{redirect}{sep}{urlencode({'error': 'cancelled'})}", status_code=302)
    try:
        email, name = google_profile(settings, code, getattr(request.app.state, "google_http", None),
                                     getattr(request.app.state, "google_keys", None))
    except SocialError as exc:
        log.info("google sign in failed: %s", exc)
        return RedirectResponse(f"{redirect}{sep}{urlencode({'error': 'failed'})}", status_code=302)
    user = find_or_create_user(db, email, name, data.get("lang", "es"))
    return RedirectResponse(f"{redirect}{sep}{urlencode({'ticket': issue_ticket(settings, user.id)})}",
                            status_code=302)


@router.post("/ticket", response_model=VerifyOut)
def redeem(body: TicketIn, request: Request, db: Session = Depends(get_db)) -> VerifyOut:
    try:
        user_id = redeem_ticket(request.app.state.settings, body.ticket)
    except SocialError as exc:
        raise HTTPException(401, str(exc)) from None
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(401, "invalid ticket")
    return _session(request, user)
