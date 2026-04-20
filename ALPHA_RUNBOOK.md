# FSAA_AIOA Alpha Runbook

## Purpose

This runbook defines the official Alpha runtime commands and expected safety behavior (standalone `fsaa` package).

## Canonical terms

- `AIOA`: Artificial Intelligence Operating Architecture.
- `AIOS`: Your AI system runtime implementation.
- `FSAA`: Your sovereign cognition framework, parallel to AGI as your target class.

## Default (bounded) run

- Command:
  - `python -m fsaa.cli.entrypoint`
- Expected behavior:
  - Runs a meaningful bounded window (`--loop 60 --beat-seconds 1.0` by default).
  - Requires at least one meaningful action (`--min-actions-per-run 1`) before shutdown.
  - Performs hard shutdown.
  - Performs cleanup.
  - Leaves zero lingering side runtime processes.

## Speed and duration controls

- Runtime speed control:
  - `--beat-seconds` (lower = faster beats, higher = slower beats).
- Runtime duration control:
  - `--loop` (number of beats before bounded shutdown in non-auto mode).
- Bounded activity control:
  - `--min-actions-per-run` (minimum non-idle actions before bounded shutdown).
- Example longer bounded test:
  - `python -m fsaa.control_plane.supervisor --side left --safe-low-ram --loop 180 --beat-seconds 1.0 --min-actions-per-run 2`

## Auto mode run

- Command:
  - `python -m fsaa.control_plane.supervisor --side left --safe-low-ram --auto --gc-threshold-mb 8192 --auto-max-cycles 0`
- Expected behavior:
  - Runs continuously while below memory threshold.
  - On threshold breach, enters dream consolidation.
  - Executes shutdown and cleanup.
  - Restarts next cycle.

## Evidence to check

- `${WORKSPACE_ROOT}/automation/fsaa_supervisor_events.jsonl`
  - Look for explicit phase events:
    - `runtime:start|complete`
    - `dream_consolidation:start|complete` (auto threshold only)
    - `shutdown:start|complete`
    - `cleanup:start|complete`
    - `restart:start|complete` (auto mode)
- `${WORKSPACE_ROOT}/automation/translation_metrics.jsonl`
  - One line per IPC `guarded_commit`: `commit_latency_ms`, `outcome`, `loss` (reject=1), `run_id`, `actor`, `intent`.
- `${WORKSPACE_ROOT}/automation/authority_guard_log.jsonl`
  - Raw accept/reject stream for envelopes.

## Turn-token A/B harness (conclusive window)

- Baseline uses `python main.py` at workspace root (spawns runtime, then exits); rows accrue during the **post-boot sleep** window, not during the subprocess.
- Longer windows yield more `autonomy_1hz.jsonl` rows; if logs are sparse, lower `--min-valid-samples` or extend `--duration-seconds`.
- Example:

  `python -m fsaa.experiments.ab_harness --duration-seconds 300 --min-valid-samples 14`

## Hard guardrail

- If runtime errors, process must stop.
- No silent auto-restart unless `--auto` is explicitly enabled.
