"""PYQ v2 PR-5/6 (slice B) — learner PYQ practice attempt assembly.

Practice selects VERIFIED, actively-projected PYQ rows from mock_question_bank by
paper / section / topic and starts an ad-hoc attempt through the generated
blueprint path. The resulting attempt is a normal mock attempt (served by the
existing /attempts/{id} routes) and carries the PR-4/slice-A render fidelity.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import mock_engine as mock_engine_api
from app.core.auth import get_current_user
from app.study_os import mock_engine as engine
from app.study_os import pyq_practice as svc
from tests.persona_questions._stub import SBStub

EXAM = "11111111-1111-1111-1111-111111111111"
EXAM_B = "1b1b1b1b-1b1b-1b1b-1b1b-1b1b1b1b1b1b"
PHASE = "22222222-2222-2222-2222-222222222222"
SECTION = "33333333-3333-3333-3333-333333333333"
PAPER = "44444444-4444-4444-4444-444444444444"
TOPIC = "55555555-5555-5555-5555-555555555555"


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


def _q(qid: str, *, paper: str = PAPER, section: str = SECTION, topic: str = TOPIC, year: int = 2024, exam: str = EXAM) -> dict:
    return {
        "id": qid,
        "question_text": f"Question {qid}",
        "question_type": "mcq",
        "reviewer_status": "verified",
        "correct_option_id": f"opt-{qid}-2",
        "exam_id": exam,
        "subject_id": "sub-1",
        "pyq_question_id": f"pyqq-{qid}",
        "pyq_paper_id": paper,
        "section_id": section,
        "topic_id": topic,
        "pyq_year": year,
        "difficulty": "medium",
    }


def _db(questions: list[dict], *, active: bool = True, stimuli: list[dict] | None = None, pyq_order: dict[str, int] | None = None) -> SBStub:
    opts = [_opt(q["id"], i, i == 2) for q in questions for i in range(1, 5)]
    pyq_order = pyq_order or {}
    pyq_questions = [
        {
            "id": q["pyq_question_id"],
            "display_order": pyq_order.get(q["id"]),
            "question_number": pyq_order.get(q["id"]),
            "source_question_ref": str(pyq_order[q["id"]]) if q["id"] in pyq_order else None,
        }
        for q in questions
    ]
    db = {
        "mock_question_bank": questions,
        "mock_question_options": opts,
        "mock_question_stimuli": stimuli or [],
        "pyq_questions": pyq_questions,
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
        [_q("q1"), _q("q2")],
        stimuli=[{
            "id": "s1", "mock_question_id": "q1", "stimulus_type": "passage",
            "content_text": "A shared passage.", "language": "en", "display_order": 1,
        }],
        pyq_order={"q1": 1, "q2": 2},
    )
    res = svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id=PAPER, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 2
    assert res["source"] == "pyq_practice_paper"
    assert res["exam_id"] == EXAM
    assert res["attempt_id"]

    state = engine.get_attempt(sb, "u1", res["attempt_id"])
    q1 = next(q for q in state["questions"] if q["question_id"] == "q1")
    assert q1["stimuli"] and q1["stimuli"][0]["content_text"] == "A shared passage."
    assert [o["source_label"] for o in q1["options"]] == ["(a)", "(b)", "(c)", "(d)"]


def test_paper_practice_preserves_source_printed_order_not_bank_id():
    # bank id order (q1, q2) is the REVERSE of the source printed order.
    sb = _db([_q("q1"), _q("q2")], pyq_order={"q1": 2, "q2": 1})
    res = svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id=PAPER, exam_id=EXAM)
    state = engine.get_attempt(sb, "u1", res["attempt_id"])
    # served in source display_order → q2 (display_order 1) before q1 (2)
    assert [q["question_id"] for q in state["questions"]] == ["q2", "q1"]


def test_section_practice_filters_by_section():
    sb = _db([_q("q1", section=SECTION), _q("q2", section="99999999-9999-9999-9999-999999999999")], pyq_order={"q1": 1, "q2": 1})
    res = svc.start_pyq_practice(sb, user_id="u1", mode="section", target_id=SECTION, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 1
    assert res["source"] == "pyq_practice_section"


def test_topic_practice_requires_exam_id():
    sb = _db([_q("q1")])
    try:
        svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=TOPIC)
        raise AssertionError("expected PracticeInputError for topic without exam_id")
    except svc.PracticeInputError:
        pass


def test_topic_practice_does_not_mix_exams():
    # same topic_id shared across two exams; exam_id scopes the set to one exam.
    sb = _db([_q("q1", exam=EXAM), _q("q2", exam=EXAM_B)])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 1
    assert res["exam_id"] == EXAM
    state = engine.get_attempt(sb, "u1", res["attempt_id"])
    assert [q["question_id"] for q in state["questions"]] == ["q1"]


def test_timed_practice_freezes_server_owned_countdown():
    # GQR-R10: seconds_per_question × frozen count becomes the attempt's expiry window,
    # so the shared objective attempt shell surfaces a short countdown (not the long
    # learning-mode TTL). duration_sec is also frozen on the template for reports.
    sb = _db([_q("q1", exam=EXAM), _q("q2", exam=EXAM)], pyq_order={"q1": 1, "q2": 2})
    res = svc.start_pyq_practice(
        sb, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM,
        seconds_per_question=30,
    )
    assert res["outcome"] == "ready" and res["question_count"] == 2
    state = engine.get_attempt(sb, "u1", res["attempt_id"])
    # 30s × 2 questions → ~60s countdown (a second or two may have elapsed).
    assert 55 <= state.get("time_remaining_sec") <= 60


def test_untimed_practice_reports_no_countdown():
    sb = _db([_q("q1", exam=EXAM)], pyq_order={"q1": 1})
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM)
    state = engine.get_attempt(sb, "u1", res["attempt_id"])
    # Untimed practice must surface no learner clock — the shell renders "--" and never
    # auto-submits. The long 24h abandonment TTL stays server-side on expires_at.
    assert state.get("time_remaining_sec") is None
    assert state.get("expires_at")


def _attempt_row(sb, attempt_id):
    return next(a for a in sb.db["mock_attempts"] if a["id"] == attempt_id)


def test_timed_deadline_is_the_single_enforced_window():
    # F1 (checkpost #960): the timed countdown is not display-only. The persisted
    # expires_at IS the short timed window (not the 24h abandonment TTL), so the shared
    # runtime paths (save/submit/auto-submit/sweeper) enforce it — untimed practice
    # keeps the long TTL.
    sb = _db([_q("q1", exam=EXAM), _q("q2", exam=EXAM)], pyq_order={"q1": 1, "q2": 2})
    timed = svc.start_pyq_practice(
        sb, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM, seconds_per_question=30,
    )
    assert 0 < engine._time_remaining_sec(_attempt_row(sb, timed["attempt_id"])) <= 60

    sb2 = _db([_q("q1", exam=EXAM)], pyq_order={"q1": 1})
    untimed = svc.start_pyq_practice(sb2, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM)
    assert engine._time_remaining_sec(_attempt_row(sb2, untimed["attempt_id"])) > 3600


def test_late_save_rejected_after_timed_deadline():
    # Advancing beyond the timed deadline: a save is rejected server-side by the shared
    # expires_at guard — the browser auto-submit is convenience, not enforcement.
    sb = _db([_q("q1", exam=EXAM)], pyq_order={"q1": 1})
    res = svc.start_pyq_practice(
        sb, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM, seconds_per_question=30,
    )
    aid = res["attempt_id"]
    q0 = engine.get_attempt(sb, "u1", aid)["questions"][0]
    # simulate the timed window elapsing
    _attempt_row(sb, aid)["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=5)
    ).isoformat()
    with pytest.raises(ValueError, match="expired"):
        engine.save_answer(
            sb, "u1", aid, q0["question_id"], (q0["options"][0] or {}).get("id"),
            is_marked_for_review=False, client_seq=1, time_spent_sec=5,
        )


def test_empty_pool_returns_no_writes():
    sb = _db([_q("q1", paper="66666666-6666-6666-6666-666666666666")])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id=PAPER, exam_id=EXAM)
    assert res["outcome"] == "empty_pool"
    assert res["question_count"] == 0
    assert sb.db["mock_attempts"] == []
    assert sb.db["mock_attempt_responses"] == []


def test_stale_projection_is_excluded_from_practice():
    sb = _db([_q("q1")], active=False, pyq_order={"q1": 1})
    res = svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id=PAPER, exam_id=EXAM)
    assert res["outcome"] == "empty_pool"


def test_unverified_bank_row_is_excluded():
    q = _q("q1")
    q["reviewer_status"] = "pending"
    sb = _db([q], pyq_order={"q1": 1})
    res = svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id=PAPER, exam_id=EXAM)
    assert res["outcome"] == "empty_pool"


def test_invalid_uuid_target_is_rejected():
    sb = _db([_q("q1")])
    try:
        svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id="not-a-uuid", exam_id=EXAM)
        raise AssertionError("expected PracticeInputError for malformed target_id")
    except svc.PracticeInputError:
        pass


def _client(sb: SBStub, user_id: str = "u1") -> TestClient:
    app = FastAPI()
    app.include_router(mock_engine_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id}
    mock_engine_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


def test_api_start_practice_ready_and_409_on_empty():
    sb = _db([_q("q1")], pyq_order={"q1": 1})
    client = _client(sb)
    r = client.post("/api/study/mocks/practice/start", json={"mode": "paper", "target_id": PAPER, "exam_id": EXAM})
    assert r.status_code == 200
    assert r.json()["outcome"] == "ready"
    r2 = client.post("/api/study/mocks/practice/start", json={"mode": "paper", "target_id": "66666666-6666-6666-6666-666666666666", "exam_id": EXAM})
    assert r2.status_code == 409


def test_api_rejects_unknown_mode_and_bad_uuid():
    sb = _db([_q("q1")])
    client = _client(sb)
    assert client.post("/api/study/mocks/practice/start", json={"mode": "essay", "target_id": PAPER}).status_code == 422
    assert client.post("/api/study/mocks/practice/start", json={"mode": "paper", "target_id": "nope", "exam_id": EXAM}).status_code == 422
