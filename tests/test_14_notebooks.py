"""14. Notebooks contain no fitting, no splitting, no writes outside figures/ and reports/, and import
only frostwatch_ml."""

import subprocess
import sys

from frostwatch_ml import config


def test_check_notebooks():
    r = subprocess.run([sys.executable, str(config.ROOT / "tools" / "check_notebooks.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
