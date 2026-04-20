from __future__ import annotations

import pytest

from fsaa.contracts.errors import ConfigurationError
from fsaa.runtime.adapters.mock import MockRuntimeAdapter
from fsaa.runtime.registry import resolve_adapter


def test_resolve_aios() -> None:
    a = resolve_adapter("aios")
    assert a.__class__.__name__ == "AIOSRuntimeAdapter"


def test_resolve_mock() -> None:
    m = resolve_adapter("mock")
    assert isinstance(m, MockRuntimeAdapter)


def test_resolve_unknown() -> None:
    with pytest.raises(ConfigurationError):
        resolve_adapter("nope")
