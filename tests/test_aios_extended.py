"""Cover AIOSRuntimeAdapter branches (probes, shutdown, Windows helpers)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from fsaa.config.paths import get_paths
from fsaa.runtime.adapters.aios import AIOSRuntimeAdapter, AIOSRuntimeHandle
from fsaa.runtime.protocol import RuntimeStartConfig


def test_probe_liveness_exited() -> None:
    paths = get_paths()
    ad = AIOSRuntimeAdapter(paths)
    proc = MagicMock()
    proc.pid = 1
    proc.poll.return_value = 0
    h = AIOSRuntimeHandle(proc=proc, script_path=Path("."), side="left")
    st = ad.probe_liveness(h)
    assert not st.alive


def test_shutdown_already_exited() -> None:
    paths = get_paths()
    ad = AIOSRuntimeAdapter(paths)
    proc = MagicMock()
    proc.poll.return_value = 0
    proc.returncode = 0
    h = AIOSRuntimeHandle(proc=proc, script_path=Path("."), side="left")
    r = ad.shutdown(h, 1.0)
    assert r.exit_code == 0


def test_shutdown_timeout_kills() -> None:
    paths = get_paths()
    ad = AIOSRuntimeAdapter(paths)
    proc = MagicMock()
    proc.poll.return_value = None
    proc.wait.side_effect = [
        subprocess.TimeoutExpired("x", 99),
        None,
    ]
    proc.kill = MagicMock()
    proc.returncode = -9
    h = AIOSRuntimeHandle(proc=proc, script_path=Path("."), side="left")
    r = ad.shutdown(h, 0.01)
    proc.kill.assert_called_once()
    assert "kill" in r.message.lower() or r.exit_code != 0


def test_probe_readiness() -> None:
    paths = get_paths()
    ad = AIOSRuntimeAdapter(paths)
    proc = MagicMock()
    proc.pid = 1
    proc.poll.return_value = None
    h = AIOSRuntimeHandle(proc=proc, script_path=Path("."), side="left")
    assert ad.probe_readiness(h).ready


def test_kill_side_win32_mocked() -> None:
    paths = get_paths()
    ad = AIOSRuntimeAdapter(paths)
    with (
        patch.object(sys, "platform", "win32"),
        patch("fsaa.runtime.adapters.aios.subprocess.run") as run,
    ):
        run.return_value = MagicMock(stdout="42\n", returncode=0)
        n = ad.kill_existing_side_processes("left")
        assert n >= 0


def test_memory_mb_win32() -> None:
    paths = get_paths()
    ad = AIOSRuntimeAdapter(paths)
    with (
        patch.object(sys, "platform", "win32"),
        patch("fsaa.runtime.adapters.aios.subprocess.run") as run,
    ):
        run.return_value = MagicMock(stdout="1048576\n", returncode=0)
        assert ad.side_memory_mb("right") >= 0


def test_dream_consolidation() -> None:
    paths = get_paths()
    ad = AIOSRuntimeAdapter(paths)
    with patch("fsaa.runtime.adapters.aios.subprocess.run") as run:
        run.return_value = MagicMock(returncode=0)
        ad.request_dream_consolidation()
        run.assert_called_once()


def test_stop_process_pid_win32() -> None:
    paths = get_paths()
    ad = AIOSRuntimeAdapter(paths)
    with (
        patch.object(sys, "platform", "win32"),
        patch("fsaa.runtime.adapters.aios.subprocess.run") as run,
    ):
        ad.stop_process_pid(123)
        run.assert_called_once()


def test_start_config() -> None:
    paths = get_paths()
    ad = AIOSRuntimeAdapter(paths)
    cfg = RuntimeStartConfig(
        script_path=Path(__file__),
        env={},
        cwd=paths.workspace_root,
        side="left",
    )
    with patch("fsaa.runtime.adapters.aios.subprocess.Popen") as P:
        proc = MagicMock()
        proc.pid = 7
        proc.poll.return_value = None
        P.return_value = proc
        h = ad.start(cfg)
        assert h.pid == 7
