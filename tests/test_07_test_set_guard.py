"""7. The test split loads only through load_test_split with an explicit flag, called from
pipelines/06_final_eval.py; any other call raises. Code is searched for other access paths."""

import re

import pytest

from conftest import code_files
from frostwatch_ml import config, leakage


def test_model_rows_refuses_test(features):
    with pytest.raises(leakage.TestSetLockedError):
        leakage.model_rows(features, "test")


def test_load_test_split_refuses_without_flag_and_from_elsewhere(features):
    with pytest.raises(leakage.TestSetLockedError):
        leakage.load_test_split(features)
    with pytest.raises(leakage.TestSetLockedError):
        leakage.load_test_split(features, i_confirm_final=True)


# Files allowed to contain the literal "test" next to a split: the guard itself, the split
# definitions, descriptive Part 1 EDA (class balance and drift tables, no model), the model card
# (prints the locked test years), the manifest reader (skips the small CDS test downloads, not a
# split) and the final evaluation stub.
ALLOWED = {"src/frostwatch_ml/leakage.py", "src/frostwatch_ml/splits.py", "src/frostwatch_ml/config.py",
           "src/frostwatch_ml/eda/merged.py", "src/frostwatch_ml/artifacts/model_card.py", "src/frostwatch_ml/dataio/manifest.py",
           "pipelines/06_final_eval.py"}
TEST_LITERAL = re.compile(r"""["']test["']""")


def test_code_search_for_test_access():
    calls = {str(p.relative_to(config.ROOT)) for p in code_files() if "load_test_split(" in p.read_text()}
    assert calls <= {"src/frostwatch_ml/leakage.py", "pipelines/06_final_eval.py"}, calls
    literal = {str(p.relative_to(config.ROOT)) for p in code_files() if TEST_LITERAL.search(p.read_text())}
    assert literal <= ALLOWED, sorted(literal - ALLOWED)
