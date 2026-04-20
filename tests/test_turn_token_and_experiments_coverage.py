"""Unit coverage for large runtime/experiment modules (no subprocess integration)."""

from __future__ import annotations

import socket
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fsaa.config.paths import clear_paths_cache, get_paths
from fsaa.experiments import ab_harness
from fsaa.runtime import turn_token as tt


def test_turn_token_utc_and_cores() -> None:
    assert "T" in tt.utc_now()
    assert tt._cores_to_mask([0, 1]) == 3
    assert tt._cores_to_mask([-1]) == 0


def test_turn_token_paths_from_fsaa(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    clear_paths_cache()
    p = get_paths()
    ttp = tt.TurnTokenPaths.from_fsaa(p)
    assert ttp.workspace_root == tmp_path
    assert ttp.chat == tmp_path / "chat.py"


def test_load_scheduler_config_creates_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    clear_paths_cache()
    p = get_paths()
    ttp = tt.TurnTokenPaths.from_fsaa(p)
    cfg = tt._load_scheduler_config(ttp)
    assert cfg["cpu_turn_beats"] == 4
    assert ttp.scheduler_config.is_file()


def test_append_and_emit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    clear_paths_cache()
    ttp = tt.TurnTokenPaths.from_fsaa(get_paths())
    tt.append_event(ttp, {"x": 1})
    tt.append_desk_trace(
        ttp,
        "t",
        actor="a",
        decision="d",
        outcome="o",
        input_context={},
    )
    tt.write_state(ttp, {"k": "v"})
    tt.emit_integration_seam(ttp, enabled=False, experiment_id="e", rollback_external_pilot=True)
    assert ttp.event_log.read_text(encoding="utf-8").strip()
    assert ttp.integration_state.is_file()


def test_choose_cpu_stage_action() -> None:
    g: list[str] = []
    d, ctx = tt.choose_cpu_stage_action(3, g)
    assert d == "stage"
    assert "staged_depth" in ctx


def test_brain_status_empty_on_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    clear_paths_cache()
    ttp = tt.TurnTokenPaths.from_fsaa(get_paths())

    def _boom(*_a: object, **_k: object) -> None:
        raise OSError("nope")

    monkeypatch.setattr(socket, "socket", _boom)
    assert tt.brain_status(ttp) == {}


def test_ab_harness_utc_and_run_cmd() -> None:
    assert "T" in ab_harness.utc_now()
    code, out, _err = ab_harness.run_cmd([sys.executable, "-c", "print(1)"], timeout=30)
    assert code == 0
    assert "1" in out


def test_entrypoint_main(monkeypatch: pytest.MonkeyPatch) -> None:
    from fsaa.cli import entrypoint

    monkeypatch.setattr(
        "fsaa.cli.entrypoint.subprocess.run",
        MagicMock(return_value=MagicMock(returncode=0)),
    )
    assert entrypoint.main() == 0


def test_aios_sides_exports() -> None:
    import importlib

    m = importlib.import_module("fsaa.runtime.adapters.aios_sides")
    assert callable(m.run_luna_main)
    assert callable(m.run_aria_main)
