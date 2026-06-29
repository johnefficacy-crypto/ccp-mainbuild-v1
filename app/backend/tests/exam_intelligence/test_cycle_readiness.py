"""Tests for the I9 cycle activation checklist (compute_cycle_readiness).

All tests run through the management detail endpoint to validate
end-to-end integration (D01: field on existing endpoint, D04: contract_version).
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as admin_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub

_RECENT = "2026-06-16T00:00:00+00:00"


def _build_app(sb, role="super_admin"):
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api")
    admin_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    user = {
        "id": "admin-1",
        "role": role,
        "permissions": [],
    }
    app.dependency_overrides[get_current_user] = lambda: user
    return app


class _Seed:
    def __init__(self):
        self.db: dict = {t: [] for t in (
            "exams", "exam_phases", "exam_topic_coverage", "syllabus_topic_mentions",
            "exam_policy_updates", "pyq_papers", "pyq_questions",
            "pyq_question_topic_tags", "pyq_options", "organizations", "exam_families",
            "exam_cycles", "document_assets", "document_processing_jobs",
            "exam_competition_metrics",
        )}

    def exam(self, eid, *, name, mode="core", locked=1, vpyq=0, active=True):
        self.db["exams"].append({
            "id": eid, "slug": eid, "name": name, "exam_type": "recruitment",
            "is_active": active, "exam_family_id": None,
            "management_mode": mode, "cadence": "annual",
            "conducting_organization_id": None,
        })
        for i in range(locked):
            self.db["exam_topic_coverage"].append({
                "id": f"{eid}-cl{i}", "exam_id": eid,
                "reviewer_status": "locked", "created_at": _RECENT,
            })
        if vpyq:
            self.db["pyq_papers"].append(
                {"id": f"{eid}-pp", "exam_id": eid, "trust_status": "verified"})
            for i in range(vpyq):
                qid = f"{eid}-vq{i}"
                self.db["pyq_questions"].append({
                    "id": qid, "pyq_paper_id": f"{eid}-pp",
                    "reviewer_status": "verified", "created_at": _RECENT,
                })
                self.db["pyq_question_topic_tags"].append({
                    "id": f"{qid}-t", "question_id": qid,
                    "reviewer_status": "verified", "created_at": _RECENT,
                })
        return self

    def cycle(self, cid, exam_id, *, name="Cycle 2026", year=2026, status="active"):
        self.db["exam_cycles"].append({
            "id": cid, "exam_id": exam_id, "cycle_name": name,
            "year": year, "status": status, "created_at": _RECENT,
        })
        return self

    def phase(self, pid, exam_id, cycle_id):
        self.db["exam_phases"].append({
            "id": pid, "exam_id": exam_id, "exam_cycle_id": cycle_id,
            "phase_name": "Prelims", "phase_slug": "prelims", "phase_order": 1,
            "phase_start": None, "phase_end": None, "status": "expected",
        })
        return self


def _detail(client, eid, **params):
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"/api/admin/exam-intelligence/management/exams/{eid}"
    if qs:
        url += f"?{qs}"
    return client.get(url)


def _client_from_seed(s: _Seed):
    sb = SBStub(s.db)
    return TestClient(_build_app(sb))


def test_contract_version_present():
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    r = _detail(_client_from_seed(s), "e1")
    assert r.status_code == 200
    assert r.json()["contract_version"] == 1


def test_no_cycles_step1_missing():
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    r = _detail(_client_from_seed(s), "e1")
    assert r.status_code == 200
    body = r.json()
    cr = body["cycle_readiness"]
    assert cr is not None
    step1 = cr["steps"][0]
    assert step1["step"] == 1
    assert step1["status"] == "missing"


def test_cycle_no_phases_step2_missing():
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    s.cycle("cy1", "e1")
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step2 = next(st for st in cr["steps"] if st["step"] == 2)
    assert step2["status"] == "missing"


def test_cycle_with_phases_step2_ready():
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    s.cycle("cy1", "e1")
    s.phase("ph1", "e1", "cy1")
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step2 = next(st for st in cr["steps"] if st["step"] == 2)
    assert step2["status"] == "ready"


def test_unknown_cycle_id_returns_200_with_error():
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    r = _detail(_client_from_seed(s), "e1", cycle_id="ghost-cycle")
    assert r.status_code == 200
    body = r.json()
    assert body["cycle_readiness"] is None
    assert body["cycle_readiness_error"] == {"code": "cycle_not_found", "requested_cycle_id": "ghost-cycle"}


def test_index_only_source_docs_not_applicable():
    s = _Seed()
    s.exam("e1", name="Exam1", mode="index_only", locked=1)
    s.cycle("cy1", "e1")
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step3 = next(st for st in cr["steps"] if st["step"] == 3)
    assert step3["status"] == "not_applicable"
    assert step3["not_applicable_reason"] == "optional_for_management_mode"


def test_step1_ready_when_name_and_year():
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    s.cycle("cy1", "e1", name="2026 Cycle", year=2026)
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step1 = next(st for st in cr["steps"] if st["step"] == 1)
    assert step1["status"] == "ready"


def test_hard_gate_missing_when_no_phases():
    """No phases -> step2 missing (hard gate). D03: no overall field on cycle_readiness."""
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    s.cycle("cy1", "e1")
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    assert "overall" not in cr  # D03: overall verdict comes only from work_queue.classify_exam
    step2 = next(st for st in cr["steps"] if st["step"] == 2)
    assert step2["status"] == "missing"
    assert step2["gate_class"] == "hard"
