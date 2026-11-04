"""Read-only helpers for the presentation notebooks. Notebooks import only this package: they load
saved outputs (tables, JSON, figures) and plot them. Nothing here fits a model or writes data."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .. import config
from . import plots  # noqa: F401  (re-exported for notebooks)

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)


def path(relpath: str) -> Path:
    return config.ROOT / relpath


def csv(relpath: str, index_col=0) -> pd.DataFrame:
    return pd.read_csv(path(relpath), index_col=index_col)


def parquet(relpath: str) -> pd.DataFrame:
    return pd.read_parquet(path(relpath))


def load_json(relpath: str):
    return json.loads(path(relpath).read_text())


def markdown(relpath: str) -> str:
    return path(relpath).read_text()


def show_figure(relpath: str):
    """Display a saved PNG inside a notebook."""
    from IPython.display import Image
    return Image(filename=str(path(relpath)))


def show_markdown(text: str):
    from IPython.display import Markdown
    return Markdown(text)


def latest_model_dir(prefix: str) -> str:
    """reports/<model_version> folder of the newest version with the given model prefix."""
    dirs = sorted(p.name for p in config.REPORTS.glob(f"{prefix}-*") if p.is_dir())
    if not dirs:
        raise FileNotFoundError(f"no reports/{prefix}-* folder")
    return f"reports/{dirs[-1]}"


def figure(fig):
    """Render a matplotlib figure as an embedded PNG (works with the Agg backend)."""
    import io

    import matplotlib.pyplot as plt
    from IPython.display import Image
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    return Image(data=buf.getvalue())
