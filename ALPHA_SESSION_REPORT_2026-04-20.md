# FSAA_AIOA Alpha Session Report (2026-04-20)

## Scope

This document records what was implemented and validated for the Alpha session, with direct log/report excerpts for traceability.

## What was built tonight

- Hardened the `brainstem_supervisor` lifecycle so every run emits explicit phases:
  - `runtime`, `dream_consolidation`, `shutdown`, `cleanup`, `restart`
- Enforced bounded non-auto behavior:
  - default bounded window (`loop` + `beat-seconds`)
  - full kill + cleanup at cycle end
- Added observe-only bounded success gate:
  - require at least one meaningful action (`min-actions-per-run`)
  - do not force which action; only observe whether one occurred
- Added alpha artifacts:
  - `ALPHA_MANIFEST.json`
  - `ALPHA_RUNBOOK.md`
- Standardized vocabulary in docs:
  - `AIOA` = Artificial Intelligence Operating Architecture
  - `AIOS` = runtime/system implementation
  - `FSAA` = sovereign framework (parallel concept to AGI target class)

## Validation summary

- Real PoC validator: `PASS`
- A/B turn-token gate: `INCONCLUSIVE` (correct due to valid-sample discipline)
- Supervisor bounded runs: observed meaningful action and clean shutdown
- Post-run process checks: `0` lingering Luna `main.py` processes

## Evidence excerpts (raw)

### 1) Real PoC report (`real_poc_report.json`)

```json
{
  "run_id": 4,
  "criteria": {
    "runtime_boot": true,
    "seeded_timers_executed": true,
    "forced_interrupt": true,
    "recovery_restart": true,
    "beat_progress_after_restart": true,
    "sandbox_side_effect_seen": true,
    "sleep_wake_cycle_seen": true,
    "dream_action_seen": true
  },
  "pass": true
}
```

### 2) A/B report (`ab_turn_token_report.json`)

```json
{
  "run_id": 3,
  "duration_seconds": 20,
  "sample_thresholds": {
    "min_valid_baseline": 20,
    "min_valid_pilot": 20
  },
  "outcome": "INCONCLUSIVE",
  "valid_samples": false,
  "delta": {
    "speak_ratio": 0.0769,
    "idle_ratio": 0.3846,
    "sandbox_ratio": 0.0769
  }
}
```

### 3) Auto threshold -> dream -> cleanup cycle (`fsaa_supervisor_events.jsonl`, run_id 12)

```json
{"ts":"2026-04-20T09:43:00.598677+00:00","run_id":12,"event":"auto_gc_threshold","side":"left","cycle":1,"mem_mb":625,"threshold_mb":256}
{"ts":"2026-04-20T09:43:00.598677+00:00","run_id":12,"event":"phase","phase":"dream_consolidation","status":"start","side":"left","cycle":1,"mem_mb":625,"threshold_mb":256}
{"ts":"2026-04-20T09:43:01.191677+00:00","run_id":12,"event":"phase","phase":"dream_consolidation","status":"complete","side":"left","cycle":1}
{"ts":"2026-04-20T09:43:04.453675+00:00","run_id":12,"event":"phase","phase":"cleanup","status":"start","side":"left","cycle":1}
{"ts":"2026-04-20T09:43:04.455175+00:00","run_id":12,"event":"phase","phase":"cleanup","status":"complete","side":"left","cycle":1}
{"ts":"2026-04-20T09:43:04.788176+00:00","run_id":12,"event":"outcome","label":"main_left.py","rc":0,"steady_state":false,"bounded_auto_shutdown":true,"killed_existing":0,"killed_post":0}
```

### 4) Bounded observe-only cycle with meaningful action (`fsaa_supervisor_events.jsonl`, run_id 16)

```json
{"ts":"2026-04-20T09:49:31.365676+00:00","run_id":16,"event":"run_start","side":"left","safe_low_ram":true,"auto":false,"loop_count":60,"beat_seconds":1.0,"min_actions_per_run":1,"kill_existing":true}
{"ts":"2026-04-20T09:50:00.842175+00:00","run_id":16,"event":"phase","phase":"bounded_target","status":"complete","side":"left","target_actions":1,"seen_count":1,"seen_actions":["speak"]}
{"ts":"2026-04-20T09:50:01.865675+00:00","run_id":16,"event":"phase","phase":"shutdown","status":"start","side":"left","reason":"bounded_action_target_reached","action_target_met":true}
{"ts":"2026-04-20T09:50:02.199175+00:00","run_id":16,"event":"phase","phase":"cleanup","status":"complete","side":"left","killed_post":0}
{"ts":"2026-04-20T09:50:02.199675+00:00","run_id":16,"event":"run_end","side":"left","rc":0,"safe_low_ram":true,"auto":false,"kill_existing":true}
```

### 5) Runtime action stream context (`autonomy_1hz.jsonl`)

```json
{"ts":"2026-04-20T09:47:14.932176+00:00","beat":0,"active":"luna","chosen_action":"speak","queue_depth":0,"s_n":0.330723,"note":"speak:(aria's voice, with a subtle tone of concern and clarity) \"resting, awaiting signal to recalibrate internal rhythms for "}
```

## Commands used for proof checks

- Bounded run:
  - `python -m fsaa.cli.entrypoint`
- Auto threshold test:
  - `python -m fsaa.control_plane.supervisor --side left --safe-low-ram --auto --gc-threshold-mb 256 --auto-max-cycles 1 --timeout 25 --beat-seconds 1`
- Real PoC validator (workspace harness, not part of FSAA_v2):
  - `python real_poc_runner.py` (from `${WORKSPACE_ROOT}/automation` with env set)
- A/B harness:
  - `python -m fsaa.experiments.ab_harness --duration-seconds 20 --min-valid-samples 20`

## Current alpha status

Alpha is operational with:

- explicit phase telemetry
- clean shutdown/cleanup behavior
- observe-only bounded cycle semantics
- reproducible validation command path

Known constraint:

- A/B outcome remains `INCONCLUSIVE` for the latest short window due to low/invalid baseline sample count; this is expected and policy-correct.
