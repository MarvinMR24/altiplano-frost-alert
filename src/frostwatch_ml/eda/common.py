"""Names used by the EDA modules, re-exported from the package (keeps the Part 1 EDA code unchanged)."""

from __future__ import annotations

from pathlib import Path

from .. import config
from ..dataio.cds_reader import AGERA5_NAMES, ERA5_VARS, read_agera5, read_era5land  # noqa: F401
from ..dataio.manifest import manifest_entries  # noqa: F401
from ..dataio.tables import sha256_of  # noqa: F401
from ..dataio.tables import write_json as _write_json
from ..evaluation.reports import md_table  # noqa: F401
from ..features.labels import frost_nights, night_windows  # noqa: F401
from ..prep.physics import SIGMA, haversine_km, magnus_rh  # noqa: F401
from ..prep.units import convert_era5land  # noqa: F401

ROOT = config.ROOT
PROCESSED = config.PROCESSED
FIGURES = config.FIGURES
MANIFEST_PATH = config.RAW_MANIFEST
SEED = config.SEED
point_ids = config.point_ids


def load_yaml(path):
    return config.load_yaml(path)


def write_json(path, obj):
    _write_json(obj, Path(path))
