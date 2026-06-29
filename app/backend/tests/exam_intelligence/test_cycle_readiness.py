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
    """D05 (updated): index_only still requires source provenance; no phases
    means steps 3+ are not_applicable via A2 cascade (not mode-based).
    D15: not_applicable_reason must be 'no_phases_in_cycle' (typed reason required)."""
    s = _Seed()
    s.exam("e1", name="Exam1", mode="index_only", locked=1)
    s.cycle("cy1", "e1")
    # No phases -> steps 3+ should be not_applicable via A2 cascade
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step3 = next(st for st in cr["steps"] if st["step"] == 3)
    assert step3["status"] == "not_applicable"
    assert step3["not_applicable_reason"] == "no_phases_in_cycle"


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


# ---------------------------------------------------------------------------
# A1: no cycle_id -> steps 2-9 not_applicable with no_selected_cycle
# ---------------------------------------------------------------------------

def test_a1_no_cycle_steps_2_to_9_not_applicable():
    """When cycle_id=None, step 1 = missing, steps 2-9 all not_applicable
    with not_applicable_reason='no_selected_cycle'."""
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    r = _detail(_client_from_seed(s), "e1")  # no cycle_id param
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    assert cr is not None
    step1 = next(st for st in cr["steps"] if st["step"] == 1)
    assert step1["status"] == "missing"
    for step_num in range(2, 10):
        step = next((st for st in cr["steps"] if st["step"] == step_num), None)
        assert step is not None, f"step {step_num} missing from response"
        assert step["status"] == "not_applicable", (
            f"step {step_num} expected not_applicable, got {step['status']}"
        )
        assert step["not_applicable_reason"] == "no_selected_cycle", (
            f"step {step_num} wrong reason: {step['not_applicable_reason']}"
        )


# ---------------------------------------------------------------------------
# D06: extraction (step 4) — latest-per-doc semantics
# ---------------------------------------------------------------------------

def _add_doc(s: _Seed, doc_id: str, exam_id: str, job_statuses: list):
    """Add a document_asset for exam_id and jobs with given statuses (in order)."""
    s.db["document_assets"].append({
        "id": doc_id,
        "scope": "admin_exam_intelligence",
        "metadata": {"exam_id": exam_id},
        "status": "uploaded",
    })
    for i, job_status in enumerate(job_statuses):
        s.db["document_processing_jobs"].append({
            "id": f"{doc_id}-job{i}",
            "document_id": doc_id,
            "job_type": "text_extract",
            "status": job_status,
            "created_at": f"2026-06-{10 + i:02d}T00:00:00+00:00",
        })


def test_d06_one_success_among_latest_jobs_ready():
    """One doc latest job = succeeded, another doc latest job = failed.
    Step 4 should be 'ready' because latest-per-doc: doc1 succeeded."""
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    s.cycle("cy1", "e1")
    s.phase("ph1", "e1", "cy1")
    # doc1: only job = succeeded
    _add_doc(s, "doc1", "e1", ["succeeded"])
    # doc2: only job = failed
    _add_doc(s, "doc2", "e1", ["failed"])
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step4 = next(st for st in cr["steps"] if st["step"] == 4)
    assert step4["status"] == "ready", (
        f"Expected ready (one doc succeeded latest), got {step4['status']}"
    )


def test_d06_all_latest_failed_step_is_failed():
    """All documents have latest job = failed. Step 4 should be 'failed'."""
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    s.cycle("cy1", "e1")
    s.phase("ph1", "e1", "cy1")
    _add_doc(s, "doc1", "e1", ["failed"])
    _add_doc(s, "doc2", "e1", ["failed"])
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step4 = next(st for st in cr["steps"] if st["step"] == 4)
    assert step4["status"] == "failed", (
        f"Expected failed (all docs failed), got {step4['status']}"
    )


def test_d06_mixed_failed_unstarted_not_failed():
    """One doc has a failed job, another doc has NO job at all.
    Step 4 should NOT be 'failed' — the unstarted doc makes it 'uploaded'."""
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    s.cycle("cy1", "e1")
    s.phase("ph1", "e1", "cy1")
    # doc1: failed job
    _add_doc(s, "doc1", "e1", ["failed"])
    # doc2: no jobs at all
    s.db["document_assets"].append({
        "id": "doc2",
        "scope": "admin_exam_intelligence",
        "metadata": {"exam_id": "e1"},
        "status": "uploaded",
    })
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step4 = next(st for st in cr["steps"] if st["step"] == 4)
    assert step4["status"] != "failed", (
        f"Expected non-failed (one doc unstarted), got {step4['status']}"
    )
    assert step4["status"] == "uploaded", (
        f"Expected uploaded (one doc unstarted), got {step4['status']}"
    )


# ---------------------------------------------------------------------------
# D08: syllabus_mapping (step 5) — cycle-scoped vs exam-wide rows
# ---------------------------------------------------------------------------

def test_d08_cycle_scoped_takes_precedence():
    """exam_topic_coverage has both a cycle-scoped (locked) and exam-wide row
    for the same (exam_phase_id, topic_id) pair. Cycle-scoped locked row should
    count toward locked_coverage >= 1, making step 5 ready (not missing)."""
    s = _Seed()
    # exam with locked=0 so we can manually control coverage rows
    s.exam("e1", name="Exam1", locked=0)
    s.cycle("cy1", "e1")
    s.phase("ph1", "e1", "cy1")
    # Cycle-scoped locked row
    s.db["exam_topic_coverage"].append({
        "id": "cov-cycle",
        "exam_id": "e1",
        "exam_phase_id": "ph1",
        "topic_id": "t1",
        "exam_cycle_id": "cy1",
        "reviewer_status": "locked",
        "created_at": _RECENT,
    })
    # Exam-wide row for same (phase, topic) — missing status
    s.db["exam_topic_coverage"].append({
        "id": "cov-wide",
        "exam_id": "e1",
        "exam_phase_id": "ph1",
        "topic_id": "t1",
        "exam_cycle_id": None,
        "reviewer_status": "missing",
        "created_at": _RECENT,
    })
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step5 = next(st for st in cr["steps"] if st["step"] == 5)
    # Cycle-scoped locked row should count: locked_coverage >= 1 -> not missing
    assert step5["status"] != "missing", (
        f"Expected non-missing (cycle-scoped locked row exists), got {step5['status']}"
    )


def test_d08_exam_wide_counts_when_no_cycle_row():
    """Only exam-wide rows (exam_cycle_id=None) with reviewer_status=locked.
    No cycle-scoped rows. Should still count toward locked_coverage."""
    s = _Seed()
    s.exam("e1", name="Exam1", locked=0)
    s.cycle("cy1", "e1")
    s.phase("ph1", "e1", "cy1")
    # Exam-wide locked row
    s.db["exam_topic_coverage"].append({
        "id": "cov-wide-locked",
        "exam_id": "e1",
        "exam_phase_id": "ph1",
        "topic_id": "t1",
        "exam_cycle_id": None,
        "reviewer_status": "locked",
        "created_at": _RECENT,
    })
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step5 = next(st for st in cr["steps"] if st["step"] == 5)
    assert step5["status"] != "missing", (
        f"Expected non-missing (exam-wide locked row counts), got {step5['status']}"
    )


# ---------------------------------------------------------------------------
# D10: pyq_readiness (step 6) — verified chain
# ---------------------------------------------------------------------------

def test_d10_one_verified_chain_ready():
    """One pyq_paper verified, one question in it verified, one tag verified.
    Step 6 must be exactly 'ready' (full verified chain exists)."""
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    s.cycle("cy1", "e1")
    s.phase("ph1", "e1", "cy1")
    # Verified paper
    s.db["pyq_papers"].append({
        "id": "pp1", "exam_id": "e1", "trust_status": "verified",
    })
    # Verified question with verified tag
    s.db["pyq_questions"].append({
        "id": "q1", "pyq_paper_id": "pp1",
        "reviewer_status": "verified", "created_at": _RECENT,
    })
    s.db["pyq_question_topic_tags"].append({
        "id": "tg1", "question_id": "q1",
        "reviewer_status": "verified", "created_at": _RECENT,
    })
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step6 = next(st for st in cr["steps"] if st["step"] == 6)
    # Full verified chain exists -> exactly ready
    assert step6["status"] == "ready", (
        f"Expected ready (full verified chain exists), got {step6['status']}"
    )


def test_d10_no_verified_chain_missing():
    """Papers verified but questions are only pending (no verified chain).
    Step 6 = review_pending because papers are verified but questions need review."""
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    s.cycle("cy1", "e1")
    s.phase("ph1", "e1", "cy1")
    # Verified paper
    s.db["pyq_papers"].append({
        "id": "pp1", "exam_id": "e1", "trust_status": "verified",
    })
    # Questions exist but none verified — pending
    s.db["pyq_questions"].append({
        "id": "q1", "pyq_paper_id": "pp1",
        "reviewer_status": "pending", "created_at": _RECENT,
    })
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step6 = next(st for st in cr["steps"] if st["step"] == 6)
    # Verified paper but no verified questions -> review_pending (questions pending review)
    assert step6["status"] == "review_pending", (
        f"Expected review_pending (no verified questions, but paper verified + q pending), got {step6['status']}"
    )


# ---------------------------------------------------------------------------
# D12: review_activate (step 9) — index_only -> not_applicable
# ---------------------------------------------------------------------------

def test_d12_index_only_review_activate_not_applicable():
    """management_mode='index_only' -> step 9 = not_applicable with
    optional_for_management_mode reason."""
    s = _Seed()
    s.exam("e1", name="Exam1", mode="index_only", locked=1)
    s.cycle("cy1", "e1")
    s.phase("ph1", "e1", "cy1")
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step9 = next(st for st in cr["steps"] if st["step"] == 9)
    assert step9["status"] == "not_applicable"
    assert step9["not_applicable_reason"] == "optional_for_management_mode"


# ---------------------------------------------------------------------------
# D05: index_only still requires source_documents (missing, not not_applicable)
# ---------------------------------------------------------------------------

def test_d05_index_only_source_docs_not_missing_not_na():
    """management_mode='index_only', no documents uploaded, but cycle+phase present.
    Step 3 should be 'missing' — index_only still requires source provenance
    per D05. NOT not_applicable."""
    s = _Seed()
    s.exam("e1", name="Exam1", mode="index_only", locked=0)
    s.cycle("cy1", "e1")
    s.phase("ph1", "e1", "cy1")
    # No document_assets for e1
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step3 = next(st for st in cr["steps"] if st["step"] == 3)
    assert step3["status"] == "missing", (
        f"Expected missing for index_only with no docs, got {step3['status']}"
    )


# ---------------------------------------------------------------------------
# A2: cycle provided but no phases -> steps 3-9 not_applicable
# ---------------------------------------------------------------------------

def test_a2_no_phases_steps_3_to_9_not_applicable():
    """cycle_id provided, but no phases in exam_phases.
    Steps 3-9 should be not_applicable (depend on phases being configured).
    D15: not_applicable_reason must be 'no_phases_in_cycle' (not 'no_selected_cycle')."""
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    s.cycle("cy1", "e1", name="Cycle 2026", year=2026)
    # No phases added
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step1 = next(st for st in cr["steps"] if st["step"] == 1)
    assert step1["status"] == "ready"
    step2 = next(st for st in cr["steps"] if st["step"] == 2)
    assert step2["status"] == "missing"
    for step_num in range(3, 10):
        step = next((st for st in cr["steps"] if st["step"] == step_num), None)
        assert step is not None, f"step {step_num} missing from response"
        assert step["status"] == "not_applicable", (
            f"step {step_num} expected not_applicable when no phases, got {step['status']}"
        )
        # A2/D15: typed reason required; must be 'no_phases_in_cycle' (not null, not 'no_selected_cycle')
        assert step["not_applicable_reason"] == "no_phases_in_cycle", (
            f"step {step_num} expected 'no_phases_in_cycle' reason, "
            f"got {step['not_applicable_reason']}"
        )
