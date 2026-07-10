"""Tests for the learner PYQ summary endpoint + /pyqs phase/subject enrichment
(PR #942 P1 — items 8 & 9)."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import exam_intelligence as ei_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub


def _build_app(sb: SBStub):
    app = FastAPI()
    app.include_router(ei_api.router, prefix="/api")
    ei_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": "u-1", "role": "user", "permissions": []}
    return app


def _seed() -> dict[str, Any]:
    return {
        "exams": [{"id": "e1", "slug": "upsc-cse"}],
        "exam_phases": [{"id": "ph1", "phase_slug": "prelims", "name": "Prelims"}],
        "subjects": [{"id": "s1", "name": "General Studies"}],
        "topics": [{"id": "t1", "subject_id": "s1", "name": "Polity"}],
        "pyq_papers": [
            {"id": "p1", "exam_id": "e1", "year": 2024, "exam_phase_id": "ph1", "trust_status": "verified"},
            {"id": "p2", "exam_id": "e1", "year": 2023, "exam_phase_id": "ph1", "trust_status": "verified"},
            # unverified paper — must be excluded
            {"id": "p3", "exam_id": "e1", "year": 2022, "exam_phase_id": "ph1", "trust_status": "pending"},
        ],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "question_number": 1, "question_text": "Q1", "observed_difficulty": "medium", "reviewer_status": "verified"},
            {"id": "q2", "pyq_paper_id": "p1", "question_number": 2, "question_text": "Q2", "observed_difficulty": "hard", "reviewer_status": "verified"},
            {"id": "q3", "pyq_paper_id": "p2", "question_number": 1, "question_text": "Q3", "observed_difficulty": "medium", "reviewer_status": "verified"},
            # unverified / paper-excluded questions
            {"id": "q4", "pyq_paper_id": "p2", "question_number": 2, "question_text": "Q4", "observed_difficulty": "easy", "reviewer_status": "pending"},
            {"id": "q5", "pyq_paper_id": "p3", "question_number": 1, "question_text": "Q5", "observed_difficulty": "easy", "reviewer_status": "verified"},
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1", "tag_role": "primary", "reviewer_status": "verified"},
            {"question_id": "q2", "topic_id": "t1", "tag_role": "primary", "reviewer_status": "verified"},
            {"question_id": "q3", "topic_id": "t1", "tag_role": "primary", "reviewer_status": "verified"},
        ],
        "pyq_options": [
            {"id": "o1", "question_id": "q1", "option_label": "A", "option_text": "one", "is_correct": True},
        ],
        # Projected bank rows; practice-ready only when projection is active.
        "mock_question_bank": [
            {"id": "b1", "exam_id": "e1", "pyq_paper_id": "p1", "pyq_question_id": "q1", "reviewer_status": "verified", "valid_until": None},
            {"id": "b2", "exam_id": "e1", "pyq_paper_id": "p1", "pyq_question_id": "q2", "reviewer_status": "verified", "valid_until": None},
            {"id": "b3", "exam_id": "e1", "pyq_paper_id": "p2", "pyq_question_id": "q3", "reviewer_status": "verified", "valid_until": None},
        ],
        "pyq_mock_question_projections": [
            {"mock_question_id": "b1", "sync_status": "active"},
            {"mock_question_id": "b2", "sync_status": "active"},
            # b3 projection is NOT active → p2 has 0 practice-ready
            {"mock_question_id": "b3", "sync_status": "inactive"},
        ],
    }


def _summary(sb: SBStub) -> dict:
    client = TestClient(_build_app(sb))
    r = client.get("/api/exam-intelligence/exams/upsc-cse/pyq-summary")
    assert r.status_code == 200
    return r.json()


def test_pyq_summary_verified_only():
    body = _summary(SBStub(_seed()))
    # p3 (pending paper) and q4 (pending question) / q5 (on pending paper) excluded.
    assert body["totals"]["papers"] == 2
    assert body["totals"]["questions"] == 3
    assert {p["paper_id"] for p in body["papers"]} == {"p1", "p2"}


def test_pyq_summary_counts_by_year_phase_subject_difficulty():
    body = _summary(SBStub(_seed()))
    by_year = {row["year"]: row for row in body["by_year"]}
    assert by_year[2024]["questions"] == 2 and by_year[2024]["papers"] == 1
    assert by_year[2023]["questions"] == 1 and by_year[2023]["papers"] == 1

    by_phase = {row["phase_slug"]: row for row in body["by_phase"]}
    assert by_phase["prelims"]["questions"] == 3
    assert by_phase["prelims"]["phase_name"] == "Prelims"

    by_diff = {row["difficulty"]: row["questions"] for row in body["by_difficulty"]}
    assert by_diff == {"medium": 2, "hard": 1}

    by_subject = {row["subject_name"]: row["questions"] for row in body["by_subject"]}
    assert by_subject == {"General Studies": 3}


def test_pyq_summary_paper_practice_ready_count_uses_active_projection():
    body = _summary(SBStub(_seed()))
    papers = {p["paper_id"]: p for p in body["papers"]}
    # p1: b1 + b2 active → 2 ready, enabled.
    assert papers["p1"]["practice_ready_count"] == 2
    assert papers["p1"]["practice_enabled"] is True
    # p2: b3 projection inactive → 0 ready, disabled (even though q3 is verified).
    assert papers["p2"]["practice_ready_count"] == 0
    assert papers["p2"]["practice_enabled"] is False
    assert body["totals"]["projected_practice_ready"] == 2


def test_pyq_list_includes_phase_and_subject_metadata():
    client = TestClient(_build_app(SBStub(_seed())))
    r = client.get("/api/exam-intelligence/exams/upsc-cse/pyqs?page=1&page_size=20")
    assert r.status_code == 200
    items = {it["id"]: it for it in r.json()["items"]}
    q1 = items["q1"]
    assert q1["phase_slug"] == "prelims"
    assert q1["phase_name"] == "Prelims"
    assert q1["subject_name"] == "General Studies"
    assert q1["topic_names"] == ["Polity"]
