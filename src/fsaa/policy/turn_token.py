"""Turn-token / A/B guard helpers — keep in sync with ``automation/ab_test_turn_token.py``."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fsaa.policy.guard import SCHEMA_VERSION, guarded_commit


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def intent_from_label(label: str) -> str:
    value = (label or "").strip().lower()
    if "ensure_runtime" in value:
        return "runtime_boot"
    if "turn_loop" in value:
        return "turn_token_step"
    return "status_poll"


def guard_or_raise(
    *,
    run_id: int,
    prev_hash: str,
    event_type: str,
    label: str,
    payload: dict[str, Any],
) -> None:
    """Same contract as ``ab_test_turn_token._guard_or_raise`` (raises ``RuntimeError`` on reject)."""
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "run_id": int(run_id),
        "timestamp": utc_now_iso(),
        "actor": "runner",
        "event_type": event_type,
        "intent": intent_from_label(label),
        "payload": {"label": label, **payload},
        "prev_hash": prev_hash,
    }
    verdict = guarded_commit(envelope)
    if not verdict.ok:
        raise RuntimeError(f"authority_guard_reject:{verdict.reason}")
