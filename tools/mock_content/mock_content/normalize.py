from __future__ import annotations

import re

from unidecode import unidecode_expect_nonascii

_WS = re.compile(r"\s+")

SMART_MAP = str.maketrans({
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
})


def normalize_text(value: str, collapse_whitespace: bool = True) -> str:
    if value is None:
        return ""
    s = str(value).replace("\ufeff", "")
    s = s.translate(SMART_MAP)
    s = unidecode_expect_nonascii(s) if any(ord(ch) > 127 for ch in s) else s
    if collapse_whitespace:
        s = _WS.sub(" ", s).strip()
    return s


def normalize_stem_for_fp(value: str) -> str:
    return normalize_text(value, collapse_whitespace=True).lower()
