"""Path resolution — ``WORKSPACE_ROOT`` required; workspace-relative paths only (no legacy package roots)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from fsaa.contracts.errors import ConfigurationError


def _fsaa_repo_root() -> Path:
    """Directory containing ``src/fsaa`` (this repository root)."""
    return Path(__file__).resolve().parents[3]


def _default_venv_python(workspace: Path) -> Path:
    if sys.platform == "win32":
        return workspace / ".venv" / "Scripts" / "python.exe"
    return workspace / ".venv" / "bin" / "python"


@dataclass(frozen=True)
class FsaaPaths:
    workspace_root: Path
    fsaa_repo_root: Path
    observability_dir: Path
    authority_log: Path
    translation_metrics: Path
    supervisor_run_state: Path
    supervisor_events: Path
    autonomy_telemetry: Path
    python_executable: Path
    chat_entry: Path
    luna_runtime_main: Path
    aria_runtime_main: Path
    ipc_schema_override: Path | None
    reflex_policy_override: Path | None
    brain_status_port: int
    fsaa_integration_state_path: Path
    turn_token_module_py: Path

    @classmethod
    def from_environ(cls) -> FsaaPaths:
        raw = os.environ.get("WORKSPACE_ROOT", "").strip()
        if not raw:
            raise ConfigurationError(
                "WORKSPACE_ROOT is required: absolute path to the workspace "
                "(contains automation, chat.py, AIOS_Luna_Aria)."
            )
        workspace = Path(raw).resolve()
        fsaa_root = _fsaa_repo_root()
        obs = (
            Path(os.environ["FSAA_OBSERVABILITY_DIR"]).resolve()
            if os.environ.get("FSAA_OBSERVABILITY_DIR")
            else workspace / "automation"
        )
        auth = (
            Path(os.environ["FSAA_AUTHORITY_LOG"]).resolve()
            if os.environ.get("FSAA_AUTHORITY_LOG")
            else obs / "authority_guard_log.jsonl"
        )
        tm = (
            Path(os.environ["FSAA_TRANSLATION_METRICS"]).resolve()
            if os.environ.get("FSAA_TRANSLATION_METRICS")
            else obs / "translation_metrics.jsonl"
        )
        venv_py = _default_venv_python(workspace)
        if os.environ.get("FSAA_PYTHON"):
            py_exe = Path(os.environ["FSAA_PYTHON"]).resolve()
        elif venv_py.is_file():
            py_exe = venv_py
        else:
            py_exe = Path(sys.executable)
        ipc_override: Path | None = None
        if os.environ.get("FSAA_IPC_SCHEMA"):
            ipc_override = Path(os.environ["FSAA_IPC_SCHEMA"]).resolve()
            if not ipc_override.is_file():
                raise ConfigurationError(f"FSAA_IPC_SCHEMA is not a file: {ipc_override}")
        reflex_override: Path | None = None
        if os.environ.get("FSAA_REFLEX_POLICY"):
            reflex_override = Path(os.environ["FSAA_REFLEX_POLICY"]).resolve()
            if not reflex_override.is_file():
                raise ConfigurationError(f"FSAA_REFLEX_POLICY is not a file: {reflex_override}")
        brain_port = 5151
        if os.environ.get("FSAA_BRAIN_STATUS_PORT", "").strip():
            try:
                brain_port = int(os.environ["FSAA_BRAIN_STATUS_PORT"].strip(), 10)
            except ValueError as e:
                raise ConfigurationError("FSAA_BRAIN_STATUS_PORT must be an integer") from e
        luna_main = workspace / "AIOS_Luna_Aria" / "Luna" / "AIOS_V2" / "main.py"
        aria_main = workspace / "AIOS_Luna_Aria" / "Aria" / "AIOS_V3" / "main_v3.py"
        turn_py = fsaa_root / "src" / "fsaa" / "runtime" / "turn_token.py"
        return cls(
            workspace_root=workspace,
            fsaa_repo_root=fsaa_root,
            observability_dir=obs,
            authority_log=auth,
            translation_metrics=tm,
            supervisor_run_state=obs / "fsaa_supervisor_run_state.json",
            supervisor_events=obs / "fsaa_supervisor_events.jsonl",
            autonomy_telemetry=obs / "autonomy_1hz.jsonl",
            python_executable=py_exe,
            chat_entry=workspace / "chat.py",
            luna_runtime_main=luna_main,
            aria_runtime_main=aria_main,
            ipc_schema_override=ipc_override,
            reflex_policy_override=reflex_override,
            brain_status_port=brain_port,
            fsaa_integration_state_path=obs / "fsaa_integration_state.json",
            turn_token_module_py=turn_py,
        )


def read_ipc_schema_bytes(paths: FsaaPaths) -> bytes:
    if paths.ipc_schema_override is not None:
        return paths.ipc_schema_override.read_bytes()
    from fsaa.resources import packaged_ipc_schema_bytes

    return packaged_ipc_schema_bytes()


def read_ipc_schema_text(paths: FsaaPaths) -> str:
    return read_ipc_schema_bytes(paths).decode("utf-8")


def read_reflex_policy_bytes(paths: FsaaPaths) -> bytes:
    if paths.reflex_policy_override is not None:
        return paths.reflex_policy_override.read_bytes()
    from fsaa.resources import packaged_reflex_policy_bytes

    return packaged_reflex_policy_bytes()


def read_reflex_policy_text(paths: FsaaPaths) -> str:
    return read_reflex_policy_bytes(paths).decode("utf-8")


@lru_cache
def get_paths() -> FsaaPaths:
    return FsaaPaths.from_environ()


def clear_paths_cache() -> None:
    get_paths.cache_clear()
