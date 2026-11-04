"""Small matplotlib figures for reports and notebooks. Inputs are saved tables; nothing is fitted here."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _save(fig, path: str | Path | None):
    fig.tight_layout()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=110)
    return fig


def lines(df: pd.DataFrame, title: str, ylabel: str, path=None, marker: str | None = "o", figsize=(8, 4)):
    fig, ax = plt.subplots(figsize=figsize)
    df.plot(ax=ax, marker=marker)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    return _save(fig, path)


def barh(series: pd.Series, title: str, xlabel: str, path=None, figsize=(6, 7)):
    fig, ax = plt.subplots(figsize=figsize)
    series.iloc[::-1].plot.barh(ax=ax)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    return _save(fig, path)


def scatter(x, y, xlabel: str, ylabel: str, title: str, path=None, diagonal: bool = True):
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(x, y, s=2, alpha=0.3)
    if diagonal:
        lim = [float(np.nanmin([np.nanmin(x), np.nanmin(y)])), float(np.nanmax([np.nanmax(x), np.nanmax(y)]))]
        ax.plot(lim, lim, color="k", lw=1)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    return _save(fig, path)


def pr_curves(curves: dict[str, pd.DataFrame], base_rate: float, title: str, path=None):
    """curves: name -> DataFrame with columns recall, precision."""
    fig, ax = plt.subplots(figsize=(6, 5))
    for name, c in curves.items():
        ax.plot(c["recall"], c["precision"], label=name, lw=1.2)
    ax.axhline(base_rate, color="grey", ls="--", lw=1, label=f"base rate {base_rate:.3f}")
    ax.set_xlabel("recall")
    ax.set_ylabel("precision")
    ax.set_title(title)
    ax.legend(fontsize=7)
    return _save(fig, path)


def reliability(bins: pd.DataFrame, title: str, path=None):
    """bins: columns mean_predicted, observed_rate, count."""
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], color="k", lw=1)
    ax.plot(bins["mean_predicted"], bins["observed_rate"], marker="o")
    ax.set_xlabel("mean predicted probability")
    ax.set_ylabel("observed frost rate")
    ax.set_title(title)
    return _save(fig, path)
