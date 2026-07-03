"""Comprehensive tests for the pyq_readiness shared aggregation module (D10).

Tests cover:
- Scope invariance (selected_cycle_id never changes counts)
- Trust gate logic (three-gate rule)
- State derivation
- Batch variant correctness
- Parity between single-exam and batch results
"""
from __future__ import annotations

import pytest

from app.exam_intelligence.pyq_readiness import (
    aggregate_pyq_evidence,
    aggregate_pyq_evidence_batch,
)

# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

EXAM_ID = "exam-1"
EXAM_ID_B = "exam-2"

CYCLE_2026 = "cycle-2026"
CYCLE_2025 = "cycle-2025"

# Papers
PAPER_VER = {
    "id": "paper-v",
    "exam_id": EXAM_ID,
    "exam_cycle_id": CYCLE_2026,
    "trust_status": "verified",
}
PAPER_VER_2025 = {
    "id": "paper-v-2025",
    "exam_id": EXAM_ID,
    "exam_cycle_id": CYCLE_2025,
    "trust_status": "verified",
}
PAPER_PEND = {
    "id": "paper-p",
    "exam_id": EXAM_ID,
    "exam_cycle_id": CYCLE_2025,
    "trust_status": "pending",
}
PAPER_REJ = {
    "id": "paper-r",
    "exam_id": EXAM_ID,
    "exam_cycle_id": CYCLE_2026,
    "trust_status": "rejected",
}
PAPER_UNSCO = {
    "id": "paper-u",
    "exam_id": EXAM_ID,
    "exam_cycle_id": None,
    "trust_status": "verified",
}
PAPER_EXAM_B = {
    "id": "paper-b",
    "exam_id": EXAM_ID_B,
    "exam_cycle_id": CYCLE_2026,
    "trust_status": "verified",
}

# Questions
Q_VER = {"id": "q-1", "pyq_paper_id": "paper-v", "reviewer_status": "verified"}
Q_VER_2 = {"id": "q-2", "pyq_paper_id": "paper-v", "reviewer_status": "verified"}
Q_VER_2025 = {
    "id": "q-3",
    "pyq_paper_id": "paper-v-2025",
    "reviewer_status": "verified",
}
Q_PEND = {"id": "q-p", "pyq_paper_id": "paper-v", "reviewer_status": "pending"}
Q_REJ = {"id": "q-r", "pyq_paper_id": "paper-v", "reviewer_status": "rejected"}
Q_NEEDS_CORR = {
    "id": "q-nc",
    "pyq_paper_id": "paper-v",
    "reviewer_status": "needs_correction",
}
Q_ON_PEND_PAPER = {
    "id": "q-pp",
    "pyq_paper_id": "paper-p",
    "reviewer_status": "verified",
}
Q_ON_REJ_PAPER = {
    "id": "q-rp",
    "pyq_paper_id": "paper-r",
    "reviewer_status": "verified",
}
Q_EXAM_B = {"id": "q-b", "pyq_paper_id": "paper-b", "reviewer_status": "verified"}

# Topic tags
TAG_VER = {"id": "tag-1", "question_id": "q-1", "reviewer_status": "verified"}
TAG_VER_2 = {"id": "tag-2", "question_id": "q-2", "reviewer_status": "verified"}
TAG_VER_2025 = {
    "id": "tag-3",
    "question_id": "q-3",
    "reviewer_status": "verified",
}
TAG_PEND = {"id": "tag-p", "question_id": "q-1", "reviewer_status": "pending"}
TAG_REJ = {"id": "tag-r", "question_id": "q-1", "reviewer_status": "rejected"}
TAG_NEEDS_CORR = {
    "id": "tag-nc",
    "question_id": "q-1",
    "reviewer_status": "needs_correction",
}
TAG_EXAM_B = {"id": "tag-b", "question_id": "q-b", "reviewer_status": "verified"}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _call(papers, questions, tags, cycle=None):
    return aggregate_pyq_evidence(
        papers=papers,
        questions=questions,
        topic_tags=tags,
        selected_cycle_id=cycle,
    )


# ===========================================================================
# SCOPE CASES
# ===========================================================================


def test_scope_selected_cycle_paper_and_verified_2025_paper_included():
    """Selecting 2026 cycle does not exclude a verified 2025 paper.

    papers_total must reflect both papers regardless of selected cycle.
    """
    papers = [PAPER_VER, PAPER_VER_2025]
    questions = [Q_VER, Q_VER_2025]
    tags = [TAG_VER, TAG_VER_2025]

    result = _call(papers, questions, tags, cycle=CYCLE_2026)

    assert result["papers_total"] == 2
    assert result["selected_cycle_papers"] == 1   # only PAPER_VER
    assert result["other_cycle_papers"] == 1       # PAPER_VER_2025
    assert result["unscoped_papers"] == 0
    # Both questions are verified — must count both.
    assert result["verified_question_count"] == 2


def test_scope_unscoped_paper_included_when_cycle_selected():
    """A paper with exam_cycle_id=None is always included (goes to unscoped_papers)."""
    papers = [PAPER_UNSCO]
    questions = [{"id": "q-u", "pyq_paper_id": "paper-u", "reviewer_status": "verified"}]
    tags = [{"id": "t-u", "question_id": "q-u", "reviewer_status": "verified"}]

    result = _call(papers, questions, tags, cycle=CYCLE_2026)

    assert result["papers_total"] == 1
    assert result["unscoped_papers"] == 1
    assert result["selected_cycle_papers"] == 0
    assert result["other_cycle_papers"] == 0
    assert result["verified_question_count"] == 1


def test_scope_other_cycle_paper_counted_in_other_cycle_papers():
    """A paper from a different cycle increments other_cycle_papers."""
    papers = [PAPER_VER_2025]  # CYCLE_2025 paper, selecting CYCLE_2026
    questions = [Q_VER_2025]
    tags = [TAG_VER_2025]

    result = _call(papers, questions, tags, cycle=CYCLE_2026)

    assert result["papers_total"] == 1
    assert result["other_cycle_papers"] == 1
    assert result["selected_cycle_papers"] == 0
    assert result["verified_question_count"] == 1


def test_scope_cross_exam_paper_excluded_by_caller_passing_only_same_exam():
    """Only same-exam papers should be passed; callers filter by exam.

    Passing only EXAM_ID papers gives a result containing only those questions.
    """
    papers = [PAPER_VER]
    questions = [Q_VER]
    tags = [TAG_VER]

    result = _call(papers, questions, tags)

    assert result["papers_total"] == 1
    assert result["verified_question_count"] == 1


def test_scope_papers_total_unchanged_when_cycle_selected():
    """Selecting a cycle must not change papers_total."""
    papers = [PAPER_VER, PAPER_VER_2025, PAPER_UNSCO]
    questions = [Q_VER]
    tags = [TAG_VER]

    result_no_cycle = _call(papers, questions, tags, cycle=None)
    result_with_cycle = _call(papers, questions, tags, cycle=CYCLE_2026)

    assert result_no_cycle["papers_total"] == result_with_cycle["papers_total"] == 3


def test_scope_papers_total_unchanged_when_cycle_cleared():
    """Clearing selected_cycle_id (None) must not change papers_total."""
    papers = [PAPER_VER, PAPER_VER_2025]
    questions = [Q_VER]
    tags = [TAG_VER]

    result_with_cycle = _call(papers, questions, tags, cycle=CYCLE_2026)
    result_cleared = _call(papers, questions, tags, cycle=None)

    assert result_with_cycle["papers_total"] == result_cleared["papers_total"] == 2


def test_scope_verified_question_count_unchanged_when_cycle_selected():
    """Setting selected_cycle_id must never alter verified_question_count."""
    papers = [PAPER_VER, PAPER_VER_2025]
    questions = [Q_VER, Q_VER_2025]
    tags = [TAG_VER, TAG_VER_2025]

    result_none = _call(papers, questions, tags, cycle=None)
    result_2026 = _call(papers, questions, tags, cycle=CYCLE_2026)
    result_2025 = _call(papers, questions, tags, cycle=CYCLE_2025)

    assert (
        result_none["verified_question_count"]
        == result_2026["verified_question_count"]
        == result_2025["verified_question_count"]
        == 2
    )


def test_scope_verified_question_count_unchanged_when_cycle_cleared():
    """Clearing selected_cycle_id must not reduce verified_question_count."""
    papers = [PAPER_VER]
    questions = [Q_VER]
    tags = [TAG_VER]

    result_cycle = _call(papers, questions, tags, cycle=CYCLE_2026)
    result_no_cycle = _call(papers, questions, tags, cycle=None)

    assert (
        result_cycle["verified_question_count"]
        == result_no_cycle["verified_question_count"]
        == 1
    )


def test_scope_provenance_counters_sum_to_papers_total_single_cycle():
    """selected_cycle_papers + other_cycle_papers + unscoped_papers == papers_total."""
    papers = [PAPER_VER, PAPER_VER_2025, PAPER_UNSCO, PAPER_PEND]
    questions = []
    tags = []

    result = _call(papers, questions, tags, cycle=CYCLE_2026)

    total = result["papers_total"]
    assert (
        result["selected_cycle_papers"]
        + result["other_cycle_papers"]
        + result["unscoped_papers"]
        == total
    )
    assert result["selected_cycle_papers"] == 1   # PAPER_VER is cycle-2026
    assert result["other_cycle_papers"] == 2       # PAPER_VER_2025, PAPER_PEND
    assert result["unscoped_papers"] == 1          # PAPER_UNSCO


def test_scope_provenance_counters_sum_to_papers_total_no_cycle():
    """Invariant holds when selected_cycle_id=None (all papers become other_cycle or unscoped)."""
    papers = [PAPER_VER, PAPER_VER_2025, PAPER_UNSCO]
    questions = []
    tags = []

    result = _call(papers, questions, tags, cycle=None)

    total = result["papers_total"]
    assert (
        result["selected_cycle_papers"]
        + result["other_cycle_papers"]
        + result["unscoped_papers"]
        == total
    )
    # With selected_cycle_id=None, no paper matches it — all non-None go to other_cycle.
    assert result["selected_cycle_papers"] == 0
    assert result["other_cycle_papers"] == 2
    assert result["unscoped_papers"] == 1


# ===========================================================================
# TRUST CASES (three-gate rule)
# ===========================================================================


def test_trust_all_three_gates_pass_counts_once():
    """Verified paper + verified question + verified tag → verified_question_count=1."""
    result = _call([PAPER_VER], [Q_VER], [TAG_VER])

    assert result["verified_question_count"] == 1
    assert result["state"] == "ready"


def test_trust_gate1_fails_pending_paper():
    """pending paper gate 1 fails → verified_question_count=0."""
    result = _call([PAPER_PEND], [Q_ON_PEND_PAPER], [
        {"id": "t", "question_id": "q-pp", "reviewer_status": "verified"}
    ])

    assert result["verified_question_count"] == 0
    assert result["papers_total"] == 1


def test_trust_gate1_fails_rejected_paper():
    """rejected paper gate 1 fails → verified_question_count=0."""
    result = _call([PAPER_REJ], [Q_ON_REJ_PAPER], [
        {"id": "t", "question_id": "q-rp", "reviewer_status": "verified"}
    ])

    assert result["verified_question_count"] == 0


def test_trust_gate2_fails_pending_question():
    """verified paper + pending question → gate 2 fails → verified_question_count=0."""
    result = _call([PAPER_VER], [Q_PEND], [TAG_VER])

    assert result["verified_question_count"] == 0
    assert result["questions_eligible_before_tag_gate"] == 0


def test_trust_gate2_fails_rejected_question():
    """verified paper + rejected question → gate 2 fails → verified_question_count=0."""
    result = _call([PAPER_VER], [Q_REJ], [TAG_VER])

    assert result["verified_question_count"] == 0


def test_trust_gate3_fails_no_tag():
    """verified paper + verified question + no tag → gate 3 fails."""
    result = _call([PAPER_VER], [Q_VER], [])

    assert result["questions_eligible_before_tag_gate"] == 1
    assert result["verified_question_count"] == 0


def test_trust_gate3_fails_pending_tag():
    """verified paper + verified question + pending tag → gate 3 fails."""
    result = _call([PAPER_VER], [Q_VER], [TAG_PEND])

    assert result["questions_eligible_before_tag_gate"] == 1
    assert result["verified_question_count"] == 0
    assert result["pending_tag_count"] == 1


def test_trust_gate3_fails_rejected_tag():
    """verified paper + verified question + rejected tag → gate 3 fails."""
    result = _call([PAPER_VER], [Q_VER], [TAG_REJ])

    assert result["questions_eligible_before_tag_gate"] == 1
    assert result["verified_question_count"] == 0


def test_trust_multiple_verified_tags_count_question_once():
    """Two verified tags on the same question still yield verified_question_count=1."""
    tag_a = {"id": "tag-a", "question_id": "q-1", "reviewer_status": "verified"}
    tag_b = {"id": "tag-b", "question_id": "q-1", "reviewer_status": "verified"}

    result = _call([PAPER_VER], [Q_VER], [tag_a, tag_b])

    assert result["verified_question_count"] == 1


def test_trust_verified_paper_no_questions_gives_review_pending():
    """A verified paper with no questions satisfies gate 1 but not gate 3 → review_pending."""
    result = _call([PAPER_VER], [], [])

    assert result["verified_question_count"] == 0
    assert result["state"] == "review_pending"
    assert result["papers_total"] == 1


def test_trust_locked_question_status_does_not_count():
    """Non-schema 'locked' question status is not 'verified' → gate 2 fails."""
    q_locked = {"id": "q-lock", "pyq_paper_id": "paper-v", "reviewer_status": "locked"}
    tag = {"id": "t-lock", "question_id": "q-lock", "reviewer_status": "verified"}

    result = _call([PAPER_VER], [q_locked], [tag])

    assert result["verified_question_count"] == 0
    # 'locked' is not in pending states either, so pending_question_count should be 0.
    assert result["pending_question_count"] == 0


def test_trust_needs_correction_question_does_not_count_as_verified():
    """needs_correction question status does not pass gate 2."""
    result = _call([PAPER_VER], [Q_NEEDS_CORR], [
        {"id": "t", "question_id": "q-nc", "reviewer_status": "verified"}
    ])

    assert result["verified_question_count"] == 0
    # needs_correction is in _QUESTION_PENDING_STATES → increments pending count.
    assert result["pending_question_count"] == 1


def test_trust_needs_correction_tag_does_not_satisfy_gate3():
    """needs_correction tag does not satisfy gate 3."""
    result = _call([PAPER_VER], [Q_VER], [TAG_NEEDS_CORR])

    assert result["questions_eligible_before_tag_gate"] == 1
    assert result["verified_question_count"] == 0
    assert result["pending_tag_count"] == 1


# ===========================================================================
# STATE LOGIC CASES
# ===========================================================================


def test_state_missing_when_no_papers():
    """papers_total=0 → state='missing'."""
    result = _call([], [], [])

    assert result["papers_total"] == 0
    assert result["state"] == "missing"


def test_state_review_pending_when_papers_but_no_verified_question():
    """papers exist but verified_question_count=0 → state='review_pending'."""
    result = _call([PAPER_VER], [Q_PEND], [TAG_VER])

    assert result["papers_total"] == 1
    assert result["verified_question_count"] == 0
    assert result["state"] == "review_pending"


def test_state_ready_when_at_least_one_verified_question():
    """verified_question_count >= 1 → state='ready'."""
    result = _call([PAPER_VER], [Q_VER], [TAG_VER])

    assert result["verified_question_count"] >= 1
    assert result["state"] == "ready"


def test_state_ready_with_multiple_verified_questions():
    """More than one verified question → state='ready' (not some other state)."""
    result = _call([PAPER_VER], [Q_VER, Q_VER_2], [TAG_VER, TAG_VER_2])

    assert result["verified_question_count"] == 2
    assert result["state"] == "ready"


def test_state_review_pending_mixed_rejected_and_pending():
    """Mix of rejected + pending papers: still review_pending (pending paper exists)."""
    papers = [PAPER_REJ, PAPER_PEND]
    result = _call(papers, [], [], cycle=None)

    assert result["state"] == "review_pending"


# ===========================================================================
# BATCH VARIANT CASES
# ===========================================================================


def test_batch_returns_separate_entries_per_exam_id():
    """Papers from two exams yield two separate result entries."""
    papers = [PAPER_VER, PAPER_EXAM_B]
    questions = [Q_VER, Q_EXAM_B]
    tags = [TAG_VER, TAG_EXAM_B]

    batch = aggregate_pyq_evidence_batch(
        papers=papers, questions=questions, topic_tags=tags
    )

    assert EXAM_ID in batch
    assert EXAM_ID_B in batch
    assert len(batch) == 2


def test_batch_questions_do_not_leak_between_exams():
    """A question belonging to exam A's paper must not appear in exam B's result."""
    papers = [PAPER_VER, PAPER_EXAM_B]
    questions = [Q_VER, Q_EXAM_B]
    tags = [TAG_VER, TAG_EXAM_B]

    batch = aggregate_pyq_evidence_batch(
        papers=papers, questions=questions, topic_tags=tags
    )

    # Each exam should have exactly 1 question each.
    assert batch[EXAM_ID]["questions_total"] == 1
    assert batch[EXAM_ID_B]["questions_total"] == 1
    # Each should independently be ready.
    assert batch[EXAM_ID]["verified_question_count"] == 1
    assert batch[EXAM_ID_B]["verified_question_count"] == 1


def test_batch_result_matches_single_exam_call():
    """Batch result for a given exam_id matches the single-exam call for identical data."""
    papers = [PAPER_VER, PAPER_VER_2025]
    questions = [Q_VER, Q_VER_2025]
    tags = [TAG_VER, TAG_VER_2025]

    single = aggregate_pyq_evidence(
        papers=papers,
        questions=questions,
        topic_tags=tags,
        selected_cycle_id=None,
    )
    batch = aggregate_pyq_evidence_batch(
        papers=papers, questions=questions, topic_tags=tags
    )

    batch_result = batch[EXAM_ID]
    # Core numeric fields must match.
    assert batch_result["papers_total"] == single["papers_total"]
    assert batch_result["verified_question_count"] == single["verified_question_count"]
    assert batch_result["questions_total"] == single["questions_total"]
    assert batch_result["state"] == single["state"]


def test_batch_paper_without_exam_id_is_skipped():
    """A paper row with no exam_id is silently skipped by the batch function."""
    papers_with_none = [
        {"id": "orphan", "exam_id": None, "exam_cycle_id": CYCLE_2026, "trust_status": "verified"},
        PAPER_VER,
    ]
    questions = [Q_VER]
    tags = [TAG_VER]

    batch = aggregate_pyq_evidence_batch(
        papers=papers_with_none, questions=questions, topic_tags=tags
    )

    assert EXAM_ID in batch
    assert None not in batch
    # Only PAPER_VER contributes to EXAM_ID.
    assert batch[EXAM_ID]["papers_total"] == 1


# ===========================================================================
# PARITY CASES
# ===========================================================================


def test_parity_verified_count_cycle_none_equals_cycle_2026():
    """aggregate_pyq_evidence with cycle=None and cycle='cycle-2026' yield same verified_question_count."""
    papers = [PAPER_VER, PAPER_VER_2025, PAPER_UNSCO]
    questions = [Q_VER, Q_VER_2025]
    tags = [TAG_VER, TAG_VER_2025]

    result_none = _call(papers, questions, tags, cycle=None)
    result_2026 = _call(papers, questions, tags, cycle=CYCLE_2026)

    assert result_none["verified_question_count"] == result_2026["verified_question_count"]


def test_parity_verified_count_cycle_2026_equals_cycle_2025():
    """Selecting 2026 vs. 2025 yields identical verified_question_count."""
    papers = [PAPER_VER, PAPER_VER_2025]
    questions = [Q_VER, Q_VER_2025]
    tags = [TAG_VER, TAG_VER_2025]

    result_2026 = _call(papers, questions, tags, cycle=CYCLE_2026)
    result_2025 = _call(papers, questions, tags, cycle=CYCLE_2025)

    assert result_2026["verified_question_count"] == result_2025["verified_question_count"]


def test_parity_batch_per_exam_matches_single_exam_call():
    """For every exam, batch result matches the corresponding single-exam call."""
    all_papers = [PAPER_VER, PAPER_VER_2025, PAPER_EXAM_B]
    all_questions = [Q_VER, Q_VER_2025, Q_EXAM_B]
    all_tags = [TAG_VER, TAG_VER_2025, TAG_EXAM_B]

    batch = aggregate_pyq_evidence_batch(
        papers=all_papers, questions=all_questions, topic_tags=all_tags
    )

    # Single-exam call for EXAM_ID using only its papers/questions/tags.
    single_a = aggregate_pyq_evidence(
        papers=[PAPER_VER, PAPER_VER_2025],
        questions=[Q_VER, Q_VER_2025],
        topic_tags=[TAG_VER, TAG_VER_2025],
        selected_cycle_id=None,
    )
    single_b = aggregate_pyq_evidence(
        papers=[PAPER_EXAM_B],
        questions=[Q_EXAM_B],
        topic_tags=[TAG_EXAM_B],
        selected_cycle_id=None,
    )

    for key in ("papers_total", "verified_question_count", "questions_total", "state"):
        assert batch[EXAM_ID][key] == single_a[key], f"Mismatch on {key} for {EXAM_ID}"
        assert batch[EXAM_ID_B][key] == single_b[key], f"Mismatch on {key} for {EXAM_ID_B}"


def test_parity_papers_total_invariant_across_all_cycle_selections():
    """papers_total is identical across None, 2026, and 2025 cycle selections."""
    papers = [PAPER_VER, PAPER_VER_2025, PAPER_UNSCO, PAPER_PEND]
    questions = []
    tags = []

    r_none = _call(papers, questions, tags, cycle=None)
    r_2026 = _call(papers, questions, tags, cycle=CYCLE_2026)
    r_2025 = _call(papers, questions, tags, cycle=CYCLE_2025)

    assert r_none["papers_total"] == r_2026["papers_total"] == r_2025["papers_total"] == 4


def test_parity_scope_invariant_holds_for_all_provenance_counts():
    """For each cycle selection the provenance counters always sum to papers_total."""
    papers = [PAPER_VER, PAPER_VER_2025, PAPER_UNSCO, PAPER_PEND]
    questions = []
    tags = []

    for cycle in [None, CYCLE_2026, CYCLE_2025, "cycle-unknown"]:
        result = _call(papers, questions, tags, cycle=cycle)
        assert (
            result["selected_cycle_papers"]
            + result["other_cycle_papers"]
            + result["unscoped_papers"]
            == result["papers_total"]
        ), f"Invariant failed for cycle={cycle!r}"


# ===========================================================================
# ADDITIONAL EDGE CASES
# ===========================================================================


def test_output_contains_all_required_keys():
    """Return value must include every documented key."""
    result = _call([PAPER_VER], [Q_VER], [TAG_VER], cycle=CYCLE_2026)

    expected_keys = {
        "scope",
        "selected_cycle_id",
        "papers_total",
        "selected_cycle_papers",
        "other_cycle_papers",
        "unscoped_papers",
        "questions_total",
        "verified_question_count",
        "questions_eligible_before_tag_gate",
        "pending_question_count",
        "pending_tag_count",
        "papers_pending_review",
        "state",
    }
    assert expected_keys.issubset(set(result.keys()))


def test_scope_is_always_exam_wide():
    """The 'scope' key must always be 'exam_wide'."""
    for cycle in [None, CYCLE_2026]:
        result = _call([PAPER_VER], [Q_VER], [TAG_VER], cycle=cycle)
        assert result["scope"] == "exam_wide"


def test_selected_cycle_id_echoed_in_output():
    """The selected_cycle_id value passed in must be returned unchanged."""
    result_none = _call([PAPER_VER], [Q_VER], [TAG_VER], cycle=None)
    result_cycle = _call([PAPER_VER], [Q_VER], [TAG_VER], cycle=CYCLE_2026)

    assert result_none["selected_cycle_id"] is None
    assert result_cycle["selected_cycle_id"] == CYCLE_2026


def test_papers_pending_review_counts_non_terminal_papers():
    """papers_pending_review counts papers whose trust_status is 'pending' (not verified/rejected).

    Schema: pyq_papers.trust_status IN ('pending', 'verified', 'rejected').
    Only 'verified' and 'rejected' are terminal; 'pending' is the awaiting-review state.
    """
    papers = [PAPER_VER, PAPER_REJ, PAPER_PEND]
    result = _call(papers, [], [], cycle=None)

    # PAPER_VER (verified) and PAPER_REJ (rejected) are terminal.
    # Only PAPER_PEND (pending) counts as pending review.
    assert result["papers_pending_review"] == 1


def test_state_missing_when_all_papers_rejected():
    """All-rejected corpus has no usable evidence → state='missing', not 'review_pending'.

    review_pending requires at least one non-rejected paper that could have its
    questions/tags reviewed. An all-rejected corpus has no such paper.
    """
    papers = [PAPER_REJ]
    result = _call(papers, [], [], cycle=None)

    assert result["state"] == "missing"
    assert result["papers_total"] == 1
    assert result["verified_question_count"] == 0


def test_state_review_pending_when_pending_paper_exists():
    """A pending (non-rejected) paper with no verified questions → state='review_pending'."""
    papers = [PAPER_PEND]
    result = _call(papers, [], [], cycle=None)

    assert result["state"] == "review_pending"
    assert result["papers_total"] == 1


def test_questions_eligible_before_tag_gate_reflects_gates_1_and_2():
    """questions_eligible_before_tag_gate counts questions passing gates 1+2 before tag check."""
    # Q_VER passes gates 1+2; Q_PEND fails gate 2; Q_ON_PEND_PAPER fails gate 1.
    papers = [PAPER_VER, PAPER_PEND]
    questions = [Q_VER, Q_PEND, Q_ON_PEND_PAPER]
    # No tags → gate 3 fails for everyone, so verified_question_count stays 0.
    tags = []

    result = _call(papers, questions, tags)

    assert result["questions_eligible_before_tag_gate"] == 1
    assert result["verified_question_count"] == 0


# ===========================================================================
# EI-CLEAN-03 — explicit metric decomposition
# (planner-ready vs reviewed vs missing-tag vs rejected)
# ===========================================================================

def test_metrics_reviewed_vs_planner_ready_vs_missing_tag_vs_rejected():
    """The exact screenshot scenario: a verified paper with 98 SME-verified
    questions (no verified tags) + 2 rejected → 0 planner-ready, not '0 of 100
    verified' overloaded onto the review count."""
    paper = {"id": "paper-v", "exam_id": EXAM_ID, "exam_cycle_id": CYCLE_2026, "trust_status": "verified"}
    questions = (
        [{"id": f"q{i}", "pyq_paper_id": "paper-v", "reviewer_status": "verified"} for i in range(98)]
        + [{"id": f"r{i}", "pyq_paper_id": "paper-v", "reviewer_status": "rejected"} for i in range(2)]
    )
    result = _call([paper], questions, tags=[])

    assert result["questions_total"] == 100
    assert result["reviewed_question_count"] == 98
    assert result["rejected_question_count"] == 2
    assert result["planner_ready_question_count"] == 0
    assert result["verified_question_count"] == 0            # planner-ready alias
    assert result["missing_verified_tag_count"] == 98
    assert result["questions_eligible_before_tag_gate"] == 98


def test_metrics_planner_ready_increments_and_missing_tag_decrements_with_tags():
    """Tagging one of the reviewed questions moves it from missing-tag to
    planner-ready; reviewed count is unchanged."""
    paper = {"id": "paper-v", "exam_id": EXAM_ID, "exam_cycle_id": CYCLE_2026, "trust_status": "verified"}
    questions = [
        {"id": "q1", "pyq_paper_id": "paper-v", "reviewer_status": "verified"},
        {"id": "q2", "pyq_paper_id": "paper-v", "reviewer_status": "verified"},
    ]
    tags = [{"id": "t1", "question_id": "q1", "reviewer_status": "verified"}]
    result = _call([paper], questions, tags)

    assert result["reviewed_question_count"] == 2
    assert result["planner_ready_question_count"] == 1
    assert result["missing_verified_tag_count"] == 1
    assert result["rejected_question_count"] == 0


def test_metrics_reviewed_counts_only_verified_reviewer_status():
    """reviewed_question_count is reviewer_status=='verified' only — pending /
    needs_correction / rejected are excluded."""
    paper = {"id": "paper-v", "exam_id": EXAM_ID, "exam_cycle_id": CYCLE_2026, "trust_status": "verified"}
    questions = [
        {"id": "qv", "pyq_paper_id": "paper-v", "reviewer_status": "verified"},
        {"id": "qp", "pyq_paper_id": "paper-v", "reviewer_status": "pending"},
        {"id": "qn", "pyq_paper_id": "paper-v", "reviewer_status": "needs_correction"},
        {"id": "qr", "pyq_paper_id": "paper-v", "reviewer_status": "rejected"},
    ]
    result = _call([paper], questions, tags=[])

    assert result["reviewed_question_count"] == 1
    assert result["rejected_question_count"] == 1
    assert result["pending_question_count"] == 2            # pending + needs_correction
    assert result["missing_verified_tag_count"] == 1        # the one verified, untagged


def test_metrics_missing_tag_excludes_questions_on_unverified_papers():
    """A verified question on a PENDING paper never reaches the tag gate, so it
    is not counted as missing-tag (it fails gate 1 first)."""
    pending_paper = {"id": "paper-p", "exam_id": EXAM_ID, "exam_cycle_id": CYCLE_2026, "trust_status": "pending"}
    questions = [{"id": "qpp", "pyq_paper_id": "paper-p", "reviewer_status": "verified"}]
    result = _call([pending_paper], questions, tags=[])

    assert result["reviewed_question_count"] == 1           # SME-verified regardless of paper
    assert result["questions_eligible_before_tag_gate"] == 0
    assert result["missing_verified_tag_count"] == 0
    assert result["planner_ready_question_count"] == 0
