"""
Idempotency and content-hash dedup for extractor writes.

Two keys per extracted question:

  idempotency_key — sha256(doc_id || page || question_number || extractor_version)
                    Identity key. Same logical question yields the same key across
                    re-runs. bbox jitter does NOT change this.

  content_hash    — sha256(normalize(question_text))
                    Content fingerprint for dedup against existing manual rows.

Why question_number, not regions_hash:
  Empirical IoU p10=0.000 on the 2026 GS-I fixture acceptance run. At least 10%
  of matched questions have zero spatial overlap with their fixture position.
  Bbox-based identity would yield different idempotency_keys for the same logical
  question on re-runs, defeating dedup. (page, question_number) is stable.

Why fuzzy content_hash, not exact:
  Empirical text-sim p10=0.432 on the 2026 fixture. Some matched questions have
  <50% character similarity to ground truth due to OCR noise. Exact sha256 of
  normalized text would treat them as new questions on every re-run, polluting
  the reviewer queue. The fuzzy threshold (0.85) is set above p25=0.874 so that
  clearly noisy matches are still caught.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from Levenshtein import ratio


_WHITESPACE_RE = re.compile(r'\s+')
_PUNCT_RE = re.compile(r'[^\w\s]')


def normalize_for_content_hash(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation.

    Canonical normalization for the content_hash column. Same input → same hash,
    modulo trivial formatting differences.
    """
    t = _PUNCT_RE.sub(' ', text.lower())
    t = _WHITESPACE_RE.sub(' ', t).strip()
    return t


def compute_idempotency_key(
    document_id: str,
    page: int,
    question_number: int,
    extractor_version: str,
) -> str:
    """Deterministic identity key for a logical question."""
    payload = f"{document_id}|{page}|{question_number}|{extractor_version}"
    return hashlib.sha256(payload.encode()).hexdigest()


def compute_content_hash(question_text: str) -> str:
    """sha256 of normalized text. For exact-match fast path in dedup."""
    normalized = normalize_for_content_hash(question_text)
    return hashlib.sha256(normalized.encode()).hexdigest()


@dataclass(frozen=True)
class DedupDecision:
    action: str  # 'insert' | 'skip_idempotent' | 'link_fuzzy_duplicate'
    reason: str
    linked_row_id: str | None = None  # set for link_fuzzy_duplicate


def decide_dedup(
    candidate_question_text: str,
    candidate_idempotency_key: str,
    candidate_content_hash: str,
    existing_rows_for_document: list[dict],
    fuzzy_threshold: float = 0.85,
) -> DedupDecision:
    """Decide whether to insert, skip (idempotent re-run), or link to existing row.

    Logic (in priority order):
      1. idempotency_key exact match  → skip_idempotent (same extraction re-run)
      2. content_hash exact match     → link_fuzzy_duplicate (same content, different path)
      3. Levenshtein ratio >= threshold → link_fuzzy_duplicate (OCR-noisy match)
      4. Otherwise                    → insert
    """
    candidate_normalized = normalize_for_content_hash(candidate_question_text)

    # Step 1: exact idempotency
    for row in existing_rows_for_document:
        if row.get('idempotency_key') == candidate_idempotency_key:
            return DedupDecision(
                action='skip_idempotent',
                reason=f"idempotency_key match with existing row {row['id']}",
                linked_row_id=row['id'],
            )

    # Step 2: exact content_hash (fast path)
    for row in existing_rows_for_document:
        if row.get('content_hash') == candidate_content_hash:
            return DedupDecision(
                action='link_fuzzy_duplicate',
                reason=f"content_hash exact match with row {row['id']}",
                linked_row_id=row['id'],
            )

    # Step 3: fuzzy Levenshtein ratio
    best_ratio = 0.0
    best_match: dict | None = None
    for row in existing_rows_for_document:
        existing_text = row.get('question_text', '')
        if not existing_text:
            continue
        r = ratio(candidate_normalized, normalize_for_content_hash(existing_text))
        if r > best_ratio:
            best_ratio = r
            best_match = row

    if best_match and best_ratio >= fuzzy_threshold:
        return DedupDecision(
            action='link_fuzzy_duplicate',
            reason=f"fuzzy match (ratio={best_ratio:.3f}) with row {best_match['id']}",
            linked_row_id=best_match['id'],
        )

    return DedupDecision(action='insert', reason='no existing match')
