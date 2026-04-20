from __future__ import annotations

from pathlib import Path

import pytest

from fsaa.config.paths import (
    FsaaPaths,
    clear_paths_cache,
    get_paths,
    read_ipc_schema_bytes,
)
from fsaa.contracts.errors import ConfigurationError


def test_workspace_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKSPACE_ROOT", raising=False)
    clear_paths_cache()
    with pytest.raises(ConfigurationError):
        FsaaPaths.from_environ()


def test_read_ipc_schema_respects_fsaa_ipc_schema_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ws = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    alt = tmp_path / "override.json"
    alt.write_bytes(b'{"x": 1}')
    monkeypatch.setenv("FSAA_IPC_SCHEMA", str(alt))
    clear_paths_cache()
    assert read_ipc_schema_bytes(get_paths()) == b'{"x": 1}'
    monkeypatch.delenv("FSAA_IPC_SCHEMA", raising=False)
    clear_paths_cache()


def test_paths_resolve(monkeypatch: pytest.MonkeyPatch) -> None:
    ws = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    clear_paths_cache()
    p = get_paths()
    assert p.workspace_root == ws
    assert p.chat_entry == ws / "chat.py"
    assert read_ipc_schema_bytes(p).startswith(b"{")
    assert p.ipc_schema_override is None
    assert p.brain_status_port == 5151
    assert p.fsaa_integration_state_path.name == "fsaa_integration_state.json"
