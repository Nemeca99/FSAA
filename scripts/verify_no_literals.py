#!/usr/bin/env python3
"""Scan src/fsaa for drive-letter path literals (allowlist in docs/gap_analysis.md)."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    src = root / "src" / "fsaa"
    if not src.is_dir():
        print("skip: no src/fsaa", file=sys.stderr)
        return 0
    bad: list[str] = []
    pat = re.compile(r"[L-Z]:[/\\\\]", re.IGNORECASE)
    for path in src.rglob("*.py"):
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if pat.search(line) and "gap_analysis" not in line:
                bad.append(f"{path.relative_to(root)}:{i}:{line.strip()!r}")
    if bad:
        print("Forbidden drive-letter literals in src/fsaa:", file=sys.stderr)
        for b in bad:
            print(b, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
