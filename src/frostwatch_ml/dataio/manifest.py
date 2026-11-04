"""Read and verify the CDS download manifest (data/raw/cds/manifest.json). Read-only."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .. import config
from .tables import read_json, sha256_of


def manifest_entries() -> dict[tuple[str, str, str], dict[str, Any]]:
    """Complete, non-test entries keyed by (dataset, point, use), with an absolute `path`."""
    files = read_json(config.RAW_MANIFEST)["files"]
    out = {}
    for key, rec in files.items():
        if rec.get("status") != "complete" or rec.get("use", "").startswith("test"):
            continue
        out[(rec["dataset_name"], rec["point_id"], rec["use"])] = dict(rec, path=config.ROOT / key)
    return out


def verify_manifest(check_hashes: bool = True) -> list[dict[str, Any]]:
    """Check that every complete entry exists with the recorded size (and sha256). Returns one row per file."""
    rows = []
    for (ds, pid, use), rec in manifest_entries().items():
        path = Path(rec["path"])
        exists = path.exists()
        size_ok = exists and path.stat().st_size == rec["file_size_bytes"]
        sha_ok = size_ok and (not check_hashes or sha256_of(path) == rec["sha256"])
        rows.append({"dataset": ds, "point_id": pid, "use": use, "exists": exists, "size_ok": size_ok, "sha_ok": sha_ok})
    return rows
