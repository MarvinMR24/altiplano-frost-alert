"""Classification metrics at a fixed threshold. Pure functions of (y, score, threshold)."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

METRIC_EXPLANATIONS = {
    "accuracy": "Share of nights classified correctly; misleading alone because frost nights are a minority.",
    "majority_class_accuracy": "Accuracy of always predicting the most frequent class in the same rows; accuracy must beat it.",
    "precision": "Of the nights flagged as frost, the share that had frost (few false alarms means high precision).",
    "recall": "Of the nights with frost, the share that was flagged (few missed frosts means high recall).",
    "f1": "Harmonic mean of precision and recall.",
    "f2": "Like F1 but weights recall four times more than precision, because a missed frost costs more than a false alarm.",
    "roc_auc": "Probability that a random frost night gets a higher score than a random non-frost night (0.5 is chance).",
    "pr_auc": "Average precision over all thresholds; its chance level is the base rate, so it is informative for rare events.",
    "brier": "Mean squared error of the predicted probability (lower is better); defined only for probability scores.",
}


def _counts(y, pred):
    tp = int(np.sum((pred == 1) & (y == 1)))
    fp = int(np.sum((pred == 1) & (y == 0)))
    fn = int(np.sum((pred == 0) & (y == 1)))
    tn = int(np.sum((pred == 0) & (y == 0)))
    return tp, fp, fn, tn


def metrics_at(y, score, threshold: float, is_probability: bool) -> dict[str, float]:
    """All metrics for one set of rows; `pred = score >= threshold`."""
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    pred = (score >= threshold).astype(int)
    tp, fp, fn, tn = _counts(y, pred)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    f2 = 5 * precision * recall / (4 * precision + recall) if precision + recall else 0.0
    rate = float(y.mean())
    both = 0 < y.sum() < len(y)
    return {
        "n": int(len(y)),
        "base_rate": rate,
        "threshold": float(threshold),
        "accuracy": (tp + tn) / len(y),
        "majority_class_accuracy": max(rate, 1 - rate),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "f2": f2,
        "roc_auc": float(roc_auc_score(y, score)) if both else float("nan"),
        "pr_auc": float(average_precision_score(y, score)) if both else float("nan"),
        "brier": float(brier_score_loss(y, np.clip(score, 0, 1))) if is_probability else float("nan"),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }
