# ADR-0003: `_TURN_LOCK` is in-process only (Alpha)

## Status

Accepted — Alpha

## Context

Legacy `authority_guard` serializes `guarded_commit` with `threading.Lock()` (`_TURN_LOCK`). That provides mutual exclusion **within one Python process** only.

Supervisor and sidecars run as **separate processes** (each has its own interpreter and its own `threading.Lock` instance). The lock does **not** coordinate commits across processes.

## Decision (Option A — honest Alpha)

- Preserve `threading.Lock` semantics **exactly** for in-process serialization, matching the legacy port.
- Document explicitly that cross-process mutual exclusion is **out of scope** for Alpha; observed correctness today depends on **low contention**, not on the lock spanning processes.

## Consequences

- Beta may introduce a maintainer-approved cross-process mechanism (e.g. file lock under `FSAA_OBSERVABILITY_DIR`) with an ADR and migration plan if multi-writer contention becomes real.
