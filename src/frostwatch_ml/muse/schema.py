"""Strict validation of Muse JSON responses. Invalid items are reported, never repaired."""

from __future__ import annotations

import math
import re

ACTIONS = ("keep", "correct")
CATEGORIES = ("radiative_cooling", "humidity_deficit", "wind", "cloud")
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,48}$")


def _number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def validate_review(parsed: dict | None, ids: list[str]) -> tuple[dict[str, dict], list[str]]:
    """Items of an anomaly review response keyed by record id, plus the list of problems found."""
    errors: list[str] = []
    if not isinstance(parsed, dict) or not isinstance(parsed.get("records"), list):
        return {}, ["response is not an object with a 'records' list"]
    wanted = set(ids)
    out: dict[str, dict] = {}
    for i, item in enumerate(parsed["records"]):
        if not isinstance(item, dict):
            errors.append(f"item {i}: not an object")
            continue
        rid = item.get("id")
        if rid not in wanted:
            errors.append(f"item {i}: unknown id {rid!r}")
            continue
        if rid in out:
            errors.append(f"{rid}: duplicate, first kept")
            continue
        problems = []
        if item.get("action") not in ACTIONS:
            problems.append("action")
        if not _number(item.get("value")):
            problems.append("value")
        c = item.get("confidence")
        if not (_number(c) and 0 <= c <= 1):
            problems.append("confidence")
        if not isinstance(item.get("reason"), str):
            problems.append("reason")
        if problems:
            errors.append(f"{rid}: invalid {', '.join(problems)}")
            continue
        out[rid] = {"action": item["action"], "value": float(item["value"]), "confidence": float(c),
                    "reason": item["reason"][:300]}
    missing = wanted - set(out) - {e.split(":")[0] for e in errors}
    errors += [f"{rid}: missing in response" for rid in sorted(missing)]
    return out, errors


def validate_proposals(parsed: dict | None, max_n: int) -> tuple[list[dict], list[str]]:
    """Candidate features of a proposal response (at most max_n), plus the problems found."""
    if not isinstance(parsed, dict) or not isinstance(parsed.get("features"), list):
        return [], ["response is not an object with a 'features' list"]
    out, errors = [], []
    for i, item in enumerate(parsed["features"]):
        if len(out) >= max_n:
            errors.append(f"item {i}: over the limit of {max_n}, ignored")
            continue
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in ("name", "formula", "rationale")):
            errors.append(f"item {i}: missing name, formula or rationale")
            continue
        out.append({"name": item["name"][:50], "formula": item["formula"][:400],
                    "category": item.get("category") if item.get("category") in CATEGORIES else "other",
                    "rationale": item["rationale"][:300], "valid_name": bool(NAME_RE.match(item["name"]))})
    return out, errors
