"""PYQ v2 PR-5/6 (slice B) — learner PYQ practice attempt assembly.

Practice selects VERIFIED, actively-projected PYQ rows from mock_question_bank by
paper / section / topic and starts an ad-hoc attempt through the generated
blueprint path. The resulting attempt is a normal mock attempt (served by the
existing /attempts/{id} routes) and carries the PR-4/slice-A render fidelity.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import mock_engine as mock_engine_api
from app.core.auth import get_current_user
from app.study_os import mock_engine as engine
from app.study_os import pyq_practice as svc
from tests.persona_questions._stub import SBStub

EXAM = "exam-1"
PHASE = "phase-1"
SECTION = "sec-1"
PAPER = "paper-1"
TOPIC = "topic-1"


def _opt(qid: str, i: int, correct: bool) -> dict:
    return {
        "id": f"opt-{qid}-{i}",
        "question_id": qid,
        "option_text": f"Option {i}",
        "option_index": i,
        "is_correct": correct,
        "source_label": f"({chr(96 + i)})",
        "display_order": i,
        "reviewer_status": "verified",
    }


def _q(qid: str, *, paper: str = PAPER, section: str = SECTION, topic: str = TOPIC, year: int = 2024) -> dict:
    return {
        "id": qid,
        "question_text": f"Question {qid}",
        "question_type": "mcq",
        "reviewer_status": "verified",
        "correct_option_id": f"opt-{qid}-2",
        "exam_id": EXAM,
        "subject_id": "sub-1",
        "pyq_question_id": f"pyqq-{qid}",
        "pyq_paper_id": paper,
        "section_id": section,
        "topic_id": topic,
        "pyq_year": year,
        "difficulty": "medium",
    }


def _db(questions: list[dict], *, active: bool = True, stimuli: list[dict] | None = None) -> SBStub:
    opts = [_opt(q["id"], i, i == 2) for q in questions for i in range(1, 5)]
    db = {
        "mock_question_bank": questions,
        "mock_question_options": opts,
        "mock_question_stimuli": stimuli or [],
        "pyq_mock_question_projections": [
            {"mock_question_id": q["id"], "sync_status": "active" if active else "stale"}
            for q in questions
        ],
        "exam_phase_sections": [{"id": SECTION, "exam_phase_id": PHASE}],
        "mock_generated_blueprints": [],
        "mock_attempts": [],
        "mock_attempt_responses": [],
    }
    return SBStub(db)


def test_paper_practice_starts_attempt_with_render_fidelity():
    sb = _db(
        [_q("q1"), _q("q2", year=2023)],
        stimuli=[{
            "id": "s1", "mock_question_id": "q1", "stimulus_type": "passage",
            "content_text": "A shared passage.", "language": "en", "display_order": 1,
        }],
    )
    res = svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id=PAPER, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 2
    assert res["source"] == "pyq_practice_paper"
    assert res["attempt_id"]

    state = engine.get_attempt(sb, "u1", res["attempt_id"])
    assert [q["question_id"] for q in state["questions"]] == ["q1", "q2"]  # newest year first
    q1 = next(q for q in state["questions"] if q["question_id"] == "q1")
    assert q1["stimuli"] and q1["stimuli"][0]["content_text"] == "A shared passage."
    assert [o["source_label"] for o in q1["options"]] == ["(a)", "(b)", "(c)", "(d)"]


def test_section_practice_filters_by_section():
    sb = _db([_q("q1", section=SECTION), _q("q2", section="other-section")])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="section", target_id=SECTION, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 1
    assert res["source"] == "pyq_practice_section"


def test_topic_practice_filters_by_topic():
    sb = _db([_q("q1", topic=TOPIC), _q("q2", topic="other-topic")])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 1
    assert res["source"] == "pyq_practice_topic"


def test_empty_pool_returns_no_writes():
    sb = _db([_q("q1", paper="other-paper")])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id=PAPER, exam_id=EXAM)
    assert res["outcome"] == "empty_pool"
    assert res["question_count"] == 0
    assert sb.db["mock_attempts"] == []
    assert sb.db["mock_attempt_responses"] == []


def test_stale_projection_is_excluded_from_practice():
    sb = _db([_q("q1")], active=False)
    res = svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id=PAPER, exam_id=EXAM)
    assert res["outcome"] == "empty_pool"


def test_unverified_bank_row_is_excluded():
    q = _q("q1")
    q["reviewer_status"] = "pending"
    sb = _db([q])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id=PAPER, exam_id=EXAM)
    assert res["outcome"] == "empty_pool"


def _client(sb: SBStub, user_id: str = "u1") -> TestClient:
    app = FastAPI()
    app.include_router(mock_engine_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id}
    mock_engine_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


def test_api_start_practice_ready_and_409_on_empty():
    sb = _db([_q("q1")])
    client = _client(sb)
    r = client.post("/api/study/mocks/practice/start", json={"mode": "paper", "target_id": PAPER, "exam_id": EXAM})
    assert r.status_code == 200
    assert r.json()["outcome"] == "ready"
    r2 = client.post("/api/study/mocks/practice/start", json={"mode": "paper", "target_id": "no-such-paper", "exam_id": EXAM})
    assert r2.status_code == 409


def test_api_rejects_unknown_mode():
    sb = _db([_q("q1")])
    client = _client(sb)
    r = client.post("/api/study/mocks/practice/start", json={"mode": "essay", "target_id": PAPER})
    assert r.status_code == 422
