"""Packaged policy artifacts (IPC schema, reflex policy)."""

from __future__ import annotations

from importlib import resources


def packaged_ipc_schema_bytes() -> bytes:
    return (resources.files("fsaa.resources") / "ipc_schema.json").read_bytes()


def packaged_reflex_policy_bytes() -> bytes:
    return (resources.files("fsaa.resources") / "reflex_policy.json").read_bytes()
