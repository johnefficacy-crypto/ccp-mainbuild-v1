"""Tests for exam_topic_score_snapshots writer and reader."""
from __future__ import annotations

from tests.persona_questions._stub import SBStub
from app.exam_intelligence.score_snapshots import (
    compute_exam_topic_scores,
    locked_score_snapshots,
    list_exam_score_snapshots,
    MODEL_VERSION,
    _build_fingerprint,
)

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
    assert result["read_error"] is False

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


# ── 3. Multiple primary tags per question ─────────────────────────────────────


def test_multiple_primary_tags_excluded_from_frequency():
    """q1 with primary→t1 AND primary→t2 is ambiguous and contributes to neither topic's count.

    Both t1 and t2 still get snapshots from their locked coverage, but their
    frequency_component must be 0 (no unambiguous question contributed).
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
            {"question_id": "q1", "topic_id": "t2", "reviewer_status": "verified", "tag_role": "primary"},
        ],
        "exam_topic_coverage": [
            {"topic_id": "t1", "exam_id": "exam-1", "exam_priority_score": 70, "is_high_yield": True, "reviewer_status": "locked"},
            {"topic_id": "t2", "exam_id": "exam-1", "exam_priority_score": 60, "is_high_yield": False, "reviewer_status": "locked"},
        ],
    })

    result = compute_exam_topic_scores(sb, "exam-1")

    # q1 is ambiguous → excluded from frequency counts
    # Both topics still get snapshots from locked coverage
    assert result["total_topics"] == 2
    snapshots = {s["topic_id"]: s for s in sb.db.get("exam_topic_score_snapshots", [])}
    assert snapshots["t1"]["score_components"]["frequency_component"] == 0.0
    assert snapshots["t2"]["score_components"]["frequency_component"] == 0.0
    assert result["read_error"] is False


# ── 4. Idempotency ────────────────────────────────────────────────────────────


def test_idempotency_skips_same_fingerprint():
    """Running compute twice with unchanged data skips on the second run."""
    seed = {
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
    }
    sb = SBStub(seed)

    result1 = compute_exam_topic_scores(sb, "exam-1")
    assert result1["written"] == 1
    assert result1["skipped"] == 0

    result2 = compute_exam_topic_scores(sb, "exam-1")
    assert result2["written"] == 0
    assert result2["skipped"] == 1
    assert result2["errors"] == 0
    assert len(sb.db.get("exam_topic_score_snapshots", [])) == 1


# ── 5. Zero evidence ──────────────────────────────────────────────────────────


def test_zero_evidence_returns_empty():
    """No papers → zero summary, nothing written, read_error=False."""
    sb = SBStub({
        "pyq_papers": [],
        "exam_topic_coverage": [],
    })

    result = compute_exam_topic_scores(sb, "exam-1")

    assert result == {"written": 0, "skipped": 0, "errors": 0, "total_topics": 0, "read_error": False}
    assert sb.db.get("exam_topic_score_snapshots", []) == []


# ── 6. Empty exam_id ─────────────────────────────────────────────────────────


def test_empty_exam_id():
    """Empty exam_id → immediate zero return, no DB calls."""
    sb = SBStub({})
    result = compute_exam_topic_scores(sb, "")
    assert result == {"written": 0, "skipped": 0, "errors": 0, "total_topics": 0, "read_error": False}


# ── 7. Broken table → read_error ─────────────────────────────────────────────


def test_broken_table_returns_read_error():
    """If Supabase raises on first call, read_error=True is returned, no exception propagates."""

    class _Broken:
        def table(self, name: str):
            raise RuntimeError(f"table {name!r} not available")

    result = compute_exam_topic_scores(_Broken(), "exam-1")
    assert result["read_error"] is True
    assert result["written"] == 0
    assert result["total_topics"] == 0


# ── 8. locked_score_snapshots filters by status ───────────────────────────────


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


# ── 9. locked_score_snapshots sorted by priority ──────────────────────────────


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


# ── 10. locked_score_snapshots deduplicates to latest per topic ───────────────


def test_locked_snapshots_deduplicates_to_latest_per_topic():
    """Two locked rows for the same topic → only the latest (by computed_at) is returned."""
    sb = SBStub({
        "exam_topic_score_snapshots": [
            {"id": "s1", "exam_id": "e1", "topic_id": "t1", "status": "locked",
             "exam_priority_score": 60, "is_high_yield": False, "confidence_score": 0.6,
             "model_version": "v0.9", "score_components": {},
             "computed_at": "2026-04-01T00:00:00+00:00"},
            {"id": "s2", "exam_id": "e1", "topic_id": "t1", "status": "locked",
             "exam_priority_score": 80, "is_high_yield": True, "confidence_score": 0.8,
             "model_version": MODEL_VERSION, "score_components": {},
             "computed_at": "2026-06-01T00:00:00+00:00"},
        ],
    })

    rows = locked_score_snapshots(sb, "e1")

    assert len(rows) == 1, "must deduplicate to one row per topic"
    assert rows[0]["exam_priority_score"] == 80, "latest (higher priority) row must win"


# ── 11. locked_score_snapshots isolates by phase ─────────────────────────────


def test_locked_snapshots_excludes_phase_rows_when_no_phase():
    """Without exam_phase_id, only exam-wide (null phase) rows are returned."""
    sb = SBStub({
        "exam_topic_score_snapshots": [
            {"id": "s1", "exam_id": "e1", "topic_id": "t1", "status": "locked",
             "exam_phase_id": None, "exam_priority_score": 80, "is_high_yield": True,
             "confidence_score": 0.8, "model_version": MODEL_VERSION, "score_components": {},
             "computed_at": "2026-06-01T00:00:00+00:00"},
            {"id": "s2", "exam_id": "e1", "topic_id": "t2", "status": "locked",
             "exam_phase_id": "phase-1", "exam_priority_score": 90, "is_high_yield": True,
             "confidence_score": 0.9, "model_version": MODEL_VERSION, "score_components": {},
             "computed_at": "2026-06-01T00:00:00+00:00"},
        ],
    })

    rows = locked_score_snapshots(sb, "e1")

    assert len(rows) == 1, "phase-1 row must be excluded when no exam_phase_id is given"
    assert rows[0]["topic_id"] == "t1"


# ── 12. Phase validation: cross-exam phase returns read_error ─────────────────


def test_cross_exam_phase_returns_invalid_scope():
    """exam_phase_id belonging to a different exam → invalid_scope=True (not read_error)."""
    sb = SBStub({
        "exam_phases": [
            {"id": "phase-x", "exam_id": "exam-2"},  # wrong exam
        ],
        "pyq_papers": [
            {"id": "p1", "exam_id": "exam-1", "trust_status": "verified"},
        ],
    })

    result = compute_exam_topic_scores(sb, "exam-1", exam_phase_id="phase-x")

    assert result.get("invalid_scope") is True
    assert result.get("read_error") is not True
    assert result["written"] == 0


# ── 13. Phase scope: papers filtered by exam_phase_id ────────────────────────


def test_phase_scopes_paper_corpus():
    """With exam_phase_id, only papers in that phase are included; others are excluded."""
    sb = SBStub({
        "exam_phases": [
            {"id": "phase-1", "exam_id": "exam-1"},
        ],
        "pyq_papers": [
            {"id": "p1", "exam_id": "exam-1", "exam_phase_id": "phase-1", "trust_status": "verified"},
            {"id": "p2", "exam_id": "exam-1", "exam_phase_id": None, "trust_status": "verified"},
        ],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"},
            {"id": "q2", "pyq_paper_id": "p2", "reviewer_status": "verified"},
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1", "reviewer_status": "verified", "tag_role": "primary"},
            {"question_id": "q2", "topic_id": "t2", "reviewer_status": "verified", "tag_role": "primary"},
        ],
        "exam_topic_coverage": [
            {"topic_id": "t1", "exam_id": "exam-1", "exam_phase_id": "phase-1",
             "exam_priority_score": 70, "is_high_yield": False, "reviewer_status": "locked"},
        ],
    })

    result = compute_exam_topic_scores(sb, "exam-1", exam_phase_id="phase-1")

    assert result["read_error"] is False
    snapshots = sb.db.get("exam_topic_score_snapshots", [])
    assert len(snapshots) == 1, "only t1 (from phase-1 paper p1) should be written"
    assert snapshots[0]["topic_id"] == "t1"
    assert snapshots[0]["exam_phase_id"] == "phase-1"


# ── 14. _build_fingerprint: coverage changes invalidate draft ─────────────────


def test_fingerprint_changes_when_coverage_changes():
    """Changing locked coverage for a topic must produce a new fingerprint."""
    paper_ids = ["p1"]
    question_ids = ["q1"]
    primary_tag_tuples = [("q1", "t1")]
    locked_cov_v1 = [{"topic_id": "t1", "exam_priority_score": 70, "is_high_yield": False}]
    locked_cov_v2 = [{"topic_id": "t1", "exam_priority_score": 90, "is_high_yield": True}]

    fp1 = _build_fingerprint("exam-1", MODEL_VERSION, None, paper_ids, question_ids, primary_tag_tuples, locked_cov_v1)
    fp2 = _build_fingerprint("exam-1", MODEL_VERSION, None, paper_ids, question_ids, primary_tag_tuples, locked_cov_v2)

    assert fp1 != fp2


def test_fingerprint_changes_when_tag_topic_reassigned():
    """Reassigning a primary tag from t1 to t3 must produce a new fingerprint."""
    paper_ids = ["p1"]
    question_ids = ["q1"]
    locked_cov = [{"topic_id": "t1", "exam_priority_score": 80, "is_high_yield": True}]

    fp_before = _build_fingerprint("exam-1", MODEL_VERSION, None, paper_ids, question_ids, [("q1", "t1")], locked_cov)
    fp_after = _build_fingerprint("exam-1", MODEL_VERSION, None, paper_ids, question_ids, [("q1", "t3")], locked_cov)

    assert fp_before != fp_after


def test_fingerprint_changes_when_phase_changes():
    """Changing exam_phase_id must produce a new fingerprint."""
    paper_ids = ["p1"]
    question_ids = ["q1"]
    primary_tag_tuples = [("q1", "t1")]
    locked_cov = [{"topic_id": "t1", "exam_priority_score": 80, "is_high_yield": True}]

    fp_none = _build_fingerprint("exam-1", MODEL_VERSION, None, paper_ids, question_ids, primary_tag_tuples, locked_cov)
    fp_phase = _build_fingerprint("exam-1", MODEL_VERSION, "phase-1", paper_ids, question_ids, primary_tag_tuples, locked_cov)

    assert fp_none != fp_phase


# ── 15. Exam-wide coverage excludes phase-specific rows ───────────────────────


def test_exam_wide_coverage_excludes_phase_rows():
    """Exam-wide compute (no exam_phase_id) filters coverage to exam_phase_id IS NULL.

    A locked coverage row scoped to a specific phase must not appear in the
    exam-wide all_topic_ids set when no PYQ evidence exists for that topic,
    preventing phase-scoped coverage from polluting exam-wide scores.
    """
    sb = SBStub({
        "pyq_papers": [
            {"id": "p1", "exam_id": "exam-1", "trust_status": "verified"},
        ],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"},
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1",
             "reviewer_status": "verified", "tag_role": "primary"},
        ],
        "exam_topic_coverage": [
            # exam-wide coverage for t1 — should be included
            {"topic_id": "t1", "exam_id": "exam-1", "exam_phase_id": None,
             "exam_priority_score": 80, "is_high_yield": True, "reviewer_status": "locked"},
            # phase-specific coverage for t2 — must be EXCLUDED from exam-wide read
            {"topic_id": "t2", "exam_id": "exam-1", "exam_phase_id": "phase-1",
             "exam_priority_score": 90, "is_high_yield": True, "reviewer_status": "locked"},
        ],
    })

    result = compute_exam_topic_scores(sb, "exam-1")  # exam-wide (no exam_phase_id)

    assert result["read_error"] is False
    topic_ids = {s["topic_id"] for s in sb.db.get("exam_topic_score_snapshots", [])}
    assert "t2" not in topic_ids, "phase-specific coverage row must not appear in exam-wide results"
    assert "t1" in topic_ids, "exam-wide coverage row must be included"


# ── 16. Draft read failure: fail-closed ───────────────────────────────────────


def test_draft_read_failure_returns_read_error():
    """If reading existing drafts fails, compute returns read_error=True (fail-closed).

    Without this guard a DB error on the draft SELECT is indistinguishable from
    'no drafts', so every recompute would insert a duplicate instead of skipping.
    """

    class _DraftReadFailStub(SBStub):
        def __init__(self, db):
            super().__init__(db)
            self._snapshots_calls = 0

        def table(self, name):
            q = super().table(name)
            if name != "exam_topic_score_snapshots":
                return q
            self._snapshots_calls += 1
            if self._snapshots_calls == 1:
                def _fail():
                    raise RuntimeError("DB read error on snapshots table")
                q.execute = _fail
            return q

    sb = _DraftReadFailStub({
        "pyq_papers": [{"id": "p1", "exam_id": "exam-1", "trust_status": "verified"}],
        "pyq_questions": [{"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"}],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1",
             "reviewer_status": "verified", "tag_role": "primary"},
        ],
        "exam_topic_coverage": [
            {"topic_id": "t1", "exam_id": "exam-1", "exam_phase_id": None,
             "exam_priority_score": 80, "is_high_yield": True, "reviewer_status": "locked"},
        ],
    })

    result = compute_exam_topic_scores(sb, "exam-1")

    assert result["read_error"] is True
    assert result["written"] == 0
    # No INSERT must run when the draft SELECT fails — duplicates are prevented.
    assert sb.db.get("exam_topic_score_snapshots", []) == []


# ── 17. Multi-draft idempotency: all fingerprints per topic checked ───────────


def test_multi_draft_per_topic_idempotency():
    """With multiple draft rows for a topic, skip if ANY has the current fingerprint.

    Previously only one draft per topic was checked (arbitrary dict selection),
    so a stale draft could cause the current fingerprint to be missed, triggering
    a duplicate insert. existing_fps collects ALL fingerprints per topic.
    """
    seed = {
        "pyq_papers": [{"id": "p1", "exam_id": "exam-1", "trust_status": "verified"}],
        "pyq_questions": [{"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"}],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1",
             "reviewer_status": "verified", "tag_role": "primary"},
        ],
        "exam_topic_coverage": [
            {"topic_id": "t1", "exam_id": "exam-1", "exam_phase_id": None,
             "exam_priority_score": 80, "is_high_yield": True, "reviewer_status": "locked"},
        ],
    }
    sb = SBStub(seed)

    # First compute: writes 1 draft with fingerprint F_current.
    result1 = compute_exam_topic_scores(sb, "exam-1")
    assert result1["written"] == 1
    current_fp = sb.db["exam_topic_score_snapshots"][0]["input_summary"]["fingerprint"]

    # Manually inject a STALE draft for the same topic (simulates an orphaned row
    # from a previous model version or data state).
    sb.db["exam_topic_score_snapshots"].append({
        "id": "stale-draft",
        "exam_id": "exam-1",
        "topic_id": "t1",
        "status": "draft",
        "model_version": MODEL_VERSION,
        "input_summary": {"fingerprint": "stale-fp-000"},
        "exam_phase_id": None,
    })

    # Second compute: existing_fps["t1"] == {current_fp, "stale-fp-000"}.
    # Current fingerprint matches → must skip, NOT insert a third row.
    result2 = compute_exam_topic_scores(sb, "exam-1")
    assert result2["written"] == 0, "should skip when current fingerprint is already present"
    assert result2["skipped"] == 1
    assert len(sb.db["exam_topic_score_snapshots"]) == 2  # stale row still there, no new insert
