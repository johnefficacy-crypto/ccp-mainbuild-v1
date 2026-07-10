"""Mock Engine — acceptance criteria 2–7.

AC2: Two tabs cannot start an active attempt for same (user, template) — second → ConflictError / 409.
AC3: Reopening /attempts/:id after a tab kill restores saved answers + correct time_remaining_sec.
AC4: Replaying the same client_seq is a no-op (idempotent upsert).
AC5: Double /submit returns identical scores.
AC6: After submit, a mock_tests row exists (Mocks.jsx compat).
AC7: Editing mock_question_bank after submit does NOT change score or question text in result.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import mock_engine as mock_engine_api
from app.core.auth import get_current_user
from app.study_os import mock_engine as svc
from app.study_os.mock_engine import (
    AttemptFinalizationError,
    ConflictError,
    SubmissionPersistenceError,
)
from tests.persona_questions._stub import SBStub


# ─── helpers ──────────────────────────────────────────────────────────────────

def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _future_iso(secs=3600):
    return (datetime.now(timezone.utc) + timedelta(seconds=secs)).isoformat()


def _past_iso(secs=10):
    return (datetime.now(timezone.utc) - timedelta(seconds=secs)).isoformat()


def _make_option(question_id: str, opt_idx: int, is_correct: bool) -> dict:
    return {
        "id": f"opt-{question_id}-{opt_idx}",
        "question_id": question_id,
        "option_text": f"Option {opt_idx}",
        "option_index": opt_idx,
        "is_correct": is_correct,
    }


def _make_question(qid: str | None = None) -> dict:
    qid = qid or str(uuid.uuid4())
    opts = [_make_option(qid, i, i == 2) for i in range(1, 5)]
    correct_opt_id = opts[1]["id"]  # option_index=2
    return {
        "id": qid,
        "exam_family": "TEST",
        "question_text": f"Question {qid[:8]}",
        "question_type": "mcq",
        "difficulty": "easy",
        "marks": 1.0,
        "negative_marks": 0.25,
        "correct_option_id": correct_opt_id,
        "explanation": "Explanation text.",
        "reviewer_status": "published",
        "options": opts,
    }


def _make_template(slug: str = "test-mock-1") -> tuple[dict, list[dict]]:
    questions = [_make_question() for _ in range(5)]
    qids = [q["id"] for q in questions]
    template = {
        "id": f"tmpl-{slug}",
        "slug": slug,
        "name": "Test Mock",
        "exam_family": "TEST",
        "total_questions": len(questions),
        "duration_sec": 300,
        "negative_marking": True,
        "marks_per_correct": 1.0,
        "marks_per_wrong": 0.25,
        "config": {"question_ids": qids},
        "status": "active",
    }
    return template, questions


def _seeded_db(slug: str = "test-mock-1") -> tuple[SBStub, dict, list[dict]]:
    """Return a stub with one template and its questions already seeded."""
    template, questions = _make_template(slug)
    db: dict = {
        "mock_templates": [template],
        "mock_question_bank": questions,
        "mock_question_options": [o for q in questions for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
        "mock_tests": [],
    }
    return SBStub(db), template, questions


def _client(sb: SBStub, user_id: str = "user-1"):
    app = FastAPI()
    app.include_router(mock_engine_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id}
    mock_engine_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


# ─── AC2: duplicate active attempt → 409 ──────────────────────────────────────

def test_ac2_second_start_raises_conflict_error():
    """Service layer: starting twice raises ConflictError."""
    sb, template, questions = _seeded_db()
    svc.start_attempt(sb, "user-1", "test-mock-1")
    with pytest.raises(ConflictError):
        svc.start_attempt(sb, "user-1", "test-mock-1")


def test_ac2_second_start_returns_409_via_api():
    """API layer: second POST /start returns 409."""
    sb, template, questions = _seeded_db()
    client = _client(sb)
    r1 = client.post("/api/study/mocks/attempts/start", json={"template_slug": "test-mock-1"})
    assert r1.status_code == 200
    r2 = client.post("/api/study/mocks/attempts/start", json={"template_slug": "test-mock-1"})
    assert r2.status_code == 409


def test_ac2_different_users_can_both_start():
    """Two different users can each hold an active attempt for the same template."""
    sb, _, _ = _seeded_db()
    svc.start_attempt(sb, "user-1", "test-mock-1")
    # user-2 starts — should not conflict
    result = svc.start_attempt(sb, "user-2", "test-mock-1")
    assert "attempt_id" in result


# ─── AC3: resume restores answers + correct time_remaining_sec ────────────────

def test_ac3_resume_restores_saved_answer():
    """After saving an answer, get_attempt returns the saved selection."""
    sb, _, questions = _seeded_db()
    start_result = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start_result["attempt_id"]
    q = questions[0]
    correct_opt_id = q["correct_option_id"]

    svc.save_answer(sb, "user-1", attempt_id, q["id"], correct_opt_id,
                    is_marked_for_review=False, client_seq=1, time_spent_sec=10)

    state = svc.get_attempt(sb, "user-1", attempt_id)
    answered = next(qq for qq in state["questions"] if qq["question_id"] == q["id"])
    assert answered["selected_option_id"] == correct_opt_id


def test_ac3_time_remaining_decreases_over_time():
    """time_remaining_sec is derived from expires_at and is < duration_sec at any moment."""
    sb, _, _ = _seeded_db()
    result = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = result["attempt_id"]
    state = svc.get_attempt(sb, "user-1", attempt_id)
    # Template has 300s. Immediately after start, time_remaining must be close but < 300.
    assert 0 < state["time_remaining_sec"] <= 300


def test_ac3_expired_attempt_shows_zero_time():
    """An attempt whose expires_at is in the past shows time_remaining_sec=0."""
    sb, template, questions = _seeded_db()
    # Manually plant an expired attempt
    attempt_id = "expired-attempt-1"
    snap = {
        "question_ids": [q["id"] for q in questions],
        "duration_sec": 300,
        "negative_marking": True,
        "marks_per_correct": 1.0,
        "marks_per_wrong": 0.25,
    }
    sb.db["mock_attempts"].append({
        "id": attempt_id,
        "user_id": "user-1",
        "template_id": template["id"],
        "template_snapshot": snap,
        "status": "in_progress",
        "started_at": _past_iso(400),
        "expires_at": _past_iso(100),
    })
    for q in questions:
        sb.db["mock_attempt_responses"].append({
            "id": f"resp-{q['id']}",
            "attempt_id": attempt_id,
            "question_id": q["id"],
            "question_snapshot": svc._question_snapshot({**q, "options": []}),
            "selected_option_id": None,
            "is_marked_for_review": False,
            "is_visited": False,
            "time_spent_sec": 0,
            "client_seq": 0,
        })

    state = svc.get_attempt(sb, "user-1", attempt_id)
    assert state["time_remaining_sec"] == 0


# ─── AC4: idempotent answer (same client_seq) ─────────────────────────────────

def test_ac4_same_client_seq_is_noop():
    """Replaying the same client_seq returns idempotent=True and does not overwrite."""
    sb, _, questions = _seeded_db()
    start_result = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start_result["attempt_id"]
    q = questions[0]
    opts = q["options"]
    correct_opt = q["correct_option_id"]
    wrong_opt = next(o["id"] for o in opts if o["id"] != correct_opt)

    # First answer: correct option, seq=5
    svc.save_answer(sb, "user-1", attempt_id, q["id"], correct_opt,
                    is_marked_for_review=False, client_seq=5, time_spent_sec=10)

    # Replay with same seq=5 but different option — must be ignored
    result = svc.save_answer(sb, "user-1", attempt_id, q["id"], wrong_opt,
                             is_marked_for_review=False, client_seq=5, time_spent_sec=20)
    assert result["idempotent"] is True

    # Verify the stored answer is still the original correct option
    state = svc.get_attempt(sb, "user-1", attempt_id)
    answered = next(qq for qq in state["questions"] if qq["question_id"] == q["id"])
    assert answered["selected_option_id"] == correct_opt


def test_ac4_lower_seq_is_also_noop():
    """A client_seq lower than the stored one is also rejected as stale."""
    sb, _, questions = _seeded_db()
    start_result = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start_result["attempt_id"]
    q = questions[0]
    correct_opt = q["correct_option_id"]
    opts = q["options"]
    wrong_opt = next(o["id"] for o in opts if o["id"] != correct_opt)

    svc.save_answer(sb, "user-1", attempt_id, q["id"], correct_opt,
                    is_marked_for_review=False, client_seq=10, time_spent_sec=5)
    result = svc.save_answer(sb, "user-1", attempt_id, q["id"], wrong_opt,
                             is_marked_for_review=False, client_seq=3, time_spent_sec=5)
    assert result["idempotent"] is True


# ─── AC5: double submit returns identical scores ───────────────────────────────

def test_ac5_double_submit_identical():
    """Submitting twice returns the same score summary."""
    sb, _, questions = _seeded_db()
    start_result = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start_result["attempt_id"]

    # Answer some questions
    for i, q in enumerate(questions[:3]):
        correct_opt = q["correct_option_id"]
        svc.save_answer(sb, "user-1", attempt_id, q["id"], correct_opt,
                        is_marked_for_review=False, client_seq=i + 1, time_spent_sec=5)

    r1 = svc.submit_attempt(sb, "user-1", attempt_id)
    r2 = svc.submit_attempt(sb, "user-1", attempt_id)

    assert r1["score_raw"] == r2["score_raw"]
    assert r1["score_percentage"] == r2["score_percentage"]
    assert r1["total_correct"] == r2["total_correct"]
    assert r1["total_wrong"] == r2["total_wrong"]
    assert r1["total_unattempted"] == r2["total_unattempted"]


def test_ac5_double_submit_via_api():
    """API: POST /submit twice → both return 200 with same scores."""
    sb, _, questions = _seeded_db()
    client = _client(sb)
    r = client.post("/api/study/mocks/attempts/start", json={"template_slug": "test-mock-1"})
    attempt_id = r.json()["attempt_id"]

    s1 = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    s2 = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    assert s1.status_code == 200
    assert s2.status_code == 200
    assert s1.json()["score_raw"] == s2.json()["score_raw"]


# ─── AC6: submit emits mock_tests row ─────────────────────────────────────────

def test_ac6_submit_writes_mock_tests_row():
    """After submit, a mock_tests row exists for the user."""
    sb, _, questions = _seeded_db()
    start_result = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start_result["attempt_id"]

    # Answer one correctly
    q = questions[0]
    svc.save_answer(sb, "user-1", attempt_id, q["id"], q["correct_option_id"],
                    is_marked_for_review=False, client_seq=1, time_spent_sec=10)

    svc.submit_attempt(sb, "user-1", attempt_id)

    mock_rows = [r for r in sb.db.get("mock_tests", []) if r.get("user_id") == "user-1"]
    assert len(mock_rows) == 1
    mt = mock_rows[0]
    assert mt["scored_marks"] is not None
    assert mt["total_marks"] is not None
    assert mt["correct_answers"] is not None
    assert mt["review_state"] == "unreviewed"
    # analysis_payload links back to the attempt (mock_tests has no metadata column)
    assert mt.get("analysis_payload", {}).get("mock_attempt_id") == attempt_id


def test_ac6_double_submit_does_not_duplicate_mock_tests_row():
    """Second submit call must not insert a second mock_tests row."""
    sb, _, questions = _seeded_db()
    start_result = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start_result["attempt_id"]

    svc.submit_attempt(sb, "user-1", attempt_id)
    svc.submit_attempt(sb, "user-1", attempt_id)

    user_rows = [r for r in sb.db.get("mock_tests", []) if r.get("user_id") == "user-1"]
    assert len(user_rows) == 1


# ─── AC7: question edits after submit don't change result ─────────────────────

def test_ac7_post_submit_question_edit_does_not_affect_result():
    """Mutating mock_question_bank after submit leaves the result unchanged."""
    sb, _, questions = _seeded_db()
    start_result = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start_result["attempt_id"]

    # Answer all correctly
    for i, q in enumerate(questions):
        svc.save_answer(sb, "user-1", attempt_id, q["id"], q["correct_option_id"],
                        is_marked_for_review=False, client_seq=i + 1, time_spent_sec=5)

    submit_result = svc.submit_attempt(sb, "user-1", attempt_id)
    original_score = submit_result["score_raw"]
    original_text = submit_result["per_question"][0]["question_text"]

    # Mutate the live question bank — change text and swap correct answer
    live_q = sb.db["mock_question_bank"][0]
    live_q["question_text"] = "TOTALLY DIFFERENT QUESTION TEXT"
    # Change correct_option_id to a different option
    old_correct = live_q["correct_option_id"]
    new_wrong = next(
        o["id"] for o in questions[0]["options"] if o["id"] != old_correct
    )
    live_q["correct_option_id"] = new_wrong
    for o in sb.db["mock_question_options"]:
        if o["question_id"] == live_q["id"]:
            o["is_correct"] = (o["id"] == new_wrong)

    # Fetch result again — must be identical (uses snapshot, not live table)
    result_after = svc.get_result(sb, "user-1", attempt_id)
    assert result_after["score_raw"] == original_score
    assert result_after["per_question"][0]["question_text"] == original_text


def test_ac7_correct_option_from_snapshot_not_live_table():
    """The correct_option_id shown in the result comes from question_snapshot."""
    sb, _, questions = _seeded_db()
    start_result = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start_result["attempt_id"]
    svc.submit_attempt(sb, "user-1", attempt_id)

    # Flip correct answer in live DB
    live_q = sb.db["mock_question_bank"][0]
    original_correct = live_q["correct_option_id"]
    new_opt = next(
        o["id"] for o in questions[0]["options"] if o["id"] != original_correct
    )
    live_q["correct_option_id"] = new_opt

    result = svc.get_result(sb, "user-1", attempt_id)
    # Result must still show original correct option from snapshot
    assert result["per_question"][0]["correct_option_id"] == original_correct


# ─── scoring correctness ──────────────────────────────────────────────────────

def test_scoring_correct_wrong_unattempted():
    """Score = correct×1 − wrong×0.25; unattempted contributes 0."""
    sb, _, questions = _seeded_db()
    start_result = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start_result["attempt_id"]

    # Answer q0 correctly, q1 wrongly, q2–q4 unattempted
    q0, q1, *rest = questions
    wrong_opt = next(
        o["id"] for o in q1["options"] if o["id"] != q1["correct_option_id"]
    )
    svc.save_answer(sb, "user-1", attempt_id, q0["id"], q0["correct_option_id"],
                    is_marked_for_review=False, client_seq=1, time_spent_sec=5)
    svc.save_answer(sb, "user-1", attempt_id, q1["id"], wrong_opt,
                    is_marked_for_review=False, client_seq=2, time_spent_sec=5)

    result = svc.submit_attempt(sb, "user-1", attempt_id)
    assert result["total_correct"] == 1
    assert result["total_wrong"] == 1
    assert result["total_unattempted"] == len(questions) - 2
    assert abs(result["score_raw"] - (1.0 - 0.25)) < 0.01


def test_submit_derivation_failure_does_not_block(monkeypatch):
    sb, _, questions = _seeded_db()
    start_result = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start_result["attempt_id"]
    monkeypatch.setattr(svc.attempt_analytics, "compute_and_persist", lambda *_: (_ for _ in ()).throw(RuntimeError("boom")))
    out = svc.submit_attempt(sb, "user-1", attempt_id)
    assert out["status"] == "submitted"


@pytest.mark.parametrize(
    "exc_cls", [SubmissionPersistenceError, AttemptFinalizationError]
)
def test_submit_persistence_failure_returns_503_retry_after(monkeypatch, exc_cls):
    """API: a finalization-persistence failure surfaces as a retryable 503 with
    the documented contract. Both exceptions map to the same response, so each
    path is pinned via parametrization."""
    sb, _, _ = _seeded_db()
    client = _client(sb)

    def _raise(*_a, **_k):
        raise exc_cls("simulated persistence failure")

    monkeypatch.setattr(mock_engine_api, "submit_attempt", _raise)

    r = client.post("/api/study/mocks/attempts/some-attempt/submit")
    assert r.status_code == 503
    assert r.json()["detail"]["error"] == "submit_persist_failed"
    assert r.headers["Retry-After"] == "1"


def test_get_review_endpoint_shape():
    sb, _, _ = _seeded_db()
    start = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start["attempt_id"]
    svc.submit_attempt(sb, "user-1", attempt_id)
    review = svc.get_review(sb, "user-1", attempt_id)
    assert review["attempt_id"] == attempt_id
    assert isinstance(review["questions"], list)


def test_get_review_orders_by_frozen_attempt_order():
    """Review numbering must follow the frozen attempt order, not PostgREST row
    order. Shuffle the response rows and confirm the review still returns
    questions in template_snapshot.question_ids order with a matching 1-based
    attempt_order."""
    sb, template, _ = _seeded_db()
    start = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start["attempt_id"]
    svc.submit_attempt(sb, "user-1", attempt_id)

    # Simulate PostgREST returning the response rows out of attempt order.
    sb.db["mock_attempt_responses"].reverse()

    review = svc.get_review(sb, "user-1", attempt_id)
    frozen_ids = template["config"]["question_ids"]
    assert [q["question_id"] for q in review["questions"]] == frozen_ids
    assert [q["attempt_order"] for q in review["questions"]] == list(range(1, len(frozen_ids) + 1))
