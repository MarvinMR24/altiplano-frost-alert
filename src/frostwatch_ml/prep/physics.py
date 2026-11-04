"""Physical formulas. Pure functions of their arguments."""

from __future__ import annotations

import numpy as np

SIGMA = 5.670374419e-8  # Stefan-Boltzmann constant, W m-2 K-4


def magnus_rh(t_c, td_c):
    """Relative humidity (%) from temperature and dew point (C), Magnus form with coefficients
    17.62 and 243.12 C (WMO guide, over water)."""
    def es(x):
        return 6.112 * np.exp(17.62 * x / (243.12 + x))
    return 100.0 * es(td_c) / es(t_c)


def sky_emissivity(strd_wm2, t_k):
    """Apparent sky emissivity: downward longwave / (sigma * T^4)."""
    return strd_wm2 / (SIGMA * t_k ** 4)


def elevation_proxy_m(p_hpa):
    """Standard-atmosphere height for a pressure: 44330.8 * (1 - (p / 1013.25) ^ 0.190263), m."""
    return 44330.8 * (1 - (p_hpa / 1013.25) ** 0.190263)


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))
