"""Wall-clock and monotonic timestamps for telemetry."""

from __future__ import annotations

import time
from datetime import UTC, datetime


def utc_wall_iso_z_ms() -> str:
    """ISO 8601 UTC with millisecond precision and Z suffix (not +00:00)."""
    now = datetime.now(UTC)
    ms = now.microsecond // 1000
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{ms:03d}Z"


def monotonic_ns_now() -> int:
    return time.monotonic_ns()
