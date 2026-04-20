"""Brainstem supervisor — bounded scheduling and runtime subprocess lifecycle via FsaaPaths + adapter.

Uses :class:`~fsaa.runtime.adapters.aios.AIOSRuntimeAdapter` by default; set ``FSAA_RUNTIME_ADAPTER=turn_token``
for the turn-token pilot subclass (socket brain status on ``FSAA_BRAIN_STATUS_PORT``, default 5151).
"""

from __future__ import annotations

import argparse
import contextlib
import gc
import json
import os
import signal
import time
from datetime import UTC, datetime
from pathlib import Path

from fsaa.config.paths import FsaaPaths, get_paths
from fsaa.contracts.errors import ConfigurationError
from fsaa.policy.guard import SCHEMA_VERSION, guarded_commit
from fsaa.runtime.adapters.aios import AIOSRuntimeAdapter, AIOSRuntimeHandle
from fsaa.runtime.protocol import RuntimeStartConfig
from fsaa.runtime.registry import resolve_adapter

NON_MEANINGFUL_ACTIONS = {"idle", "status_poll"}


def meaningful_actions_since_lines(all_lines: list[str], start_line: int) -> tuple[int, list[str]]:
    """Pure helper for autonomy JSONL lines (parity tests + Supervisor)."""
    actions: list[str] = []
    for raw in all_lines[max(0, int(start_line)) :]:
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        action = str(row.get("chosen_action", "")).strip()
        if not action or action in NON_MEANINGFUL_ACTIONS:
            continue
        actions.append(action)
    return len(actions), actions


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _health_touch(name: str) -> None:
    raw = os.environ.get("FSAA_HEALTH_DIR", "").strip()
    if not raw:
        return
    d = Path(raw)
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(_utc_now(), encoding="utf-8")


class Supervisor:
    """Orchestrates bounded/auto runs; sidecar lifecycle goes through ``AIOSRuntimeAdapter`` (or subclass)."""

    def __init__(self, paths: FsaaPaths, adapter: AIOSRuntimeAdapter) -> None:
        self.paths = paths
        self.adapter = adapter
        self._handles: list = []
        self._shutdown_requested = False

    @classmethod
    def from_env(cls) -> Supervisor:
        paths = get_paths()
        ad = resolve_adapter(paths=paths)
        if not isinstance(ad, AIOSRuntimeAdapter):
            raise ConfigurationError(
                "Alpha supervisor requires AIOSRuntimeAdapter or TurnTokenRuntimeAdapter "
                "(FSAA_RUNTIME_ADAPTER=aios or turn_token)"
            )
        return cls(paths, ad)

    def _next_run_id(self) -> int:
        run_state = self.paths.supervisor_run_state
        current = 0
        if run_state.is_file():
            try:
                current = int(
                    json.loads(run_state.read_text(encoding="utf-8")).get("last_run_id", 0) or 0
                )
            except (OSError, json.JSONDecodeError, ValueError, TypeError):
                current = 0
        run_id = current + 1
        run_state.parent.mkdir(parents=True, exist_ok=True)
        run_state.write_text(json.dumps({"last_run_id": run_id}, indent=2), encoding="utf-8")
        return run_id

    def _append_event(self, row: dict) -> None:
        ev = self.paths.supervisor_events
        ev.parent.mkdir(parents=True, exist_ok=True)
        with ev.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _guard_or_raise(self, *, run_id: int, event_type: str, intent: str, payload: dict) -> None:
        envelope = {
            "schema_version": SCHEMA_VERSION,
            "run_id": int(run_id),
            "timestamp": _utc_now(),
            "actor": "steel_brain",
            "event_type": event_type,
            "intent": intent,
            "payload": payload,
            "prev_hash": payload.get("prev_hash", ""),
        }
        verdict = guarded_commit(envelope)
        if not verdict.ok:
            raise RuntimeError(f"authority_guard_reject:{verdict.reason}")

    def _phase_event(
        self, *, run_id: int, side: str, phase: str, status: str, payload: dict | None = None
    ) -> None:
        body = dict(payload or {})
        body.update({"phase": phase, "status": status, "side": side})
        self._guard_or_raise(run_id=run_id, event_type="status", intent="status_poll", payload=body)
        self._append_event(
            {
                "ts": _utc_now(),
                "run_id": run_id,
                "event": "phase",
                "phase": phase,
                "status": status,
                "side": side,
                **(payload or {}),
            }
        )

    def _autonomy_line_count(self) -> int:
        log = self.paths.autonomy_telemetry
        if not log.is_file():
            return 0
        try:
            return len(log.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            return 0

    def _meaningful_actions_since(self, start_line: int) -> tuple[int, list[str]]:
        log = self.paths.autonomy_telemetry
        if not log.is_file():
            return 0, []
        try:
            lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return 0, []
        return meaningful_actions_since_lines(lines, start_line)

    def _build_launch_env(self, *, safe_low_ram: bool) -> dict[str, str]:
        env = dict(os.environ)
        if safe_low_ram:
            env.update(
                {
                    "AIOS_FAST_INFERENCE": "1",
                    "AIOS_FAST_MAX_NEW_TOKENS": env.get("AIOS_FAST_MAX_NEW_TOKENS", "96"),
                    "AIOS_UNIFIED_GGUF": "1",
                    "AIOS_LLM_BASE_ONLY": "1",
                    "AIOS_REFINER_USE_TRANSFORMERS": "1",
                }
            )
        return env

    def _run_single_loop_cycle(
        self,
        *,
        script_path: Path,
        side: str,
        beat_seconds: float,
        loop_count: int,
        min_actions_per_run: int,
        run_id: int,
        env: dict[str, str],
        argv_extra: tuple[str, ...] = (),
    ) -> tuple[int, bool, bool]:
        start_line = self._autonomy_line_count()
        cfg = RuntimeStartConfig(
            script_path=script_path,
            env=env,
            cwd=self.paths.workspace_root,
            side=side,
            argv_extra=argv_extra,
        )
        handle = self.adapter.start(cfg)
        self._handles.append(handle)
        proc = handle.proc if isinstance(handle, AIOSRuntimeHandle) else None
        if proc is None:
            return 1, False, False
        run_for_s = max(1.0, float(loop_count) * max(0.1, float(beat_seconds)))
        deadline = time.time() + run_for_s
        target_actions = max(1, int(min_actions_per_run))
        action_target_met = False
        while time.time() < deadline:
            if self._shutdown_requested:
                break
            if proc.poll() is not None:
                return int(proc.returncode or 0), False, False
            seen_count, seen_actions = self._meaningful_actions_since(start_line)
            if seen_count >= target_actions:
                self._phase_event(
                    run_id=run_id,
                    side=side,
                    phase="bounded_target",
                    status="complete",
                    payload={
                        "target_actions": target_actions,
                        "seen_count": seen_count,
                        "seen_actions": seen_actions[-5:],
                    },
                )
                action_target_met = True
                break
            time.sleep(0.1)
        else:
            action_target_met = False
        self.adapter.shutdown(handle, grace_seconds=10.0)
        self._handles.remove(handle)
        self.adapter.stop_process_pid(proc.pid)
        self.adapter.kill_existing_side_processes(side)
        return 0, True, action_target_met

    def _run_side(
        self,
        script_path: Path,
        run_id: int,
        timeout: int,
        *,
        side: str,
        safe_low_ram: bool,
        auto: bool,
        loop_count: int,
        beat_seconds: float,
        min_actions_per_run: int,
        kill_existing: bool,
        gc_threshold_mb: int,
        auto_max_cycles: int,
        argv_extra: tuple[str, ...] = (),
    ) -> int:
        label = script_path.name
        self._guard_or_raise(
            run_id=run_id,
            event_type="intent",
            intent="runtime_boot",
            payload={
                "label": label,
                "timeout": timeout,
                "safe_low_ram": safe_low_ram,
                "side": side,
                "auto": auto,
                "loop_count": loop_count,
                "beat_seconds": beat_seconds,
                "min_actions_per_run": min_actions_per_run,
                "kill_existing": kill_existing,
                "gc_threshold_mb": gc_threshold_mb,
                "auto_max_cycles": auto_max_cycles,
            },
        )
        self._append_event({"ts": _utc_now(), "run_id": run_id, "event": "intent", "label": label})
        killed = 0
        if kill_existing:
            killed = self.adapter.kill_existing_side_processes(side)
            self._append_event(
                {
                    "ts": _utc_now(),
                    "run_id": run_id,
                    "event": "pre_kill",
                    "side": side,
                    "count": killed,
                }
            )
        env = self._build_launch_env(safe_low_ram=safe_low_ram)
        env["FSAA_SIDE"] = side
        self._phase_event(
            run_id=run_id, side=side, phase="runtime", status="start", payload={"label": label}
        )
        timed_out = False
        bounded_auto_shutdown = False
        rc = 0
        killed_post = 0
        action_target_met = False
        if not auto:
            rc, bounded_auto_shutdown, action_target_met = self._run_single_loop_cycle(
                script_path=script_path,
                side=side,
                beat_seconds=beat_seconds,
                loop_count=loop_count,
                min_actions_per_run=min_actions_per_run,
                run_id=run_id,
                env=env,
                argv_extra=argv_extra,
            )
            self._phase_event(
                run_id=run_id,
                side=side,
                phase="shutdown",
                status="start",
                payload={
                    "reason": "bounded_action_target_reached"
                    if action_target_met
                    else "bounded_loop_deadline",
                    "action_target_met": action_target_met,
                },
            )
            self._phase_event(run_id=run_id, side=side, phase="cleanup", status="start")
            gc.collect()
            killed_post = self.adapter.kill_existing_side_processes(side)
            self._phase_event(
                run_id=run_id,
                side=side,
                phase="cleanup",
                status="complete",
                payload={"killed_post": killed_post},
            )
            self._phase_event(run_id=run_id, side=side, phase="shutdown", status="complete")
        else:
            cycle = 0
            deadline = time.time() + max(10, int(timeout))
            while True:
                cycle += 1
                if kill_existing:
                    self.adapter.kill_existing_side_processes(side)
                self._phase_event(
                    run_id=run_id,
                    side=side,
                    phase="restart",
                    status="start",
                    payload={"cycle": cycle},
                )
                cfg = RuntimeStartConfig(
                    script_path=script_path,
                    env=env,
                    cwd=self.paths.workspace_root,
                    side=side,
                    argv_extra=argv_extra,
                )
                handle = self.adapter.start(cfg)
                self._handles.append(handle)
                proc = handle.proc if isinstance(handle, AIOSRuntimeHandle) else None
                if proc is None:
                    rc = 1
                    break
                self._phase_event(
                    run_id=run_id,
                    side=side,
                    phase="runtime",
                    status="start",
                    payload={"cycle": cycle, "pid": int(proc.pid)},
                )
                tripped = False
                while time.time() < deadline:
                    if self._shutdown_requested:
                        break
                    if proc.poll() is not None:
                        rc = int(proc.returncode or 0)
                        self._phase_event(
                            run_id=run_id,
                            side=side,
                            phase="runtime",
                            status="complete",
                            payload={"cycle": cycle, "rc": rc},
                        )
                        break
                    mem_mb = self.adapter.side_memory_mb(side)
                    if mem_mb >= max(256, int(gc_threshold_mb)):
                        tripped = True
                        self._append_event(
                            {
                                "ts": _utc_now(),
                                "run_id": run_id,
                                "event": "auto_gc_threshold",
                                "side": side,
                                "cycle": cycle,
                                "mem_mb": mem_mb,
                                "threshold_mb": gc_threshold_mb,
                            }
                        )
                        self._phase_event(
                            run_id=run_id,
                            side=side,
                            phase="dream_consolidation",
                            status="start",
                            payload={
                                "cycle": cycle,
                                "mem_mb": mem_mb,
                                "threshold_mb": gc_threshold_mb,
                            },
                        )
                        self.adapter.request_dream_consolidation()
                        self._phase_event(
                            run_id=run_id,
                            side=side,
                            phase="dream_consolidation",
                            status="complete",
                            payload={"cycle": cycle},
                        )
                        time.sleep(max(0.1, beat_seconds) * 2.0)
                        break
                    time.sleep(max(0.1, beat_seconds))
                self._phase_event(
                    run_id=run_id,
                    side=side,
                    phase="shutdown",
                    status="start",
                    payload={"cycle": cycle, "reason": "auto_cycle_boundary"},
                )
                self.adapter.shutdown(handle, grace_seconds=10.0)
                if handle in self._handles:
                    self._handles.remove(handle)
                self.adapter.kill_existing_side_processes(side)
                self._phase_event(
                    run_id=run_id,
                    side=side,
                    phase="cleanup",
                    status="start",
                    payload={"cycle": cycle},
                )
                gc.collect()
                self._phase_event(
                    run_id=run_id,
                    side=side,
                    phase="cleanup",
                    status="complete",
                    payload={"cycle": cycle},
                )
                self._phase_event(
                    run_id=run_id,
                    side=side,
                    phase="shutdown",
                    status="complete",
                    payload={"cycle": cycle},
                )
                if tripped:
                    bounded_auto_shutdown = True
                    self._phase_event(
                        run_id=run_id,
                        side=side,
                        phase="restart",
                        status="complete",
                        payload={"cycle": cycle},
                    )
                    if auto_max_cycles > 0 and cycle >= auto_max_cycles:
                        rc = 0
                        break
                    continue
                if time.time() >= deadline:
                    timed_out = True
                    rc = 0
                self._phase_event(
                    run_id=run_id,
                    side=side,
                    phase="restart",
                    status="complete",
                    payload={"cycle": cycle},
                )
                break
            killed_post = self.adapter.kill_existing_side_processes(side)
        self._guard_or_raise(
            run_id=run_id,
            event_type="outcome",
            intent="runtime_boot",
            payload={
                "label": label,
                "rc": rc,
                "safe_low_ram": safe_low_ram,
                "steady_state": timed_out,
                "bounded_auto_shutdown": bounded_auto_shutdown,
                "action_target_met": action_target_met,
                "killed_existing": killed,
                "killed_post": killed_post,
            },
        )
        self._append_event(
            {
                "ts": _utc_now(),
                "run_id": run_id,
                "event": "outcome",
                "label": label,
                "rc": rc,
                "steady_state": timed_out,
                "bounded_auto_shutdown": bounded_auto_shutdown,
                "action_target_met": action_target_met,
                "killed_existing": killed,
                "killed_post": killed_post,
            }
        )
        return rc

    def _on_sigterm(self, _signum: int, _frame: object) -> None:
        self._shutdown_requested = True
        for h in list(self._handles):
            with contextlib.suppress(OSError):
                self.adapter.shutdown(h, grace_seconds=5.0)

    def run_cli(self, args: argparse.Namespace) -> int:
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, self._on_sigterm)
        _health_touch("live")
        _health_touch("ready")
        auto = False
        if args.no_auto:
            auto = False
        elif args.auto:
            auto = True
        kill_existing = True
        if args.no_kill_existing:
            kill_existing = False
        elif args.kill_existing:
            kill_existing = True

        run_id = self._next_run_id()
        self._append_event(
            {
                "ts": _utc_now(),
                "run_id": run_id,
                "event": "run_start",
                "mode": args.mode,
                "side": args.side,
                "safe_low_ram": bool(args.safe_low_ram),
                "auto": auto,
                "loop_count": max(1, int(args.loop)),
                "beat_seconds": max(0.1, float(args.beat_seconds)),
                "min_actions_per_run": max(1, int(args.min_actions_per_run)),
                "kill_existing": kill_existing,
                "gc_threshold_mb": max(256, int(args.gc_threshold_mb)),
                "auto_max_cycles": max(0, int(args.auto_max_cycles)),
                "turn_token_max_seconds": args.turn_token_max_seconds,
                "turn_token_cpu_beats": args.turn_token_cpu_beats,
                "turn_token_gpu_beats": args.turn_token_gpu_beats,
            }
        )
        if args.mode == "turn_token":
            target = self.paths.turn_token_module_py
            argv_extra = (
                "--max-seconds",
                str(max(1, int(args.turn_token_max_seconds))),
                "--cpu-turn-beats",
                str(max(1, int(args.turn_token_cpu_beats))),
                "--gpu-turn-beats",
                str(max(1, int(args.turn_token_gpu_beats))),
            )
        else:
            target = self.paths.luna_runtime_main if args.side == "left" else self.paths.aria_runtime_main
            argv_extra = ()
        rc = self._run_side(
            target,
            run_id=run_id,
            timeout=max(10, int(args.timeout)),
            side=args.side,
            safe_low_ram=bool(args.safe_low_ram),
            auto=auto,
            loop_count=max(1, int(args.loop)),
            beat_seconds=max(0.1, float(args.beat_seconds)),
            min_actions_per_run=max(1, int(args.min_actions_per_run)),
            kill_existing=kill_existing,
            gc_threshold_mb=max(256, int(args.gc_threshold_mb)),
            auto_max_cycles=max(0, int(args.auto_max_cycles)),
            argv_extra=argv_extra,
        )
        self._append_event(
            {
                "ts": _utc_now(),
                "run_id": run_id,
                "event": "run_end",
                "side": args.side,
                "rc": rc,
                "safe_low_ram": bool(args.safe_low_ram),
                "auto": auto,
                "kill_existing": kill_existing,
            }
        )
        return rc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="FSAA brainstem supervisor for left/right entrypoints."
    )
    ap.add_argument(
        "--mode",
        choices=["sidecar", "turn_token"],
        default="sidecar",
        help="sidecar: Luna/Aria wrappers (default). turn_token: supervise automation/turn_token_loop.py.",
    )
    ap.add_argument(
        "--side", choices=["left", "right"], default="left", help="Run left (Luna) or right (Aria)."
    )
    ap.add_argument("--timeout", type=int, default=120, help="Subprocess timeout in seconds.")
    ap.add_argument(
        "--safe-low-ram",
        action="store_true",
        help="Enable low-RAM model routing and fast inference profile.",
    )
    ap.add_argument(
        "--auto",
        action="store_true",
        help="Continuous auto mode: run-until-threshold, dream+cleanup, then restart.",
    )
    ap.add_argument(
        "--no-auto",
        action="store_true",
        help="Disable auto mode (default): run bounded loops then full shutdown.",
    )
    ap.add_argument(
        "--loop", type=int, default=60, help="Bounded loops for non-auto mode before full shutdown."
    )
    ap.add_argument("--beat-seconds", type=float, default=1.0, help="Seconds per loop beat.")
    ap.add_argument(
        "--min-actions-per-run",
        type=int,
        default=1,
        help="Meaningful actions before shutdown in non-auto mode.",
    )
    ap.add_argument(
        "--kill-existing",
        action="store_true",
        help="Kill existing side processes before launch (default).",
    )
    ap.add_argument(
        "--no-kill-existing",
        action="store_true",
        help="Do not kill existing side processes before launch.",
    )
    ap.add_argument(
        "--gc-threshold-mb", type=int, default=8192, help="Memory threshold for --auto mode."
    )
    ap.add_argument(
        "--auto-max-cycles", type=int, default=0, help="Limit auto restart cycles (0 = unlimited)."
    )
    ap.add_argument(
        "--turn-token-max-seconds",
        type=int,
        default=120,
        help="With --mode turn_token: pass --max-seconds to turn_token_loop.py.",
    )
    ap.add_argument(
        "--turn-token-cpu-beats",
        type=int,
        default=4,
        help="With --mode turn_token: pass --cpu-turn-beats to turn_token_loop.py.",
    )
    ap.add_argument(
        "--turn-token-gpu-beats",
        type=int,
        default=2,
        help="With --mode turn_token: pass --gpu-turn-beats to turn_token_loop.py.",
    )
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        sup = Supervisor.from_env()
        return sup.run_cli(args)
    except ConfigurationError as e:
        import logging

        logging.basicConfig(level=logging.INFO)
        logging.getLogger(__name__).error("configuration invalid: %s", e)
        return 78
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
