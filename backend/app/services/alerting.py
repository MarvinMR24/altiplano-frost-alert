"""Process one night for every user and AOI (replay or manual tick, never a scheduler).

For each AOI: compute the risk; if it reaches the AOI threshold and the dedupe rules allow it,
create the alert, generate the explanation, send push and email according to the AOI channels
and record each delivery. Processing the same night twice creates nothing new.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass, field

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import Alert, Aoi, Delivery, Device, Run, User
from ..providers.base import DataProvider
from . import dedupe
from .coverage import AoiValidationError
from .drivers import group_drivers
from .explain import LEVEL_LABELS, Explainer, build_facts
from .notify_email import EmailError, EmailSender, alert_email
from .notify_push import send_push
from .risk import aoi_risk, threshold_reached

log = logging.getLogger("frostwatch.alerting")


@dataclass
class Summary:
    run_id: str | None
    night_date: str
    mode: str
    dry_run: bool
    data_source: str
    aois_checked: int = 0
    alerts_created: list[str] = field(default_factory=list)
    would_alert: list[dict] = field(default_factory=list)
    skipped: dict[str, int] = field(default_factory=dict)
    deliveries: dict[str, int] = field(default_factory=dict)
    explanations: dict = field(default_factory=dict)

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    def delivered(self, channel: str, status: str) -> None:
        key = f"{channel}_{status}"
        self.deliveries[key] = self.deliveries.get(key, 0) + 1

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def process_night(db: Session, *, settings: Settings, provider: DataProvider, night: dt.date, mode: str,
                  email_sender: EmailSender, email: str | None = None, dry_run: bool = False,
                  push_client: httpx.Client | None = None, explainer: Explainer | None = None) -> Summary:
    if mode not in {"replay", "tick"}:
        raise ValueError("mode must be 'replay' or 'tick'")
    cells = provider.get_cells(night)
    night_str = night.isoformat()
    data_source = cells[0].data_source
    explainer = explainer or Explainer(settings)
    run = Run(night_date=night_str, mode=mode, dry_run=dry_run, data_source=data_source)
    db.add(run)
    db.commit()
    summary = Summary(run.id, night_str, mode, dry_run, data_source)
    clock_at = dedupe.night_clock(night_str)

    users_q = select(User).order_by(User.created_at)
    if email:
        users_q = users_q.where(User.email == email.strip().lower())
    for user in db.scalars(users_q).all():
        for aoi in db.scalars(select(Aoi).where(Aoi.user_id == user.id).order_by(Aoi.created_at)).all():
            summary.aois_checked += 1
            try:
                risk = aoi_risk(aoi.polygon, cells, settings.coverage_radius_km)
            except AoiValidationError:
                summary.skip("aoi_outside_coverage")
                continue
            if risk is None:
                summary.skip("no_cell")
                continue
            if not threshold_reached(risk.probability, aoi.threshold):
                summary.skip("below_threshold")
                continue
            allowed, reason = dedupe.check(db, aoi.id, night_str, risk.level, clock_at)
            if not allowed:
                summary.skip(reason)
                continue
            if dry_run:
                summary.would_alert.append({"aoi_id": aoi.id, "aoi_name": aoi.name, "level": risk.level,
                                            "probability": risk.probability, "cell_used": risk.cell_used,
                                            "channels": [c for c, on in (("push", aoi.channel_push),
                                                                         ("email", aoi.channel_email)) if on]})
                continue
            alert_id = _create_and_send(db, settings, user, aoi, risk, mode, clock_at, run.id, explainer,
                                        email_sender, push_client, summary)
            if alert_id:
                summary.alerts_created.append(alert_id)

    summary.explanations = {**explainer.stats, "muse_calls": explainer.calls_made, "engine": explainer.engine}
    run.finished_at = dt.datetime.now(dt.UTC)
    run.stats = {k: v for k, v in summary.as_dict().items() if k not in {"run_id"}}
    db.commit()
    log.info("night processed night=%s mode=%s dry_run=%s alerts=%d", night_str, mode, dry_run,
             len(summary.alerts_created))
    return summary


def _create_and_send(db: Session, settings: Settings, user: User, aoi: Aoi, risk, mode: str, clock_at: dt.datetime,
                     run_id: str, explainer: Explainer, email_sender: EmailSender, push_client, summary: Summary) -> str | None:
    rec = risk.record
    groups = group_drivers(rec.top_drivers)
    facts = build_facts(rec, user.profile, user.language, groups)
    expl = explainer.explain(db, facts)
    alert = Alert(user_id=user.id, aoi_id=aoi.id, aoi_name=aoi.name, night_date=risk.night_date, level=risk.level,
                  probability=risk.probability, cell_used=risk.cell_used, distance_km=risk.distance_km, mode=mode,
                  clock_at=clock_at, headline=expl.payload["headline"][:300], explanation_id=expl.id,
                  data_source=rec.data_source, model_version=rec.model_version, run_id=run_id)
    db.add(alert)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        summary.skip("already_alerted")
        return None
    db.commit()

    label = LEVEL_LABELS[user.language][risk.level]
    pct = round(risk.probability * 100)
    sent: list[str] = []
    if aoi.channel_push:
        tokens = list(db.scalars(select(Device.expo_push_token).where(Device.user_id == user.id)).all())
        if not tokens:
            db.add(Delivery(alert_id=alert.id, channel="push", status="skipped", error="no_device"))
            summary.delivered("push", "skipped")
        else:
            title, body = _push_text(user.language, label, aoi.name, risk.night_date, pct, mode, rec.data_source)
            results = send_push(tokens, title=title, body=body, data={"alert_id": alert.id},
                                url=settings.expo_push_url, client=push_client)
            for res in results:
                db.add(Delivery(alert_id=alert.id, channel="push", status=res.status, ticket_id=res.ticket_id,
                                error=res.error))
                summary.delivered("push", res.status)
                if res.error == "DeviceNotRegistered":
                    db.query(Device).filter(Device.expo_push_token == res.token).delete()
            if any(r.status == "sent" for r in results):
                sent.append("push")
    if aoi.channel_email:
        msg = alert_email(user.notification_email, language=user.language, aoi_name=aoi.name, level_label=label,
                          night_date=risk.night_date, explanation=expl.payload, probability_pct=pct, cell_name=rec.name,
                          model_version=rec.model_version, data_source=rec.data_source, mode=mode,
                          processed_at=dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", ""))
        try:
            email_sender.send(msg)
            db.add(Delivery(alert_id=alert.id, channel="email", status="sent"))
            summary.delivered("email", "sent")
            sent.append("email")
        except EmailError as exc:
            db.add(Delivery(alert_id=alert.id, channel="email", status="error", error=str(exc)[:300]))
            summary.delivered("email", "error")
        except Exception as exc:  # never let one delivery stop the run
            db.add(Delivery(alert_id=alert.id, channel="email", status="error", error=type(exc).__name__))
            summary.delivered("email", "error")
    alert.channels_sent = sent
    db.commit()
    return alert.id


def _push_text(language: str, label: str, aoi_name: str, night: str, pct: int, mode: str, data_source: str) -> tuple[str, str]:
    prefix = ("[REPLAY] " if mode == "replay" else "") + ("[MOCK] " if data_source == "MOCK" else "")
    if language == "en":
        return (f"{prefix}Frost: {label} risk at {aoi_name}",
                f"Night of {night}: {pct}%. Reanalysis data. Tap for details.")
    return (f"{prefix}Helada: riesgo {label} en {aoi_name}",
            f"Noche del {night}: {pct}%. Datos de reanálisis. Toca para ver más.")
