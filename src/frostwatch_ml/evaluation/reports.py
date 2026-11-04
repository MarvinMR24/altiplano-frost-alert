"""Report tables: Markdown rendering and CSV / JSON / Markdown writers (atomic)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ..dataio.tables import write_csv, write_json, write_text


def md_table(df: pd.DataFrame, floatfmt: int = 3) -> str:
    """Small markdown table without extra dependencies."""
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join([df.index.name or ""] + cols) + " |",
             "|" + "---|" * (len(cols) + 1)]
    for row in df.itertuples(name=None):
        idx, vals = row[0], []
        for v in row[1:]:
            if isinstance(v, (float, np.floating)):
                vals.append("" if np.isnan(v) else f"{v:.{floatfmt}f}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join([str(idx)] + vals) + " |")
    return "\n".join(lines)


def save_table(df: pd.DataFrame, base: str | Path, floatfmt: int = 4, title: str | None = None) -> None:
    """Write `base`.csv, `base`.json (records) and `base`.md."""
    base = Path(base)
    write_csv(df, base.with_suffix(".csv"))
    write_json(df.reset_index().to_dict(orient="records"), base.with_suffix(".json"))
    text = (f"# {title}\n\n" if title else "") + md_table(df, floatfmt) + "\n"
    write_text(text, base.with_suffix(".md"))
