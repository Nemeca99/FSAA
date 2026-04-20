from __future__ import annotations

from fsaa.runtime.adapters.mock import MockRuntimeAdapter
from fsaa.runtime.protocol import RuntimeStartConfig


def test_mock_adapter() -> None:
    ad = MockRuntimeAdapter()
    cfg = RuntimeStartConfig(
        script_path=__import__("pathlib").Path("."),
        env={},
        cwd=__import__("pathlib").Path("."),
        side="left",
    )
    h = ad.start(cfg)
    assert ad.probe_liveness(h).alive
    assert ad.probe_readiness(h).ready
    assert ad.shutdown(h, 1.0).exit_code == 0
