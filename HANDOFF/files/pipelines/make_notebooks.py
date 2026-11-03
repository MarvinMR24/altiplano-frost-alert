"""Write the EDA notebooks. They only load outputs saved by the pipeline scripts and plot them.

Run: .venv/bin/python pipelines/make_notebooks.py
Then execute and export:
  .venv/bin/jupyter nbconvert --execute --to notebook --inplace notebooks/0*.ipynb
  .venv/bin/jupyter nbconvert --to html notebooks/0*.ipynb
"""

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"

SETUP = """from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
from IPython.display import Markdown, display

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
P = ROOT / "data" / "processed"
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)"""

NOTEBOOKS = {
    "01_eda_era5land.ipynb": [
        ("md", "# EDA: ERA5-Land hourly series\n\nLoads the outputs of `pipelines/02a_eda_era5land.py` (run it, or `dvc repro`, first). ERA5-Land is reanalysis, not raw satellite imagery, and the frost label comes from the same reanalysis."),
        ("code", SETUP),
        ("md", "## Coverage, gaps, duplicates and NaN"),
        ("code", 'pd.read_csv(P / "eda_era5land" / "coverage.csv", index_col=0).T'),
        ("md", "## Anomaly flags by rule and field\n\nRules and thresholds are in `configs/frost.yaml`. Nothing is fixed or dropped."),
        ("code", 'pd.read_csv(P / "eda_era5land" / "anomaly_counts.csv")'),
        ("code", 'anom = pd.read_parquet(P / "anomalies.parquet")\nanom.groupby(["rule", "field", "point_id"]).size().unstack(fill_value=0)'),
        ("code", 'jumps = anom[(anom["rule"] == "hourly_jump") & (anom["field"] == "t2m_c")]\njumps["timestamp_utc"].dt.hour.value_counts().sort_index().rename("t2m jumps by UTC hour")'),
        ("md", "## Frost frequency (nights of 1985-2025)"),
        ("code", 'pd.read_csv(P / "eda_era5land" / "frost_by_cell.csv", index_col=0)'),
        ("code", 'by_month = pd.read_csv(P / "eda_era5land" / "frost_rate_by_month.csv", index_col=0)\nax = by_month.plot(marker="o", figsize=(8, 4), title="Frost night rate by month")\nax.set_ylabel("rate"); plt.show()'),
        ("md", "## Trends 1985-2025"),
        ("code", 'pd.read_csv(P / "eda_era5land" / "trends.csv", index_col=0).round(2)'),
        ("code", 'by_year = pd.read_csv(P / "eda_era5land" / "frost_nights_by_year.csv", index_col=0)\nax = by_year.plot(figsize=(9, 4), title="Frost nights per year")\nax.set_ylabel("nights"); plt.show()'),
    ],
    "02_eda_agera5.ipynb": [
        ("md", "# EDA: AgERA5 daily series and cross-checks\n\nLoads the outputs of `pipelines/02b_eda_agera5.py`. AgERA5 is derived from ERA5 reanalysis; agreement with ERA5-Land is a consistency check, not an independent validation."),
        ("code", SETUP),
        ("md", "## Coverage, NaN, cloud range and grid offset"),
        ("code", 'pd.read_csv(P / "eda_agera5" / "coverage.csv", index_col=0).T'),
        ("md", "## Cloud cover seasonal cycle"),
        ("code", 'cc = pd.read_csv(P / "eda_agera5" / "cloud_cover_by_month.csv", index_col=0)\nax = cc.plot(marker="o", figsize=(8, 4), title="AgERA5 24 h mean cloud cover by month")\nax.set_ylabel("fraction"); plt.show()'),
        ("md", "## Cross-checks against ERA5-Land\n\nThe night-time minimum dated D covers the night ending on the morning of D; the two correlation columns compare both alignments."),
        ("code", 'pd.read_csv(P / "eda_agera5" / "crosschecks.csv", index_col=0).round(3)'),
        ("code", 'd = pd.read_parquet(P / "eda_agera5" / "daily_crosscheck.parquet")\nel = d[d["point_id"] == "el_alto"].dropna()\nfig, axes = plt.subplots(1, 2, figsize=(10, 4.5))\naxes[0].scatter(el["era5land_min_night_ending_c"], el["agera5_tmin_c"], s=2, alpha=0.3)\naxes[0].set(xlabel="ERA5-Land min, night ending on D (C)", ylabel="AgERA5 night min (C)", title="El Alto")\naxes[1].scatter(el["era5land_rh_19utc"], el["agera5_rh15"], s=2, alpha=0.3)\naxes[1].set(xlabel="ERA5-Land RH at 15:00 local (Magnus, %)", ylabel="AgERA5 RH 15:00 (%)", title="El Alto")\nplt.tight_layout(); plt.show()'),
    ],
    "03_night_table_and_eda.ipynb": [
        ("md", "# Night table and merged EDA\n\nLoads `data/processed/features.parquet` (built by `pipelines/03_build_night_table.py`) and the tables of `pipelines/03b_eda_merged.py`. Labels come from the same ERA5-Land reanalysis as the features."),
        ("code", SETUP),
        ("code", 'manifest = json.loads((P / "features_manifest.json").read_text())\nprint(manifest["night_range"], manifest["rows"], "rows")\npd.DataFrame(manifest["definitions"], index=["definition"]).T'),
        ("code", 'df = pd.read_parquet(P / "features.parquet")\ndf.head()'),
        ("md", "## Class balance by split"),
        ("code", 'pd.read_csv(P / "eda_merged" / "class_balance.csv", index_col=0)'),
        ("code", 'pd.read_csv(P / "eda_merged" / "frost_by_cell_split.csv", index_col=0).round(3)'),
        ("code", 'fy = pd.read_csv(P / "eda_merged" / "frost_by_year.csv", index_col=0)\nax = fy.plot(marker="o", legend=False, figsize=(9, 4), title="Frost night rate by year (8 cells)")\nfor s, (lo, hi) in manifest["split_definition"].items():\n    ax.axvspan(lo - 0.5, hi + 0.5, alpha=0.08)\n    ax.text((lo + hi) / 2, ax.get_ylim()[1], s, ha="center", va="top", fontsize=8)\nplt.show()'),
        ("md", "## Drift by split (standardized mean difference vs train)"),
        ("code", 'pd.read_csv(P / "eda_merged" / "drift_std_mean_diff.csv", index_col=0).round(3)'),
        ("md", "## Correlation with the label (training years only)"),
        ("code", 'corr = pd.read_csv(P / "eda_merged" / "corr_with_label_train.csv", index_col=0)\nax = corr.iloc[::-1].plot.barh(legend=False, figsize=(6, 7))\nax.set_xlabel("correlation with frost (train)"); plt.tight_layout(); plt.show()'),
        ("md", "## Sign check and agreement with the AgERA5 night minimum"),
        ("code", 's = json.loads((P / "eda_merged" / "summary.json").read_text())\nprint("cloud_cover_prev_day vs sky_emissivity_1800 (train):", round(s["sign_check_corr_cloud_prev_vs_emissivity_train"], 4))\nprint("label vs AgERA5 agreement:", round(s["label_vs_agera5_agreement_overall"], 4))\npd.read_csv(P / "eda_merged" / "label_vs_agera5.csv", index_col=0).round(3)'),
        ("md", "## Limitations\n\nSee `docs/eda_merged.md`: reanalysis labels, 9 km cells, AgERA5 grid offset in general, lagged cloud proxy, downward frost trend across the chronological splits, no confidence intervals."),
    ],
}


def main():
    NB_DIR.mkdir(exist_ok=True)
    for name, cells in NOTEBOOKS.items():
        nb = nbf.v4.new_notebook()
        nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
        nb.cells = [nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src) for kind, src in cells]
        nbf.write(nb, NB_DIR / name)
        print("wrote", NB_DIR / name)


if __name__ == "__main__":
    main()
