"""B2: Muse proposes feature combinations, code computes them.

Muse receives only feature names, units, one-line meanings and train-only summary statistics
(mean, std, p5, p95). Cell-constant features (latitude, elevation) are never sent or usable.
Each formula is parsed by the whitelist parser in formula.py (no eval) and rejected if it uses a
name outside the allowlist, produces NaN or inf, is constant on train or duplicates a column.
"""

from __future__ import annotations

import ast

import numpy as np
import pandas as pd

from . import formula


def usable_names(features: list[str], pcfg: dict) -> list[str]:
    return [f for f in features if f not in set(pcfg["exclude"])]


def _sig(x: float) -> float:
    return float(f"{x:.4g}")


def summary_payload(train: pd.DataFrame, names: list[str], pcfg: dict) -> dict:
    """Names, units, meanings and train-only statistics. No rows, labels, dates or places."""
    rows = []
    for n in names:
        v = train[n].to_numpy(dtype=float)
        m = pcfg["meanings"][n]
        rows.append({"name": n, "unit": m["unit"], "meaning": m["meaning"], "mean": _sig(np.mean(v)),
                     "std": _sig(np.std(v)), "p5": _sig(np.percentile(v, 5)), "p95": _sig(np.percentile(v, 95))})
    return {"features": rows, "max_new_features": pcfg["max_features"]}


def mock_proposals(payload: dict) -> dict:
    """Deterministic fake answer with the real schema; one candidate is invalid on purpose."""
    return {"features": [
        {"name": "dry_clear_cooling", "formula": "dewpoint_depression_1800_c * (1 - sky_emissivity_1800)",
         "category": "radiative_cooling", "rationale": "mock: dry air under a clear sky cools faster"},
        {"name": "calm_clear", "formula": "afternoon_clearness / (1 + wind_1800_ms)",
         "category": "wind", "rationale": "mock: clear and calm evenings favor radiative cooling"},
        {"name": "bad_name", "formula": "latitude + 1", "category": "cloud", "rationale": "mock: invalid on purpose"},
    ]}


def accept(candidates: list[dict], table: pd.DataFrame, train_mask: np.ndarray, names: list[str],
           existing: list[str]) -> tuple[dict[str, np.ndarray], list[dict]]:
    """Compute accepted candidates as muse_f1.. columns. Returns (columns, one decision row per candidate)."""
    allowed = set(names)
    cols: dict[str, np.ndarray] = {}
    rows, seen = [], set()
    for i, c in enumerate(candidates, start=1):
        row = {"candidate": i, "muse_name": c["name"], "formula": c["formula"], "category": c["category"],
               "rationale": c["rationale"], "column": None, "decision": None}
        try:
            tree = formula.parse(c["formula"], allowed)
        except formula.FormulaError as exc:
            rows.append({**row, "decision": f"rejected: {exc}"})
            continue
        canon = ast.dump(tree)
        if canon in seen:
            rows.append({**row, "decision": "rejected: duplicate formula"})
            continue
        v = formula.evaluate(tree, table)
        if not np.isfinite(v[train_mask]).all():
            rows.append({**row, "decision": "rejected: NaN or inf on train"})
            continue
        if not np.isfinite(v).all():
            rows.append({**row, "decision": "rejected: NaN or inf outside train"})
            continue
        if np.std(v[train_mask]) == 0:
            rows.append({**row, "decision": "rejected: constant on train"})
            continue
        dup = next((e for e in existing + list(cols) if np.allclose(v, table[e].to_numpy(dtype=float) if e in table
                                                                     else cols[e])), None)
        if dup:
            rows.append({**row, "decision": f"rejected: same values as {dup}"})
            continue
        seen.add(canon)
        name = f"muse_f{len(cols) + 1}"
        cols[name] = v
        rows.append({**row, "column": name, "decision": "accepted", "names_used": sorted(formula.names_used(tree))})
    return cols, rows
