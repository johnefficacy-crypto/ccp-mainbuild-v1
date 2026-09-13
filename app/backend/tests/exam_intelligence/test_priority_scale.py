"""RANK-SCALE-01 — `exam_priority_score` carried two incompatible unit systems.

Live on 2026-09-12 the Mains maximum (36.10, v2.0 cohort model, 1,497 rows) sat
BELOW the Prelims minimum (60.00, hand-authored, 13 rows), so a derived row
could never outrank an authored one whatever the evidence said. These tests pin
the read-time reconciliation and, just as importantly, pin that a set with only
one unit system is left completely alone.
"""
from __future__ import annotations

from app.exam_intelligence.priority_scale import (
    EVIDENCE_DERIVED_BASIS,
    attach_comparable_priority,
    comparable_priorities,
)

DERIVED = EVIDENCE_DERIVED_BASIS
AUTHORED = "official_syllabus"


def _row(score: float, basis: str, tid: str = "t") -> dict:
    return {"topic_id": tid, "exam_priority_score": score, "source_basis": basis}


# ── 1. The defect, and the fix ───────────────────────────────────────────────
def test_a_strong_derived_row_can_outrank_an_authored_one():
    """The headline. A derived row at 14.95 — the top of the observed optionals
    range — against an authored row at 85. On the raw column the derived row
    loses by construction; on its standing within its own unit system it wins,
    because it is the best of 1,497 and the authored one is mid-pack of 13."""
    rows = [_row(14.95, DERIVED, "strong-derived")]
    rows += [_row(s, DERIVED, f"d{i}") for i, s in enumerate([0.5, 1.2, 3.0, 6.4, 9.1])]
    rows += [_row(s, AUTHORED, f"a{i}") for i, s in enumerate([60.0, 70.0, 85.0, 90.0, 95.0])]
    rows[8]["topic_id"] = "mid-authored"  # the 85.0 row

    attach_comparable_priority(rows)
    by_id = {r["topic_id"]: r for r in rows}

    # Raw: the authored row wins every time.
    assert by_id["mid-authored"]["exam_priority_score"] > by_id["strong-derived"]["exam_priority_score"]
    # Comparable: the derived row is top of its basis, the authored one is not.
    assert by_id["strong-derived"]["comparable_priority"] > by_id["mid-authored"]["comparable_priority"]

    ranked = sorted(rows, key=lambda r: -r["comparable_priority"])
    assert ranked[0]["topic_id"] == "strong-derived"


def test_the_raw_column_is_never_rewritten():
    """Neither score is recomputed — the v2.0 output is locked and published and
    the authored rows are somebody's judgement. Only a new key is added."""
    rows = [_row(6.42, DERIVED), _row(82.31, AUTHORED)]
    attach_comparable_priority(rows)
    assert rows[0]["exam_priority_score"] == 6.42
    assert rows[1]["exam_priority_score"] == 82.31
    assert rows[0]["source_basis"] == DERIVED


def test_order_within_a_basis_is_preserved():
    rows = [_row(s, DERIVED, f"d{i}") for i, s in enumerate([1.0, 5.0, 20.0, 36.1])]
    rows += [_row(s, AUTHORED, f"a{i}") for i, s in enumerate([55.0, 62.0, 95.0])]
    attach_comparable_priority(rows)
    derived = [r for r in rows if r["source_basis"] == DERIVED]
    assert [r["topic_id"] for r in sorted(derived, key=lambda r: -r["comparable_priority"])] == [
        "d3", "d2", "d1", "d0"
    ]


# ── 2. A single-basis set must not move (D3) ─────────────────────────────────
def test_a_single_basis_set_is_returned_unchanged():
    """Rank order would survive percentile-ranking, but the GAPS would not, and
    every consumer blends this score with other terms rather than sorting on it
    alone. So a set with one unit system is handed back exactly as it came."""
    scores = [84.0, 70.0, 40.0, 40.0, 5.0]
    rows = [_row(s, AUTHORED, f"a{i}") for i, s in enumerate(scores)]
    attach_comparable_priority(rows)
    assert [r["comparable_priority"] for r in rows] == scores


def test_rows_with_no_basis_recorded_are_also_left_alone():
    rows = [{"exam_priority_score": s} for s in (84.0, 70.0, 40.0)]
    attach_comparable_priority(rows)
    assert [r["comparable_priority"] for r in rows] == [84.0, 70.0, 40.0]


def test_an_unrecorded_basis_is_its_own_group_not_folded_into_derived():
    """Guessing which unit system a null basis belongs to would silently
    mis-rank it."""
    rows = [_row(10.0, DERIVED), _row(20.0, DERIVED), {"exam_priority_score": 90.0}]
    values = comparable_priorities(rows)
    # Three rows, two groups → normalisation applies; the unknown row is alone
    # in its group and therefore lands at the neutral midpoint.
    assert values[2] == 50.0


# ── 3. Mid-rank behaviour ────────────────────────────────────────────────────
def test_ties_share_a_value():
    rows = [_row(5.0, DERIVED), _row(5.0, DERIVED), _row(9.0, DERIVED), _row(60.0, AUTHORED)]
    values = comparable_priorities(rows)
    assert values[0] == values[1]
    assert values[2] > values[0]


def test_a_lone_row_in_a_basis_scores_the_neutral_midpoint():
    """The only honest answer when there is nothing to rank against — and it
    keeps a single authored row from being pinned to 0 or 100 by group size."""
    rows = [_row(1.0, DERIVED), _row(2.0, DERIVED), _row(95.0, AUTHORED)]
    assert comparable_priorities(rows)[2] == 50.0


def test_no_row_is_pinned_to_zero_or_one_hundred():
    rows = [_row(float(i), DERIVED, f"d{i}") for i in range(5)]
    rows += [_row(60.0, AUTHORED)]
    values = comparable_priorities(rows)
    assert all(0.0 < v < 100.0 for v in values)


# ── 4. Shared reference keeps a before/after diff honest ─────────────────────
def test_a_shared_reference_keeps_two_sets_on_one_footing():
    """Percentile is set-relative, so a before/after pair measured separately
    would show movement that is only a change of denominator."""
    before = [_row(s, DERIVED, f"d{i}") for i, s in enumerate([1.0, 5.0, 20.0])]
    before += [_row(60.0, AUTHORED, "a0")]
    after = [dict(r) for r in before] + [_row(30.0, DERIVED, "new")]

    reference = attach_comparable_priority([dict(r) for r in after])
    attach_comparable_priority(before, reference=reference)
    attach_comparable_priority(after, reference=reference)

    b = {r["topic_id"]: r["comparable_priority"] for r in before}
    a = {r["topic_id"]: r["comparable_priority"] for r in after}
    # Every row present in both sides keeps the same standing; only the genuinely
    # new row appears.
    for tid in b:
        assert b[tid] == a[tid], tid
    assert a["new"] > a["d2"]
