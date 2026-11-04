"""Atomic, idempotent file writes (temp file then rename) and hashing."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd


def sha256_of(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _atomic(path: Path, write) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    os.close(fd)
    try:
        write(Path(tmp))
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return path


def write_parquet(df: pd.DataFrame, path: str | Path) -> Path:
    return _atomic(Path(path), lambda t: df.to_parquet(t, index=False))


def read_parquet(path: str | Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def write_csv(df: pd.DataFrame, path: str | Path, index: bool = True) -> Path:
    return _atomic(Path(path), lambda t: df.to_csv(t, index=index))


def write_json(obj: Any, path: str | Path) -> Path:
    return _atomic(Path(path), lambda t: t.write_text(json.dumps(obj, indent=2, default=str)))


def write_text(text: str, path: str | Path) -> Path:
    return _atomic(Path(path), lambda t: t.write_text(text))


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text())


def content_sha256(df: pd.DataFrame) -> str:
    """Hash of the values, index, column names and dtypes (independent of the parquet writer version)."""
    h = hashlib.sha256(pd.util.hash_pandas_object(df, index=True).values.tobytes())
    h.update(repr(list(df.columns)).encode())
    h.update(repr([str(t) for t in df.dtypes]).encode())
    return h.hexdigest()
