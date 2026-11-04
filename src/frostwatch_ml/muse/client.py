"""Meta Model API client for Muse Spark (OpenAI-compatible chat completions).

- Keys come from the environment only (META_API_KEY, META_API_BASE_URL); they are never logged.
- MUSE_MOCK=1 (the default unless MUSE_MOCK=0) returns a deterministic fake response from a
  caller-supplied function and makes no network call.
- Every response is cached by the SHA-256 of the request body in logs/muse_cache/ (mock responses
  in logs/muse_cache/mock/). Re-runs read from the cache; the cache is the source of truth.
- Real calls append token usage to logs/muse_usage.jsonl. One attempt per call, no retries.
- Before each real call the worst-case cost (estimated input plus max_tokens output) is checked
  against the experiment cap; the run stops with BudgetExceeded if it would pass it.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import config
from . import costs

CACHE_DIR = config.ROOT / "logs" / "muse_cache"
USAGE_LOG = config.ROOT / "logs" / "muse_usage.jsonl"


class BudgetExceeded(RuntimeError):
    """Raised before a real call that could push the experiment past its cap."""


def mock_enabled() -> bool:
    return os.environ.get("MUSE_MOCK", "1") != "0"


@dataclass
class CallResult:
    status: str                 # ok | invalid_json | failed
    source: str                 # api | cache | mock | mock_cache
    parsed: dict | None
    content: str | None
    usage: dict
    cache_key: str
    error: str | None = None


@dataclass
class CallStats:
    api_calls: int = 0
    cache_hits: int = 0
    mock_calls: int = 0
    failed: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    est_cost_usd: float = 0.0
    log: list = field(default_factory=list)


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _urllib_transport(url: str, headers: dict, body: bytes, timeout: float) -> dict:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (URL from the environment)
        return json.loads(r.read().decode("utf-8"))


def _parse_json(content: str | None) -> dict | None:
    if not content:
        return None
    try:
        obj = json.loads(content)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


class MuseClient:
    def __init__(self, cfg: dict, *, mock: bool | None = None, cache_dir: Path = CACHE_DIR, usage_log: Path = USAGE_LOG,
                 transport: Callable[[str, dict, bytes, float], dict] | None = None, verbose: bool = False):
        self.cfg = cfg
        self.mock = mock_enabled() if mock is None else mock
        self.cache_dir = Path(cache_dir)
        self.usage_log = Path(usage_log)
        self.transport = transport or _urllib_transport
        self.model = os.environ.get("MUSE_MODEL", cfg["model"])
        self.max_tokens = int(os.environ.get("MUSE_MAX_TOKENS", cfg["max_tokens"]))
        self.stats = CallStats()
        self.verbose = verbose

    def _say(self, msg: str) -> None:
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", file=sys.stdout, flush=True)

    def _totals(self) -> str:
        s = self.stats
        return (f"run totals: {s.api_calls} api, {s.cache_hits} cache, {s.mock_calls} mock, {s.failed} failed, "
                f"{s.prompt_tokens} in, {s.completion_tokens} out, {s.est_cost_usd:.4f} USD")

    def body(self, system: str, user: str) -> dict:
        return {"model": self.model, "temperature": self.cfg["temperature"], "max_tokens": self.max_tokens,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}

    @staticmethod
    def cache_key(body: dict) -> str:
        return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    def _cache_path(self, key: str) -> Path:
        return (self.cache_dir / "mock" if self.mock else self.cache_dir) / f"{key}.json"

    def worst_case_usd(self, body: dict) -> float:
        b = self.cfg["budget"]
        text = "".join(m["content"] for m in body["messages"])
        return costs.cost_usd(costs.estimate_tokens(text, b["chars_per_token_estimate"]), self.max_tokens, b)

    def call(self, purpose: str, prompt_version: str, system: str, user_payload: dict,
             mock_fn: Callable[[dict], dict]) -> CallResult:
        user = json.dumps(user_payload, ensure_ascii=False, separators=(",", ":"))
        body = self.body(system, user)
        key = self.cache_key(body)
        path = self._cache_path(key)
        if path.exists():
            entry = json.loads(path.read_text())
            self.stats.cache_hits += 1
            self._say(f"  {purpose}: cache hit ({entry['status']}) | {self._totals()}")
            return CallResult(entry["status"], "mock_cache" if self.mock else "cache", _parse_json(entry["content"]),
                              entry["content"], entry.get("usage", {}), key)
        if self.mock:
            content = json.dumps(mock_fn(user_payload))
            b = self.cfg["budget"]
            usage = {"prompt_tokens": costs.estimate_tokens(system + user, b["chars_per_token_estimate"]),
                     "completion_tokens": costs.estimate_tokens(content, b["chars_per_token_estimate"]), "estimated": True}
            self._write_cache(path, key, purpose, prompt_version, body, None, content, usage, "ok")
            self.stats.mock_calls += 1
            self._say(f"  {purpose}: mock answer | {self._totals()}")
            return CallResult("ok", "mock", _parse_json(content), content, usage, key)
        return self._real_call(purpose, prompt_version, body, key, path)

    def _real_call(self, purpose: str, prompt_version: str, body: dict, key: str, path: Path) -> CallResult:
        cap = self.cfg["budget"]["experiment_cap_usd"]
        spent = costs.spent_usd(costs.read_usage(self.usage_log))
        worst = self.worst_case_usd(body)
        if spent + worst > cap:
            raise BudgetExceeded(f"spent {spent:.4f} + worst case {worst:.4f} USD would exceed the cap of {cap} USD")
        api_key = os.environ.get("META_API_KEY")
        base = os.environ.get("META_API_BASE_URL")
        if not api_key or not base:
            return self._failed(purpose, prompt_version, key, "META_API_KEY or META_API_BASE_URL not set", 0.0)
        url = base.rstrip("/") + "/chat/completions"
        self._say(f"  {purpose}: calling {self.model} (max_tokens {self.max_tokens}, worst case {worst:.4f} USD, "
                  f"experiment spent so far {spent:.4f} of {cap} USD)...")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        t0 = time.monotonic()
        try:
            raw = self.transport(url, headers, json.dumps(body).encode("utf-8"), float(self.cfg["timeout_s"]))
        except urllib.error.HTTPError as exc:
            return self._failed(purpose, prompt_version, key, f"HTTP {exc.code}", time.monotonic() - t0)
        except Exception as exc:  # network, timeout, bad JSON envelope: logged, skipped, never retried
            return self._failed(purpose, prompt_version, key, type(exc).__name__, time.monotonic() - t0)
        latency = time.monotonic() - t0
        self.stats.api_calls += 1
        try:
            content = raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            content = None
        u = raw.get("usage") or {}
        try:
            finish = raw["choices"][0].get("finish_reason")
        except (KeyError, IndexError, TypeError, AttributeError):
            finish = None
        usage = {"prompt_tokens": int(u.get("prompt_tokens") or 0), "completion_tokens": int(u.get("completion_tokens") or 0),
                 "reasoning_tokens": int((u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0),
                 "finish_reason": finish}
        parsed = _parse_json(content)
        status = "ok" if parsed is not None else "invalid_json"
        cost = costs.cost_usd(usage["prompt_tokens"], usage["completion_tokens"], self.cfg["budget"])
        self.stats.prompt_tokens += usage["prompt_tokens"]
        self.stats.completion_tokens += usage["completion_tokens"]
        self.stats.est_cost_usd += cost
        self._write_cache(path, key, purpose, prompt_version, body, raw, content, usage, status)
        self._log_usage(purpose, prompt_version, key, status, usage, cost, latency, None)
        self._say(f"  {purpose}: {status} in {latency:.1f}s, finish {finish}, {usage['prompt_tokens']} in, "
                  f"{usage['completion_tokens']} out ({usage['reasoning_tokens']} reasoning), {cost:.4f} USD | {self._totals()}")
        return CallResult(status, "api", parsed, content, usage, key)

    def _failed(self, purpose: str, prompt_version: str, key: str, error: str, latency: float) -> CallResult:
        self.stats.failed += 1
        self._say(f"  {purpose}: FAILED after {latency:.1f}s ({error}); logged, skipped, not retried")
        self._log_usage(purpose, prompt_version, key, "failed", {"prompt_tokens": 0, "completion_tokens": 0}, 0.0, latency, error)
        return CallResult("failed", "api", None, None, {}, key, error)

    def _write_cache(self, path, key, purpose, prompt_version, body, raw, content, usage, status) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"key": key, "created_utc": _now(), "purpose": purpose, "prompt_version": prompt_version,
                 "mock": self.mock, "status": status, "request": body, "response": raw, "content": content, "usage": usage}
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(entry, ensure_ascii=False, indent=1))
        tmp.replace(path)

    def _log_usage(self, purpose, prompt_version, key, status, usage, cost, latency, error) -> None:
        entry: dict[str, Any] = {"ts": _now(), "experiment": costs.EXPERIMENT_TAG, "purpose": purpose,
                                 "prompt_version": prompt_version, "model": self.model, "cache_key": key, "status": status,
                                 "prompt_tokens": usage.get("prompt_tokens", 0),
                                 "completion_tokens": usage.get("completion_tokens", 0),
                                 "reasoning_tokens": usage.get("reasoning_tokens", 0),
                                 "finish_reason": usage.get("finish_reason"),
                                 "est_cost_usd": round(cost, 6), "latency_s": round(latency, 2), "error": error}
        self.stats.log.append(entry)
        self.usage_log.parent.mkdir(parents=True, exist_ok=True)
        with self.usage_log.open("a") as f:
            f.write(json.dumps(entry) + "\n")
