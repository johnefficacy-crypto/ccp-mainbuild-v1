"""Unit tests for the console work-queue classifier (Wave 4.6H).

Pure-function tests: no DB, no I/O. They lock the canonical status model:
exactly one of blocked|needs_action|ready, with orthogonal flags.

Parity tests (test_wq_parity_*) prove that work_queue.aggregate() and
aggregate_pyq_evidence_batch() agree on verified_pyq_count for the same
underlying data. aggregate() delegates to the batch aggregator internally;
these tests verify that delegation produces identical counts regardless of
the routing path.
"""
from __future__ import annotations

from app.exam_intelligence import work_queue as wq
from app.exam_intelligence.pyq_readiness import aggregate_pyq_evidence_batch
from tests.persona_questions._stub import SBStub


# ── Helpers for parity tests ─────────────────────────────────────────────────

def _minimal_db(exam_id, papers, questions, tags):
    """Build the minimal DB dict that aggregate() needs (no phases/coverage/etc.)
    to exercise the PYQ three-gate path only."""
    return {
        "exams": [{"id": exam_id, "slug": exam_id, "name": "Test Exam",
                   "exam_type": "recruitment", "is_active": True,
                   "exam_family_id": None, "management_mode": "core",
                   "cadence": "annual", "conducting_organization_id": None}],
        "exam_phases": [],
        "exam_topic_coverage": [],
        "syllabus_topic_mentions": [],
        "exam_policy_updates": [],
        "pyq_papers": papers,
        "pyq_questions": questions,
        "pyq_question_topic_tags": tags,
        "pyq_options": [],
        "organizations": [],
    }


def _wq_verified_count(exam_id, papers, questions, tags):
    """Run aggregate() through the SBStub and return verified_pyq_count."""
    db = _minimal_db(exam_id, papers, questions, tags)
    sb = SBStub(db)
    exams = db["exams"]
    agg = wq.aggregate(sb, exams)
    return agg[exam_id]["verified_pyq_count"]


def _batch_verified_count(exam_id, papers, questions, tags):
    """Run aggregate_pyq_evidence_batch() directly and return verified_question_count."""
    result = aggregate_pyq_evidence_batch(
        papers=papers,
        questions=questions,
        topic_tags=tags,
    )
    return result.get(exam_id, {}).get("verified_question_count", 0)


def _agg(**over):
    """A 'ready' aggregate by default; override one signal at a time."""
    base = {
        "phase_count": 1,
        "locked_coverage_count": 1,
        "total_pyq_count": 5,
        "verified_pyq_count": 2,
        "pending_review_count": 0,
        "stale_review_count": 0,
    }
    base.update(over)
    return base


def test_ready_when_locked_coverage_and_no_signals():
    c = wq.classify_exam(_agg())
    assert c["status"] == "ready"
    assert c["flags"] == []
    assert c["blocker_count"] == 0
    assert c["first_blocker_text"] is None


def test_no_locked_coverage_is_blocked_with_missing_coverage():
    c = wq.classify_exam(_agg(locked_coverage_count=0))
    assert c["status"] == "blocked"
    assert "missing_coverage" in c["flags"]
    assert c["blocker_count"] >= 1


def test_missing_phase_setup_is_blocked():
    c = wq.classify_exam(_agg(phase_count=0))
    assert c["status"] == "blocked"
    assert c["blocker_count"] == 1
    assert "Setup" in c["first_blocker_text"]


def test_two_hard_gates_count_two_and_setup_first():
    c = wq.classify_exam(_agg(phase_count=0, locked_coverage_count=0))
    assert c["status"] == "blocked"
    assert c["blocker_count"] == 2
    assert c["first_blocker_text"].startswith("Setup")


def test_locked_but_no_verified_pyq_is_needs_action_not_blocked():
    c = wq.classify_exam(_agg(verified_pyq_count=0))
    assert c["status"] == "needs_action"
    assert "missing_pyq" in c["flags"]
    assert c["blocker_count"] == 0  # missing_pyq is advisory, never a hard blocker


def test_pending_review_is_needs_action():
    c = wq.classify_exam(_agg(pending_review_count=3))
    assert c["status"] == "needs_action"
    assert "pending_review" in c["flags"]
    assert "stale_review_queue" not in c["flags"]


def test_stale_review_sets_both_flags():
    c = wq.classify_exam(_agg(pending_review_count=2, stale_review_count=1))
    assert c["status"] == "needs_action"
    assert "pending_review" in c["flags"]
    assert "stale_review_queue" in c["flags"]


def test_reviewed_but_not_locked_is_blocked_missing_coverage():
    # 'reviewed' coverage does NOT count as planner-ready → locked count 0.
    c = wq.classify_exam(_agg(locked_coverage_count=0, verified_pyq_count=2))
    assert c["status"] == "blocked"
    assert "missing_coverage" in c["flags"]


def test_no_thin_mock_bank_flag_exists():
    # thin_mock_bank was removed in the 4.6H correction pass (not equivalent to
    # diagnostics mock readiness); it must not reappear from the classifier.
    for over in [{}, {"verified_pyq_count": 0}, {"pending_review_count": 1}]:
        assert "thin_mock_bank" not in wq.classify_exam(_agg(**over))["flags"]


def test_status_always_exactly_one_primary():
    primaries = {"blocked", "needs_action", "ready"}
    for over in [
        {}, {"phase_count": 0}, {"locked_coverage_count": 0}, {"verified_pyq_count": 0},
        {"pending_review_count": 5},
        {"phase_count": 0, "locked_coverage_count": 0, "verified_pyq_count": 0},
    ]:
        c = wq.classify_exam(_agg(**over))
        assert c["status"] in primaries


# ── Parity tests: aggregate() verified_pyq_count == aggregate_pyq_evidence_batch() verified_question_count ──

# These tests prove that the delegation path inside aggregate() (which calls
# aggregate_pyq_evidence_batch then maps verified_question_count →
# verified_pyq_count) produces counts identical to calling the batch
# aggregator directly with the same raw rows.  Any drift here would mean a
# bug in the mapping layer, not in the three-gate logic itself.

_EID = "exam-parity"


def test_wq_parity_no_cycle():
    """All three gates pass for every question — both paths return the same count."""
    papers = [
        {"id": "pp1", "exam_id": _EID, "exam_cycle_id": "cy-26", "trust_status": "verified"},
        {"id": "pp2", "exam_id": _EID, "exam_cycle_id": "cy-25", "trust_status": "verified"},
    ]
    questions = [
        {"id": "q1", "pyq_paper_id": "pp1", "reviewer_status": "verified", "created_at": "2026-01-01"},
        {"id": "q2", "pyq_paper_id": "pp1", "reviewer_status": "verified", "created_at": "2026-01-01"},
        {"id": "q3", "pyq_paper_id": "pp2", "reviewer_status": "verified", "created_at": "2025-01-01"},
    ]
    tags = [
        {"id": "t1", "question_id": "q1", "reviewer_status": "verified", "created_at": "2026-01-01"},
        {"id": "t2", "question_id": "q2", "reviewer_status": "verified", "created_at": "2026-01-01"},
        {"id": "t3", "question_id": "q3", "reviewer_status": "verified", "created_at": "2025-01-01"},
    ]

    via_aggregate = _wq_verified_count(_EID, papers, questions, tags)
    via_batch = _batch_verified_count(_EID, papers, questions, tags)

    assert via_aggregate == via_batch == 3


def test_wq_parity_no_cycle_gate3_partial():
    """Gate 3 fails for one question — both paths agree on the reduced count."""
    papers = [
        {"id": "pp1", "exam_id": _EID, "exam_cycle_id": "cy-26", "trust_status": "verified"},
    ]
    questions = [
        {"id": "q1", "pyq_paper_id": "pp1", "reviewer_status": "verified", "created_at": "2026-01-01"},
        {"id": "q2", "pyq_paper_id": "pp1", "reviewer_status": "verified", "created_at": "2026-01-01"},
    ]
    # q1 has a verified tag (clears gate 3); q2 has no tag (gate 3 fails).
    tags = [
        {"id": "t1", "question_id": "q1", "reviewer_status": "verified", "created_at": "2026-01-01"},
    ]

    via_aggregate = _wq_verified_count(_EID, papers, questions, tags)
    via_batch = _batch_verified_count(_EID, papers, questions, tags)

    assert via_aggregate == via_batch == 1


def test_wq_parity_mixed_trust():
    """Mix of verified, pending, and rejected papers/questions/tags — counts agree."""
    papers = [
        # Gate 1 passes for pp-ver; fails for pp-pend (pending) and pp-rej (rejected).
        {"id": "pp-ver",  "exam_id": _EID, "exam_cycle_id": "cy-26", "trust_status": "verified"},
        {"id": "pp-pend", "exam_id": _EID, "exam_cycle_id": "cy-26", "trust_status": "pending"},
        {"id": "pp-rej",  "exam_id": _EID, "exam_cycle_id": "cy-25", "trust_status": "rejected"},
    ]
    questions = [
        # On verified paper: one verified question + one pending question.
        {"id": "qv1", "pyq_paper_id": "pp-ver",  "reviewer_status": "verified", "created_at": "2026-01-01"},
        {"id": "qp1", "pyq_paper_id": "pp-ver",  "reviewer_status": "pending",  "created_at": "2026-01-01"},
        # On pending paper: verified question — but gate 1 fails, so it cannot count.
        {"id": "qv2", "pyq_paper_id": "pp-pend", "reviewer_status": "verified", "created_at": "2026-01-01"},
        # On rejected paper: verified question — gate 1 fails.
        {"id": "qv3", "pyq_paper_id": "pp-rej",  "reviewer_status": "verified", "created_at": "2025-01-01"},
    ]
    tags = [
        # qv1 has one verified tag → all three gates pass → counts.
        {"id": "tv1", "question_id": "qv1", "reviewer_status": "verified", "created_at": "2026-01-01"},
        # qp1 has a verified tag, but gate 2 (question status) fails → doesn't count.
        {"id": "tv2", "question_id": "qp1", "reviewer_status": "verified", "created_at": "2026-01-01"},
        # qv2 and qv3 have verified tags, but gate 1 (paper trust) fails → don't count.
        {"id": "tv3", "question_id": "qv2", "reviewer_status": "verified", "created_at": "2026-01-01"},
        {"id": "tv4", "question_id": "qv3", "reviewer_status": "verified", "created_at": "2025-01-01"},
    ]

    via_aggregate = _wq_verified_count(_EID, papers, questions, tags)
    via_batch = _batch_verified_count(_EID, papers, questions, tags)

    # Only qv1 clears all three gates.
    assert via_aggregate == via_batch == 1


def test_wq_parity_zero_when_no_papers():
    """No papers → zero verified questions via both paths."""
    via_aggregate = _wq_verified_count(_EID, [], [], [])
    via_batch = _batch_verified_count(_EID, [], [], [])

    assert via_aggregate == via_batch == 0


def test_wq_parity_zero_when_all_tags_pending():
    """Verified paper + verified question + only pending tag → gate 3 fails on both paths."""
    papers = [{"id": "pp1", "exam_id": _EID, "exam_cycle_id": "cy-26", "trust_status": "verified"}]
    questions = [{"id": "q1", "pyq_paper_id": "pp1", "reviewer_status": "verified", "created_at": "2026-01-01"}]
    tags = [{"id": "t1", "question_id": "q1", "reviewer_status": "pending", "created_at": "2026-01-01"}]

    via_aggregate = _wq_verified_count(_EID, papers, questions, tags)
    via_batch = _batch_verified_count(_EID, papers, questions, tags)

    assert via_aggregate == via_batch == 0


def test_wq_parity_multiple_verified_tags_count_once():
    """Two verified tags on one question count it exactly once on both paths."""
    papers = [{"id": "pp1", "exam_id": _EID, "exam_cycle_id": "cy-26", "trust_status": "verified"}]
    questions = [{"id": "q1", "pyq_paper_id": "pp1", "reviewer_status": "verified", "created_at": "2026-01-01"}]
    tags = [
        {"id": "ta", "question_id": "q1", "reviewer_status": "verified", "created_at": "2026-01-01"},
        {"id": "tb", "question_id": "q1", "reviewer_status": "verified", "created_at": "2026-01-01"},
    ]

    via_aggregate = _wq_verified_count(_EID, papers, questions, tags)
    via_batch = _batch_verified_count(_EID, papers, questions, tags)

    assert via_aggregate == via_batch == 1
