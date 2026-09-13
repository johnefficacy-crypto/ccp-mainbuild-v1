"""PLAN-SCOPE-01 — elective scoping, and the row cap that hid behind it.

Twelve optional-paper subjects went live and widened every derived-from-coverage
surface: calibration demanded 16 subjects, the Subject Hub rendered twelve
optional cards, and the planner ranked a PSIR aspirant's week against
Anthropology Paper-II. One scope rule at one chokepoint closes all three.

The `.limit(2000)` on the same read is tested FIRST and separately. Scoping
shrinks the per-user row count and would mask the cap rather than fix it, so the
truncation test deliberately uses an UNSCOPED exam — it must fail if the cap
comes back even while every scoping test still passes.
"""
from __future__ import annotations

from typing import Any

import pytest

from app.study_os import calibration as calibration_module
from app.study_os.planner import (
    _PAGE,
    _load_locked_coverage,
    generate_plan,
    load_scoped_coverage,
    load_scoped_coverage_checked,
)
from app.study_os.subjects import list_subjects
from app.exam_intelligence.lookup import invalidate_exam_lookup_cache
from tests.persona_questions._stub import SBStub

_EXAM = "e-upsc"
_PHASE = "ph-mains"

# Two compulsory sections (GS I, GS II) and two optionals, each two papers.
_SEC_GS1, _SEC_GS2 = "sec-gs1", "sec-gs2"
_SEC_PSIR1, _SEC_PSIR2 = "sec-psir1", "sec-psir2"
_SEC_ANTH1, _SEC_ANTH2 = "sec-anth1", "sec-anth2"

_SUB_GS1, _SUB_GS2 = "sub-gs1", "sub-gs2"
_SUB_PSIR1, _SUB_PSIR2 = "sub-psir1", "sub-psir2"
_SUB_ANTH1, _SUB_ANTH2 = "sub-anth1", "sub-anth2"


@pytest.fixture(autouse=True)
def _clear_exam_cache():
    """The exam resolvers share a process-wide TTL cache across tests."""
    invalidate_exam_lookup_cache()
    yield
    invalidate_exam_lookup_cache()


def _section(sec_id: str, subject_id: str, *, elective: bool) -> dict[str, Any]:
    return {
        "id": sec_id,
        "exam_phase_id": _PHASE,
        "subject_id": subject_id,
        "section_label": sec_id,
        "selection_kind": "elective" if elective else "compulsory",
        "elective_group": "upsc-cse-optional" if elective else None,
    }


def _coverage(cov_id: str, topic_id: str, section_id: str) -> dict[str, Any]:
    return {
        "id": cov_id,
        "exam_id": _EXAM,
        "exam_cycle_id": "cyc-1",
        "exam_phase_id": _PHASE,
        "section_id": section_id,
        "topic_id": topic_id,
        "exam_priority_score": 70,
        "is_high_yield": True,
        "reviewer_status": "locked",
    }


def _seed(*, electives: bool = True, chosen: list[str] | None = None) -> dict[str, Any]:
    """One topic per section, so a section's presence is countable by topic id."""
    pairs = [
        (_SEC_GS1, _SUB_GS1, False),
        (_SEC_GS2, _SUB_GS2, False),
    ]
    if electives:
        pairs += [
            (_SEC_PSIR1, _SUB_PSIR1, True),
            (_SEC_PSIR2, _SUB_PSIR2, True),
            (_SEC_ANTH1, _SUB_ANTH1, True),
            (_SEC_ANTH2, _SUB_ANTH2, True),
        ]
    seed: dict[str, Any] = {
        # target_exam holds the SLUG here: _resolve_target_exam only takes the
        # by-id path for a 36-char UUID, and falls back to slug otherwise.
        "profiles": [{"id": "u-1", "target_exam": "upsc-cse"}],
        "exams": [{"id": _EXAM, "slug": "upsc-cse", "name": "UPSC CSE", "is_active": True}],
        "exam_phases": [{"id": _PHASE, "exam_id": _EXAM, "phase_slug": "mains"}],
        "exam_phase_sections": [_section(s, sub, elective=e) for s, sub, e in pairs],
        "subjects": [
            {"id": sub, "name": sub, "slug": sub, "subject_group": None}
            for _, sub, _ in pairs
        ],
        "topics": [
            {"id": f"t-{s}", "name": f"Topic {s}", "subject_id": sub, "is_active": True}
            for s, sub, _ in pairs
        ],
        "exam_topic_coverage": [
            _coverage(f"c-{s}", f"t-{s}", s) for s, _, _ in pairs
        ],
    }
    if chosen is not None:
        seed["user_exam_electives"] = [
            {
                "id": "ue-1",
                "user_id": "u-1",
                "exam_id": _EXAM,
                "elective_group": "upsc-cse-optional",
                "subject_ids": chosen,
            }
        ]
    return seed


def _topic_ids(rows: list[dict[str, Any]]) -> set[str]:
    return {r["topic_id"] for r in rows}


# ── 5. the truncation test, written first ──────────────────────────────────


def test_reads_every_row_past_the_old_2000_cap():
    """A corpus above the old ceiling returns in full, exactly.

    Deliberately an exam with NO elective sections: scoping must not be what
    makes this pass. If `.limit(2000)` returns, this fails while every scoping
    test below still passes — which is the whole point of testing it separately.
    """
    total = 2500
    seed = {
        "exams": [{"id": _EXAM, "slug": "upsc-cse", "name": "UPSC CSE", "is_active": True}],
        "exam_phases": [{"id": _PHASE, "exam_id": _EXAM, "phase_slug": "mains"}],
        "exam_phase_sections": [_section(_SEC_GS1, _SUB_GS1, elective=False)],
        "subjects": [{"id": _SUB_GS1, "name": "GS I", "slug": "gs1", "subject_group": None}],
        "topics": [
            {"id": f"t{i}", "name": f"T{i}", "subject_id": _SUB_GS1, "is_active": True}
            for i in range(total)
        ],
        "exam_topic_coverage": [
            _coverage(f"c{i}", f"t{i}", _SEC_GS1) for i in range(total)
        ],
    }
    rows = _load_locked_coverage(SBStub(seed), _EXAM)
    assert len(rows) == total, f"truncated to {len(rows)} of {total}"
    assert len(_topic_ids(rows)) == total


# ── 2. the chosen elective, and the ten that must not appear ───────────────


def test_chosen_elective_includes_its_two_papers_and_excludes_the_others():
    sb = SBStub(_seed(chosen=[_SUB_PSIR1, _SUB_PSIR2]))
    rows = load_scoped_coverage(sb, "u-1", _EXAM)

    ids = _topic_ids(rows)
    # Compulsory GS plus exactly the two chosen papers.
    assert ids == {
        f"t-{_SEC_GS1}", f"t-{_SEC_GS2}", f"t-{_SEC_PSIR1}", f"t-{_SEC_PSIR2}",
    }
    # By count as well as by id — a regression that adds rows must not slip past
    # a set comparison that happens to still contain the right four.
    assert len(rows) == 4
    # The unchosen optional is absent, by id.
    assert f"t-{_SEC_ANTH1}" not in ids
    assert f"t-{_SEC_ANTH2}" not in ids


# ── 1. undecided is a valid state ──────────────────────────────────────────


def test_no_elective_row_yields_compulsory_only_without_error():
    sb = SBStub(_seed(chosen=None))
    rows = load_scoped_coverage(sb, "u-1", _EXAM)

    assert _topic_ids(rows) == {f"t-{_SEC_GS1}", f"t-{_SEC_GS2}"}
    assert rows, "compulsory-only must be non-empty, not an error state"


def test_empty_subject_ids_is_also_compulsory_only():
    """'Still choosing', or 'my optional is not in the corpus'."""
    sb = SBStub(_seed(chosen=[]))
    assert _topic_ids(load_scoped_coverage(sb, "u-1", _EXAM)) == {
        f"t-{_SEC_GS1}", f"t-{_SEC_GS2}",
    }


# ── 3. switching ───────────────────────────────────────────────────────────


def test_switching_choice_changes_the_set_and_orphans_nothing():
    psir = load_scoped_coverage(SBStub(_seed(chosen=[_SUB_PSIR1, _SUB_PSIR2])), "u-1", _EXAM)
    anth = load_scoped_coverage(SBStub(_seed(chosen=[_SUB_ANTH1, _SUB_ANTH2])), "u-1", _EXAM)

    assert _topic_ids(psir) != _topic_ids(anth)
    # GS survives both — it is compulsory, and that is the only reason.
    common = _topic_ids(psir) & _topic_ids(anth)
    assert common == {f"t-{_SEC_GS1}", f"t-{_SEC_GS2}"}
    assert len(psir) == len(anth) == 4


# ── 4. an unresolvable stored choice ───────────────────────────────────────


def test_unresolvable_choice_falls_back_to_compulsory_only(caplog):
    """A retired paper or a bad write must never widen scope back to all."""
    sb = SBStub(_seed(chosen=["sub-does-not-exist"]))
    with caplog.at_level("WARNING"):
        rows = load_scoped_coverage(sb, "u-1", _EXAM)

    assert _topic_ids(rows) == {f"t-{_SEC_GS1}", f"t-{_SEC_GS2}"}
    assert "do not resolve to an elective section" in caplog.text


def test_partially_unresolvable_choice_keeps_the_half_that_resolves(caplog):
    sb = SBStub(_seed(chosen=[_SUB_PSIR1, "sub-gone"]))
    with caplog.at_level("WARNING"):
        rows = load_scoped_coverage(sb, "u-1", _EXAM)

    assert f"t-{_SEC_PSIR1}" in _topic_ids(rows)
    assert f"t-{_SEC_PSIR2}" not in _topic_ids(rows)
    assert "do not resolve" in caplog.text


# ── 7. an exam with no electives at all ────────────────────────────────────


def test_exam_without_elective_sections_is_unchanged():
    sb = SBStub(_seed(electives=False, chosen=None))
    scoped = load_scoped_coverage(sb, "u-1", _EXAM)
    unscoped = _load_locked_coverage(SBStub(_seed(electives=False)), _EXAM)

    assert _topic_ids(scoped) == _topic_ids(unscoped)
    assert len(scoped) == len(unscoped) == 2


def test_unscoped_loader_still_sees_every_elective():
    """Admin/derivation reads must keep seeing the whole exam."""
    rows = _load_locked_coverage(SBStub(_seed(chosen=[_SUB_PSIR1, _SUB_PSIR2])), _EXAM)
    assert len(rows) == 6


# ── 6. the three regressions, at their own call sites ──────────────────────


def test_calibration_asks_only_for_subjects_in_scope():
    """Regression 1: the gate demanded GS I-IV plus all twelve optional papers."""
    sb = SBStub(_seed(chosen=[_SUB_PSIR1, _SUB_PSIR2]))
    subjects, ok = calibration_module.resolve_required_subjects(sb, _EXAM, "u-1")

    assert ok is True
    ids = {s["subject_id"] for s in subjects}
    assert ids == {_SUB_GS1, _SUB_GS2, _SUB_PSIR1, _SUB_PSIR2}
    assert _SUB_ANTH1 not in ids and _SUB_ANTH2 not in ids


def test_calibration_undecided_user_asks_for_compulsory_only():
    sb = SBStub(_seed(chosen=None))
    subjects, ok = calibration_module.resolve_required_subjects(sb, _EXAM, "u-1")

    assert ok is True
    assert {s["subject_id"] for s in subjects} == {_SUB_GS1, _SUB_GS2}


def test_calibration_still_fails_closed_on_a_read_failure():
    """The scoping rewrite must not cost the fail-closed health flag."""

    class _Boom(SBStub):
        def table(self, name: str):
            if name == "exam_topic_coverage":
                raise RuntimeError("simulated coverage outage")
            return super().table(name)

    subjects, ok = calibration_module.resolve_required_subjects(
        _Boom(_seed(chosen=None)), _EXAM, "u-1"
    )
    assert subjects == []
    assert ok is False, "a failed coverage read must read as UNKNOWN, not 'nothing to do'"


def test_subject_hub_shows_only_the_chosen_optional():
    """Regression 2: the hub rendered twelve optional cards."""
    sb = SBStub(_seed(chosen=[_SUB_PSIR1, _SUB_PSIR2]))
    items = list_subjects(sb, "u-1")

    subject_ids = {it.get("subject_id") for it in items if it.get("subject_id")}
    assert _SUB_PSIR1 in subject_ids and _SUB_PSIR2 in subject_ids
    assert _SUB_ANTH1 not in subject_ids and _SUB_ANTH2 not in subject_ids


def test_planner_emits_tasks_only_for_subjects_in_scope():
    """Regression 3: a PSIR aspirant's week could go to Anthropology Paper-II.

    Drives ``generate_plan`` end to end and asserts on the topic ids of the
    tasks it actually PERSISTS. The previous version of this test called
    ``load_scoped_coverage_checked`` directly and passed for months while
    ``_compute_plan`` still called the unscoped loader — it proved the wrapper
    worked, never that the planner used it.
    """
    sb = SBStub(_seed(chosen=[_SUB_PSIR1, _SUB_PSIR2]))
    out = generate_plan(sb, "u-1")
    assert out.get("generated") is True, out

    tasks = [t for t in (sb.db.get("study_tasks") or []) if t.get("user_id") == "u-1"]
    assert tasks, "planner persisted no tasks"

    # Resolve each emitted task back to the subject that owns its topic.
    topic_subject = {t["id"]: t["subject_id"] for t in sb.db["topics"]}
    task_subjects = {topic_subject[t["topic_id"]] for t in tasks}

    assert task_subjects <= {_SUB_GS1, _SUB_GS2, _SUB_PSIR1, _SUB_PSIR2}
    # By id: the unchosen optional never reaches a task.
    assert _SUB_ANTH1 not in task_subjects
    assert _SUB_ANTH2 not in task_subjects
    # By count: four sections are in scope, so at most four distinct topics can
    # be — a pool that widened back to six would break this even if the four
    # right ones were still present.
    assert len({t["topic_id"] for t in tasks}) <= 4
    assert not any(
        t["topic_id"] in {f"t-{_SEC_ANTH1}", f"t-{_SEC_ANTH2}"} for t in tasks
    )


def test_planner_refuses_rather_than_planning_from_a_truncated_pool():
    """A partial coverage read must not become a quietly incomplete plan.

    ``_paginate_all`` returns a PREFIX when a page fails mid-walk. Planning from
    that prefix would drop topics with no error on any surface, so the planner
    refuses with a retryable reason instead.
    """
    seed = _seed(chosen=[_SUB_PSIR1, _SUB_PSIR2])
    calls = {"n": 0}

    class _FlakyCoverage(SBStub):
        def table(self, name: str):
            if name == "exam_topic_coverage":
                calls["n"] += 1
                if calls["n"] > 1:  # first page lands, the walk then fails
                    raise RuntimeError("simulated mid-walk read failure")
            return super().table(name)

    # Force a second page: _PAGE rows + 1 means the walk cannot finish in one.
    big = dict(seed)
    big["topics"] = list(seed["topics"]) + [
        {"id": f"t-bulk{i}", "name": f"B{i}", "subject_id": _SUB_GS1, "is_active": True}
        for i in range(_PAGE)
    ]
    big["exam_topic_coverage"] = list(seed["exam_topic_coverage"]) + [
        _coverage(f"c-bulk{i}", f"t-bulk{i}", _SEC_GS1) for i in range(_PAGE)
    ]

    out = generate_plan(_FlakyCoverage(big), "u-1")
    assert out.get("generated") is False
    assert out.get("reason") == "coverage_read_failed"


def test_section_id_is_carried_on_every_row():
    """The filter is a section-id intersection, so the id has to survive.

    It was selected from the table but dropped when the output row was built,
    so callers saw rows with no section identity at all.
    """
    rows = _load_locked_coverage(SBStub(_seed()), _EXAM)
    assert rows and all(r.get("section_id") for r in rows)
