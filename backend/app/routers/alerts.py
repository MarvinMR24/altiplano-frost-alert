"""GET /alerts, GET /alerts/{id} and POST /alerts/{id}/read."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import current_user, get_db, get_provider_dep, rate_limit
from ..models import Alert, Explanation, User
from ..providers import DataProvider, NightNotFound, ProviderError
from ..schemas import AlertDetail, AlertSummary
from ..serializers import alert_summary, model_card_summary
from ..services.drivers import group_drivers

router = APIRouter(prefix="/alerts", tags=["alerts"], dependencies=[Depends(rate_limit)])


def _own(db: Session, user: User, alert_id: str) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None or alert.user_id != user.id:
        raise HTTPException(404, "alert not found")
    return alert


@router.get("", response_model=list[AlertSummary])
def list_alerts(user: User = Depends(current_user), db: Session = Depends(get_db)) -> list[AlertSummary]:
    rows = db.scalars(select(Alert).where(Alert.user_id == user.id)
                      .order_by(Alert.sent_at.desc(), Alert.night_date.desc())).all()
    return [alert_summary(a) for a in rows]


@router.get("/{alert_id}", response_model=AlertDetail)
def get_alert(alert_id: str, user: User = Depends(current_user), db: Session = Depends(get_db),
              provider: DataProvider = Depends(get_provider_dep)) -> AlertDetail:
    alert = _own(db, user, alert_id)
    expl = db.get(Explanation, alert.explanation_id) if alert.explanation_id else None
    explanation = expl.payload if expl else {"headline": alert.headline, "why": "", "actions": [], "caveats": []}
    try:
        cells = provider.get_cells(dt.date.fromisoformat(alert.night_date))
        rec = next(c for c in cells if c.point_id == alert.cell_used)
        card_summary = model_card_summary(provider.get_model_card())
    except (ProviderError, NightNotFound, StopIteration):
        raise HTTPException(503, "the predictions for this alert are no longer available") from None
    return AlertDetail(**alert_summary(alert).model_dump(), explanation=explanation, conditions_1800=rec.conditions_1800,
                       top_drivers=rec.top_drivers, driver_groups=group_drivers(rec.top_drivers),
                       historical_reliability=rec.historical_reliability, outcome=rec.observed,
                       model_card_summary=card_summary, data_source=alert.data_source, mode=alert.mode)


@router.post("/{alert_id}/read", status_code=204)
def mark_read(alert_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    alert = _own(db, user, alert_id)
    alert.read = True
    db.commit()
    return Response(status_code=204)
