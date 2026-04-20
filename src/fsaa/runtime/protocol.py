"""Runtime adapter protocol (Section 4.4)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass
class RuntimeStartConfig:
    script_path: Path
    env: dict[str, str]
    cwd: Path
    side: str
    #: Extra argv after ``script_path`` (e.g. ``turn_token_loop.py`` CLI flags).
    argv_extra: tuple[str, ...] = ()


@dataclass
class LivenessState:
    alive: bool
    detail: str = ""


@dataclass
class ReadinessState:
    ready: bool
    detail: str = ""


@dataclass
class ExitReport:
    exit_code: int
    message: str = ""


@runtime_checkable
class RuntimeHandle(Protocol):
    """Opaque handle returned by RuntimeAdapter.start (implementation-specific)."""

    @property
    def pid(self) -> int | None: ...


@runtime_checkable
class RuntimeAdapter(Protocol):
    def start(self, config: RuntimeStartConfig) -> RuntimeHandle: ...

    def probe_liveness(self, handle: RuntimeHandle) -> LivenessState: ...

    def probe_readiness(self, handle: RuntimeHandle) -> ReadinessState: ...

    def shutdown(self, handle: RuntimeHandle, grace_seconds: float) -> ExitReport: ...
