from __future__ import annotations

from fsaa.control_plane.supervisor import parse_args


def test_parse_defaults() -> None:
    a = parse_args([])
    assert a.side == "left"
    assert a.loop == 60
    assert a.mode == "sidecar"
    assert a.turn_token_max_seconds == 120


def test_parse_turn_token_mode() -> None:
    a = parse_args(
        [
            "--mode",
            "turn_token",
            "--turn-token-max-seconds",
            "45",
            "--turn-token-cpu-beats",
            "3",
            "--turn-token-gpu-beats",
            "1",
        ]
    )
    assert a.mode == "turn_token"
    assert a.turn_token_max_seconds == 45
    assert a.turn_token_cpu_beats == 3
    assert a.turn_token_gpu_beats == 1
