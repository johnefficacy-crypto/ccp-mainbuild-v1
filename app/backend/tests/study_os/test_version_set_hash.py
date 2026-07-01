"""Pinned cross-side vector for ``version_set_hash`` (architecture §4.5a).

The digest is the identity anchor for stale-check detection. Clients consume
it but never compute it, so the guarantee we protect here is that the backend
helper is byte-stable: the pinned hex below must never change for the same
input. If a refactor changes the digest, the change is a breaking wire-format
change and must be treated as a new domain (new separator), not a silent edit.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_MODULE_PATH = (
    Path(__file__).parents[2]
    / "app/study_os/writing_practice/version_set_hash.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "writing_practice_version_set_hash", _MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


vsh = _load()
UnitRow = vsh.UnitRow
compute_version_set_hash = vsh.compute_version_set_hash

# Fixed input → pinned digest. Any deviation is a wire-format break.
_TWO_UNITS = [
    UnitRow(2, "22222222-2222-4222-8222-222222222222",
            "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", "b" * 64),
    UnitRow(1, "11111111-1111-4111-8111-111111111111",
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "a" * 64),
]
_EXPECTED_TWO = "5f2a87f0beebc522e30197da180066b5c4cf449e41bafebb7967f636cb3e5a10"
_EXPECTED_EMPTY = "12bab607092ef5a8e433521349b6c0ecfc8c4003e7f15eb52df20485fc87a060"


def test_pinned_two_unit_vector():
    assert compute_version_set_hash(_TWO_UNITS) == _EXPECTED_TWO


def test_pinned_empty_vector():
    assert compute_version_set_hash([]) == _EXPECTED_EMPTY


def test_sort_order_is_canonical():
    """Input order must not matter; units are sorted by unit_number."""
    reversed_input = list(reversed(_TWO_UNITS))
    assert compute_version_set_hash(reversed_input) == _EXPECTED_TWO


def test_version_change_changes_digest():
    changed = [
        _TWO_UNITS[0],
        UnitRow(1, "11111111-1111-4111-8111-111111111111",
                "cccccccc-cccc-4ccc-8ccc-cccccccccccc", "a" * 64),
    ]
    assert compute_version_set_hash(changed) != _EXPECTED_TWO


def test_content_hash_change_changes_digest():
    changed = [
        _TWO_UNITS[0],
        UnitRow(1, "11111111-1111-4111-8111-111111111111",
                "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "f" * 64),
    ]
    assert compute_version_set_hash(changed) != _EXPECTED_TWO


def test_digest_is_lowercase_hex_64():
    digest = compute_version_set_hash(_TWO_UNITS)
    assert len(digest) == 64
    assert digest == digest.lower()
    int(digest, 16)  # parses as hex


def test_bad_content_hash_length_rejected():
    with pytest.raises(ValueError):
        compute_version_set_hash([
            UnitRow(1, "11111111-1111-4111-8111-111111111111",
                    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "ab"),
        ])
