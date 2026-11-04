"""Check that notebooks only present results: no fit(, no train_test_split, no writes outside
figures/ and reports/, and imports only from frostwatch_ml. Exit code 1 on any violation."""

import re
import sys
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = [re.compile(p) for p in (r"\.fit\(", r"\bfit\(", r"train_test_split")]
WRITES = re.compile(r"\.(to_csv|to_parquet|to_json|savefig|write_text|write_bytes)\(|open\([^)]*['\"][wa]")
IMPORT = re.compile(r"^\s*(import|from)\s+([\w.]+)")


def check(path: Path) -> list[str]:
    errors = []
    nb = nbformat.read(path, as_version=4)
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        for line in cell.source.splitlines():
            for pat in FORBIDDEN:
                if pat.search(line):
                    errors.append(f"{path.name} cell {i}: forbidden {pat.pattern!r}: {line.strip()}")
            if WRITES.search(line) and not re.search(r"(figures|reports)/", line):
                errors.append(f"{path.name} cell {i}: write outside figures/ or reports/: {line.strip()}")
            m = IMPORT.match(line)
            if m and not m.group(2).startswith("frostwatch_ml"):
                errors.append(f"{path.name} cell {i}: import outside frostwatch_ml: {line.strip()}")
    return errors


def main() -> int:
    errors = [e for p in sorted((ROOT / "notebooks").glob("*.ipynb")) for e in check(p)]
    print("\n".join(errors) if errors else "notebooks ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
