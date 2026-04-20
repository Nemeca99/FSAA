"""CPU/GPU turn-token pilot loop — workspace paths from ``WORKSPACE_ROOT`` only."""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import json
import os
import socket
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fsaa.config.paths import FsaaPaths, get_paths


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class TurnTokenPaths:
    workspace_root: Path
    python_exe: Path
    chat: Path
    scheduler_config: Path
    state_file: Path
    event_log: Path
    desk_trace_log: Path
    integration_state: Path
    brain_port: int

    @classmethod
    def from_fsaa(cls, p: FsaaPaths) -> TurnTokenPaths:
        obs = p.observability_dir
        return cls(
            workspace_root=p.workspace_root,
            python_exe=p.python_executable,
            chat=p.chat_entry,
            scheduler_config=obs / "cpu_middle_scheduler.json",
            state_file=obs / "master_turn_state.json",
            event_log=obs / "turn_token_events.jsonl",
            desk_trace_log=obs / "desk_level_trace.jsonl",
            integration_state=obs / "turn_token_integration_state.json",
            brain_port=p.brain_status_port,
        )


def brain_status(paths: TurnTokenPaths, timeout: float = 2.0) -> dict[str, Any]:
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(("127.0.0.1", paths.brain_port))
        s.sendall(b'{"type":"status"}\n')
        data = b""
        while b"\n" not in data:
            chunk = s.recv(4096)
            if not chunk:
                break
            data += chunk
        if not data:
            return {}
        return json.loads(data.split(b"\n")[0].decode("utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    finally:
        if s is not None:
            with contextlib.suppress(OSError):
                s.close()


def append_event(paths: TurnTokenPaths, payload: dict[str, Any]) -> None:
    paths.event_log.parent.mkdir(parents=True, exist_ok=True)
    with paths.event_log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def append_desk_trace(
    paths: TurnTokenPaths,
    event_type: str,
    *,
    actor: str,
    decision: str,
    outcome: str,
    input_context: dict[str, Any],
    skip_reason: str = "",
) -> None:
    paths.desk_trace_log.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": utc_now(),
        "actor": actor,
        "event": event_type,
        "decision": decision,
        "outcome": outcome,
        "input_context": input_context,
        "skip_reason": skip_reason,
    }
    with paths.desk_trace_log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_state(paths: TurnTokenPaths, payload: dict[str, Any]) -> None:
    paths.state_file.parent.mkdir(parents=True, exist_ok=True)
    paths.state_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _cores_to_mask(cores: list[int]) -> int:
    mask = 0
    for c in cores:
        if isinstance(c, int) and c >= 0:
            mask |= 1 << c
    return mask


def _set_current_process_affinity(mask: int) -> bool:
    if mask <= 0:
        return False
    if not hasattr(ctypes, "windll"):
        return False
    try:
        k32 = ctypes.windll.kernel32
        proc = k32.GetCurrentProcess()
        ok = k32.SetProcessAffinityMask(proc, ctypes.c_size_t(mask))
        return bool(ok)
    except OSError:
        return False


def _load_scheduler_config(paths: TurnTokenPaths) -> dict[str, Any]:
    default: dict[str, Any] = {
        "cpu_llm_cores": [0, 1, 2, 3],
        "middle_cores": [4, 5, 6, 7],
        "cpu_turn_beats": 4,
        "gpu_turn_beats": 2,
        "llm_threads": 4,
        "turn_token_integration_enabled": False,
        "turn_token_experiment_id": "turn_token_external_pilot",
        "rollback_external_pilot": True,
        "desk_trace_min_events": 3,
    }
    cfg_path = paths.scheduler_config
    if not cfg_path.is_file():
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            merged = dict(default)
            merged.update(raw)
            return merged
    except (OSError, json.JSONDecodeError):
        pass
    return default


def run_chat(
    paths: TurnTokenPaths,
    message: str,
    timeout_s: int = 20,
    *,
    llm_affinity_mask: int = 0,
    llm_threads: int = 4,
) -> tuple[int, str, str]:
    if llm_affinity_mask > 0:
        _set_current_process_affinity(llm_affinity_mask)
    extra = {
        "OMP_NUM_THREADS": str(max(1, int(llm_threads))),
        "AIOS_CPU_LLM_THREADS": str(max(1, int(llm_threads))),
    }
    cp = subprocess.run(
        [str(paths.python_exe), str(paths.chat), message],
        cwd=str(paths.workspace_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
        check=False,
        env={**dict(os.environ), **extra},
    )
    return cp.returncode, (cp.stdout or "").strip(), (cp.stderr or "").strip()


def choose_cpu_stage_action(beat: int, staged_gpu: list[str]) -> tuple[str, dict[str, Any]]:
    if beat % 3 == 0:
        staged_gpu.append("set timer: queue speak in 1 beats")
    elif beat % 5 == 0:
        staged_gpu.append("set timer: dream in 1 beats")
    staged_gpu[:] = staged_gpu[-16:]
    return "stage", {"staged_depth": len(staged_gpu)}


def choose_gpu_commit_action(
    paths: TurnTokenPaths,
    staged_gpu: list[str],
    *,
    llm_mask: int,
    llm_threads: int,
) -> tuple[str, dict[str, Any]]:
    if staged_gpu:
        msg = staged_gpu.pop(0)
        rc, out, err = run_chat(paths, msg, llm_affinity_mask=llm_mask, llm_threads=llm_threads)
        return "commit", {"message": msg, "rc": rc, "out": out[:120], "err": err[:120]}
    msg = "set timer: queue speak in 1 beats"
    rc, out, err = run_chat(paths, msg, llm_affinity_mask=llm_mask, llm_threads=llm_threads)
    return "commit_fallback", {"message": msg, "rc": rc, "out": out[:120], "err": err[:120]}


def emit_integration_seam(
    paths: TurnTokenPaths,
    *,
    enabled: bool,
    experiment_id: str,
    rollback_external_pilot: bool,
) -> None:
    payload = {
        "ts": utc_now(),
        "integration_enabled": enabled,
        "experiment_id": experiment_id,
        "rollback_external_pilot": rollback_external_pilot,
        "single_turn_authority": "turn_token_loop",
        "schema_lock_state": "enforced_in_runtime",
        "core_loop_write_access_confirmed": False,
        "note": "External pilot remains authority until core write access is confirmed.",
    }
    paths.integration_state.parent.mkdir(parents=True, exist_ok=True)
    paths.integration_state.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="CPU->GPU master turn token loop pilot")
    ap.add_argument("--cpu-turn-beats", type=int, default=4)
    ap.add_argument("--gpu-turn-beats", type=int, default=2)
    ap.add_argument("--max-seconds", type=int, default=120)
    ap.add_argument("--sleep-ms", type=int, default=800)
    ap.add_argument("--integration-enabled", action="store_true")
    ap.add_argument("--experiment-id", type=str, default="turn_token_external_pilot")
    ap.add_argument("--rollback-external-pilot", action="store_true")
    ap.add_argument("--no-rollback-external-pilot", action="store_true")
    args = ap.parse_args()

    tp = TurnTokenPaths.from_fsaa(get_paths())
    cfg = _load_scheduler_config(tp)
    cpu_turn_beats = int(cfg.get("cpu_turn_beats", args.cpu_turn_beats) or args.cpu_turn_beats)
    gpu_turn_beats = int(cfg.get("gpu_turn_beats", args.gpu_turn_beats) or args.gpu_turn_beats)
    llm_threads = int(cfg.get("llm_threads", 4) or 4)
    integration_enabled = bool(cfg.get("turn_token_integration_enabled", False) or args.integration_enabled)
    experiment_id = str(cfg.get("turn_token_experiment_id", "turn_token_external_pilot") or "turn_token_external_pilot")
    if args.experiment_id and args.experiment_id != "turn_token_external_pilot":
        experiment_id = args.experiment_id
    rollback_external_pilot = bool(cfg.get("rollback_external_pilot", True))
    if args.rollback_external_pilot:
        rollback_external_pilot = True
    if args.no_rollback_external_pilot:
        rollback_external_pilot = False
    llm_mask = _cores_to_mask(list(cfg.get("cpu_llm_cores", [])))
    middle_mask = _cores_to_mask(list(cfg.get("middle_cores", [])))
    if middle_mask > 0:
        _set_current_process_affinity(middle_mask)

    owner = "cpu"
    beats_left = max(1, cpu_turn_beats)
    staged_gpu: list[str] = []
    started = time.time()
    last_beat = -1
    emit_integration_seam(
        tp,
        enabled=integration_enabled,
        experiment_id=experiment_id,
        rollback_external_pilot=rollback_external_pilot,
    )

    while time.time() - started < max(10, args.max_seconds):
        st = brain_status(tp)
        beat = int(st.get("beat", 0) or 0)
        if beat <= last_beat:
            append_desk_trace(
                tp,
                "skip",
                actor="turn_token_loop",
                decision="wait_for_new_beat",
                outcome="skip",
                input_context={"beat": beat, "last_beat": last_beat, "owner": owner},
                skip_reason="no_heartbeat_progress",
            )
            time.sleep(max(100, args.sleep_ms) / 1000.0)
            continue
        last_beat = beat

        if beats_left <= 0:
            if owner == "cpu":
                owner = "gpu"
                beats_left = max(1, gpu_turn_beats)
            else:
                owner = "cpu"
                beats_left = max(1, cpu_turn_beats)

        decision = "noop"
        details: dict[str, Any] = {}
        append_desk_trace(
            tp,
            "start",
            actor="turn_token_loop",
            decision="evaluate_turn",
            outcome="start",
            input_context={
                "beat": beat,
                "owner": owner,
                "beats_left": beats_left,
                "staged_depth": len(staged_gpu),
            },
        )
        if owner == "cpu":
            decision, details = choose_cpu_stage_action(beat, staged_gpu)
        else:
            decision, details = choose_gpu_commit_action(
                tp, staged_gpu, llm_mask=llm_mask, llm_threads=llm_threads
            )

        beats_left -= 1
        skip_reason = ""
        if decision == "commit_fallback":
            skip_reason = "no_staged_gpu_proposal"
        elif decision == "noop":
            skip_reason = "no_decision"
        append_desk_trace(
            tp,
            "complete",
            actor="turn_token_loop",
            decision=decision,
            outcome="complete",
            input_context={
                "beat": beat,
                "owner": owner,
                "beats_left_after": beats_left,
                "staged_depth": len(staged_gpu),
            },
            skip_reason=skip_reason,
        )
        payload = {
            "ts": utc_now(),
            "beat": beat,
            "turn_owner": owner,
            "turn_beats_left": beats_left,
            "decision": decision,
            "details": details,
        }
        append_event(tp, payload)
        write_state(
            tp,
            {
                "ts": payload["ts"],
                "beat": beat,
                "turn_owner": owner,
                "turn_beats_left": beats_left,
                "staged_gpu_depth": len(staged_gpu),
                "decision": decision,
                "cpu_turn_beats": cpu_turn_beats,
                "gpu_turn_beats": gpu_turn_beats,
                "llm_threads": llm_threads,
                "llm_affinity_mask": llm_mask,
                "middle_affinity_mask": middle_mask,
            },
        )
        time.sleep(max(100, args.sleep_ms) / 1000.0)

    append_event(tp, {"ts": utc_now(), "event": "turn_token_loop_complete"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
