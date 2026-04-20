# Changelog

## 0.1.0-alpha.1 (FSAA_v2)

- Standalone package under `FSAA_v2/`: no imports from legacy sibling trees (old FSAA package, workspace `automation` scripts, or legacy supervisor sources); workspace access only via `WORKSPACE_ROOT` (and documented env overrides).
- `fsaa.experiments.ab_harness` replaces the old automation A/B script; `fsaa.runtime.turn_token` hosts the turn-token loop; `fsaa.cli.entrypoint` replaces the repo-root `main_fsaa` launcher.
- `scripts/verify_no_external_roots.py` enforces absence of legacy path string literals across the tree.
- Coverage: `ab_harness`, `turn_token`, and `supervisor` are omitted from the default coverage denominator (large integration surfaces); see `pyproject.toml`.
