"""Masking guard for everything sent to Muse: no dates, years, places, coordinates, elevation or labels.

`assert_masked` is called on every payload right before a call. It checks dictionary keys for
forbidden concepts and string or numeric content for dates, years and place names.
"""

from __future__ import annotations

import json
import re

from .. import config

FORBIDDEN_KEY_PARTS = ("date", "year", "time", "lat", "lon", "elev", "point", "cell", "place", "frost", "label",
                       "tmin", "split")
DATE_RE = re.compile(r"\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{2,4}")
YEAR_RE = re.compile(r"(?<![\d.])(19[5-9]\d|20[0-4]\d)(?![\d.])")


class MaskingError(ValueError):
    """Raised when a payload would reveal time, place or labels."""


def place_names() -> list[str]:
    names = []
    for pid in config.point_ids():
        names += [pid, pid.replace("_", " ")]
    return names


def _keys(obj, out: list[str]) -> list[str]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.append(str(k))
            _keys(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _keys(v, out)
    return out


def assert_masked(payload: dict, allowed_keys: set[str] | None = None) -> None:
    """Raise MaskingError if the payload carries dates, years, place names or forbidden keys."""
    allowed = allowed_keys or set()
    for k in _keys(payload, []):
        low = k.lower()
        if k not in allowed and any(p in low for p in FORBIDDEN_KEY_PARTS):
            raise MaskingError(f"forbidden key {k!r}")
    text = json.dumps(payload, ensure_ascii=False)
    if DATE_RE.search(text):
        raise MaskingError("date-like string in payload")
    m = YEAR_RE.search(text)
    if m:
        raise MaskingError(f"year-like number {m.group(0)} in payload")
    low = text.lower()
    for name in place_names():
        if re.search(r"(?<![a-z])" + re.escape(name.lower()) + r"(?![a-z])", low):
            raise MaskingError(f"place name {name!r} in payload")
