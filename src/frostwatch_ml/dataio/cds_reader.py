"""Read the CDS downloads listed in the manifest.

ERA5-Land downloads are zip archives with several NetCDF parts. They are always extracted
from the zip into data/processed/scratch/unzipped/<name>_<sha16>/; the *_unzipped/ folders
next to the raw files are never read and need not be versioned.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pandas as pd
import xarray as xr

from .. import config
from .manifest import manifest_entries
from .tables import sha256_of

ERA5_VARS = ["t2m", "d2m", "sp", "tp", "ssrd", "strd", "skt", "stl1", "u10", "v10"]
AGERA5_NAMES = {
    "Cloud_Cover_Mean_24h": "cloud_cover_24h",
    "Temperature_Air_2m_Min_Night_Time": "tmin_night_k",
    "Relative_Humidity_2m_15h": "rh_15h",
}


def extract_zip(zip_path: Path) -> list[Path]:
    """Extract a zipped download into the scratch folder once per archive hash."""
    digest = sha256_of(zip_path)[:16]
    target = config.SCRATCH / f"{zip_path.stem}_{digest}"
    done = target / ".complete"
    if not done.exists():
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(target)
        done.write_text(digest)
    return sorted(target.rglob("*.nc"))


def _open(path: Path):
    parts = extract_zip(path) if zipfile.is_zipfile(path) else [path]
    dsets = [xr.open_dataset(p) for p in parts]
    ds = xr.merge(dsets, compat="override", join="outer") if len(dsets) > 1 else dsets[0]
    return ds, dsets


def read_era5land(point_id: str, entries: dict | None = None) -> pd.DataFrame:
    """Hourly ERA5-Land series for one point (main file plus 2026 file), raw units, UTC index.
    Accumulated variables (tp, ssrd, strd) cover the hour ending at the timestamp."""
    entries = entries or manifest_entries()
    frames = []
    for use in ("train_val_test", "out_of_sample_check"):
        rec = entries[("era5land_ts", point_id, use)]
        ds, dsets = _open(Path(rec["path"]))
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


def read_agera5(point_id: str, entries: dict | None = None) -> pd.DataFrame:
    """Daily AgERA5 series for one point, raw units, indexed by local date. The night minimum of
    date D covers 18:00 local of D-1 to 06:00 local of D; the cloud cover of D covers local day D."""
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
