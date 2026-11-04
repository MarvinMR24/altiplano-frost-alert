"""Shared argparse options for the thin pipeline scripts."""

from __future__ import annotations

import argparse

from . import config
from .tracking.dvc_sync import sync


def parser(description: str, default_config: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--config", default=default_config, help="YAML config relative to the project root")
    p.add_argument("--seed", type=int, default=config.SEED)
    p.add_argument("--dry-run", action="store_true", help="check inputs and print the plan, write nothing")
    p.add_argument("--no-sync", action="store_true", help="skip dvc status / push / status -c at the end")
    return p


def finish(stage: str, args: argparse.Namespace) -> None:
    """End-of-script sync (non-fatal). Skipped on --dry-run or --no-sync, and when DVC runs the script
    inside `dvc repro` (DVC holds its lock then; the Makefile `sync` target pushes afterwards)."""
    import os
    if args.dry_run or args.no_sync or os.environ.get("DVC_STAGE") or os.environ.get("FROSTWATCH_IN_REPRO"):
        return
    result = sync(stage)
    print("sync:", result.get("failed", "ok"), [s["tail"] for s in result.get("steps", [])])
