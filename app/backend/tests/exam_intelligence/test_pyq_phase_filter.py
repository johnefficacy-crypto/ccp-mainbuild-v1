"""Regression tests for the PYQ Explorer's `phase` filter.

Root cause (found live 2026-09-12): `list_exam_pyqs` resolved the `phase`
query parameter to a phase id with

    sb.table("exam_phases").select("id").eq("phase_slug", phase).limit(1)

— no `exam_id` scope. `phase_slug` is **not** globally unique: 86 exams in the
registry carry a phase slugged ``mains``. PostgREST returned whichever row it
liked, the id belonged to some other exam, no paper matched it, and the
explorer returned ``{items: [], total: 0}`` for every exam but the lucky one.

Observed: UPSC CSE Mains returned 0 while 6,074 verified questions were
reachable on the same route without the filter.

The slug is not unique *within* an exam either — UPSC CSE has three ``mains``
phases (a null-cycle template plus cycle-specific phases promoted from it), so
the fix matches every phase on the exam rather than picking one arbitrarily.
Both properties are pinned below; revert either and a test here fails.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import exam_intelligence as ei_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub


def _build_app(sb):
    app = FastAPI()
    app.include_router(ei_api.router, prefix="/api")
    ei_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "u-1", "role": "user", "permissions": [],
    }
    return app


def _get(sb, slug: str, params: str):
    client = TestClient(_build_app(sb))
    r = client.get(f"/api/exam-intelligence/exams/{slug}/pyqs?{params}")
    assert r.status_code == 200, r.text
    return r.json()


def _question(qid: str, paper_id: str, n: int) -> dict:
    return {
        "id": qid,
        "pyq_paper_id": paper_id,
        "question_number": n,
        "question_text": f"Question {n}",
        "observed_difficulty": "medium",
        "reviewer_status": "verified",
    }


def _seed_two_exams_sharing_a_slug() -> dict:
    """Two exams, each with a phase slugged 'mains' and one verified paper.

    The other exam is seeded FIRST so a lookup without an exam scope is
    likely to resolve to it — which is exactly the live failure.
    """
    return {
        "exams": [
            {"id": "e-other", "slug": "some-state-pcs"},
            {"id": "e-upsc", "slug": "upsc-cse"},
        ],
        "exam_phases": [
            {"id": "ph-other", "exam_id": "e-other", "phase_slug": "mains",
             "phase_name": "Mains"},
            {"id": "ph-upsc", "exam_id": "e-upsc", "phase_slug": "mains",
             "phase_name": "Mains"},
        ],
        "pyq_papers": [
            {"id": "p-other", "exam_id": "e-other", "year": 2024,
             "exam_phase_id": "ph-other", "trust_status": "verified"},
            {"id": "p-upsc", "exam_id": "e-upsc", "year": 2024,
             "exam_phase_id": "ph-upsc", "trust_status": "verified"},
        ],
        "subjects": [{"id": "s1", "name": "General Studies"}],
        "topics": [{"id": "t1", "name": "Polity", "subject_id": "s1"}],
        "pyq_questions": [
            _question("q-other-1", "p-other", 1),
            _question("q-upsc-1", "p-upsc", 1),
            _question("q-upsc-2", "p-upsc", 2),
        ],
        "pyq_question_topic_tags": [],
    }


def _seed_one_exam_three_mains_phases() -> dict:
    """One exam whose 'mains' slug appears on three phases.

    UPSC CSE really is shaped this way: a null-cycle template phase plus
    cycle-specific phases promoted from it, all slugged 'mains'. A paper may
    hang off any of them, so all three must match.
    """
    return {
        "exams": [{"id": "e-upsc", "slug": "upsc-cse"}],
        "exam_phases": [
            {"id": "ph-template", "exam_id": "e-upsc", "phase_slug": "mains",
             "phase_name": "Mains", "exam_cycle_id": None},
            {"id": "ph-2024", "exam_id": "e-upsc", "phase_slug": "mains",
             "phase_name": "Mains", "exam_cycle_id": "c-2024"},
            {"id": "ph-2026", "exam_id": "e-upsc", "phase_slug": "mains",
             "phase_name": "Mains", "exam_cycle_id": "c-2026"},
        ],
        "pyq_papers": [
            {"id": "p-t", "exam_id": "e-upsc", "year": 2023,
             "exam_phase_id": "ph-template", "trust_status": "verified"},
            {"id": "p-24", "exam_id": "e-upsc", "year": 2024,
             "exam_phase_id": "ph-2024", "trust_status": "verified"},
            {"id": "p-26", "exam_id": "e-upsc", "year": 2026,
             "exam_phase_id": "ph-2026", "trust_status": "verified"},
        ],
        "subjects": [{"id": "s1", "name": "General Studies"}],
        "topics": [{"id": "t1", "name": "Polity", "subject_id": "s1"}],
        "pyq_questions": [
            _question("q-t", "p-t", 1),
            _question("q-24", "p-24", 1),
            _question("q-26", "p-26", 1),
        ],
        "pyq_question_topic_tags": [],
    }


def test_phase_filter_does_not_resolve_to_another_exams_phase():
    """Filtering UPSC CSE by phase=mains returns UPSC's questions, not zero.

    Without the exam_id scope the lookup could bind 'mains' to the other
    exam's phase, no UPSC paper would match, and total would be 0.
    """
    body = _get(SBStub(_seed_two_exams_sharing_a_slug()), "upsc-cse",
                "phase=mains&page=1&page_size=20")
    assert body["total"] == 2, (
        "phase=mains resolved to a phase that is not this exam's — "
        "the lookup is missing its exam_id scope"
    )
    assert {i["id"] for i in body["items"]} == {"q-upsc-1", "q-upsc-2"}


def test_phase_filter_never_returns_another_exams_questions():
    """The converse: the other exam's paper must not leak into this result."""
    body = _get(SBStub(_seed_two_exams_sharing_a_slug()), "upsc-cse",
                "phase=mains&page=1&page_size=20")
    assert "q-other-1" not in {i["id"] for i in body["items"]}


def test_phase_filter_matches_every_phase_carrying_that_slug_on_the_exam():
    """Three 'mains' phases on one exam -> all three papers are in scope.

    Picking one with .limit(1) would return a third of the corpus and look
    like a data problem rather than a query bug.
    """
    body = _get(SBStub(_seed_one_exam_three_mains_phases()), "upsc-cse",
                "phase=mains&page=1&page_size=20")
    assert body["total"] == 3, (
        "only some 'mains' phases matched — the lookup is still taking one row"
    )
    assert {i["id"] for i in body["items"]} == {"q-t", "q-24", "q-26"}


def test_unknown_phase_slug_returns_empty_not_everything():
    """A slug that matches nothing on this exam must return no rows.

    Falling through to an unfiltered result would be worse than the original
    bug: the aspirant would silently get every phase.
    """
    body = _get(SBStub(_seed_two_exams_sharing_a_slug()), "upsc-cse",
                "phase=does-not-exist&page=1&page_size=20")
    assert body["total"] == 0
    assert body["items"] == []
