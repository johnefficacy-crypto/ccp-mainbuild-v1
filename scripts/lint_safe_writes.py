#!/usr/bin/env python3
"""Lint: detect _safe() wrapping write operations without explicit suppression.

_safe() swallows exceptions silently. Using it for INSERT/UPSERT (create-new-data
operations) hides failures that should trigger a retry job. This script fails CI
if new undecorated occurrences are introduced.

Suppression: add  # safe-write-ok: <reason>  on the same line to mark an
occurrence as intentionally fire-and-forget.

Usage:
    python scripts/lint_safe_writes.py [path ...]
    Defaults to app/backend/
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

# Matches _safe( ... ) calls on a single logical line that also contain a
# write method (.insert( or .upsert().
_SAFE_WRITE_RE = re.compile(r"_safe\s*\(.*\.(insert|upsert)\s*\(")
_SUPPRESS_RE = re.compile(r"safe-write-ok", re.IGNORECASE)

VIOLATION_HEADER = "lint_safe_writes: _safe() wrapping write op without suppression"


def scan_file(path: Path) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return violations
    for lineno, line in enumerate(lines, start=1):
        if _SAFE_WRITE_RE.search(line) and not _SUPPRESS_RE.search(line):
            violations.append((lineno, line.rstrip()))
    return violations


def main(argv: list[str]) -> int:
    roots = [Path(p) for p in argv] if argv else [Path("app/backend")]
    all_violations: list[tuple[Path, int, str]] = []
    for root in roots:
        paths = root.rglob("*.py") if root.is_dir() else [root]
        for path in sorted(paths):
            for lineno, line in scan_file(path):
                all_violations.append((path, lineno, line))

    if not all_violations:
        print("lint_safe_writes: OK — no undecorated _safe write operations found")
        return 0

    print(VIOLATION_HEADER)
    print()
    for path, lineno, line in all_violations:
        print(f"  {path}:{lineno}: {line.strip()}")
    print()
    print(
        f"{len(all_violations)} violation(s). "
        "Either replace _safe() with explicit try/except + retry job, "
        "or add  # safe-write-ok: <reason>  to suppress."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
