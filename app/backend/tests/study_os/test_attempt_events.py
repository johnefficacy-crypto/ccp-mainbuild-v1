"""PR2b Attempt Events — acceptance criteria tests.

AC4 : Posting the same batch of client events twice produces no duplicates.
AC5 : Out-of-order sequence numbers are accepted (ordering is query-time concern).
AC7 : Calling POST /events after attempt.status='abandoned' returns 409.
AC8 : Calling POST /events on someone else's attempt returns 403.
AC9 : Heartbeat event with large drift is accepted but does not change attempt state.
+ Batch size > 100 returns 413.
+ submit_attempt writes exactly one attempt.submitted server event.
+ start_attempt writes one attempt.started server event.
+ save_answer writes one question.answered server event (non-idempotent path only).
+ GET /events respects RBAC (owner reads; non-owner without permission → 403).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import mock_attempt_events as events_api
from app.api import mock_engine as mock_engine_api
from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_admin
from app.study_os import attempt_events as svc
from app.study_os import mock_engine as engine_svc
from tests.persona_questions._stub import SBStub


# ── shared helpers (mirrored from test_mock_engine) ───────────────────────────

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
    correct_opt_id = opts[1]["id"]
    return {
        "id": qid,
        "exam_family": "TEST",
        "question_text": f"Question {qid[:8]}",
        "question_type": "mcq",
        "difficulty": "easy",
        "marks": 1.0,
        "negative_marks": 0.25,
        "correct_option_id": correct_opt_id,
        "explanation": "Explanation.",
        "reviewer_status": "published",
        "valid_until": None,
        "options": opts,
    }


def _make_template(slug: str = "test-mock-ev") -> tuple[dict, list[dict]]:
    questions = [_make_question() for _ in range(3)]
    qids = [q["id"] for q in questions]
    template = {
        "id": f"tmpl-{slug}",
        "slug": slug,
        "name": "Events Test Mock",
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


def _seeded_db(slug="test-mock-ev") -> tuple[SBStub, dict, list[dict]]:
    template, questions = _make_template(slug)
    db = {
        "mock_templates": [template],
        "mock_question_bank": questions,
        "mock_question_options": [o for q in questions for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
        "mock_attempt_events": [],
        "mock_tests": [],
    }
    return SBStub(db), template, questions


def _client(sb: SBStub, user_id: str = "user-1"):
    app = FastAPI()
    app.include_router(events_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id, "role": "user", "permissions": []}
    events_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


def _full_client(sb: SBStub, user_id: str = "user-1", role: str = "user", perms: list | None = None):
    """Client with both mock_engine and mock_attempt_events routers mounted."""
    app = FastAPI()
    app.include_router(mock_engine_api.router, prefix="/api")
    app.include_router(events_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {
        "id": user_id, "role": role, "permissions": perms or [],
    }
    mock_engine_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    events_api.get_supabase_admin = lambda: sb       # type: ignore[assignment]
    return TestClient(app)


# ── server-event emission ─────────────────────────────────────────────────────
# Note: start_attempt uses .or_() which the SBStub does not support (returns
# LookupError via _safe). These tests use planted attempts + direct service
# calls to test event emission without going through the question-loading path.

def _plant_full_attempt(sb: SBStub, attempt_id: str, user_id: str, questions: list[dict]) -> None:
    """Plant a complete in_progress attempt with response rows in the stub."""
    snap = {
        "question_ids": [q["id"] for q in questions],
        "duration_sec": 300,
        "negative_marking": True,
        "marks_per_correct": 1.0,
        "marks_per_wrong": 0.25,
    }
    sb.db.setdefault("mock_attempts", []).append({
        "id": attempt_id,
        "user_id": user_id,
        "template_id": "tmpl-test",
        "template_snapshot": snap,
        "status": "in_progress",
        "started_at": _now_iso(),
        "expires_at": _future_iso(3600),
    })
    for q in questions:
        sb.db.setdefault("mock_attempt_responses", []).append({
            "id": f"resp-{q['id']}",
            "attempt_id": attempt_id,
            "question_id": q["id"],
            "question_snapshot": {
                "id": q["id"],
                "question_text": q["question_text"],
                "question_type": q["question_type"],
                "marks": float(q.get("marks") or 1),
                "negative_marks": float(q.get("negative_marks") or 0),
                "correct_option_id": q.get("correct_option_id"),
                "explanation": q.get("explanation"),
                "options": q.get("options") or [],
            },
            "selected_option_id": None,
            "is_marked_for_review": False,
            "is_visited": False,
            "time_spent_sec": 0,
            "client_seq": 0,
            "is_correct": None,
            "marks_awarded": None,
        })


def test_start_attempt_emits_started_event():
    """record_server_event with ATTEMPT_STARTED writes one server row."""
    sb, _, _ = _seeded_db()
    from app.study_os.attempt_events import record_server_event
    from app.study_os.attempt_event_types import ATTEMPT_STARTED
    attempt_id = "se-attempt-started"
    record_server_event(sb, attempt_id, "user-1", ATTEMPT_STARTED,
                        payload={"template_slug": "test-mock-ev"})
    events = sb.db.get("mock_attempt_events", [])
    started = [e for e in events if e["event_type"] == "attempt.started"]
    assert len(started) == 1
    assert started[0]["source"] == "server"
    assert started[0]["payload"]["template_slug"] == "test-mock-ev"


def test_save_answer_emits_question_answered_server_event():
    """save_answer (non-idempotent) writes one question.answered server event."""
    sb, _, questions = _seeded_db()
    attempt_id = "se-attempt-answer"
    _plant_full_attempt(sb, attempt_id, "user-1", questions)
    q = questions[0]
    engine_svc.save_answer(sb, "user-1", attempt_id, q["id"], q["correct_option_id"],
                           is_marked_for_review=False, client_seq=1, time_spent_sec=5)
    events = sb.db.get("mock_attempt_events", [])
    answered = [e for e in events if e["event_type"] == "question.answered" and e["source"] == "server"]
    assert len(answered) == 1
    assert answered[0]["payload"]["question_id"] == q["id"]


def test_save_answer_idempotent_does_not_emit_event():
    """Idempotent save_answer (same or lower seq) must not emit a server event."""
    sb, _, questions = _seeded_db()
    attempt_id = "se-attempt-idem"
    _plant_full_attempt(sb, attempt_id, "user-1", questions)
    q = questions[0]
    engine_svc.save_answer(sb, "user-1", attempt_id, q["id"], q["correct_option_id"],
                           is_marked_for_review=False, client_seq=5, time_spent_sec=5)
    before = len([e for e in sb.db.get("mock_attempt_events", [])
                  if e["event_type"] == "question.answered" and e["source"] == "server"])
    # Replay with same seq — must not add a second event.
    engine_svc.save_answer(sb, "user-1", attempt_id, q["id"], q["correct_option_id"],
                           is_marked_for_review=False, client_seq=5, time_spent_sec=10)
    after = len([e for e in sb.db.get("mock_attempt_events", [])
                 if e["event_type"] == "question.answered" and e["source"] == "server"])
    assert after == before


def test_submit_emits_exactly_one_submitted_event():
    """submit_attempt writes exactly one attempt.submitted server event."""
    sb, _, questions = _seeded_db()
    attempt_id = "se-attempt-submit"
    _plant_full_attempt(sb, attempt_id, "user-1", questions)
    engine_svc.submit_attempt(sb, "user-1", attempt_id)
    events = sb.db.get("mock_attempt_events", [])
    submitted = [e for e in events if e["event_type"] == "attempt.submitted"]
    assert len(submitted) == 1
    assert submitted[0]["source"] == "server"
    assert submitted[0]["payload"]["score_raw"] is not None


def test_double_submit_does_not_emit_second_event():
    """Second submit call (idempotent path) must not write a second server event."""
    sb, _, questions = _seeded_db()
    attempt_id = "se-attempt-dbl"
    _plant_full_attempt(sb, attempt_id, "user-1", questions)
    engine_svc.submit_attempt(sb, "user-1", attempt_id)
    engine_svc.submit_attempt(sb, "user-1", attempt_id)
    submitted = [e for e in sb.db.get("mock_attempt_events", []) if e["event_type"] == "attempt.submitted"]
    assert len(submitted) == 1


# ── client event ingest ───────────────────────────────────────────────────────

def _plant_attempt(sb: SBStub, attempt_id: str, user_id: str, status: str = "in_progress") -> dict:
    submitted_at = _now_iso() if status == "submitted" else None
    row = {
        "id": attempt_id,
        "user_id": user_id,
        "status": status,
        "submitted_at": submitted_at,
        "expires_at": _future_iso(3600) if status == "in_progress" else _past_iso(10),
        "template_snapshot": {},
    }
    sb.db.setdefault("mock_attempts", []).append(row)
    return row


def _make_client_events(n: int, start_seq: int = 1) -> list[dict]:
    return [
        {
            "event_type": "question.visited",
            "sequence_no": start_seq + i,
            "occurred_at": _now_iso(),
            "payload": {"question_id": f"q-{i}"},
        }
        for i in range(n)
    ]


def test_client_events_accepted():
    """Valid client events are accepted and persisted."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-ev-1"
    _plant_attempt(sb, attempt_id, "user-1")
    events = _make_client_events(3)
    result = svc.ingest_client_events(sb, attempt_id, "user-1", events)
    assert result["accepted"] == 3
    assert result["duplicates"] == 0
    assert result["rejected"] == []
    stored = [e for e in sb.db.get("mock_attempt_events", []) if e["source"] == "client"]
    assert len(stored) == 3


def test_client_events_idempotent_on_sequence_no():
    """Posting the same batch twice produces no duplicates (AC4)."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-ev-2"
    _plant_attempt(sb, attempt_id, "user-1")
    batch = _make_client_events(5)
    r1 = svc.ingest_client_events(sb, attempt_id, "user-1", batch)
    r2 = svc.ingest_client_events(sb, attempt_id, "user-1", batch)
    assert r1["accepted"] == 5
    assert r2["accepted"] == 0
    assert r2["duplicates"] == 5
    stored = [e for e in sb.db.get("mock_attempt_events", []) if e["source"] == "client"]
    assert len(stored) == 5


def test_client_events_out_of_order_accepted():
    """Out-of-order sequence numbers are accepted (AC5)."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-ev-3"
    _plant_attempt(sb, attempt_id, "user-1")
    # Intentionally reversed order
    events = [
        {"event_type": "question.visited", "sequence_no": 10, "occurred_at": _now_iso(), "payload": {}},
        {"event_type": "question.visited", "sequence_no": 3,  "occurred_at": _now_iso(), "payload": {}},
        {"event_type": "question.visited", "sequence_no": 7,  "occurred_at": _now_iso(), "payload": {}},
    ]
    result = svc.ingest_client_events(sb, attempt_id, "user-1", events)
    assert result["accepted"] == 3
    assert result["rejected"] == []


def test_intra_batch_duplicates_counted():
    """Duplicate sequence numbers within a single batch count as duplicates."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-ev-4"
    _plant_attempt(sb, attempt_id, "user-1")
    events = [
        {"event_type": "question.visited", "sequence_no": 1, "occurred_at": _now_iso(), "payload": {}},
        {"event_type": "question.visited", "sequence_no": 1, "occurred_at": _now_iso(), "payload": {}},
    ]
    result = svc.ingest_client_events(sb, attempt_id, "user-1", events)
    assert result["accepted"] == 1
    assert result["duplicates"] == 1


def test_unknown_event_type_is_rejected():
    """Events with unknown event_type are rejected with reason."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-ev-5"
    _plant_attempt(sb, attempt_id, "user-1")
    events = [{"event_type": "hacker.special", "sequence_no": 1, "occurred_at": _now_iso(), "payload": {}}]
    result = svc.ingest_client_events(sb, attempt_id, "user-1", events)
    assert result["accepted"] == 0
    assert len(result["rejected"]) == 1
    assert "unknown event_type" in result["rejected"][0]["reason"]


def test_event_missing_occurred_at_is_rejected():
    """Events without occurred_at are rejected."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-ev-6"
    _plant_attempt(sb, attempt_id, "user-1")
    events = [{"event_type": "question.visited", "sequence_no": 1, "payload": {}}]
    result = svc.ingest_client_events(sb, attempt_id, "user-1", events)
    assert result["accepted"] == 0
    assert result["rejected"][0]["reason"] == "missing occurred_at"


# ── API-level RBAC and status checks ─────────────────────────────────────────

def test_api_post_events_rejected_for_abandoned_attempt():
    """POST /events after attempt is abandoned returns 409 (AC7)."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-aban-1"
    _plant_attempt(sb, attempt_id, "user-1", status="abandoned")
    client = _client(sb, "user-1")
    body = {"events": [{"event_type": "question.visited", "sequence_no": 1,
                        "occurred_at": _now_iso(), "payload": {}}]}
    r = client.post(f"/api/study/mocks/attempts/{attempt_id}/events", json=body)
    assert r.status_code == 409


def test_api_post_events_rejected_for_wrong_user():
    """POST /events on another user's attempt returns 403 (AC8)."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-rbac-1"
    _plant_attempt(sb, attempt_id, "user-owner", status="in_progress")
    client = _client(sb, "user-intruder")
    body = {"events": [{"event_type": "question.visited", "sequence_no": 1,
                        "occurred_at": _now_iso(), "payload": {}}]}
    r = client.post(f"/api/study/mocks/attempts/{attempt_id}/events", json=body)
    assert r.status_code == 403


def test_api_post_events_batch_too_large_returns_413():
    """Batch with > 100 events returns 413."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-big-1"
    _plant_attempt(sb, attempt_id, "user-1")
    client = _client(sb, "user-1")
    events = [{"event_type": "question.visited", "sequence_no": i + 1,
               "occurred_at": _now_iso(), "payload": {}} for i in range(101)]
    r = client.post(f"/api/study/mocks/attempts/{attempt_id}/events", json={"events": events})
    assert r.status_code == 413


def test_api_get_events_owner_can_read():
    """Attempt owner can GET their own events."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-get-1"
    _plant_attempt(sb, attempt_id, "user-1")
    sb.db.setdefault("mock_attempt_events", []).append({
        "id": 1, "attempt_id": attempt_id, "user_id": "user-1",
        "event_type": "question.visited", "payload": {}, "sequence_no": 1,
        "source": "client", "occurred_at": _now_iso(), "recorded_at": _now_iso(),
    })
    client = _client(sb, "user-1")
    r = client.get(f"/api/study/mocks/attempts/{attempt_id}/events")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_api_get_events_other_user_without_permission_is_403():
    """Non-owner without mock_questions:publish permission gets 403."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-get-2"
    _plant_attempt(sb, attempt_id, "user-owner")
    client = _client(sb, "user-stranger")
    r = client.get(f"/api/study/mocks/attempts/{attempt_id}/events")
    assert r.status_code == 403


def test_api_get_events_publisher_can_read_any():
    """User with mock_questions:publish permission can read any attempt's events."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-get-3"
    _plant_attempt(sb, attempt_id, "user-owner")

    app = FastAPI()
    app.include_router(events_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "user-publisher",
        "role": "user",
        "permissions": ["mock_questions:publish"],
    }
    events_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    publisher_client = TestClient(app)
    r = publisher_client.get(f"/api/study/mocks/attempts/{attempt_id}/events")
    assert r.status_code == 200


def test_api_post_events_submitted_within_grace_window_accepted():
    """Events posted within 5 min of submit are still accepted."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-grace-1"
    # submitted 2 minutes ago — within grace window
    recent_submit = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    row = {
        "id": attempt_id,
        "user_id": "user-1",
        "status": "submitted",
        "submitted_at": recent_submit,
        "expires_at": _past_iso(10),
        "template_snapshot": {},
    }
    sb.db.setdefault("mock_attempts", []).append(row)
    client = _client(sb, "user-1")
    body = {"events": [{"event_type": "attempt.heartbeat", "sequence_no": 1,
                        "occurred_at": _now_iso(), "payload": {}}]}
    r = client.post(f"/api/study/mocks/attempts/{attempt_id}/events", json=body)
    assert r.status_code == 200


def test_late_event_to_submitted_attempt_triggers_recompute(monkeypatch):
    """Accepted client events on a submitted attempt (within grace) idempotently
    recompute the persisted analytics (closes the submit/late-event race)."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-recompute-1"
    recent_submit = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    sb.db.setdefault("mock_attempts", []).append({
        "id": attempt_id, "user_id": "user-1", "status": "submitted",
        "submitted_at": recent_submit, "expires_at": _past_iso(10), "template_snapshot": {},
    })
    calls = []
    import app.study_os.attempt_analytics.service as analytics_svc
    monkeypatch.setattr(analytics_svc, "compute_and_persist", lambda _sb, aid: calls.append(aid))
    client = _client(sb, "user-1")
    body = {"events": [{"event_type": "question.visited", "sequence_no": 1,
                        "occurred_at": _now_iso(), "payload": {"question_id": "q-1"}}]}
    r = client.post(f"/api/study/mocks/attempts/{attempt_id}/events", json=body)
    assert r.status_code == 200
    assert calls == [attempt_id]
    assert r.json().get("analytics_recomputed") is True


def test_recompute_failure_schedules_analytics_retry(monkeypatch):
    """If the in-line recompute fails, the analytics_retry job is scheduled so the
    stale snapshot is reconciled durably (the events are already ACKed)."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-recompute-fail"
    recent_submit = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    sb.db.setdefault("mock_attempts", []).append({
        "id": attempt_id, "user_id": "user-1", "status": "submitted",
        "submitted_at": recent_submit, "expires_at": _past_iso(10), "template_snapshot": {},
    })
    import app.study_os.attempt_analytics.service as analytics_svc
    import app.study_os.mock_engine as engine_mod

    def _boom(_sb, _aid):
        raise RuntimeError("db down")

    scheduled = []
    monkeypatch.setattr(analytics_svc, "compute_and_persist", _boom)
    monkeypatch.setattr(engine_mod, "schedule_job",
                        lambda _sb, kind, aid, **kw: scheduled.append((kind, aid)))

    client = _client(sb, "user-1")
    body = {"events": [{"event_type": "question.visited", "sequence_no": 1,
                        "occurred_at": _now_iso(), "payload": {"question_id": "q-1"}}]}
    r = client.post(f"/api/study/mocks/attempts/{attempt_id}/events", json=body)
    assert r.status_code == 200
    assert r.json().get("analytics_recomputed") is False
    assert r.json().get("analytics_retry_scheduled") is True
    assert scheduled == [(engine_mod.JOB_ANALYTICS_RETRY, attempt_id)]


def test_duplicate_replay_accepts_zero_and_skips_recompute(monkeypatch):
    """A duplicate replay (accepted=0) must NOT retrigger recompute — the first
    accepted delivery already did (or scheduled the retry)."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-dup-replay"
    recent_submit = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    sb.db.setdefault("mock_attempts", []).append({
        "id": attempt_id, "user_id": "user-1", "status": "submitted",
        "submitted_at": recent_submit, "expires_at": _past_iso(10), "template_snapshot": {},
    })
    calls = []
    import app.study_os.attempt_analytics.service as analytics_svc
    monkeypatch.setattr(analytics_svc, "compute_and_persist", lambda _sb, aid: calls.append(aid))
    client = _client(sb, "user-1")
    body = {"events": [{"event_type": "question.visited", "sequence_no": 1,
                        "occurred_at": _now_iso(), "payload": {"question_id": "q-1"}}]}

    r1 = client.post(f"/api/study/mocks/attempts/{attempt_id}/events", json=body)
    assert r1.json()["accepted"] == 1 and r1.json().get("analytics_recomputed") is True
    r2 = client.post(f"/api/study/mocks/attempts/{attempt_id}/events", json=body)
    assert r2.json()["accepted"] == 0 and r2.json()["duplicates"] == 1
    assert "analytics_recomputed" not in r2.json()  # no recompute on a 0-accept replay
    assert calls == [attempt_id]  # recompute ran exactly once (first delivery)


def test_in_progress_event_does_not_trigger_recompute(monkeypatch):
    """Events on an in_progress attempt must NOT trigger a post-submit recompute."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-recompute-2"
    _plant_attempt(sb, attempt_id, "user-1", status="in_progress")
    calls = []
    import app.study_os.attempt_analytics.service as analytics_svc
    monkeypatch.setattr(analytics_svc, "compute_and_persist", lambda _sb, aid: calls.append(aid))
    client = _client(sb, "user-1")
    body = {"events": [{"event_type": "question.visited", "sequence_no": 1,
                        "occurred_at": _now_iso(), "payload": {"question_id": "q-1"}}]}
    r = client.post(f"/api/study/mocks/attempts/{attempt_id}/events", json=body)
    assert r.status_code == 200
    assert calls == []


def test_heartbeat_with_large_drift_accepted_no_state_change():
    """Heartbeat with client_remaining_sec >> server_remaining_sec is recorded, not enforced (AC9)."""
    sb, _, _ = _seeded_db()
    attempt_id = "attempt-drift-1"
    _plant_attempt(sb, attempt_id, "user-1")
    events = [{
        "event_type": "attempt.heartbeat",
        "sequence_no": 1,
        "occurred_at": _now_iso(),
        "payload": {"client_remaining_sec": 300, "server_remaining_sec_last_seen": 10},
    }]
    result = svc.ingest_client_events(sb, attempt_id, "user-1", events)
    assert result["accepted"] == 1
    # Attempt state must be untouched.
    attempt_row = next(r for r in sb.db["mock_attempts"] if r["id"] == attempt_id)
    assert attempt_row["status"] == "in_progress"
