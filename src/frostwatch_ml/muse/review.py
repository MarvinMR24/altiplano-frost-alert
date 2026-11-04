"""B1: anomaly review. Select flagged hours that can change a feature, clip known ERA5
de-accumulation artifacts in code, build masked records for Muse, and accept a correction only if
it passes physical checks in code.

Feature window: night D reads hourly values at or before 22:00 UTC (18:00 local) of D. A flagged
hour h is first used by the night whose snapshot is the first 22:00 UTC at or after h; that
snapshot is the cutoff: no value after it is sent or used to judge a correction.
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pandas as pd

from .. import splits

SHORT = {"t2m_c": "t2m", "d2m_c": "d2m", "skt_c": "skt"}
REVIEWABLE = tuple(SHORT)
CLIPPED_RULES = {"tp_mm": "precipitation_negative", "ssrd_wm2": "ssrd_negative"}


def feature_hours(field: str, frost_cfg: dict) -> set[int]:
    """UTC hours of day at which the night-table features read `field` (see features/snapshot.py)."""
    f, lw = frost_cfg["features"], frost_cfg["label_window"]
    snap, h15 = f["snapshot_hour_utc"], f["hour_1500_utc"]
    prev_night = {(lw["start_hour_utc"] + i) % 24 for i in range(lw["n_hours"])}
    hours = {
        "t2m_c": {snap, h15} | prev_night,
        "t2m_k": {snap, h15},
        "ssrd_wm2": set(f["afternoon_hours_utc"]) | {snap},
        "strd_wm2": set(f["afternoon_hours_utc"]) | {snap, h15},
        "tp_mm": set(range(24)),
    }
    return hours.get(field, {snap})


def cutoff(ts: pd.Timestamp, snap_hour: int) -> pd.Timestamp:
    """First snapshot time (snap_hour UTC) at or after ts."""
    day = ts.normalize() + pd.Timedelta(hours=snap_hour)
    return day if ts <= day else day + pd.Timedelta(days=1)


def clip_tiny_negatives(conv: pd.DataFrame, clip_cfg: dict) -> tuple[pd.DataFrame, dict[str, int]]:
    """Set small negative accumulations (|x| <= tolerance) to 0. Larger negatives are left as they are."""
    out = conv.copy()
    counts = {}
    for col, tol in clip_cfg.items():
        m = (out[col] < 0) & (out[col] >= -tol)
        counts[col] = int(m.sum())
        out.loc[m, col] = 0.0
    return out, counts


def in_scope(anoms: pd.DataFrame, frost_cfg: dict, sample_splits: list[str]) -> pd.DataFrame:
    """Flagged hours that can change a feature of a night in `sample_splits`, excluding the clipped
    de-accumulation rules and fields that are not reviewable."""
    snap = frost_cfg["features"]["snapshot_hour_utc"]
    a = anoms.copy()
    hour = a["timestamp_utc"].dt.hour
    a["affects_feature"] = [h in feature_hours(f, frost_cfg) for f, h in zip(a["field"], hour, strict=True)]
    a["clipped_in_code"] = [CLIPPED_RULES.get(f) == r for f, r in zip(a["field"], a["rule"], strict=True)]
    a["cutoff_utc"] = [cutoff(t, snap) for t in a["timestamp_utc"]]
    a["night_split"] = [splits.split_of(c.year, frost_cfg["split"]) for c in a["cutoff_utc"]]
    keep = a["affects_feature"] & ~a["clipped_in_code"] & a["field"].isin(REVIEWABLE) & a["night_split"].isin(sample_splits)
    return a[keep].reset_index(drop=True)


def stratified_sample(df: pd.DataFrame, cap: int, seed: int) -> pd.DataFrame:
    """At most `cap` rows, balanced over (field, rule) strata: each stratum gets an equal share,
    unused share goes to the larger strata. Shuffled with the seed."""
    rng = np.random.default_rng(seed)
    if len(df) <= cap:
        return df.iloc[rng.permutation(len(df))].reset_index(drop=True)
    groups = {k: g for k, g in df.groupby(["field", "rule"], sort=True)}
    alloc = dict.fromkeys(groups, 0)
    remaining, open_ = cap, sorted(groups)
    while remaining > 0 and open_:
        share = max(1, remaining // len(open_))
        for k in list(open_):
            take = min(share, len(groups[k]) - alloc[k], remaining)
            alloc[k] += take
            remaining -= take
            if alloc[k] == len(groups[k]):
                open_.remove(k)
            if remaining == 0:
                break
    parts = [groups[k].iloc[np.sort(rng.choice(len(groups[k]), n, replace=False))] for k, n in alloc.items() if n]
    picked = pd.concat(parts)
    return picked.iloc[rng.permutation(len(picked))].reset_index(drop=True)


def record_id(seed: int, point_id: str, ts: pd.Timestamp, field: str) -> str:
    return "r" + hashlib.sha256(f"{seed}|{point_id}|{ts.isoformat()}|{field}".encode()).hexdigest()[:10]


def _r(x) -> float | None:
    return None if x is None or not math.isfinite(float(x)) else round(float(x), 2)


def context_values(conv: pd.DataFrame, field: str, ts: pd.Timestamp, cut: pd.Timestamp, n: int) -> dict[str, float]:
    out = {}
    for k in range(-n, n + 1):
        t = ts + pd.Timedelta(hours=k)
        if t > cut or t not in conv.index:
            continue
        v = _r(conv.at[t, field])
        if v is not None:
            out[f"h{k:+d}" if k else "h0"] = v
    return out


def build_record(row: pd.Series, conv: pd.DataFrame, rcfg: dict, frost_cfg: dict, rid: str) -> dict:
    """Masked record: opaque id, field, unit, flag, value and relative-hour context, nothing else."""
    field, ts, cut = row["field"], row["timestamp_utc"], row["cutoff_utc"]
    n = rcfg["neighbor_hours"]
    ctx = {SHORT[field]: context_values(conv, field, ts, cut, n)}
    for other in ("t2m_c", "d2m_c"):
        ctx.setdefault(SHORT[other], context_values(conv, other, ts, cut, n))
    unit = rcfg["units"][field]
    flag = row["rule"]
    if flag == "hourly_jump":
        limit = frost_cfg["eda"]["max_hourly_jump"][field]
        flag = f"absolute change from h-1 above {limit} {unit}"
    return {"id": rid, "field": SHORT[field], "name": rcfg["names"][field], "unit": unit, "flag": flag,
            "value": _r(conv.at[ts, field]), "context": ctx}


def mock_review(payload: dict) -> dict:
    """Deterministic fake answer with the real schema: keep, except every 10th id (by hash) which is
    corrected to the mean of its h-1 and h+1 neighbors when both exist."""
    out = []
    for rec in payload["records"]:
        ctx = rec["context"][rec["field"]]
        corr = int(hashlib.sha256(rec["id"].encode()).hexdigest(), 16) % 10 == 0 and "h-1" in ctx and "h+1" in ctx
        if corr:
            out.append({"id": rec["id"], "action": "correct", "value": round((ctx["h-1"] + ctx["h+1"]) / 2, 2),
                        "confidence": 0.85, "reason": "mock: replaced by neighbor mean"})
        else:
            out.append({"id": rec["id"], "action": "keep", "value": rec["value"], "confidence": 0.9,
                        "reason": "mock: plausible"})
    return {"records": out}


def decide(row: pd.Series, item: dict | None, conv: pd.DataFrame, rcfg: dict) -> tuple[str, float | None]:
    """Decision for one record and the value to write (None if nothing is applied)."""
    if item is None:
        return "invalid_response", None
    if item["action"] == "keep":
        return "kept", None
    if item["confidence"] < rcfg["confidence_min"]:
        return "rejected_low_confidence", None
    field, ts, cut, v = row["field"], row["timestamp_utc"], row["cutoff_utc"], item["value"]
    lo, hi = rcfg["ranges_c"][field]
    if not lo <= v <= hi:
        return "rejected_range", None
    if field == "d2m_c" and v > float(conv.at[ts, "t2m_c"]):
        return "rejected_dewpoint", None
    if field == "t2m_c" and v < float(conv.at[ts, "d2m_c"]):
        return "rejected_dewpoint", None
    orig = float(conv.at[ts, field])
    nbs = [float(conv.at[t, field]) for t in (ts - pd.Timedelta(hours=1), ts + pd.Timedelta(hours=1))
           if t <= cut and t in conv.index]
    if nbs and max(abs(v - x) for x in nbs) > max(abs(orig - x) for x in nbs):
        return "rejected_jump", None
    return "applied", v


def apply_corrections(conv: pd.DataFrame, applied: pd.DataFrame) -> pd.DataFrame:
    """Write accepted values (rows with timestamp_utc, field, value) into a copy of the hourly series."""
    out = conv.copy()
    for ts, field, v in zip(applied["timestamp_utc"], applied["field"], applied["new_value"], strict=True):
        out.at[ts, field] = np.asarray(v, dtype=out[field].dtype)
        if field == "t2m_c":
            out.at[ts, "t2m_k"] = np.asarray(v + 273.15, dtype=out["t2m_k"].dtype)
    return out
