"""Unit tests for SourceKind enum and source eligibility in dispatch.py."""
from __future__ import annotations

import pytest

from app.exam_intelligence.extraction.dispatch import (
    ELIGIBLE_SOURCE_KINDS_V1,
    SourceKind,
    is_source_eligible_v1,
)


class TestSourceKindEnum:

    def test_all_expected_values_present(self):
        values = {sk.value for sk in SourceKind}
        assert 'official_scan' in values
        assert 'sanitized_coaching' in values
        assert 'raw_coaching' in values
        assert 'crowd_sourced' in values
        assert 'unknown' in values

    def test_source_kind_is_str_enum(self):
        assert isinstance(SourceKind.OFFICIAL_SCAN, str)
        assert SourceKind.OFFICIAL_SCAN == 'official_scan'

    def test_construct_from_string(self):
        assert SourceKind('sanitized_coaching') is SourceKind.SANITIZED_COACHING
        assert SourceKind('raw_coaching') is SourceKind.RAW_COACHING
        assert SourceKind('unknown') is SourceKind.UNKNOWN

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            SourceKind('not_a_real_kind')


class TestEligibleSourceKindsV1:

    def test_eligible_set_contains_official_scan(self):
        assert SourceKind.OFFICIAL_SCAN in ELIGIBLE_SOURCE_KINDS_V1

    def test_eligible_set_contains_sanitized_coaching(self):
        assert SourceKind.SANITIZED_COACHING in ELIGIBLE_SOURCE_KINDS_V1

    def test_raw_coaching_not_eligible(self):
        assert SourceKind.RAW_COACHING not in ELIGIBLE_SOURCE_KINDS_V1

    def test_crowd_sourced_not_eligible(self):
        assert SourceKind.CROWD_SOURCED not in ELIGIBLE_SOURCE_KINDS_V1

    def test_unknown_not_eligible(self):
        assert SourceKind.UNKNOWN not in ELIGIBLE_SOURCE_KINDS_V1

    def test_eligible_set_is_frozenset(self):
        assert isinstance(ELIGIBLE_SOURCE_KINDS_V1, frozenset)

    def test_eligible_set_has_exactly_two_members(self):
        assert len(ELIGIBLE_SOURCE_KINDS_V1) == 2


class TestIsSourceEligibleV1:

    @pytest.mark.parametrize("kind", [
        SourceKind.OFFICIAL_SCAN,
        SourceKind.SANITIZED_COACHING,
    ])
    def test_eligible_kinds_return_true(self, kind):
        assert is_source_eligible_v1(kind) is True

    @pytest.mark.parametrize("kind", [
        SourceKind.RAW_COACHING,
        SourceKind.CROWD_SOURCED,
        SourceKind.UNKNOWN,
    ])
    def test_ineligible_kinds_return_false(self, kind):
        assert is_source_eligible_v1(kind) is False

    def test_every_source_kind_is_covered(self):
        """All SourceKind values must be explicitly eligible or not — no gaps."""
        for kind in SourceKind:
            result = is_source_eligible_v1(kind)
            assert isinstance(result, bool), f"is_source_eligible_v1({kind!r}) must return bool"
