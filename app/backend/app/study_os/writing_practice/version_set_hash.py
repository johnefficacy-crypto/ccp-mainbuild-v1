"""Shared ``version_set_hash`` helper (architecture §4.5a).

This is the single backend owner of the version-set hash. Clients consume the
digest but never compute it. The hash detects stale ``writing_session_checks``
results: any change to the set of latest unit versions changes the digest.

The payload is domain-separated and length-prefixed so it cannot collide with
other SHA-256 uses in the codebase, and so that no two distinct unit sets can
produce the same byte stream.
"""
from __future__ import annotations

import hashlib
import struct
import uuid
from dataclasses import dataclass

_DOMAIN = b"WPS_VERSION_SET_V1\x00"


@dataclass(frozen=True)
class UnitRow:
    """One unit's contribution to the version-set hash.

    unit_number:  1-indexed position of the unit within the session.
    id:           the ``writing_session_units`` UUID.
    version_id:   the latest ``writing_unit_versions`` UUID for the unit.
    content_hash: lowercase 64-char SHA-256 hex of that version's answer text.
    """

    unit_number: int
    id: str
    version_id: str
    content_hash: str


def compute_version_set_hash(units: list[UnitRow]) -> str:
    """Return the lowercase 64-char SHA-256 hex digest for ``units``.

    Units are sorted by ``unit_number`` ascending before hashing, so callers
    need not pre-sort. Each unit contributes, in order:

      * uint32 big-endian ``unit_number``
      * 16-byte RFC 4122 network-order bytes of the unit id
      * 16-byte RFC 4122 network-order bytes of the version id
      * 32 raw bytes of the content hash

    The stream is prefixed with the domain separator and a uint32 big-endian
    unit count.
    """
    payload = bytearray(_DOMAIN)
    payload += struct.pack(">I", len(units))

    for unit in sorted(units, key=lambda r: r.unit_number):
        content_hex = unit.content_hash.strip().lower()
        content_bytes = bytes.fromhex(content_hex)
        if len(content_bytes) != 32:
            raise ValueError(
                f"content_hash must be 32 bytes (64 hex chars), got "
                f"{len(content_bytes)} bytes for unit {unit.unit_number}"
            )
        payload += struct.pack(">I", unit.unit_number)
        payload += uuid.UUID(str(unit.id)).bytes
        payload += uuid.UUID(str(unit.version_id)).bytes
        payload += content_bytes

    return hashlib.sha256(bytes(payload)).hexdigest()
