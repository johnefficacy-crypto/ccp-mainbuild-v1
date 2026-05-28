"""Ordinal detection and stripping for question text.

Ported from tools/extraction-labeler/src/lib/ordinal.ts (Guard 1).
The regex pattern is the single source of truth shared by both the
labeler (TypeScript) and the extractor (Python).
"""
from __future__ import annotations

import re

# Matches a leading printed question number followed by a separator.
# Separators: period, closing paren, colon, or any whitespace.
# Examples that match: "21. ", "3 ", "1) ", "42: "
# Examples that do NOT match: "I. ", "Statement I:", "21" (no separator)
PATTERN = r'^\s*(\d+)[.):\s]'

_RE = re.compile(PATTERN)
_STRIP_RE = re.compile(r'^\s*\d+[.):\s]\s*')


def detect_ordinal(text: str) -> int | None:
    """Return the printed leading ordinal if text starts with one, else None."""
    m = _RE.match(text)
    if not m:
        return None
    return int(m.group(1))


def strip_ordinal(text: str) -> str:
    """Return text with the leading ordinal and its separator removed."""
    return _STRIP_RE.sub('', text, count=1)
