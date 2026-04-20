from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_validate_policy_exits_zero() -> None:
    root = Path(__file__).resolve().parents[1]
    # WORKSPACE_ROOT from conftest not passed to subprocess — set explicitly
    ws = root.parent
    cp2 = subprocess.run(
        [sys.executable, "-m", "fsaa.cli.main", "validate-policy"],
        cwd=str(root),
        env={**__import__("os").environ, "PYTHONPATH": str(root / "src"), "WORKSPACE_ROOT": str(ws)},
        capture_output=True,
        text=True,
    )
    assert cp2.returncode == 0, cp2.stderr
