from __future__ import annotations

import fsaa.control_plane.supervisor as supervisor
import fsaa.runtime.turn_token as turn_token


def test_supervisor_and_turn_token_main_callable() -> None:
    assert callable(supervisor.main)
    assert callable(turn_token.main)
