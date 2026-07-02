"""Unit tests for the D05 evidence-policy evaluator (document_policy)."""
from __future__ import annotations

from app.exam_intelligence.document_policy import evaluate_required_phases_complete
from tests.persona_questions._stub import SBStub

_RECENT = "2026-06-16T00:00:00+00:00"


def _base_db():
    return {t: [] for t in (
        "exam_evidence_requirements", "exam_evidence_requirement_overrides",
        "exam_document_evidence", "exam_document_evidence_roles",
        "source_registry", "document_processing_jobs", "pyq_papers",
    )}


def _req(db, kind, *, scope="phase", phase_kind="objective_written", cond="always",
         src=True, extract=True, satisfied_by="document_asset", mode="core"):
    db["exam_evidence_requirements"].append({
        "id": f"req-{kind}-{scope}", "management_mode": mode,
        "phase_kind": phase_kind if scope == "phase" else None,
        "evidence_kind": kind, "satisfied_by": satisfied_by, "requirement_level": "required",
        "gate_effect": "block", "scope": scope, "minimum_count": 1,
        "requires_verified_source": src, "requires_extraction": extract,
        "condition_code": cond, "is_active": True,
    })


def _evi(db, exam, kind, *, cycle=None, phase=None, verified=True, official=True,
         active=True, discovery=False, extracted=True, superseded=False, n=1):
    doc = f"doc{n}"; src = f"src{n}"; ev = f"ev{n}"
    db["source_registry"].append({"id": src, "is_active": active,
                                   "is_official_source": official, "discovery_only": discovery})
    db["exam_document_evidence"].append({
        "id": ev, "document_asset_id": doc, "exam_id": exam, "exam_cycle_id": cycle,
        "exam_phase_id": phase, "source_registry_id": src,
        "trust_status": "verified" if verified else "pending",
        "superseded_by_id": "someother" if superseded else None})
    db["exam_document_evidence_roles"].append({
        "document_evidence_id": ev, "evidence_kind": kind,
        "exam_cycle_id": cycle, "exam_phase_id": phase})
    if extracted:
        db["document_processing_jobs"].append({
            "id": f"job{n}", "document_id": doc, "job_type": "text_extract",
            "status": "succeeded", "created_at": _RECENT})


def _eval(db, mode="core", cycle_status="active"):
    sb = SBStub(db)
    phases = [{"id": "pA", "phase_kind": "objective_written", "status": "active"}]
    return evaluate_required_phases_complete(sb, "e1", "cA", mode, phases, cycle_status=cycle_status)


def test_single_requirement_satisfied():
    db = _base_db(); _req(db, "syllabus")
    _evi(db, "e1", "syllabus", cycle="cA", phase="pA")
    assert _eval(db)["complete"] is True


def test_non_official_source_fails_authority_predicate():
    db = _base_db(); _req(db, "syllabus", src=True)
    _evi(db, "e1", "syllabus", cycle="cA", phase="pA", official=False)
    assert _eval(db)["complete"] is False


def test_missing_extraction_fails_when_required():
    db = _base_db(); _req(db, "syllabus", extract=True)
    _evi(db, "e1", "syllabus", cycle="cA", phase="pA", extracted=False)
    assert _eval(db)["complete"] is False


def test_superseded_evidence_does_not_satisfy():
    db = _base_db(); _req(db, "syllabus")
    _evi(db, "e1", "syllabus", cycle="cA", phase="pA", superseded=True)
    assert _eval(db)["complete"] is False


def test_other_cycle_evidence_does_not_satisfy():
    db = _base_db(); _req(db, "syllabus")
    _evi(db, "e1", "syllabus", cycle="cB", phase="pA")  # wrong cycle
    assert _eval(db)["complete"] is False


def test_exam_wide_evidence_satisfies():
    db = _base_db(); _req(db, "syllabus")
    _evi(db, "e1", "syllabus", cycle=None, phase=None)  # exam-wide inherits
    assert _eval(db)["complete"] is True


def test_override_drops_blocker():
    db = _base_db(); _req(db, "syllabus")
    db["exam_evidence_requirement_overrides"].append({
        "exam_id": "e1", "exam_cycle_id": None, "exam_phase_id": None,
        "evidence_kind": "syllabus", "requirement_level": "not_applicable",
        "gate_effect": "none", "minimum_count": None, "requires_verified_source": None,
        "requires_extraction": None, "is_active": True})
    # no evidence, but the override removes the blocker -> complete
    assert _eval(db)["complete"] is True


def test_cycle_scoped_requirement_gated_on_operational_status():
    db = _base_db()
    _req(db, "primary_cycle_document", scope="cycle", cond="cycle_is_operational")
    # non-operational cycle -> requirement not applicable -> complete with no evidence
    assert _eval(db, cycle_status="closed")["complete"] is True
    # operational cycle -> requirement applies -> not complete without evidence
    assert _eval(db, cycle_status="active")["complete"] is False


def test_pyq_requirement_uses_verified_papers():
    db = _base_db(); _req(db, "pyq_paper", satisfied_by="source_registry", src=True, extract=False)
    db["pyq_papers"].append({"id": "p1", "exam_id": "e1", "trust_status": "pending"})
    assert _eval(db)["complete"] is False
    db["pyq_papers"].append({"id": "p2", "exam_id": "e1", "trust_status": "verified"})
    assert _eval(db)["complete"] is True


def test_unclassified_phase_never_complete():
    db = _base_db()
    sb = SBStub(db)
    phases = [{"id": "pA", "phase_kind": None, "status": "active"}]
    res = evaluate_required_phases_complete(sb, "e1", "cA", "core", phases, cycle_status="active")
    assert res["complete"] is False
    assert res["unclassified_phases"] == 1
