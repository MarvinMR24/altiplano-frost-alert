"""GET /coverage and GET /nights."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..deps import current_user, get_provider_dep, rate_limit
from ..providers import DataProvider, ProviderError
from ..schemas import NightsOut
from ..services.coverage import coverage_geojson
from .errors import provider_unavailable

router = APIRouter(tags=["geo"], dependencies=[Depends(rate_limit), Depends(current_user)])


@router.get("/coverage")
def coverage(request: Request) -> dict:
    return coverage_geojson(request.app.state.settings.coverage_radius_km)


@router.get("/nights", response_model=NightsOut)
def nights(provider: DataProvider = Depends(get_provider_dep)) -> NightsOut:
    try:
        available = provider.list_nights()
    except ProviderError as exc:
        raise provider_unavailable(exc) from None
    if not available:
        raise provider_unavailable(ProviderError("no nights available"))
    return NightsOut(latest=available[-1].isoformat(), available=[n.isoformat() for n in available])
