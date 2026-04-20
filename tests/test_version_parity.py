"""VERSION file and ALPHA_MANIFEST must match [project].version in pyproject.toml."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path


def test_version_file_matches_pyproject() -> None:
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as f:
        pv = tomllib.load(f)["project"]["version"]
    vf = (root / "VERSION").read_text(encoding="utf-8").strip()
    assert vf == pv
    with (root / "ALPHA_MANIFEST.json").open(encoding="utf-8") as f:
        mv = json.load(f)["version"]
    assert mv == pv
