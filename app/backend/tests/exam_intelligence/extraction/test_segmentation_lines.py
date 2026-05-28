"""Unit tests for reconstruct_lines and join_lines_text."""
from __future__ import annotations

import pytest

from app.exam_intelligence.extraction.segmentation import (
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
