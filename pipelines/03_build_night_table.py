"""Build the night table: one row per (point_id, night D), D = local date of the 18:00 snapshot.

Features use only information at or before 18:00 local (22:00 UTC) of day D. The label is
the minimum hourly t2m from 22:00 UTC of D to 13:00 UTC of D+1 (16 values) at or below 0 C.
Splits by whole years of D: train 1985-2009, validation 2010-2017, test 2018-2025,
out_of_sample_check 2026. Statistics used by features (clearness percentiles, elevation
proxy) are computed on training years only.

Outputs: data/processed/features.parquet, data/processed/crosschecks.parquet,
data/processed/features_manifest.json.

Run: .venv/bin/python pipelines/03_build_night_table.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c

FEATURES_PATH = c.PROCESSED / "features.parquet"
CROSSCHECKS_PATH = c.PROCESSED / "crosschecks.parquet"
MANIFEST_OUT = c.PROCESSED / "features_manifest.json"

DEFINITIONS = {
    "t2m_1800_c": "2 m temperature at 18:00 local (22:00 UTC), C.",
    "d2m_1800_c": "2 m dew point at 18:00 local, C.",
    "dewpoint_depression_1800_c": "t2m minus d2m at 18:00 local, C.",
    "rh_1800_pct": "Relative humidity at 18:00 local from t2m and d2m (Magnus, 17.62 and 243.12 C), %.",
    "wind_1800_ms": "10 m wind speed sqrt(u10^2 + v10^2) at 18:00 local, m s-1.",
    "sp_1800_hpa": "Surface pressure at 18:00 local, hPa.",
    "ssrd_1800_wm2": "Downward shortwave radiation over the hour ending at 18:00 local, W m-2.",
    "strd_1800_wm2": "Downward longwave radiation over the hour ending at 18:00 local, W m-2.",
    "ssrd_afternoon_mean_wm2": "Mean ssrd for hours ending 12:00 to 17:00 local (16:00 to 21:00 UTC), W m-2.",
    "strd_afternoon_mean_wm2": "Mean strd for hours ending 12:00 to 17:00 local, W m-2.",
    "skt_1800_c": "Skin temperature at 18:00 local, C.",
    "stl1_1800_c": "Soil temperature level 1 (0 to 7 cm) at 18:00 local, C.",
    "precip_24h_mm": "Total precipitation over the 24 hours ending at 18:00 local, mm.",
    "prev_night_tmin_c": "Minimum t2m of the previous night (18:00 local of D-1 to 09:00 local of D), C.",
    "prev_night_frost": "1 if prev_night_tmin_c <= 0 C, else 0.",
    "cooling_rate_1500_1800_c_per_h": "(t2m at 18:00 minus t2m at 15:00 local) / 3, C per hour.",
    "doy_sin": "sin(2 pi doy / 365.25), doy of D.",
    "doy_cos": "cos(2 pi doy / 365.25), doy of D.",
    "latitude": "Latitude of the ERA5-Land cell, degrees.",
    "elevation_proxy_m": "Elevation proxy from the cell mean surface pressure over training years, standard atmosphere: 44330.8 * (1 - (p / 1013.25) ^ 0.190263), m.",
    "sky_emissivity_1800": "strd_1800_wm2 / (5.670374419e-8 * t2m_1800_K^4), dimensionless. Higher means a more emissive (cloudier or moister) sky.",
    "sky_emissivity_change_1500_1800": "sky_emissivity at 18:00 minus at 15:00 local.",
    "afternoon_clearness": "ssrd_afternoon_mean_wm2 divided by the 95th percentile of that quantity for the same cell and day-of-year window (+-7 days) over training years, clipped to [0, 1].",
    "cloud_cover_prev_day": "AgERA5 24 h mean cloud cover (00:00 to 00:00 local) of day D-1, fraction 0 to 1. Joined by point_id and date.",
}
FEATURES = list(DEFINITIONS)


def split_of(year, split_cfg):
    for name, (lo, hi) in split_cfg.items():
        if lo <= year <= hi:
            return name
    return None


def build_point(pid, entries, cfg):
    f = cfg["features"]
    conv = c.convert_era5land(c.read_era5land(pid, entries))
    ag = c.read_agera5(pid, entries)
    days = pd.date_range(conv.index.min().normalize(), conv.index.max().normalize(), freq="D")

    def at(col, hour_utc, day_offset=0):
        when = days + pd.Timedelta(days=day_offset, hours=hour_utc)
        return conv[col].reindex(when).to_numpy()

    snap, h15 = f["snapshot_hour_utc"], f["hour_1500_utc"]
    aft = np.vstack([at("ssrd_wm2", h) for h in f["afternoon_hours_utc"]])
    aft_l = np.vstack([at("strd_wm2", h) for h in f["afternoon_hours_utc"]])
    t18, td18 = at("t2m_c", snap), at("d2m_c", snap)
    tk18, tk15 = at("t2m_k", snap), at("t2m_k", h15)
    emis18 = at("strd_wm2", snap) / (c.SIGMA * tk18 ** 4)
    emis15 = at("strd_wm2", h15) / (c.SIGMA * tk15 ** 4)
    tp24 = conv["tp_mm"].rolling(24, min_periods=24).sum()

    df = pd.DataFrame({
        "point_id": pid,
        "night_date": days,
        "t2m_1800_c": t18,
        "d2m_1800_c": td18,
        "dewpoint_depression_1800_c": t18 - td18,
        "rh_1800_pct": c.magnus_rh(t18, td18),
        "wind_1800_ms": at("wind_ms", snap),
        "sp_1800_hpa": at("sp_hpa", snap),
        "ssrd_1800_wm2": at("ssrd_wm2", snap),
        "strd_1800_wm2": at("strd_wm2", snap),
        "ssrd_afternoon_mean_wm2": aft.mean(axis=0),
        "strd_afternoon_mean_wm2": aft_l.mean(axis=0),
        "skt_1800_c": at("skt_c", snap),
        "stl1_1800_c": at("stl1_c", snap),
        "precip_24h_mm": tp24.reindex(days + pd.Timedelta(hours=snap)).to_numpy(),
        "cooling_rate_1500_1800_c_per_h": (t18 - at("t2m_c", h15)) / 3.0,
        "sky_emissivity_1800": emis18,
        "sky_emissivity_change_1500_1800": emis18 - emis15,
    })

    label = c.frost_nights(conv, cfg)
    df["tmin_c"] = label["tmin_c"].reindex(days).to_numpy()
    df["frost"] = label["frost"].reindex(days).to_numpy()
    prev = label.reindex(days - pd.Timedelta(days=1))
    df["prev_night_tmin_c"] = prev["tmin_c"].to_numpy()
    df["prev_night_frost"] = prev["frost"].to_numpy()

    doy = df["night_date"].dt.day_of_year
    df["doy"] = doy
    df["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    df["latitude"] = round(conv.attrs["grid_lat"], 4)
    df["cloud_cover_prev_day"] = ag["cloud_cover_24h"].reindex(days - pd.Timedelta(days=1)).to_numpy()
    df["split"] = [split_of(y, cfg["split"]) for y in df["night_date"].dt.year]

    # Cross-check columns, kept out of the feature table.
    nw = cfg["agera5_night_window"]
    w = c.night_windows(conv["t2m_c"], nw["start_hour_utc"], nw["n_hours"])
    w = w["min"].where(w["count"] == nw["n_hours"])
    xc = pd.DataFrame({
        "point_id": pid,
        "night_date": days,
        "agera5_tmin_night_c": (ag["tmin_night_k"] - 273.15).reindex(days + pd.Timedelta(days=1)).to_numpy(),
        "era5land_min_1800_0600_c": w.reindex(days).to_numpy(),
        "agera5_rh_1500_pct": ag["rh_15h"].reindex(days).to_numpy(),
        "era5land_rh_1500_pct": c.magnus_rh(at("t2m_c", h15), at("d2m_c", h15)),
    })
    return df, xc


def add_train_statistics(df, cfg):
    """Elevation proxy and afternoon clearness, using training years only."""
    f = cfg["features"]
    train = df[df["split"] == "train"]
    mean_sp = train.groupby("point_id")["sp_1800_hpa"].mean()
    df["elevation_proxy_m"] = df["point_id"].map(44330.8 * (1 - (mean_sp / 1013.25) ** 0.190263))

    hw, q = f["clearness_doy_halfwidth"], f["clearness_percentile"] / 100.0
    ref = {}
    for pid, g in train.groupby("point_id"):
        doys, vals = g["doy"].to_numpy(), g["ssrd_afternoon_mean_wm2"].to_numpy()
        for d in range(1, 367):
            dist = np.abs(doys - d)
            dist = np.minimum(dist, 366 - dist)
            ref[(pid, d)] = np.nanquantile(vals[dist <= hw], q)
    p95 = np.array([ref[(p, d)] for p, d in zip(df["point_id"], df["doy"])])
    df["afternoon_clearness"] = np.clip(df["ssrd_afternoon_mean_wm2"] / p95, 0, 1)
    return df


def main():
    cfg = c.load_yaml("configs/frost.yaml")
    entries = c.manifest_entries()
    parts, xcs = [], []
    for pid in c.point_ids():
        df, xc = build_point(pid, entries, cfg)
        parts.append(df)
        xcs.append(xc)
    df = pd.concat(parts, ignore_index=True)
    xc = pd.concat(xcs, ignore_index=True)
    df = add_train_statistics(df, cfg)

    # First night (1985-01-01) has no previous night: drop it for every point.
    first = df["night_date"].min()
    df = df[df["night_date"] > first]
    xc = xc[xc["night_date"] > first]
    last = df["night_date"].max()
    df["use"] = np.where(df["night_date"] == last, "latest_available_night", "labeled")
    if df.loc[df["use"] == "latest_available_night", "frost"].notna().any():
        raise SystemExit("the latest night unexpectedly has a label")
    labeled = df["use"] == "labeled"
    missing = df.loc[labeled, FEATURES + ["frost"]].isna().sum()
    if missing.any():
        raise SystemExit(f"missing values in labeled rows: {missing[missing > 0].to_dict()}")

    df["frost"] = df["frost"].astype("Int8")
    df["prev_night_frost"] = df["prev_night_frost"].astype("Int8")
    cols = ["point_id", "night_date", "split", "use"] + FEATURES + ["frost", "tmin_c"]
    df = df[cols].sort_values(["point_id", "night_date"]).reset_index(drop=True)
    xc = xc.sort_values(["point_id", "night_date"]).reset_index(drop=True)
    df.to_parquet(FEATURES_PATH, index=False)
    xc.to_parquet(CROSSCHECKS_PATH, index=False)

    counts = df.groupby("split").agg(rows=("frost", "size"), labeled=("frost", "count"),
                                     frost_rate=("frost", "mean"))
    c.write_json(MANIFEST_OUT, {
        "features_parquet": "data/processed/features.parquet",
        "features_sha256": c.sha256_of(FEATURES_PATH),
        "crosschecks_sha256": c.sha256_of(CROSSCHECKS_PATH),
        "raw_manifest_sha256": c.sha256_of(c.MANIFEST_PATH),
        "rows": int(len(df)),
        "points": sorted(df["point_id"].unique().tolist()),
        "night_range": [str(df["night_date"].min().date()), str(df["night_date"].max().date())],
        "identifier_columns": ["point_id", "night_date", "split", "use"],
        "label_columns": ["frost", "tmin_c"],
        "feature_columns": FEATURES,
        "definitions": DEFINITIONS,
        "label_definition": "frost = 1 if the minimum hourly ERA5-Land t2m from 22:00 UTC of D to 13:00 UTC of D+1 (18:00 to 09:00 local, 16 values) is <= 0 C. tmin_c is that minimum. Labels come from the same reanalysis as the features.",
        "split_definition": cfg["split"],
        "split_counts": {k: {kk: (float(vv) if kk == "frost_rate" else int(vv)) for kk, vv in v.items()}
                         for k, v in counts.to_dict(orient="index").items()},
        "train_only_statistics": ["elevation_proxy_m (mean surface pressure)", "afternoon_clearness (95th percentile reference)"],
        "latest_available_night": str(last.date()),
        "seed": c.SEED,
    })
    print(counts.to_string())
    print("rows", len(df), "latest night", last.date())


if __name__ == "__main__":
    main()
