import logging

from app.schemas import Driver
from app.services.drivers import group_drivers, theme_of

MODEL_FEATURES = ["t2m_1800_c", "d2m_1800_c", "dewpoint_depression_1800_c", "rh_1800_pct", "wind_1800_ms", "sp_1800_hpa",
                  "ssrd_1800_wm2", "strd_1800_wm2", "ssrd_afternoon_mean_wm2", "strd_afternoon_mean_wm2", "skt_1800_c",
                  "stl1_1800_c", "precip_24h_mm", "prev_night_tmin_c", "prev_night_frost",
                  "cooling_rate_1500_1800_c_per_h", "doy_sin", "doy_cos", "latitude", "elevation_proxy_m",
                  "sky_emissivity_1800", "sky_emissivity_change_1500_1800", "afternoon_clearness", "cloud_cover_prev_day"]


def test_theme_mapping_of_model_features():
    themes = {f: theme_of(f) for f in MODEL_FEATURES}
    assert themes["strd_1800_wm2"] == themes["sky_emissivity_1800"] == themes["cloud_cover_prev_day"] == "sky_radiation"
    assert themes["afternoon_clearness"] == "sky_radiation"
    assert themes["dewpoint_depression_1800_c"] == themes["rh_1800_pct"] == themes["d2m_1800_c"] == "humidity"
    assert themes["t2m_1800_c"] == themes["prev_night_tmin_c"] == themes["cooling_rate_1500_1800_c_per_h"] == "temperature"
    assert themes["skt_1800_c"] == themes["stl1_1800_c"] == "temperature"
    assert themes["wind_1800_ms"] == themes["sp_1800_hpa"] == "wind_pressure"
    assert themes["doy_sin"] == themes["doy_cos"] == "season"
    assert {f for f, t in themes.items() if t == "other"} == {"latitude", "elevation_proxy_m"}


def test_collinear_drivers_are_summed():
    groups = group_drivers([Driver(feature="strd_1800_wm2", effect="down", weight=5.5),
                            Driver(feature="sky_emissivity_1800", effect="up", weight=5.3),
                            Driver(feature="rh_1800_pct", effect="down", weight=2.0),
                            Driver(feature="doy_cos", effect="up", weight=1.9)])
    by = {g.theme: g for g in groups}
    assert by["sky_radiation"].effect == "down" and abs(by["sky_radiation"].weight - 0.2) < 1e-9
    assert by["humidity"].weight == 2.0 and by["humidity"].effect == "down"
    assert [g.theme for g in groups] == ["humidity", "season", "sky_radiation"]
    assert by["season"].label_es and by["season"].label_en


def test_unmapped_feature_is_logged(caplog):
    with caplog.at_level(logging.WARNING, logger="frostwatch.drivers"):
        groups = group_drivers([Driver(feature="mystery_x", effect="up", weight=1.0)])
    assert groups[0].theme == "other" and "mystery_x" in caplog.text
