"""EDA of the daily AgERA5 series and cross-checks against ERA5-Land.

Writes docs/eda_agera5.md, figures in docs/figures/ and summary tables in
data/processed/eda_agera5/ (including a daily cross-check table for the notebook).

Run: .venv/bin/python pipelines/02b_eda_agera5.py
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c

OUT_DIR = c.PROCESSED / "eda_agera5"
DOC = c.ROOT / "docs" / "eda_agera5.md"
EXPECTED_DAYS = 15274


def file_attrs(entries, pid):
    rec = next(r for (d, p, _), r in entries.items() if d == "agera5_ts" and p == pid)
    ds = xr.open_dataset(rec["path"])
    try:
        return {v: dict(ds[v].attrs) for v in c.AGERA5_NAMES}, dict(ds.attrs)
    finally:
        ds.close()


def stats(x, y):
    ok = x.notna() & y.notna()
    x, y = x[ok], y[ok]
    return {"n": int(ok.sum()), "corr": float(np.corrcoef(x, y)[0, 1]),
            "bias": float((x - y).mean()), "mae": float((x - y).abs().mean())}


def main():
    cfg = c.load_yaml("configs/frost.yaml")
    entries = c.manifest_entries()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    c.FIGURES.mkdir(parents=True, exist_ok=True)
    nw = cfg["agera5_night_window"]

    coverage, xcheck_rows, daily, seasonal = [], [], [], {}
    for pid in c.point_ids():
        ag = c.read_agera5(pid, entries)
        conv = c.convert_era5land(c.read_era5land(pid, entries))
        era_lat, era_lon = conv.attrs["grid_lat"], conv.attrs["grid_lon"]
        idx = ag.index
        steps = idx.to_series().diff().dropna()
        cc = ag["cloud_cover_24h"]
        coverage.append({
            "point_id": pid, "first_date": idx.min().date(), "last_date": idx.max().date(),
            "days": len(idx), "expected_days": EXPECTED_DAYS,
            "non_daily_steps": int((steps != pd.Timedelta(days=1)).sum()),
            "duplicates": int(idx.duplicated().sum()),
            **{f"nan_{k}": int(ag[k].isna().sum()) for k in ag.columns},
            "cloud_below_0": int((cc < 0).sum()), "cloud_above_1": int((cc > 1).sum()),
            "agera5_lat": round(ag.attrs["grid_lat"], 4), "agera5_lon": round(ag.attrs["grid_lon"], 4),
            "era5land_lat": round(era_lat, 4), "era5land_lon": round(era_lon, 4),
            "offset_km": round(float(c.haversine_km(ag.attrs["grid_lat"], ag.attrs["grid_lon"], era_lat, era_lon)), 3),
        })
        seasonal[pid] = cc.groupby(cc.index.month).mean()

        # ERA5-Land minimum over 18:00 to 06:00 local. Window starting on S (22:00 UTC) ends on the
        # morning of S+1. Two alignments are compared: AgERA5 date = S+1 (night ending on that
        # date) and AgERA5 date = S (night starting on that date).
        w = c.night_windows(conv["t2m_c"], nw["start_hour_utc"], nw["n_hours"])
        w = w[w["count"] == nw["n_hours"]]["min"]
        ending = pd.Series(w.values, index=w.index + pd.Timedelta(days=1))
        starting = w
        rh19 = c.magnus_rh(conv["t2m_c"], conv["d2m_c"])
        rh19 = rh19[rh19.index.hour == cfg["features"]["hour_1500_utc"]]
        rh19.index = rh19.index.normalize()

        d = pd.DataFrame({
            "agera5_tmin_c": ag["tmin_night_k"] - 273.15,
            "era5land_min_night_ending_c": ending.reindex(idx),
            "era5land_min_night_starting_c": starting.reindex(idx),
            "agera5_rh15": ag["rh_15h"],
            "era5land_rh_19utc": rh19.reindex(idx),
            "cloud_cover_24h": cc,
        })
        d = d[d.index <= "2025-12-31"]  # 2026 is out of sample
        d.insert(0, "point_id", pid)
        daily.append(d.reset_index())

        t_end = stats(d["agera5_tmin_c"], d["era5land_min_night_ending_c"])
        t_start = stats(d["agera5_tmin_c"], d["era5land_min_night_starting_c"])
        both = d[["agera5_tmin_c", "era5land_min_night_ending_c"]].dropna()
        fa = both["agera5_tmin_c"] <= 0
        fe = both["era5land_min_night_ending_c"] <= 0
        rh = stats(d["agera5_rh15"], d["era5land_rh_19utc"])
        xcheck_rows.append({
            "point_id": pid, "n_days": t_end["n"],
            "tmin_corr_night_ending": t_end["corr"], "tmin_corr_night_starting": t_start["corr"],
            "tmin_bias_c": t_end["bias"], "tmin_mae_c": t_end["mae"],
            "frost_flag_agreement": float((fa == fe).mean()),
            "frost_rate_agera5": float(fa.mean()), "frost_rate_era5land": float(fe.mean()),
            "rh_corr": rh["corr"], "rh_bias_pct": rh["bias"], "rh_mae_pct": rh["mae"],
        })

    coverage = pd.DataFrame(coverage).set_index("point_id")
    xcheck = pd.DataFrame(xcheck_rows).set_index("point_id")
    seasonal = pd.DataFrame(seasonal)
    seasonal.index.name = "month"
    daily = pd.concat(daily, ignore_index=True)

    coverage.to_csv(OUT_DIR / "coverage.csv")
    xcheck.to_csv(OUT_DIR / "crosschecks.csv")
    seasonal.to_csv(OUT_DIR / "cloud_cover_by_month.csv")
    daily.to_parquet(OUT_DIR / "daily_crosscheck.parquet", index=False)

    fig, ax = plt.subplots(figsize=(8, 4))
    seasonal.plot(ax=ax, marker="o")
    ax.set_ylabel("mean cloud cover (0 to 1)"); ax.set_title("AgERA5 24 h mean cloud cover by month, 1984-12-31 to 2026-10-25")
    fig.tight_layout(); fig.savefig(c.FIGURES / "agera5_cloud_cover_by_month.png", dpi=120); plt.close(fig)
    el = daily[daily["point_id"] == "el_alto"].dropna()
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(el["era5land_min_night_ending_c"], el["agera5_tmin_c"], s=2, alpha=0.3)
    lim = [el[["era5land_min_night_ending_c", "agera5_tmin_c"]].min().min(), el[["era5land_min_night_ending_c", "agera5_tmin_c"]].max().max()]
    ax.plot(lim, lim, color="k", lw=1)
    ax.set_xlabel("ERA5-Land min 18:00 to 06:00 local (C)"); ax.set_ylabel("AgERA5 night minimum (C)")
    ax.set_title("El Alto, night ending on the AgERA5 date")
    fig.tight_layout(); fig.savefig(c.FIGURES / "agera5_vs_era5land_tmin_el_alto.png", dpi=120); plt.close(fig)

    var_attrs, global_attrs = file_attrs(entries, "el_alto")
    write_doc(coverage, xcheck, seasonal, var_attrs, global_attrs)
    c.write_json(OUT_DIR / "summary.json", {
        "days_per_point": coverage["days"].to_dict(),
        "max_offset_km": float(coverage["offset_km"].max()),
        "mean_tmin_corr_night_ending": float(xcheck["tmin_corr_night_ending"].mean()),
        "mean_tmin_corr_night_starting": float(xcheck["tmin_corr_night_starting"].mean()),
        "mean_frost_flag_agreement": float(xcheck["frost_flag_agreement"].mean()),
    })
    print(coverage[["days", "non_daily_steps", "cloud_below_0", "cloud_above_1", "offset_km"]].to_string())
    print(xcheck.round(3).to_string())


def write_doc(coverage, xcheck, seasonal, var_attrs, global_attrs):
    attr_rows = pd.DataFrame({v: {"long_name": a.get("long_name", ""), "units": a.get("units", ""),
                                  "temporal_aggregation": a.get("temporal_aggregation", "")}
                              for v, a in var_attrs.items()}).T
    attr_rows.index.name = "variable"
    lines = [
        "# EDA: AgERA5 daily series",
        "",
        "Generated by `pipelines/02b_eda_agera5.py`. AgERA5 (`sis-agrometeorological-indicators-timeseries`, Copernicus CDS) is a daily product derived from the ERA5 reanalysis, with its own 0.1 degree grid. It is reanalysis, not raw satellite imagery. Cross-checks use rows up to 2025-12-31; 2026 is out of sample.",
        "",
        f"File source attribute: \"{global_attrs.get('title', '')}\", institution \"{global_attrs.get('institution', '')}\".",
        "",
        "## Time convention",
        "From the variable attributes of the downloaded files:",
        "",
        c.md_table(attr_rows),
        "",
        "`valid_time` holds the date at 00:00, and the aggregation windows are given in local time (LT). The night-time minimum of date D covers 18:00 local of D-1 to 06:00 local of D, that is, the night that ends on the morning of D. This is confirmed below: the correlation with the ERA5-Land minimum of the night ending on D is far higher than with the night starting on D. Consequences for the night table: the AgERA5 night minimum for night D (starting at 18:00 of D) is the value dated D+1, and only as a label cross-check; the 24 h cloud cover of date D covers the whole local day D, so night D only uses the value of D-1.",
        "",
        "## Coverage, NaN, cloud range and grid offset",
        c.md_table(coverage, 3),
        "",
        "offset_km is the great-circle distance between the AgERA5 point returned for the city coordinates and the ERA5-Land cell used for the same point.",
        "",
        "## Cloud cover seasonal cycle (mean by month)",
        c.md_table(seasonal, 3),
        "",
        "![cloud cover by month](figures/agera5_cloud_cover_by_month.png)",
        "",
        "## Cross-checks against ERA5-Land",
        "- Night minimum: AgERA5 night-time minimum vs the minimum of hourly ERA5-Land t2m over 18:00 to 06:00 local (13 values). Bias and MAE are AgERA5 minus ERA5-Land, for the night ending on the AgERA5 date. Frost-flag agreement: share of nights where both are at or below 0 C or both are above.",
        "- RH: AgERA5 relative humidity at 15:00 local vs RH from ERA5-Land t2m and d2m at 19:00 UTC (Magnus, coefficients 17.62 and 243.12 C). Bias in percentage points.",
        "",
        c.md_table(xcheck, 3),
        "",
        "![AgERA5 vs ERA5-Land night minimum, El Alto](figures/agera5_vs_era5land_tmin_el_alto.png)",
        "",
        "Both products come from the ERA5 family, so agreement here is a consistency check, not an independent validation.",
        "",
    ]
    DOC.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
