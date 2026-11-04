"""Expo Push API: batches of at most 100 messages, only tokens that start with
"ExponentPushToken", alert id in the data payload so a tap opens the alert detail."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx

log = logging.getLogger("frostwatch.push")

BATCH_SIZE = 100
TOKEN_PREFIX = "ExponentPushToken"
TOKEN_RE = re.compile(r"Expo(nent)?PushToken\[[^\]]*\]")


@dataclass
class PushResult:
    token: str
    status: str  # "sent", "error", "skipped"
    ticket_id: str | None = None
    error: str | None = None


def valid_token(token: str) -> bool:
    return token.startswith(TOKEN_PREFIX + "[") and token.endswith("]")


def send_push(tokens: list[str], *, title: str, body: str, data: dict, url: str,
              client: httpx.Client | None = None) -> list[PushResult]:
    results = [PushResult(t, "skipped", error="invalid_token") for t in tokens if not valid_token(t)]
    good = [t for t in tokens if valid_token(t)]
    own = client is None
    client = client or httpx.Client(timeout=15)
    try:
        for start in range(0, len(good), BATCH_SIZE):
            batch = good[start:start + BATCH_SIZE]
            messages = [{"to": t, "title": title, "body": body, "data": data, "sound": "default"} for t in batch]
            try:
                resp = client.post(url, json=messages, headers={"Accept": "application/json"})
                resp.raise_for_status()
                tickets = resp.json().get("data") or []
            except (httpx.HTTPError, ValueError) as exc:
                results += [PushResult(t, "error", error=f"request_failed:{type(exc).__name__}") for t in batch]
                continue
            for i, t in enumerate(batch):
                ticket = tickets[i] if i < len(tickets) else {}
                if ticket.get("status") == "ok":
                    results.append(PushResult(t, "sent", ticket_id=ticket.get("id")))
                else:
                    err = (ticket.get("details") or {}).get("error") or ticket.get("message") or "no_ticket"
                    results.append(PushResult(t, "error", error=TOKEN_RE.sub("<token>", str(err))[:200]))
    finally:
        if own:
            client.close()
    return results
