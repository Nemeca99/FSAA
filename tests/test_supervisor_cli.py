from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fsaa.config.paths import clear_paths_cache, get_paths
from fsaa.control_plane.supervisor import Supervisor, parse_args


def test_run_cli_turn_token_passes_argv_extra(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FSAA_AUTHORITY_LOG", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("FSAA_TRANSLATION_METRICS", str(tmp_path / "m.jsonl"))
    clear_paths_cache()
    paths = get_paths()
    from fsaa.runtime.adapters.aios import AIOSRuntimeAdapter

    sup = Supervisor(paths, AIOSRuntimeAdapter(paths))
    captured: dict = {}

    def _capture_side(
        script_path: object,
        run_id: int,
        timeout: int,
        *,
        side: str,
        safe_low_ram: bool,
        auto: bool,
        loop_count: int,
        beat_seconds: float,
        min_actions_per_run: int,
        kill_existing: bool,
        gc_threshold_mb: int,
        auto_max_cycles: int,
        argv_extra: tuple[str, ...] = (),
    ) -> int:
        captured["script"] = script_path
        captured["argv_extra"] = argv_extra
        return 0

    # Plain function: instance call passes `script_path` as first arg (no bound self).
    monkeypatch.setattr(sup, "_run_side", _capture_side)
    args = parse_args(
        [
            "--mode",
            "turn_token",
            "--no-auto",
            "--loop",
            "1",
            "--turn-token-max-seconds",
            "30",
            "--turn-token-cpu-beats",
            "4",
            "--turn-token-gpu-beats",
            "2",
        ]
    )
    assert sup.run_cli(args) == 0
    assert captured["script"] == paths.turn_token_module_py
    assert captured["argv_extra"] == ("--max-seconds", "30", "--cpu-turn-beats", "4", "--gpu-turn-beats", "2")


def test_run_cli_smoke(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("FSAA_AUTHORITY_LOG", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("FSAA_TRANSLATION_METRICS", str(tmp_path / "m.jsonl"))
    clear_paths_cache()
    paths = get_paths()
    from fsaa.runtime.adapters.aios import AIOSRuntimeAdapter

    sup = Supervisor(paths, AIOSRuntimeAdapter(paths))
    monkeypatch.setattr(sup, "_run_side", MagicMock(return_value=0))
    args = parse_args(["--side", "left", "--no-auto", "--loop", "1"])
    assert sup.run_cli(args) == 0
