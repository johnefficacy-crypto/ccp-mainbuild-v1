"""PR #719 — mastery classification readiness gate.

Tests:
  1. check_classification_readiness unit tests (A)
  2. MasteryWriter gate: raises MasteryClassificationNotReady + schedules analytics_retry (B)
  3. api/mock_engine submit route: classification not ready → 200, mastery rescheduled (C)
  4. _run_job JOB_ANALYTICS_RETRY → enqueue mastery_retry when FF != off (D4)
  5. auto_submit_attempt → enqueue mastery_retry when FF != off (D2)
  6. Idempotency: duplicate mastery_retry not inserted when active job exists
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import mock_engine as mock_engine_api
from app.core.auth import get_current_user
from app.study_os import mock_engine as svc
from app.study_os.attempt_classification_readiness import (
    ClassificationReadiness,
    check_classification_readiness,
)
from app.study_os.mastery_writer import MasteryClassificationNotReady, MasteryWriter
from app.study_os.mock_engine import (
    JOB_ANALYTICS_RETRY,
    JOB_MASTERY_RETRY,
    _run_job,
    auto_submit_attempt,
    enqueue_mastery_retry_required,
)
from tests.persona_questions._stub import SBStub
from tests.study_os.test_mock_engine import _seeded_db


# ─── helpers ──────────────────────────────────────────────────────────────────

def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _future_iso(secs: int = 3600) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=secs)).isoformat()


def _client(sb: SBStub, user_id: str = "user-1") -> TestClient:
    app = FastAPI()
    app.include_router(mock_engine_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id}
    mock_engine_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


def _stub_with_attempt(n_responses: int = 3, n_classifications: int | None = None) -> tuple[SBStub, str]:
    """Return a seeded stub plus an attempt_id with `n_responses` responses.

    If n_classifications is None, writes one classification per response
    (ready state).  If 0, writes no classification rows (not ready).
    Otherwise writes exactly n_classifications rows.
    """
    sb = SBStub({})
    attempt_id = str(uuid.uuid4())
    user_id = "user-1"
    sb.db["mock_attempts"] = [{"id": attempt_id, "user_id": user_id, "status": "submitted"}]
    qids = [str(uuid.uuid4()) for _ in range(n_responses)]
    sb.db["mock_attempt_responses"] = [
        {"id": str(uuid.uuid4()), "attempt_id": attempt_id, "question_id": qid,
         "selected_option_id": None, "is_correct": False, "time_spent_sec": 0,
         "question_snapshot": {}}
        for qid in qids
    ]
    n_cls = n_responses if n_classifications is None else n_classifications
    sb.db["mock_attempt_response_classification"] = [
        {"id": str(uuid.uuid4()), "attempt_id": attempt_id, "question_id": qids[i], "error_type": None}
        for i in range(n_cls)
    ]
    return sb, attempt_id


# ─── A: check_classification_readiness unit tests ─────────────────────────────

def test_readiness_all_classified():
    sb, attempt_id = _stub_with_attempt(n_responses=3, n_classifications=3)
    r = check_classification_readiness(sb, attempt_id)
    assert r.ready is True
    assert r.response_count == 3
    assert r.classification_count == 3
    assert r.unique_classification_count == 3
    assert r.missing_question_ids == []
    assert r.duplicate_question_ids == []


def test_readiness_no_classifications():
    sb, attempt_id = _stub_with_attempt(n_responses=3, n_classifications=0)
    r = check_classification_readiness(sb, attempt_id)
    assert r.ready is False
    assert r.response_count == 3
    assert r.classification_count == 0
    assert len(r.missing_question_ids) == 3


def test_readiness_partial_classifications():
    sb, attempt_id = _stub_with_attempt(n_responses=4, n_classifications=2)
    r = check_classification_readiness(sb, attempt_id)
    assert r.ready is False
    assert r.response_count == 4
    assert len(r.missing_question_ids) == 2


def test_readiness_zero_responses():
    sb, attempt_id = _stub_with_attempt(n_responses=0, n_classifications=0)
    r = check_classification_readiness(sb, attempt_id)
    assert r.ready is True
    assert r.response_count == 0
    assert r.missing_question_ids == []
    assert r.duplicate_question_ids == []


def test_readiness_returns_dataclass():
    sb, attempt_id = _stub_with_attempt(n_responses=2, n_classifications=2)
    r = check_classification_readiness(sb, attempt_id)
    assert isinstance(r, ClassificationReadiness)


# ─── B: MasteryWriter raises when classifications missing ─────────────────────

def test_mastery_writer_raises_when_not_ready(monkeypatch):
    """process_attempt_sync raises MasteryClassificationNotReady when classifications absent."""
    sb, attempt_id = _stub_with_attempt(n_responses=2, n_classifications=0)
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    writer = MasteryWriter(sb, "shadow")
    with pytest.raises(MasteryClassificationNotReady) as exc_info:
        writer.process_attempt_sync(attempt_id)
    assert "classification_not_ready" in str(exc_info.value)
    assert "missing=2" in str(exc_info.value)


def test_mastery_writer_enqueues_analytics_retry_when_not_ready(monkeypatch):
    """process_attempt_sync schedules analytics_retry before raising."""
    sb, attempt_id = _stub_with_attempt(n_responses=2, n_classifications=0)
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    writer = MasteryWriter(sb, "shadow")
    with pytest.raises(MasteryClassificationNotReady):
        writer.process_attempt_sync(attempt_id)
    jobs = sb.db.get("mock_attempt_jobs", [])
    analytics_jobs = [j for j in jobs if j["job_kind"] == JOB_ANALYTICS_RETRY and j["attempt_id"] == attempt_id]
    assert len(analytics_jobs) == 1


def test_mastery_writer_proceeds_when_ready(monkeypatch):
    """process_attempt_sync does not raise when all classifications are present."""
    sb, attempt_id = _stub_with_attempt(n_responses=2, n_classifications=2)
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    writer = MasteryWriter(sb, "shadow")
    writer.process_attempt_sync(attempt_id)  # must not raise


def test_mastery_writer_skips_gate_when_flag_off(monkeypatch):
    """Flag=off: process_attempt_sync returns immediately without readiness check."""
    sb, attempt_id = _stub_with_attempt(n_responses=3, n_classifications=0)
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "off")
    writer = MasteryWriter(sb, "off")
    writer.process_attempt_sync(attempt_id)  # must not raise even with missing classifications
    assert not sb.db.get("mock_attempt_jobs")  # no jobs enqueued


def test_mastery_writer_error_message_includes_counts(monkeypatch):
    sb, attempt_id = _stub_with_attempt(n_responses=5, n_classifications=1)
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    writer = MasteryWriter(sb, "shadow")
    with pytest.raises(MasteryClassificationNotReady) as exc_info:
        writer.process_attempt_sync(attempt_id)
    msg = str(exc_info.value)
    assert "missing=4" in msg
    assert "duplicate=0" in msg


# ─── C: submit route returns 200 and reschedules mastery when not ready ────────

def test_submit_classification_not_ready_returns_200(monkeypatch):
    """API submit: MasteryClassificationNotReady is handled — response is 200."""
    sb, _, _ = _seeded_db()
    client = _client(sb)

    def _raise_not_ready(*_a, **_k):
        raise MasteryClassificationNotReady("classification_not_ready: missing=3 duplicate=0")

    monkeypatch.setattr(mock_engine_api, "MasteryWriter", lambda *_a, **_k: type("W", (), {"process_attempt": _raise_not_ready})())
    r1 = client.post("/api/study/mocks/attempts/start", json={"template_slug": "test-mock-1"})
    attempt_id = r1.json()["attempt_id"]
    r2 = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    assert r2.status_code == 200


def test_submit_classification_not_ready_reschedules_mastery(monkeypatch):
    """API submit: when MasteryClassificationNotReady is raised, mastery job is rescheduled pending."""
    sb, _, _ = _seeded_db()

    not_ready_exc = MasteryClassificationNotReady("classification_not_ready: missing=3 duplicate=0")

    async def _raise_not_ready(_attempt_id):
        raise not_ready_exc

    class _FakeWriter:
        async def process_attempt(self, attempt_id):
            raise not_ready_exc

    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    monkeypatch.setattr(mock_engine_api, "MasteryWriter", lambda *_a, **_k: _FakeWriter())
    client = _client(sb, "user-1")
    r1 = client.post("/api/study/mocks/attempts/start", json={"template_slug": "test-mock-1"})
    attempt_id = r1.json()["attempt_id"]
    client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")

    mastery_jobs = [
        j for j in sb.db.get("mock_attempt_jobs", [])
        if j["job_kind"] == JOB_MASTERY_RETRY and j["attempt_id"] == attempt_id
    ]
    assert mastery_jobs, "mastery_retry job must exist after classification-not-ready"
    assert mastery_jobs[0]["status"] == "pending"


def test_submit_classification_not_ready_records_last_error(monkeypatch):
    """last_error on the rescheduled mastery job reflects the not-ready message."""
    sb, _, _ = _seeded_db()
    not_ready_exc = MasteryClassificationNotReady("classification_not_ready: missing=2 duplicate=0")

    class _FakeWriter:
        async def process_attempt(self, _attempt_id):
            raise not_ready_exc

    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    monkeypatch.setattr(mock_engine_api, "MasteryWriter", lambda *_a, **_k: _FakeWriter())
    client = _client(sb, "user-1")
    r1 = client.post("/api/study/mocks/attempts/start", json={"template_slug": "test-mock-1"})
    attempt_id = r1.json()["attempt_id"]
    client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")

    mastery_jobs = [
        j for j in sb.db.get("mock_attempt_jobs", [])
        if j["job_kind"] == JOB_MASTERY_RETRY and j["attempt_id"] == attempt_id
    ]
    assert mastery_jobs
    assert "classification_not_ready" in (mastery_jobs[0].get("last_error") or "")


# ─── D4: analytics_retry job triggers mastery enqueue ─────────────────────────

def test_analytics_retry_job_enqueues_mastery_retry_shadow(monkeypatch):
    """_run_job(JOB_ANALYTICS_RETRY) enqueues mastery_retry when FF=shadow."""
    sb = SBStub({})
    attempt_id = str(uuid.uuid4())
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")

    compute_calls: list[str] = []

    def _fake_compute(supabase, aid):
        compute_calls.append(aid)

    monkeypatch.setattr(svc.attempt_analytics, "compute_and_persist", _fake_compute)

    job = {"job_kind": JOB_ANALYTICS_RETRY, "attempt_id": attempt_id, "id": str(uuid.uuid4())}
    _run_job(sb, job)

    assert compute_calls == [attempt_id]
    mastery_jobs = [
        j for j in sb.db.get("mock_attempt_jobs", [])
        if j["job_kind"] == JOB_MASTERY_RETRY and j["attempt_id"] == attempt_id
    ]
    assert len(mastery_jobs) == 1
    assert mastery_jobs[0]["mastery_flag_state"] == "shadow"


def test_analytics_retry_job_does_not_enqueue_mastery_when_flag_off(monkeypatch):
    """_run_job(JOB_ANALYTICS_RETRY) does NOT enqueue mastery_retry when FF=off."""
    sb = SBStub({})
    attempt_id = str(uuid.uuid4())
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "off")

    monkeypatch.setattr(svc.attempt_analytics, "compute_and_persist", lambda *_: None)

    job = {"job_kind": JOB_ANALYTICS_RETRY, "attempt_id": attempt_id, "id": str(uuid.uuid4())}
    _run_job(sb, job)

    mastery_jobs = sb.db.get("mock_attempt_jobs", [])
    assert not mastery_jobs


def test_analytics_retry_job_enqueues_mastery_retry_live(monkeypatch):
    """_run_job(JOB_ANALYTICS_RETRY) enqueues mastery_retry with flag_state=live when FF=live
    and the attempt owner is in the per-user live allowlist."""
    canary_user = "user-live-canary-0000-000000000001"
    attempt_id = str(uuid.uuid4())
    sb = SBStub({"mock_attempts": [{"id": attempt_id, "user_id": canary_user}]})
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
    monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", canary_user)

    monkeypatch.setattr(svc.attempt_analytics, "compute_and_persist", lambda *_: None)

    job = {"job_kind": JOB_ANALYTICS_RETRY, "attempt_id": attempt_id, "id": str(uuid.uuid4())}
    _run_job(sb, job)

    mastery_jobs = [
        j for j in sb.db.get("mock_attempt_jobs", [])
        if j["job_kind"] == JOB_MASTERY_RETRY
    ]
    assert mastery_jobs[0]["mastery_flag_state"] == "live"


# ─── D2: auto_submit_attempt enqueues mastery_retry ───────────────────────────

def test_auto_submit_enqueues_mastery_retry_when_flag_shadow(monkeypatch):
    """auto_submit_attempt enqueues mastery_retry when FF=shadow."""
    sb, template, _ = _seeded_db()
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")

    start = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start["attempt_id"]
    sb.db["mock_attempts"][0]["expires_at"] = _now_iso()

    auto_submit_attempt(sb, attempt_id)

    mastery_jobs = [
        j for j in sb.db.get("mock_attempt_jobs", [])
        if j["job_kind"] == JOB_MASTERY_RETRY and j["attempt_id"] == attempt_id
    ]
    assert len(mastery_jobs) >= 1
    assert mastery_jobs[0]["mastery_flag_state"] == "shadow"


def test_auto_submit_does_not_enqueue_mastery_when_flag_off(monkeypatch):
    """auto_submit_attempt does NOT enqueue mastery_retry when FF=off."""
    sb, template, _ = _seeded_db()
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "off")

    start = svc.start_attempt(sb, "user-1", "test-mock-1")
    attempt_id = start["attempt_id"]
    sb.db["mock_attempts"][0]["expires_at"] = _now_iso()

    auto_submit_attempt(sb, attempt_id)

    mastery_jobs = [
        j for j in sb.db.get("mock_attempt_jobs", [])
        if j["job_kind"] == JOB_MASTERY_RETRY
    ]
    assert not mastery_jobs


# ─── Idempotency: no duplicate mastery_retry jobs ─────────────────────────────

def test_enqueue_mastery_retry_idempotent_active_job(monkeypatch):
    """enqueue_mastery_retry_required resets an existing active job instead of inserting a duplicate."""
    sb = SBStub({})
    attempt_id = str(uuid.uuid4())
    enqueue_mastery_retry_required(sb, attempt_id, "shadow")
    enqueue_mastery_retry_required(sb, attempt_id, "shadow")

    mastery_jobs = [
        j for j in sb.db.get("mock_attempt_jobs", [])
        if j["job_kind"] == JOB_MASTERY_RETRY and j["attempt_id"] == attempt_id
    ]
    assert len(mastery_jobs) == 1


def test_analytics_retry_d4_idempotent_with_existing_mastery_job(monkeypatch):
    """D4 handoff with an existing active mastery_retry job resets it, not duplicates it."""
    sb = SBStub({})
    attempt_id = str(uuid.uuid4())
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    monkeypatch.setattr(svc.attempt_analytics, "compute_and_persist", lambda *_: None)

    enqueue_mastery_retry_required(sb, attempt_id, "shadow")
    job = {"job_kind": JOB_ANALYTICS_RETRY, "attempt_id": attempt_id, "id": str(uuid.uuid4())}
    _run_job(sb, job)

    mastery_jobs = [
        j for j in sb.db.get("mock_attempt_jobs", [])
        if j["job_kind"] == JOB_MASTERY_RETRY and j["attempt_id"] == attempt_id
    ]
    assert len(mastery_jobs) == 1
