"""Database rows and provider records to API schemas."""

from __future__ import annotations

import datetime as dt

from .models import Alert, Aoi, User
from .providers.base import CellRecord, ModelCardIn
from .schemas import AlertSummary, AoiOut, CellOut, Channels, UserOut
from .services.drivers import group_drivers


def iso_utc(t: dt.datetime) -> str:
    t = t if t.tzinfo else t.replace(tzinfo=dt.UTC)
    return t.astimezone(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, name=u.name, phone=u.phone, email_verified=bool(u.email_verified),
                   language=u.language, profile=u.profile, crops=list(u.crops or []),
                   livestock=list(u.livestock or []), default_threshold=u.default_threshold,
                   notification_email=u.notification_email, onboarded=u.onboarded)


def cell_out(r: CellRecord) -> CellOut:
    return CellOut(point_id=r.point_id, name=r.name, lat=r.lat, lon=r.lon, elevation_m=r.elevation_m,
                   probability=r.probability, level=r.level, top_drivers=r.top_drivers,
                   driver_groups=group_drivers(r.top_drivers), conditions_1800=r.conditions_1800,
                   historical_reliability=r.historical_reliability, observed=r.observed)


def aoi_out(a: Aoi, current: dict | None = None) -> AoiOut:
    return AoiOut(id=a.id, name=a.name, polygon=a.polygon, threshold=a.threshold,
                  channels=Channels(push=a.channel_push, email=a.channel_email), current=current)


def alert_summary(a: Alert) -> AlertSummary:
    return AlertSummary(id=a.id, aoi_id=a.aoi_id, aoi_name=a.aoi_name, night_date=a.night_date, level=a.level,
                        probability=a.probability, channels_sent=list(a.channels_sent or []), sent_at=iso_utc(a.sent_at),
                        read=a.read, headline=a.headline)


def model_card_out(card: ModelCardIn) -> dict:
    """ModelCard of the contract. Test metrics stay null until the final evaluation exists."""
    def metrics(m) -> dict:
        keys = ("pr_auc", "f2", "precision", "recall", "f1", "roc_auc", "brier", "accuracy", "majority_accuracy")
        return {k: (getattr(m, k) if m is not None else None) for k in keys}

    test = card.metrics.get("test")
    return {"model_version": card.model_version, "trained_years": list(card.trained_years), "n_cells": card.n_cells,
            "metrics": {"validation": metrics(card.metrics.get("validation")), "test": metrics(test)},
            "test_status": "available" if test is not None and test.pr_auc is not None else "pending",
            "limitations": card.limitations, "data_source": card.data_source}


def model_card_summary(card: ModelCardIn) -> str:
    v = card.metrics.get("validation")
    parts = [f"Model {card.model_version} ({card.model_type}), trained on {card.trained_years[0]}-{card.trained_years[1]}."]
    if v is not None and v.pr_auc is not None and v.f2 is not None:
        parts.append(f"Validation PR-AUC {v.pr_auc:.3f}, F2 {v.f2:.3f}.")
    test = card.metrics.get("test")
    if test is None or test.pr_auc is None:
        parts.append("Test metrics pending.")
    parts.append(f"Data: {card.data_source}.")
    return " ".join(parts)
