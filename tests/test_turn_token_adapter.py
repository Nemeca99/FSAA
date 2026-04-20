"""Exercise socket-gated readiness on ``TurnTokenRuntimeAdapter``."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fsaa.config.paths import get_paths
from fsaa.runtime.adapters.turn_token import TurnTokenRuntimeAdapter
from fsaa.runtime.protocol import LivenessState


def test_turn_token_probe_readiness_uses_brain_socket(monkeypatch) -> None:
    paths = get_paths()
    ad = TurnTokenRuntimeAdapter(paths)
    h = MagicMock()
    h.proc = MagicMock()
    h.proc.poll.return_value = None
    monkeypatch.setattr(ad, "probe_liveness", lambda _x: LivenessState(alive=True))
    with patch(
        "fsaa.runtime.adapters.turn_token.fetch_brain_status_json",
        return_value={"beat": 2},
    ):
        r = ad.probe_readiness(h)
    assert r.ready is True
    assert "beat" in r.detail
