"""Launch Luna/Aria workspace runtimes using ``FsaaPaths`` (no drive literals)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Literal

from fsaa.config.paths import get_paths
from fsaa.contracts.errors import ConfigurationError

Side = Literal["left", "right"]


def launch_workspace_side(side: Side) -> int:
    """Set ``FSAA_SIDE`` and run the workspace Luna (left) or Aria (right) entry script."""
    try:
        paths = get_paths()
    except ConfigurationError:
        return 78
    if side == "left":
        os.environ["FSAA_SIDE"] = "left"
        target = paths.luna_runtime_main
        label = "Luna"
    else:
        os.environ["FSAA_SIDE"] = "right"
        target = paths.aria_runtime_main
        label = "Aria"
    if not target.is_file():
        print(f"{label} entry missing: {target}", file=sys.stderr)
        return 78
    py = paths.python_executable
    if not py.is_file():
        py = Path(sys.executable)
    cp = subprocess.run(
        [str(py), str(target)],
        cwd=str(paths.workspace_root),
        env=os.environ.copy(),
        check=False,
    )
    return int(cp.returncode)


def main_left() -> int:
    return launch_workspace_side("left")


def main_right() -> int:
    return launch_workspace_side("right")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Launch Luna (left) or Aria (right) using WORKSPACE_ROOT paths."
    )
    ap.add_argument("side", choices=("left", "right"), nargs="?", default=None)
    args = ap.parse_args(argv)
    if args.side is None:
        ap.print_help()
        return 2
    return launch_workspace_side(args.side)  # type: ignore[arg-type]


if __name__ == "__main__":
    raise SystemExit(main())
