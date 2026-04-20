"""IPC envelope guard — schema + reflex policy enforcement with FsaaPaths.

Schema file: default load uses :mod:`importlib.resources` at
``fsaa.resources/ipc_schema.json`` (see :func:`fsaa.config.paths.read_ipc_schema_bytes`).
Repo-root ``ipc_schema.json`` remains for legacy shims; tests assert byte parity.

``_TURN_LOCK`` is a :class:`threading.Lock` — **in-process mutual exclusion only**
(see ``docs/adr/ADR-0003-turn-lock-in-process-only.md``). Separate processes each
hold an independent lock; Alpha assumes low cross-process contention on
``guarded_commit``.
"""

from __future__ import annotations

__all__ = [
    "ALLOWED_ACTORS",
    "ALLOWED_EVENT_TYPES",
    "ALLOWED_INTENTS",
    "REQUIRED_FIELDS",
    "SCHEMA_VERSION",
    "ValidationResult",
    "guarded_commit",
    "load_schema",
    "validate_envelope",
    "validate_envelope_jsonschema",
]

import json
import os
import time
from dataclasses import dataclass
from datetime import UTC
from threading import Lock
from typing import Any

from jsonschema import Draft202012Validator

from fsaa.config.paths import get_paths, read_ipc_schema_bytes

# In-process only; does not serialize across subprocesses (ADR-0003).
_TURN_LOCK = Lock()

SCHEMA_VERSION = "fsaa-ipc-v1"
ALLOWED_ACTORS = {"luna_left", "aria_right", "steel_brain", "runner", "scheduler", "operator"}
ALLOWED_EVENT_TYPES = {"intent", "outcome", "status", "reject", "heartbeat"}
ALLOWED_INTENTS = {
    "runtime_boot",
    "runtime_stop",
    "seed_timer",
    "turn_token_step",
    "sandbox_write",
    "speak",
    "dream_cycle",
    "sleep",
    "wake",
    "status_poll",
    "operator_override",
}
REQUIRED_FIELDS = {
    "schema_version",
    "run_id",
    "timestamp",
    "actor",
    "event_type",
    "intent",
    "payload",
    "prev_hash",
}


def _utc_now() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def _authority_log_path() -> Any:
    p = os.environ.get("FSAA_AUTHORITY_LOG")
    if p:
        from pathlib import Path

        return Path(p)
    return get_paths().authority_log


def _translation_metrics_path() -> Any:
    p = os.environ.get("FSAA_TRANSLATION_METRICS")
    if p:
        from pathlib import Path

        return Path(p)
    return get_paths().translation_metrics


def _append_log(entry: dict[str, Any]) -> None:
    path = _authority_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _append_translation_metric(row: dict[str, Any]) -> None:
    path = _translation_metrics_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


@dataclass
class ValidationResult:
    ok: bool
    reason: str = ""


def load_schema() -> dict[str, Any]:
    try:
        raw = read_ipc_schema_bytes(get_paths())
    except OSError:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def _ipc_validator() -> Draft202012Validator:
    schema = load_schema()
    if not schema:
        raise ValueError("empty_ipc_schema")
    return Draft202012Validator(schema)


def validate_envelope_jsonschema(envelope: dict[str, Any]) -> None:
    """Validate envelope against ipc_schema.json (single source of truth). Raises jsonschema.ValidationError."""
    _ipc_validator().validate(envelope)


def validate_envelope(envelope: dict[str, Any]) -> ValidationResult:
    """Same acceptance rules as legacy authority_guard (byte-compatible outcomes for parity)."""
    missing = [k for k in REQUIRED_FIELDS if k not in envelope]
    if missing:
        return ValidationResult(False, f"schema_invalid:missing_fields:{','.join(missing)}")
    if envelope.get("schema_version") != SCHEMA_VERSION:
        return ValidationResult(False, "schema_invalid:version")
    if not isinstance(envelope.get("run_id"), int) or int(envelope["run_id"]) < 1:
        return ValidationResult(False, "schema_invalid:run_id")
    if not isinstance(envelope.get("payload"), dict):
        return ValidationResult(False, "schema_invalid:payload")
    actor = str(envelope.get("actor", ""))
    if actor not in ALLOWED_ACTORS:
        return ValidationResult(False, "unauthorized_actor")
    event_type = str(envelope.get("event_type", ""))
    if event_type not in ALLOWED_EVENT_TYPES:
        return ValidationResult(False, "schema_invalid:event_type")
    intent = str(envelope.get("intent", ""))
    if intent not in ALLOWED_INTENTS:
        return ValidationResult(False, "schema_invalid:intent")
    return ValidationResult(True)


def guarded_commit(envelope: dict[str, Any]) -> ValidationResult:
    """Serialize validation + logging under the in-process ``_TURN_LOCK`` (ADR-0003)."""
    t0 = time.perf_counter()
    with _TURN_LOCK:
        result = validate_envelope(envelope)
        commit_ms = round((time.perf_counter() - t0) * 1000.0, 4)
        run_id = int(envelope.get("run_id", 0) or 0) if isinstance(envelope, dict) else 0
        actor = str(envelope.get("actor", "")) if isinstance(envelope, dict) else ""
        event_type = str(envelope.get("event_type", "")) if isinstance(envelope, dict) else ""
        intent = str(envelope.get("intent", "")) if isinstance(envelope, dict) else ""
        metric = {
            "ts": _utc_now(),
            "metric_type": "ipc_envelope_commit",
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "actor": actor,
            "event_type": event_type,
            "intent": intent,
            "outcome": "accept" if result.ok else "reject",
            "reject_reason": "" if result.ok else result.reason,
            "commit_latency_ms": commit_ms,
            "loss": 0 if result.ok else 1,
            "retry": 0,
            "fallback": 0,
        }
        _append_translation_metric(metric)
        if not result.ok:
            _append_log(
                {
                    "ts": _utc_now(),
                    "event_type": "reject",
                    "reason": result.reason,
                    "envelope": envelope,
                }
            )
            return result
        _append_log(
            {
                "ts": _utc_now(),
                "event_type": "accept",
                "reason": "ok",
                "envelope": envelope,
            }
        )
        return ValidationResult(True)


if __name__ == "__main__":
    example = {
        "schema_version": SCHEMA_VERSION,
        "run_id": 1,
        "timestamp": _utc_now(),
        "actor": "runner",
        "event_type": "intent",
        "intent": "status_poll",
        "payload": {"note": "authority guard self-test"},
        "prev_hash": "",
    }
    verdict = guarded_commit(example)
    print(
        json.dumps(
            {"ok": verdict.ok, "reason": verdict.reason, "schema_loaded": bool(load_schema())},
            indent=2,
        )
    )
