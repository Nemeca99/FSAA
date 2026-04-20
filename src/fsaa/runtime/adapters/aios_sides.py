"""Launch Luna (left) and Aria (right) AIOS entrypoints under ``WORKSPACE_ROOT``."""

from __future__ import annotations

import argparse
import os
import subprocess

from fsaa.config.paths import FsaaPaths


def run_luna_main(paths: FsaaPaths) -> int:
    os.environ["FSAA_SIDE"] = "left"
    cp = subprocess.run(
        [str(paths.python_executable), str(paths.luna_runtime_main)],
        cwd=str(paths.workspace_root),
        check=False,
    )
    return int(cp.returncode)


def run_aria_main(paths: FsaaPaths) -> int:
    os.environ["FSAA_SIDE"] = "right"
    cp = subprocess.run(
        [str(paths.python_executable), str(paths.aria_runtime_main)],
        cwd=str(paths.workspace_root),
        check=False,
    )
    return int(cp.returncode)


def main(argv: list[str] | None = None) -> int:
    """CLI: ``python -m fsaa.runtime.adapters.aios_sides left|right``."""
    from fsaa.config.paths import get_paths

    ap = argparse.ArgumentParser(description="Run Luna or Aria AIOS main under WORKSPACE_ROOT.")
    ap.add_argument("side", choices=["left", "right"])
    args = ap.parse_args(argv)
    paths = get_paths()
    if args.side == "left":
        return run_luna_main(paths)
    return run_aria_main(paths)


if __name__ == "__main__":
    raise SystemExit(main())
