from __future__ import annotations

from fsaa.policy.guard import (
    SCHEMA_VERSION,
    ValidationResult,
    validate_envelope,
    validate_envelope_jsonschema,
)


def test_validate_envelope_ok() -> None:
    env = {
        "schema_version": SCHEMA_VERSION,
        "run_id": 1,
        "timestamp": "2026-01-01T00:00:00.000000+00:00",
        "actor": "runner",
        "event_type": "intent",
        "intent": "status_poll",
        "payload": {},
        "prev_hash": "",
    }
    assert validate_envelope(env) == ValidationResult(True, "")


def test_validate_envelope_missing_run_id() -> None:
    env = {
        "schema_version": SCHEMA_VERSION,
        "timestamp": "2026-01-01T00:00:00.000000+00:00",
        "actor": "runner",
        "event_type": "intent",
        "intent": "status_poll",
        "payload": {},
        "prev_hash": "",
    }
    r = validate_envelope(env)
    assert not r.ok
    assert "missing_fields" in r.reason


def test_validate_envelope_jsonschema() -> None:
    env = {
        "schema_version": SCHEMA_VERSION,
        "run_id": 1,
        "timestamp": "2026-01-01T00:00:00.000000+00:00",
        "actor": "runner",
        "event_type": "intent",
        "intent": "status_poll",
        "payload": {},
        "prev_hash": "",
    }
    validate_envelope_jsonschema(env)
