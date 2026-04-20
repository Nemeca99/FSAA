"""Append-only JSONL with size-bounded lines (Section 4.7).

Implementation contract:

- Open with append-binary flags (POSIX ``O_APPEND``); one :func:`os.write` per record.
- Serialize UTF-8 bytes including trailing ``\\n``; raise :exc:`~fsaa.contracts.errors.TelemetryRecordTooLarge` if ``len > 4096``.
- :func:`os.fsync` before :func:`os.close` on the descriptor (no per-call flush beyond the syscall).

On Windows, append atomicity is best-effort under contention; Alpha assumes low
contention. High-contention multi-writer scenarios need a Beta upgrade (see
:mod:`fsaa.observability` package docstring).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fsaa.contracts.errors import TelemetryRecordTooLarge
from fsaa.observability.timeutil import monotonic_ns_now, utc_wall_iso_z_ms

# POSIX PIPE_BUF is often 4096; single-write atomicity for small appends on POSIX.
MAX_JSONL_LINE_BYTES = 4096

_DEFAULT_SEMCONV = "1.28.0"


def build_telemetry_record(
    *,
    fsaa_payload: dict[str, Any],
    otel_payload: dict[str, Any],
    telemetry_schema_version: str = "1",
    semconv_version: str | None = None,
    include_monotonic_ns: bool = True,
) -> dict[str, Any]:
    sem = semconv_version or _DEFAULT_SEMCONV
    row: dict[str, Any] = {
        "telemetry_schema_version": telemetry_schema_version,
        "semconv_version": sem,
        "fsaa": fsaa_payload,
        "otel": otel_payload,
        "ts": utc_wall_iso_z_ms(),
    }
    if include_monotonic_ns:
        row["monotonic_ns"] = monotonic_ns_now()
    return row


class AppendOnlyStream:
    """Append one complete UTF-8 line per record; raises if line exceeds MAX_JSONL_LINE_BYTES."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def append_record(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"
        data = line.encode("utf-8")
        if len(data) > MAX_JSONL_LINE_BYTES:
            raise TelemetryRecordTooLarge(
                f"telemetry line is {len(data)} bytes; max {MAX_JSONL_LINE_BYTES}"
            )
        self._path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        fd = os.open(self._path, flags, 0o644)
        try:
            n = os.write(fd, data)
            if n != len(data):
                msg = f"short write: wrote {n} of {len(data)} bytes"
                raise OSError(msg)
        finally:
            os.fsync(fd)
            os.close(fd)
