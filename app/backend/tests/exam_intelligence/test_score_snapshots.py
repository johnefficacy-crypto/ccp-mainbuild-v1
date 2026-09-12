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
            {"topic_id": "t1", "exam_id": "exam-1", "exam_priority_score": 80, "is_high_yield": True, "reviewer_status": "locked", "source_basis": "manual"},
            {"topic_id": "t2", "exam_id": "exam-1", "exam_priority_score": 60, "is_high_yield": False, "reviewer_status": "locked", "source_basis": "manual"},
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
            {"topic_id": "t1", "exam_id": "exam-1", "exam_priority_score": 70, "is_high_yield": True, "reviewer_status": "locked", "source_basis": "manual"},
            {"topic_id": "t2", "exam_id": "exam-1", "exam_priority_score": 60, "is_high_yield": False, "reviewer_status": "locked", "source_basis": "manual"},
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


# ── Break-the-edge invariant (OD-3, Option A) ───────────────────────────────
#
# docs/status/J3-Evidence-Coverage-Scoring-Gate-2026-07-02.md Section D /
# docs/status/J3-OD-Resolutions-Locked-2026-07-02.md §5 OD-3: score_snapshots
# MUST exclude source_basis='evidence_derived' coverage rows from its
# coverage_component input. This closes the residual feedback loop where a
# derived-and-locked coverage row would otherwise be folded back into the
# snapshot that produced it (via coverage_derivation.py), causing
# self-reinforcement across recompute cycles. This is a genuine scoring
# invariant — it must hold even when the evidence_derived row is locked.


def test_locked_evidence_derived_coverage_excluded_from_coverage_component():
    """A locked coverage row with source_basis='evidence_derived' must NOT
    contribute to coverage_component — only genuinely human-authored
    coverage does. Verified against the real scoring formula: with the
    evidence_derived row excluded, coverage_component must be 0 (no
    qualifying locked-coverage input for the topic)."""
    sb = SBStub({
        "pyq_papers": [{"id": "p1", "exam_id": "exam-1", "trust_status": "verified"}],
        "pyq_questions": [{"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"}],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1",
             "reviewer_status": "verified", "tag_role": "primary"},
        ],
        "exam_topic_coverage": [
            {
                "topic_id": "t1", "exam_id": "exam-1", "exam_phase_id": None,
                "exam_priority_score": 99, "is_high_yield": True,
                "reviewer_status": "locked", "source_basis": "evidence_derived",
            },
        ],
    })

    result = compute_exam_topic_scores(sb, "exam-1")
    assert result["written"] == 1
    snap = sb.db["exam_topic_score_snapshots"][0]
    # coverage_component would be 0.99 (99/100) if the evidence_derived row
    # leaked in — it must be exactly 0 once excluded.
    assert snap["score_components"]["coverage_component"] == 0.0


def test_human_authored_locked_coverage_still_feeds_coverage_component():
    """Control case: a genuinely human-authored source_basis (e.g. 'manual')
    at the same priority MUST still be included — proves the exclusion is
    specific to 'evidence_derived', not a blanket coverage-read regression."""
    sb = SBStub({
        "pyq_papers": [{"id": "p1", "exam_id": "exam-1", "trust_status": "verified"}],
        "pyq_questions": [{"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"}],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1",
             "reviewer_status": "verified", "tag_role": "primary"},
        ],
        "exam_topic_coverage": [
            {
                "topic_id": "t1", "exam_id": "exam-1", "exam_phase_id": None,
                "exam_priority_score": 99, "is_high_yield": True,
                "reviewer_status": "locked", "source_basis": "manual",
            },
        ],
    })

    result = compute_exam_topic_scores(sb, "exam-1")
    assert result["written"] == 1
    snap = sb.db["exam_topic_score_snapshots"][0]
    assert snap["score_components"]["coverage_component"] == 0.99


def test_no_self_reinforcement_across_derive_lock_recompute_cycle():
    """Simulates the full residual loop the gate calls out: a snapshot is
    computed with no coverage input, an operator locks a derived coverage
    row projected from that snapshot (as coverage_derivation.py would
    produce), and the snapshot is recomputed again. The recompute must be
    STABLE — the newly-locked evidence_derived row must not push the
    snapshot's priority any higher than the pre-derivation snapshot."""
    seed = {
        "pyq_papers": [{"id": "p1", "exam_id": "exam-1", "trust_status": "verified"}],
        "pyq_questions": [{"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"}],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1",
             "reviewer_status": "verified", "tag_role": "primary"},
        ],
        "exam_topic_coverage": [],
    }
    sb = SBStub(seed)

    # Cycle 1: compute with no coverage at all.
    r1 = compute_exam_topic_scores(sb, "exam-1")
    assert r1["written"] == 1
    baseline_priority = sb.db["exam_topic_score_snapshots"][0]["exam_priority_score"]

    # Simulate: an operator locks a derived coverage row projected from that
    # snapshot.
    sb.db["exam_topic_coverage"].append({
        "topic_id": "t1", "exam_id": "exam-1", "exam_phase_id": None,
        "exam_priority_score": baseline_priority, "is_high_yield": True,
        "reviewer_status": "locked", "source_basis": "evidence_derived",
    })

    # Cycle 2: recompute. Because evidence_derived coverage is excluded from
    # BOTH the coverage_component AND the fingerprint's coverage input, the
    # newly-locked evidence_derived row is fully invisible to the recompute:
    # the fingerprint is byte-identical to cycle 1, so the existing draft is
    # skipped rather than replaced — the strongest form of "no reinforcement"
    # (not just same priority, but literally no new write).
    r2 = compute_exam_topic_scores(sb, "exam-1")
    assert r2["written"] == 0
    assert r2["skipped"] == 1
    assert len(sb.db["exam_topic_score_snapshots"]) == 1
    assert sb.db["exam_topic_score_snapshots"][0]["exam_priority_score"] == baseline_priority


# ── 20. Cohort scale model (v2.0) ─────────────────────────────────────────────
#
# SCORE-MAINS-01. The v1.0 model normalised a topic's frequency against every
# verified primary tag on the whole exam. That works for an objective paper
# (100 questions a sitting, one paper examining every subject) and collapses on
# a descriptive Mains paper, where ~1,250 topics share ~5,100 questions so no
# topic exceeds 0.5% and the only varying component moves in the third decimal.
#
# v2.0 measures a topic against its PEER COHORT — the papers that examine its
# own subject. The cohort is derived from the evidence, never from an exam id.
# Where an exam is a single cohort (every paper examines every subject) the
# cohort IS the scope and every output is identical to v1.0: that is the
# neutrality guarantee these tests pin.


def _prelims_corpus():
    """Objective-paper shape: two papers, BOTH examining BOTH subjects.

    This is the structural property that makes an exam single-cohort, and it is
    what UPSC CSE Prelims Paper I looks like — one general-studies paper per
    sitting carrying History, Geography, Polity and the rest together.

    Counts: t-hist-a 5, t-hist-b 2, t-geo-a 10, t-geo-b 3 → 20 primary tags.
    """
    papers = [
        {"id": "p1", "exam_id": "prelims", "trust_status": "verified"},
        {"id": "p2", "exam_id": "prelims", "trust_status": "verified"},
    ]
    topics = [
        {"id": "t-hist-a", "subject_id": "s-history"},
        {"id": "t-hist-b", "subject_id": "s-history"},
        {"id": "t-geo-a", "subject_id": "s-geography"},
        {"id": "t-geo-b", "subject_id": "s-geography"},
    ]
    # (paper, topic, count) — every subject appears in every paper.
    layout = [
        ("p1", "t-hist-a", 3), ("p1", "t-hist-b", 1),
        ("p1", "t-geo-a", 5), ("p1", "t-geo-b", 1),
        ("p2", "t-hist-a", 2), ("p2", "t-hist-b", 1),
        ("p2", "t-geo-a", 5), ("p2", "t-geo-b", 2),
    ]
    questions, tags = [], []
    n = 0
    for pid, tid, count in layout:
        for _ in range(count):
            n += 1
            qid = f"q{n}"
            questions.append({"id": qid, "pyq_paper_id": pid, "reviewer_status": "verified"})
            tags.append({
                "question_id": qid, "topic_id": tid,
                "reviewer_status": "verified", "tag_role": "primary",
            })
    return SBStub({
        "pyq_papers": papers,
        "pyq_questions": questions,
        "pyq_question_topic_tags": tags,
        "topics": topics,
        "exam_topic_coverage": [],
    })


# v1.0 output for _prelims_corpus(), computed by hand from
#   exam_priority_score = (count/20)*50 + 0*40 + min(count/10,1)*10
#   is_high_yield       = (count/20) > 0.15
# and pinned here as literals so the assertion does not restate the formula.
# t-geo-b sits exactly ON the 0.15 boundary (3/20) and must stay False.
_PRELIMS_V1_PIN = {
    "t-geo-a": (35.00, True),    # 10/20 → 25.00 + 10.00
    "t-hist-a": (17.50, True),   #  5/20 → 12.50 +  5.00
    "t-geo-b": (10.50, False),   #  3/20 →  7.50 +  3.00
    "t-hist-b": (7.00, False),   #  2/20 →  5.00 +  2.00
}


def test_prelims_scores_are_unchanged_by_the_cohort_model():
    """D1. An exam whose papers each examine every subject is a single cohort,
    so v2.0 must reproduce v1.0 exactly — score, high-yield flag and the three
    v1.0 score components. This test passes on the v1.0 implementation too;
    that is the point of it."""
    sb = _prelims_corpus()

    result = compute_exam_topic_scores(sb, "prelims")
    assert result["written"] == 4
    assert result["read_error"] is False

    snaps = {s["topic_id"]: s for s in sb.db["exam_topic_score_snapshots"]}
    assert set(snaps) == set(_PRELIMS_V1_PIN)

    for tid, (score, high_yield) in _PRELIMS_V1_PIN.items():
        snap = snaps[tid]
        assert snap["exam_priority_score"] == score, tid
        assert snap["is_high_yield"] is high_yield, tid

    # The v1.0 components are untouched, and the frequency denominator is still
    # the whole 20-tag corpus.
    assert snaps["t-geo-a"]["score_components"]["frequency_component"] == 0.5
    assert snaps["t-hist-a"]["score_components"]["frequency_component"] == 0.25
    assert snaps["t-geo-b"]["score_components"]["frequency_component"] == 0.15
    assert snaps["t-hist-b"]["score_components"]["frequency_component"] == 0.1
    for tid in _PRELIMS_V1_PIN:
        assert snaps[tid]["score_components"]["coverage_component"] == 0.0
        assert snaps[tid]["input_summary"]["corpus_total_primary"] == 20


def test_single_cohort_exam_carries_zero_cohort_weight():
    """The mechanism behind D1: cohort == scope ⇒ weight 0 ⇒ the cohort
    prominence term drops out of the composite entirely."""
    sb = _prelims_corpus()
    compute_exam_topic_scores(sb, "prelims")

    for snap in sb.db["exam_topic_score_snapshots"]:
        comps = snap["score_components"]
        assert comps["cohort_weight"] == 0.0, snap["topic_id"]
        assert snap["input_summary"]["cohort_total_primary"] == 20


def test_topic_with_no_subject_row_falls_back_to_the_whole_scope():
    """A missing ``topics`` row must degrade to v1.0 behaviour for that topic,
    never silently drop it into a wrong cohort."""
    sb = _prelims_corpus()
    sb.db["topics"] = [t for t in sb.db["topics"] if t["id"] != "t-geo-a"]

    compute_exam_topic_scores(sb, "prelims")
    snaps = {s["topic_id"]: s for s in sb.db["exam_topic_score_snapshots"]}

    assert snaps["t-geo-a"]["exam_priority_score"] == _PRELIMS_V1_PIN["t-geo-a"][0]
    assert snaps["t-geo-a"]["score_components"]["cohort_weight"] == 0.0


def _descriptive_corpus(spec: dict[str, dict[str, int]]):
    """Descriptive-paper shape: each subject is examined in its own paper only.

    *spec* is ``{subject_id: {topic_id: primary_count}}``. This is the UPSC
    Mains optional structure — a PSIR question was never going to be asked in
    the History Optional paper, so the two subjects share no paper.
    """
    papers, questions, tags, topics = [], [], [], []
    n = 0
    for sid, counts in spec.items():
        pid = f"paper-{sid}"
        papers.append({"id": pid, "exam_id": "mains", "trust_status": "verified"})
        for tid, count in counts.items():
            topics.append({"id": tid, "subject_id": sid})
            for _ in range(count):
                n += 1
                qid = f"q{n}"
                questions.append({"id": qid, "pyq_paper_id": pid, "reviewer_status": "verified"})
                tags.append({
                    "question_id": qid, "topic_id": tid,
                    "reviewer_status": "verified", "tag_role": "primary",
                })
    return SBStub({
        "pyq_papers": papers,
        "pyq_questions": questions,
        "pyq_question_topic_tags": tags,
        "topics": topics,
        "exam_topic_coverage": [],
    })


def _mains_spec():
    """Four optional subjects, one paper each; 610 primary tags over 160 topics.

    The subject under test (``history-opt``) holds 160 tags over 40 topics —
    the live optional shape, where a topic asked 24 times in nine years sits
    alongside one asked 14 times and one asked once.
    """
    history = {"t-temple": 24, "t-neolithic": 14, "t-onceoff": 1}
    #  37 filler topics summing to 121 → 160 tags over 40 topics, mean 4.0
    for i in range(10):
        history[f"t-h-four-{i}"] = 4
    for i in range(27):
        history[f"t-h-three-{i}"] = 3
    spec = {"history-opt": history}
    #  three peer subjects, 150 tags over 40 topics each
    for sid in ("psir", "sociology", "geography-opt"):
        peer = {}
        for i in range(30):
            peer[f"t-{sid}-four-{i}"] = 4
        for i in range(10):
            peer[f"t-{sid}-three-{i}"] = 3
        spec[sid] = peer
    return spec


def test_mains_topics_separate_by_an_actionable_margin():
    """D3/validation. On a descriptive corpus the 24-, 14- and 1-question topics
    of one subject must order correctly and separate by a margin a human would
    act on — not by the 0.01 points the v1.0 model produced."""
    sb = _descriptive_corpus(_mains_spec())

    result = compute_exam_topic_scores(sb, "mains")
    assert result["read_error"] is False

    snaps = {s["topic_id"]: s for s in sb.db["exam_topic_score_snapshots"]}
    top = snaps["t-temple"]["exam_priority_score"]
    mid = snaps["t-neolithic"]["exam_priority_score"]
    low = snaps["t-onceoff"]["exam_priority_score"]

    assert top > mid > low
    # Stated minimum margins. v1.0 on this same corpus produces
    # 11.97 / 11.15 / 1.08 — 0.82 points between 24 questions and 14.
    assert top - mid >= 8.0, (top, mid)
    assert mid - low >= 15.0, (mid, low)

    # The cohort is the subject's own paper, not the 610-tag exam.
    assert snaps["t-temple"]["input_summary"]["cohort_total_primary"] == 160
    assert snaps["t-temple"]["input_summary"]["corpus_total_primary"] == 610
    # 24 questions against a cohort mean of 4.0.
    assert snaps["t-temple"]["score_components"]["cohort_lift"] == 6.0


def test_mains_high_yield_fires_for_a_prominent_topic_and_not_a_median_one():
    """D3. The flag must be reachable on Mains and must still mean something:
    asked far more than its peers, not true for everything."""
    sb = _descriptive_corpus(_mains_spec())
    compute_exam_topic_scores(sb, "mains")
    snaps = {s["topic_id"]: s for s in sb.db["exam_topic_score_snapshots"]}

    assert snaps["t-temple"]["is_high_yield"] is True      # 24 → 6.0x cohort mean
    assert snaps["t-neolithic"]["is_high_yield"] is True   # 14 → 3.5x cohort mean
    assert snaps["t-h-three-0"]["is_high_yield"] is False  # 3 → 0.75x, the median
    assert snaps["t-h-four-0"]["is_high_yield"] is False   # 4 → exactly the mean
    assert snaps["t-onceoff"]["is_high_yield"] is False

    fired = [s for s in sb.db["exam_topic_score_snapshots"] if s["is_high_yield"]]
    assert len(fired) == 2, [s["topic_id"] for s in fired]
    assert len(fired) / len(sb.db["exam_topic_score_snapshots"]) < 0.05


def test_cohort_inputs_change_the_fingerprint():
    """Moving a topic to another subject changes its cohort and therefore its
    score, so it must invalidate the existing draft."""
    args = ("exam-1", MODEL_VERSION, None, ["p1"], ["q1"], [("q1", "t1")],
            [{"topic_id": "t1", "exam_priority_score": 80, "is_high_yield": True}])

    fp_s1 = _build_fingerprint(*args, q_to_paper={"q1": "p1"}, topic_subject={"t1": "s1"})
    fp_s2 = _build_fingerprint(*args, q_to_paper={"q1": "p1"}, topic_subject={"t1": "s2"})
    fp_p2 = _build_fingerprint(*args, q_to_paper={"q1": "p2"}, topic_subject={"t1": "s1"})

    assert fp_s1 != fp_s2
    assert fp_s1 != fp_p2


def test_topics_read_failure_fails_closed():
    """A partial topic→subject map would move topics into the wrong cohort, so
    a failed read is a compute failure, not a silent fallback."""
    sb = _prelims_corpus()
    original = sb.table

    def _boom(name):
        if name == "topics":
            raise RuntimeError("topics read failed")
        return original(name)

    sb.table = _boom
    result = compute_exam_topic_scores(sb, "prelims")

    assert result["read_error"] is True
    assert result["written"] == 0
    assert sb.db.get("exam_topic_score_snapshots", []) == []
