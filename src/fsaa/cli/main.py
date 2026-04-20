"""`fsaa` console entrypoint."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _cmd_verify() -> int:
    root = Path(__file__).resolve().parents[3]
    scripts = root / "scripts"
    steps = [
        [sys.executable, str(scripts / "verify_no_external_roots.py")],
        [sys.executable, str(scripts / "verify_no_literals.py")],
        [sys.executable, str(scripts / "verify_terminology.py")],
        # -W: suppress coverage's "module-not-measured" for fsaa (pytest-cov import order). Dotted
        # class names are invalid in -W; match the message text against base Warning instead.
        [
            sys.executable,
            "-W",
            "ignore:Module fsaa was previously imported:Warning",
            "-m",
            "pytest",
            "tests",
            "-q",
        ],
    ]
    for cmd in steps:
        cp = subprocess.run(cmd, cwd=str(root), check=False)
        if cp.returncode != 0:
            return int(cp.returncode)
    return 0


def _cmd_validate_policy() -> int:
    import jsonschema

    from fsaa.config.paths import get_paths, read_ipc_schema_text, read_reflex_policy_text
    from fsaa.contracts.errors import ConfigurationError

    try:
        paths = get_paths()
    except ConfigurationError:
        return 78
    try:
        raw = read_ipc_schema_text(paths)
    except OSError:
        return 78
    try:
        ipc = json.loads(raw)
    except json.JSONDecodeError:
        return 78
    try:
        jsonschema.Draft202012Validator.check_schema(ipc)
    except jsonschema.exceptions.SchemaError:
        return 65
    try:
        rraw = read_reflex_policy_text(paths)
    except OSError:
        return 78
    try:
        reflex = json.loads(rraw)
    except json.JSONDecodeError:
        return 78
    if not isinstance(reflex, dict):
        return 65
    for key in ("version", "bounded_mode", "auto_mode"):
        if key not in reflex:
            return 65
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="fsaa")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser(
        "verify", help="Run verify scripts, terminology check, and pytest with coverage."
    )
    sub.add_parser("validate-policy", help="Validate ipc_schema.json and reflex_policy.json.")
    args = ap.parse_args(argv)
    if args.cmd == "verify":
        return _cmd_verify()
    if args.cmd == "validate-policy":
        return _cmd_validate_policy()
    return 78


if __name__ == "__main__":
    raise SystemExit(main())
