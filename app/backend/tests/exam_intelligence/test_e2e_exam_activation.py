"""End-to-end: an exam goes empty → planner-ready entirely through the CMS.

Seeds the full chain via the CMS write endpoints, promotes the review-gated
rows (mention / tag / coverage), proves the readiness validator passes, then
runs the Study OS planner and asserts it emits a task linked to the locked
coverage row. In-memory stub only — no real DB.
"""
from __future__ import annotations

import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from app.study_os.planner import generate_plan
from scripts import validate_exam_intelligence_seed as validator
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms"


def _cms(sb):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": "super_admin", "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def test_exam_activation_empty_to_planner_ready(monkeypatch):
    sb = TaxSBStub({
        "profiles": [{"id": "u-1", "target_exam": "ssc-cgl"}],
        "study_plan_preferences": [{"user_id": "u-1", "study_policy": {"max_tasks_per_day": 3, "preferred_task_size": "small"}}],
    })
    c = _cms(sb)

    def post(path, payload, reason="e2e exam activation seed step"):
        r = c.post(f"{_BASE}/{path}", json={"reason": reason, "payload": payload})
        assert r.status_code == 200, f"{path}: {r.text}"
        body = r.json()
        return body.get("row") or body.get("question")

    # 1. registry
    fam = post("exam-families", {"slug": "ssc", "name": "SSC"})
    exam = post("exams", {"slug": "ssc-cgl", "name": "SSC CGL", "exam_family_id": fam["id"]})
    post("exam-cycles", {"exam_id": exam["id"], "year": 2026, "cycle_name": "2026", "status": "open"})
    phase = post("exam-phases", {"exam_id": exam["id"], "phase_name": "Tier 1", "phase_slug": "tier-1", "status": "active"})
    # 2-3. taxonomy: subject + topic + microtopic-under-topic
    subj = post("subjects", {"slug": "quant", "name": "Quant"})
    topic = post("topics", {"subject_id": subj["id"], "slug": "percentages", "name": "Percentages", "level": "topic"})
    post("topics", {"subject_id": subj["id"], "slug": "successive-pct", "name": "Successive %",
                    "level": "microtopic", "parent_topic_id": topic["id"]})
    # 4-5. syllabus doc + mention → topic
    doc = post("syllabus-documents", {"exam_id": exam["id"], "document_type": "syllabus_pdf", "title": "Syllabus"})
    post("syllabus-topic-mentions", {"syllabus_document_id": doc["id"], "exam_id": exam["id"],
                                     "topic_id": topic["id"], "mention_type": "explicit"})
    # 6-9. pyq source + paper + question(+4 options) + tag → topic
    post("pyq-sources", {"exam_id": exam["id"], "source_type": "official", "title": "Official"})
    paper = post("pyq-papers", {"exam_id": exam["id"], "year": 2024, "exam_phase_id": phase["id"]})
    q = post("pyq-questions", {"pyq_paper_id": paper["id"], "question_text": "10% of 200?", "question_type": "mcq",
                               "options": [
                                   {"option_label": "A", "option_text": "10", "is_correct": False},
                                   {"option_label": "B", "option_text": "20", "is_correct": True},
                                   {"option_label": "C", "option_text": "30", "is_correct": False},
                                   {"option_label": "D", "option_text": "40", "is_correct": False},
                               ]})
    post("pyq-question-topic-tags", {"question_id": q["id"], "topic_id": topic["id"], "tag_role": "primary"})
    # 10. coverage → topic
    post("exam-topic-coverage", {"exam_id": exam["id"], "topic_id": topic["id"], "source_basis": "pyq_analysis",
                                 "exam_priority_score": 88, "is_high_yield": True, "confidence_score": 0.8})

    # 4 options were created inline with the question.
    assert len(sb.db["pyq_options"]) == 4

    # Promote the review-gated rows (the steps a reviewer performs).
    sb.db["syllabus_topic_mentions"][0]["reviewer_status"] = "verified"
    sb.db["pyq_questions"][0]["reviewer_status"] = "verified"
    sb.db["pyq_question_topic_tags"][0]["reviewer_status"] = "verified"
    sb.db["exam_topic_coverage"][0]["reviewer_status"] = "locked"
    coverage_id = sb.db["exam_topic_coverage"][0]["id"]

    # 11. readiness validator passes.
    monkeypatch.setattr(validator, "get_supabase_admin", lambda: sb)
    monkeypatch.setattr(sys, "argv", ["validate", "--exam-slug", "ssc-cgl", "--strict"])
    assert validator.main() == 0

    # 12. planner runs for the user targeting this exam.
    out = generate_plan(sb, "u-1")

    # 13. assertions
    assert out["generated"] is True
    assert out["task_count"] >= 1
    tasks = sb.db["study_tasks"]
    assert len(tasks) >= 1
    assert any(t["topic_id"] == topic["id"] for t in tasks)
    assert any(t.get("exam_topic_coverage_id") == coverage_id for t in tasks)
