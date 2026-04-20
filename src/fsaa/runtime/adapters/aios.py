"""AIOS reference runtime adapter — chat.py, venv Python, Luna/Aria, Windows PowerShell hygiene."""

from __future__ import annotations

import contextlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from fsaa.config.paths import FsaaPaths
from fsaa.runtime.protocol import (
    ExitReport,
    LivenessState,
    ReadinessState,
    RuntimeHandle,
    RuntimeStartConfig,
)


def _popen_extra_kwargs() -> dict:
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


@dataclass
class AIOSRuntimeHandle:
    proc: subprocess.Popen | None
    script_path: Path
    side: str

    @property
    def pid(self) -> int | None:
        return self.proc.pid if self.proc else None


class AIOSRuntimeAdapter:
    """Encapsulates AIOS-specific paths and subprocess behavior (Section 4.4)."""

    def __init__(self, paths: FsaaPaths) -> None:
        self._paths = paths

    def start(self, config: RuntimeStartConfig) -> RuntimeHandle:
        proc = subprocess.Popen(
            [sys.executable, str(config.script_path), *config.argv_extra],
            env=config.env,
            cwd=str(config.cwd),
            **_popen_extra_kwargs(),
        )
        return AIOSRuntimeHandle(proc=proc, script_path=config.script_path, side=config.side)

    def probe_liveness(self, handle: RuntimeHandle) -> LivenessState:
        h = handle
        if not isinstance(h, AIOSRuntimeHandle) or h.proc is None:
            return LivenessState(alive=False, detail="no_process")
        code = h.proc.poll()
        if code is None:
            return LivenessState(alive=True, detail="running")
        return LivenessState(alive=False, detail=f"exited:{code}")

    def probe_readiness(self, handle: RuntimeHandle) -> ReadinessState:
        liv = self.probe_liveness(handle)
        return ReadinessState(ready=liv.alive, detail=liv.detail)

    def shutdown(self, handle: RuntimeHandle, grace_seconds: float) -> ExitReport:
        h = handle
        if not isinstance(h, AIOSRuntimeHandle) or h.proc is None:
            return ExitReport(0, "no_process")
        proc = h.proc
        if proc.poll() is not None:
            return ExitReport(int(proc.returncode or 0), "already_exited")
        proc.terminate()
        try:
            proc.wait(timeout=grace_seconds)
            return ExitReport(int(proc.returncode or 0), "terminated")
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5.0)
            return ExitReport(int(proc.returncode or 0), "killed")

    def process_query_pattern_for_side(self, side: str) -> str:
        if side == "right":
            return "AIOS_Luna_Aria\\\\Aria\\\\AIOS_V3\\\\main_v3.py"
        return "AIOS_Luna_Aria\\\\Luna\\\\AIOS_V2\\\\main.py"

    def kill_existing_side_processes(self, side: str) -> int:
        if sys.platform != "win32":
            return 0
        pattern = self.process_query_pattern_for_side(side)
        cmd = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -and $_.CommandLine -match "
            f"'{pattern}' }} | "
            "Select-Object -ExpandProperty ProcessId"
        )
        cp = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        pids = []
        for raw in (cp.stdout or "").splitlines():
            v = raw.strip()
            if not v:
                continue
            try:
                pids.append(int(v))
            except ValueError:
                continue
        for pid in pids:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        return len(pids)

    def side_memory_mb(self, side: str) -> int:
        if sys.platform != "win32":
            return 0
        pattern = self.process_query_pattern_for_side(side)
        cmd = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -and $_.CommandLine -match "
            f"'{pattern}' }} | "
            "Measure-Object -Property WorkingSetSize -Sum | "
            "Select-Object -ExpandProperty Sum"
        )
        cp = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        raw = (cp.stdout or "").strip()
        if not raw:
            return 0
        try:
            return int(int(raw) / (1024 * 1024))
        except ValueError:
            return 0

    def request_dream_consolidation(self) -> None:
        subprocess.run(
            [
                str(self._paths.python_executable),
                str(self._paths.chat_entry),
                "set timer: dream in 1 beats",
            ],
            cwd=str(self._paths.workspace_root),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

    def stop_process_pid(self, pid: int) -> None:
        if sys.platform == "win32":
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        else:
            with contextlib.suppress(OSError):
                subprocess.run(["kill", "-TERM", str(pid)], check=False, timeout=5)
