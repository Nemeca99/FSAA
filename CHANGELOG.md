# Changelog

## 0.1.0a1

- Canonical package under `src/fsaa/`; workspace (`WORKSPACE_ROOT`: automation, Luna/Aria, chat) is not imported from package code—only env-based paths.
- `fsaa.experiments.ab_harness`, `fsaa.runtime.turn_token`, `fsaa.cli.entrypoint`, `main_fsaa.py` launchers.
- `scripts/verify_no_external_roots.py` enforces legacy path string literals are absent from `src/fsaa`, `scripts/`, and `tests/` only.
- Coverage: `ab_harness`, `turn_token`, and `supervisor` are omitted from the default coverage denominator (large integration surfaces); see `pyproject.toml`.
