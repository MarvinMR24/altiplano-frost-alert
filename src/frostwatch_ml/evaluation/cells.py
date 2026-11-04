"""Per-cell and macro-averaged metrics, and skill against reference baselines.

Base rates differ a lot between cells, so every model is reported pooled, per cell (at the model's
single validation threshold) and as the unweighted mean over the 8 cells (macro).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import metrics_at

MAIN = ["accuracy", "majority_class_accuracy", "precision", "recall", "f1", "f2", "roc_auc", "pr_auc", "brier"]


def per_cell(rows: pd.DataFrame, y, score, threshold: float, is_probability: bool) -> pd.DataFrame:
    y = np.asarray(y)
    score = np.asarray(score)
    out = []
    for pid in sorted(rows["point_id"].unique()):
        m = (rows["point_id"] == pid).to_numpy()
        out.append({"point_id": pid, **metrics_at(y[m], score[m], threshold, is_probability)})
    return pd.DataFrame(out).set_index("point_id")


def macro(cells: pd.DataFrame) -> dict[str, float]:
    return {k: float(cells[k].mean()) for k in MAIN + ["base_rate"]}


def skill(table: pd.DataFrame, references=("climatology", "persistence")) -> pd.DataFrame:
    """Difference in PR-AUC and F2 against the best reference baseline (per metric), and the Brier
    skill score against climatology: 1 - Brier / Brier_climatology. `table` is indexed by model name."""
    best_pr = table.loc[list(references), "pr_auc"].max()
    best_f2 = table.loc[list(references), "f2"].max()
    brier_clim = table.loc["climatology", "brier"]
    return pd.DataFrame({
        "pr_auc": table["pr_auc"],
        "pr_auc_minus_best_baseline": table["pr_auc"] - best_pr,
        "f2": table["f2"],
        "f2_minus_best_baseline": table["f2"] - best_f2,
        "brier_skill_vs_climatology": 1 - table["brier"] / brier_clim,
    })
