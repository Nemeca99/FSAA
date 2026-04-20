"""Packaged IPC schema matches the canonical file under ``src/fsaa/resources``."""

from __future__ import annotations

from pathlib import Path

from fsaa.resources import packaged_ipc_schema_bytes


def test_packaged_ipc_schema_matches_resources_file() -> None:
    root = Path(__file__).resolve().parents[1]
    on_disk = (root / "src" / "fsaa" / "resources" / "ipc_schema.json").read_bytes()
    packaged = packaged_ipc_schema_bytes()
    assert on_disk == packaged, "Keep ipc_schema.json and packaged bytes in sync."
