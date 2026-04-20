"""FSAA integration / authority delegation state (governance artifact)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class FsaaIntegrationState:
    """Mirror of ``turn_token_integration_state.json`` fields plus FSAA subsystems map."""

    ts: str
    integration_enabled: bool
    experiment_id: str
    rollback_external_pilot: bool
    single_turn_authority: str
    schema_lock_state: str
    core_loop_write_access_confirmed: bool
    note: str
    #: Subsystem name → authority level label (e.g. ``external_pilot``, ``supervisor``).
    subsystems: dict[str, str]

    @classmethod
    def default(cls) -> FsaaIntegrationState:
        return cls(
            ts="",
            integration_enabled=False,
            experiment_id="turn_token_external_pilot",
            rollback_external_pilot=True,
            single_turn_authority="turn_token_loop",
            schema_lock_state="enforced_in_runtime",
            core_loop_write_access_confirmed=False,
            note="External pilot remains authority until core write access is confirmed.",
            subsystems={"turn_token_loop": "external_pilot", "steel_brain": "supervisor"},
        )


def load_integration_state(path: Path) -> FsaaIntegrationState | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, dict):
        return None
    base = FsaaIntegrationState.default()
    subs = raw.get("subsystems")
    sub_map: dict[str, str] = dict(base.subsystems)
    if isinstance(subs, dict):
        sub_map = {str(k): str(v) for k, v in subs.items()}
    merged = {
        "ts": str(raw.get("ts", base.ts)),
        "integration_enabled": bool(raw.get("integration_enabled", base.integration_enabled)),
        "experiment_id": str(raw.get("experiment_id", base.experiment_id)),
        "rollback_external_pilot": bool(
            raw.get("rollback_external_pilot", base.rollback_external_pilot)
        ),
        "single_turn_authority": str(raw.get("single_turn_authority", base.single_turn_authority)),
        "schema_lock_state": str(raw.get("schema_lock_state", base.schema_lock_state)),
        "core_loop_write_access_confirmed": bool(
            raw.get("core_loop_write_access_confirmed", base.core_loop_write_access_confirmed)
        ),
        "note": str(raw.get("note", base.note)),
        "subsystems": sub_map,
    }
    return FsaaIntegrationState(**merged)


def save_integration_state(path: Path, state: FsaaIntegrationState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = asdict(state)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
