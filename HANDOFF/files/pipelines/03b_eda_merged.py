"""EDA of the night table: class balance, missing values, drift by split, label correlations
(training years only), the cloud / sky emissivity sign check and label agreement with AgERA5.

Writes docs/eda_merged.md, figures in docs/figures/ and summary tables in
data/processed/eda_merged/. Stops with an error if the sign check fails.

Run: .venv/bin/python pipelines/03b_eda_merged.py
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as c

OUT_DIR = c.PROCESSED / "eda_merged"
DOC = c.ROOT / "docs" / "eda_merged.md"
SPLITS = ["train", "validation", "test", "out_of_sample_check"]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    c.FIGURES.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((c.PROCESSED / "features_manifest.json").read_text())
    feats = manifest["feature_columns"]
    df = pd.read_parquet(c.PROCESSED / "features.parquet")
    xc = pd.read_parquet(c.PROCESSED / "crosschecks.parquet")
    lab = df[df["frost"].notna()].copy()
    lab["frost"] = lab["frost"].astype(float)
    lab["year"] = lab["night_date"].dt.year
    lab["month"] = lab["night_date"].dt.month

    balance = lab.groupby("split").agg(rows=("frost", "size"), frost_nights=("frost", "sum"), frost_rate=("frost", "mean"))
    balance["majority_class_accuracy"] = np.maximum(balance["frost_rate"], 1 - balance["frost_rate"])
    balance = balance.reindex(SPLITS)
    by_cell = lab.pivot_table(index="point_id", columns="split", values="frost", aggfunc="mean")[SPLITS]
    by_month = lab[lab["split"] == "train"].pivot_table(index="month", columns="point_id", values="frost", aggfunc="mean")
    by_year = lab.groupby("year")["frost"].mean().to_frame("frost_rate")
    missing = df[feats + ["frost", "tmin_c"]].isna().groupby(df["split"]).sum().T[SPLITS]
    missing = missing[missing.sum(axis=1) > 0]

    train = lab[lab["split"] == "train"]
    mu, sd = train[feats].mean(), train[feats].std()
    drift = pd.DataFrame({s: (lab.loc[lab["split"] == s, feats].mean() - mu) / sd for s in SPLITS})
    drift.index.name = "feature"
    means = pd.DataFrame({s: lab.loc[lab["split"] == s, feats].mean() for s in SPLITS})
    means.index.name = "feature"
    corr = train[feats].corrwith(train["frost"]).sort_values(key=np.abs, ascending=False).to_frame("corr_with_frost_train")
    corr.index.name = "feature"

    sign_corr = float(train["cloud_cover_prev_day"].corr(train["sky_emissivity_1800"]))
    sign_by_cell = train.groupby("point_id")[["cloud_cover_prev_day", "sky_emissivity_1800"]].corr().xs("sky_emissivity_1800", level=1)["cloud_cover_prev_day"]

    m = lab.merge(xc, on=["point_id", "night_date"], how="left")
    m = m[m["split"].isin(["train", "validation", "test"])].dropna(subset=["agera5_tmin_night_c"])
    ag_frost = m["agera5_tmin_night_c"] <= 0
    agreement = pd.DataFrame({
        "nights": m.groupby("point_id").size(),
        "agreement": (ag_frost == (m["frost"] == 1)).groupby(m["point_id"]).mean(),
        "label_frost_rate": m.groupby("point_id")["frost"].mean(),
        "agera5_frost_rate": ag_frost.groupby(m["point_id"]).mean(),
        "corr_tmin": m.groupby("point_id")[["tmin_c", "agera5_tmin_night_c"]].corr().xs("tmin_c", level=1)["agera5_tmin_night_c"],
    })
    agreement.index.name = "point_id"
    confusion = pd.crosstab(m["frost"].astype(int).rename("label_frost"), ag_frost.astype(int).rename("agera5_frost"))
    overall_agreement = float((ag_frost == (m["frost"] == 1)).mean())

    for name, t in [("class_balance", balance), ("frost_by_cell_split", by_cell), ("frost_by_month_train", by_month),
                    ("frost_by_year", by_year), ("missing", missing), ("drift_std_mean_diff", drift),
                    ("feature_means_by_split", means), ("corr_with_label_train", corr), ("label_vs_agera5", agreement)]:
        t.to_csv(OUT_DIR / f"{name}.csv")

    fig, ax = plt.subplots(figsize=(9, 4))
    by_year.plot(ax=ax, legend=False, marker="o")
    for s, (lo, hi) in manifest["split_definition"].items():
        ax.axvspan(lo - 0.5, hi + 0.5, alpha=0.08, color={"train": "C0", "validation": "C1", "test": "C2", "out_of_sample_check": "C3"}[s])
    ax.set_ylabel("frost night rate (8 cells)"); ax.set_title("Frost night rate by year with the chronological splits")
    fig.tight_layout(); fig.savefig(c.FIGURES / "merged_frost_rate_by_year.png", dpi=120); plt.close(fig)
    fig, ax = plt.subplots(figsize=(6, 7))
    corr["corr_with_frost_train"].iloc[::-1].plot.barh(ax=ax)
    ax.set_xlabel("Pearson correlation with frost (train 1985-2009)")
    fig.tight_layout(); fig.savefig(c.FIGURES / "merged_corr_with_label_train.png", dpi=120); plt.close(fig)

    summary = {
        "class_balance": balance.round(6).to_dict(orient="index"),
        "sign_check_corr_cloud_prev_vs_emissivity_train": sign_corr,
        "sign_check_by_cell": sign_by_cell.to_dict(),
        "label_vs_agera5_agreement_overall": overall_agreement,
        "confusion_label_vs_agera5": {f"label_{i}": {f"agera5_{j}": int(confusion.loc[i, j]) for j in confusion.columns} for i in confusion.index},
    }
    c.write_json(OUT_DIR / "summary.json", summary)
    write_doc(balance, by_cell, by_month, missing, drift, corr, sign_corr, sign_by_cell, agreement, confusion, overall_agreement)
    print(balance.round(4).to_string())
    print("sign check corr:", round(sign_corr, 4), "by cell:", sign_by_cell.round(3).to_dict())
    print("label vs agera5 agreement:", round(overall_agreement, 4))
    if not sign_corr > 0:
        raise SystemExit("sign check failed: cloud_cover_prev_day vs sky_emissivity_1800 is not positive; check the date alignment")


def write_doc(balance, by_cell, by_month, missing, drift, corr, sign_corr, sign_by_cell, agreement, confusion, overall):
    lines = [
        "# EDA: night table",
        "",
        "Generated by `pipelines/03b_eda_merged.py` from `data/processed/features.parquet`. One row per cell and night D (local date of the 18:00 snapshot). Labels come from the same ERA5-Land reanalysis as the features (grid frost, not station frost).",
        "",
        "## Class balance by split",
        "majority_class_accuracy is the accuracy of always predicting the most frequent class; any model must beat it.",
        "",
        c.md_table(balance, 4),
        "",
        "The out_of_sample_check rows (2026) are reported for information only; they never enter training, validation, test or any training statistic.",
        "",
        "### Frost rate by cell and split",
        c.md_table(by_cell, 3),
        "",
        "### Frost rate by month (train)",
        c.md_table(by_month, 3),
        "",
        "![frost rate by year](figures/merged_frost_rate_by_year.png)",
        "",
        "## Missing values",
        ("No missing values in features or labels." if missing.empty else c.md_table(missing, 0)),
        "",
        "## Drift by split",
        "Mean of each split minus the training mean, divided by the training standard deviation.",
        "",
        c.md_table(drift, 3),
        "",
        "## Correlation with the label (training years only)",
        c.md_table(corr, 3),
        "",
        "![correlation with label](figures/merged_corr_with_label_train.png)",
        "",
        "## Sign check: cloud_cover_prev_day vs sky_emissivity_1800",
        f"Pearson correlation on training rows: {sign_corr:.4f} ({'positive, as expected' if sign_corr > 0 else 'NOT positive'}). A cloudier previous day should go with a more emissive sky at 18:00 on average; a negative sign would point to a date misalignment.",
        "",
        c.md_table(sign_by_cell.to_frame("corr_train"), 3),
        "",
        "## Label vs AgERA5 night minimum (train, validation and test nights)",
        "The AgERA5 night-time minimum for night D is the value dated D+1 (18:00 local of D to 06:00 local of D+1). It is a cross-check only, never a feature. The window is 3 hours shorter than the label window (which ends at 09:00 local), and the products differ, so perfect agreement is not expected.",
        "",
        c.md_table(agreement, 3),
        "",
        f"Overall agreement: {overall:.4f}. Confusion (rows: label, columns: AgERA5 frost flag):",
        "",
        c.md_table(confusion, 0),
        "",
        "## Limitations",
        "- Labels are computed from the same reanalysis as the features: the model predicts grid frost, which is smoother than frost at a station or in a cold hollow.",
        "- ERA5-Land cells are 0.1 degree (about 9 km). Local terrain, cold air pooling and crop-level temperatures are not resolved.",
        "- AgERA5 is a different product with its own 0.1 degree grid. For these 8 points the returned AgERA5 point coincides with the ERA5-Land cell, but in general it can be offset by up to about 7 km.",
        "- The cloud proxy is lagged: cloud_cover_prev_day is the mean of the previous local day, because the same-day value includes hours after 18:00.",
        "- Frost rates trend down over 1985-2025, so the chronological splits have different base rates.",
        "- No confidence intervals are computed.",
        "",
    ]
    DOC.write_text("\n".join(lines))


if __name__ == "__main__":
    main()
