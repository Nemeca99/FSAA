from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsaa.config.paths import clear_paths_cache
from fsaa.policy.guard import SCHEMA_VERSION, guarded_commit


def test_guarded_commit_accept(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    auth = tmp_path / "auth.jsonl"
    tm = tmp_path / "tm.jsonl"
    monkeypatch.setenv("FSAA_AUTHORITY_LOG", str(auth))
    monkeypatch.setenv("FSAA_TRANSLATION_METRICS", str(tm))
    clear_paths_cache()
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
    r = guarded_commit(env)
    assert r.ok
    assert auth.is_file()
    lines = auth.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["event_type"] == "accept"
