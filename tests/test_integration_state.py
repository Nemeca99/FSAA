from __future__ import annotations

from fsaa.observability.integration_state import (
    FsaaIntegrationState,
    load_integration_state,
    save_integration_state,
)


def test_roundtrip_integration_state(tmp_path) -> None:
    p = tmp_path / "fsaa_integration_state.json"
    s = FsaaIntegrationState.default()
    save_integration_state(p, s)
    loaded = load_integration_state(p)
    assert loaded is not None
    assert loaded.core_loop_write_access_confirmed is False
    assert "steel_brain" in loaded.subsystems
