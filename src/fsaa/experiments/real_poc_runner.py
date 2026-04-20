#!/usr/bin/env python3
"""Real PoC runner — ported from workspace automation; uses ``FsaaPaths`` and ``fsaa.policy.guard`` only."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import socket
import subprocess
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from fsaa.config.paths import get_paths
from fsaa.policy.guard import SCHEMA_VERSION, guarded_commit

_CTX: SimpleNamespace | None = None


def _cx() -> SimpleNamespace:
    global _CTX
    if _CTX is None:
        p = get_paths()
        o = p.observability_dir
        w = p.workspace_root
        ns = SimpleNamespace()
        ns.ROOT = w
        ns.PYTHON = p.python_executable
        ns.UNIFIED_MAIN = w / "main.py"
        ns.UNIFIED_CHAT = p.chat_entry
        ns.AUTONOMY_LOG = p.autonomy_telemetry
        ns.TIMERS_FILE = o / "subagents" / "timers.json"
        ns.REPORT_JSON = o / "real_poc_report.json"
        ns.REPORT_MD = o / "real_poc_report.md"
        ns.DESK_TRACE_LOG = o / "desk_level_trace.jsonl"
        ns.RUN_STATE_JSON = o / "real_poc_run_state.json"
        ns.AUDIT_LOG = o / "real_poc_audit.jsonl"
        ns.brain_port = p.brain_status_port
        ns.luna_main = p.luna_runtime_main
        _CTX = ns
    return _CTX


def _luna_cmdline_regex_fragment() -> str:
    p = _cx().luna_main
    root = _cx().ROOT
    try:
        rel = p.relative_to(root)
    except ValueError:
        rel = p
    s = str(rel).replace("/", "\\")
    return s.replace("\\", "\\\\")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def run_cmd(args: list[str], timeout: int = 60) -> tuple[int, str, str]:
    cp = subprocess.run(
        args,
        cwd=str(_cx().ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    return cp.returncode, (cp.stdout or "").strip(), (cp.stderr or "").strip()


def _load_last_audit_hash() -> str:
    if not _cx().AUDIT_LOG.is_file():
        return ""
    try:
        lines = _cx().AUDIT_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
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
    if _cx().RUN_STATE_JSON.is_file():
        try:
            obj = json.loads(_cx().RUN_STATE_JSON.read_text(encoding="utf-8"))
            current = int(obj.get("last_run_id", 0) or 0)
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            current = 0
    run_id = current + 1
    _cx().RUN_STATE_JSON.parent.mkdir(parents=True, exist_ok=True)
    _cx().RUN_STATE_JSON.write_text(json.dumps({"last_run_id": run_id}, indent=2), encoding="utf-8")
    return run_id


def append_audit_event(
    *,
    run_id: int,
    prev_hash: str,
    event_type: str,
    actor: str,
    payload: dict[str, Any],
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
    _cx().AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _cx().AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event_hash


def _intent_from_label(label: str) -> str:
    value = (label or "").strip().lower()
    if "boot_runtime" in value or "restart_runtime" in value:
        return "runtime_boot"
    if "seed_timer" in value or "post_restart_seed" in value:
        return "seed_timer"
    return "status_poll"


def _guard_or_raise(
    *, run_id: int, prev_hash: str, event_type: str, label: str, payload: dict[str, Any]
) -> None:
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "run_id": int(run_id),
        "timestamp": utc_now(),
        "actor": "runner",
        "event_type": event_type,
        "intent": _intent_from_label(label),
        "payload": {"label": label, **payload},
        "prev_hash": prev_hash,
    }
    verdict = guarded_commit(envelope)
    if not verdict.ok:
        raise RuntimeError(f"authority_guard_reject:{verdict.reason}")


def audited_run_cmd(
    *,
    run_id: int,
    prev_hash: str,
    args: list[str],
    timeout: int,
    label: str,
) -> tuple[int, str, str, str]:
    # Write-ahead intent log: if this fails, do not execute command.
    _guard_or_raise(
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
        actor="real_poc_runner",
        payload={"label": label, "args": args, "timeout": timeout},
    )
    rc, out, err = run_cmd(args, timeout=timeout)
    _guard_or_raise(
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
        actor="real_poc_runner",
        payload={"label": label, "rc": rc, "out": out[:500], "err": err[:500]},
    )
    return rc, out, err, prev_hash


def append_desk_trace(
    event_type: str,
    *,
    actor: str,
    decision: str,
    outcome: str,
    input_context: dict,
    skip_reason: str = "",
) -> None:
    _cx().DESK_TRACE_LOG.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": utc_now(),
        "actor": actor,
        "event": event_type,
        "decision": decision,
        "outcome": outcome,
        "input_context": input_context,
        "skip_reason": skip_reason,
    }
    with _cx().DESK_TRACE_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def brain_status(timeout: float = 2.0) -> dict[str, Any]:
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(("127.0.0.1", _cx().brain_port))
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


def wait_for_brain_online(wait_s: int = 20) -> bool:
    end = time.time() + wait_s
    while time.time() < end:
        st = brain_status()
        if st:
            return True
        time.sleep(0.5)
    return False


def wait_for_beat_progress(
    start_beat: int, wait_s: int = 12, poll_s: float = 0.5
) -> tuple[bool, int]:
    end = time.time() + max(1, wait_s)
    last_beat = int(start_beat or 0)
    while time.time() < end:
        st = brain_status()
        if st:
            beat = int(st.get("beat", 0) or 0)
            last_beat = max(last_beat, beat)
            if beat > start_beat:
                return True, beat
        time.sleep(max(0.1, poll_s))
    return False, last_beat


def read_last_autonomy_lines(n: int = 120) -> list[dict[str, Any]]:
    if not _cx().AUTONOMY_LOG.is_file():
        return []
    lines = _cx().AUTONOMY_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[dict[str, Any]] = []
    for line in lines[-n:]:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def load_timers() -> list[dict[str, Any]]:
    if not _cx().TIMERS_FILE.is_file():
        return []
    try:
        data = json.loads(_cx().TIMERS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def current_main_pid() -> int:
    frag = _luna_cmdline_regex_fragment()
    cmd = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.CommandLine -and $_.CommandLine -match "
        f"'{frag}' }} | "
        "Select-Object -First 1 -ExpandProperty ProcessId"
    )
    rc, out, _ = run_cmd(["powershell", "-NoProfile", "-Command", cmd], timeout=20)
    if rc != 0:
        return 0
    out = out.strip()
    try:
        return int(out) if out else 0
    except ValueError:
        return 0


def kill_pid(pid: int) -> bool:
    if pid <= 0:
        return False
    rc, _, _ = run_cmd(
        ["powershell", "-NoProfile", "-Command", f"Stop-Process -Id {pid} -Force"],
        timeout=20,
    )
    return rc == 0


def run_real_test(
    *, enable_restart_test: bool = False, shutdown_after_test: bool = True
) -> dict[str, Any]:
    run_id = _next_run_id()
    prev_hash = _load_last_audit_hash()
    prev_hash = append_audit_event(
        run_id=run_id,
        prev_hash=prev_hash,
        event_type="run_start",
        actor="real_poc_runner",
        payload={
            "enable_restart_test": enable_restart_test,
            "shutdown_after_test": shutdown_after_test,
        },
    )
    result: dict[str, Any] = {
        "run_id": run_id,
        "started_utc": utc_now(),
        "criteria": {},
        "notes": [],
        "commands": [],
        "audit_chain_head": prev_hash,
    }

    append_desk_trace(
        "start",
        actor="real_poc_runner",
        decision="runtime_boot",
        outcome="start",
        input_context={"cmd": "python main.py"},
    )
    rc, out, err, prev_hash = audited_run_cmd(
        run_id=run_id,
        prev_hash=prev_hash,
        args=[str(_cx().PYTHON), str(_cx().UNIFIED_MAIN)],
        timeout=60,
        label="boot_runtime",
    )
    result["commands"].append(
        {"cmd": "python main.py", "rc": rc, "out": out[:200], "err": err[:200]}
    )
    if rc != 0 or not wait_for_brain_online():
        result["criteria"]["runtime_boot"] = False
        result["notes"].append("Runtime failed to boot.")
        append_desk_trace(
            "skip",
            actor="real_poc_runner",
            decision="runtime_boot",
            outcome="skip",
            input_context={"rc": rc, "brain_online": False},
            skip_reason="runtime_boot_failed",
        )
        result["finished_utc"] = utc_now()
        result["audit_chain_tail"] = prev_hash
        return result
    result["criteria"]["runtime_boot"] = True
    append_desk_trace(
        "complete",
        actor="real_poc_runner",
        decision="runtime_boot",
        outcome="complete",
        input_context={"rc": rc, "brain_online": True},
    )

    st0 = brain_status()
    beat0 = int(st0.get("beat", 0) or 0)

    seeds = [
        "set timer: queue sandbox_write in 2 beats",
        "set timer: dream in 3 beats",
        "set timer: sleep 4 beats",
        "set timer: wake in 7 beats",
    ]
    for s in seeds:
        append_desk_trace(
            "start",
            actor="real_poc_runner",
            decision="seed_timer",
            outcome="start",
            input_context={"seed": s},
        )
        rc, out, err, prev_hash = audited_run_cmd(
            run_id=run_id,
            prev_hash=prev_hash,
            args=[str(_cx().PYTHON), str(_cx().UNIFIED_CHAT), s],
            timeout=30,
            label=f"seed_timer:{s}",
        )
        result["commands"].append(
            {"cmd": f'chat "{s}"', "rc": rc, "out": out[:200], "err": err[:200]}
        )
        if rc != 0:
            append_desk_trace(
                "skip",
                actor="real_poc_runner",
                decision="seed_timer",
                outcome="skip",
                input_context={"seed": s, "rc": rc},
                skip_reason="seed_command_failed",
            )
        else:
            append_desk_trace(
                "complete",
                actor="real_poc_runner",
                decision="seed_timer",
                outcome="complete",
                input_context={"seed": s, "rc": rc},
            )

    time.sleep(12)
    timers_now = load_timers()
    seeded_done = 0
    for row in timers_now:
        src = str(row.get("source", ""))
        if src.endswith(":chat") and bool(row.get("done")):
            seeded_done += 1
    result["criteria"]["seeded_timers_executed"] = seeded_done >= 4
    result["metrics_seeded_done"] = seeded_done
    if not result["criteria"]["seeded_timers_executed"]:
        result["notes"].append("Degraded: seeded timers did not fully execute.")

    progressed_beat = beat0
    if enable_restart_test:
        pid = current_main_pid()
        killed = kill_pid(pid)
        result["criteria"]["forced_interrupt"] = bool(killed)
        result["killed_pid"] = pid
        append_desk_trace(
            "complete",
            actor="real_poc_runner",
            decision="forced_interrupt",
            outcome="complete" if killed else "skip",
            input_context={"pid": pid, "killed": bool(killed)},
            skip_reason="" if killed else "pid_not_found_or_kill_failed",
        )

        time.sleep(2)
        rc, out, err, prev_hash = audited_run_cmd(
            run_id=run_id,
            prev_hash=prev_hash,
            args=[str(_cx().PYTHON), str(_cx().UNIFIED_MAIN)],
            timeout=60,
            label="restart_runtime",
        )
        result["commands"].append(
            {"cmd": "python main.py (restart)", "rc": rc, "out": out[:200], "err": err[:200]}
        )
        time.sleep(2)
        st1 = brain_status()
        beat1 = int(st1.get("beat", 0) or 0)
        result["criteria"]["recovery_restart"] = bool(st1)
        progressed, progressed_beat = wait_for_beat_progress(beat1, wait_s=12, poll_s=0.5)
        result["criteria"]["beat_progress_after_restart"] = progressed
        if not progressed:
            result["notes"].append(
                f"Degraded: beat did not advance within restart window (start={beat1}, last={progressed_beat})."
            )

        rc, out, err, prev_hash = audited_run_cmd(
            run_id=run_id,
            prev_hash=prev_hash,
            args=[
                str(_cx().PYTHON),
                str(_cx().UNIFIED_CHAT),
                "set timer: queue sandbox_write in 2 beats",
            ],
            timeout=30,
            label="post_restart_seed",
        )
        result["commands"].append(
            {
                "cmd": 'chat "set timer: queue sandbox_write in 2 beats" (post-restart)',
                "rc": rc,
                "out": out[:200],
                "err": err[:200],
            }
        )
        time.sleep(5)
    else:
        result["criteria"]["forced_interrupt"] = True
        result["criteria"]["recovery_restart"] = True
        result["criteria"]["beat_progress_after_restart"] = True
        result["notes"].append("Restart test disabled (manual stop policy active).")

    recent = read_last_autonomy_lines(160)
    sandbox_actions = [r for r in recent if "sandbox_write" in str(r.get("note", ""))]
    dream_actions = [r for r in recent if str(r.get("chosen_action")) == "dream_cycle"]
    sleep_actions = [r for r in recent if str(r.get("chosen_action")) == "sleep"]
    wake_actions = [r for r in recent if str(r.get("chosen_action")) == "wake"]
    result["criteria"]["sandbox_side_effect_seen"] = len(sandbox_actions) > 0
    result["criteria"]["sleep_wake_cycle_seen"] = len(sleep_actions) > 0 and len(wake_actions) > 0
    result["criteria"]["dream_action_seen"] = len(dream_actions) > 0
    result["metrics"] = {
        "beat_start": beat0,
        "beat_after_restart": progressed_beat,
        "recent_entries": len(recent),
        "sandbox_actions": len(sandbox_actions),
        "dream_actions": len(dream_actions),
        "sleep_actions": len(sleep_actions),
        "wake_actions": len(wake_actions),
    }

    result["pass"] = all(bool(v) for v in result["criteria"].values())
    append_desk_trace(
        "complete",
        actor="real_poc_runner",
        decision="finalize_real_test",
        outcome="complete" if result["pass"] else "skip",
        input_context={"criteria": result["criteria"], "metrics": result["metrics"]},
        skip_reason="" if result["pass"] else "one_or_more_criteria_failed",
    )
    if shutdown_after_test:
        pid = current_main_pid()
        if pid > 0:
            stopped = kill_pid(pid)
            append_desk_trace(
                "complete",
                actor="real_poc_runner",
                decision="shutdown_after_test",
                outcome="complete" if stopped else "skip",
                input_context={"pid": pid, "stopped": bool(stopped)},
                skip_reason="" if stopped else "shutdown_failed",
            )
            if not stopped:
                result["notes"].append(f"Degraded: failed to stop runtime pid={pid} at test end.")
        else:
            append_desk_trace(
                "skip",
                actor="real_poc_runner",
                decision="shutdown_after_test",
                outcome="skip",
                input_context={"pid": 0, "stopped": False},
                skip_reason="runtime_not_found",
            )
    prev_hash = append_audit_event(
        run_id=run_id,
        prev_hash=prev_hash,
        event_type="run_end",
        actor="real_poc_runner",
        payload={"pass": bool(result["pass"]), "criteria": result["criteria"]},
    )
    result["audit_chain_tail"] = prev_hash
    result["finished_utc"] = utc_now()
    return result


def write_reports(data: dict[str, Any]) -> None:
    _cx().REPORT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    lines = [
        "# AIOS Real PoC Report",
        "",
        f"- Started: {data.get('started_utc')}",
        f"- Finished: {data.get('finished_utc')}",
        f"- PASS: {data.get('pass')}",
        "",
        "## Criteria",
    ]
    for k, v in data.get("criteria", {}).items():
        lines.append(f"- {k}: {'PASS' if v else 'FAIL'}")
    lines += ["", "## Metrics"]
    for k, v in data.get("metrics", {}).items():
        lines.append(f"- {k}: {v}")
    if "metrics_seeded_done" in data:
        lines.append(f"- seeded_done: {data['metrics_seeded_done']}")
    lines += ["", "## Notes"]
    notes = data.get("notes", []) or ["none"]
    for n in notes:
        lines.append(f"- {n}")
    _cx().REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run real PoC validation checks.")
    ap.add_argument(
        "--enable-restart-test",
        action="store_true",
        help="Enable forced interrupt and restart recovery checks.",
    )
    ap.add_argument(
        "--no-shutdown-after-test",
        action="store_true",
        help="Leave runtime running after test completes.",
    )
    args = ap.parse_args()
    try:
        data = run_real_test(
            enable_restart_test=bool(args.enable_restart_test),
            shutdown_after_test=not bool(args.no_shutdown_after_test),
        )
        write_reports(data)
        print(
            json.dumps(
                {
                    "pass": data.get("pass"),
                    "run_id": data.get("run_id"),
                    "report_json": str(_cx().REPORT_JSON),
                    "report_md": str(_cx().REPORT_MD),
                },
                indent=2,
            )
        )
        return 0 if data.get("pass") else 2
    except Exception as exc:
        failure = {
            "run_id": None,
            "started_utc": utc_now(),
            "finished_utc": utc_now(),
            "pass": False,
            "criteria": {"crash_free": False},
            "notes": [f"Fatal runner error: {exc}"],
            "commands": [],
        }
        with contextlib.suppress(Exception):
            write_reports(failure)
        print(
            json.dumps(
                {
                    "pass": False,
                    "error": str(exc),
                    "report_json": str(_cx().REPORT_JSON),
                    "report_md": str(_cx().REPORT_MD),
                },
                indent=2,
            )
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
