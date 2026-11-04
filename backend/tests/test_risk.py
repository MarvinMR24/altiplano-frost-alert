import datetime as dt

import pytest

from app.providers.base import CellRecord, level_for
from app.schemas import Reliability
from app.services.risk import aoi_risk, threshold_reached
from tests.conftest import square


def rec(pid, p, name="x", lat=0.0, lon=0.0):
    return CellRecord(point_id=pid, name=name, lat=lat, lon=lon, elevation_m=0, night_date=dt.date(2018, 7, 15),
                      probability=p, level=level_for(p), top_drivers=[], conditions_1800={},
                      historical_reliability=Reliability(range=(0, 0.1), observed_rate=0, n=0),
                      model_version="m", data_source="FIXTURE")


@pytest.mark.parametrize("p,level", [(0.0, "low"), (0.2999, "low"), (0.3, "moderate"), (0.4999, "moderate"),
                                     (0.5, "high"), (0.6999, "high"), (0.7, "very_high"), (1.0, "very_high")])
def test_levels(p, level):
    assert level_for(p) == level


def test_thresholds():
    assert threshold_reached(0.3, 30) and not threshold_reached(0.2999, 30)
    assert threshold_reached(0.7, 70) and not threshold_reached(0.69, 70)
    with pytest.raises(ValueError):
        threshold_reached(0.5, 40)


def test_overlap_picks_highest_probability():
    # Midway between Patacamaya (-17.2, -67.9) and Calamarca (-17.0, -68.1): inside both circles.
    poly = square(-68.0, -17.1)
    r = aoi_risk(poly, [rec("patacamaya", 0.41), rec("calamarca", 0.33), rec("el_alto", 0.99)], 30)
    assert r.cell_used == "patacamaya" and r.probability == 0.41 and 10 < r.distance_km < 20
    r = aoi_risk(poly, [rec("patacamaya", 0.2), rec("calamarca", 0.6), rec("el_alto", 0.99)], 30)
    assert r.cell_used == "calamarca" and r.level == "high"


def test_single_cell_and_distance():
    r = aoi_risk(square(-67.1, -18.0), [rec("oruro", 0.55), rec("huanuni", 0.9)], 30)
    assert r.cell_used == "oruro" and r.distance_km < 1
