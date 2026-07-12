"""GQR-Q8 — quant performance signal derivation (shadow) + exclusions + labels."""
from __future__ import annotations

from app.study_os import quant_signals as qs
from tests.persona_questions._stub import SBStub


def _row(topic="t1", *, correct=True, attempted=True, exp=10, act=10, micro=None):
    return {
        "topic_id": topic, "microtopic_id": micro, "is_correct": correct,
        "attempted": attempted, "expected_time_sec": exp, "actual_time_sec": act,
    }


def _one(analytics):
    out = qs.derive_signals(analytics)
    assert len(out) == 1
    return out[0]


# ── labels ────────────────────────────────────────────────────────────────────

def test_insufficient_evidence_below_min_samples():
    sig = _one([_row() for _ in range(3)])  # < min_samples (5)
    assert sig["signal_type"] == "insufficient_evidence"


def test_concept_gap_low_accuracy():
    rows = [_row(correct=(i == 0)) for i in range(6)]  # 1/6 correct
    sig = _one(rows)
    assert sig["signal_type"] == "concept_gap"


def test_application_gap_moderate_accuracy():
    rows = [_row(correct=(i < 3)) for i in range(5)]  # 3/5 = 0.6
    sig = _one(rows)
    assert sig["signal_type"] == "application_gap"


def test_speed_gap_accurate_but_slow():
    rows = [_row(correct=True, exp=10, act=15) for _ in range(6)]  # ratio 1.5
    sig = _one(rows)
    assert sig["signal_type"] == "speed_gap"
    assert sig["median_time_ratio"] == 1.5


def test_calculation_gap_accurate_but_very_slow():
    rows = [_row(correct=True, exp=10, act=20) for _ in range(6)]  # ratio 2.0
    sig = _one(rows)
    assert sig["signal_type"] == "calculation_gap"


def test_stable_accurate_and_fast():
    rows = [_row(correct=True, exp=10, act=9) for _ in range(6)]  # ratio 0.9
    sig = _one(rows)
    assert sig["signal_type"] == "stable"


# ── exclusions (§3.3) ─────────────────────────────────────────────────────────

def test_excludes_unanswered_missing_time_and_outliers_from_ratio():
    rows = [_row(correct=True, exp=10, act=10) for _ in range(5)]  # ratio 1.0
    rows.append(_row(correct=True, exp=10, act=1000))   # extreme dwell (ratio 100) → excluded
    rows.append(_row(correct=True, exp=0, act=10))      # missing expected time → excluded
    rows.append(_row(correct=True, exp=10, act=0))      # zero-duration → excluded
    sig = _one(rows)
    # median ratio computed only from the 5 usable 1.0 rows
    assert sig["median_time_ratio"] == 1.0
    # the unanswered exclusion does not apply here; all are attempted so accuracy
    # counts every answered row
    assert sig["sample_count"] == 8


def test_unattempted_not_counted_in_accuracy():
    rows = [_row(correct=True) for _ in range(5)] + [_row(correct=False, attempted=False)]
    sig = _one(rows)
    assert sig["sample_count"] == 5          # the unattempted row is not counted
    assert sig["accuracy_pct"] == 100.0


def test_groups_by_topic_and_microtopic():
    rows = (
        [_row(topic="t1", micro="m1") for _ in range(5)]
        + [_row(topic="t1", micro="m2") for _ in range(5)]
        + [_row(topic="t2") for _ in range(5)]
    )
    out = qs.derive_signals(rows)
    keys = {(s["topic_id"], s["microtopic_id"]) for s in out}
    assert keys == {("t1", "m1"), ("t1", "m2"), ("t2", None)}


# ── shadow persistence — never a mastery writer ───────────────────────────────

def test_persist_upserts_and_touches_no_mastery():
    sb = SBStub({"quant_performance_signals": [], "user_topic_mastery": []})
    signals = qs.derive_signals([_row() for _ in range(6)])
    n = qs.persist_signals(sb, user_id="u1", signals=signals, exam_id="e1")
    assert n == 1
    assert len(sb.db["quant_performance_signals"]) == 1
    # a recompute for the same scope upserts (no duplicate row)
    qs.persist_signals(sb, user_id="u1", signals=signals, exam_id="e1")
    assert len(sb.db["quant_performance_signals"]) == 1
    # the sibling signal must never write mastery
    assert sb.db["user_topic_mastery"] == []
