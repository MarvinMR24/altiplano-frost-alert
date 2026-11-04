"""GET /map?night=YYYY-MM-DD and GET /map/{point_id}/explain (plain explanation by Muse)."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ..deps import current_user, get_db, get_provider_dep, rate_limit
from ..models import User
from ..providers import DataProvider, NightNotFound, ProviderError
from ..schemas import Language, MapOut, PlaceExplanationOut, SourceOut
from ..serializers import cell_out
from ..services.place_explain import PlaceExplainer
from .errors import cells_for, provider_unavailable, resolve_night

router = APIRouter(tags=["map"], dependencies=[Depends(rate_limit), Depends(current_user)])


@router.get("/map", response_model=MapOut)
def get_map(night: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
            provider: DataProvider = Depends(get_provider_dep)) -> MapOut:
    d = resolve_night(provider, night)
    cells = cells_for(provider, d)
    return MapOut(night_date=d.isoformat(), data_source=cells[0].data_source, model_version=cells[0].model_version,
                  cells=[cell_out(c) for c in cells])


def _cell_or_none(provider: DataProvider, night: dt.date, point_id: str):
    try:
        return next((c for c in provider.get_cells(night) if c.point_id == point_id), None)
    except NightNotFound:
        return None
    except ProviderError as exc:
        raise provider_unavailable(exc) from None


@router.get("/map/{point_id}/explain", response_model=PlaceExplanationOut)
def explain_place(point_id: str, request: Request,
                  night: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
                  lang: Language | None = Query(default=None),
                  provider: DataProvider = Depends(get_provider_dep), db: Session = Depends(get_db),
                  user: User = Depends(current_user)) -> PlaceExplanationOut:
    d = resolve_night(provider, night)
    rec = next((c for c in cells_for(provider, d) if c.point_id == point_id), None)
    if rec is None:
        raise HTTPException(404, f"unknown point {point_id}")
    previous = _cell_or_none(provider, d - dt.timedelta(days=1), point_id)
    following = _cell_or_none(provider, d + dt.timedelta(days=1), point_id)
    explainer = PlaceExplainer(request.app.state.settings)
    result = explainer.explain_place(db, rec, previous, following, user.profile or "producer",
                                     lang or user.language or "es", request.app.state.limiter, user.id)
    p = result.payload
    return PlaceExplanationOut(point_id=point_id, night_date=d.isoformat(), language=result.language,
                               source=result.source, headline=p["headline"], what_happened=p["what_happened"],
                               what_next=p["what_next"], actions=p["actions"],
                               sources=[SourceOut(**s) for s in p["sources"]])
