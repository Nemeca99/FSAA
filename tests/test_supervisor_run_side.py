"""Exercise Supervisor._run_side with heavy mocks (bounded, non-auto)."""

from __future__ import annotations

from pathlib import Path

import pytest

from fsaa.config.paths import clear_paths_cache, get_paths
from fsaa.control_plane.supervisor import Supervisor
from fsaa.policy.guard import ValidationResult
from fsaa.runtime.adapters.aios import AIOSRuntimeAdapter


@pytest.fixture
def sup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Supervisor:
    paths = get_paths()
    monkeypatch.setenv("FSAA_AUTHORITY_LOG", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("FSAA_TRANSLATION_METRICS", str(tmp_path / "m.jsonl"))
    clear_paths_cache()
    ad = AIOSRuntimeAdapter(paths)
    return Supervisor(paths, ad)


def test_run_side_bounded_mocked(sup: Supervisor, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "fsaa.control_plane.supervisor.guarded_commit",
        lambda e: ValidationResult(True, ""),
    )
    calls = {"n": 0}

    def _fake_cycle(**_kwargs: object) -> tuple[int, bool, bool]:
        calls["n"] += 1
        return 0, True, True

    monkeypatch.setattr(sup, "_run_single_loop_cycle", _fake_cycle)
    monkeypatch.setattr(sup, "_append_event", lambda row: None)
    rc = sup._run_side(
        Path(__file__),
        run_id=1,
        timeout=120,
        side="left",
        safe_low_ram=False,
        auto=False,
        loop_count=1,
        beat_seconds=0.1,
        min_actions_per_run=1,
        kill_existing=False,
        gc_threshold_mb=8192,
        auto_max_cycles=0,
    )
    assert rc == 0
    assert calls["n"] == 1


def test_sigterm_sets_flag(sup: Supervisor) -> None:
    sup._on_sigterm(15, None)
    assert sup._shutdown_requested


def test_supervisor_main_returns_78_without_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKSPACE_ROOT", raising=False)
    clear_paths_cache()
    from fsaa.control_plane.supervisor import main

    assert main([]) == 78
