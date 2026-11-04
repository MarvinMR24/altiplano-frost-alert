"""Database tables. Only the data the app needs: email, name, language, profile, crops,
livestock, push tokens and AOI polygons. DELETE /me removes every row tied to a user."""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    language: Mapped[str] = mapped_column(String(2), default="es")
    profile: Mapped[str] = mapped_column(String(16), default="producer")
    crops: Mapped[list] = mapped_column(JSON, default=list)
    livestock: Mapped[list] = mapped_column(JSON, default=list)
    default_threshold: Mapped[int] = mapped_column(Integer, default=50)
    notification_email: Mapped[str] = mapped_column(String(254))
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuthCode(Base):
    __tablename__ = "auth_codes"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(254), index=True)
    purpose: Mapped[str] = mapped_column(String(32))
    requester_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Device(Base):
    __tablename__ = "devices"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expo_push_token: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Aoi(Base):
    __tablename__ = "aois"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    polygon: Mapped[dict] = mapped_column(JSON)
    threshold: Mapped[int] = mapped_column(Integer)
    channel_push: Mapped[bool] = mapped_column(Boolean, default=True)
    channel_email: Mapped[bool] = mapped_column(Boolean, default=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Explanation(Base):
    """Cache of explanations, keyed by a hash of the facts, the model version and the prompt
    version. Holds no personal data (facts are per cell and night)."""

    __tablename__ = "explanations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    facts_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    model_version: Mapped[str] = mapped_column(String(80))
    language: Mapped[str] = mapped_column(String(2))
    profile: Mapped[str] = mapped_column(String(16))
    level: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(16))  # "muse" or "template"
    payload: Mapped[dict] = mapped_column(JSON)
    fallback_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (UniqueConstraint("aoi_id", "night_date", "level", name="uq_alert_aoi_night_level"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    aoi_id: Mapped[str] = mapped_column(String(32), ForeignKey("aois.id", ondelete="CASCADE"), index=True)
    aoi_name: Mapped[str] = mapped_column(String(80))
    night_date: Mapped[str] = mapped_column(String(10), index=True)
    level: Mapped[str] = mapped_column(String(16))
    probability: Mapped[float] = mapped_column(Float)
    cell_used: Mapped[str] = mapped_column(String(32))
    distance_km: Mapped[float] = mapped_column(Float)
    mode: Mapped[str] = mapped_column(String(16))  # "replay" or "tick"
    clock_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))  # simulated clock of the night
    sent_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    headline: Mapped[str] = mapped_column(String(300))
    explanation_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("explanations.id"), nullable=True)
    channels_sent: Mapped[list] = mapped_column(JSON, default=list)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    data_source: Mapped[str] = mapped_column(String(80))
    model_version: Mapped[str] = mapped_column(String(80))
    run_id: Mapped[str | None] = mapped_column(String(32), nullable=True)


class Delivery(Base):
    __tablename__ = "deliveries"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    alert_id: Mapped[str] = mapped_column(String(32), ForeignKey("alerts.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(8))  # "push" or "email"
    status: Mapped[str] = mapped_column(String(16))  # "sent", "error", "skipped"
    ticket_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    night_date: Mapped[str] = mapped_column(String(10))
    mode: Mapped[str] = mapped_column(String(16))
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    data_source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
