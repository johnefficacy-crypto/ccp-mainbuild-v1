"""Tests for exam_topic_score_snapshots writer and reader."""
from __future__ import annotations

import hashlib

from tests.persona_questions._stub import SBStub
from app.exam_intelligence.score_snapshots import (
    compute_exam_topic_scores,
    locked_score_snapshots,
    list_exam_score_snapshots,
    MODEL_VERSION,
)

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_fingerprint(exam_id: str, paper_ids: list[str], question_ids: list[str]) -> str:
    return hashlib.sha256(
        f"{exam_id}:{MODEL_VERSION}:{','.join(sorted(paper_ids))}:{','.join(sorted(question_ids))}".encode()
    ).hexdigest()[:24]


# ── 1. Basic write ────────────────────────────────────────────────────────────


def test_compute_writes_draft_for_covered_topics():
    """1 paper, 1 verified question with primary tag→t1, locked coverage for t1 → written=1."""
    sb = SBStub({
        "pyq_papers": [
            {"id": "p1", "exam_id": "exam-1", "trust_status": "verified"},
        ],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"},
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1", "reviewer_status": "verified", "tag_role": "primary"},
        ],
        "exam_topic_coverage": [
            {"topic_id": "t1", "exam_id": "exam-1", "exam_priority_score": 80, "is_high_yield": True, "reviewer_status": "locked"},
        ],
    })

    result = compute_exam_topic_scores(sb, "exam-1")

    assert result["written"] == 1
    assert result["skipped"] == 0
    assert result["errors"] == 0
    assert result["total_topics"] == 1

    snapshots = sb.db.get("exam_topic_score_snapshots", [])
    assert len(snapshots) == 1
    snap = snapshots[0]
    assert snap["status"] == "draft"
    assert snap["evidence_count"] == 1
    assert "frequency_component" in snap["score_components"]
    assert "coverage_component" in snap["score_components"]
    assert snap["exam_id"] == "exam-1"
    assert snap["topic_id"] == "t1"


# ── 2. Secondary tags excluded ────────────────────────────────────────────────


def test_secondary_tag_not_counted():
    """q1 has primary→t1 and secondary→t2; only t1 gets a snapshot from primary counts.
    t2 has no locked coverage, so it is absent from all_topic_ids → not included.
    """
    sb = SBStub({
        "pyq_papers": [
            {"id": "p1", "exam_id": "exam-1", "trust_status": "verified"},
        ],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"},
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1", "reviewer_status": "verified", "tag_role": "primary"},
            {"question_id": "q1", "topic_id": "t2", "reviewer_status": "verified", "tag_role": "secondary"},
        ],
        "exam_topic_coverage": [
            {"topic_id": "t1", "exam_id": "exam-1", "exam_priority_score": 80, "is_high_yield": True, "reviewer_status": "locked"},
        ],
    })

    result = compute_exam_topic_scores(sb, "exam-1")

    # Only t1 gets a snapshot; t2 has no primary tag and no locked coverage
    assert result["total_topics"] == 1
    snapshots = sb.db.get("exam_topic_score_snapshots", [])
    assert len(snapshots) == 1
    assert snapshots[0]["topic_id"] == "t1"


def test_secondary_tag_covered_topic_gets_zero_freq():
    """t2 has locked coverage but only a secondary tag → freq_component=0, still gets a snapshot."""
    sb = SBStub({
        "pyq_papers": [
            {"id": "p1", "exam_id": "exam-1", "trust_status": "verified"},
        ],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"},
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1", "reviewer_status": "verified", "tag_role": "primary"},
            {"question_id": "q1", "topic_id": "t2", "reviewer_status": "verified", "tag_role": "secondary"},
        ],
        "exam_topic_coverage": [
            {"topic_id": "t1", "exam_id": "exam-1", "exam_priority_score": 80, "is_high_yield": True, "reviewer_status": "locked"},
            {"topic_id": "t2", "exam_id": "exam-1", "exam_priority_score": 60, "is_high_yield": False, "reviewer_status": "locked"},
        ],
    })

    result = compute_exam_topic_scores(sb, "exam-1")

    # Both t1 and t2 appear (t2 via locked coverage)
    assert result["total_topics"] == 2
    snapshots = {s["topic_id"]: s for s in sb.db.get("exam_topic_score_snapshots", [])}
    assert "t2" in snapshots
    # t2 has no primary tag → freq_component = 0
    assert snapshots["t2"]["score_components"]["frequency_component"] == 0.0


# ── 3. Idempotency ────────────────────────────────────────────────────────────


def test_idempotency_skips_same_fingerprint():
    """Second call with same state skips (fingerprint already stored)."""
    fingerprint = _make_fingerprint("exam-1", ["p1"], ["q1"])

    sb = SBStub({
        "pyq_papers": [
            {"id": "p1", "exam_id": "exam-1", "trust_status": "verified"},
        ],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"},
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1", "reviewer_status": "verified", "tag_role": "primary"},
        ],
        "exam_topic_coverage": [
            {"topic_id": "t1", "exam_id": "exam-1", "exam_priority_score": 80, "is_high_yield": True, "reviewer_status": "locked"},
        ],
        # Pre-seed the draft with the same fingerprint to simulate a prior run
        "exam_topic_score_snapshots": [
            {
                "id": "snap-1",
                "exam_id": "exam-1",
                "topic_id": "t1",
                "model_version": MODEL_VERSION,
                "status": "draft",
                "input_summary": {"fingerprint": fingerprint},
            },
        ],
    })

    result = compute_exam_topic_scores(sb, "exam-1")

    assert result["written"] == 0
    assert result["skipped"] == 1
    assert result["errors"] == 0
    # The pre-seeded snapshot should still be the only one
    assert len(sb.db.get("exam_topic_score_snapshots", [])) == 1


# ── 4. Zero evidence ──────────────────────────────────────────────────────────


def test_zero_evidence_returns_empty():
    """No papers → zero summary, nothing written."""
    sb = SBStub({
        "pyq_papers": [],
        "exam_topic_coverage": [],
    })

    result = compute_exam_topic_scores(sb, "exam-1")

    assert result == {"written": 0, "skipped": 0, "errors": 0, "total_topics": 0}
    assert sb.db.get("exam_topic_score_snapshots", []) == []


# ── 5. Empty exam_id ─────────────────────────────────────────────────────────


def test_empty_exam_id():
    """Empty exam_id → immediate zero return, no DB calls."""
    sb = SBStub({})
    result = compute_exam_topic_scores(sb, "")
    assert result == {"written": 0, "skipped": 0, "errors": 0, "total_topics": 0}


# ── 6. locked_score_snapshots filters by status ───────────────────────────────


def test_locked_snapshots_returns_only_locked():
    """Seed draft/reviewed/locked/rejected rows; only the locked one is returned."""
    sb = SBStub({
        "exam_topic_score_snapshots": [
            {"id": "s1", "exam_id": "e1", "topic_id": "t1", "status": "draft",     "exam_priority_score": 90, "is_high_yield": True,  "confidence_score": 0.9, "model_version": MODEL_VERSION, "score_components": {}},
            {"id": "s2", "exam_id": "e1", "topic_id": "t2", "status": "reviewed",  "exam_priority_score": 80, "is_high_yield": True,  "confidence_score": 0.8, "model_version": MODEL_VERSION, "score_components": {}},
            {"id": "s3", "exam_id": "e1", "topic_id": "t3", "status": "locked",    "exam_priority_score": 70, "is_high_yield": False, "confidence_score": 0.7, "model_version": MODEL_VERSION, "score_components": {}},
            {"id": "s4", "exam_id": "e1", "topic_id": "t4", "status": "rejected",  "exam_priority_score": 60, "is_high_yield": False, "confidence_score": 0.6, "model_version": MODEL_VERSION, "score_components": {}},
        ],
    })

    rows = locked_score_snapshots(sb, "e1")

    assert len(rows) == 1
    assert rows[0]["topic_id"] == "t3"
    assert rows[0]["is_high_yield"] is False


# ── 7. locked_score_snapshots sorted by priority ──────────────────────────────


def test_locked_snapshots_sorted_by_priority():
    """Two locked snapshots with priority 80 and 40 → returned [80, 40]."""
    sb = SBStub({
        "exam_topic_score_snapshots": [
            {"id": "s1", "exam_id": "e1", "topic_id": "t1", "status": "locked", "exam_priority_score": 40, "is_high_yield": False, "confidence_score": 0.5, "model_version": MODEL_VERSION, "score_components": {}},
            {"id": "s2", "exam_id": "e1", "topic_id": "t2", "status": "locked", "exam_priority_score": 80, "is_high_yield": True,  "confidence_score": 0.9, "model_version": MODEL_VERSION, "score_components": {}},
        ],
    })

    rows = locked_score_snapshots(sb, "e1")

    assert len(rows) == 2
    assert rows[0]["exam_priority_score"] == 80
    assert rows[1]["exam_priority_score"] == 40


# ── 8. Broken table graceful return ───────────────────────────────────────────


def test_broken_table_returns_gracefully():
    """If supabase raises on first call, written=0 is returned, no exception propagates."""

    class _Broken:
        def table(self, name: str):
            raise RuntimeError(f"table {name!r} not available")

    result = compute_exam_topic_scores(_Broken(), "exam-1")
    assert result == {"written": 0, "skipped": 0, "errors": 0, "total_topics": 0}
