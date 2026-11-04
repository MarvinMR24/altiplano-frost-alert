"""Email code login (POST /auth/email/request, POST /auth/email/verify)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth.providers import EmailCodeProvider, RateLimited
from ..deps import auth_rate_limit, get_db, login_user
from ..models import User
from ..schemas import EmailRequestIn, EmailVerifyIn, UserOnlyOut, VerifyOut
from ..security import create_session_token
from ..serializers import user_out

router = APIRouter(prefix="/auth/email", tags=["auth"], dependencies=[Depends(auth_rate_limit)])


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
    requester = user.id if body.purpose == "notification_email" else None
    if not _provider(request).verify_code(db, email, body.code, body.purpose, requester):
        raise HTTPException(400, "invalid or expired code")
    if body.purpose == "notification_email":
        user.notification_email = email
        db.commit()
        return UserOnlyOut(user=user_out(user))
    account = db.scalar(select(User).where(User.email == email))
    if account is None:
        account = User(email=email, notification_email=email)
        db.add(account)
        db.commit()
    token = create_session_token(request.app.state.settings, account.id)
    return VerifyOut(session_token=token, user=user_out(account))
