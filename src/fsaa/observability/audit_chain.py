"""A/B and automation audit chain — must match ``automation/ab_test_turn_token.py`` hash semantics.

Preserving this format keeps SHA-256 chain continuity across legacy runs and FSAA-era tooling.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def audit_event_body_for_hash(
    *,
    timestamp: str,
    run_id: int,
    event_type: str,
    actor: str,
    payload: dict[str, Any],
    prev_hash: str,
) -> bytes:
    """UTF-8 body bytes hashed by :func:`audit_event_hash_hex` (``sort_keys=True``, no ``event_hash``)."""
    event = {
        "timestamp": timestamp,
        "run_id": run_id,
        "event_type": event_type,
        "actor": actor,
        "payload": payload,
        "prev_hash": prev_hash,
    }
    return json.dumps(event, ensure_ascii=False, sort_keys=True).encode("utf-8")


def audit_event_hash_hex(
    *,
    timestamp: str,
    run_id: int,
    event_type: str,
    actor: str,
    payload: dict[str, Any],
    prev_hash: str,
) -> str:
    """SHA-256 hex digest of the canonical audit body (same as ``ab_test_turn_token.append_audit_event``)."""
    body = audit_event_body_for_hash(
        timestamp=timestamp,
        run_id=run_id,
        event_type=event_type,
        actor=actor,
        payload=payload,
        prev_hash=prev_hash,
    )
    return hashlib.sha256(body).hexdigest()
