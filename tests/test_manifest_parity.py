"""ALPHA_MANIFEST pip_console_commands must stay in sync with pyproject [project.scripts]."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _manifest_target(desc: str) -> str:
    return desc.split(" - ", 1)[0].strip()


def test_manifest_console_commands_match_pyproject_scripts() -> None:
    root = _repo_root()
    with (root / "pyproject.toml").open("rb") as f:
        py = tomllib.load(f)
    scripts: dict[str, str] = py["project"]["scripts"]
    with (root / "ALPHA_MANIFEST.json").open(encoding="utf-8") as f:
        manifest = json.load(f)
    pip: dict[str, str] = manifest["pip_console_commands"]
    assert set(pip.keys()) == set(scripts.keys())
    for name, target in scripts.items():
        assert _manifest_target(pip[name]) == target
