"""Tests for cycle activation checklist (I9).

Covers all 10 specified scenarios using the SBStub pattern.
"""
from __future__ import annotations

import pytest
from tests.persona_questions._stub import SBStub

from app.exam_intelligence.cycle_checklist import compute_cycle_activation_checklist


def _make_sb(*, exam_id="exam-1", cycle_id="cy-1", cycle_name="2026 Cycle",
             cycle_year=2026, has_phases=False, has_docs=False,
             doc_asset_id=None, extraction_status=None,
             has_locked_coverage=False, has_pending_mentions=False,
             verified_pyq=0, management_mode="core",
             has_comp_metrics=False):
    db = {
        "exam_cycles": [],
        "exam_phases": [],
        "exams": [],
        "exam_documents": [],
        "document_processing_jobs": [],
        "exam_topic_coverage": [],
        "syllabus_topic_mentions": [],
        "pyq_papers": [],
        "pyq_questions": [],
        "pyq_question_topic_tags": [],
        "exam_competition_metrics": [],
        "exam_policy_updates": [],
    }

    db["exams"].append({"id": exam_id, "management_mode": management_mode})
    db["exam_cycles"].append({
        "id": cycle_id, "exam_id": exam_id,
        "cycle_name": cycle_name, "year": cycle_year, "status": "active",
    })

    if has_phases:
        db["exam_phases"].append({"id": "ph-1", "exam_cycle_id": cycle_id, "exam_id": exam_id})

    if has_docs:
        asset_id = doc_asset_id or "asset-1"
        db["exam_documents"].append({"id": "doc-1", "exam_id": exam_id, "document_asset_id": asset_id})
        if extraction_status:
            db["document_processing_jobs"].append({
                "id": "job-1", "asset_id": asset_id,
                "job_type": "text_extract", "status": extraction_status,
                "created_at": "2026-01-01T00:00:00+00:00",
            })

    if has_locked_coverage:
        db["exam_topic_coverage"].append({
            "id": "cov-1", "exam_id": exam_id,
            "reviewer_status": "locked", "exam_cycle_id": None,
        })

    if has_pending_mentions:
        db["syllabus_topic_mentions"].append({
            "id": "men-1", "exam_id": exam_id, "reviewer_status": "pending",
        })

    if verified_pyq > 0:
        db["pyq_papers"].append({"id": "pp-1", "exam_id": exam_id, "trust_status": "verified"})
        for i in range(verified_pyq):
            qid = f"q-{i}"
            db["pyq_questions"].append({
                "id": qid, "pyq_paper_id": "pp-1", "reviewer_status": "verified",
            })
            db["pyq_question_topic_tags"].append({
                "id": f"tag-{i}", "question_id": qid, "reviewer_status": "verified",
            })

    if has_comp_metrics:
        db["exam_competition_metrics"].append({
            "id": "cm-1", "exam_id": exam_id, "reviewer_status": "reviewed",
        })

    return SBStub(db)


def _step(result, step_id):
    steps = result["steps"]
    return next(s for s in steps if s["step_id"] == step_id)


# ── 1. Unknown cycle → None ──────────────────────────────────────────────────

def test_unknown_cycle_returns_none():
    sb = _make_sb()
    result = compute_cycle_activation_checklist(sb, "exam-1", "nonexistent-cycle")
    assert result is None


# ── 2. Wrong exam_id on cycle → None ────────────────────────────────────────

def test_wrong_exam_id_returns_none():
    sb = _make_sb(exam_id="exam-1")
    result = compute_cycle_activation_checklist(sb, "exam-OTHER", "cy-1")
    assert result is None


# ── 3. Missing cycle_name → cycle_details=missing ───────────────────────────

def test_missing_cycle_name_gives_missing():
    sb = _make_sb(cycle_name="")
    result = compute_cycle_activation_checklist(sb, "exam-1", "cy-1")
    assert result is not None
    step = _step(result, "cycle_details")
    assert step["status"] == "missing"
    assert step["note"] is not None


# ── 4. Has name+year → cycle_details=ready ──────────────────────────────────

def test_cycle_name_and_year_gives_ready():
    sb = _make_sb(cycle_name="2026 Cycle", cycle_year=2026)
    result = compute_cycle_activation_checklist(sb, "exam-1", "cy-1")
    step = _step(result, "cycle_details")
    assert step["status"] == "ready"
    assert step["note"] is None


# ── 5. No phases → phases_schedule=missing ──────────────────────────────────

def test_no_phases_gives_missing():
    sb = _make_sb(has_phases=False)
    result = compute_cycle_activation_checklist(sb, "exam-1", "cy-1")
    step = _step(result, "phases_schedule")
    assert step["status"] == "missing"


# ── 6. Has phases → phases_schedule=ready ───────────────────────────────────

def test_has_phases_gives_ready():
    sb = _make_sb(has_phases=True)
    result = compute_cycle_activation_checklist(sb, "exam-1", "cy-1")
    step = _step(result, "phases_schedule")
    assert step["status"] == "ready"


# ── 7. Failed extraction job → extraction=failed ────────────────────────────

def test_failed_extraction_job_gives_failed():
    sb = _make_sb(has_docs=True, doc_asset_id="asset-x", extraction_status="failed")
    result = compute_cycle_activation_checklist(sb, "exam-1", "cy-1")
    step = _step(result, "extraction")
    assert step["status"] == "failed"


# ── 8. No locked coverage → syllabus_mapping=missing ────────────────────────

def test_no_locked_coverage_gives_missing():
    sb = _make_sb(has_locked_coverage=False)
    result = compute_cycle_activation_checklist(sb, "exam-1", "cy-1")
    step = _step(result, "syllabus_mapping")
    assert step["status"] == "missing"
    assert step["note"] is not None


# ── 9. Locked coverage, no pending mentions → syllabus_mapping=ready ────────

def test_locked_coverage_no_pending_gives_ready():
    sb = _make_sb(has_locked_coverage=True, has_pending_mentions=False)
    result = compute_cycle_activation_checklist(sb, "exam-1", "cy-1")
    step = _step(result, "syllabus_mapping")
    assert step["status"] == "ready"


# ── 10. Full ready scenario ──────────────────────────────────────────────────

def test_result_has_nine_steps():
    sb = _make_sb(
        cycle_name="2026 Cycle", cycle_year=2026,
        has_phases=True, has_docs=True, extraction_status="succeeded",
        has_locked_coverage=True, has_pending_mentions=False,
        verified_pyq=1, has_comp_metrics=True,
    )
    result = compute_cycle_activation_checklist(sb, "exam-1", "cy-1")
    assert result is not None
    assert len(result["steps"]) == 9
    assert result["cycle_id"] == "cy-1"
    assert "computed_at" in result


def test_hard_steps_ready_when_all_conditions_met():
    sb = _make_sb(
        cycle_name="2026 Cycle", cycle_year=2026,
        has_phases=True, has_locked_coverage=True,
    )
    result = compute_cycle_activation_checklist(sb, "exam-1", "cy-1")
    assert _step(result, "cycle_details")["status"] == "ready"
    assert _step(result, "phases_schedule")["status"] == "ready"
    assert _step(result, "syllabus_mapping")["status"] == "ready"


def test_pending_mentions_gives_review_pending():
    sb = _make_sb(has_locked_coverage=True, has_pending_mentions=True)
    result = compute_cycle_activation_checklist(sb, "exam-1", "cy-1")
    step = _step(result, "syllabus_mapping")
    assert step["status"] == "review_pending"


def test_gate_class_fields_present():
    sb = _make_sb()
    result = compute_cycle_activation_checklist(sb, "exam-1", "cy-1")
    for step in result["steps"]:
        assert "gate_class" in step
        assert step["gate_class"] in ("hard", "advisory")


def test_step_order_matches_spec():
    from app.exam_intelligence.cycle_checklist import STEP_ORDER
    sb = _make_sb()
    result = compute_cycle_activation_checklist(sb, "exam-1", "cy-1")
    ids = [s["step_id"] for s in result["steps"]]
    assert ids == STEP_ORDER
