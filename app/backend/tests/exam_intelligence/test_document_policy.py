"""Unit tests for the D05 evidence-policy evaluator (document_policy)."""
from __future__ import annotations

from app.exam_intelligence.document_policy import evaluate_required_phases_complete
from tests.persona_questions._stub import SBStub

_RECENT = "2026-06-16T00:00:00+00:00"


def _base_db():
    return {t: [] for t in (
        "exam_evidence_requirements", "exam_evidence_requirement_overrides",
        "exam_document_evidence", "exam_document_evidence_roles",
        "source_registry", "document_processing_jobs", "pyq_papers", "pyq_sources",
    )}


def _pyq(db, *, phase="pA", verified=True, official=True, active=True, discovery=False,
         with_source=True, in_registry=True, n=1):
    """Register a PYQ paper + its source chain (pyq_sources -> source_registry)."""
    psrc = f"psrc{n}" if with_source else None
    if with_source:
        reg = f"pyreg{n}" if in_registry else None
        db["pyq_sources"].append({"id": psrc, "exam_id": "e1", "source_id": reg})
        if in_registry:
            db["source_registry"].append({"id": reg, "is_active": active,
                                          "is_official_source": official, "discovery_only": discovery})
    db["pyq_papers"].append({"id": f"pp{n}", "exam_id": "e1", "exam_phase_id": phase,
                             "year": 2025, "pyq_source_id": psrc,
                             "trust_status": "verified" if verified else "pending"})


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


def test_non_operational_cycle_is_never_complete():
    """D05 §6: a closed/completed/cancelled cycle is not an activation target."""
    db = _base_db(); _req(db, "syllabus")
    _evi(db, "e1", "syllabus", cycle="cA", phase="pA")  # evidence present
    for st in ("closed", "completed", "cancelled"):
        res = _eval(db, cycle_status=st)
        assert res["complete"] is False
        assert res["reason"] == "cycle_not_operational"


def test_cycle_scoped_requirement_applies_on_operational_cycle():
    db = _base_db()
    _req(db, "syllabus")  # phase policy (satisfied below) so the phase isn't empty-policy
    _evi(db, "e1", "syllabus", cycle="cA", phase="pA", n=1)
    _req(db, "primary_cycle_document", scope="cycle", cond="cycle_is_operational")
    # operational cycle -> cycle requirement applies -> not complete without cycle evidence
    assert _eval(db, cycle_status="active")["complete"] is False
    # register cycle-scoped primary_cycle_document -> complete
    _evi(db, "e1", "primary_cycle_document", cycle="cA", phase=None, n=2)
    assert _eval(db, cycle_status="active")["complete"] is True


def test_empty_policy_phase_is_not_ready():
    """Checkpost P1: a classified phase with NO seeded blocking policy must NOT be vacuously
    complete (fail-closed by code, independent of the seed)."""
    db = _base_db()  # no requirements at all
    assert _eval(db, cycle_status="active")["complete"] is False


def test_wrong_role_does_not_satisfy():
    """Evidence-role-match predicate: a doc registered under a different role must not satisfy."""
    db = _base_db(); _req(db, "syllabus")
    _evi(db, "e1", "exam_pattern", cycle="cA", phase="pA")  # wrong role for a syllabus requirement
    assert _eval(db)["complete"] is False


def test_inactive_source_fails_authority():
    db = _base_db(); _req(db, "syllabus", src=True)
    _evi(db, "e1", "syllabus", cycle="cA", phase="pA", active=False)
    assert _eval(db)["complete"] is False


def test_discovery_only_source_fails_authority():
    db = _base_db(); _req(db, "syllabus", src=True)
    _evi(db, "e1", "syllabus", cycle="cA", phase="pA", discovery=True)
    assert _eval(db)["complete"] is False


def test_override_can_promote_advisory_to_blocking():
    """Direction: an override may PROMOTE a warn/advisory base requirement to blocking."""
    db = _base_db()
    # base syllabus is advisory (warn) -> not blocking on its own
    db["exam_evidence_requirements"].append({
        "id": "req-syl-warn", "management_mode": "core", "exam_type": None,
        "phase_kind": "objective_written", "evidence_kind": "syllabus",
        "satisfied_by": "document_asset", "requirement_level": "recommended", "gate_effect": "warn",
        "scope": "phase", "minimum_count": 1, "requires_verified_source": True,
        "requires_extraction": True, "condition_code": "always", "is_active": True})
    # with only the advisory row + no override, base exists but nothing blocks -> complete
    assert _eval(db, cycle_status="active")["complete"] is True
    # exam-level override promotes it to required/block -> now not complete without evidence
    db["exam_evidence_requirement_overrides"].append({
        "exam_id": "e1", "exam_cycle_id": None, "exam_phase_id": None,
        "evidence_kind": "syllabus", "requirement_level": "required", "gate_effect": "block",
        "expires_at": None, "is_active": True})
    assert _eval(db, cycle_status="active")["complete"] is False


def test_expired_override_is_ignored():
    """An expired exam-level 'syllabus -> not_applicable' override must NOT drop the blocker."""
    db = _base_db(); _req(db, "syllabus")
    db["exam_evidence_requirement_overrides"].append({
        "exam_id": "e1", "exam_cycle_id": None, "exam_phase_id": None,
        "evidence_kind": "syllabus", "requirement_level": "not_applicable",
        "gate_effect": "none", "expires_at": "2020-01-01T00:00:00+00:00", "is_active": True})
    assert _eval(db)["complete"] is False  # expired -> blocker remains, no evidence


def test_phase_override_beats_exam_override():
    """Precedence: a phase-level override outranks an exam-level override for the same kind."""
    db = _base_db(); _req(db, "syllabus")
    # exam-level drops the blocker; phase-level re-requires it -> phase wins -> not complete
    db["exam_evidence_requirement_overrides"].append({
        "exam_id": "e1", "exam_cycle_id": None, "exam_phase_id": None,
        "evidence_kind": "syllabus", "requirement_level": "not_applicable",
        "gate_effect": "none", "expires_at": None, "is_active": True})
    db["exam_evidence_requirement_overrides"].append({
        "exam_id": "e1", "exam_cycle_id": None, "exam_phase_id": "pA",
        "evidence_kind": "syllabus", "requirement_level": "required",
        "gate_effect": "block", "expires_at": None, "is_active": True})
    assert _eval(db)["complete"] is False


def test_pyq_requirement_uses_verified_phase_compatible_papers():
    # src=False isolates the phase-compatibility predicate from source authority.
    db = _base_db(); _req(db, "pyq_paper", satisfied_by="source_registry", src=False, extract=False)
    _pyq(db, phase=None, n=1)   # verified but NOT phase-tagged -> does not satisfy
    assert _eval(db)["complete"] is False
    _pyq(db, phase="pA", n=2)   # verified + phase-tagged -> satisfies
    assert _eval(db)["complete"] is True


def test_pyq_other_phase_paper_does_not_satisfy():
    """Cross-phase rejection: a verified paper tagged to a different phase must not satisfy."""
    db = _base_db(); _req(db, "pyq_paper", satisfied_by="source_registry", src=False, extract=False)
    _pyq(db, phase="pOTHER", n=1)
    assert _eval(db)["complete"] is False


def test_pyq_source_authority_resolved_through_registry():
    """requires_verified_source for PYQ resolves pyq_sources -> source_registry and applies the
    active+official+not-discovery predicate (not just a non-null pyq_source_id)."""
    def one(**kw):
        db = _base_db(); _req(db, "pyq_paper", satisfied_by="source_registry", src=True, extract=False)
        _pyq(db, phase="pA", n=1, **kw)
        return _eval(db)["complete"]
    assert one() is True                       # official + active + not discovery -> ok
    assert one(official=False) is False        # aggregator / non-official
    assert one(active=False) is False          # inactive source
    assert one(discovery=True) is False        # discovery-only
    assert one(with_source=False) is False     # null pyq_source_id
    assert one(in_registry=False) is False     # pyq_source not linked to a registry row


def test_requires_human_review_flag_is_honored():
    """When requires_human_review=false a usable non-verified (pending) doc satisfies; when true
    it does not. Rejected/superseded are always rejected."""
    # human_review true (default): pending does NOT satisfy
    db = _base_db(); _req(db, "syllabus")
    _evi(db, "e1", "syllabus", cycle="cA", phase="pA", verified=False)
    assert _eval(db)["complete"] is False
    # human_review false: pending DOES satisfy
    db2 = _base_db()
    db2["exam_evidence_requirements"].append({
        "id": "req-nr", "management_mode": "core", "exam_type": None,
        "phase_kind": "objective_written", "evidence_kind": "syllabus",
        "satisfied_by": "document_asset", "requirement_level": "required", "gate_effect": "block",
        "scope": "phase", "minimum_count": 1, "requires_verified_source": False,
        "requires_human_review": False, "requires_extraction": False,
        "condition_code": "always", "is_active": True})
    _evi(db2, "e1", "syllabus", cycle="cA", phase="pA", verified=False)  # pending
    assert _eval(db2)["complete"] is True
    # ...but a rejected doc never satisfies even when human_review=false
    db2["exam_document_evidence"][0]["trust_status"] = "rejected"
    assert _eval(db2)["complete"] is False


def test_targeted_override_only_affects_matching_base():
    """An override with base_requirement_id applies only to the base row with that id."""
    db = _base_db(); _req(db, "syllabus")  # base id 'req-syllabus-phase'
    db["exam_evidence_requirement_overrides"].append({
        "exam_id": "e1", "base_requirement_id": "some-other-base-id",
        "exam_cycle_id": None, "exam_phase_id": None, "evidence_kind": "syllabus",
        "requirement_level": "not_applicable", "gate_effect": "none",
        "expires_at": None, "is_active": True})
    # override targets a different base -> does NOT drop this blocker -> not complete (no evidence)
    assert _eval(db)["complete"] is False
    # a targeted override matching the actual base id DOES apply
    db["exam_evidence_requirement_overrides"][0]["base_requirement_id"] = "req-syllabus-phase"
    assert _eval(db)["complete"] is True


def test_exam_type_overlay_selects_most_specific_base():
    """Specificity: an exact (mode+exam_type+phase_kind) row beats a (mode+phase_kind) row."""
    db = _base_db()
    _req(db, "syllabus")  # (core, exam_type=None, objective_written) required
    db["exam_evidence_requirements"].append({  # (core, entrance, objective_written) N/A
        "id": "req-et", "management_mode": "core", "exam_type": "entrance",
        "phase_kind": "objective_written", "evidence_kind": "syllabus",
        "satisfied_by": "document_asset", "requirement_level": "not_applicable",
        "gate_effect": "none", "scope": "phase", "minimum_count": 1,
        "requires_verified_source": True, "requires_extraction": True,
        "condition_code": "always", "is_active": True})

    def ev(exam_type):
        sb = SBStub(db)
        phases = [{"id": "pA", "phase_kind": "objective_written", "status": "active"}]
        return evaluate_required_phases_complete(
            sb, "e1", "cA", "core", phases, exam_type=exam_type, cycle_status="active")
    # entrance -> exact row (N/A) wins -> no blocker -> complete without evidence
    assert ev("entrance")["complete"] is True
    # recruitment -> falls back to mode+phase_kind (required) -> not complete
    assert ev("recruitment")["complete"] is False


def test_answer_key_condition_objective_vs_non_objective():
    """objective_pyq_used_for_scoring (conservative default): applies to objective/mixed,
    not to non-written phase kinds."""
    db = _base_db()
    db["exam_evidence_requirements"].append({
        "id": "req-ak-int", "management_mode": "core", "exam_type": None,
        "phase_kind": "interview", "evidence_kind": "answer_key",
        "satisfied_by": "document_asset", "requirement_level": "required", "gate_effect": "block",
        "scope": "phase", "minimum_count": 1, "requires_verified_source": True,
        "requires_extraction": True, "condition_code": "objective_pyq_used_for_scoring",
        "is_active": True})
    sb = SBStub(db)
    phases = [{"id": "pI", "phase_kind": "interview", "status": "active"}]
    # interview: condition false -> answer_key not required -> complete without evidence
    res = evaluate_required_phases_complete(sb, "e1", "cA", "core", phases, cycle_status="active")
    assert res["complete"] is True


def test_unclassified_phase_never_complete():
    db = _base_db()
    sb = SBStub(db)
    phases = [{"id": "pA", "phase_kind": None, "status": "active"}]
    res = evaluate_required_phases_complete(sb, "e1", "cA", "core", phases, cycle_status="active")
    assert res["complete"] is False
    assert res["unclassified_phases"] == 1
