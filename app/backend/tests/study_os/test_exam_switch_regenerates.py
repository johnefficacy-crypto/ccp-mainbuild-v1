"""D5 — switching target exam must not leave the user with zero active plans.

``PUT /api/study/target-exam?confirm_archive=true`` archived the active plan
(``study_os.py:293``) and returned ``{"ok": True}`` without regenerating.
``archived`` is terminal — nothing writes ``study_plans.status`` back to
``'active'`` — and both regen entry points require an active plan, so the user
had no automatic route back. Three live plans were archived this way on
2026-07-13 and the platform planned for nobody for two months.

The switch now attempts generation for the NEW exam in the same request, as a
best-effort step that reports its outcome without ever failing the switch.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import study_os as study_os_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub

_OLD = "11111111-1111-1111-1111-111111111111"
_NEW = "22222222-2222-2222-2222-222222222222"


def _exam(exam_id: str, slug: str) -> dict[str, Any]:
    return {
        "id": exam_id,
        "slug": slug,
        "name": f"Exam {slug}",
        "exam_type": "recruitment",
        "is_active": True,
    }


def _seed(
    *,
    with_active_plan: bool,
    plannable_new_exam: bool = True,
    calibrated_for_new: bool = True,
) -> dict[str, Any]:
    """Two exams; the NEW one carries locked coverage when *plannable_new_exam*.

    ``study_plans`` seeded with an active plan for the OLD exam when requested —
    that is the row the switch must archive. The user is given a plan row for the
    new exam only via generation, never by the fixture.

    ``calibrated_for_new`` seeds a completed ``user_exam_calibration`` gate for
    the NEW exam. Without it the planner legitimately declines with
    ``calibration_required`` (the gate is a pre-first-plan interstitial and the
    user has no plan for the new exam to be grandfathered by), which is the
    common real-world path and is covered by its own test below.
    """
    seed: dict[str, Any] = {
        "profiles": [{"id": "u-1", "target_exam": _OLD}],
        "exams": [_exam(_OLD, "old-exam"), _exam(_NEW, "new-exam")],
        "exam_cycles": [
            {"id": "cyc-old", "exam_id": _OLD, "exam_start": "2099-09-15"},
            {"id": "cyc-new", "exam_id": _NEW, "exam_start": "2099-10-20"},
        ],
        "topics": [
            {"id": "t1", "name": "Percentage", "subject_id": "s1", "is_active": True}
        ],
        "subjects": [{"id": "s1", "name": "Quant"}],
        "exam_topic_coverage": [
            {
                "id": "c-old",
                "exam_id": _OLD,
                "exam_cycle_id": "cyc-old",
                "exam_phase_id": "ph-old",
                "topic_id": "t1",
                "exam_priority_score": 80,
                "is_high_yield": True,
                "reviewer_status": "locked",
            }
        ],
        "aspirant_preferences": [{"id": "ap-1", "user_id": "u-1", "target_exams": ["old-exam"]}],
    }
    if calibrated_for_new:
        seed["user_exam_calibration"] = [
            {
                "id": "cal-new",
                "user_id": "u-1",
                "exam_id": _NEW,
                "status": "completed",
                "required_subject_set_hash": None,
                "attempts_used": 1,
            }
        ]
    if plannable_new_exam:
        seed["exam_topic_coverage"].append(
            {
                "id": "c-new",
                "exam_id": _NEW,
                "exam_cycle_id": "cyc-new",
                "exam_phase_id": "ph-new",
                "topic_id": "t1",
                "exam_priority_score": 75,
                "is_high_yield": True,
                "reviewer_status": "locked",
            }
        )
    if with_active_plan:
        seed["study_plans"] = [
            {
                "id": "p-old",
                "user_id": "u-1",
                "status": "active",
                "exam_id": _OLD,
                "title": "Old plan",
            }
        ]
    return seed


def _client(sb: SBStub, user_id: str = "u-1") -> TestClient:
    app = FastAPI()
    app.include_router(study_os_api.router, prefix="/api")
    study_os_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id, "role": "user"}
    return TestClient(app, raise_server_exceptions=False)


def _plans(sb: SBStub) -> list[dict[str, Any]]:
    return list(sb.db.get("study_plans") or [])


def _active(sb: SBStub) -> list[dict[str, Any]]:
    return [p for p in _plans(sb) if p.get("status") == "active"]


# ── 6. the one that matters ────────────────────────────────────────────────


def test_exactly_one_active_plan_after_switch():
    """A second active row would make the nightly sweep nondeterministic.

    ``regenerate_stale_plans`` iterates every ``status='active'`` row and
    ``_persist`` reuses "the" active plan via ``_active_plan``, which takes
    ``limit(1)`` — with two active rows, which one gets refreshed depends on
    row order. Assert the count, not merely that one exists.
    """
    sb = SBStub(_seed(with_active_plan=True))
    r = _client(sb).put(f"/api/study/target-exam?confirm_archive=true", json={"exam_id": _NEW})

    assert r.status_code == 200
    active = _active(sb)
    assert len(active) == 1, f"expected exactly one active plan, got {active}"
    assert str(active[0].get("exam_id")) == _NEW


# ── 1-2. archival + regeneration ───────────────────────────────────────────


def test_switch_archives_old_plan_and_creates_one_for_the_new_exam():
    sb = SBStub(_seed(with_active_plan=True))
    r = _client(sb).put(f"/api/study/target-exam?confirm_archive=true", json={"exam_id": _NEW})

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["plan"]["created"] is True
    assert body["plan"]["reason"] is None

    old = [p for p in _plans(sb) if p.get("id") == "p-old"][0]
    assert old["status"] == "archived"
    assert old.get("end_date")


def test_archived_plan_exam_id_is_not_repointed():
    """The fix must not rewrite the old plan onto the new exam."""
    sb = SBStub(_seed(with_active_plan=True))
    _client(sb).put(f"/api/study/target-exam?confirm_archive=true", json={"exam_id": _NEW})

    old = [p for p in _plans(sb) if p.get("id") == "p-old"][0]
    assert str(old.get("exam_id")) == _OLD


# ── 3. generation declines ─────────────────────────────────────────────────


def test_generation_refusal_passes_reason_through_and_writes_no_plan():
    """New exam has no locked coverage → planner refuses; switch still succeeds."""
    sb = SBStub(_seed(with_active_plan=True, plannable_new_exam=False))  # gate satisfied
    r = _client(sb).put(f"/api/study/target-exam?confirm_archive=true", json={"exam_id": _NEW})

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["plan"]["created"] is False
    # Verbatim planner vocabulary, not a string invented by the route.
    assert body["plan"]["reason"] == "no_locked_coverage"
    assert _active(sb) == []
    # The switch itself still happened.
    assert sb.db["profiles"][0]["target_exam"] == _NEW


def test_uncalibrated_new_exam_reports_calibration_required():
    """The common real-world switch: the user has not calibrated for the new exam.

    The calibration gate is a pre-first-plan interstitial, and a freshly-chosen
    exam has no plan to grandfather the user. Generation therefore declines and
    the switch reports the gate's own reason verbatim so the client can route
    the user into calibration — rather than leaving them on a dead Study Plan
    page wondering where their tasks went.
    """
    sb = SBStub(_seed(with_active_plan=True, calibrated_for_new=False))
    r = _client(sb).put(
        "/api/study/target-exam?confirm_archive=true", json={"exam_id": _NEW}
    )

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["plan"]["created"] is False
    assert body["plan"]["reason"] == "calibration_required"
    assert _active(sb) == []
    # The switch itself is complete regardless.
    assert sb.db["profiles"][0]["target_exam"] == _NEW


# ── 4. generation raises ───────────────────────────────────────────────────


def test_generation_exception_does_not_fail_the_switch(monkeypatch, caplog):
    sb = SBStub(_seed(with_active_plan=True))

    def _boom(*_a: Any, **_k: Any) -> dict[str, Any]:
        raise RuntimeError("planner exploded")

    monkeypatch.setattr(study_os_api, "_apply_plan_envelope", _boom)

    with caplog.at_level("ERROR"):
        r = _client(sb).put(
            f"/api/study/target-exam?confirm_archive=true", json={"exam_id": _NEW}
        )

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["plan"]["created"] is False
    assert body["plan"]["reason"] == "error"
    # The exception did not reach the client, but it is on the record.
    assert "plan regeneration failed" in caplog.text
    # The switch still landed.
    assert sb.db["profiles"][0]["target_exam"] == _NEW


# ── 5. no prior plan ───────────────────────────────────────────────────────


def test_switch_with_no_existing_plan_still_generates():
    """Nothing to archive — generation must still run."""
    sb = SBStub(_seed(with_active_plan=False))
    r = _client(sb).put(f"/api/study/target-exam?confirm_archive=true", json={"exam_id": _NEW})

    assert r.status_code == 200
    assert r.json()["plan"]["created"] is True
    active = _active(sb)
    assert len(active) == 1
    assert str(active[0].get("exam_id")) == _NEW


# ── 7. unconfirmed switch is unchanged ─────────────────────────────────────


def test_switch_without_confirm_archive_still_409s_and_changes_nothing():
    """Pin today's behaviour: no archival, no regeneration, no target write."""
    sb = SBStub(_seed(with_active_plan=True))
    r = _client(sb).put("/api/study/target-exam", json={"exam_id": _NEW})

    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "ACTIVE_PLAN_EXISTS"
    old = [p for p in _plans(sb) if p.get("id") == "p-old"][0]
    assert old["status"] == "active"
    assert sb.db["profiles"][0]["target_exam"] == _OLD
    assert len(_active(sb)) == 1


def test_switch_to_same_exam_needs_no_confirmation_and_regenerates():
    """Re-selecting the current exam never hits the 409 path."""
    sb = SBStub(_seed(with_active_plan=True))
    r = _client(sb).put("/api/study/target-exam", json={"exam_id": _OLD})

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    # Nothing was archived — the plan is for the exam we re-selected.
    old = [p for p in _plans(sb) if p.get("id") == "p-old"][0]
    assert old["status"] == "active"
    assert body["plan"]["created"] is True
    assert len(_active(sb)) == 1
