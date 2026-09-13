"""D6 — the planner must refuse to build plans on inactive exams.

``resolve_exam_by_id`` / ``resolve_exam_by_slug`` resolved on identity alone,
with no ``exams.is_active`` predicate, and ``_compute_plan``'s only exam-level
gate is for ``management_mode == 'light'``. A retired or sandbox exam with
locked coverage therefore produced a real study plan.

The guard lives in the resolvers and fails closed. These tests pin both halves:
the resolver contract, and every consumer's behaviour when it trips.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import study_os as study_os_api
from app.core.auth import get_current_user
from app.exam_intelligence import lookup as lookup_module
from app.exam_intelligence.lookup import (
    InactiveExamError,
    resolve_exam_by_id,
    resolve_exam_by_slug,
)
from app.study_os.planner import generate_plan
from app.study_os.regen import regenerate_stale_plans
from tests.persona_questions._stub import SBStub


def _exam(exam_id: str, slug: str, *, is_active: bool) -> dict:
    return {
        "id": exam_id,
        "slug": slug,
        "name": f"Exam {slug}",
        "exam_type": "recruitment",
        "is_active": is_active,
    }


def _planner_seed(exams: list[dict], profiles: list[dict]) -> dict:
    """One locked, plannable topic per exam in *exams*.

    Mirrors ``tests/study_os/test_plan_preferences.py::_planner_seed`` — the
    point here is the exam gate, so the rest of the chain is deliberately
    minimal but complete enough that an ACTIVE exam really does produce tasks.
    """
    coverage = []
    cycles = []
    for i, ex in enumerate(exams):
        cycles.append(
            {"id": f"cyc-{i}", "exam_id": ex["id"], "exam_start": "2099-09-15"}
        )
        coverage.append(
            {
                "id": f"c-{i}",
                "exam_id": ex["id"],
                "exam_cycle_id": f"cyc-{i}",
                "exam_phase_id": f"ph-{i}",
                "topic_id": "t1",
                "exam_priority_score": 80,
                "is_high_yield": True,
                "reviewer_status": "locked",
            }
        )
    return {
        "profiles": profiles,
        "exams": exams,
        "exam_cycles": cycles,
        "exam_topic_coverage": coverage,
        "topics": [
            {"id": "t1", "name": "Percentage", "subject_id": "s1", "is_active": True}
        ],
        "subjects": [{"id": "s1", "name": "Quant"}],
    }


@pytest.fixture(autouse=True)
def _clear_exam_cache():
    """The resolvers share a process-wide TTL cache across tests."""
    lookup_module.invalidate_exam_lookup_cache()
    yield
    lookup_module.invalidate_exam_lookup_cache()


# ── 6. the one that matters: a mixed regen cohort ──────────────────────────


def test_regenerate_stale_plans_skips_inactive_exam_user_and_plans_the_rest():
    """One user on a retired exam must not abort the nightly sweep.

    ``regenerate_stale_plans`` iterates every active plan in the system. If a
    single user's target exam is retired, the other users' plans must still be
    regenerated, and the skip must be counted rather than silently lost.
    """
    live = _exam("e-live", "upsc-cse", is_active=True)
    dead = _exam("e-dead", "sandbox-do-not-use", is_active=False)
    seed = _planner_seed(
        [live, dead],
        [
            {"id": "u-live-1", "target_exam": "upsc-cse"},
            {"id": "u-dead", "target_exam": "sandbox-do-not-use"},
            {"id": "u-live-2", "target_exam": "upsc-cse"},
        ],
    )
    stale = "2020-01-01T00:00:00+00:00"
    seed["study_plans"] = [
        {"id": "p-1", "user_id": "u-live-1", "status": "active", "updated_at": stale},
        {"id": "p-2", "user_id": "u-dead", "status": "active", "updated_at": stale},
        {"id": "p-3", "user_id": "u-live-2", "status": "active", "updated_at": stale},
    ]

    out = regenerate_stale_plans(SBStub(seed))

    assert out["checked"] == 3
    assert out["skipped_inactive_exam"] == 1
    # The sweep did not abort: both live users were planned.
    assert out["regenerated"] == 2


def test_regenerate_stale_plans_reports_zero_skips_when_all_exams_active():
    """The new counter must not fire for an ordinary all-healthy sweep."""
    live = _exam("e-live", "upsc-cse", is_active=True)
    seed = _planner_seed([live], [{"id": "u-1", "target_exam": "upsc-cse"}])
    seed["study_plans"] = [
        {
            "id": "p-1",
            "user_id": "u-1",
            "status": "active",
            "updated_at": "2020-01-01T00:00:00+00:00",
        }
    ]

    out = regenerate_stale_plans(SBStub(seed))

    assert out["regenerated"] == 1
    assert out["skipped_inactive_exam"] == 0


# ── 1-4. the resolver contract ─────────────────────────────────────────────


def test_active_exam_resolves_unchanged():
    """Existing behaviour has not moved for a live exam."""
    row = _exam("e1", "upsc-cse", is_active=True)
    sb = SBStub({"exams": [row]})
    assert resolve_exam_by_id(sb, "e1") == row
    lookup_module.invalidate_exam_lookup_cache()
    assert resolve_exam_by_slug(sb, "upsc-cse") == row


def test_inactive_exam_raises_by_default():
    row = _exam("e-dead", "sandbox-do-not-use", is_active=False)
    sb = SBStub({"exams": [row]})

    with pytest.raises(InactiveExamError) as caught:
        resolve_exam_by_id(sb, "e-dead")
    assert caught.value.exam_id == "e-dead"
    assert caught.value.slug == "sandbox-do-not-use"

    lookup_module.invalidate_exam_lookup_cache()
    with pytest.raises(InactiveExamError):
        resolve_exam_by_slug(sb, "sandbox-do-not-use")


def test_inactive_exam_resolves_with_allow_inactive():
    """The opt-out admin/diagnostic surfaces rely on."""
    row = _exam("e-dead", "sandbox-do-not-use", is_active=False)
    sb = SBStub({"exams": [row]})
    assert resolve_exam_by_id(sb, "e-dead", allow_inactive=True) == row
    lookup_module.invalidate_exam_lookup_cache()
    assert (
        resolve_exam_by_slug(sb, "sandbox-do-not-use", allow_inactive=True) == row
    )


def test_missing_is_active_is_treated_as_inactive():
    """Fail closed on a row that reached us without the flag.

    ``exams.is_active`` is ``boolean not null default true`` (migration 030),
    so production rows always carry it. This pins the guard's behaviour if a
    narrowed ``select`` or a stub ever drops the column: absent is not consent.
    """
    sb = SBStub({"exams": [{"id": "e1", "slug": "upsc-cse", "name": "UPSC"}]})
    with pytest.raises(InactiveExamError):
        resolve_exam_by_id(sb, "e1")


def test_guard_applies_to_a_cached_row():
    """A row cached by an ``allow_inactive=True`` caller must still be refused.

    The TTL cache is shared across callers, so the guard has to run on the
    cache-hit path too — otherwise one admin read would open the exam to every
    planner read for the rest of the TTL window.
    """
    row = _exam("e-dead", "sandbox-do-not-use", is_active=False)
    sb = SBStub({"exams": [row]})
    assert resolve_exam_by_id(sb, "e-dead", allow_inactive=True) == row
    with pytest.raises(InactiveExamError):
        resolve_exam_by_id(sb, "e-dead")


def test_missing_exam_still_returns_none_not_raise():
    """Absent row is still ``None`` — the guard did not swallow the 404 path."""
    sb = SBStub({"exams": []})
    assert resolve_exam_by_id(sb, "nope") is None
    assert resolve_exam_by_slug(sb, "nope") is None


# ── 5. planner entry point ─────────────────────────────────────────────────


def test_generate_plan_reports_exam_inactive_in_band():
    """The planner reports refusal in-band, distinct from ``no_target_exam``."""
    dead = _exam("e-dead", "sandbox-do-not-use", is_active=False)
    seed = _planner_seed([dead], [{"id": "u-1", "target_exam": "sandbox-do-not-use"}])

    out = generate_plan(SBStub(seed), "u-1")

    assert out["generated"] is False
    assert out["reason"] == "exam_inactive"
    assert out["exam"] == "sandbox-do-not-use"
    assert out["exam_id"] == "e-dead"


def _app(sb: SBStub, user_id: str = "u-1") -> FastAPI:
    app = FastAPI()
    app.include_router(study_os_api.router, prefix="/api")
    study_os_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {
        "id": user_id,
        "role": "user",
    }
    return app


def test_plan_generate_route_returns_422_not_500():
    """An aspirant gets the route's existing unprocessable shape, not a crash."""
    dead = _exam("e-dead", "sandbox-do-not-use", is_active=False)
    seed = _planner_seed([dead], [{"id": "u-1", "target_exam": "sandbox-do-not-use"}])
    # An existing plan grandfathers the onboarding-calibration gate, so the
    # request reaches the planner instead of short-circuiting on
    # ``calibration_required`` — which is what this test is about.
    seed["study_plans"] = [
        {"id": "p-1", "user_id": "u-1", "status": "active", "exam_id": "e-dead"}
    ]

    client = TestClient(_app(SBStub(seed)), raise_server_exceptions=False)
    r = client.post("/api/study/plan/generate")

    assert r.status_code == 422
    assert r.json()["detail"]["reason"] == "exam_inactive"


def test_topics_route_returns_empty_tree_for_inactive_exam():
    """``GET /topics`` degrades to its existing empty shape, not a 500."""
    dead = _exam("e-dead", "sandbox-do-not-use", is_active=False)
    seed = _planner_seed([dead], [{"id": "u-1", "target_exam": "sandbox-do-not-use"}])

    client = TestClient(_app(SBStub(seed)), raise_server_exceptions=False)
    r = client.get("/api/study/topics")

    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["exam_id"] is None
