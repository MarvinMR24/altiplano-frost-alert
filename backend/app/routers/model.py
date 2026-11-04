"""GET /model-card."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import current_user, get_provider_dep, rate_limit
from ..providers import DataProvider, ProviderError
from ..serializers import model_card_out
from .errors import provider_unavailable

router = APIRouter(tags=["model"], dependencies=[Depends(rate_limit), Depends(current_user)])


@router.get("/model-card")
def model_card(provider: DataProvider = Depends(get_provider_dep)) -> dict:
    try:
        return model_card_out(provider.get_model_card())
    except ProviderError as exc:
        raise provider_unavailable(exc) from None
