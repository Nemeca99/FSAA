#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime
from types import SimpleNamespace

from fsaa.config.paths import get_paths
from fsaa.policy.turn_token import guard_or_raise

_NS: SimpleNamespace | None = None


def _harness_ns() -> SimpleNamespace:
    """Lazily resolve paths so importing this module does not require WORKSPACE_ROOT yet."""
    global _NS
    if _NS is None:
        p = get_paths()
        o = p.observability_dir
        w = p.workspace_root
        ns = SimpleNamespace()
        ns.ROOT = w
        ns.PYTHON = p.python_executable
        ns.UNIFIED_MAIN = w / "main.py"
        ns.SCHED_CFG = o / "cpu_middle_scheduler.json"
        ns.AUTONOMY_LOG = o / "autonomy_1hz.jsonl"
        ns.REPORT = o / "ab_turn_token_report.json"
        ns.REPORT_MD = o / "ab_turn_token_report.md"
        ns.RUN_STATE_JSON = o / "ab_turn_token_run_state.json"
        ns.AUDIT_LOG = o / "ab_turn_token_audit.jsonl"
        _NS = ns
    return _NS


def __getattr__(name: str) -> object:
    if name in {
        "ROOT",
        "PYTHON",
        "UNIFIED_MAIN",
        "SCHED_CFG",
        "AUTONOMY_LOG",
        "REPORT",
        "REPORT_MD",
        "RUN_STATE_JSON",
        "AUDIT_LOG",
    }:
        return getattr(_harness_ns(), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _hp() -> SimpleNamespace:
    return _harness_ns()


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def run_cmd(args: list[str], timeout: int = 120) -> tuple[int, str, str]:
    cp = subprocess.run(
        args,
        cwd=str(_hp().ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    return cp.returncode, (cp.stdout or "").strip(), (cp.stderr or "").strip()


def _load_last_audit_hash() -> str:
    if not _hp().AUDIT_LOG.is_file():
        return ""
    try:
        lines = _hp().AUDIT_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        h = str(obj.get("event_hash", "")).strip()
        if h:
            return h
    return ""


def _next_run_id() -> int:
    current = 0
    if _hp().RUN_STATE_JSON.is_file():
        try:
            obj = json.loads(_hp().RUN_STATE_JSON.read_text(encoding="utf-8"))
            current = int(obj.get("last_run_id", 0) or 0)
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            current = 0
    run_id = current + 1
    _hp().RUN_STATE_JSON.parent.mkdir(parents=True, exist_ok=True)
    _hp().RUN_STATE_JSON.write_text(json.dumps({"last_run_id": run_id}, indent=2), encoding="utf-8")
    return run_id


def append_audit_event(
    *,
    run_id: int,
    prev_hash: str,
    event_type: str,
    actor: str,
    payload: dict,
) -> str:
    event = {
        "timestamp": utc_now(),
        "run_id": run_id,
        "event_type": event_type,
        "actor": actor,
        "payload": payload,
        "prev_hash": prev_hash,
    }
    body = json.dumps(event, ensure_ascii=False, sort_keys=True)
    event_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    event["event_hash"] = event_hash
    _hp().AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _hp().AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event_hash


def audited_run_cmd(
    *,
    run_id: int,
    prev_hash: str,
    args: list[str],
    timeout: int,
    label: str,
) -> tuple[int, str, str, str]:
    guard_or_raise(
        run_id=run_id,
        prev_hash=prev_hash,
        event_type="intent",
        label=label,
        payload={"args": args, "timeout": timeout},
    )
    prev_hash = append_audit_event(
        run_id=run_id,
        prev_hash=prev_hash,
        event_type="intent",
        actor="ab_test_turn_token",
        payload={"label": label, "args": args, "timeout": timeout},
    )
    rc, out, err = run_cmd(args, timeout=timeout)
    guard_or_raise(
        run_id=run_id,
        prev_hash=prev_hash,
        event_type="outcome",
        label=label,
        payload={"rc": rc, "out": out[:500], "err": err[:500]},
    )
    prev_hash = append_audit_event(
        run_id=run_id,
        prev_hash=prev_hash,
        event_type="outcome",
        actor="ab_test_turn_token",
        payload={"label": label, "rc": rc, "out": out[:500], "err": err[:500]},
    )
    return rc, out, err, prev_hash


def _read_lines() -> list[str]:
    if not _hp().AUTONOMY_LOG.is_file():
        return []
    return _hp().AUTONOMY_LOG.read_text(encoding="utf-8", errors="replace").splitlines()


def slice_actions_by_index(start_idx: int, end_idx: int) -> dict:
    lines = _read_lines()
    start_idx = max(0, min(start_idx, len(lines)))
    end_idx = max(start_idx, min(end_idx, len(lines)))
    rows = []
    for line in lines[start_idx:end_idx]:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        rows.append(obj)
    c = Counter(str(r.get("chosen_action", "unknown")) for r in rows)
    beats = [
        int(r.get("beat", 0) or 0)
        for r in rows
        if isinstance(r.get("beat", 0), int) or str(r.get("beat", "")).isdigit()
    ]
    beat_min = min(beats) if beats else 0
    beat_max = max(beats) if beats else 0
    beat_span = max(0, beat_max - beat_min) if beats else 0
    unique_beats = len(set(beats)) if beats else 0
    heartbeat_progress = unique_beats > 1 and beat_span > 0
    stalls = max(0, len(rows) - unique_beats)
    err_rows = 0
    for r in rows:
        note = str(r.get("note", "")).lower()
        if "error" in note or "fail" in note or "unavailable" in note:
            err_rows += 1
    total = max(1, len(rows))
    return {
        "start_idx": start_idx,
        "end_idx": end_idx,
        "total_rows": len(rows),
        "actions": dict(c),
        "idle_ratio": round(c.get("idle", 0) / total, 4),
        "speak_ratio": round(c.get("speak", 0) / total, 4),
        "sandbox_ratio": round(c.get("sandbox_write", 0) / total, 4),
        "runtime_health": {
            "beat_min": beat_min,
            "beat_max": beat_max,
            "beat_span": beat_span,
            "unique_beats": unique_beats,
            "heartbeat_progression": heartbeat_progress,
            "stalls": stalls,
            "error_like_rows": err_rows,
        },
    }


def ensure_runtime() -> None:
    run_cmd([str(_hp().PYTHON), str(_hp().UNIFIED_MAIN)], timeout=60)
    time.sleep(2)


def main() -> int:
    run_id = _next_run_id()
    prev_hash = _load_last_audit_hash()
    prev_hash = append_audit_event(
        run_id=run_id,
        prev_hash=prev_hash,
        event_type="run_start",
        actor="ab_test_turn_token",
        payload={},
    )
    ap = argparse.ArgumentParser(description="A/B test baseline vs turn-token pilot")
    ap.add_argument("--duration-seconds", type=int, default=45)
    ap.add_argument("--min-valid-samples", type=int, default=20)
    ap.add_argument("--min-valid-baseline", type=int, default=0)
    ap.add_argument("--min-valid-pilot", type=int, default=0)
    args = ap.parse_args()
    duration = max(20, args.duration_seconds)
    min_valid_baseline = max(1, args.min_valid_baseline or args.min_valid_samples)
    min_valid_pilot = max(1, args.min_valid_pilot or args.min_valid_samples)
    baseline_timeout = max(60, int(duration) + 30)

    rc, out, err, prev_hash = audited_run_cmd(
        run_id=run_id,
        prev_hash=prev_hash,
        args=[str(_hp().PYTHON), str(_hp().UNIFIED_MAIN)],
        timeout=baseline_timeout,
        label="ensure_runtime_baseline",
    )
    if rc != 0:
        prev_hash = append_audit_event(
            run_id=run_id,
            prev_hash=prev_hash,
            event_type="run_end",
            actor="ab_test_turn_token",
            payload={"outcome": "FAIL", "reason": "runtime_boot_failed_baseline", "rc": rc},
        )
        print(
            json.dumps(
                {
                    "report_json": str(_hp().REPORT),
                    "report_md": str(_hp().REPORT_MD),
                    "outcome": "FAIL",
                    "error": "runtime_boot_failed_baseline",
                },
                indent=2,
            )
        )
        return 2
    # Unified workspace main.py returns after spawning the active runtime; autonomy rows accrue during the sleep window.
    time.sleep(2)
    base_start_idx = len(_read_lines())
    time.sleep(duration)
    base_end_idx = len(_read_lines())
    baseline = slice_actions_by_index(base_start_idx, base_end_idx)

    rc, out, err, prev_hash = audited_run_cmd(
        run_id=run_id,
        prev_hash=prev_hash,
        args=[str(_hp().PYTHON), str(_hp().UNIFIED_MAIN)],
        timeout=baseline_timeout,
        label="ensure_runtime_pilot",
    )
    if rc != 0:
        prev_hash = append_audit_event(
            run_id=run_id,
            prev_hash=prev_hash,
            event_type="run_end",
            actor="ab_test_turn_token",
            payload={"outcome": "FAIL", "reason": "runtime_boot_failed_pilot", "rc": rc},
        )
        print(
            json.dumps(
                {
                    "report_json": str(_hp().REPORT),
                    "report_md": str(_hp().REPORT_MD),
                    "outcome": "FAIL",
                    "error": "runtime_boot_failed_pilot",
                },
                indent=2,
            )
        )
        return 2
    time.sleep(2)
    pilot_start_idx = len(_read_lines())
    rc, out, err, prev_hash = audited_run_cmd(
        run_id=run_id,
        prev_hash=prev_hash,
        args=[
            str(_hp().PYTHON),
            "-m",
            "fsaa.runtime.turn_token",
            "--max-seconds",
            str(duration),
            "--cpu-turn-beats",
            "4",
            "--gpu-turn-beats",
            "2",
        ],
        timeout=duration + 30,
        label="turn_loop_pilot",
    )
    pilot_end_idx = len(_read_lines())
    pilot = slice_actions_by_index(pilot_start_idx, pilot_end_idx)

    baseline_valid = baseline["total_rows"] >= min_valid_baseline
    pilot_valid = pilot["total_rows"] >= min_valid_pilot
    valid_samples = baseline_valid and pilot_valid
    outcome = "INCONCLUSIVE"
    if valid_samples:
        speak_delta = round(pilot["speak_ratio"] - baseline["speak_ratio"], 4)
        outcome = "PASS" if speak_delta >= 0 else "FAIL"
    result = {
        "run_id": run_id,
        "generated_utc": utc_now(),
        "duration_seconds": duration,
        "window_duration_seconds": duration,
        "scheduler_config": (
            json.loads(_hp().SCHED_CFG.read_text(encoding="utf-8"))
            if _hp().SCHED_CFG.is_file()
            else {}
        ),
        "sample_thresholds": {
            "min_valid_baseline": min_valid_baseline,
            "min_valid_pilot": min_valid_pilot,
        },
        "baseline": baseline,
        "pilot": pilot,
        "turn_loop_rc": rc,
        "turn_loop_out": out[:200],
        "turn_loop_err": err[:200],
        "outcome": outcome,
        "valid_samples": valid_samples,
        "delta": {
            "speak_ratio": round(pilot["speak_ratio"] - baseline["speak_ratio"], 4),
            "idle_ratio": round(pilot["idle_ratio"] - baseline["idle_ratio"], 4),
            "sandbox_ratio": round(pilot["sandbox_ratio"] - baseline["sandbox_ratio"], 4),
        },
        "action_distributions": {
            "baseline": baseline["actions"],
            "pilot": pilot["actions"],
        },
        "runtime_health_notes": {
            "baseline": baseline["runtime_health"],
            "pilot": pilot["runtime_health"],
            "turn_loop_rc": rc,
            "turn_loop_err_non_empty": bool(err.strip()),
        },
        "audit_chain_head": _load_last_audit_hash(),
    }
    _hp().REPORT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    lines = [
        "# Turn Token A/B Report",
        "",
        f"- Generated (UTC): {result['generated_utc']}",
        f"- Window duration (s): {duration}",
        f"- Outcome: {outcome}",
        f"- Valid samples: {valid_samples}",
        f"- Baseline rows: {baseline['total_rows']} (min {min_valid_baseline})",
        f"- Pilot rows: {pilot['total_rows']} (min {min_valid_pilot})",
        "",
        "## Deltas (pilot - baseline)",
        f"- speak_ratio: {result['delta']['speak_ratio']}",
        f"- idle_ratio: {result['delta']['idle_ratio']}",
        f"- sandbox_ratio: {result['delta']['sandbox_ratio']}",
        "",
        "## Runtime Health",
        f"- baseline heartbeat_progression: {baseline['runtime_health']['heartbeat_progression']}, stalls: {baseline['runtime_health']['stalls']}, error_like_rows: {baseline['runtime_health']['error_like_rows']}",
        f"- pilot heartbeat_progression: {pilot['runtime_health']['heartbeat_progression']}, stalls: {pilot['runtime_health']['stalls']}, error_like_rows: {pilot['runtime_health']['error_like_rows']}",
        f"- turn_loop_rc: {rc}",
    ]
    _hp().REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    prev_hash = append_audit_event(
        run_id=run_id,
        prev_hash=prev_hash,
        event_type="run_end",
        actor="ab_test_turn_token",
        payload={"outcome": outcome, "valid_samples": valid_samples, "delta": result["delta"]},
    )
    result["audit_chain_tail"] = prev_hash
    _hp().REPORT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "report_json": str(_hp().REPORT),
                "report_md": str(_hp().REPORT_MD),
                "run_id": run_id,
                "outcome": outcome,
                "delta": result["delta"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
