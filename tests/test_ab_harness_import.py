from __future__ import annotations

import fsaa.experiments.ab_harness as ab


def test_ab_harness_main() -> None:
    assert callable(ab.main)
