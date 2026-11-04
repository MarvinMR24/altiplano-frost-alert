"""6. Whole-year chronological split: disjoint ordered years, counts add up, 2026 only as
out_of_sample_check, and no row-level random split anywhere in the code."""

import re

from conftest import code_files
from frostwatch_ml import splits


def test_split_integrity(features, frost_cfg):
    splits.assert_integrity(features, frost_cfg["split"])
    years = features.groupby("split")["night_date"].agg(lambda s: (s.dt.year.min(), s.dt.year.max()))
    assert years["train"][1] < years["validation"][0] <= years["validation"][1] < years["test"][0]
    assert years["test"][1] < years["out_of_sample_check"][0]
    assert features["split"].value_counts().sum() == len(features)
    y2026 = features[features["night_date"].dt.year == 2026]
    assert (y2026["split"] == "out_of_sample_check").all()
    assert not (features.loc[features["split"] != "out_of_sample_check", "night_date"].dt.year >= 2026).any()


RANDOM_SPLIT = re.compile(r"train_test_split|(?<!Group)KFold\(|StratifiedKFold|ShuffleSplit|shuffle\s*=\s*True|\.sample\(\s*frac")


def test_no_random_split_in_code():
    # tools/check_notebooks.py names these patterns in order to forbid them.
    files = [p for p in code_files() if p.name != "check_notebooks.py"]
    hits = [f"{p}:{i}" for p in files for i, line in enumerate(p.read_text().splitlines(), 1)
            if RANDOM_SPLIT.search(line) and "RANDOM_SPLIT" not in line]
    assert not hits, hits
