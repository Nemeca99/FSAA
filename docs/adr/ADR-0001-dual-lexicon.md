# ADR-0001 — Control plane vs runtime adapter

## Status

Accepted (Alpha)

## Context

FSAA supervises and validates; it must not embed a single vendor runtime. Legacy code coupled `chat.py` and AIOS paths into the supervisor.

## Decision

- Introduce `fsaa.runtime.RuntimeAdapter` and `AIOSRuntimeAdapter` as the reference implementation.
- `fsaa.control_plane.supervisor` orchestrates only; AIOS-specific subprocess and Windows hygiene live in the adapter.

## Consequences

- Additional adapter implementations (mock, future HTTP) do not require supervisor changes.
