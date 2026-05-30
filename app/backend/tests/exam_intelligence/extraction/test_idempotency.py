"""Unit tests for idempotency.py."""
from __future__ import annotations

import pytest

from app.exam_intelligence.extraction.idempotency import (
    DedupDecision,
    compute_content_hash,
    compute_idempotency_key,
    decide_dedup,
    normalize_for_content_hash,
)


class TestNormalize:
    def test_lowercase(self):
        assert normalize_for_content_hash("Hello") == "hello"

    def test_collapse_whitespace(self):
        assert normalize_for_content_hash("a  b\tc\nd") == "a b c d"

    def test_strip_punctuation(self):
        result = normalize_for_content_hash("What is X?")
        assert '?' not in result
        assert 'what' in result
        assert 'x' in result

    def test_preserves_alphanumerics(self):
        result = normalize_for_content_hash("Q12 Article 370")
        assert 'q12' in result
        assert 'article' in result
        assert '370' in result

    def test_strips_leading_trailing_whitespace(self):
        assert normalize_for_content_hash("  hello  ") == "hello"

    def test_empty_string(self):
        assert normalize_for_content_hash("") == ""


class TestIdempotencyKey:
    def test_deterministic(self):
        k1 = compute_idempotency_key('doc-a', 3, 1, 'v1.0.0')
        k2 = compute_idempotency_key('doc-a', 3, 1, 'v1.0.0')
        assert k1 == k2

    def test_differs_by_document(self):
        k1 = compute_idempotency_key('doc-a', 3, 1, 'v1.0.0')
        k2 = compute_idempotency_key('doc-b', 3, 1, 'v1.0.0')
        assert k1 != k2

    def test_differs_by_page(self):
        k1 = compute_idempotency_key('doc-a', 3, 1, 'v1.0.0')
        k2 = compute_idempotency_key('doc-a', 5, 1, 'v1.0.0')
        assert k1 != k2

    def test_differs_by_question_number(self):
        k1 = compute_idempotency_key('doc-a', 3, 1, 'v1.0.0')
        k2 = compute_idempotency_key('doc-a', 3, 2, 'v1.0.0')
        assert k1 != k2

    def test_differs_by_version(self):
        k1 = compute_idempotency_key('doc-a', 3, 1, 'v1.0.0')
        k2 = compute_idempotency_key('doc-a', 3, 1, 'v1.1.0')
        assert k1 != k2

    def test_returns_hex_string(self):
        k = compute_idempotency_key('doc-a', 3, 1, 'v1.0.0')
        assert len(k) == 64
        assert all(c in '0123456789abcdef' for c in k)


class TestContentHash:
    def test_deterministic(self):
        h1 = compute_content_hash("What is X?")
        h2 = compute_content_hash("What is X?")
        assert h1 == h2

    def test_normalization_applied(self):
        # Whitespace differences should hash to same value
        h1 = compute_content_hash("What  is  X?")
        h2 = compute_content_hash("What is X?")
        assert h1 == h2

    def test_case_insensitive(self):
        h1 = compute_content_hash("WHAT IS X?")
        h2 = compute_content_hash("what is x?")
        assert h1 == h2

    def test_different_texts_different_hashes(self):
        h1 = compute_content_hash("Question about Y")
        h2 = compute_content_hash("Question about Z")
        assert h1 != h2


class TestDedupDecision:
    def test_inserts_when_no_existing_rows(self):
        d = decide_dedup(
            candidate_question_text="What is X?",
            candidate_idempotency_key="abc",
            candidate_content_hash="def",
            existing_rows_for_document=[],
        )
        assert d.action == 'insert'
        assert d.linked_row_id is None

    def test_skips_on_idempotency_key_match(self):
        existing = [{
            'id': 'row-1',
            'idempotency_key': 'abc',
            'content_hash': 'other',
            'question_text': 'something completely different',
        }]
        d = decide_dedup(
            candidate_question_text="What is X?",
            candidate_idempotency_key='abc',
            candidate_content_hash='different',
            existing_rows_for_document=existing,
        )
        assert d.action == 'skip_idempotent'
        assert d.linked_row_id == 'row-1'

    def test_links_on_exact_content_hash(self):
        existing = [{
            'id': 'row-1',
            'idempotency_key': 'other-key',
            'content_hash': 'def',
            'question_text': 'What is X?',
        }]
        d = decide_dedup(
            candidate_question_text="What is X?",
            candidate_idempotency_key='different-key',
            candidate_content_hash='def',
            existing_rows_for_document=existing,
        )
        assert d.action == 'link_fuzzy_duplicate'
        assert d.linked_row_id == 'row-1'

    def test_links_on_fuzzy_match_above_threshold(self):
        existing = [{
            'id': 'row-1',
            'idempotency_key': 'other-key',
            'content_hash': 'other-hash',
            'question_text': "What is X? Some minor varation here",
        }]
        d = decide_dedup(
            candidate_question_text="What is X? Some minor variation here",
            candidate_idempotency_key='different-key',
            candidate_content_hash='different-hash',
            existing_rows_for_document=existing,
            fuzzy_threshold=0.85,
        )
        assert d.action == 'link_fuzzy_duplicate'

    def test_inserts_when_fuzzy_below_threshold(self):
        existing = [{
            'id': 'row-1',
            'idempotency_key': 'other-key',
            'content_hash': 'other-hash',
            'question_text': "Completely different question about the Constitution",
        }]
        d = decide_dedup(
            candidate_question_text="What is X?",
            candidate_idempotency_key='different-key',
            candidate_content_hash='different-hash',
            existing_rows_for_document=existing,
            fuzzy_threshold=0.85,
        )
        assert d.action == 'insert'

    def test_idempotency_takes_priority_over_content_hash(self):
        """idempotency_key match fires before content_hash check."""
        existing = [{
            'id': 'row-1',
            'idempotency_key': 'abc',
            'content_hash': 'abc-hash',
            'question_text': 'some text',
        }]
        d = decide_dedup(
            candidate_question_text="What is X?",
            candidate_idempotency_key='abc',
            candidate_content_hash='abc-hash',
            existing_rows_for_document=existing,
        )
        assert d.action == 'skip_idempotent'

    def test_rows_with_empty_question_text_skipped_in_fuzzy(self):
        existing = [{'id': 'row-1', 'idempotency_key': 'other', 'content_hash': 'other', 'question_text': ''}]
        d = decide_dedup(
            candidate_question_text="What is X?",
            candidate_idempotency_key='different',
            candidate_content_hash='different',
            existing_rows_for_document=existing,
        )
        assert d.action == 'insert'
