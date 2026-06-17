"""Unit tests for the console work-queue classifier (Wave 4.6H).

Pure-function tests: no DB, no I/O. They lock the canonical status model:
exactly one of blocked|needs_action|ready, with orthogonal flags.
"""
from __future__ import annotations

from app.exam_intelligence import work_queue as wq


def _agg(**over):
    """A 'ready' aggregate by default; override one signal at a time."""
    base = {
        "phase_count": 1,
        "locked_coverage_count": 1,
        "total_pyq_count": 5,
        "verified_pyq_count": 2,
        "selectable_mock_count": wq.MIN_SELECTABLE_MOCK,
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
    assert c["blocker_count"] == 0


def test_thin_mock_bank_only_is_needs_action_never_blocked():
    c = wq.classify_exam(_agg(selectable_mock_count=wq.MIN_SELECTABLE_MOCK - 1))
    assert c["status"] == "needs_action"
    assert c["flags"] == ["thin_mock_bank"]
    assert c["blocker_count"] == 0  # advisory never counts as a hard blocker


def test_thin_mock_bank_not_flagged_without_locked_coverage():
    # No locked coverage → blocked; mock bank is irrelevant (no thin flag).
    c = wq.classify_exam(_agg(locked_coverage_count=0, selectable_mock_count=0))
    assert "thin_mock_bank" not in c["flags"]


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


def test_status_always_exactly_one_primary():
    primaries = {"blocked", "needs_action", "ready"}
    for over in [
        {}, {"phase_count": 0}, {"locked_coverage_count": 0}, {"verified_pyq_count": 0},
        {"selectable_mock_count": 0}, {"pending_review_count": 5},
        {"phase_count": 0, "locked_coverage_count": 0, "verified_pyq_count": 0},
    ]:
        c = wq.classify_exam(_agg(**over))
        assert c["status"] in primaries
