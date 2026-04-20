from __future__ import annotations

from pathlib import Path

from fsaa.control_plane.supervisor import meaningful_actions_since_lines


def test_fixture_categories() -> None:
    fixture = Path(__file__).parent / "fixtures" / "autonomy_1hz.fixture.jsonl"
    lines = fixture.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 20
    n, actions = meaningful_actions_since_lines(lines, 0)
    assert n == len(actions)
    assert n > 0
    _, after_10 = meaningful_actions_since_lines(lines, 10)
    assert len(after_10) >= 1
