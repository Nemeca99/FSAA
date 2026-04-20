from __future__ import annotations

import fsaa.experiments.real_poc_runner as real_poc


def test_real_poc_runner_importable() -> None:
    assert callable(real_poc.main)
