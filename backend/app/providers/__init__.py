"""Data providers selected by DATA_PROVIDER ("mock" or "artifacts")."""

from __future__ import annotations

from ..config import Settings
from .artifacts import ArtifactsProvider
from .base import DataProvider, NightNotFound, ProviderError
from .mock import MockProvider

__all__ = ["DataProvider", "NightNotFound", "ProviderError", "get_provider"]


def get_provider(settings: Settings) -> DataProvider:
    if settings.data_provider == "mock":
        return MockProvider()
    if settings.data_provider == "artifacts":
        return ArtifactsProvider(settings.artifacts_dir)
    raise ValueError(f"DATA_PROVIDER must be 'mock' or 'artifacts', got {settings.data_provider!r}")
