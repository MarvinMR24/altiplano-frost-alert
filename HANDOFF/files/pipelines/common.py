"""Shared helpers for the EDA and night-table pipelines.

Raw inputs are read only from the files listed in data/raw/cds/manifest.json. ERA5-Land
downloads are zip archives with several NetCDF parts; they are always extracted from the
zip into a scratch folder under data/processed/scratch/, so the pipeline never depends on
the *_unzipped/ folders next to the raw files (those are not versioned).
"""

import hashlib
import json
import shutil
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "data" / "raw" / "cds" / "manifest.json"
PROCESSED = ROOT / "data" / "processed"
SCRATCH = PROCESSED / "scratch" / "unzipped"
FIGURES = ROOT / "docs" / "figures"

SEED = 42
LOCAL_UTC_OFFSET_H = -4  # Bolivia, no daylight saving
SIGMA = 5.670374419e-8  # Stefan-Boltzmann constant, W m-2 K-4

ERA5_VARS = ["t2m", "d2m", "sp", "tp", "ssrd", "strd", "skt", "stl1", "u10", "v10"]
AGERA5_NAMES = {
    "Cloud_Cover_Mean_24h": "cloud_cover_24h",
    "Temperature_Air_2m_Min_Night_Time": "tmin_night_k",
    "Relative_Humidity_2m_15h": "rh_15h",
}


def load_yaml(path):
    return yaml.safe_load((ROOT / path).read_text())


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_entries():
    """Complete, non-test entries of the download manifest, keyed by (dataset, point, use)."""
    files = json.loads(MANIFEST_PATH.read_text())["files"]
    out = {}
    for key, rec in files.items():
        if rec.get("status") != "complete" or rec.get("use", "").startswith("test"):
            continue
        out[(rec["dataset_name"], rec["point_id"], rec["use"])] = dict(rec, path=ROOT / key)
    return out


def point_ids():
    return [p["id"] for p in load_yaml("configs/points.yaml")["points"]]


def _extract(zip_path):
    """Extract a zipped download into the scratch folder (once per archive hash)."""
    digest = sha256_of(zip_path)[:16]
    target = SCRATCH / f"{zip_path.stem}_{digest}"
    done = target / ".complete"
    if not done.exists():
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(target)
        done.write_text(digest)
    return sorted(target.rglob("*.nc"))


def _open_netcdf(path):
    path = Path(path)
    parts = _extract(path) if zipfile.is_zipfile(path) else [path]
    dsets = [xr.open_dataset(p) for p in parts]
    ds = xr.merge(dsets, compat="override", join="outer") if len(dsets) > 1 else dsets[0]
    return ds, dsets


def read_era5land(point_id, entries=None):
    """Hourly ERA5-Land series for one point (main file plus 2026 file), raw units, UTC index."""
    entries = entries or manifest_entries()
    frames = []
    for use in ("train_val_test", "out_of_sample_check"):
        rec = entries[("era5land_ts", point_id, use)]
        ds, dsets = _open_netcdf(rec["path"])
        try:
            df = ds[ERA5_VARS].squeeze(drop=True).to_dataframe()[ERA5_VARS]
        finally:
            for d in dsets:
                d.close()
        df.index = pd.DatetimeIndex(df.index, name="timestamp_utc")
        df["source_file"] = use
        frames.append(df)
    df = pd.concat(frames).sort_index()
    df.attrs["grid_lat"] = entries[("era5land_ts", point_id, "train_val_test")]["grid_lat"]
    df.attrs["grid_lon"] = entries[("era5land_ts", point_id, "train_val_test")]["grid_lon"]
    return df


def convert_era5land(raw):
    """Unit conversions: K to C, Pa to hPa, J m-2 per hour to W m-2, m to mm, wind speed."""
    out = pd.DataFrame(index=raw.index)
    for v in ("t2m", "d2m", "skt", "stl1"):
        out[f"{v}_c"] = raw[v] - 273.15
    out["t2m_k"] = raw["t2m"]
    out["sp_hpa"] = raw["sp"] / 100.0
    out["ssrd_wm2"] = raw["ssrd"] / 3600.0
    out["strd_wm2"] = raw["strd"] / 3600.0
    out["tp_mm"] = raw["tp"] * 1000.0
    out["u10"] = raw["u10"]
    out["v10"] = raw["v10"]
    out["wind_ms"] = np.hypot(raw["u10"], raw["v10"])
    out.attrs.update(raw.attrs)
    return out


def read_agera5(point_id, entries=None):
    """Daily AgERA5 series for one point, raw units, indexed by local date."""
    entries = entries or manifest_entries()
    rec = next(r for (d, p, _), r in entries.items() if d == "agera5_ts" and p == point_id)
    ds = xr.open_dataset(rec["path"])
    try:
        df = ds[list(AGERA5_NAMES)].to_dataframe()[list(AGERA5_NAMES)].rename(columns=AGERA5_NAMES)
    finally:
        ds.close()
    df.index = pd.DatetimeIndex(df.index, name="date").normalize()
    df.attrs["grid_lat"] = rec["grid_lat"]
    df.attrs["grid_lon"] = rec["grid_lon"]
    return df


def magnus_rh(t_c, td_c):
    """Relative humidity (%) from temperature and dew point (C), Magnus form with
    coefficients 17.62 and 243.12 C (WMO guide over water)."""
    def es(x):
        return 6.112 * np.exp(17.62 * x / (243.12 + x))
    return 100.0 * es(td_c) / es(t_c)


def night_windows(series, start_hour_utc, n_hours):
    """Group an hourly UTC series into windows that start at start_hour_utc on day D and
    span n_hours. Returns min and count per D (D = the UTC date of the window start)."""
    shifted = series.index - pd.Timedelta(hours=start_hour_utc)
    in_window = shifted.hour < n_hours
    d = pd.DatetimeIndex(shifted[in_window]).normalize()
    g = pd.Series(series.values[in_window], index=d).groupby(level=0)
    return pd.DataFrame({"min": g.min(), "count": g.count()})


def frost_nights(conv, cfg):
    """Label per night D: minimum hourly t2m from 22:00 UTC of D to 13:00 UTC of D+1."""
    lw = cfg["label_window"]
    w = night_windows(conv["t2m_c"], lw["start_hour_utc"], lw["n_hours"])
    complete = w["count"] == lw["n_hours"]
    out = pd.DataFrame(index=w.index)
    out.index.name = "night_date"
    out["tmin_c"] = w["min"].where(complete)
    out["frost"] = (out["tmin_c"] <= cfg["frost_threshold_c"]).astype("Int64").where(complete)
    return out


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = p2 - p1, np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def md_table(df, floatfmt=3):
    """Small markdown table without extra dependencies."""
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join([df.index.name or ""] + cols) + " |",
             "|" + "---|" * (len(cols) + 1)]
    for row in df.itertuples(name=None):
        idx, vals = row[0], []
        for v in row[1:]:
            if isinstance(v, (float, np.floating)):
                vals.append("" if np.isnan(v) else f"{v:.{floatfmt}f}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join([str(idx)] + vals) + " |")
    return "\n".join(lines)


def write_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=2, default=str))
