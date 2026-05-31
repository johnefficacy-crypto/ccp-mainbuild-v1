"""Shared text utilities for exam intelligence modules.

Levenshtein ratio and text normalization helpers used across
pyq_bulk_import, syllabus_mapper, and similar proposer modules.
"""
from __future__ import annotations

import re
import unicodedata


def levenshtein_ratio(a: str, b: str) -> float:
    """Return Levenshtein similarity ratio in [0.0, 1.0].

    Uses the python-Levenshtein C extension when available, falls back to
    a pure-Python DP implementation.
    """
    try:
        from Levenshtein import ratio
        return ratio(a, b)
    except ImportError:
        pass
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    la, lb = len(a), len(b)
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = curr
    dist = prev[lb]
    return 1 - dist / max(la, lb)


_UNICODE_FOLDS = str.maketrans(
    {
        "‘": "'", "’": "'", "‚": "'", "‛": "'",
        "“": '"', "”": '"', "„": '"', "‟": '"',
        "–": "-", "—": "-", "−": "-",
        " ": " ", " ": " ", "​": "",
    }
)


def normalize_text(text: str) -> str:
    """Canonical lowercase/whitespace-collapsed form for alias matching.

    - Unicode NFC
    - Smart punctuation → ASCII
    - Collapse whitespace
    - Lowercase
    """
    if not text:
        return ""
    t = unicodedata.normalize("NFC", str(text)).translate(_UNICODE_FOLDS)
    t = re.sub(r"\s+", " ", t).strip()
    return t.lower()
