"""exam_phase_sections CMS + exam_topic_coverage.section_id (migrations 030)."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core import config as core_config
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms"
_SEC = f"{_BASE}/exam-phase-sections"
_COV = f"{_BASE}/exam-topic-coverage"


def _client(sb, *, flag=True):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    if flag:
        app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    else:
        core_config.get_settings.cache_clear()
        core_config.get_settings().ADMIN_STUDY_OS_ENABLED = False
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "a1", "role": "super_admin", "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed():
    return {
        "exams": [{"id": "e1"}],
        "exam_phases": [{"id": "ph1", "exam_id": "e1"}, {"id": "ph2", "exam_id": "e1"}],
        "subjects": [{"id": "s1", "is_active": True}],
        "topics": [{"id": "t1", "subject_id": "s1", "is_active": True}],
    }


def test_create_section():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_SEC, json={"reason": "seed section", "payload": {
        "exam_phase_id": "ph1", "subject_id": "s1", "section_label": "GA", "question_count": 25, "marks": 50}})
    assert r.status_code == 200, r.text
    row = sb.db["exam_phase_sections"][0]
    assert row["section_label"] == "GA" and row["exam_phase_id"] == "ph1"


def test_create_section_bad_subject_422():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_SEC, json={"reason": "bad subject", "payload": {
        "exam_phase_id": "ph1", "subject_id": "nope", "section_label": "GA"}})
    assert r.status_code == 422, r.text


def test_section_rejects_unknown_field_422():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_SEC, json={"reason": "stale col", "payload": {
        "exam_phase_id": "ph1", "subject_id": "s1", "section_label": "GA", "section_code": "x"}})
    assert r.status_code == 422 and "section_code" in str(r.json().get("detail"))


def test_patch_section_whitelisted():
    sb = TaxSBStub({**_seed(), "exam_phase_sections": [{"id": "sec1", "exam_phase_id": "ph1", "subject_id": "s1", "section_label": "GA"}]})
    r = _client(sb).patch(f"{_SEC}/sec1", json={"reason": "fix marks", "payload": {"marks": 75, "bogus": 1}})
    # bogus is unknown -> 422 (whitelist enforced)
    assert r.status_code == 422, r.text
    r2 = _client(sb).patch(f"{_SEC}/sec1", json={"reason": "fix marks", "payload": {"marks": 75}})
    assert r2.status_code == 200 and sb.db["exam_phase_sections"][0]["marks"] == 75


def test_bulk_50_sections_one_bad():
    sb = TaxSBStub(_seed())
    rows = [{"exam_phase_id": "ph1", "subject_id": ("bad" if i == 7 else "s1"), "section_label": f"S{i}"} for i in range(50)]
    r = _client(sb).post(f"{_BASE}/bulk-import", json={"reason": "bulk sections", "entity": "exam-phase-sections", "rows": rows})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["ok_count"] == 49 and b["error_count"] == 1


def test_flag_off_404():
    sb = TaxSBStub(_seed())
    try:
        assert _client(sb, flag=False).get(_SEC).status_code == 404
    finally:
        core_config.get_settings.cache_clear()


def test_coverage_section_phase_mismatch_422():
    sb = TaxSBStub({**_seed(), "exam_phase_sections": [{"id": "sec1", "exam_phase_id": "ph2", "subject_id": "s1", "section_label": "GA"}]})
    r = _client(sb).post(_COV, json={"reason": "mismatch section", "payload": {
        "exam_id": "e1", "topic_id": "t1", "exam_phase_id": "ph1", "section_id": "sec1"}})
    assert r.status_code == 422 and "different exam_phase" in str(r.json().get("detail"))


def test_coverage_section_phase_match_ok():
    sb = TaxSBStub({**_seed(), "exam_phase_sections": [{"id": "sec1", "exam_phase_id": "ph1", "subject_id": "s1", "section_label": "GA"}]})
    r = _client(sb).post(_COV, json={"reason": "matching section", "payload": {
        "exam_id": "e1", "topic_id": "t1", "exam_phase_id": "ph1", "section_id": "sec1"}})
    assert r.status_code == 200, r.text
    assert sb.db["exam_topic_coverage"][0]["section_id"] == "sec1"


def test_coverage_without_section_ok():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_COV, json={"reason": "no section", "payload": {"exam_id": "e1", "topic_id": "t1"}})
    assert r.status_code == 200, r.text
    assert sb.db["exam_topic_coverage"][0]["reviewer_status"] == "pending_review"
