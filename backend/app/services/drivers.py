"""Group per-feature drivers into themes.

Single-feature drivers are fragile because some features are collinear (for example downward
longwave radiation and sky emissivity get large weights of opposite sign). Signed
contributions are summed per theme, matched by regex over the feature name, first match wins.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

from ..schemas import Driver, DriverGroup

log = logging.getLogger("frostwatch.drivers")

# (theme, regex, label_es, label_en). Order matters: e.g. "dewpoint_depression" is humidity.
THEMES: list[tuple[str, re.Pattern, str, str]] = [
    ("sky_radiation", re.compile(r"strd|ssrd|emissiv|clear|cloud|tcc|lw_down"), "Cielo y radiación", "Sky and radiation"),
    ("humidity", re.compile(r"(^|_)rh(_|$)|dewpoint|d2m|depression|precip"), "Humedad", "Humidity"),
    ("temperature", re.compile(r"t2m|cool|tmin|skt|stl|temp|frost"), "Temperatura", "Temperature"),
    ("wind_pressure", re.compile(r"wind|(^|_)sp(_|$)|pressure"), "Viento y presión", "Wind and pressure"),
    ("season", re.compile(r"(^|_)doy|(^|_)sin(_|$)|(^|_)cos(_|$)"), "Época del año", "Time of year"),
]
OTHER = ("other", "Otros factores", "Other factors")


def theme_of(feature: str) -> str:
    for theme, pattern, _, _ in THEMES:
        if pattern.search(feature):
            return theme
    return OTHER[0]


def group_drivers(drivers: Iterable[Driver]) -> list[DriverGroup]:
    """Sum the signed contributions (up = +weight, down = -weight) per theme, largest first."""
    totals: dict[str, float] = {}
    for d in drivers:
        theme = theme_of(d.feature)
        if theme == OTHER[0]:
            log.warning("driver feature not mapped to a theme: %s", d.feature)
        signed = abs(d.weight) if d.effect == "up" else -abs(d.weight)
        totals[theme] = totals.get(theme, 0.0) + signed
    labels = {t: (es, en) for t, _, es, en in THEMES}
    labels[OTHER[0]] = OTHER[1:]
    groups = [DriverGroup(theme=t, label_es=labels[t][0], label_en=labels[t][1],
                          effect="up" if v >= 0 else "down", weight=round(abs(v), 3))
              for t, v in totals.items() if round(abs(v), 3) > 0]
    return sorted(groups, key=lambda g: g.weight, reverse=True)
