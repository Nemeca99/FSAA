#!/usr/bin/env python3
"""Fail if the FSAA_v2 tree contains string references to legacy package paths."""

from __future__ import annotations

import sys
from pathlib import Path


def _forbidden_substrings() -> list[str]:
    """Patterns are composed so this file does not contain grep-visible legacy path literals."""
    bs = chr(92)
    c = "Continue"
    fsaa = "FSAA"
    auto = "automation"
    steel = "Steel" + chr(95) + "Brain"
    return [
        f"{c}{bs}{fsaa}{bs}",
        f"{c}/{fsaa}/",
        f"{c}{bs}{auto}{bs}",
        f"{c}/{auto}/",
        f"L:{bs}{c}{bs}{fsaa}{bs}",
        f"L:/{c}/{fsaa}/",
        f"L:{bs}{c}{bs}{auto}{bs}",
        f"L:/{c}/{auto}/",
        steel,
    ]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    script = Path(__file__).resolve()
    forbidden = _forbidden_substrings()
    bad: list[str] = []
    skip_names = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if path.resolve() == script:
            continue
        if any(part in skip_names for part in rel.parts):
            continue
        if path.suffix in {".png", ".jpg", ".ico", ".woff", ".woff2"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        for sub in forbidden:
            if sub in text:
                bad.append(f"{rel}: contains forbidden substring {sub!r}")
                break
    if bad:
        print("Legacy path references are forbidden under FSAA_v2:", file=sys.stderr)
        for b in bad:
            print(b, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
