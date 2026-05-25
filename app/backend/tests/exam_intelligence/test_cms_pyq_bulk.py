"""Bulk import for pyq-questions (with inline options) and pyq-options."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms"


def _client(sb):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": "super_admin", "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed():
    return {"exams": [{"id": "e1"}], "pyq_papers": [{"id": "p1", "exam_id": "e1"}],
            "pyq_questions": [{"id": "q-pre", "pyq_paper_id": "p1"}]}


def _opts():
    return [{"option_label": lbl, "option_text": lbl, "is_correct": lbl == "B"} for lbl in "ABCD"]


def test_bulk_100_questions_with_inline_options():
    sb = TaxSBStub(_seed())
    rows = [{"pyq_paper_id": "p1", "question_text": f"Q{i}?", "question_type": "mcq", "options": _opts()} for i in range(100)]
    r = _client(sb).post(f"{_BASE}/bulk-import", json={"reason": "bulk seed 100 questions", "entity": "pyq-questions", "rows": rows})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok_count"] == 100
    # 100 new questions (plus the 1 pre-seeded) and 400 options.
    assert len([q for q in sb.db["pyq_questions"] if q.get("question_text")]) == 100
    assert len(sb.db["pyq_options"]) == 400
    assert all(q["reviewer_status"] == "pending" for q in sb.db["pyq_questions"] if q.get("question_text"))
    assert all(res.get("children_created") == 4 for res in body["results"])


def test_bulk_bad_question_type_row_error_rest_succeed():
    sb = TaxSBStub(_seed())
    rows = [{"pyq_paper_id": "p1", "question_text": f"Q{i}?", "question_type": ("essay" if i == 2 else "mcq")} for i in range(5)]
    r = _client(sb).post(f"{_BASE}/bulk-import", json={"reason": "bulk with one bad type", "entity": "pyq-questions", "rows": rows})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok_count"] == 4 and body["error_count"] == 1
    bad = [x for x in body["results"] if not x["ok"]]
    assert len(bad) == 1 and bad[0]["index"] == 2 and "question_type" in bad[0]["error"]


def test_bulk_cap_exceeded_422():
    sb = TaxSBStub(_seed())
    rows = [{"pyq_paper_id": "p1", "question_text": "q"} for _ in range(2001)]
    r = _client(sb).post(f"{_BASE}/bulk-import", json={"reason": "over the questions cap", "entity": "pyq-questions", "rows": rows})
    assert r.status_code == 422, r.text
    assert "at most 2000" in str(r.json().get("detail"))


def test_bulk_options_standalone():
    sb = TaxSBStub(_seed())
    rows = [{"question_id": "q-pre", "option_label": lbl, "option_text": lbl, "is_correct": lbl == "A"} for lbl in "ABCD"]
    r = _client(sb).post(f"{_BASE}/bulk-import", json={"reason": "bulk options for a question", "entity": "pyq-options", "rows": rows})
    assert r.status_code == 200, r.text
    assert r.json()["ok_count"] == 4
    assert len(sb.db["pyq_options"]) == 4
