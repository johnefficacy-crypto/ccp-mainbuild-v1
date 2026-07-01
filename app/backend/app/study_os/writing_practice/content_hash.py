"""Content-hash helpers for writing unit versions (architecture §4.5).

`content_hash` is `SHA-256(answer_text)` lowercase hex. The empty-string hash
is a fixed constant used for server-created blank exam versions.
"""
from __future__ import annotations

import hashlib

# SHA-256 of the empty string — the canonical blank-version content hash (§4.5).
EMPTY_CONTENT_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def compute_content_hash(answer_text: str) -> str:
    """Return the lowercase SHA-256 hex digest of ``answer_text`` (UTF-8)."""
    return hashlib.sha256(answer_text.encode("utf-8")).hexdigest()
