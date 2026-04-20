from __future__ import annotations

import pytest

from fsaa.config.paths import clear_paths_cache
from fsaa.contracts.errors import ConfigurationError
from fsaa.runtime.adapters.turn_token import TurnTokenRuntimeAdapter
from fsaa.runtime.registry import resolve_adapter


def test_resolve_turn_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FSAA_RUNTIME_ADAPTER", "turn_token")
    clear_paths_cache()
    ad = resolve_adapter()
    assert isinstance(ad, TurnTokenRuntimeAdapter)
    clear_paths_cache()
    monkeypatch.delenv("FSAA_RUNTIME_ADAPTER", raising=False)


def test_resolve_unknown_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FSAA_RUNTIME_ADAPTER", "nope")
    clear_paths_cache()
    with pytest.raises(ConfigurationError):
        resolve_adapter()
    monkeypatch.delenv("FSAA_RUNTIME_ADAPTER", raising=False)
    clear_paths_cache()
