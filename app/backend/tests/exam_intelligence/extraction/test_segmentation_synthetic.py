"""Synthetic acceptance test for the extraction segmentation pipeline.

Builds ~65 Word objects simulating OCR output for a two-column UPSC page.
Asserts that the rebuilt pipeline (extract_from_words) correctly:
  - extracts exactly 6 questions (Q1–Q6)
  - does not emit statement numerals as separate questions
  - excludes option lines and MCQ footer from question_text

This test MUST fail RED against the pre-fix code (pipeline has no
extract_from_words) and pass after the rebuild.
"""
from __future__ import annotations

import pytest

from app.exam_intelligence.extraction import pipeline
from app.exam_intelligence.extraction.types import Word


def _w(
    text: str,
    x: float,
    y: float,
    w: float = 0.08,
    h: float = 0.018,
    page: int = 3,
) -> Word:
    return Word(text=text, bbox=(x, y, x + w, y + h), page=page, confidence=90.0)


# ---------------------------------------------------------------------------
# Synthetic two-column page  (normalized coordinates, page=3)
#
# Left column   x ≈ 0.01 – 0.43   col_left detected ≈ 0.00
# Right column  x ≈ 0.51 – 0.94   col_left detected ≈ 0.50
#
# Anchor threshold = effective_left + 0.04  (effective_left = min word x in column):
#   Left  anchors:    effective_left=0.01, gate=0.05  →  "1." at x=0.01  ✓
#   Left  statements: x_min=0.06 > gate=0.05          →  REJECTED
#   Right anchors:    effective_left=0.51, gate=0.55  →  "4." at x=0.51  ✓
#   Right options:    x_min=0.53, caught by option regex before ordinal check
# ---------------------------------------------------------------------------

WORDS: list[Word] = [
    # ── Left column ─────────────────────────────────────────────────────────
    # Q1 stem with two internal statement numerals
    _w("1.",        0.01, 0.04),
    _w("Consider",  0.10, 0.04),
    _w("the",       0.22, 0.04),
    _w("following", 0.28, 0.04),
    # statement 1 — indented x=0.06 > gate(0.01+0.04=0.05)  →  NOT an anchor
    _w("1.",        0.06, 0.07),
    _w("First",     0.14, 0.07),
    _w("point.",    0.24, 0.07),
    # statement 2 — indented
    _w("2.",        0.06, 0.09),
    _w("Second",    0.14, 0.09),
    _w("point",     0.24, 0.09),
    _w("here.",     0.33, 0.09),
    # continuation line (also x=0.01, but "How" has no ordinal)
    _w("How",       0.01, 0.12),
    _w("many",      0.10, 0.12),
    _w("are",       0.18, 0.12),
    _w("correct?",  0.24, 0.12),

    # Q2
    _w("2.",        0.01, 0.22),
    _w("Which",     0.10, 0.22),
    _w("of",        0.19, 0.22),
    _w("the",       0.24, 0.22),
    _w("following", 0.29, 0.22),
    _w("rivers",    0.10, 0.25),
    _w("flows",     0.19, 0.25),
    _w("westward?", 0.25, 0.25),

    # Q3 stem + options (options MUST be excluded from question_text)
    _w("3.",        0.01, 0.36),
    _w("Arrange",   0.10, 0.36),
    _w("the",       0.20, 0.36),
    _w("events",    0.26, 0.36),
    _w("(a)",       0.03, 0.40),   # option label — find_stem_end stops here
    _w("First",     0.12, 0.40),
    _w("event",     0.20, 0.40),
    _w("(b)",       0.03, 0.43),
    _w("Second",    0.12, 0.43),
    _w("event",     0.20, 0.43),
    _w("Select",    0.01, 0.47),   # MCQ footer — also excluded
    _w("the",       0.10, 0.47),
    _w("answer",    0.17, 0.47),
    _w("using",     0.27, 0.47),
    _w("codes",     0.35, 0.47),

    # ── Right column ────────────────────────────────────────────────────────
    # Q4
    _w("4.",         0.51, 0.04),
    _w("With",       0.60, 0.04),
    _w("reference",  0.68, 0.04),
    _w("to",         0.79, 0.04),
    _w("India,",     0.82, 0.04),
    _w("consider",   0.60, 0.07),
    _w("the",        0.72, 0.07),
    _w("following",  0.79, 0.07),

    # Q5
    _w("5.",         0.51, 0.22),
    _w("The",        0.60, 0.22),
    _w("Preamble",   0.67, 0.22),
    _w("declares",   0.79, 0.22),
    _w("India",      0.60, 0.25),
    _w("a",          0.70, 0.25),
    _w("republic.",  0.73, 0.25),

    # Q6 stem + options + "Select the answer" footer
    _w("6.",          0.51, 0.36),
    _w("Which",       0.60, 0.36),
    _w("article",     0.69, 0.36),
    _w("relates",     0.79, 0.36),
    _w("to",          0.60, 0.39),
    _w("fundamental", 0.65, 0.39),
    _w("rights?",     0.79, 0.39),
    _w("(a)",         0.53, 0.43),  # option — find_stem_end stops here
    _w("Article",     0.62, 0.43),
    _w("12",          0.73, 0.43),
    _w("(b)",         0.53, 0.46),
    _w("Article",     0.62, 0.46),
    _w("13",          0.73, 0.46),
    _w("Select",      0.51, 0.50),
    _w("the",         0.60, 0.50),
    _w("answer",      0.67, 0.50),
    _w("using",       0.77, 0.50),
    _w("codes",       0.86, 0.50),
]


def test_six_questions_extracted():
    result = pipeline.extract_from_words(WORDS, page=3, document_id="test")
    qnums = sorted(q.question_number for q in result.questions)
    assert qnums == [1, 2, 3, 4, 5, 6]


def test_no_statement_numerals_as_questions():
    result = pipeline.extract_from_words(WORDS, page=3, document_id="test")
    # Exactly one question with number 1 — the anchor, not a statement numeral.
    assert len([q for q in result.questions if q.question_number == 1]) == 1


def test_stems_exclude_options():
    result = pipeline.extract_from_words(WORDS, page=3, document_id="test")
    for q in result.questions:
        assert "(a)" not in q.question_text
        assert "(b)" not in q.question_text
        assert "Select the answer" not in q.question_text


def test_q1_contains_stem_text():
    result = pipeline.extract_from_words(WORDS, page=3, document_id="test")
    q1 = next(q for q in result.questions if q.question_number == 1)
    assert "Consider" in q1.question_text
