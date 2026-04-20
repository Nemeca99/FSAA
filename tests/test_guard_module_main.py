from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_policy_guard_module_main(tmp_path: Path) -> None:
    ws = Path(__file__).resolve().parents[2]
    env = {
        **os.environ,
        "WORKSPACE_ROOT": str(ws),
        "FSAA_AUTHORITY_LOG": str(tmp_path / "a.jsonl"),
        "FSAA_TRANSLATION_METRICS": str(tmp_path / "m.jsonl"),
    }
    root = Path(__file__).resolve().parents[1]
    cp = subprocess.run(
        [sys.executable, "-m", "fsaa.policy.guard"],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
    )
    assert cp.returncode == 0
    assert "true" in cp.stdout.lower() or '"ok": true' in cp.stdout
