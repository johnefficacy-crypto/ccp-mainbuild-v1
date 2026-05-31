"""Stateless syllabus mention proposer (PR3a).

propose_syllabus_mentions(...) -> list[dict]

Pure read — no writes, no side effects. Returns proposed mention objects;
the caller decides whether and how to persist them.

Algorithm:
  1. Resolve syllabus document (belongs to exam, else raise)
  2. Load document_pages ordered by page_number
  3. Load topic_aliases scoped to the exam's subjects
  4. For each page text, for each alias:
       - exact substring match → confidence 1.0
       - fuzzy sliding-window match ≥ threshold → confidence = ratio
  5. Deduplicate by (topic_id, source_page) — keep highest confidence
  6. Return sorted by (source_page asc, confidence desc)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.exam_intelligence.text_utils import levenshtein_ratio, normalize_text

logger = logging.getLogger("career_copilot.exam_intelligence.syllabus_mapper")

SYLLABUS_ALIAS_MATCH_THRESHOLD: float = 0.85
PROPOSER_VERSION: str = "syllabus_mapper_v1"


def _safe(call, default=None):
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("syllabus_mapper read failed: %s", exc)
        return default


class ProposerError(ValueError):
    """Raised when input validation fails (caller maps to HTTP error)."""
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def _sliding_window_ratio(alias_norm: str, page_norm: str) -> tuple[float, int] | None:
    """Scan page_norm for the best fuzzy match of alias_norm.

    Returns (best_ratio, start_pos) or None if alias is longer than page.
    Uses a sliding window of len(alias_norm) characters.
    """
    alen = len(alias_norm)
    plen = len(page_norm)
    if alen == 0 or alen > plen:
        return None
    best_ratio = 0.0
    best_pos = 0
    # Step by word boundary when possible to reduce O(n*m) cost.
    # Fall back to character step if alias is short.
    step = max(1, alen // 4)
    for start in range(0, plen - alen + 1, step):
        window = page_norm[start : start + alen]
        r = levenshtein_ratio(alias_norm, window)
        if r > best_ratio:
            best_ratio = r
            best_pos = start
    return best_ratio, best_pos


def propose_syllabus_mentions(
    sb: Any,
    *,
    exam_id: str,
    syllabus_document_id: str,
    cycle_id: str | None = None,
    phase_id: str | None = None,
    threshold: float | None = None,
) -> list[dict]:
    """Return proposed syllabus_topic_mention objects for the given document.

    Raises ProposerError (status_code=404 or 422) on invalid input.
    """
    eff_threshold = threshold if threshold is not None else SYLLABUS_ALIAS_MATCH_THRESHOLD

    # ── 1. Resolve document ───────────────────────────────────────────────────
    doc_rows = _safe(
        lambda: (
            sb.table("document_assets")
            .select("id, exam_id, exam_cycle_id")
            .eq("id", syllabus_document_id)
            .limit(1)
            .execute()
            .data
        ),
        default=[],
    ) or []
    if not doc_rows:
        raise ProposerError(f"syllabus document not found: {syllabus_document_id}", 404)
    doc = doc_rows[0]
    if doc.get("exam_id") != exam_id:
        raise ProposerError("syllabus document does not belong to this exam", 422)

    # ── 2. Load document pages ────────────────────────────────────────────────
    pages = _safe(
        lambda: (
            sb.table("document_pages")
            .select("page_number, text_content")
            .eq("document_id", syllabus_document_id)
            .order("page_number", desc=False)
            .limit(2000)
            .execute()
            .data
        ),
        default=[],
    ) or []

    if not pages:
        return []

    # ── 3. Load topic_aliases for the exam's subject scope ────────────────────
    # topics → subject_id → subjects → exam_subject_map → exam_id
    # We query topic_aliases joined through topics that belong to this exam.
    # Since Supabase doesn't do cross-table joins in the client, we load
    # exam's subject-scoped topics first, then their aliases.
    topic_rows = _safe(
        lambda: (
            sb.table("topics")
            .select("id, subject_id")
            .limit(20000)
            .execute()
            .data
        ),
        default=[],
    ) or []

    # Scope to exam's subjects via exam_subject_map
    esm_rows = _safe(
        lambda: (
            sb.table("exam_subject_map")
            .select("subject_id")
            .eq("exam_id", exam_id)
            .limit(1000)
            .execute()
            .data
        ),
        default=[],
    ) or []
    exam_subject_ids = {r["subject_id"] for r in esm_rows if r.get("subject_id")}

    if exam_subject_ids:
        scoped_topic_ids = [t["id"] for t in topic_rows if t.get("subject_id") in exam_subject_ids]
    else:
        # Fallback: use all topics (no subject scoping configured)
        scoped_topic_ids = [t["id"] for t in topic_rows if t.get("id")]

    if not scoped_topic_ids:
        return []

    # Load aliases in chunks
    aliases: list[dict] = []
    chunk = 200
    for i in range(0, len(scoped_topic_ids), chunk):
        batch = scoped_topic_ids[i : i + chunk]
        batch_rows = _safe(
            lambda b=batch: (
                sb.table("topic_aliases")
                .select("id, topic_id, alias_text, normalized_alias")
                .in_("topic_id", b)
                .limit(10000)
                .execute()
                .data
            ),
            default=[],
        ) or []
        aliases.extend(batch_rows)

    if not aliases:
        return []

    # Precompute normalized alias texts
    alias_norms = [
        (a["topic_id"], a.get("alias_text") or "", a.get("normalized_alias") or normalize_text(a.get("alias_text") or ""))
        for a in aliases
    ]

    # ── 4. Match aliases against pages ────────────────────────────────────────
    # key = (topic_id, source_page) → best proposal dict
    best: dict[tuple, dict] = {}

    for page in pages:
        page_num = page.get("page_number", 0)
        raw_text = page.get("text_content") or ""
        page_norm = normalize_text(raw_text)
        if not page_norm:
            continue

        for topic_id, alias_text, alias_norm in alias_norms:
            if not alias_norm:
                continue
            key = (topic_id, page_num)
            existing = best.get(key)

            # Exact substring match
            pos = page_norm.find(alias_norm)
            if pos != -1:
                raw_substr = raw_text[pos : pos + len(alias_norm)]
                if not existing or existing["confidence_score"] < 1.0:
                    best[key] = {
                        "syllabus_document_id": syllabus_document_id,
                        "exam_id": exam_id,
                        "exam_cycle_id": cycle_id,
                        "exam_phase_id": phase_id,
                        "topic_id": topic_id,
                        "raw_text": raw_substr,
                        "normalized_text": alias_norm,
                        "mention_type": "explicit",
                        "confidence_score": 1.0,
                        "source_page": page_num,
                        "matched_alias": alias_text,
                        "match_method": "topic_alias_exact",
                        "proposer_version": PROPOSER_VERSION,
                    }
                continue

            # Fuzzy sliding-window match
            if existing and existing["confidence_score"] >= 1.0:
                continue
            result = _sliding_window_ratio(alias_norm, page_norm)
            if result is None:
                continue
            ratio, pos = result
            if ratio >= eff_threshold:
                raw_substr = raw_text[pos : pos + len(alias_norm)]
                if not existing or existing["confidence_score"] < ratio:
                    best[key] = {
                        "syllabus_document_id": syllabus_document_id,
                        "exam_id": exam_id,
                        "exam_cycle_id": cycle_id,
                        "exam_phase_id": phase_id,
                        "topic_id": topic_id,
                        "raw_text": raw_substr,
                        "normalized_text": normalize_text(raw_substr),
                        "mention_type": "explicit",
                        "confidence_score": round(ratio, 4),
                        "source_page": page_num,
                        "matched_alias": alias_text,
                        "match_method": "topic_alias_fuzzy",
                        "proposer_version": PROPOSER_VERSION,
                    }

    # ── 5 & 6. Deduplicated list sorted by (source_page, confidence desc) ────
    return sorted(best.values(), key=lambda p: (p["source_page"], -p["confidence_score"]))
