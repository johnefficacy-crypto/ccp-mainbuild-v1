"""Stateless syllabus mention proposer + accept helpers (PR3a/PR3b).

propose_syllabus_mentions(...) -> list[dict]   [PR3a — pure read]
compute_proposal_key(proposal) -> str          [PR3b — deterministic hash]
preview_accept(sb, *, exam_id, proposals)      [PR3b — dry-run]
commit_accept(sb, *, exam_id, proposals, reason, actor_id)  [PR3b — writes]

SCHEMA NOTE (PR3b)
  syllabus_topic_mentions has no dedicated proposer_version / matched_alias /
  source_page columns (migration 031). Proposer metadata is stored in the
  existing `metadata` jsonb column; extraction_method carries match_method.
  No new migration is needed.

PROPOSAL KEY
  sha256(syllabus_document_id + "|" + topic_id + "|" + str(source_page) +
         "|" + normalized_text + "|" + (exam_phase_id or ""))
  Must be identical in frontend JS (see proposalKey.js).

Algorithm (PR3a):
  1. Resolve syllabus document (belongs to exam, else raise)
  2. Load all document_pages for syllabus_document_id ordered by page_number
  3. Load topic_aliases scoped to the exam's subject scope
  4. For each page text, for each alias:
       - exact substring match → confidence 1.0
       - fuzzy sliding-window match ≥ threshold → confidence = ratio
  5. Deduplicate by (topic_id, source_page) — keep highest confidence
  6. Return sorted by (source_page asc, confidence desc)
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.exam_intelligence.text_utils import levenshtein_ratio, normalize_text

logger = logging.getLogger("career_copilot.exam_intelligence.syllabus_mapper")

SYLLABUS_ALIAS_MATCH_THRESHOLD: float = 0.85
PROPOSER_VERSION: str = "syllabus_mapper_v1"
ACCEPT_PROPOSER_VERSION: str = "syllabus_mapper_v1"


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


# ── PR3a: propose ─────────────────────────────────────────────────────────────

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
            sb.table("syllabus_documents")
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
                .select("id, topic_id, alias, normalized_alias")
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
        (a["topic_id"], a.get("alias") or "", a.get("normalized_alias") or normalize_text(a.get("alias") or ""))
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


# ── PR3b: proposal key + accept ───────────────────────────────────────────────

def compute_proposal_key(proposal: dict) -> str:
    """Deterministic identity hash for a proposal.

    sha256(syllabus_document_id|topic_id|source_page|normalized_text|exam_phase_id)

    Must produce identical output to the JS implementation in proposalKey.js.
    """
    parts = "|".join([
        str(proposal.get("syllabus_document_id") or ""),
        str(proposal.get("topic_id") or ""),
        str(proposal.get("source_page") or 0),
        str(proposal.get("normalized_text") or ""),
        str(proposal.get("exam_phase_id") or ""),
    ])
    return hashlib.sha256(parts.encode("utf-8")).hexdigest()


def _validate_proposal(proposal: dict, exam_id: str) -> str | None:
    """Return error reason string or None if valid."""
    if not proposal.get("topic_id"):
        return "missing topic_id"
    if not proposal.get("syllabus_document_id"):
        return "missing syllabus_document_id"
    if proposal.get("exam_id") and proposal["exam_id"] != exam_id:
        return "exam_id mismatch"
    if not isinstance(proposal.get("source_page"), int):
        return "source_page must be an integer"
    if not (proposal.get("normalized_text") or "").strip():
        return "normalized_text is empty"
    return None


def _check_duplicate(sb: Any, proposal: dict) -> str | None:
    """Return existing mention id if a non-rejected duplicate exists, else None."""
    dup_statuses = {"pending", "verified", "needs_correction"}
    rows = _safe(
        lambda: (
            sb.table("syllabus_topic_mentions")
            .select("id, reviewer_status")
            .eq("syllabus_document_id", proposal["syllabus_document_id"])
            .eq("topic_id", proposal["topic_id"])
            .eq("normalized_text", proposal["normalized_text"])
            .limit(10)
            .execute()
            .data
        ),
        default=[],
    ) or []
    for r in rows:
        if r.get("reviewer_status") in dup_statuses:
            return r["id"]
    return None


def preview_accept(sb: Any, *, exam_id: str, proposals: list[dict]) -> dict:
    """Dry-run: classify proposals without writing anything."""
    will_insert: list[dict] = []
    will_skip_duplicate: list[dict] = []
    invalid: list[dict] = []

    for prop in proposals:
        key = compute_proposal_key(prop)
        err = _validate_proposal(prop, exam_id)
        if err:
            invalid.append({**prop, "proposal_key": key, "reason": err})
            continue
        existing_id = _check_duplicate(sb, prop)
        if existing_id:
            will_skip_duplicate.append({**prop, "proposal_key": key, "existing_mention_id": existing_id})
        else:
            will_insert.append({**prop, "proposal_key": key})

    return {
        "exam_id": exam_id,
        "total": len(proposals),
        "will_insert": will_insert,
        "will_skip_duplicate": will_skip_duplicate,
        "invalid": invalid,
        "summary": {
            "insert": len(will_insert),
            "skip_duplicate": len(will_skip_duplicate),
            "invalid": len(invalid),
        },
    }


def commit_accept(
    sb: Any,
    *,
    exam_id: str,
    proposals: list[dict],
    reason: str,
    actor_id: str | None = None,
) -> dict:
    """Write accepted proposals to syllabus_topic_mentions with reviewer_status=pending."""
    per_row: list[dict] = []
    committed = skipped_duplicate = skipped_stale = failed = 0

    for prop in proposals:
        recomputed_key = compute_proposal_key(prop)
        client_key = prop.get("client_proposal_key")

        # Stale guard — client must send the key it received from preview/propose
        if client_key and client_key != recomputed_key:
            per_row.append({
                "proposal_key": recomputed_key,
                "result": "skipped_stale",
                "mention_id": None,
                "reason": "client_proposal_key does not match recomputed key",
            })
            skipped_stale += 1
            continue

        # Validate
        err = _validate_proposal(prop, exam_id)
        if err:
            per_row.append({
                "proposal_key": recomputed_key,
                "result": "failed",
                "mention_id": None,
                "reason": err,
            })
            failed += 1
            continue

        # Duplicate check (idempotent re-run)
        existing_id = _check_duplicate(sb, prop)
        if existing_id:
            per_row.append({
                "proposal_key": recomputed_key,
                "result": "skipped_duplicate",
                "mention_id": existing_id,
                "reason": "duplicate mention already exists",
            })
            skipped_duplicate += 1
            continue

        # Insert
        row = {
            "exam_id": exam_id,
            "syllabus_document_id": prop["syllabus_document_id"],
            "topic_id": prop["topic_id"],
            "exam_cycle_id": prop.get("exam_cycle_id"),
            "exam_phase_id": prop.get("exam_phase_id"),
            "raw_text": prop.get("raw_text") or "",
            "normalized_text": prop["normalized_text"],
            "mention_type": prop.get("mention_type") or "explicit",
            "confidence_score": prop.get("confidence_score"),
            "extraction_method": prop.get("match_method") or prop.get("proposer_version"),
            "reviewer_status": "pending",  # forced — never trust caller
            "metadata": {
                "proposer_version": prop.get("proposer_version") or ACCEPT_PROPOSER_VERSION,
                "matched_alias": prop.get("matched_alias"),
                "source_page": prop.get("source_page"),
                "proposer_match_method": prop.get("match_method"),
                "review_reason": reason,
                "proposal_key": recomputed_key,
                "accepted_by": actor_id,
            },
        }

        try:
            result = sb.table("syllabus_topic_mentions").insert(row).execute()
            inserted = (result.data or [{}])[0]
            mention_id = inserted.get("id")
            per_row.append({
                "proposal_key": recomputed_key,
                "result": "committed",
                "mention_id": mention_id,
                "reason": None,
            })
            committed += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("commit_accept insert failed for key %s: %s", recomputed_key, exc)
            per_row.append({
                "proposal_key": recomputed_key,
                "result": "failed",
                "mention_id": None,
                "reason": str(exc),
            })
            failed += 1

    return {
        "exam_id": exam_id,
        "committed": committed,
        "skipped_duplicate": skipped_duplicate,
        "skipped_stale": skipped_stale,
        "failed": failed,
        "per_row": per_row,
    }
