"""Areas of interest: GET, POST /aois and PATCH, DELETE /aois/{id}."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..deps import current_user, get_db, get_provider_dep, rate_limit
from ..models import Alert, Aoi, Delivery, User
from ..providers import DataProvider, NightNotFound, ProviderError
from ..schemas import AoiCreateIn, AoiOut, AoiPatchIn
from ..serializers import aoi_out
from ..services.coverage import AoiValidationError, validate_aoi_polygon
from ..services.risk import aoi_risk

log = logging.getLogger("frostwatch.aois")
router = APIRouter(prefix="/aois", tags=["aois"], dependencies=[Depends(rate_limit)])
MAX_AOIS_PER_USER = 20


def _current(provider: DataProvider, polygon: dict, radius_km: float) -> dict | None:
    """Risk of the AOI for the latest night, or None when no data is available."""
    try:
        night = provider.latest_night()
        risk = aoi_risk(polygon, provider.get_cells(night), radius_km)
    except (ProviderError, NightNotFound, AoiValidationError) as exc:
        log.info("no current risk for AOI: %s", type(exc).__name__)
        return None
    if risk is None:
        return None
    return {"night_date": risk.night_date, "probability": risk.probability, "level": risk.level,
            "cell_used": risk.cell_used, "distance_km": risk.distance_km}


def _own(db: Session, user: User, aoi_id: str) -> Aoi:
    aoi = db.get(Aoi, aoi_id)
    if aoi is None or aoi.user_id != user.id:
        raise HTTPException(404, "AOI not found")
    return aoi


@router.get("", response_model=list[AoiOut])
def list_aois(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db),
              provider: DataProvider = Depends(get_provider_dep)) -> list[AoiOut]:
    radius = request.app.state.settings.coverage_radius_km
    rows = db.scalars(select(Aoi).where(Aoi.user_id == user.id).order_by(Aoi.created_at)).all()
    return [aoi_out(a, _current(provider, a.polygon, radius)) for a in rows]


@router.post("", response_model=AoiOut, status_code=201)
def create_aoi(body: AoiCreateIn, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db),
               provider: DataProvider = Depends(get_provider_dep)) -> AoiOut:
    radius = request.app.state.settings.coverage_radius_km
    polygon = {"type": "Polygon", "coordinates": [[list(p) for p in body.polygon.coordinates[0]]]}
    try:
        validate_aoi_polygon(polygon, radius)
    except AoiValidationError as exc:
        raise HTTPException(422, str(exc)) from None
    count = len(db.scalars(select(Aoi.id).where(Aoi.user_id == user.id)).all())
    if count >= MAX_AOIS_PER_USER:
        raise HTTPException(409, f"at most {MAX_AOIS_PER_USER} AOIs per user")
    aoi = Aoi(user_id=user.id, name=body.name, polygon=polygon, threshold=body.threshold,
              channel_push=body.channels.push, channel_email=body.channels.email)
    db.add(aoi)
    db.commit()
    return aoi_out(aoi, _current(provider, polygon, radius))


@router.patch("/{aoi_id}", response_model=AoiOut)
def patch_aoi(aoi_id: str, body: AoiPatchIn, request: Request, user: User = Depends(current_user),
              db: Session = Depends(get_db), provider: DataProvider = Depends(get_provider_dep)) -> AoiOut:
    aoi = _own(db, user, aoi_id)
    data = body.model_dump(exclude_unset=True)
    if data.get("name") is not None:
        aoi.name = data["name"]
    if data.get("threshold") is not None:
        aoi.threshold = data["threshold"]
    if data.get("channels") is not None:
        aoi.channel_push = data["channels"]["push"]
        aoi.channel_email = data["channels"]["email"]
    db.commit()
    return aoi_out(aoi, _current(provider, aoi.polygon, request.app.state.settings.coverage_radius_km))


@router.delete("/{aoi_id}", status_code=204)
def delete_aoi(aoi_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
    aoi = _own(db, user, aoi_id)
    alert_ids = select(Alert.id).where(Alert.aoi_id == aoi.id)
    db.execute(delete(Delivery).where(Delivery.alert_id.in_(alert_ids)))
    db.execute(delete(Alert).where(Alert.aoi_id == aoi.id))
    db.delete(aoi)
    db.commit()
    return Response(status_code=204)
