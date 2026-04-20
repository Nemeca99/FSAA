from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fsaa.cli import workspace_runtime as wr


def test_launch_left_missing_entry_returns_78(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    py_exe = tmp_path / "python.exe"
    py_exe.write_bytes(b"")
    fake_paths = MagicMock()
    fake_paths.luna_runtime_main = ws / "missing.py"
    fake_paths.python_executable = py_exe
    fake_paths.workspace_root = ws
    monkeypatch.setattr(wr, "get_paths", lambda: fake_paths)
    assert wr.launch_workspace_side("left") == 78


def test_launch_left_runs_subprocess(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    entry = ws / "luna.py"
    entry.write_text("# stub\n", encoding="utf-8")
    py = tmp_path / "py.exe"
    py.write_bytes(b"")
    fake_paths = MagicMock()
    fake_paths.luna_runtime_main = entry
    fake_paths.python_executable = py
    fake_paths.workspace_root = ws
    monkeypatch.setattr(wr, "get_paths", lambda: fake_paths)
    mock_run = MagicMock(return_value=MagicMock(returncode=0))
    monkeypatch.setattr(wr.subprocess, "run", mock_run)
    assert wr.launch_workspace_side("left") == 0
    assert mock_run.called
    args, kwargs = mock_run.call_args
    assert args[0][0:2] == [str(py), str(entry)]
    assert kwargs["cwd"] == str(ws)


def test_main_left_calls_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wr, "launch_workspace_side", lambda _s: 42)
    assert wr.main_left() == 42


def test_main_argv_left(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wr, "launch_workspace_side", lambda s: 7 if s == "left" else 0)
    assert wr.main(["left"]) == 7
