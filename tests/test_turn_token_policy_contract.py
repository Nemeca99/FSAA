"""``ab_test_turn_token`` guard contract: RuntimeError prefix + intent mapping."""

from __future__ import annotations

from pathlib import Path

import pytest

from fsaa.config.paths import clear_paths_cache
from fsaa.policy.guard import ValidationResult
from fsaa.policy.turn_token import guard_or_raise, intent_from_label


def test_intent_from_label_maps_like_ab_test() -> None:
    assert intent_from_label("ensure_runtime_baseline") == "runtime_boot"
    assert intent_from_label("turn_loop_pilot") == "turn_token_step"
    assert intent_from_label("other") == "status_poll"


def test_guard_or_raise_reject_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    import fsaa.policy.turn_token as tt

    monkeypatch.setattr(
        tt,
        "guarded_commit",
        lambda _e: ValidationResult(False, "schema_invalid:missing_fields:x"),
    )
    with pytest.raises(RuntimeError, match=r"^authority_guard_reject:schema_invalid:missing_fields:x$"):
        guard_or_raise(
            run_id=1,
            prev_hash="",
            event_type="intent",
            label="noop",
            payload={},
        )


def test_guard_or_raise_accepts_with_isolated_logs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    log = tmp_path / "authority_guard_log.jsonl"
    met = tmp_path / "translation_metrics.jsonl"
    monkeypatch.setenv("FSAA_AUTHORITY_LOG", str(log))
    monkeypatch.setenv("FSAA_TRANSLATION_METRICS", str(met))
    clear_paths_cache()
    guard_or_raise(
        run_id=99,
        prev_hash="",
        event_type="intent",
        label="ensure_runtime_smoke",
        payload={"args": ["a"], "timeout": 1},
    )
    assert log.is_file()
    clear_paths_cache()
