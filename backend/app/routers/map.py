"""GET /map?night=YYYY-MM-DD."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..deps import current_user, get_provider_dep, rate_limit
from ..providers import DataProvider
from ..schemas import MapOut
from ..serializers import cell_out
from .errors import cells_for, resolve_night

router = APIRouter(tags=["map"], dependencies=[Depends(rate_limit), Depends(current_user)])


@router.get("/map", response_model=MapOut)
def get_map(night: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
            provider: DataProvider = Depends(get_provider_dep)) -> MapOut:
    d = resolve_night(provider, night)
    cells = cells_for(provider, d)
    return MapOut(night_date=d.isoformat(), data_source=cells[0].data_source, model_version=cells[0].model_version,
                  cells=[cell_out(c) for c in cells])
