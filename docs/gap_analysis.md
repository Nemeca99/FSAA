# Gap analysis (FSAA_v2)

`verify_no_literals.py` scans `src/fsaa/**/*.py` for drive-letter path literals. New code must not introduce ad-hoc `L:` (or other drive) literals; use `WORKSPACE_ROOT`, `FsaaPaths`, and environment overrides (`FSAA_IPC_SCHEMA`, `FSAA_REFLEX_POLICY`, etc.).

Historical Alpha work tracked parity between packaged resources and on-disk policy artifacts; FSAA_v2 keeps a single packaged IPC schema and reflex policy with optional overrides.

## Phase C guard parity (production-shaped)

- Committed `tests/fixtures/authority_guard_log.sample.jsonl` replays **accept** envelopes through `validate_envelope` + `validate_envelope_jsonschema`.
- `fsaa.policy.turn_token.guard_or_raise` matches the historical reject prefix `authority_guard_reject:`.
- `fsaa.observability.audit_chain` preserves **SHA-256** over `json.dumps(..., sort_keys=True)` for audit bodies (hash continuity with the A/B harness).

## IPC schema

The canonical schema lives at `src/fsaa/resources/ipc_schema.json` and is loaded via `importlib.resources` unless `FSAA_IPC_SCHEMA` points at a file. `tests/test_ipc_schema_parity.py` asserts packaged bytes match that file on disk.
