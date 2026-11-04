"""Token and cost accounting for Muse calls. Prices come from configs/muse.yaml (marked "verify")."""

from __future__ import annotations

import json
import math
from pathlib import Path

EXPERIMENT_TAG = "muse_ab"


def estimate_tokens(text: str, chars_per_token: float = 4.0) -> int:
    """Rough token count for planning only (no tokenizer for Muse is available locally)."""
    return int(math.ceil(len(text) / chars_per_token))


def cost_usd(prompt_tokens: int, completion_tokens: int, budget: dict) -> float:
    return (prompt_tokens * budget["price_input_per_m_usd"] + completion_tokens * budget["price_output_per_m_usd"]) / 1e6


def read_usage(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    out = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def spent_usd(entries: list[dict], tag: str = EXPERIMENT_TAG) -> float:
    """Estimated spend of real API calls with this experiment tag."""
    return float(sum(e.get("est_cost_usd", 0.0) for e in entries if e.get("experiment") == tag))


def summarize(entries: list[dict]) -> dict:
    """Totals per purpose over real API calls (cache hits and mock calls are never logged)."""
    by: dict[str, dict] = {}
    for e in entries:
        s = by.setdefault(e.get("purpose", "unknown"), {"calls": 0, "ok": 0, "failed": 0, "invalid_json": 0,
                                                       "prompt_tokens": 0, "completion_tokens": 0, "est_cost_usd": 0.0})
        s["calls"] += 1
        s[e.get("status", "failed")] = s.get(e.get("status", "failed"), 0) + 1
        s["prompt_tokens"] += int(e.get("prompt_tokens") or 0)
        s["completion_tokens"] += int(e.get("completion_tokens") or 0)
        s["est_cost_usd"] += float(e.get("est_cost_usd") or 0.0)
    total = {k: sum(v[k] for v in by.values()) for k in ("calls", "prompt_tokens", "completion_tokens", "est_cost_usd")}
    return {"by_purpose": by, "total": total}
