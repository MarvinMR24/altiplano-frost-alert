"""11. The night table, anomaly list and cross-checks equal Part 1 in content (values, index, columns,
dtypes). File hashes can differ only through the parquet writer version stamped in the metadata."""

import pandas as pd
import pyarrow.parquet as pq

from frostwatch_ml import config
from frostwatch_ml.dataio.tables import content_sha256, read_json, sha256_of


def test_content_matches_part1():
    ref = read_json(config.ROOT / "tests" / "expected_hashes.json")["files"]
    for rel, exp in ref.items():
        df = pd.read_parquet(config.ROOT / rel)
        assert len(df) == exp["rows"], rel
        assert content_sha256(df) == exp["content_sha256"], rel
        if sha256_of(config.ROOT / rel) != exp["file_sha256"]:
            created_by = pq.read_metadata(config.ROOT / rel).created_by
            assert "parquet-cpp-arrow" in created_by, created_by


def test_manifest_hash_matches_file():
    m = read_json(config.PROCESSED / "features_manifest.json")
    assert m["features_sha256"] == sha256_of(config.PROCESSED / "features.parquet")
