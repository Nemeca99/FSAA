"""Observability helpers (telemetry JSONL, time formatting).

**Windows caveat:** :class:`~fsaa.observability.append_only.AppendOnlyStream` uses
append mode and a single :func:`os.write` per record, but Windows does not
guarantee the same append atomicity as POSIX ``O_APPEND`` under contention.
Alpha assumes low-contention, single-machine append; Beta may add explicit
file-locking or another multi-writer strategy if needed.
"""

from fsaa.observability.append_only import MAX_JSONL_LINE_BYTES, AppendOnlyStream

__all__ = ["MAX_JSONL_LINE_BYTES", "AppendOnlyStream"]
