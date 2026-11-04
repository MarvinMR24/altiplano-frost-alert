"""Serving artifacts for the backend, in the shape of docs/artifacts_contract.md.

artifacts/model_card.json, artifacts/model_coefficients.json (no pickle) and
artifacts/predictions/<YYYY-MM-DD>.parquet (one file per night, one row per cell) for the held-out
nights: the test period (replay demo) and the 2026 out-of-sample nights (latest available nights).
Rows come from leakage.serving_rows, which works only after the single final evaluation exists.
Probabilities come from the numpy-only export (inference.predict), checked against the bundle.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import numpy as np
import pandas as pd

from .. import config
from ..dataio.tables import read_json, write_json, write_parquet, write_text
from ..evaluation.reports import md_table
from ..inference import predict

ART = config.ROOT / "artifacts"
DATA_SOURCE = "ERA5-Land reanalysis (Copernicus CDS)"
CONTRACT_CUTS = [0.3, 0.5, 0.7]
CONTRACT_LEVELS = ["low", "moderate", "high", "very_high"]
ALERT_LEVELS = ("high", "very_high")
# conditions_1800 keys the app already labels (docs/backend_notes.md) and their source features.
# Cloud cover is left out on purpose: the model only has the previous day's 24 h mean, which is not
# an 18:00 condition.
CONDITIONS = {"t2m_c": "t2m_1800_c", "d2m_c": "d2m_1800_c", "rh_pct": "rh_1800_pct", "wind_ms": "wind_1800_ms",
              "sp_hpa": "sp_1800_hpa", "lw_down_wm2": "strd_1800_wm2", "dewpoint_depression_c": "dewpoint_depression_1800_c"}
PERIOD_REPLAY = "replay_test_period"
PERIOD_LATEST = "out_of_sample_latest"
METRIC_KEYS = ("pr_auc", "f2", "precision", "recall", "f1", "roc_auc", "brier", "accuracy")


def contract_level(p: float) -> str:
    return CONTRACT_LEVELS[int(np.searchsorted(CONTRACT_CUTS, p, side="right"))]


def contract_metrics(m: dict) -> dict:
    return {**{k: float(m[k]) for k in METRIC_KEYS}, "majority_accuracy": float(m["majority_class_accuracy"])}


def model_card(lr_card: dict, final: dict, export: dict, muse_status: str) -> dict[str, Any]:
    lr = final["finalists"]["LR_best"]
    d = lr_card["data"]
    return {
        "model_version": lr_card["model_version"],
        "model_type": "logistic_regression",
        "condition": "A",
        "muse_condition_b": muse_status,
        "trained_years": d["training_years"],
        "validation_years": d["validation_years"],
        "test_years": d["test_years"],
        "test_status": "available",
        "n_cells": 8,
        "features": lr_card["features"],
        "decision_threshold": float(lr_card["threshold"]["value"]),
        "threshold_rule": "maximize F2 on validation",
        "calibration": lr_card["calibration"],
        "levels": {"low": "p < 0.3", "moderate": "0.3 <= p < 0.5", "high": "0.5 <= p < 0.7", "very_high": "p >= 0.7"},
        "metrics": {"validation": contract_metrics(lr_card["metrics_validation"]["pooled"]),
                    "test": contract_metrics(lr["pooled"])},
        "metrics_macro_over_cells": {"validation": contract_metrics(lr_card["metrics_validation"]["macro_over_cells"]),
                                     "test": contract_metrics(lr["macro_over_cells"])},
        "base_rates": final["base_rates"],
        "label_definition": lr_card["label_definition"],
        "data_source": DATA_SOURCE,
        "limitations": [
            "Labels come from the same ERA5-Land reanalysis as the features: the model predicts grid frost (0.1 degree cell), not frost measured at a station.",
            "The data is reanalysis (a weather model with assimilated observations), not raw satellite imagery, and it is published a few days late: this is not a live forecast.",
            "Valid only for the 8 ERA5-Land cells of configs/points.yaml.",
            "Test nights (2018-2025) have fewer frost nights than training (1985-2009) because frost nights trend down.",
            "No confidence intervals are computed; small metric differences may be noise.",
        ],
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_hash": final["data_hash"],
        "serving_parity": "probabilities from the numpy export (lr_export.json), equal to the model bundle within 1e-9",
        "lr_export_model_version": export["model_version"],
    }


def coefficients(export: dict) -> dict[str, Any]:
    names = export["feature_names"]
    return {"model_version": export["model_version"], "intercept": export["intercept"],
            "coefficients": dict(zip(names, export["coefficients"], strict=True)),
            "scaler": {"mean": dict(zip(names, export["means"], strict=True)),
                       "scale": dict(zip(names, export["stds"], strict=True))},
            "calibration": export["calibration"], "decision_threshold": export["threshold"],
            "formula": "z = intercept + sum(coef[f] * (x[f] - mean[f]) / scale[f]); p = sigmoid(a * z + b) with calibration (a, b)"}


def _bin(bins: list[dict], p: float) -> dict:
    edges = [b["upper"] for b in bins[:-1]]
    b = bins[int(np.searchsorted(edges, p, side="right"))]
    if not b["count"]:
        raise ValueError(f"empty validation reliability bin for p={p}")
    return {"range": [round(b["lower"], 6), round(b["upper"], 6)], "observed_rate": float(b["observed_rate"]),
            "n": int(b["count"])}


def prediction_table(rows: pd.DataFrame, export: dict, bins: list[dict], cells: dict[str, list[float]]) -> pd.DataFrame:
    """One contract row per (cell, night). `rows` are night-table rows with their split."""
    names = export["feature_names"]
    p = predict.probability(export, rows)
    z = (rows[names].to_numpy(dtype=float) - np.asarray(export["means"])) / np.asarray(export["stds"])
    contrib = z * np.asarray(export["coefficients"])
    drivers = []
    for i in range(len(rows)):
        order = np.argsort(-np.abs(contrib[i]), kind="mergesort")
        drivers.append(json.dumps([{"feature": names[j], "effect": "up" if contrib[i, j] > 0 else "down",
                                    "weight": round(abs(float(contrib[i, j])), 3)} for j in order]))
    cond = [json.dumps({k: round(float(r[f]), 2) for k, f in CONDITIONS.items()}) for _, r in rows.iterrows()]
    frost = rows["frost"].astype("Int8")
    out = pd.DataFrame({
        "point_id": rows["point_id"].astype(str).to_numpy(),
        "grid_lat": [float(cells[pid][0]) for pid in rows["point_id"]],
        "grid_lon": [float(cells[pid][1]) for pid in rows["point_id"]],
        "elevation_m": rows["elevation_proxy_m"].astype(float).to_numpy(),
        "night_date": rows["night_date"].dt.date.to_numpy(),
        "probability": p.astype(float),
        "level": [contract_level(float(x)) for x in p],
        "top_drivers": drivers,
        "conditions_1800": cond,
        "historical_reliability": [json.dumps(_bin(bins, float(x))) for x in p],
        "observed_frost": pd.array([None if pd.isna(v) else bool(v) for v in frost], dtype="boolean"),
        "observed_tmin_c": rows["tmin_c"].astype(float).where(frost.notna().to_numpy()).to_numpy(),
        "model_version": export["model_version"],
        "data_source": DATA_SOURCE,
        "period": np.where(rows["split"].to_numpy() == "out_of_sample_check", PERIOD_LATEST, PERIOD_REPLAY),
    })
    return out


def write_predictions(table: pd.DataFrame) -> int:
    folder = ART / "predictions"
    folder.mkdir(parents=True, exist_ok=True)
    n = 0
    for night, g in table.groupby("night_date", sort=True):
        if len(g) != 8 or g["point_id"].duplicated().any():
            raise ValueError(f"{night}: expected 8 distinct cells, got {len(g)}")
        write_parquet(g.sort_values("point_id").reset_index(drop=True), folder / f"{night.isoformat()}.parquet")
        n += 1
    return n


def write_card_files(card: dict, coefs: dict) -> None:
    write_json(card, ART / "model_card.json")
    write_json(coefs, ART / "model_coefficients.json")


def _n(k, one: str, many: str | None = None) -> str:
    k = int(k)
    return f"{k} {one if k == 1 else (many or one + 's')}"


def replay_candidates(table: pd.DataFrame, path) -> dict[str, Any]:
    """Demo nights from the test period only: good nights, one honest miss and one false alarm."""
    t = table[table["period"] == PERIOD_REPLAY].copy()
    t["frost"] = t["observed_frost"].astype(bool)
    t["alert"] = t["level"].isin(ALERT_LEVELS)
    t["hit"] = t["frost"] & t["alert"]
    t["miss"] = t["frost"] & (t["level"] == "low")
    t["quiet_ok"] = ~t["frost"] & (t["level"] == "low")
    per = t.groupby("night_date").agg(hits=("hit", "sum"), misses=("miss", "sum"), quiet_ok=("quiet_ok", "sum"),
                                      frost_cells=("frost", "sum"), mean_p=("probability", "mean")).reset_index()
    per["correct"] = per["hits"] + per["quiet_ok"]
    good = per[(per["hits"] >= 3) & (per["misses"] == 0) & (per["quiet_ok"] >= 1)]
    good = good.sort_values(["correct", "hits", "night_date"], ascending=[False, False, False], kind="mergesort")
    picks, months = [], set()
    for _, r in good.iterrows():
        ym = (r["night_date"].year, r["night_date"].month)
        if ym in months:
            continue
        picks.append(r["night_date"])
        months.add(ym)
        if len(picks) == 3:
            break
    miss = t[t["miss"]].sort_values(["observed_tmin_c", "probability"], kind="mergesort").head(1)
    fa = t[~t["frost"] & t["alert"]].sort_values("probability", ascending=False, kind="mergesort").head(1)
    cols = ["point_id", "probability", "level", "observed_frost", "observed_tmin_c"]

    def night_table(night):
        g = t[t["night_date"] == night][cols].sort_values("probability", ascending=False).set_index("point_id")
        return md_table(g, 3)

    lines = ["# Replay candidates (test period 2018-2025 only)", "",
             "Generated by `pipelines/07_export_serving.py` from the exported predictions of LR_best "
             "(thresholds fixed on validation). Levels: low < 0.3, moderate 0.3 to 0.5, high 0.5 to 0.7, very_high >= 0.7. "
             "Observed values come from the same ERA5-Land reanalysis as the features (grid frost, not station frost).", "",
             f"Selection: nights with at least 3 cells where frost occurred and the model said high or very_high, no cell "
             f"with frost left at low, and at least one cell without frost correctly at low. {len(good)} test nights qualify; "
             "the 3 below are the ones with the most correct cells, from different months.", ""]
    for i, night in enumerate(picks, start=1):
        r = per[per["night_date"] == night].iloc[0]
        lines += [f"## Good demo night {i}: {night.isoformat()}", "",
                  f"{_n(r['hits'], 'cell')} with frost flagged high or very_high, {_n(r['quiet_ok'], 'cell')} without frost "
                  f"correctly low, {_n(r['misses'], 'miss', 'misses')}.", "", night_table(night), ""]
    if len(miss):
        m = miss.iloc[0]
        lines += [f"## Honest miss: {m['night_date'].isoformat()}, {m['point_id']}", "",
                  f"Frost observed (tmin {m['observed_tmin_c']:.2f} C) but the model gave {m['probability']:.3f} ({m['level']}). "
                  "Among all test misses (frost observed, level low), this is the one with the coldest observed minimum.", "",
                  night_table(m["night_date"]), ""]
    if len(fa):
        f = fa.iloc[0]
        lines += [f"## False alarm: {f['night_date'].isoformat()}, {f['point_id']}", "",
                  f"No frost (tmin {f['observed_tmin_c']:.2f} C) but the model gave {f['probability']:.3f} ({f['level']}). "
                  "Among all test false alarms (no frost, level high or very_high), this is the one with the highest probability.", "",
                  night_table(f["night_date"]), ""]
    rec = None
    if picks:
        rec = picks[0]
        r = per[per["night_date"] == rec].iloc[0]
        lines += ["## Recommended replay night", "",
                  f"**{rec.isoformat()}**: it has the most correct cells of all qualifying test nights "
                  f"({_n(r['hits'], 'frost cell')} flagged high or very_high and {_n(r['quiet_ok'], 'frost-free cell')} left at low, "
                  "no misses). The demo shows real alerts and quiet cells on the same night, so the model visibly discriminates "
                  "instead of flagging everything.", ""]
    counts = {"test_nights": int(per["night_date"].nunique()), "qualifying_good_nights": int(len(good)),
              "misses_total": int(t["miss"].sum()), "false_alarms_total": int((~t["frost"] & t["alert"]).sum())}
    lines += ["## Counts", "", f"Test nights: {counts['test_nights']}. Cell-nights with frost left at low (misses): "
              f"{counts['misses_total']}. Cell-nights without frost at high or very_high (false alarms at the high cut): "
              f"{counts['false_alarms_total']}. Note: alerts in the app use the validation threshold and the user's threshold, "
              "not only these levels.", ""]
    write_text("\n".join(lines), path)
    return {"recommended": rec.isoformat() if rec else None, "good": [d.isoformat() for d in picks], **counts}


def load_inputs(version: str) -> tuple[dict, dict, list[dict]]:
    folder = config.REPORTS / version
    return read_json(folder / "lr_export.json"), read_json(folder / "model_card.json"), read_json(folder / "reliability_bins.json")
