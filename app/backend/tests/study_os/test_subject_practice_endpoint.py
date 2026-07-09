"""Endpoint tests for the Subject Practice Hub launch orchestrator.

Focus: server-owned subject scope (checkpost #937, fix 1) — a ``topic_pyq``
launch must reject a ``topic_id`` that does not belong to the PATH ``subject_id``
in the caller's resolved exam, and must start when it does. Uses the shared
in-memory ``SBStub``; ``start_pyq_practice`` is stubbed on the success path so the
test exercises the scope gate, not the full attempt-freeze assembly.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import subject_practice
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub

_EXAM = "44444444-4444-4444-4444-444444444444"
_S_QUANT = "22222222-2222-2222-2222-222222222222"
_S_ENGLISH = "11111111-1111-1111-1111-111111111111"
_T_QUANT = "33333333-3333-3333-3333-333333333333"


def _seed():
    return {
        "profiles": [{"id": "u-1", "target_exam": _EXAM}],
        "exams": [{"id": _EXAM, "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_topic_coverage": [
            {"id": "cov-q", "exam_id": _EXAM, "topic_id": _T_QUANT,
             "reviewer_status": "locked"},
        ],
        "topics": [
            {"id": _T_QUANT, "name": "Percentage", "slug": "pct",
             "subject_id": _S_QUANT, "is_active": True},
        ],
        "subjects": [
            {"id": _S_QUANT, "slug": "quant", "name": "Quant", "is_active": True},
            {"id": _S_ENGLISH, "slug": "english", "name": "English", "is_active": True},
        ],
    }


def _client(sb: SBStub):
    app = FastAPI()
    app.include_router(subject_practice.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": "u-1"}
    subject_practice.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


def test_topic_pyq_rejects_cross_subject_topic():
    # T_QUANT belongs to subject S_QUANT; posting it to S_ENGLISH's launch path
    # must be rejected server-side rather than trusting the browser-sent topic.
    resp = _client(SBStub(_seed())).post(
        f"/api/study/subjects/{_S_ENGLISH}/practice/start",
        json={"mode": "topic_pyq", "topic_id": _T_QUANT},
    )
    assert resp.status_code == 422
    assert "subject" in resp.json()["detail"].lower()


def test_topic_pyq_starts_for_in_subject_topic(monkeypatch):
    monkeypatch.setattr(
        subject_practice, "start_pyq_practice",
        lambda *a, **k: {"outcome": "ready", "attempt_id": "att-9"},
    )
    resp = _client(SBStub(_seed())).post(
        f"/api/study/subjects/{_S_QUANT}/practice/start",
        json={"mode": "topic_pyq", "topic_id": _T_QUANT},
    )
    assert resp.status_code == 200
    assert resp.json() == {
        "kind": "pyq_practice",
        "route": "/app/study/mocks/attempts/att-9",
    }
