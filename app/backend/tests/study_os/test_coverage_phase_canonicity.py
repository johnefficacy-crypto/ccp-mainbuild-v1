"""COV-PHASE-01 — one coverage row per topic, and which phase's row it is.

Live UPSC CSE holds the Mains corpus on TWO phases with the same slug: 1,497
locked rows on a cycle-less template and 1,317 on the cycle-attached phase, the
same topics with identical scores. ``exam_topic_coverage`` is unique on
``(exam, cycle, phase, topic)``, so that is legal, and every learner read that
is exam-wide offered each Mains topic twice — the duplicate palette entries
reported on 'Balance of power', 9.20 twice.

The decision these tests encode: **the cycle-attached phase is canonical for
coverage**, because it is the only phase a plan can ever target. The template
phase stays canonical for evidence, which this module does not touch.

The orphan test is the one that matters most. 180 topics have a row ONLY on the
template phase. Deduping must not turn "duplicated" into "deleted" — a topic
with one row keeps it whichever phase it sits on.
"""
from __future__ import annotations

from typing import Any

import pytest

from app.study_os.planner import (
    _canonical_coverage_rows,
    load_scoped_coverage,
    load_scoped_coverage_checked,
)
from app.study_os.planner_board import list_candidates
from app.exam_intelligence.lookup import invalidate_exam_lookup_cache
from tests.persona_questions._stub import SBStub

_EXAM = "e-upsc"
_TEMPLATE = "ph-mains-template"   # exam_cycle_id IS NULL — never targetable
_CYCLE = "ph-mains-cycle"         # hangs off cycle cyc-1 — the plannable one
_SUB = "sub-gs1"


@pytest.fixture(autouse=True)
def _clear_exam_cache():
    invalidate_exam_lookup_cache()
    yield
    invalidate_exam_lookup_cache()


def _cov(cov_id: str, topic_id: str, phase_id: str | None, score: float = 9.2):
    return {
        "id": cov_id,
        "exam_id": _EXAM,
        "exam_cycle_id": None,          # the derivation hard-codes this
        "exam_phase_id": phase_id,
        "section_id": None,
        "topic_id": topic_id,
        "exam_priority_score": score,
        "is_high_yield": False,
        "reviewer_status": "locked",
        "source_basis": "evidence_derived",
    }


def _seed(coverage: list[dict[str, Any]], topic_ids: list[str]) -> dict[str, Any]:
    return {
        "profiles": [{"id": "u-1", "target_exam": "upsc-cse"}],
        "exams": [
            {"id": _EXAM, "slug": "upsc-cse", "name": "UPSC CSE", "is_active": True}
        ],
        "exam_phases": [
            # Same slug on both, which is exactly why nothing downstream could
            # tell them apart by name.
            {"id": _TEMPLATE, "exam_id": _EXAM, "phase_slug": "mains",
             "exam_cycle_id": None},
            {"id": _CYCLE, "exam_id": _EXAM, "phase_slug": "mains",
             "exam_cycle_id": "cyc-1"},
        ],
        # No elective section anywhere, so elective scoping short-circuits and
        # cannot be what makes these assertions pass.
        "exam_phase_sections": [
            {"id": "sec-gs1", "exam_phase_id": _CYCLE, "subject_id": _SUB,
             "section_label": "GS I", "selection_kind": "compulsory",
             "elective_group": None},
        ],
        "subjects": [
            {"id": _SUB, "name": "GS I", "slug": "gs1", "subject_group": None}
        ],
        "topics": [
            {"id": t, "name": f"Topic {t}", "subject_id": _SUB, "is_active": True}
            for t in topic_ids
        ],
        "exam_topic_coverage": coverage,
    }


def _by_topic(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r["topic_id"]): r for r in rows}


# ── the duplicate ──────────────────────────────────────────────────────────


def test_topic_on_both_mains_phases_is_offered_once_from_the_cycle_phase():
    sb = SBStub(
        _seed(
            [
                _cov("c-template", "t-dup", _TEMPLATE),
                _cov("c-cycle", "t-dup", _CYCLE),
            ],
            ["t-dup"],
        )
    )
    rows = load_scoped_coverage(sb, "u-1", _EXAM)

    assert len(rows) == 1, f"expected one row per topic, got {len(rows)}"
    assert rows[0]["exam_phase_id"] == _CYCLE
    assert rows[0]["coverage_id"] == "c-cycle"


def test_the_template_row_wins_nothing_even_when_it_is_read_first():
    """Order of arrival must not decide it — rank does.

    The coverage read is ordered by id, so the template row can page in first
    or second depending on nothing meaningful. Both orders must land on the
    cycle-attached row.
    """
    forward = load_scoped_coverage(
        SBStub(_seed([_cov("a", "t-dup", _TEMPLATE), _cov("b", "t-dup", _CYCLE)],
                     ["t-dup"])),
        "u-1",
        _EXAM,
    )
    reverse = load_scoped_coverage(
        SBStub(_seed([_cov("a", "t-dup", _CYCLE), _cov("b", "t-dup", _TEMPLATE)],
                     ["t-dup"])),
        "u-1",
        _EXAM,
    )
    assert [r["exam_phase_id"] for r in forward] == [_CYCLE]
    assert [r["exam_phase_id"] for r in reverse] == [_CYCLE]


# ── the 180 orphans ────────────────────────────────────────────────────────


def test_a_topic_with_only_a_template_row_keeps_it():
    """180 live topics are in this state. Dedupe must not delete them.

    They are genuinely in the aspirant's syllabus; what is missing is coverage
    on the plannable phase, which an operator re-derive produces. Until then the
    palette shows them and the planner's own phase filter declines to schedule
    them — visible and unschedulable, never invisible.
    """
    sb = SBStub(
        _seed(
            [
                _cov("c-orphan", "t-orphan", _TEMPLATE),
                _cov("c-cycle", "t-normal", _CYCLE),
            ],
            ["t-orphan", "t-normal"],
        )
    )
    rows = _by_topic(load_scoped_coverage(sb, "u-1", _EXAM))

    assert set(rows) == {"t-orphan", "t-normal"}
    assert rows["t-orphan"]["exam_phase_id"] == _TEMPLATE


# ── the exam-wide row ──────────────────────────────────────────────────────


def test_exam_wide_row_loses_to_the_cycle_phase_but_beats_the_template():
    """An ``exam_phase_id IS NULL`` row applies to whichever phase is targeted.

    So it outranks a template row (which applies to none) and is outranked by
    the cycle phase's own row (which is specifically about the phase in play).
    """
    rows = _by_topic(
        load_scoped_coverage(
            SBStub(
                _seed(
                    [
                        _cov("c-wide-a", "t-a", None),
                        _cov("c-cycle-a", "t-a", _CYCLE),
                        _cov("c-wide-b", "t-b", None),
                        _cov("c-template-b", "t-b", _TEMPLATE),
                    ],
                    ["t-a", "t-b"],
                )
            ),
            "u-1",
            _EXAM,
        )
    )

    assert rows["t-a"]["coverage_id"] == "c-cycle-a"
    assert rows["t-b"]["coverage_id"] == "c-wide-b"


# ── determinism ────────────────────────────────────────────────────────────


def test_two_rows_of_equal_rank_break_on_coverage_id():
    """Two cycle-attached phases could both hold a topic. Pick the same one
    every read — an arbitrary winner that changes between requests would make a
    palette reorder itself for no reason the user can see."""
    phases = [
        {"id": _CYCLE, "exam_cycle_id": "cyc-1"},
        {"id": "ph-other", "exam_cycle_id": "cyc-1"},
    ]
    rows = [
        {"topic_id": "t", "coverage_id": "c-zz", "exam_phase_id": _CYCLE},
        {"topic_id": "t", "coverage_id": "c-aa", "exam_phase_id": "ph-other"},
    ]
    assert [r["coverage_id"] for r in _canonical_coverage_rows(rows, phases)] == ["c-aa"]
    assert [
        r["coverage_id"]
        for r in _canonical_coverage_rows(list(reversed(rows)), phases)
    ] == ["c-aa"]


def test_single_phase_exams_are_untouched():
    """Every exam but UPSC CSE has one row per topic already."""
    rows = [
        {"topic_id": "t1", "coverage_id": "c1", "exam_phase_id": "p"},
        {"topic_id": "t2", "coverage_id": "c2", "exam_phase_id": "p"},
    ]
    out = _canonical_coverage_rows(rows, [{"id": "p", "exam_cycle_id": "cyc"}])
    assert out == rows


# ── the unhealthy read ─────────────────────────────────────────────────────


class _NoPhases(SBStub):
    """The ``exam_phases`` read fails; every other read succeeds."""

    def table(self, name: str):
        if name == "exam_phases":
            raise RuntimeError("forced exam_phases read failure")
        return super().table(name)


def test_a_failed_phase_read_keeps_the_duplicates_and_reports_unhealthy():
    """Fail closed, and fail LOUD rather than wrong.

    A partial phase list would rank a cycle-attached phase as a template and
    keep the wrong row of a duplicated pair. Calibration reads this flag and
    must treat the result as unknown, so leaving the duplicates in place beside
    a False flag is the honest outcome.
    """
    sb = _NoPhases(
        _seed(
            [_cov("c-template", "t-dup", _TEMPLATE), _cov("c-cycle", "t-dup", _CYCLE)],
            ["t-dup"],
        )
    )
    rows, reads_ok = load_scoped_coverage_checked(sb, "u-1", _EXAM)

    assert reads_ok is False
    assert len(rows) == 2


# ── the surface that reported it ───────────────────────────────────────────


def test_the_palette_lists_a_duplicated_topic_once():
    """'Balance of power', 9.20 twice — the reported symptom, end to end."""
    sb = SBStub(
        _seed(
            [
                _cov("c-template", "t-bop", _TEMPLATE),
                _cov("c-cycle", "t-bop", _CYCLE),
            ],
            ["t-bop"],
        )
    )
    items = list_candidates(sb, "u-1")["items"]

    assert [i["topic_id"] for i in items] == ["t-bop"]


def test_rows_with_no_topic_id_are_kept_not_silently_dropped():
    """Nothing to deduplicate against is not a reason to delete a row."""
    rows = [
        {"coverage_id": "c1", "exam_phase_id": _CYCLE},
        {"topic_id": "t", "coverage_id": "c2", "exam_phase_id": _CYCLE},
    ]
    out = _canonical_coverage_rows(rows, [{"id": _CYCLE, "exam_cycle_id": "cyc-1"}])
    assert out == rows


def test_two_hand_built_rows_with_no_coverage_id_still_collapse():
    """A caller that built rows without ids must not defeat the rule."""
    rows = [
        {"topic_id": "t", "exam_phase_id": _TEMPLATE},
        {"topic_id": "t", "exam_phase_id": _CYCLE},
    ]
    out = _canonical_coverage_rows(
        rows,
        [{"id": _TEMPLATE, "exam_cycle_id": None},
         {"id": _CYCLE, "exam_cycle_id": "cyc-1"}],
    )
    assert out == [{"topic_id": "t", "exam_phase_id": _CYCLE}]
