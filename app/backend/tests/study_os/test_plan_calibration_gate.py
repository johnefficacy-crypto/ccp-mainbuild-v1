"""Backend plan-calibration gate (PR #778, FIX B).

The onboarding-calibration gate must NOT be frontend-only: the plan
entrypoints — ``POST /plan/generate``, ``GET/POST /plan/draft`` and
``POST /plan/apply`` — must themselves short-circuit with the stable
``calibration_required`` envelope (HTTP 200, no generation, no mutation) when a
first-plan calibration is still pending, and must proceed to the planner once
ANY unlock path holds:

  * a 'completed' gate row,
  * a 'skipped' gate row,
  * an existing plan for the exam (grandfathered).

These assertions are kept independent of planner internals by monkeypatching
``generate_plan`` / ``compute_draft_plan`` / ``apply_plan`` to a sentinel so we
can assert *whether* the planner was invoked, not what it produced.

Reuses the SBStub + FastAPI TestClient harness from the sibling suites.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import study_os as study_os_api
from app.core.auth import get_current_user
from app.study_os import calibration
from tests.persona_questions._stub import SBStub

EXAM_ID = "55555555-5555-4555-8555-555555555551"
S_QUANT = "66666666-6666-4666-8666-666666666661"
S_ENG = "66666666-6666-4666-8666-666666666662"
T_QUANT = "77777777-7777-4777-8777-777777777771"
T_ENG = "77777777-7777-4777-8777-777777777772"


@pytest.fixture(autouse=True)
def _clear_exam_cache():
    # resolve_exam_by_slug/by_id memoise in a module-level cache; clear it so a
    # unique-per-test exam row is never shadowed by a sibling test.
    import app.exam_intelligence.lookup as lookup

    lookup._EXAM_CACHE.clear()
    yield
    lookup._EXAM_CACHE.clear()


def _app(sb: SBStub, user_id: str = "u-1") -> FastAPI:
    app = FastAPI()
    app.include_router(study_os_api.router, prefix="/api")
    study_os_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id, "role": "user"}
    return app


def _client(sb: SBStub, user_id: str = "u-1") -> TestClient:
    return TestClient(_app(sb, user_id))


def _seed(*, unique_slug: str | None = None) -> dict:
    """Exam with two locked subjects and NO validated mastery → both required.

    With no gate row and no existing plan this fixture makes
    ``calibration_required`` True, i.e. the gate is ENGAGED.
    """
    slug = unique_slug or f"exam-{uuid.uuid4().hex[:8]}"
    return {
        "profiles": [{"id": "u-1", "target_exam": slug}],
        "exams": [{"id": EXAM_ID, "slug": slug, "name": "Test Exam", "is_active": True}],
        "exam_topic_coverage": [
            {"id": "cov-q", "exam_id": EXAM_ID, "topic_id": T_QUANT, "reviewer_status": "locked"},
            {"id": "cov-e", "exam_id": EXAM_ID, "topic_id": T_ENG, "reviewer_status": "locked"},
        ],
        "topics": [
            {"id": T_QUANT, "subject_id": S_QUANT, "name": "Quant", "is_active": True},
            {"id": T_ENG, "subject_id": S_ENG, "name": "English", "is_active": True},
        ],
        "subjects": [
            {"id": S_QUANT, "name": "Quant"},
            {"id": S_ENG, "name": "English"},
        ],
    }


_SENTINEL = {"generated": True, "applied": True, "__planner_called__": True, "tasks": []}


@pytest.fixture
def _spy_planner(monkeypatch):
    """Replace the three planner entrypoints with a call-recording sentinel."""
    calls: dict[str, int] = {"generate": 0, "draft": 0, "apply": 0}

    def _gen(*_a, **_k):
        calls["generate"] += 1
        return dict(_SENTINEL)

    def _draft(*_a, **_k):
        calls["draft"] += 1
        return dict(_SENTINEL)

    def _apply(*_a, **_k):
        calls["apply"] += 1
        return dict(_SENTINEL)

    monkeypatch.setattr(study_os_api, "generate_plan", _gen)
    monkeypatch.setattr(study_os_api, "compute_draft_plan", _draft)
    monkeypatch.setattr(study_os_api, "apply_plan", _apply)
    return calls


# Each plan entrypoint, as (method, path, planner-call-key).
_ENDPOINTS = [
    ("post", "/api/study/plan/generate", "generate"),
    ("get", "/api/study/plan/draft", "draft"),
    ("post", "/api/study/plan/draft", "draft"),
    ("post", "/api/study/plan/apply", "apply"),
]


def _call(client: TestClient, method: str, path: str):
    return client.get(path) if method == "get" else client.post(path)


# ───────────────── gate ENGAGED: required set, no gate, no plan ──────────────

@pytest.mark.parametrize("method,path,key", _ENDPOINTS)
def test_plan_endpoint_blocks_when_calibration_required(_spy_planner, method, path, key):
    sb = SBStub(_seed())
    # Precondition sanity: the gate really is engaged for this fixture.
    assert calibration.calibration_required(sb, "u-1", EXAM_ID) is True

    r = _call(_client(sb), method, path)
    assert r.status_code == 200
    body = r.json()
    assert body["calibration_required"] is True
    assert body["generated"] is False
    assert body["reason"] == "calibration_required"
    assert str(body["exam_id"]) == EXAM_ID
    # The planner was NOT invoked and nothing was mutated.
    assert _spy_planner[key] == 0
    assert sb.db.get("study_plans", []) == []
    assert sb.db.get("study_tasks", []) == []
    assert sb.db.get("study_plan_versions", []) == []


# ───────────── unlock path 1: a 'completed' gate lets the planner run ────────

@pytest.mark.parametrize("method,path,key", _ENDPOINTS)
def test_plan_endpoint_proceeds_with_completed_gate(_spy_planner, method, path, key):
    seed = _seed()
    seed["user_exam_calibration"] = [
        {
            "id": "cal-c", "user_id": "u-1", "exam_id": EXAM_ID, "status": "completed",
            "required_subject_set_hash": calibration.required_subject_set_hash([S_QUANT, S_ENG]),
            "attempts_used": 1, "completed_at": "2026-06-01T00:00:00+00:00",
        }
    ]
    sb = SBStub(seed)
    r = _call(_client(sb), method, path)
    assert r.status_code == 200
    assert r.json().get("calibration_required") is not True
    assert _spy_planner[key] == 1


# ───────────── unlock path 2: a 'skipped' gate lets the planner run ──────────

@pytest.mark.parametrize("method,path,key", _ENDPOINTS)
def test_plan_endpoint_proceeds_with_skipped_gate(_spy_planner, method, path, key):
    seed = _seed()
    seed["user_exam_calibration"] = [
        {"id": "cal-s", "user_id": "u-1", "exam_id": EXAM_ID, "status": "skipped"}
    ]
    sb = SBStub(seed)
    r = _call(_client(sb), method, path)
    assert r.status_code == 200
    assert r.json().get("calibration_required") is not True
    assert _spy_planner[key] == 1


# ──────── unlock path 3: an existing plan grandfathers the user through ───────

@pytest.mark.parametrize("method,path,key", _ENDPOINTS)
def test_plan_endpoint_proceeds_with_existing_plan(_spy_planner, method, path, key):
    seed = _seed()
    # Existing plan for THIS exam (matched via the exam_id column) → grandfathered
    # even though there is no gate row and the required set is non-empty.
    seed["study_plans"] = [
        {"id": "p-1", "user_id": "u-1", "exam_id": EXAM_ID, "status": "active"}
    ]
    sb = SBStub(seed)
    # Sanity: the existing plan flips calibration_required off.
    assert calibration.calibration_required(sb, "u-1", EXAM_ID) is False

    r = _call(_client(sb), method, path)
    assert r.status_code == 200
    assert r.json().get("calibration_required") is not True
    assert _spy_planner[key] == 1


# ──────── unlock path 3b: a legacy slug-only plan grandfathers via HTTP ───────

def test_plan_endpoint_proceeds_with_legacy_slug_plan(_spy_planner):
    slug = "legacy-grandfather-exam"
    seed = _seed(unique_slug=slug)
    # Legacy row: NULL exam_id, slug stored in the free-text target_exam column.
    seed["study_plans"] = [
        {"id": "p-legacy", "user_id": "u-1", "exam_id": None, "target_exam": slug, "status": "active"}
    ]
    sb = SBStub(seed)
    assert calibration.calibration_required(sb, "u-1", EXAM_ID) is False

    r = _call(_client(sb), "post", "/api/study/plan/apply")
    assert r.status_code == 200
    assert r.json().get("calibration_required") is not True
    assert _spy_planner["apply"] == 1


# ───────────── fail closed: a calibration read failure → 503, no generation ───

def _failing_read_sb(seed: dict, failing_table: str) -> SBStub:
    """SBStub whose ``<failing_table>`` raises on ``execute()`` (read failure)."""
    sb = SBStub(seed)
    original_table = sb.table

    class _FailingQuery:
        def __init__(self, inner, table_name):
            self._inner = inner
            self._table = table_name

        def __getattr__(self, name):
            attr = getattr(self._inner, name)
            if name == "execute":
                def _exec():
                    if self._table == failing_table:
                        raise RuntimeError("simulated read failure")
                    return attr()
                return _exec

            def _passthrough(*a, **kw):
                self._inner = attr(*a, **kw)
                return self

            return _passthrough

    sb.table = lambda name: _FailingQuery(original_table(name), name)  # type: ignore[assignment]
    return sb


@pytest.mark.parametrize("method,path,key", _ENDPOINTS)
def test_plan_endpoint_returns_503_when_calibration_read_fails(_spy_planner, method, path, key):
    # A coverage read failure makes calibration UNKNOWN; the gate must fail
    # closed (503) rather than silently unlock generation.
    sb = _failing_read_sb(_seed(), "exam_topic_coverage")
    r = _call(_client(sb), method, path)
    assert r.status_code == 503
    assert r.json()["detail"]["reason"] == "calibration_check_failed"
    assert _spy_planner[key] == 0


def test_get_self_assessment_reports_check_failed_when_read_fails():
    sb = _failing_read_sb(_seed(), "exam_topic_coverage")
    r = _client(sb).get("/api/study/self-assessment")
    assert r.status_code == 200
    body = r.json()
    assert body["calibration_check_failed"] is True
    assert body["calibrated"] is False


def test_generate_returns_503_when_target_resolution_fails(_spy_planner):
    # A transient profiles read failure must fail closed (503), NOT be mistaken
    # for "no target exam → proceed" and let the planner generate an uncalibrated
    # first plan on a re-resolve. (POST /plan/generate has no _require_canonical
    # short-circuit, so the gate's resolution is the first thing to run.)
    sb = _failing_read_sb(_seed(), "profiles")
    r = _client(sb).post("/api/study/plan/generate")
    assert r.status_code == 503
    assert r.json()["detail"]["reason"] == "calibration_check_failed"
    assert _spy_planner["generate"] == 0


def test_planner_rejects_mismatched_expected_exam_id():
    # TOCTOU guard: the gate validated calibration for expected_exam_id, but the
    # planner resolves a DIFFERENT target (the user switched exams concurrently).
    # The planner must refuse to generate/persist for the unchecked exam.
    from app.study_os.planner import generate_plan

    sb = SBStub(_seed())  # resolves to EXAM_ID
    other_exam = "99999999-9999-4999-8999-999999999999"
    result = generate_plan(sb, "u-1", expected_exam_id=other_exam)
    assert result["generated"] is False
    assert result["reason"] == "target_changed"
    # nothing was generated/persisted for the switched-to exam
    assert sb.db.get("study_plans", []) == []
    assert sb.db.get("study_tasks", []) == []


def test_planner_rejects_resolved_exam_when_gate_saw_no_target():
    # No-target → exam B race: the gate checked and found NO target exam (so it
    # hands the planner the NO_TARGET_SENTINEL), but a target appeared before the
    # planner resolved. The planner must reject the newly-resolved exam as
    # target_changed and persist nothing — not generate an unchecked first plan.
    from app.study_os.planner import generate_plan

    sb = SBStub(_seed())  # resolves to EXAM_ID — the "exam B" that appeared
    result = generate_plan(sb, "u-1", expected_exam_id=calibration.NO_TARGET_SENTINEL)
    assert result["generated"] is False
    assert result["reason"] == "target_changed"
    assert sb.db.get("study_plans", []) == []
    assert sb.db.get("study_tasks", []) == []
    assert sb.db.get("study_plan_versions", []) == []
    assert sb.db.get("study_adaptation_events", []) == []


def test_generate_no_target_user_returns_422_not_a_plan():
    # A genuinely no-target user must still get a clean no_target_exam (422), not a
    # 500 and not a generated plan. Uses the REAL planner (no spy).
    seed = _seed()
    seed["profiles"] = [{"id": "u-1", "target_exam": None}]
    seed.pop("exams", None)
    sb = SBStub(seed)
    r = _client(sb).post("/api/study/plan/generate")
    assert r.status_code == 422
    assert r.json()["detail"]["reason"] == "no_target_exam"
    assert sb.db.get("study_plans", []) == []


def test_get_grandfathered_status_is_none_during_coverage_outage():
    # An existing-plan user with NO gate row is grandfathered (calibrated), but a
    # best-effort coverage outage must NOT mislabel them status='completed' — they
    # never completed calibration. status must stay 'none'.
    seed = _seed()
    seed["study_plans"] = [
        {"id": "p1", "user_id": "u-1", "exam_id": EXAM_ID, "status": "active"}
    ]
    sb = _failing_read_sb(seed, "exam_topic_coverage")
    body = _client(sb).get("/api/study/self-assessment").json()
    assert body["calibrated"] is True
    assert body.get("calibration_check_failed") is not True
    assert body["status"] == "none"


def test_generate_proceeds_for_completed_gate_despite_coverage_outage(_spy_planner):
    # Positive unlock evidence (completed gate) must win over an unrelated
    # coverage outage — the user is already definitively unlocked.
    seed = _seed()
    seed["user_exam_calibration"] = [
        {
            "id": "cal-c", "user_id": "u-1", "exam_id": EXAM_ID, "status": "completed",
            "required_subject_set_hash": "stale-hash", "attempts_used": 1,
        }
    ]
    sb = _failing_read_sb(seed, "exam_topic_coverage")
    r = _client(sb).post("/api/study/plan/generate")
    assert r.status_code == 200
    assert r.json().get("calibration_required") is not True
    assert _spy_planner["generate"] == 1


# ───────────── empty required set: nothing to calibrate → proceed ────────────

@pytest.mark.parametrize("method,path,key", _ENDPOINTS)
def test_plan_endpoint_proceeds_when_required_set_empty(_spy_planner, method, path, key):
    seed = _seed()
    # Both locked topics already have validated mastery → required set empty →
    # calibration_required False with no gate and no plan.
    seed["user_topic_mastery"] = [
        {"id": "m-q", "user_id": "u-1", "topic_id": T_QUANT, "mastery_score": 70.0},
        {"id": "m-e", "user_id": "u-1", "topic_id": T_ENG, "mastery_score": 65.0},
    ]
    sb = SBStub(seed)
    assert calibration.calibration_required(sb, "u-1", EXAM_ID) is False

    r = _call(_client(sb), method, path)
    assert r.status_code == 200
    assert r.json().get("calibration_required") is not True
    assert _spy_planner[key] == 1
