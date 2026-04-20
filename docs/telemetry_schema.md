# Telemetry schema (Alpha)

## JSONL envelope (`telemetry_schema_version` = `1`)

New JSONL records use:

- `telemetry_schema_version`, `semconv_version`
- `fsaa`, `otel`, `ts` (ISO 8601 UTC with `Z` and millisecond precision)
- optional `monotonic_ns`

The **desk-level trace** shape used in production (`automation/desk_level_trace.jsonl`) is the reference for span-like events: `timestamp`, `actor`, `event` (start / complete / skip), `decision`, `outcome`, `input_context`, `skip_reason`. Map into nested payloads under `fsaa` / `otel` (e.g. OTel: `service.name` ← actor, span name ← decision, status attributes ← `skip_reason`).

IPC envelopes remain `schema_version: fsaa-ipc-v1` per `ipc_schema.json` (distinct from telemetry).

## Audit chain (A/B and automation)

SHA-256 over `json.dumps(event, ensure_ascii=False, sort_keys=True)` for the five fields `timestamp`, `run_id`, `event_type`, `actor`, `payload`, `prev_hash` — then `event_hash` appended. **FSAA preserves this scheme** in `fsaa.observability.audit_chain` so hash continuity holds across legacy and FSAA-era runs.

`_TURN_LOCK` in `fsaa.policy.guard` is a `threading.Lock` (in-process only); subprocesses each have an independent lock instance — see `docs/adr/ADR-0003-turn-lock-in-process-only.md`.

## Brain status (readiness)

Active runtime exposes TCP status on **127.0.0.1** port **`FSAA_BRAIN_STATUS_PORT`** (default **5151**): send line `{"type":"status"}\n` and read the first JSON line (e.g. `beat`). Used by `TurnTokenRuntimeAdapter` readiness and by `automation/turn_token_loop.py`.

## Integration state

Governance file **`fsaa_integration_state.json`** under the observability directory (default `automation/`) records authority delegation (`core_loop_write_access_confirmed`, per-subsystem map). See `fsaa.observability.integration_state`.
