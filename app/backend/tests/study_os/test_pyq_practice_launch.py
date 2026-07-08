"""PYQ v2 PR-9 (unit A) — planner task -> PYQ practice launch.

The server resolves mode/target/exam from the caller-owned study_tasks row (the
SOLE authority for exam context) and starts a topic PYQ practice attempt through
the shared start_pyq_practice assembly path. Reuses test_pyq_practice's _db seed
shape (projected + active PYQ pool) plus an owned study_tasks row.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import pyq_practice_launch as api
from app.core.auth import get_current_user
from app.study_os.pyq_practice_launch import (
    LAUNCH_PYQ_PRACTICE,
    pyq_practice_action,
    resolve_practice_payload,
)
from tests.study_os.test_pyq_practice import EXAM, TOPIC, _db, _q

TASK = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
OTHER_TOPIC = "99999999-9999-9999-9999-999999999999"


def _seed_task(sb, *, task_id=TASK, user_id="u1", topic_id=TOPIC, exam_id=EXAM):
    sb.db.setdefault("study_tasks", []).append({
        "id": task_id,
        "user_id": user_id,
        "exam_id": exam_id,
        "exam_phase_id": None,
        "subject_id": None,
        "topic_id": topic_id,
        "launch_context": None,
    })
    return sb


def _client(sb, user_id: str = "u1") -> TestClient:
    app = FastAPI()
    app.include_router(api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id}
    api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


def _launch(client, task_id=TASK):
    return client.post(f"/api/study/tasks/{task_id}/launch-pyq-practice")


# --- endpoint --------------------------------------------------------------

def test_owned_task_with_topic_and_exam_launches_practice():
    sb = _seed_task(_db([_q("q1")]))
    r = _launch(_client(sb))
    assert r.status_code == 200
    body = r.json()
    assert body["outcome"] == "ready"
    assert body["exam_id"] == EXAM
    assert body["source"] == "pyq_practice_topic"
    assert body["attempt_id"]


def test_task_not_owned_is_404():
    sb = _seed_task(_db([_q("q1")]), user_id="someone-else")
    assert _launch(_client(sb)).status_code == 404


def test_task_missing_is_404():
    sb = _db([_q("q1")])  # no study_tasks seeded
    assert _launch(_client(sb)).status_code == 404


def test_task_with_null_topic_is_409():
    sb = _seed_task(_db([_q("q1")]), topic_id=None)
    assert _launch(_client(sb)).status_code == 409


def test_task_with_null_exam_is_409():
    sb = _seed_task(_db([_q("q1")]), exam_id=None)
    assert _launch(_client(sb)).status_code == 409


def test_topic_with_no_projected_questions_is_409_empty_pool():
    # Task points at a topic that has no projected bank rows -> empty pool.
    sb = _seed_task(_db([_q("q1")]), topic_id=OTHER_TOPIC)
    r = _launch(_client(sb))
    assert r.status_code == 409
    assert "No projected PYQ questions" in r.json()["detail"]
    assert sb.db["mock_attempts"] == []


# --- resolve_practice_payload (pure) ---------------------------------------

def test_resolve_payload_both_present():
    payload = resolve_practice_payload({"topic_id": TOPIC, "exam_id": EXAM})
    assert payload == {"mode": "topic", "target_id": TOPIC, "exam_id": EXAM}


def test_resolve_payload_missing_returns_none():
    assert resolve_practice_payload({"topic_id": None, "exam_id": EXAM}) is None
    assert resolve_practice_payload({"topic_id": TOPIC, "exam_id": None}) is None
    assert resolve_practice_payload({}) is None


# --- pyq_practice_action (pure) --------------------------------------------

def test_action_for_pyq_practice_launch():
    action = pyq_practice_action(LAUNCH_PYQ_PRACTICE, TASK, None)
    assert action == {
        "action_url": f"/app/study/tasks/{TASK}/pyq-practice",
        "action_label": "Practice this topic",
    }


def test_action_none_for_other_or_missing_entity():
    assert pyq_practice_action("english_writing_session", TASK, None) is None
    assert pyq_practice_action(None, TASK, None) is None
    assert pyq_practice_action(LAUNCH_PYQ_PRACTICE, None, None) is None
