from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from fsaa.config.paths import get_paths
from fsaa.runtime.adapters.aios import AIOSRuntimeAdapter, AIOSRuntimeHandle
from fsaa.runtime.protocol import RuntimeStartConfig


def test_aios_start_shutdown() -> None:
    paths = get_paths()
    ad = AIOSRuntimeAdapter(paths)
    cfg = RuntimeStartConfig(
        script_path=Path(__file__),
        env={**__import__("os").environ},
        cwd=paths.workspace_root,
        side="left",
    )
    with patch("fsaa.runtime.adapters.aios.subprocess.Popen") as P:
        proc = MagicMock()
        proc.pid = 999
        proc.poll.return_value = None
        proc.wait.return_value = 0
        proc.returncode = 0
        P.return_value = proc
        h = ad.start(cfg)
        assert isinstance(h, AIOSRuntimeHandle)
        ad.shutdown(h, grace_seconds=0.1)
        proc.terminate.assert_called_once()


def test_aios_kill_non_windows() -> None:
    paths = get_paths()
    ad = AIOSRuntimeAdapter(paths)
    with patch.object(sys, "platform", "linux"):
        assert ad.kill_existing_side_processes("left") == 0
        assert ad.side_memory_mb("left") == 0
