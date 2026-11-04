"""Night table builder: one row per (point_id, night D), D = local date of the 18:00 snapshot.

Features use only data at or before 22:00 UTC of D (see snapshot.py, cloud.py); the label uses
the window 22:00 UTC of D to 13:00 UTC of D+1. Fitted statistics come from training years only.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .. import config, splits
from ..dataio.cds_reader import read_agera5, read_era5land
from ..dataio.manifest import manifest_entries
from ..prep.physics import magnus_rh
from ..prep.units import convert_era5land
from . import fitted
from .cloud import cloud_prev_day
from .labels import frost_nights, night_windows
from .snapshot import calendar, previous_night, snapshot_features


def feature_columns() -> list[str]:
    return list(config.features_config()["allowlist"])


def definitions() -> dict[str, str]:
    return dict(config.features_config()["definitions"])


def build_point_frame(pid: str, conv: pd.DataFrame, agera5: pd.DataFrame, cfg: dict,
                      days: pd.DatetimeIndex | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Unfitted features, label and split for one cell, plus its cross-check columns.
    `days` defaults to every date covered by the hourly series."""
    if days is None:
        days = pd.date_range(conv.index.min().normalize(), conv.index.max().normalize(), freq="D")
    df = snapshot_features(conv, days, cfg)
    df.insert(0, "point_id", pid)
    label = frost_nights(conv, cfg)
    df["tmin_c"] = label["tmin_c"].reindex(days).to_numpy()
    df["frost"] = label["frost"].reindex(days).to_numpy()
    prev = previous_night(conv, days, cfg)
    df["prev_night_tmin_c"] = prev["prev_night_tmin_c"].to_numpy()
    df["prev_night_frost"] = prev["prev_night_frost"].to_numpy()
    cal = calendar(days)
    for col in cal.columns:
        df[col] = cal[col].to_numpy()
    df["latitude"] = round(conv.attrs["grid_lat"], 4)
    df["cloud_cover_prev_day"] = cloud_prev_day(agera5, days).to_numpy()
    df["split"] = splits.assign(df["night_date"], cfg["split"])

    f = cfg["features"]
    nw = cfg["agera5_night_window"]
    w = night_windows(conv["t2m_c"], nw["start_hour_utc"], nw["n_hours"])
    w = w["min"].where(w["count"] == nw["n_hours"])
    h15 = days + pd.Timedelta(hours=f["hour_1500_utc"])
    xc = pd.DataFrame({
        "point_id": pid,
        "night_date": days,
        "agera5_tmin_night_c": (agera5["tmin_night_k"] - 273.15).reindex(days + pd.Timedelta(days=1)).to_numpy(),
        "era5land_min_1800_0600_c": w.reindex(days).to_numpy(),
        "agera5_rh_1500_pct": agera5["rh_15h"].reindex(days).to_numpy(),
        "era5land_rh_1500_pct": magnus_rh(conv["t2m_c"].reindex(h15).to_numpy(), conv["d2m_c"].reindex(h15).to_numpy()),
    })
    return df, xc


def finalize(df: pd.DataFrame, xc: pd.DataFrame, stats: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply fitted statistics, drop the first night, mark the latest night, fix dtypes and column order."""
    feats = feature_columns()
    df = fitted.apply(df, stats)
    first = df["night_date"].min()
    df = df[df["night_date"] > first]
    xc = xc[xc["night_date"] > first]
    last = df["night_date"].max()
    df["use"] = np.where(df["night_date"] == last, "latest_available_night", "labeled")
    if df.loc[df["use"] == "latest_available_night", "frost"].notna().any():
        raise ValueError("the latest night unexpectedly has a label")
    labeled = df["use"] == "labeled"
    missing = df.loc[labeled, feats + ["frost"]].isna().sum()
    if missing.any():
        raise ValueError(f"missing values in labeled rows: {missing[missing > 0].to_dict()}")
    df["frost"] = df["frost"].astype("Int8")
    df["prev_night_frost"] = df["prev_night_frost"].astype("Int8")
    cols = ["point_id", "night_date", "split", "use"] + feats + ["frost", "tmin_c"]
    df = df[cols].sort_values(["point_id", "night_date"]).reset_index(drop=True)
    xc = xc.sort_values(["point_id", "night_date"]).reset_index(drop=True)
    return df, xc


def build_night_table(cfg: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Full night table for every cell: (features, crosschecks, fitted statistics)."""
    cfg = cfg or config.frost_config()
    entries = manifest_entries()
    parts, xcs = [], []
    for pid in config.point_ids():
        conv = convert_era5land(read_era5land(pid, entries))
        df, xc = build_point_frame(pid, conv, read_agera5(pid, entries), cfg)
        parts.append(df)
        xcs.append(xc)
    df = pd.concat(parts, ignore_index=True)
    xc = pd.concat(xcs, ignore_index=True)
    stats = fitted.fit(df, cfg)
    df, xc = finalize(df, xc, stats)
    splits.assert_integrity(df, cfg["split"])
    return df, xc, stats


def write_outputs(df: pd.DataFrame, xc: pd.DataFrame, stats: dict[str, Any], cfg: dict | None = None) -> dict:
    """Write features.parquet, crosschecks.parquet, fitted_stats.json and features_manifest.json (atomic)."""
    from ..dataio.tables import sha256_of, write_json, write_parquet

    cfg = cfg or config.frost_config()
    features_path = config.PROCESSED / "features.parquet"
    xc_path = config.PROCESSED / "crosschecks.parquet"
    write_parquet(df, features_path)
    write_parquet(xc, xc_path)
    write_json(stats, config.PROCESSED / "fitted_stats.json")
    counts = df.groupby("split").agg(rows=("frost", "size"), labeled=("frost", "count"), frost_rate=("frost", "mean"))
    manifest = {
        "features_parquet": "data/processed/features.parquet",
        "features_sha256": sha256_of(features_path),
        "crosschecks_sha256": sha256_of(xc_path),
        "raw_manifest_sha256": sha256_of(config.RAW_MANIFEST),
        "rows": int(len(df)),
        "points": sorted(df["point_id"].unique().tolist()),
        "night_range": [str(df["night_date"].min().date()), str(df["night_date"].max().date())],
        "identifier_columns": ["point_id", "night_date", "split", "use"],
        "label_columns": ["frost", "tmin_c"],
        "feature_columns": feature_columns(),
        "feature_allowlist_source": "configs/features.yaml",
        "definitions": definitions(),
        "label_definition": "frost = 1 if the minimum hourly ERA5-Land t2m from 22:00 UTC of D to 13:00 UTC of D+1 (18:00 to 09:00 local, 16 values) is <= 0 C. tmin_c is that minimum. Labels come from the same reanalysis as the features.",
        "split_definition": cfg["split"],
        "split_counts": {k: {kk: (float(vv) if kk == "frost_rate" else int(vv)) for kk, vv in v.items()}
                         for k, v in counts.to_dict(orient="index").items()},
        "train_only_statistics": ["elevation_proxy_m (mean surface pressure)", "afternoon_clearness (95th percentile reference)"],
        "fitted_stats": "data/processed/fitted_stats.json",
        "latest_available_night": str(df["night_date"].max().date()),
        "seed": config.SEED,
    }
    write_json(manifest, config.PROCESSED / "features_manifest.json")
    return manifest
