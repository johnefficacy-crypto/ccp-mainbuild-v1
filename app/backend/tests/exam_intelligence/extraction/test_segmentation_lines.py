"""Unit tests for reconstruct_lines, join_lines_text, and find_anchor_lines."""
from __future__ import annotations

import pytest

from app.exam_intelligence.extraction.segmentation import (
    find_anchor_lines,
    join_lines_text,
    reconstruct_lines,
)
from app.exam_intelligence.extraction.types import Word


def _w(
    text: str,
    x: float,
    y: float,
    w: float = 0.08,
    h: float = 0.018,
    page: int = 1,
) -> Word:
    return Word(text=text, bbox=(x, y, x + w, y + h), page=page, confidence=90.0)


class TestReconstructLines:
    def test_empty_returns_empty(self):
        assert reconstruct_lines([]) == []

    def test_single_word_one_line(self):
        result = reconstruct_lines([_w("hello", 0.1, 0.1)])
        assert len(result) == 1
        assert result[0][0].text == "hello"

    def test_two_words_same_y_same_line(self):
        w1 = _w("Hello", 0.1, 0.1)
        w2 = _w("world", 0.25, 0.1)
        result = reconstruct_lines([w1, w2])
        assert len(result) == 1
        assert len(result[0]) == 2

    def test_words_sorted_left_to_right_within_line(self):
        w1 = _w("second", 0.5, 0.1)
        w2 = _w("first",  0.1, 0.1)
        result = reconstruct_lines([w1, w2])
        assert len(result) == 1
        assert result[0][0].text == "first"
        assert result[0][1].text == "second"

    def test_two_lines_separated_vertically(self):
        top = [_w("top",    0.1, 0.10, h=0.018)]
        bot = [_w("bottom", 0.1, 0.40, h=0.018)]
        result = reconstruct_lines(top + bot)
        assert len(result) == 2

    def test_no_overlap_yields_different_lines(self):
        # y1: 0.10–0.118   y2: 0.15–0.168   gap = 0.032 > 0 → different lines
        w1 = _w("A", 0.1, 0.10, h=0.018)
        w2 = _w("B", 0.1, 0.15, h=0.018)
        result = reconstruct_lines([w1, w2])
        assert len(result) == 2

    def test_overlap_below_threshold_different_lines(self):
        # h=0.018, w2 starts at 0.108 → overlap=0.010, ratio≈0.556 < 0.60
        w1 = _w("A", 0.1, 0.100, h=0.018)
        w2 = _w("B", 0.1, 0.108, h=0.018)
        result = reconstruct_lines([w1, w2])
        assert len(result) == 2

    def test_overlap_at_60pct_same_line(self):
        # h=0.020, w2 at 0.108 → overlap=0.012, ratio=0.60 ≥ 0.60 → same line
        h = 0.020
        w1 = _w("A", 0.1, 0.100, h=h)
        w2 = _w("B", 0.1, 0.108, h=h)
        result = reconstruct_lines([w1, w2])
        assert len(result) == 1

    def test_three_distinct_lines(self):
        words = (
            [_w("a", 0.1 + i * 0.06, 0.10) for i in range(4)]
            + [_w("b", 0.1 + i * 0.06, 0.30) for i in range(4)]
            + [_w("c", 0.1 + i * 0.06, 0.60) for i in range(4)]
        )
        result = reconstruct_lines(words)
        assert len(result) == 3

    def test_each_line_sorted_by_x(self):
        words = [
            _w("z", 0.9, 0.10),
            _w("a", 0.1, 0.10),
            _w("m", 0.5, 0.10),
        ]
        result = reconstruct_lines(words)
        assert len(result) == 1
        assert [w.text for w in result[0]] == ["a", "m", "z"]

    def test_mixed_heights_overlap_criterion(self):
        # Tall word (h=0.04) and a short word (h=0.018) that overlaps well
        tall  = _w("tall",  0.1, 0.10, h=0.040)
        short = _w("short", 0.3, 0.12, h=0.018)
        # overlap: min(0.138, 0.140) - max(0.12, 0.10) = 0.138 - 0.12 = 0.018
        # smaller_h = min(0.040, 0.018) = 0.018, ratio = 0.018/0.018 = 1.0 ≥ 0.60
        result = reconstruct_lines([tall, short])
        assert len(result) == 1


class TestJoinLinesText:
    def test_empty_returns_empty(self):
        assert join_lines_text([]) == ""

    def test_single_word(self):
        assert join_lines_text([[_w("hello", 0.1, 0.1)]]) == "hello"

    def test_single_line_multiple_words(self):
        words = [_w("Hello", 0.1, 0.1), _w("world", 0.3, 0.1)]
        assert join_lines_text([words]) == "Hello world"

    def test_multiple_lines_newline_separated(self):
        line1 = [_w("First",  0.1, 0.1), _w("line",  0.2, 0.1)]
        line2 = [_w("Second", 0.1, 0.3), _w("line",  0.25, 0.3)]
        assert join_lines_text([line1, line2]) == "First line\nSecond line"

    def test_empty_inner_lines_skipped(self):
        line = [_w("hello", 0.1, 0.1)]
        assert join_lines_text([line, [], line]) == "hello\nhello"


class TestFindAnchorLines:
    """D2 regression tests: anchor gate must reject statement numerals."""

    def test_question_anchor_accepted(self):
        # "1." at x=0.01, column left=0.00 → x ≤ 0.00+0.02 → accepted
        line = [_w("1.", 0.01, 0.10), _w("Consider", 0.10, 0.10)]
        anchors = find_anchor_lines([line], effective_left=0.00)
        assert len(anchors) == 1
        assert anchors[0].ordinal == 1

    def test_statement_numeral_rejected_by_anchor_gate(self):
        # "1." at x=0.05, column left=0.00 → x > 0.00+0.02 → REJECTED (D2 fix)
        line = [_w("1.", 0.05, 0.10), _w("First", 0.14, 0.10), _w("point.", 0.24, 0.10)]
        anchors = find_anchor_lines([line], effective_left=0.00)
        assert anchors == [], (
            "Statement numeral at x=0.05 must be rejected: "
            "x_min(0.05) > col_left(0.00) + _ANCHOR_X_GAP(0.02)"
        )

    def test_question_accepted_statement_rejected_in_same_column(self):
        # Real Q1 at x=0.01, then statement "1." and "2." at x=0.05
        q1_line = [_w("1.", 0.01, 0.04), _w("Consider", 0.10, 0.04)]
        stmt1   = [_w("1.", 0.05, 0.07), _w("First",    0.14, 0.07)]
        stmt2   = [_w("2.", 0.05, 0.09), _w("Second",   0.14, 0.09)]
        q2_line = [_w("2.", 0.01, 0.22), _w("Which",    0.10, 0.22)]
        anchors = find_anchor_lines([q1_line, stmt1, stmt2, q2_line], effective_left=0.00)
        ordinals = [a.ordinal for a in anchors]
        assert ordinals == [1, 2], (
            f"Only real Q1 and Q2 should be anchors, got ordinals={ordinals}"
        )

    def test_monotonicity_rejects_lower_ordinal(self):
        # If Q3 is already accepted, a later line with ordinal 2 is rejected
        q3 = [_w("3.", 0.01, 0.10), _w("Stem", 0.10, 0.10)]
        q2 = [_w("2.", 0.01, 0.30), _w("Stem", 0.10, 0.30)]
        anchors = find_anchor_lines([q3, q2], effective_left=0.00, last_accepted_ordinal=0)
        assert len(anchors) == 1
        assert anchors[0].ordinal == 3


class TestFindAnchorLinesPipePrefix:
    """F-regression: pipe-strip must happen before x-gate so the gate evaluates
    the ordinal token's bbox, not the gutter pipe's."""

    def test_pipe_then_period_separator(self):
        # OCR: "| 26. Which of" — pipe is a separate word at column edge.
        line = [_w("|", 0.00, 0.10, w=0.01), _w("26.", 0.02, 0.10), _w("Which", 0.11, 0.10)]
        anchors = find_anchor_lines([line], effective_left=0.00)
        assert len(anchors) == 1 and anchors[0].ordinal == 26

    def test_pipe_then_space_separator(self):
        # OCR: "| 74 Which" — ordinal "74" followed only by a space (space is a valid separator).
        line = [_w("|", 0.00, 0.10, w=0.01), _w("74", 0.02, 0.10), _w("Which", 0.11, 0.10)]
        anchors = find_anchor_lines([line], effective_left=0.00)
        assert len(anchors) == 1 and anchors[0].ordinal == 74

    def test_multiple_pipes_comma_separator(self):
        # OCR: "| | 4, consider" — two pipe tokens then a comma-separated ordinal.
        line = [
            _w("|", 0.00, 0.10, w=0.01),
            _w("|", 0.01, 0.10, w=0.01),
            _w("4,", 0.02, 0.10),
            _w("consider", 0.11, 0.10),
        ]
        anchors = find_anchor_lines([line], effective_left=0.00)
        assert len(anchors) == 1 and anchors[0].ordinal == 4

    def test_pipe_does_not_smuggle_indented_ordinal_past_gate(self):
        # Pipe sits at the column edge (x=0.00) but the ordinal is far right (x=0.10).
        # The gate must fire on the ordinal's bbox, not the pipe's.
        # effective_left=0.00, gate=0.04 → ordinal at x=0.10 must be REJECTED.
        line = [_w("|", 0.00, 0.10, w=0.01), _w("26.", 0.10, 0.10), _w("Which", 0.20, 0.10)]
        anchors = find_anchor_lines([line], effective_left=0.00)
        assert anchors == [], "pipe at col-edge must not smuggle an indented ordinal through the gate"
