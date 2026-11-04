"""Password registration and login, forgot and reset password, and email code login
(POST /auth/email/request, POST /auth/email/verify). Passwords, hashes, codes and phone
numbers are never logged."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.providers import EmailCodeProvider, RateLimited
from ..deps import auth_rate_limit, current_user, get_db, login_user
from ..models import User
from ..schemas import (
    ChangePasswordIn,
    EmailRequestIn,
    EmailVerifyIn,
    ForgotIn,
    LoginIn,
    RegisterIn,
    ResetIn,
    UserOnlyOut,
    VerifyOut,
)
from ..security import create_session_token, hash_password, password_matches
from ..serializers import user_out

log = logging.getLogger("frostwatch.auth")

router = APIRouter(prefix="/auth/email", tags=["auth"], dependencies=[Depends(auth_rate_limit)])
password_router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(auth_rate_limit)])

MAX_FAILED_PASSWORDS = 5
FAILED_PASSWORD_WINDOW_S = 15 * 60
DUMMY_PASSWORD_HASH = hash_password("timing-equalizer-0")


def _provider(request: Request) -> EmailCodeProvider:
    return EmailCodeProvider(request.app.state.settings, request.app.state.email_sender)


@router.post("/request", status_code=204)
def request_code(body: EmailRequestIn, request: Request, db: Session = Depends(get_db),
                 user: User | None = Depends(login_user)) -> Response:
    email = body.email.lower()
    requester = None
    language = "es"
    if body.purpose == "notification_email":
        if user is None:
            raise HTTPException(401, "missing bearer token")
        requester, language = user.id, user.language
    else:
        existing = db.scalar(select(User).where(User.email == email))
        language = existing.language if existing else "es"
        if body.purpose == "register":
            # Resend for a pending sign up. Always 204, so the response does not reveal
            # whether the email has an unverified account.
            if existing is not None and not existing.email_verified:
                try:
                    _provider(request).request_code(db, email, "register", None, language)
                except RateLimited:
                    pass
            return Response(status_code=204)
    try:
        _provider(request).request_code(db, email, body.purpose, requester, language)
    except RateLimited:
        raise HTTPException(429, "too many code requests for this email, try again later") from None
    return Response(status_code=204)


@router.post("/verify", response_model=VerifyOut | UserOnlyOut)
def verify_code(body: EmailVerifyIn, request: Request, db: Session = Depends(get_db),
                user: User | None = Depends(login_user)):
    email = body.email.lower()
    if body.purpose == "notification_email" and user is None:
        raise HTTPException(401, "missing bearer token")
    if body.purpose == "reset_password":
        raise HTTPException(400, "use POST /auth/password/reset for this code")
    requester = user.id if body.purpose == "notification_email" else None
    if not _provider(request).verify_code(db, email, body.code, body.purpose, requester):
        raise HTTPException(400, "invalid or expired code")
    if body.purpose == "notification_email":
        user.notification_email = email
        db.commit()
        return UserOnlyOut(user=user_out(user))
    account = db.scalar(select(User).where(User.email == email))
    if account is None:
        if body.purpose == "register":
            raise HTTPException(400, "invalid or expired code")
        account = User(email=email, notification_email=email)
        db.add(account)
    # A verified code proves ownership of the address.
    account.email_verified = True
    db.commit()
    token = create_session_token(request.app.state.settings, account.id)
    return VerifyOut(session_token=token, user=user_out(account))


@password_router.post("/register", status_code=202)
def register(body: RegisterIn, request: Request, db: Session = Depends(get_db)) -> Response:
    email = body.email.lower()
    account = db.scalar(select(User).where(User.email == email))
    if account is not None and account.email_verified:
        # Same response as a new registration, so the endpoint does not leak which emails
        # exist. No new code is sent.
        log.info("register attempt for an already verified email")
        return Response(status_code=202)
    if account is None:
        account = User(email=email, notification_email=email, name=body.name, phone=body.phone,
                       password_hash=hash_password(body.password), language=body.language,
                       email_verified=False)
        db.add(account)
    else:
        account.name = body.name
        account.phone = body.phone
        account.password_hash = hash_password(body.password)
        account.language = body.language
    db.commit()
    try:
        _provider(request).request_code(db, email, "register", None, account.language)
    except RateLimited:
        # Same 202 as for a verified email, so the code limit does not reveal new emails.
        log.info("register code limit reached")
    return Response(status_code=202)


@password_router.post("/login", response_model=VerifyOut)
def login_with_password(body: LoginIn, request: Request, db: Session = Depends(get_db)) -> VerifyOut:
    email = body.email.lower()
    limiter = request.app.state.limiter
    if limiter.denied(f"pwfail:{email}", MAX_FAILED_PASSWORDS, FAILED_PASSWORD_WINDOW_S):
        raise HTTPException(429, "too many failed attempts for this email, try again later")
    account = db.scalar(select(User).where(User.email == email))
    # Always run scrypt, against a dummy hash when there is no account, so the response
    # time does not reveal which emails exist.
    stored = account.password_hash if account is not None else None
    if not password_matches(body.password, stored or DUMMY_PASSWORD_HASH) or not stored:
        limiter.allow(f"pwfail:{email}", MAX_FAILED_PASSWORDS, FAILED_PASSWORD_WINDOW_S)
        raise HTTPException(401, "wrong email or password")
    if not account.email_verified:
        try:
            _provider(request).request_code(db, email, "register", None, account.language)
        except RateLimited:
            pass
        raise HTTPException(403, "email_not_verified")
    token = create_session_token(request.app.state.settings, account.id)
    return VerifyOut(session_token=token, user=user_out(account))


@password_router.post("/password/forgot", status_code=202)
def forgot_password(body: ForgotIn, request: Request, db: Session = Depends(get_db)) -> Response:
    email = body.email.lower()
    account = db.scalar(select(User).where(User.email == email))
    if account is not None:
        try:
            _provider(request).request_code(db, email, "reset_password", None, account.language)
        except RateLimited:
            pass
    return Response(status_code=202)


@password_router.post("/password/reset", response_model=VerifyOut)
def reset_password(body: ResetIn, request: Request, db: Session = Depends(get_db)) -> VerifyOut:
    email = body.email.lower()
    if not _provider(request).verify_code(db, email, body.code, "reset_password", None):
        raise HTTPException(400, "invalid or expired code")
    account = db.scalar(select(User).where(User.email == email))
    if account is None:
        raise HTTPException(400, "invalid or expired code")
    account.password_hash = hash_password(body.new_password)
    account.email_verified = True
    db.commit()
    token = create_session_token(request.app.state.settings, account.id)
    return VerifyOut(session_token=token, user=user_out(account))


@password_router.post("/password/change", status_code=204)
def change_password(body: ChangePasswordIn, user: User = Depends(current_user),
                    db: Session = Depends(get_db)) -> Response:
    if not password_matches(body.current_password, user.password_hash):
        raise HTTPException(401, "wrong current password")
    user.password_hash = hash_password(body.new_password)
    db.commit()
    return Response(status_code=204)
