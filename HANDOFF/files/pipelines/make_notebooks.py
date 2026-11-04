"""Write the presentation notebooks. They import only frostwatch_ml, load saved outputs and plot.

Run: .venv/bin/python pipelines/make_notebooks.py [--only 01 02 ...]
Then execute and export (Makefile target `notebooks`):
  .venv/bin/jupyter nbconvert --execute --to notebook --inplace notebooks/0*.ipynb
  .venv/bin/jupyter nbconvert --to html notebooks/0*.ipynb
"""

import argparse

import nbformat as nbf

from frostwatch_ml import config

SETUP = "from frostwatch_ml.evaluation import notebook as nb\nfrom frostwatch_ml.evaluation import plots"

NOTEBOOKS = {
    "01_eda_era5land.ipynb": [
        ("md", "# EDA: ERA5-Land hourly series\n\nPresents the outputs of `pipelines/02a_eda_era5land.py` (`dvc repro` first). ERA5-Land is reanalysis, not raw satellite imagery, and the frost label comes from the same reanalysis."),
        ("code", SETUP),
        ("md", "## Coverage, gaps, duplicates and NaN"),
        ("code", 'nb.csv("data/processed/eda_era5land/coverage.csv").T'),
        ("md", "## Anomaly flags by rule and field\n\nRules and thresholds are in `configs/frost.yaml`. Nothing is fixed or dropped."),
        ("code", 'nb.csv("data/processed/eda_era5land/anomaly_counts.csv", index_col=None)'),
        ("code", 'anom = nb.parquet("data/processed/anomalies.parquet")\nanom.groupby(["rule", "field", "point_id"]).size().unstack(fill_value=0)'),
        ("code", 'jumps = anom[(anom["rule"] == "hourly_jump") & (anom["field"] == "t2m_c")]\njumps["timestamp_utc"].dt.hour.value_counts().sort_index().rename("t2m jumps by UTC hour")'),
        ("md", "## Frost frequency (nights of 1985-2025)"),
        ("code", 'nb.csv("data/processed/eda_era5land/frost_by_cell.csv")'),
        ("code", 'nb.figure(plots.lines(nb.csv("data/processed/eda_era5land/frost_rate_by_month.csv"), "Frost night rate by month", "rate"))'),
        ("md", "## Trends 1985-2025"),
        ("code", 'nb.csv("data/processed/eda_era5land/trends.csv").round(2)'),
        ("code", 'nb.figure(plots.lines(nb.csv("data/processed/eda_era5land/frost_nights_by_year.csv"), "Frost nights per year", "nights", marker=None, figsize=(9, 4)))'),
    ],
    "02_eda_agera5.ipynb": [
        ("md", "# EDA: AgERA5 daily series and cross-checks\n\nPresents the outputs of `pipelines/02b_eda_agera5.py`. AgERA5 is derived from ERA5 reanalysis; agreement with ERA5-Land is a consistency check, not an independent validation."),
        ("code", SETUP),
        ("md", "## Coverage, NaN, cloud range and grid offset"),
        ("code", 'nb.csv("data/processed/eda_agera5/coverage.csv").T'),
        ("md", "## Cloud cover seasonal cycle"),
        ("code", 'nb.figure(plots.lines(nb.csv("data/processed/eda_agera5/cloud_cover_by_month.csv"), "AgERA5 24 h mean cloud cover by month", "fraction"))'),
        ("md", "## Cross-checks against ERA5-Land\n\nThe night-time minimum dated D covers the night ending on the morning of D; the two correlation columns compare both alignments."),
        ("code", 'nb.csv("data/processed/eda_agera5/crosschecks.csv").round(3)'),
        ("code", 'd = nb.parquet("data/processed/eda_agera5/daily_crosscheck.parquet")\nel = d[d["point_id"] == "el_alto"].dropna()\nnb.figure(plots.scatter(el["era5land_min_night_ending_c"], el["agera5_tmin_c"], "ERA5-Land min, night ending on D (C)", "AgERA5 night min (C)", "El Alto"))'),
        ("code", 'nb.figure(plots.scatter(el["era5land_rh_19utc"], el["agera5_rh15"], "ERA5-Land RH at 15:00 local (Magnus, %)", "AgERA5 RH 15:00 (%)", "El Alto"))'),
    ],
    "03_night_table_and_eda.ipynb": [
        ("md", "# Night table and merged EDA\n\nPresents `data/processed/features.parquet` (`pipelines/03_build_night_table.py`) and the tables of `pipelines/03b_eda_merged.py`. Labels come from the same ERA5-Land reanalysis as the features."),
        ("code", SETUP),
        ("code", 'manifest = nb.load_json("data/processed/features_manifest.json")\nprint(manifest["night_range"], manifest["rows"], "rows; features from", manifest["feature_allowlist_source"])'),
        ("code", 'nb.parquet("data/processed/features.parquet").head()'),
        ("md", "## Class balance by split"),
        ("code", 'nb.csv("data/processed/eda_merged/class_balance.csv")'),
        ("code", 'nb.csv("data/processed/eda_merged/frost_by_cell_split.csv").round(3)'),
        ("code", 'nb.show_figure("docs/figures/merged_frost_rate_by_year.png")'),
        ("md", "## Drift by split (standardized mean difference vs train)"),
        ("code", 'nb.csv("data/processed/eda_merged/drift_std_mean_diff.csv").round(3)'),
        ("md", "## Correlation with the label (training years only)"),
        ("code", 'nb.figure(plots.barh(nb.csv("data/processed/eda_merged/corr_with_label_train.csv")["corr_with_frost_train"], "Correlation with frost (train)", "Pearson r"))'),
        ("md", "## Sign check and agreement with the AgERA5 night minimum"),
        ("code", 's = nb.load_json("data/processed/eda_merged/summary.json")\nprint("cloud_cover_prev_day vs sky_emissivity_1800 (train):", round(s["sign_check_corr_cloud_prev_vs_emissivity_train"], 4))\nprint("label vs AgERA5 agreement:", round(s["label_vs_agera5_agreement_overall"], 4))\nnb.csv("data/processed/eda_merged/label_vs_agera5.csv").round(3)'),
        ("md", "## Limitations\n\nSee `docs/eda_merged.md`: reanalysis labels, 9 km cells, AgERA5 grid offset in general, lagged cloud proxy, downward frost trend across the chronological splits, no confidence intervals."),
    ],
    "04_round1_models.ipynb": [
        ("md", "# Round 1: baselines and default models (validation only)\n\nPresents the outputs of `pipelines/04_round1.py`. The test set is locked. Labels come from the same reanalysis as the features."),
        ("code", SETUP),
        ("code", 'nb.show_markdown(nb.markdown("reports/round1/comparison_pooled.md"))'),
        ("code", 'nb.show_markdown(nb.markdown("reports/round1/comparison_macro.md"))'),
        ("code", 'nb.show_markdown(nb.markdown("reports/round1/skill_vs_baselines.md"))'),
        ("code", 'nb.csv("reports/round1/per_cell_metrics.csv", index_col=None).pivot_table(index="point_id", columns="model", values="pr_auc").round(3)'),
        ("code", 'nb.show_figure("reports/round1/figures/pr_curves_validation.png")'),
    ],
    "05_round2_tuning.ipynb": [
        ("md", "# Round 2: tuning and finalists (validation only)\n\nPresents the outputs of `pipelines/05_round2.py`. The test set is locked."),
        ("code", SETUP),
        ("code", 'nb.show_markdown(nb.markdown("reports/round2/finalists.md"))'),
        ("code", 'nb.csv("reports/round2/lr_grid.csv", index_col=None).sort_values("pr_auc", ascending=False).head(10)'),
        ("code", 'nb.csv("reports/round2/tree_search.csv", index_col=None).sort_values("pr_auc", ascending=False).head(10)'),
        ("code", 'nb.show_markdown(nb.markdown("reports/round2/comparison_macro.md"))'),
        ("code", 'lr_dir = nb.latest_model_dir("lr")\nnb.csv(lr_dir + "/coefficients.csv", index_col=None).head(12)'),
        ("code", 'nb.figure(plots.reliability(nb.csv(lr_dir + "/reliability_bins.csv", index_col=None), "LR_best reliability (validation)"))'),
        ("code", 'card = nb.load_json(lr_dir + "/model_card.json")\nprint(card["status"])\ncard["limitations"]'),
    ],
}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--only", nargs="*", help="notebook number prefixes, for example 01 02")
    args = p.parse_args()
    out_dir = config.ROOT / "notebooks"
    out_dir.mkdir(exist_ok=True)
    for name, cells in NOTEBOOKS.items():
        if args.only and name[:2] not in args.only:
            continue
        nb = nbf.v4.new_notebook()
        nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
        nb.cells = [nbf.v4.new_markdown_cell(src) if kind == "md" else nbf.v4.new_code_cell(src) for kind, src in cells]
        nbf.write(nb, out_dir / name)
        print("wrote", out_dir / name)


if __name__ == "__main__":
    main()
