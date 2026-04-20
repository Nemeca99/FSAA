"""Turn-token runtime: same subprocess surface as AIOS, readiness via brain socket (port 5151)."""

from __future__ import annotations

import json

from fsaa.observability.brain_status import fetch_brain_status_json
from fsaa.runtime.adapters.aios import AIOSRuntimeAdapter
from fsaa.runtime.protocol import ReadinessState, RuntimeHandle


class TurnTokenRuntimeAdapter(AIOSRuntimeAdapter):
    """CPU/GPU turn-token pilots: use AIOS lifecycle; gate readiness on ``fetch_brain_status_json``."""

    def probe_readiness(self, handle: RuntimeHandle) -> ReadinessState:
        liv = self.probe_liveness(handle)
        if not liv.alive:
            return ReadinessState(ready=False, detail=liv.detail)
        status = fetch_brain_status_json(self._paths)
        if status:
            detail = json.dumps(status, ensure_ascii=False)[:256]
            return ReadinessState(ready=True, detail=detail)
        return ReadinessState(ready=False, detail="brain_status_empty")
