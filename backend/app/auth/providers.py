"""Email code authentication provider. Google sign in lives in app/auth/social.py."""

from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import AuthCode
from ..security import code_matches, generate_code, hash_code
from ..services.notify_email import EmailSender, login_code_email

log = logging.getLogger("frostwatch.auth")

CODE_TTL = dt.timedelta(minutes=10)
MAX_REQUESTS_PER_HOUR = 3
MAX_ATTEMPTS = 5


class RateLimited(Exception):
    pass


def _aware(t: dt.datetime) -> dt.datetime:
    return t if t.tzinfo else t.replace(tzinfo=dt.UTC)


class EmailCodeProvider:
    """6-digit code by email: stored hashed, 10 minutes, single use, at most 3 requests per hour
    per email and 5 attempts per code."""

    def __init__(self, settings: Settings, sender: EmailSender) -> None:
        self.settings = settings
        self.sender = sender

    def request_code(self, db: Session, email: str, purpose: str, requester_id: str | None,
                     language: str = "es", now: dt.datetime | None = None) -> None:
        now = now or dt.datetime.now(dt.UTC)
        recent = db.scalar(select(func.count()).select_from(AuthCode).where(
            AuthCode.email == email, AuthCode.created_at > now - dt.timedelta(hours=1)))
        if recent >= MAX_REQUESTS_PER_HOUR:
            raise RateLimited()
        # Only the newest code is valid.
        for old in db.scalars(select(AuthCode).where(AuthCode.email == email, AuthCode.purpose == purpose,
                                                     AuthCode.used_at.is_(None))).all():
            old.used_at = now
        code = generate_code()
        db.add(AuthCode(email=email, purpose=purpose, requester_id=requester_id,
                        code_hash=hash_code(self.settings, email, purpose, code), created_at=now,
                        expires_at=now + CODE_TTL))
        db.commit()
        try:
            self.sender.send(login_code_email(email, code, language))
        except Exception as exc:  # the response stays 204; the failure is logged without the code
            log.warning("login code email failed: %s", type(exc).__name__)

    def verify_code(self, db: Session, email: str, code: str, purpose: str, requester_id: str | None,
                    now: dt.datetime | None = None) -> bool:
        now = now or dt.datetime.now(dt.UTC)
        row = db.scalars(select(AuthCode).where(AuthCode.email == email, AuthCode.purpose == purpose,
                                                AuthCode.used_at.is_(None))
                         .order_by(AuthCode.created_at.desc())).first()
        if row is None or _aware(row.expires_at) <= now or row.attempts >= MAX_ATTEMPTS:
            return False
        if purpose == "notification_email" and row.requester_id != requester_id:
            return False
        row.attempts += 1
        if not code_matches(self.settings, email, purpose, code, row.code_hash):
            db.commit()
            return False
        row.used_at = now
        db.commit()
        return True

