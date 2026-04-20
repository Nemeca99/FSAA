"""Audit chain SHA-256 must stay aligned with ``automation/ab_test_turn_token.append_audit_event``."""

from __future__ import annotations

import hashlib
import json

from fsaa.observability.audit_chain import audit_event_hash_hex


def test_audit_event_hash_matches_sort_keys_sha256() -> None:
    ts = "2026-04-20T12:00:00+00:00"
    event = {
        "timestamp": ts,
        "run_id": 7,
        "event_type": "intent",
        "actor": "ab_test_turn_token",
        "payload": {"label": "x", "args": [1, 2], "timeout": 3},
        "prev_hash": "abc",
    }
    body = json.dumps(event, ensure_ascii=False, sort_keys=True).encode("utf-8")
    expected = hashlib.sha256(body).hexdigest()
    got = audit_event_hash_hex(
        timestamp=ts,
        run_id=7,
        event_type="intent",
        actor="ab_test_turn_token",
        payload={"label": "x", "args": [1, 2], "timeout": 3},
        prev_hash="abc",
    )
    assert got == expected
