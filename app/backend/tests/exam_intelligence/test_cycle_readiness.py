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
            # D05 evidence-policy (migrations 211/212) — mirrored for the document_policy evaluator.
            "exam_evidence_requirements", "exam_evidence_requirement_overrides",
            "exam_document_evidence", "exam_document_evidence_roles", "source_registry",
        )}
        self._ev_seq = 0

    # D05 phase+cycle blocking requirements for a mode (mirror of migrations 211/212, the
    # subset the tests exercise: objective_written phase + cycle primary_cycle_document).
    def policy(self, mode="core"):
        def add(scope, phase_kind, kind, satisfied_by, cond, extract, src):
            self.db["exam_evidence_requirements"].append({
                "id": f"req-{mode}-{scope}-{phase_kind}-{kind}",
                "management_mode": mode, "phase_kind": phase_kind, "evidence_kind": kind,
                "satisfied_by": satisfied_by, "requirement_level": "required",
                "gate_effect": "block", "scope": scope, "minimum_count": 1,
                "requires_verified_source": src, "requires_extraction": extract,
                "condition_code": cond, "is_active": True,
            })
        add("phase", "objective_written", "syllabus", "document_asset", "always", True, True)
        add("phase", "objective_written", "exam_pattern", "document_asset", "always", True, True)
        add("phase", "objective_written", "pyq_paper", "source_registry", "always", False, True)
        add("phase", "objective_written", "answer_key", "document_asset",
            "objective_pyq_used_for_scoring", True, True)
        add("cycle", None, "primary_cycle_document", "document_asset", "cycle_is_operational", True, True)
        return self

    # Register a verified, authoritative, extracted document evidence satisfying `kind`
    # (or a verified pyq_paper when kind == 'pyq_paper').
    def evidence(self, exam_id, kind, *, cycle_id=None, phase_id=None,
                 verified=True, official=True, extracted=True):
        if kind == "pyq_paper":
            self._ev_seq += 1
            self.db["pyq_papers"].append({
                "id": f"{exam_id}-pyq-{self._ev_seq}", "exam_id": exam_id,
                "exam_cycle_id": cycle_id, "exam_phase_id": phase_id, "year": 2025,
                "pyq_source_id": f"pysrc-{self._ev_seq}",
                "trust_status": "verified" if verified else "pending"})
            return self
        self._ev_seq += 1
        n = self._ev_seq
        doc_id = f"doc-{n}"
        src_id = f"src-{n}"
        self.db["document_assets"].append({"id": doc_id, "scope": "admin_exam_intelligence"})
        self.db["source_registry"].append({
            "id": src_id, "is_active": True,
            "is_official_source": official, "discovery_only": False})
        self.db["exam_document_evidence"].append({
            "id": f"ev-{n}", "document_asset_id": doc_id, "exam_id": exam_id,
            "exam_cycle_id": cycle_id, "exam_phase_id": phase_id,
            "source_registry_id": src_id,
            "trust_status": "verified" if verified else "pending",
            "superseded_by_id": None})
        self.db["exam_document_evidence_roles"].append({
            "document_evidence_id": f"ev-{n}", "evidence_kind": kind,
            "exam_cycle_id": cycle_id, "exam_phase_id": phase_id})
        if extracted:
            self.db["document_processing_jobs"].append({
                "id": f"job-{n}", "document_id": doc_id, "job_type": "text_extract",
                "status": "succeeded", "created_at": _RECENT})
        return self

    # Register the full evidence set that makes an objective_written phase + operational
    # cycle evidence-complete under policy(mode).
    def full_objective_evidence(self, exam_id, cycle_id, phase_id):
        for k in ("syllabus", "exam_pattern", "answer_key", "primary_cycle_document"):
            self.evidence(exam_id, k, cycle_id=cycle_id,
                          phase_id=None if k == "primary_cycle_document" else phase_id)
        self.evidence(exam_id, "pyq_paper", cycle_id=cycle_id, phase_id=phase_id)
        return self

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

    def phase(self, pid, exam_id, cycle_id, *, status="expected", phase_kind=None):
        self.db["exam_phases"].append({
            "id": pid, "exam_id": exam_id, "exam_cycle_id": cycle_id,
            "phase_name": "Prelims", "phase_slug": "prelims", "phase_order": 1,
            "phase_start": None, "phase_end": None, "status": status,
            "phase_kind": phase_kind,
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

def _add_doc(s: _Seed, doc_id: str, exam_id: str, job_statuses: list, *, cycle_id: str | None = None):
    """Add a document_asset for exam_id and jobs with given statuses (in order).

    D05 fail-closed: when testing with a selected cycle, pass cycle_id so the doc
    gets tagged to that cycle in metadata; unscoped docs are excluded from step 3/4.
    """
    meta: dict = {"exam_id": exam_id}
    if cycle_id is not None:
        meta["exam_cycle_id"] = cycle_id
    s.db["document_assets"].append({
        "id": doc_id,
        "scope": "admin_exam_intelligence",
        "metadata": meta,
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
    # doc1: only job = succeeded (tagged to cy1 — D05 fail-closed)
    _add_doc(s, "doc1", "e1", ["succeeded"], cycle_id="cy1")
    # doc2: only job = failed (tagged to cy1)
    _add_doc(s, "doc2", "e1", ["failed"], cycle_id="cy1")
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
    _add_doc(s, "doc1", "e1", ["failed"], cycle_id="cy1")
    _add_doc(s, "doc2", "e1", ["failed"], cycle_id="cy1")
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
    # doc1: failed job (tagged to cy1 — D05 fail-closed)
    _add_doc(s, "doc1", "e1", ["failed"], cycle_id="cy1")
    # doc2: no jobs at all (tagged to cy1)
    s.db["document_assets"].append({
        "id": "doc2",
        "scope": "admin_exam_intelligence",
        "metadata": {"exam_id": "e1", "exam_cycle_id": "cy1"},
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
    planner_activation_disabled reason (D12: planner activation not applicable)."""
    s = _Seed()
    s.exam("e1", name="Exam1", mode="index_only", locked=1)
    s.cycle("cy1", "e1")
    s.phase("ph1", "e1", "cy1")
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy1")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step9 = next(st for st in cr["steps"] if st["step"] == 9)
    assert step9["status"] == "not_applicable"
    assert step9["not_applicable_reason"] == "planner_activation_disabled"


# ── D12: Step 9 evaluates the SELECTED cycle directly (no exam-wide leak) ──────

def test_d12_step9_other_cycle_locked_coverage_does_not_activate():
    """FAIL-OPEN REGRESSION: selected Cycle A has no locked coverage; a locked
    coverage row exists only for Cycle B. Step 9 must NOT be ready — Cycle B's
    evidence must not satisfy Cycle A. Previously Step 9 bound to the exam-wide
    classify_exam verdict, which counted the Cycle B row and wrongly said ready."""
    s = _Seed()
    s.exam("e1", name="Exam1", mode="core", locked=0)  # no exam-wide locked
    s.cycle("cA", "e1")
    s.cycle("cB", "e1")
    s.phase("pA", "e1", "cA")
    s.db["exam_topic_coverage"].append({
        "id": "cov-cB", "exam_id": "e1", "exam_phase_id": "pB", "topic_id": "t1",
        "exam_cycle_id": "cB", "reviewer_status": "locked", "created_at": _RECENT,
    })
    r = _detail(_client_from_seed(s), "e1", cycle_id="cA")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step5 = next(st for st in cr["steps"] if st["step"] == 5)
    step9 = next(st for st in cr["steps"] if st["step"] == 9)
    assert step5["status"] == "missing"       # Cycle A has no locked coverage
    assert step9["status"] == "missing"       # ...so activation must not be ready


def test_d12_step9_classified_phase_missing_evidence_not_ready_routes_documents():
    """PR-2 evaluator: a CLASSIFIED phase + locked coverage but NO registered D05 evidence
    must NOT be ready — the phase's blocking evidence requirements are unmet. CTA routes to
    Documents (register/verify evidence), preserving cycle identity."""
    s = _Seed()
    s.exam("e1", name="Exam1", mode="core", locked=1)  # locked coverage present
    s.cycle("cA", "e1")
    s.phase("pA", "e1", "cA", status="active", phase_kind="objective_written")
    s.policy("core")  # requirements exist, but no evidence registered
    r = _detail(_client_from_seed(s), "e1", cycle_id="cA")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step9 = next(st for st in cr["steps"] if st["step"] == 9)
    assert step9["status"] == "missing"
    phase_chk = next(c for c in step9["checks"] if c["check_id"] == "required_phases_complete")
    assert phase_chk["status"] == "missing"
    assert phase_chk["unmet_requirement_count"] >= 1
    url = step9["action_cta"]["url"]
    assert "tab=documents" in url
    assert "cycle=cA" in url


def test_d12_step9_full_evidence_and_coverage_is_ready():
    """PR-2 evaluator: core + cycle details + classified objective_written phase + the full
    D05 evidence set (verified/authoritative/extracted syllabus, pattern, answer-key, primary
    cycle document + verified PYQ) + locked coverage -> Step 9 READY."""
    s = _Seed()
    s.exam("e1", name="Exam1", mode="core", locked=1)
    s.cycle("cA", "e1", status="active")  # operational -> primary_cycle_document required
    s.phase("pA", "e1", "cA", status="active", phase_kind="objective_written")
    s.policy("core")
    s.full_objective_evidence("e1", "cA", "pA")
    r = _detail(_client_from_seed(s), "e1", cycle_id="cA")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step9 = next(st for st in cr["steps"] if st["step"] == 9)
    assert step9["status"] == "ready", step9["checks"]
    assert step9["action_cta"] is None
    phase_chk = next(c for c in step9["checks"] if c["check_id"] == "required_phases_complete")
    assert phase_chk["status"] == "ready"


def test_d12_step9_unverified_evidence_does_not_satisfy():
    """Verified-only: registered but NOT trust-verified evidence must not satisfy a
    requirement — Step 9 stays not ready (D05 human-review predicate)."""
    s = _Seed()
    s.exam("e1", name="Exam1", mode="core", locked=1)
    s.cycle("cA", "e1", status="active")
    s.phase("pA", "e1", "cA", status="active", phase_kind="objective_written")
    s.policy("core")
    # all evidence present but syllabus is only pending (not verified)
    s.evidence("e1", "syllabus", cycle_id="cA", phase_id="pA", verified=False)
    s.evidence("e1", "exam_pattern", cycle_id="cA", phase_id="pA")
    s.evidence("e1", "answer_key", cycle_id="cA", phase_id="pA")
    s.evidence("e1", "primary_cycle_document", cycle_id="cA")
    s.evidence("e1", "pyq_paper", cycle_id="cA")
    r = _detail(_client_from_seed(s), "e1", cycle_id="cA")
    step9 = next(st for st in r.json()["cycle_readiness"]["steps"] if st["step"] == 9)
    assert step9["status"] == "missing"


def test_d12_step9_default_active_phase_lacking_classification_not_ready():
    """Reviewer regression: a phase using the DB default status='active' but lacking
    canonical phase_kind / D05 evidence must NOT let Step 9 reach ready. 'active' is a
    lifecycle default, not a completeness signal — D05 says an active unclassified phase
    requires operator action."""
    s = _Seed()
    s.exam("e1", name="Exam1", mode="core", locked=1)
    s.cycle("cA", "e1")
    s.phase("pA", "e1", "cA", status="active")  # DB default, unclassified
    r = _detail(_client_from_seed(s), "e1", cycle_id="cA")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step9 = next(st for st in cr["steps"] if st["step"] == 9)
    assert step9["status"] == "missing"
    phase_chk = next(c for c in step9["checks"] if c["check_id"] == "required_phases_complete")
    assert phase_chk["status"] == "missing"


def test_d12_step9_light_evaluated_not_na_no_is_active_shortcut():
    """light has no canonical planner-activation source, so it is NOT marked N/A by
    is_active — it is evaluated like core (fail-closed). Step 9 is 'missing', never
    'not_applicable', regardless of is_active."""
    s = _Seed()
    s.exam("e1", name="Exam1", mode="light", locked=1, active=False)
    s.cycle("cA", "e1")
    s.phase("pA", "e1", "cA", status="active")
    r = _detail(_client_from_seed(s), "e1", cycle_id="cA")
    step9 = next(st for st in r.json()["cycle_readiness"]["steps"] if st["step"] == 9)
    assert step9["status"] == "missing"
    assert step9["not_applicable_reason"] is None


def test_d12_step9_coverage_failure_routes_cta_to_syllabus_with_cycle():
    """Locked deep-link contract: when cycle details + phase evidence are complete but locked
    coverage is missing, the CTA routes to Syllabus/coverage AND preserves cycle identity."""
    s = _Seed()
    s.exam("e1", name="Exam1", mode="core", locked=0)  # no coverage
    s.cycle("cA", "e1", status="active")
    s.phase("pA", "e1", "cA", status="active", phase_kind="objective_written")
    s.policy("core")
    s.full_objective_evidence("e1", "cA", "pA")  # evidence complete; only coverage missing
    r = _detail(_client_from_seed(s), "e1", cycle_id="cA")
    step9 = next(st for st in r.json()["cycle_readiness"]["steps"] if st["step"] == 9)
    assert step9["status"] == "missing"
    url = step9["action_cta"]["url"]
    assert "tab=syllabus" in url
    assert "cycle=cA" in url


def test_d12_step9_non_operational_cycle_not_applicable():
    """D05 §6: a closed/completed/cancelled cycle is not an activation target -> Step 9 N/A,
    even with full evidence + coverage (must not false-ready)."""
    for st in ("closed", "completed", "cancelled"):
        s = _Seed()
        s.exam("e1", name="Exam1", mode="core", locked=1)
        s.cycle("cA", "e1", status=st)
        s.phase("pA", "e1", "cA", status="active", phase_kind="objective_written")
        s.policy("core")
        s.full_objective_evidence("e1", "cA", "pA")
        r = _detail(_client_from_seed(s), "e1", cycle_id="cA")
        step9 = next(st_ for st_ in r.json()["cycle_readiness"]["steps"] if st_["step"] == 9)
        assert step9["status"] == "not_applicable", st
        assert step9["not_applicable_reason"] == "planner_activation_disabled"


def test_d12_step9_evaluator_failure_is_fail_soft(monkeypatch):
    """Fail-soft boundary: an evaluator exception must NOT raise out of the endpoint — Step 9
    reports missing (fail-closed) with evaluator_error, checklist still returns 200."""
    import app.exam_intelligence.cycle_readiness as cr

    def _boom(*a, **k):
        raise RuntimeError("transient read failure")
    monkeypatch.setattr(cr, "evaluate_required_phases_complete", _boom)
    s = _Seed()
    s.exam("e1", name="Exam1", mode="core", locked=1)
    s.cycle("cA", "e1", status="active")
    s.phase("pA", "e1", "cA", status="active", phase_kind="objective_written")
    r = _detail(_client_from_seed(s), "e1", cycle_id="cA")
    assert r.status_code == 200
    cr_body = r.json()["cycle_readiness"]
    assert cr_body is not None
    step9 = next(st for st in cr_body["steps"] if st["step"] == 9)
    assert step9["status"] == "missing"
    chk = next(c for c in step9["checks"] if c["check_id"] == "required_phases_complete")
    assert chk["evaluator_error"] is True


def test_d12_step9_setup_cta_preserves_cycle_identity():
    """When cycle details are incomplete, the Setup CTA also preserves ?cycle=<id>."""
    s = _Seed()
    s.exam("e1", name="Exam1", mode="core", locked=1)
    # cycle row missing year -> s1 not ready -> cycle_ok False -> Setup CTA.
    s.db["exam_cycles"].append({
        "id": "cA", "exam_id": "e1", "cycle_name": "Cycle", "year": None,
        "status": "active", "created_at": _RECENT,
    })
    s.phase("pA", "e1", "cA", status="completed")
    r = _detail(_client_from_seed(s), "e1", cycle_id="cA")
    step9 = next(st for st in r.json()["cycle_readiness"]["steps"] if st["step"] == 9)
    url = step9["action_cta"]["url"]
    assert "tab=setup" in url
    assert "cycle=cA" in url


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


# ---------------------------------------------------------------------------
# Cycle A/B isolation: docs tagged to a different cycle must NOT satisfy the
# selected cycle's extraction/source readiness (D05/D06 containment).
# ---------------------------------------------------------------------------

def test_cycle_isolation_other_cycle_doc_not_counted():
    """D05/D06 Cycle A/B isolation: a doc tagged to cycle-B must not count toward
    cycle-A's step 3 (source_documents) or step 4 (extraction) readiness."""
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    s.cycle("cy-a", "e1")
    s.cycle("cy-b", "e1")
    s.phase("ph1", "e1", "cy-a")
    # Doc tagged to cycle-B with a succeeded extraction job.
    s.db["document_assets"].append({
        "id": "doc-b",
        "scope": "admin_exam_intelligence",
        "metadata": {"exam_id": "e1", "exam_cycle_id": "cy-b"},
        "status": "processed",
    })
    s.db["document_processing_jobs"].append({
        "id": "doc-b-job0",
        "document_id": "doc-b",
        "job_type": "text_extract",
        "status": "succeeded",
        "created_at": _RECENT,
    })
    # Query for cycle-A — doc-B must be excluded.
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy-a")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step3 = next(st for st in cr["steps"] if st["step"] == 3)
    step4 = next(st for st in cr["steps"] if st["step"] == 4)
    # No docs for cycle-A -> both steps should be missing, not ready.
    assert step3["status"] == "missing", f"step3 expected missing, got {step3['status']}"
    assert step4["status"] == "missing", f"step4 expected missing, got {step4['status']}"


def test_cycle_isolation_unscoped_doc_not_counted():
    """D05 fail-closed: an unscoped doc (no exam_cycle_id in metadata) must NOT
    satisfy the selected cycle's step 4.  The upload API makes exam_cycle_id optional
    so a cycle-specific doc uploaded without metadata cannot inherit into any cycle."""
    s = _Seed()
    s.exam("e1", name="Exam1", locked=1)
    s.cycle("cy-a", "e1")
    s.phase("ph1", "e1", "cy-a")
    # Unscoped doc (no exam_cycle_id) with a succeeded extraction job.
    s.db["document_assets"].append({
        "id": "doc-wide",
        "scope": "admin_exam_intelligence",
        "metadata": {"exam_id": "e1"},  # no exam_cycle_id -> must NOT count
        "status": "processed",
    })
    s.db["document_processing_jobs"].append({
        "id": "doc-wide-job0",
        "document_id": "doc-wide",
        "job_type": "text_extract",
        "status": "succeeded",
        "created_at": _RECENT,
    })
    r = _detail(_client_from_seed(s), "e1", cycle_id="cy-a")
    assert r.status_code == 200
    cr = r.json()["cycle_readiness"]
    step4 = next(st for st in cr["steps"] if st["step"] == 4)
    # Fail-closed: unscoped doc must not satisfy cycle-A's extraction step.
    assert step4["status"] == "missing", f"step4 expected missing (fail-closed), got {step4['status']}"
