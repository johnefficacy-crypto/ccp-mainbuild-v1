"""Unit tests for layout.py — detect_columns and assign_words_to_columns."""
from __future__ import annotations

import pytest

from app.exam_intelligence.extraction.layout import (
    assign_words_to_columns,
    detect_columns,
)
from app.exam_intelligence.extraction.types import Word


def _word(x_min: float, x_max: float, y_min: float = 0.1, y_max: float = 0.15,
          page: int = 1, text: str = "word") -> Word:
    return Word(text=text, bbox=(x_min, y_min, x_max, y_max), page=page, confidence=90.0)


def _two_col_words(n: int = 30) -> list[Word]:
    """Create words clearly in two columns: left [0.05..0.45] and right [0.55..0.95]."""
    words = []
    for i in range(n):
        y = 0.05 + i * 0.02
        # left column word
        words.append(_word(0.05, 0.20, y_min=y, y_max=y + 0.015))
        # right column word
        words.append(_word(0.55, 0.75, y_min=y, y_max=y + 0.015))
    return words


class TestDetectColumns:
    def test_empty_page_returns_single_column(self):
        cols = detect_columns([])
        assert cols == [(0.0, 1.0)]

    def test_single_column_words(self):
        # All words clustered near x=0.25 — single column
        words = [_word(0.1, 0.4, y_min=0.05 + i * 0.02) for i in range(20)]
        cols = detect_columns(words)
        assert cols == [(0.0, 1.0)]

    def test_two_column_bimodal(self):
        words = _two_col_words(40)
        cols = detect_columns(words)
        assert len(cols) == 2
        # Split should be somewhere between the two clusters (~0.4–0.6)
        split = cols[0][1]
        assert 0.3 < split < 0.7, f"Split at {split} not near centre"

    def test_two_columns_2026_page_width(self):
        # Page dimensions vary (2026: 538.56 pts); all coords are normalized so
        # detection must work regardless. Use same distribution as above.
        words = _two_col_words(50)
        cols = detect_columns(words)
        assert len(cols) == 2

    def test_two_columns_2025_page_width(self):
        # 2025 paper is wider (602.64 pts) but normalized coords are the same.
        words = _two_col_words(50)
        cols = detect_columns(words)
        assert len(cols) == 2

    def test_unbalanced_columns_still_detected(self):
        # Left column has 60 words, right has 20 — should still split.
        left = [_word(0.05, 0.20, y_min=0.01 + i * 0.01) for i in range(60)]
        right = [_word(0.55, 0.75, y_min=0.01 + i * 0.02) for i in range(20)]
        cols = detect_columns(left + right)
        assert len(cols) == 2


class TestAssignWordsToColumns:
    def test_single_column_all_words_assigned(self):
        words = [_word(0.1, 0.4, y_min=0.05 + i * 0.02) for i in range(5)]
        assignment = assign_words_to_columns(words, [(0.0, 1.0)])
        assert len(assignment[0]) == 5

    def test_two_columns_correct_assignment(self):
        left_words = [_word(0.05, 0.20, y_min=0.05 + i * 0.02) for i in range(5)]
        right_words = [_word(0.55, 0.75, y_min=0.05 + i * 0.02) for i in range(5)]
        cols = [(0.0, 0.5), (0.5, 1.0)]
        assignment = assign_words_to_columns(left_words + right_words, cols)
        assert len(assignment[0]) == 5
        assert len(assignment[1]) == 5

    def test_words_sorted_by_y_min(self):
        # Words provided in reverse y order — must come out sorted ascending.
        words = [_word(0.1, 0.3, y_min=0.9 - i * 0.1) for i in range(5)]
        assignment = assign_words_to_columns(words, [(0.0, 1.0)])
        y_vals = [w.bbox[1] for w in assignment[0]]
        assert y_vals == sorted(y_vals)

    def test_centroid_used_not_left_edge(self):
        # Word spans x=[0.45, 0.75]; centroid ≈ 0.60 → right column.
        word = _word(0.45, 0.75)
        cols = [(0.0, 0.5), (0.5, 1.0)]
        assignment = assign_words_to_columns([word], cols)
        assert len(assignment[1]) == 1  # right column
        assert len(assignment[0]) == 0
