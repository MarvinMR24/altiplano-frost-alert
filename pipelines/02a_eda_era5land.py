"""EDA of the hourly ERA5-Land series (8 cells, 1985-01-01 to 2026-10-26).

Writes docs/eda_era5land.md, figures in docs/figures/, the anomaly list
data/processed/anomalies.parquet (point_id, timestamp_utc, field, rule, value) and summary
tables for the notebook in data/processed/eda_era5land/. Nothing is fixed or dropped.

Run: .venv/bin/python pipelines/02a_eda_era5land.py
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c

OUT_DIR = c.PROCESSED / "eda_era5land"
DOC = c.ROOT / "docs" / "eda_era5land.md"


def anomalies_for(point_id, conv, cfg):
    e = cfg["eda"]
    rows = []

    def add(mask, field, rule):
        idx = conv.index[mask.values]
        rows.append(pd.DataFrame({"point_id": point_id, "timestamp_utc": idx, "field": field,
                                  "rule": rule, "value": conv.loc[idx, field].astype(float).values}))

    add(conv["d2m_c"] > conv["t2m_c"] + e["dewpoint_tolerance_c"], "d2m_c", "dewpoint_above_temperature")
    add(conv["wind_ms"] < 0, "wind_ms", "wind_negative")
    add(conv["ssrd_wm2"] < 0, "ssrd_wm2", "ssrd_negative")
    add(conv["tp_mm"] < 0, "tp_mm", "precipitation_negative")
    night = np.isin(conv.index.hour, e["ssrd_night_hours_utc"])
    add(pd.Series(night, index=conv.index) & (conv["ssrd_wm2"] > e["ssrd_night_max_wm2"]), "ssrd_wm2", "ssrd_at_night")
    lo, hi = e["strd_range_wm2"]
    add((conv["strd_wm2"] < lo) | (conv["strd_wm2"] > hi), "strd_wm2", "strd_out_of_range")
    add((conv["sp_hpa"] - conv["sp_hpa"].median()).abs() > e["sp_max_offset_from_cell_median_hpa"], "sp_hpa", "sp_far_from_cell_median")

    hourly = conv.index.to_series().diff() == pd.Timedelta(hours=1)
    for field, limit in e["max_hourly_jump"].items():
        jump = conv[field].diff().abs()
        add(hourly & (jump > limit), field, "hourly_jump")

    for field in e["stuck_fields"]:
        s = conv[field]
        run_id = (s != s.shift()).cumsum()
        run_len = s.groupby(run_id).transform("size")
        add(run_len >= e["stuck_min_run_hours"], field, "stuck_value")

    return pd.concat(rows, ignore_index=True)


def coverage_for(point_id, raw, conv):
    idx = raw.index
    expected = pd.date_range(idx.min(), idx.max(), freq="h")
    steps = idx.to_series().diff().dropna()
    row = {
        "point_id": point_id,
        "first_utc": idx.min(),
        "last_utc": idx.max(),
        "hours": len(idx),
        "expected_hours": len(expected),
        "missing_hours": len(expected.difference(idx)),
        "duplicate_timestamps": int(idx.duplicated().sum()),
        "non_hourly_steps": int((steps != pd.Timedelta(hours=1)).sum()),
        "grid_lat": round(raw.attrs["grid_lat"], 4),
        "grid_lon": round(raw.attrs["grid_lon"], 4),
        "mean_sp_hpa": round(float(conv["sp_hpa"].mean()), 2),
    }
    for v in c.ERA5_VARS:
        row[f"nan_{v}"] = int(raw[v].isna().sum())
    return row


def trend_per_decade(years, values):
    slope = np.polyfit(years, values, 1)[0]
    return slope * 10


def main():
    cfg = c.load_yaml("configs/frost.yaml")
    entries = c.manifest_entries()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    c.FIGURES.mkdir(parents=True, exist_ok=True)

    coverage, anomalies, nights, ranges = [], [], [], []
    for pid in c.point_ids():
        raw = c.read_era5land(pid, entries)
        conv = c.convert_era5land(raw)
        coverage.append(coverage_for(pid, raw, conv))
        anomalies.append(anomalies_for(pid, conv, cfg))
        n = c.frost_nights(conv, cfg).reset_index()
        n.insert(0, "point_id", pid)
        nights.append(n)
        desc = conv.drop(columns=["t2m_k"]).describe().T[["min", "mean", "max"]]
        desc.insert(0, "point_id", pid)
        ranges.append(desc.reset_index(names="field"))

    coverage = pd.DataFrame(coverage).set_index("point_id")
    anomalies = pd.concat(anomalies, ignore_index=True)
    nights = pd.concat(nights, ignore_index=True)
    ranges = pd.concat(ranges, ignore_index=True)

    anomalies.to_parquet(c.PROCESSED / "anomalies.parquet", index=False)
    coverage.to_csv(OUT_DIR / "coverage.csv")
    ranges.to_csv(OUT_DIR / "value_ranges.csv", index=False)
    nights.to_parquet(OUT_DIR / "nights_label.parquet", index=False)

    # Frost frequency, complete nights of 1985-2025 only (2026 is out of sample).
    hist = nights[(nights["night_date"] >= "1985-01-01") & (nights["night_date"] <= "2025-12-31")].dropna(subset=["frost"])
    hist = hist.assign(year=hist["night_date"].dt.year, month=hist["night_date"].dt.month,
                       frost=hist["frost"].astype(float))
    by_cell = hist.groupby("point_id").agg(nights=("frost", "size"), frost_rate=("frost", "mean"),
                                           mean_tmin_c=("tmin_c", "mean"))
    by_month = hist.pivot_table(index="month", columns="point_id", values="frost", aggfunc="mean")
    by_year = hist.pivot_table(index="year", columns="point_id", values="frost", aggfunc="sum")
    tmin_year = hist.pivot_table(index="year", columns="point_id", values="tmin_c", aggfunc="mean")
    trends = pd.DataFrame({
        "frost_nights_per_decade": {p: trend_per_decade(by_year.index.values, by_year[p].values) for p in by_year},
        "mean_tmin_c_per_decade": {p: trend_per_decade(tmin_year.index.values, tmin_year[p].values) for p in tmin_year},
        "frost_nights_1985_1994_mean": by_year.loc[1985:1994].mean(),
        "frost_nights_2016_2025_mean": by_year.loc[2016:2025].mean(),
    })
    trends.index.name = "point_id"
    by_cell.to_csv(OUT_DIR / "frost_by_cell.csv")
    by_month.to_csv(OUT_DIR / "frost_rate_by_month.csv")
    by_year.to_csv(OUT_DIR / "frost_nights_by_year.csv")
    trends.to_csv(OUT_DIR / "trends.csv")

    rule_counts = anomalies.groupby(["rule", "field"]).size().rename("count").reset_index()
    rule_by_cell = anomalies.pivot_table(index="rule", columns="point_id", values="value", aggfunc="size", fill_value=0)
    rule_counts.to_csv(OUT_DIR / "anomaly_counts.csv", index=False)
    neg = anomalies[anomalies["rule"].isin(["ssrd_negative", "precipitation_negative"])]
    neg_min = neg.groupby("rule")["value"].min() if len(neg) else pd.Series(dtype=float)

    # Figures
    fig, ax = plt.subplots(figsize=(8, 4))
    by_month.plot(ax=ax, marker="o")
    ax.set_ylabel("frost night rate"); ax.set_title("Frost night rate by month, 1985-2025 (ERA5-Land)")
    fig.tight_layout(); fig.savefig(c.FIGURES / "era5land_frost_rate_by_month.png", dpi=120); plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4))
    by_year.plot(ax=ax)
    ax.set_ylabel("frost nights per year"); ax.set_title("Frost nights per year (ERA5-Land, tmin <= 0 C, 18:00 to 09:00 local)")
    fig.tight_layout(); fig.savefig(c.FIGURES / "era5land_frost_nights_by_year.png", dpi=120); plt.close(fig)

    write_doc(cfg, coverage, rule_counts, rule_by_cell, neg_min, by_cell, by_month, trends, ranges)
    c.write_json(OUT_DIR / "summary.json", {
        "points": len(coverage), "hours_per_point": coverage["hours"].to_dict(),
        "anomalies_total": int(len(anomalies)),
        "anomalies_by_rule": anomalies.groupby("rule").size().to_dict(),
    })
    print(rule_counts.to_string(index=False))
    print(by_cell.round(3).to_string())


def write_doc(cfg, coverage, rule_counts, rule_by_cell, neg_min, by_cell, by_month, trends, ranges):
    e = cfg["eda"]
    cov_cols = ["first_utc", "last_utc", "hours", "expected_hours", "missing_hours",
                "duplicate_timestamps", "non_hourly_steps", "grid_lat", "grid_lon", "mean_sp_hpa"]
    nan_cols = [f"nan_{v}" for v in c.ERA5_VARS]
    rng = ranges.pivot_table(index="field", columns="point_id", values="min").round(2)
    rng_max = ranges.pivot_table(index="field", columns="point_id", values="max").round(2)
    lines = [
        "# EDA: ERA5-Land hourly series",
        "",
        "Generated by `pipelines/02a_eda_era5land.py`. Data: ERA5-Land reanalysis (Copernicus CDS), not raw satellite imagery. "
        "The frost label is computed from the same reanalysis, so it describes frost on the 0.1 degree grid, not at a station.",
        "",
        "Inputs: 8 cells, main file 1985-01-01 to 2025-12-31 plus the 2026 file up to 2026-10-26 (out-of-sample check), read from the zip archives listed in the manifest.",
        "",
        "## Units",
        "t2m, d2m, skt, stl1: K to C. sp: Pa to hPa. ssrd, strd: J m-2 accumulated over the hour ending at the timestamp, divided by 3600 to W m-2. tp: m to mm per hour. Wind speed = sqrt(u10^2 + v10^2) in m s-1.",
        "",
        "## Coverage, gaps and duplicates",
        c.md_table(coverage[cov_cols], 2),
        "",
        "## NaN per variable",
        c.md_table(coverage[nan_cols], 0),
        "",
        "## Value ranges after conversion (min / max per cell)",
        "Minimum:",
        "",
        c.md_table(rng, 2),
        "",
        "Maximum:",
        "",
        c.md_table(rng_max, 2),
        "",
        "## Anomaly rules",
        f"- dewpoint_above_temperature: d2m > t2m + {e['dewpoint_tolerance_c']} C.",
        "- wind_negative: wind speed < 0 (cannot happen by construction, checked anyway).",
        "- ssrd_negative, precipitation_negative: value < 0.",
        f"- ssrd_at_night: ssrd > {e['ssrd_night_max_wm2']} W m-2 for hours ending at {e['ssrd_night_hours_utc']} UTC (21:00 to 05:00 local).",
        f"- strd_out_of_range: strd outside {e['strd_range_wm2']} W m-2.",
        f"- sp_far_from_cell_median: |sp - cell median| > {e['sp_max_offset_from_cell_median_hpa']} hPa.",
        f"- hourly_jump: absolute change between consecutive hours above {e['max_hourly_jump']}.",
        f"- stuck_value: the same value for at least {e['stuck_min_run_hours']} consecutive hours in {e['stuck_fields']} (one row per hour of the run).",
        "",
        "These thresholds are screening choices declared in `configs/frost.yaml`, not physical constants. Flags are listed with exact positions in `data/processed/anomalies.parquet`; nothing is fixed or dropped.",
        "",
        "### Counts by rule and field",
        c.md_table(rule_counts.set_index("rule"), 0),
        "",
        "### Counts by rule and cell",
        c.md_table(rule_by_cell, 0),
        "",
    ]
    if len(neg_min):
        lines += ["Most negative values flagged by the negative-value rules (de-accumulation rounding is the likely cause when they are tiny):", "",
                  c.md_table(neg_min.to_frame("min_value"), 8), ""]
    lines += [
        "## Frost frequency (nights of 1985-2025)",
        "Frost night: minimum hourly t2m from 18:00 local of day D to 09:00 local of day D+1 (22:00 UTC to 13:00 UTC, 16 values) at or below 0 C.",
        "",
        c.md_table(by_cell, 3),
        "",
        "### By month",
        c.md_table(by_month, 3),
        "",
        "![frost rate by month](figures/era5land_frost_rate_by_month.png)",
        "",
        "## Trends 1985-2025",
        "Ordinary least squares slope of the annual count of frost nights and of the annual mean night minimum, per decade, plus the mean annual frost nights in the first and last 10 years.",
        "",
        c.md_table(trends, 2),
        "",
        "![frost nights by year](figures/era5land_frost_nights_by_year.png)",
        "",
        "A trend means the chronological split (train 1985-2009, validation 2010-2017, test 2018-2025) sees different base rates in each split. No confidence intervals are computed.",
        "",
    ]
    DOC.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
