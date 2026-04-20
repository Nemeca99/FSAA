"""Replay production-shaped envelopes from committed sample (Phase C parity)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsaa.policy.guard import validate_envelope, validate_envelope_jsonschema


def _sample_lines() -> list[str]:
    p = Path(__file__).resolve().parent / "fixtures" / "authority_guard_log.sample.jsonl"
    return [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


@pytest.mark.parametrize("line", _sample_lines())
def test_sample_envelopes_validate(line: str) -> None:
    row = json.loads(line)
    env = row.get("envelope")
    assert isinstance(env, dict)
    vr = validate_envelope(env)
    assert vr.ok, vr.reason
    validate_envelope_jsonschema(env)
