"""Integer / numerical answer runtime contract (PYQ PR-11 / gate G11).

Covers the deterministic scorer, snapshot freeze, numeric persistence, resume,
result review fields, and the fail-closed guards (no answer, ungradeable spec,
unsupported type never scored 'correct').
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import mock_engine as mock_engine_api
from app.core.auth import get_current_user
from app.study_os import mock_engine as svc
from tests.persona_questions._stub import SBStub


def _integer_question(qid: str = "intq-1", *, value=42, tolerance=0, with_spec=True) -> dict:
    q = {
        "id": qid,
        "exam_family": "TEST",
        "question_text": "What is 6 x 7?",
        "question_type": "integer",
        "difficulty": "easy",
        "marks": 1.0,
        "negative_marks": 0.25,
        "correct_option_id": None,
        "explanation": "6 x 7 = 42.",
        "reviewer_status": "published",
        "options": [],
    }
    if with_spec:
        q["numeric_answer"] = {"value": value, "tolerance": tolerance}
    return q


def _seed(question: dict, *, negative_marking: bool = True) -> tuple[SBStub, dict]:
    template = {
        "id": "tmpl-int",
        "slug": "int-mock",
        "name": "Integer Mock",
        "exam_family": "TEST",
        "total_questions": 1,
        "duration_sec": 300,
        "negative_marking": negative_marking,
        "marks_per_correct": 1.0,
        "marks_per_wrong": 0.25,
        "config": {"question_ids": [question["id"]]},
        "status": "active",
    }
    db = {
        "mock_templates": [template],
        "mock_question_bank": [question],
        "mock_question_options": [],
        "mock_attempts": [],
        "mock_attempt_responses": [],
        "mock_tests": [],
    }
    return SBStub(db), template


def _answer_and_submit(sb, question_id, numeric_answer):
    start = svc.start_attempt(sb, "user-1", "int-mock")
    attempt_id = start["attempt_id"]
    if numeric_answer is not None:
        svc.save_answer(sb, "user-1", attempt_id, question_id, None, False, 1, 10, numeric_answer=numeric_answer)
    svc.submit_attempt(sb, "user-1", attempt_id)
    return attempt_id, svc.get_result(sb, "user-1", attempt_id)


def test_exact_numeric_match_is_correct():
    sb, _ = _seed(_integer_question(value=42, tolerance=0))
    _, result = _answer_and_submit(sb, "intq-1", 42)
    assert result["total_correct"] == 1
    assert result["total_wrong"] == 0
    assert result["total_unattempted"] == 0
    assert result["per_question"][0]["is_correct"] is True


def test_within_tolerance_is_correct():
    sb, _ = _seed(_integer_question(value=3.14, tolerance=0.02))
    _, result = _answer_and_submit(sb, "intq-1", 3.15)  # |3.15-3.14|=0.01 <= 0.02
    assert result["total_correct"] == 1
    assert result["per_question"][0]["is_correct"] is True


def test_outside_tolerance_is_wrong():
    sb, _ = _seed(_integer_question(value=42, tolerance=1))
    _, result = _answer_and_submit(sb, "intq-1", 45)
    assert result["total_wrong"] == 1
    assert result["total_correct"] == 0
    assert result["per_question"][0]["is_correct"] is False


def test_no_answer_is_unattempted():
    sb, _ = _seed(_integer_question())
    _, result = _answer_and_submit(sb, "intq-1", None)
    assert result["total_unattempted"] == 1
    assert result["per_question"][0]["is_correct"] is None


def test_result_exposes_correct_value_and_learner_value():
    sb, _ = _seed(_integer_question(value=42, tolerance=0))
    _, result = _answer_and_submit(sb, "intq-1", 40)
    pq = result["per_question"][0]
    assert pq["question_type"] == "integer"
    assert float(pq["numeric_answer"]) == 40
    assert pq["correct_numeric_answer"] == 42
    assert pq["numeric_tolerance"] == 0


def test_snapshot_freezes_spec_and_attempt_does_not_leak_correct_value():
    sb, _ = _seed(_integer_question(value=42, tolerance=0))
    start = svc.start_attempt(sb, "user-1", "int-mock")
    attempt_id = start["attempt_id"]
    # The learner-facing attempt view must never carry the correct value.
    view = svc.get_attempt(sb, "user-1", attempt_id)
    q = view["questions"][0]
    assert q["question_type"] == "integer"
    assert "numeric_answer" in q and q["numeric_answer"] is None  # nothing typed yet
    assert "correct_numeric_answer" not in q
    # But the frozen response snapshot DOES hold the spec (for scoring/review).
    resp = sb.db["mock_attempt_responses"][0]
    assert resp["question_snapshot"]["numeric_answer"] == {"value": 42.0, "tolerance": 0.0}


def test_resume_restores_learner_numeric_answer_without_leaking_answer():
    sb, _ = _seed(_integer_question(value=42, tolerance=0))
    start = svc.start_attempt(sb, "user-1", "int-mock")
    attempt_id = start["attempt_id"]
    svc.save_answer(sb, "user-1", attempt_id, "intq-1", None, False, 1, 5, numeric_answer=17)
    view = svc.get_attempt(sb, "user-1", attempt_id)
    q = view["questions"][0]
    assert float(q["numeric_answer"]) == 17
    assert "correct_numeric_answer" not in q


def test_fail_closed_when_integer_question_has_no_spec():
    """An integer question frozen without a valid numeric_answer spec must never
    be scored 'correct' even if the learner types something — fail closed."""
    sb, _ = _seed(_integer_question(with_spec=False))
    _, result = _answer_and_submit(sb, "intq-1", 42)
    assert result["total_correct"] == 0
    assert result["total_unattempted"] == 1
    assert result["per_question"][0]["is_correct"] is None


def test_mcq_snapshot_has_null_numeric_answer():
    """MCQ questions must not carry a numeric_answer spec in the snapshot."""
    mcq = {
        "id": "mcq-1",
        "exam_family": "TEST",
        "question_text": "Pick one",
        "question_type": "mcq",
        "difficulty": "easy",
        "marks": 1.0,
        "negative_marks": 0.25,
        "correct_option_id": "opt-mcq-1-2",
        "reviewer_status": "published",
        "options": [
            {"id": f"opt-mcq-1-{i}", "question_id": "mcq-1", "option_text": f"O{i}", "option_index": i, "is_correct": i == 2}
            for i in range(1, 5)
        ],
    }
    template = {
        "id": "tmpl-mcq", "slug": "mcq-mock", "name": "MCQ", "exam_family": "TEST",
        "total_questions": 1, "duration_sec": 300, "negative_marking": True,
        "marks_per_correct": 1.0, "marks_per_wrong": 0.25,
        "config": {"question_ids": ["mcq-1"]}, "status": "active",
    }
    sb = SBStub({
        "mock_templates": [template], "mock_question_bank": [mcq],
        "mock_question_options": mcq["options"],
        "mock_attempts": [], "mock_attempt_responses": [], "mock_tests": [],
    })
    start = svc.start_attempt(sb, "user-1", "mcq-mock")
    resp = sb.db["mock_attempt_responses"][0]
    assert resp["question_snapshot"]["numeric_answer"] is None


def test_api_answer_accepts_numeric_answer():
    sb, _ = _seed(_integer_question(value=42, tolerance=0))
    app = FastAPI()
    app.include_router(mock_engine_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-1"}
    mock_engine_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    client = TestClient(app)
    start = client.post("/api/study/mocks/attempts/start", json={"template_slug": "int-mock"})
    attempt_id = start.json()["attempt_id"]
    r = client.post(
        f"/api/study/mocks/attempts/{attempt_id}/answer",
        json={"question_id": "intq-1", "numeric_answer": 42, "client_seq": 1, "time_spent_sec": 8},
    )
    assert r.status_code == 200
    resp = sb.db["mock_attempt_responses"][0]
    assert float(resp["numeric_answer"]) == 42
