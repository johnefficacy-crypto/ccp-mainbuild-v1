"""Unit tests for ordinal.py — detect_ordinal and strip_ordinal."""
from __future__ import annotations

import pytest

from app.exam_intelligence.extraction.ordinal import detect_ordinal, strip_ordinal


class TestDetectOrdinal:
    def test_period_separator(self):
        assert detect_ordinal("21. Consider the following...") == 21

    def test_space_separator(self):
        assert detect_ordinal("3 Statement I says something.") == 3

    def test_paren_separator(self):
        assert detect_ordinal("1) Some question text") == 1

    def test_colon_separator(self):
        assert detect_ordinal("42: Which of the following") == 42

    def test_non_ordinal_statement_marker(self):
        assert detect_ordinal("Statement I:") is None

    def test_roman_numeral_not_matched(self):
        assert detect_ordinal("I. text following a roman numeral") is None

    def test_leading_whitespace_tolerated(self):
        assert detect_ordinal("  21.  text with leading spaces") == 21

    def test_bare_number_no_separator(self):
        assert detect_ordinal("21") is None

    def test_empty_string(self):
        assert detect_ordinal("") is None

    def test_large_number(self):
        assert detect_ordinal("100. Last question") == 100

    def test_multiline_first_line_has_ordinal(self):
        text = "7. Consider the following\nStatement I: something"
        assert detect_ordinal(text) == 7

    def test_no_leading_digit_at_all(self):
        assert detect_ordinal("Which of the following...") is None


class TestStripOrdinal:
    def test_strip_period(self):
        assert strip_ordinal("21. Consider the following") == "Consider the following"

    def test_strip_space_separator(self):
        assert strip_ordinal("3 Statement I:") == "Statement I:"

    def test_strip_paren(self):
        assert strip_ordinal("1) Some text") == "Some text"

    def test_strip_leading_whitespace_and_ordinal(self):
        assert strip_ordinal("  21.  text") == "text"

    def test_no_ordinal_unchanged(self):
        assert strip_ordinal("Statement I:") == "Statement I:"

    def test_empty_string(self):
        assert strip_ordinal("") == ""
