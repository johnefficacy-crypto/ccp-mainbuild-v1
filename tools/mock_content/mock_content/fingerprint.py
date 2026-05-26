from __future__ import annotations

import hashlib
from typing import Iterable

from .normalize import normalize_stem_for_fp, normalize_text

OPTION_COLS = ["option_a", "option_b", "option_c", "option_d", "option_e", "option_f"]


def _correct_index(correct_option: str) -> str:
    parts = [p.strip().upper() for p in str(correct_option or "").split(";") if p.strip()]
    letters = "ABCDEF"
    idxs = [str(letters.index(p) + 1) for p in sorted(parts) if p in letters]
    return ";".join(idxs)


def compute_fingerprint(row: dict) -> str:
    stem = normalize_stem_for_fp(row.get("question_text", ""))
    options: Iterable[str] = (
        normalize_text(row.get(col, ""), collapse_whitespace=True).lower()
        for col in OPTION_COLS
    )
    sorted_opts = sorted([o for o in options if o])
    joined = "|".join(sorted_opts)
    cidx = _correct_index(row.get("correct_option", ""))
    payload = f"{stem}|{joined}|{cidx}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
