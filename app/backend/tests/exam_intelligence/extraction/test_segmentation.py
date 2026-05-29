"""Unit tests for segmentation.py."""
from __future__ import annotations

import pytest

from app.exam_intelligence.extraction.segmentation import (
    block_to_question,
    cluster_by_vertical_gap,
    segment_page,
)
from app.exam_intelligence.extraction.types import Word


def _word(text: str, x: float = 0.1, y: float = 0.1, w: float = 0.1, h: float = 0.02,
          page: int = 1, confidence: float = 90.0) -> Word:
    return Word(text=text, bbox=(x, y, x + w, y + h), page=page, confidence=confidence)


def _words_for_question(ordinal: str, *tokens: str, y_start: float = 0.1, page: int = 1) -> list[Word]:
    """Build a list of Words for a single question block, stacked vertically."""
    words = []
    y = y_start
    # first word is the ordinal
    words.append(_word(ordinal, x=0.05, y=y, page=page))
    y += 0.025
    for token in tokens:
        words.append(_word(token, x=0.05, y=y, page=page))
        y += 0.025
    return words


class TestClusterByVerticalGap:
    def test_empty_returns_empty(self):
        assert cluster_by_vertical_gap([]) == []

    def test_single_word_one_block(self):
        result = cluster_by_vertical_gap([_word("hello")])
        assert len(result) == 1

    def test_tight_words_one_block(self):
        words = [_word("word", y=0.1 + i * 0.02) for i in range(5)]
        result = cluster_by_vertical_gap(words)
        assert len(result) == 1

    def test_gap_creates_new_block(self):
        close = [_word("w", y=0.1 + i * 0.02) for i in range(3)]
        far = [_word("w", y=0.5 + i * 0.02) for i in range(3)]
        result = cluster_by_vertical_gap(close + far)
        assert len(result) == 2

    def test_three_blocks(self):
        g1 = [_word("a", y=0.05 + i * 0.02) for i in range(3)]
        g2 = [_word("b", y=0.30 + i * 0.02) for i in range(3)]
        g3 = [_word("c", y=0.60 + i * 0.02) for i in range(3)]
        result = cluster_by_vertical_gap(g1 + g2 + g3)
        assert len(result) == 3


class TestBlockToQuestion:
    def test_question_with_ordinal_extracted(self):
        block = _words_for_question("21.", "Consider", "the", "following")
        q = block_to_question(block)
        assert q is not None
        assert q.question_number == 21
        assert "Consider" in q.question_text

    def test_no_ordinal_returns_none(self):
        block = [_word("Statement"), _word("I:", x=0.15), _word("something", x=0.20)]
        q = block_to_question(block)
        assert q is None

    def test_empty_block_returns_none(self):
        assert block_to_question([]) is None

    def test_ordinal_outside_range_returns_none(self):
        block = _words_for_question("999.", "Some", "text")
        q = block_to_question(block)
        assert q is None

    def test_ordinal_zero_returns_none(self):
        block = _words_for_question("0.", "Some", "text")
        q = block_to_question(block)
        assert q is None

    def test_region_built_from_block_bbox(self):
        block = _words_for_question("7.", "Which", "of", "the")
        q = block_to_question(block)
        assert q is not None
        assert len(q.regions) == 1
        assert q.regions[0].page == 1

    def test_ocr_p50_confidence_computed(self):
        block = _words_for_question("3.", "text")
        # All words have confidence=90
        q = block_to_question(block)
        assert q is not None
        assert "ocr_p50" in q.confidence_by_field
        assert q.confidence_by_field["ocr_p50"] == pytest.approx(90.0, abs=1.0)

    def test_statement_based_question_is_single_block(self):
        # A question that has "I. ... II. ... III." internally — these are NOT
        # question boundaries. The entire block should emit one question.
        block = (
            _words_for_question("5.", "Consider", y_start=0.10)
            + [
                _word("I.", x=0.05, y=0.18),
                _word("Statement", x=0.10, y=0.18),
                _word("II.", x=0.05, y=0.21),
                _word("Another", x=0.10, y=0.21),
            ]
        )
        q = block_to_question(block)
        assert q is not None
        assert q.question_number == 5


class TestSegmentPage:
    def test_single_column_three_questions(self):
        w1 = _words_for_question("1.", "Text", "one", y_start=0.05)
        w2 = _words_for_question("2.", "Text", "two", y_start=0.30)
        w3 = _words_for_question("3.", "Text", "three", y_start=0.60)
        questions = segment_page(w1 + w2 + w3, page=1)
        q_nums = {q.question_number for q in questions}
        assert {1, 2, 3}.issubset(q_nums)

    def test_two_column_questions_from_both_columns(self):
        # Left column (x ≈ 0.1–0.4)
        left = _words_for_question("4.", "Left", "col", y_start=0.10)
        left = [Word(text=w.text, bbox=(w.bbox[0], w.bbox[1], w.bbox[2], w.bbox[3]),
                     page=w.page, confidence=w.confidence) for w in left]
        # Right column (x ≈ 0.6–0.9)
        right = []
        y = 0.10
        right.append(Word(text="5.", bbox=(0.60, y, 0.65, y + 0.02), page=1, confidence=90.0))
        y += 0.025
        right.append(Word(text="Right", bbox=(0.60, y, 0.72, y + 0.02), page=1, confidence=90.0))
        questions = segment_page(left + right, page=1)
        q_nums = {q.question_number for q in questions}
        assert 4 in q_nums
        assert 5 in q_nums

    def test_non_question_blocks_discarded(self):
        # Header/footer words without leading ordinal
        noise = [
            _word("UPSC", x=0.3, y=0.01),
            _word("CSE", x=0.4, y=0.01),
            _word("2026", x=0.5, y=0.01),
        ]
        q_words = _words_for_question("1.", "A", "question", y_start=0.10)
        questions = segment_page(noise + q_words, page=1)
        q_nums = [q.question_number for q in questions]
        assert 1 in q_nums
        # No question with ordinal from noise words
        assert all(1 <= n <= 200 for n in q_nums)

    def test_empty_page_returns_empty(self):
        assert segment_page([], page=1) == []

    def test_out_of_range_ordinal_discarded(self):
        block = _words_for_question("999.", "garbage")
        questions = segment_page(block, page=1)
        assert not any(q.question_number == 999 for q in questions)
