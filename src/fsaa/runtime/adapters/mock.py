"""Mock runtime adapter for tests."""

from __future__ import annotations

from dataclasses import dataclass

from fsaa.runtime.protocol import (
    ExitReport,
    LivenessState,
    ReadinessState,
    RuntimeHandle,
    RuntimeStartConfig,
)


@dataclass
class MockRuntimeHandle:
    _pid: int = 42

    @property
    def pid(self) -> int | None:
        return self._pid


class MockRuntimeAdapter:
    def start(self, config: RuntimeStartConfig) -> RuntimeHandle:
        return MockRuntimeHandle()

    def probe_liveness(self, handle: RuntimeHandle) -> LivenessState:
        return LivenessState(alive=True)

    def probe_readiness(self, handle: RuntimeHandle) -> ReadinessState:
        return ReadinessState(ready=True)

    def shutdown(self, handle: RuntimeHandle, grace_seconds: float) -> ExitReport:
        return ExitReport(0, "mock")
