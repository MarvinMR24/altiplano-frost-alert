"""Whole-year chronological split of the night table. Never random.

Train 1985-2009, validation 2010-2017, test 2018-2025, out_of_sample_check 2026 (configs/frost.yaml).
"""

from __future__ import annotations

import pandas as pd


def split_of(year: int, split_cfg: dict) -> str | None:
    for name, (lo, hi) in split_cfg.items():
        if lo <= year <= hi:
            return name
    return None


def assign(nights: pd.Series, split_cfg: dict) -> list[str | None]:
    """Split name for every night date, from its calendar year."""
    return [split_of(y, split_cfg) for y in nights.dt.year]


def assert_integrity(df: pd.DataFrame, split_cfg: dict) -> None:
    """Years disjoint and ordered train < validation < test < out_of_sample_check; every row assigned;
    the split of each row equals the one implied by its year."""
    ranges = [tuple(split_cfg[k]) for k in ("train", "validation", "test", "out_of_sample_check")]
    for (lo1, hi1), (lo2, hi2) in zip(ranges, ranges[1:], strict=False):
        assert lo1 <= hi1 < lo2 <= hi2, "split years overlap or are out of order"
    assert df["split"].notna().all(), "rows without split"
    expected = assign(df["night_date"], split_cfg)
    assert (df["split"].to_numpy() == pd.Series(expected).to_numpy()).all(), "split does not match year"
    years = df.groupby("split")["night_date"].agg(lambda s: set(s.dt.year))
    names = list(years.index)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            assert not (years[a] & years[b]), f"years shared by {a} and {b}"
