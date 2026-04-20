#!/usr/bin/env python3
"""Fail if maintained package paths contain string references to legacy import/path cheats."""

from __future__ import annotations

import sys
from pathlib import Path


def _forbidden_substrings() -> list[str]:
    """Patterns composed so this file avoids embedding grep-visible legacy path literals."""
    bs = chr(92)
    c = "Continue"
    fsaa = "FSAA"
    auto = "automation"
    steel = "Steel" + chr(95) + "Brain"
    v2 = fsaa + "_v2"
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
        v2,
    ]


def _scan_directories(repo_root: Path) -> list[Path]:
    """Only the maintained Python package, scripts, and tests (not merged workspace trees)."""
    out: list[Path] = []
    for rel in ("src/fsaa", "scripts", "tests"):
        p = repo_root / rel
        if p.is_dir():
            out.append(p)
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    script = Path(__file__).resolve()
    forbidden = _forbidden_substrings()
    bad: list[str] = []
    skip_names = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
    scan_dirs = _scan_directories(root)
    for base in scan_dirs:
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(root)
            except ValueError:
                continue
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
        print(
            "Legacy path references are forbidden under src/fsaa, scripts, tests:", file=sys.stderr
        )
        for b in bad:
            print(b, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
