from __future__ import annotations

import json
from pathlib import Path

import pytest

from fsaa.contracts.errors import TelemetryRecordTooLarge
from fsaa.observability.append_only import (
    MAX_JSONL_LINE_BYTES,
    AppendOnlyStream,
    build_telemetry_record,
)


def test_append_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "t.jsonl"
    stream = AppendOnlyStream(p)
    rec = build_telemetry_record(fsaa_payload={"k": 1}, otel_payload={})
    stream.append_record(rec)
    line = p.read_text(encoding="utf-8").strip()
    obj = json.loads(line)
    assert obj["telemetry_schema_version"] == "1"
    assert "ts" in obj


def test_too_large(tmp_path: Path) -> None:
    p = tmp_path / "t.jsonl"
    stream = AppendOnlyStream(p)
    big = {"x": "y" * MAX_JSONL_LINE_BYTES}
    rec = build_telemetry_record(fsaa_payload=big, otel_payload={})
    with pytest.raises(TelemetryRecordTooLarge):
        stream.append_record(rec)
