"""Decision threshold selection. Uses VALIDATION arrays only (the argument names make it explicit)."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import precision_recall_curve


def best_f2_threshold(y_val, score_val) -> tuple[float, float]:
    """Threshold on validation scores that maximizes F2 (predict frost when score >= threshold)."""
    y_val = np.asarray(y_val, dtype=int)
    precision, recall, thr = precision_recall_curve(y_val, np.asarray(score_val, dtype=float))
    p, r = precision[:-1], recall[:-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        f2 = np.where(4 * p + r > 0, 5 * p * r / (4 * p + r), 0.0)
    i = int(np.argmax(f2))
    return float(thr[i]), float(f2[i])


def reliability_bins(y_val, prob_val, n_bins: int = 10) -> list[dict]:
    """Equal-width probability bins on validation: count, mean predicted, observed frost rate."""
    y_val = np.asarray(y_val, dtype=float)
    prob_val = np.asarray(prob_val, dtype=float)
    edges = np.linspace(0, 1, n_bins + 1)
    idx = np.clip(np.digitize(prob_val, edges[1:-1]), 0, n_bins - 1)
    out = []
    for b in range(n_bins):
        m = idx == b
        out.append({"bin": b, "lower": float(edges[b]), "upper": float(edges[b + 1]), "count": int(m.sum()),
                    "mean_predicted": float(prob_val[m].mean()) if m.any() else None,
                    "observed_rate": float(y_val[m].mean()) if m.any() else None})
    return out
