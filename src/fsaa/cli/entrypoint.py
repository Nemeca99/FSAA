"""Default supervisor launcher (historical ``main_fsaa`` behavior, package-local)."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "fsaa.control_plane.supervisor",
            "--side",
            "left",
            "--safe-low-ram",
            "--loop",
            "60",
            "--beat-seconds",
            "1.0",
            "--min-actions-per-run",
            "1",
        ],
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
