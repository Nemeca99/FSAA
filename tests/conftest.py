"""Pytest fixtures — WORKSPACE_ROOT for FsaaPaths."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _workspace_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """Workspace = parent of this repo (e.g. Continue): automation, chat.py, AIOS_Luna_Aria; this package may be a subfolder."""
    # Import fsaa only inside the fixture so pytest-cov can enable tracing before the first
    # import of the package (avoids CoverageWarning: module-not-measured).
    from pathlib import Path

    from fsaa.config.paths import clear_paths_cache

    fsaa_repo = Path(__file__).resolve().parents[1]
    workspace = fsaa_repo.parent
    monkeypatch.setenv("WORKSPACE_ROOT", str(workspace))
    clear_paths_cache()
    yield
    clear_paths_cache()
