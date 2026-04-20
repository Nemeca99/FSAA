"""Resolve FSAA_RUNTIME_ADAPTER name to implementation."""

from __future__ import annotations

import os

from fsaa.config.paths import FsaaPaths, get_paths
from fsaa.contracts.errors import ConfigurationError
from fsaa.runtime.adapters.aios import AIOSRuntimeAdapter
from fsaa.runtime.adapters.mock import MockRuntimeAdapter
from fsaa.runtime.adapters.turn_token import TurnTokenRuntimeAdapter
from fsaa.runtime.protocol import RuntimeAdapter


def resolve_adapter(name: str | None = None, *, paths: FsaaPaths | None = None) -> RuntimeAdapter:
    raw = (name or os.environ.get("FSAA_RUNTIME_ADAPTER") or "aios").strip().lower()
    p = paths or get_paths()
    if raw == "aios":
        return AIOSRuntimeAdapter(p)
    if raw == "turn_token":
        return TurnTokenRuntimeAdapter(p)
    if raw == "mock":
        return MockRuntimeAdapter()
    raise ConfigurationError(
        f"Unknown FSAA_RUNTIME_ADAPTER: {raw!r} (expected 'aios', 'turn_token', or 'mock')"
    )
