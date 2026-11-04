"""Shared HTTP errors."""

from __future__ import annotations

import datetime as dt
import logging

from fastapi import HTTPException

from ..providers import DataProvider, NightNotFound, ProviderError

log = logging.getLogger("frostwatch.api")


def provider_unavailable(exc: Exception) -> HTTPException:
    log.error("data provider unavailable: %s", exc)
    return HTTPException(503, f"data provider unavailable: {exc}")


def parse_night(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        raise HTTPException(422, "night must be YYYY-MM-DD") from None


def resolve_night(provider: DataProvider, night: str | None) -> dt.date:
    try:
        return parse_night(night) if night else provider.latest_night()
    except ProviderError as exc:
        raise provider_unavailable(exc) from None


def cells_for(provider: DataProvider, night: dt.date):
    try:
        return provider.get_cells(night)
    except NightNotFound:
        raise HTTPException(404, f"no predictions for night {night.isoformat()}") from None
    except ProviderError as exc:
        raise provider_unavailable(exc) from None
