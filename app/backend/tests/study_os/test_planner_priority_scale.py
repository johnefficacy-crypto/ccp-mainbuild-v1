"""RANK-SCALE-01 in the planner — the consumer where the defect surfaced.

`_load_locked_coverage` is exam-wide, so a plan for an exam with both a Mains
phase (v2.0 `evidence_derived` rows, max 36.10 live) and a Prelims phase
(hand-authored `official_syllabus` rows, min 60.00 live) ranked the twenty
authored rows above all 1,497 derived ones by construction.

PLAN-POOL-01 read that as a broken phase filter. The filter was fine; the
scales were never comparable.
"""
from __future__ import annotations

from app.study_os.planner import generate_plan
from tests.persona_questions._stub import SBStub


def _mixed_seed() -> dict:
    """One exam, two phases, two unit systems.

    Mains: five derived rows topping out at 14.95, the live optionals maximum.
    Prelims: three authored rows, 60/70/85 — the live authored range.

    Mastery is identical everywhere so the coverage term is what decides, and
    the derived corpus is deliberately larger than the authored one, as it is
    live (1,497 vs 13).
    """
    derived = [(f"d{i}", s) for i, s in enumerate([0.8, 2.5, 6.4, 9.9, 14.95])]
    authored = [(f"a{i}", s) for i, s in enumerate([60.0, 70.0, 85.0])]

    coverage, topics = [], []
    for tid, score in derived:
        coverage.append({
            "id": f"c-{tid}", "exam_id": "e1", "exam_cycle_id": "cyc-1",
            "exam_phase_id": "ph-mains", "topic_id": tid,
            "exam_priority_score": score, "is_high_yield": False,
            "source_basis": "evidence_derived", "reviewer_status": "locked",
        })
        topics.append({"id": tid, "name": f"Derived {tid}", "subject_id": "s-mains",
                       "is_active": True})
    for tid, score in authored:
        coverage.append({
            "id": f"c-{tid}", "exam_id": "e1", "exam_cycle_id": "cyc-1",
            "exam_phase_id": "ph-prelims", "topic_id": tid,
            "exam_priority_score": score, "is_high_yield": False,
            "source_basis": "official_syllabus", "reviewer_status": "locked",
        })
        topics.append({"id": tid, "name": f"Authored {tid}", "subject_id": "s-prelims",
                       "is_active": True})

    return {
        "profiles": [{"id": "u-1", "target_exam": "upsc-cse"}],
        "exams": [{"id": "e1", "slug": "upsc-cse", "name": "UPSC CSE",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_cycles": [{"id": "cyc-1", "exam_id": "e1", "exam_start": "2026-09-15"}],
        "exam_topic_coverage": coverage,
        "topics": topics,
        "subjects": [{"id": "s-mains", "name": "Mains"},
                     {"id": "s-prelims", "name": "Prelims"}],
        "user_topic_mastery": [],
    }


def _ranked_topics(seed: dict) -> list[str]:
    out = generate_plan(SBStub(seed), "u-1")
    return [t["topic"] for t in out["tasks"]]


def test_the_best_derived_topic_outranks_a_mid_authored_one():
    """The assertion that fails on current `main`: with the raw column, every
    one of the three authored rows sorts above every derived row, so
    `Derived d4` cannot appear before `Authored a1`. Verified by reverting
    `planner.py` and re-running — the order comes back authored-first."""
    order = _ranked_topics(_mixed_seed())
    assert order, "planner produced no tasks"
    assert order.index("Derived d4") < order.index("Authored a1")


def test_the_top_task_is_no_longer_authored_by_construction():
    order = _ranked_topics(_mixed_seed())
    assert order[0] == "Derived d4"


def test_order_within_each_basis_is_still_by_evidence():
    """Reconciling the two scales must not reshuffle within either of them.
    The plan emits a capped number of tasks, so this checks the relative order
    of whichever topics made the cut, not that all eight did."""
    order = _ranked_topics(_mixed_seed())
    derived = [t for t in order if t.startswith("Derived")]
    authored = [t for t in order if t.startswith("Authored")]
    assert derived == sorted(derived, reverse=True)   # d4 before d3 before …
    assert authored == sorted(authored, reverse=True)  # a2 before a1 before a0
    assert derived[0] == "Derived d4"


def test_the_raw_score_is_still_reported_untouched():
    """Ranking changes; the number the payload carries does not. A reader can
    still see the v2.0 value that was locked and published."""
    out = generate_plan(SBStub(_mixed_seed()), "u-1")
    by_topic = {t["topic"]: t for t in out["tasks"]}
    why = by_topic["Derived d4"].get("why_this_task") or {}
    assert why.get("coverage_priority") == 14.95
    assert why.get("comparable_priority") is not None
    assert why["comparable_priority"] != why["coverage_priority"]


def test_a_single_basis_exam_plan_is_unchanged():
    """D3: a consumer that only ever sees one unit system must not move. With
    every row on one basis the comparable value IS the raw score, so the plan
    is bit-for-bit what it was."""
    seed = _mixed_seed()
    for row in seed["exam_topic_coverage"]:
        row["source_basis"] = "evidence_derived"
        row["exam_phase_id"] = "ph-mains"

    out = generate_plan(SBStub(seed), "u-1")
    for task in out["tasks"]:
        why = task.get("why_this_task") or {}
        assert why["comparable_priority"] == why["coverage_priority"]

    # And the ranking is plain evidence order.
    assert [t["topic"] for t in out["tasks"]][:2] == ["Authored a2", "Authored a1"]
