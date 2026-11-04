"""Automatic, non-fatal DVC sync: `dvc status`, `dvc push`, `dvc status -c`, one attempt each.

On an auth error (401 or 403) or no network nothing is retried; the result is reported once and the
exact commands are returned so they can be run by hand. Output is scanned so credentials never
reach logs (DVC does not print them; this is a second guard).
"""

from __future__ import annotations

import re
import shutil
import subprocess

from .. import config

COMMANDS = [["dvc", "status"], ["dvc", "push"], ["dvc", "status", "-c"]]
_AUTH = re.compile(r"\b(401|403)\b|unauthori[sz]ed|forbidden", re.I)
_NET = re.compile(r"name or service not known|could not resolve|connection (refused|reset|error)|timed out|network", re.I)


def _clean(text: str) -> str:
    return re.sub(r"(https?://)[^/@\s]+@", r"\1***@", text)[-1500:]


def sync(stage: str, enabled: bool = True) -> dict:
    """Run the three commands once. Never raises; returns a summary dict."""
    log = config.get_logger("dvc_sync")
    if not enabled:
        return {"stage": stage, "skipped": "--no-sync"}
    if shutil.which("dvc") is None:
        config.log_event(log, "dvc not installed, sync skipped", stage=stage)
        return {"stage": stage, "skipped": "dvc not installed", "manual": [" ".join(c) for c in COMMANDS]}
    out = {"stage": stage, "steps": []}
    for cmd in COMMANDS:
        r = subprocess.run(cmd, cwd=config.ROOT, capture_output=True, text=True)
        text = _clean((r.stdout or "") + (r.stderr or ""))
        step = {"cmd": " ".join(cmd), "returncode": r.returncode, "tail": text.strip().splitlines()[-1:] }
        out["steps"].append(step)
        if r.returncode != 0:
            kind = "auth" if _AUTH.search(text) else "network" if _NET.search(text) else "error"
            out["failed"] = kind
            out["manual"] = [" ".join(c) for c in COMMANDS]
            config.log_event(log, "dvc sync failed, continuing locally", stage=stage, cmd=step["cmd"], kind=kind)
            break
    else:
        config.log_event(log, "dvc sync ok", stage=stage, last=out["steps"][-1]["tail"])
    return out
