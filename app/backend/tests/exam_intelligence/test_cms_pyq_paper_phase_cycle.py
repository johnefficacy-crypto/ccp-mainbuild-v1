"""EI-CLEAN-09 — phase↔cycle consistency on the direct pyq_papers write paths.

The onboarding RPC (migration 220) enforces that a paper's ``exam_phase_id``
belongs to its ``exam_cycle_id``. This suite covers the same rule for the
Advanced Repair paths that write ``pyq_papers`` directly:
``POST /pyq-papers`` (create), ``PATCH /pyq-papers/{id}`` (curate), and
``POST /bulk-import`` (entity=pyq-papers).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms"


def _client(sb: TaxSBStub) -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "email": "a@test.local",
        "role": "super_admin", "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed(*, papers: list[dict] | None = None) -> dict:
    return {
        "exams": [{"id": "exam-1"}, {"id": "exam-2"}],
        "exam_cycles": [
            {"id": "cyc-A", "exam_id": "exam-1"},
            {"id": "cyc-B", "exam_id": "exam-1"},
            {"id": "cyc-exam2", "exam_id": "exam-2"},
        ],
        "exam_phases": [
            {"id": "ph-A", "exam_id": "exam-1", "exam_cycle_id": "cyc-A"},
            {"id": "ph-B", "exam_id": "exam-1", "exam_cycle_id": "cyc-B"},
            {"id": "ph-other", "exam_id": "exam-2", "exam_cycle_id": "cyc-X"},
            {"id": "ph-template", "exam_id": "exam-1", "exam_cycle_id": None},
        ],
        "pyq_papers": list(papers or []),
        "admin_audit_logs": [],
    }


def _create(payload: dict) -> dict:
    return {"reason": "add pyq paper", "payload": payload}


# ── create (POST /pyq-papers) ────────────────────────────────────────────────


def test_create_matching_phase_and_cycle_ok():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE + "/pyq-papers", json=_create(
        {"exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-A", "exam_phase_id": "ph-A"}
    ))
    assert r.status_code == 200, r.text


def test_create_cross_cycle_phase_rejected():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE + "/pyq-papers", json=_create(
        {"exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-A", "exam_phase_id": "ph-B"}
    ))
    assert r.status_code == 422, r.text
    assert "exam_phase_cycle_mismatch" in r.text
    assert len(sb.db["pyq_papers"]) == 0


def test_create_phase_without_cycle_rejected():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE + "/pyq-papers", json=_create(
        {"exam_id": "exam-1", "year": 2024, "exam_phase_id": "ph-A"}
    ))
    assert r.status_code == 422, r.text
    assert "exam_phase_cycle_mismatch" in r.text


def test_create_phase_from_other_exam_rejected():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE + "/pyq-papers", json=_create(
        {"exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-A", "exam_phase_id": "ph-other"}
    ))
    assert r.status_code == 422, r.text
    assert "exam_phase_exam_mismatch" in r.text


def test_create_unknown_phase_rejected():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE + "/pyq-papers", json=_create(
        {"exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-A", "exam_phase_id": "ph-nope"}
    ))
    assert r.status_code == 422, r.text
    assert "exam_phase_not_found" in r.text


def test_create_no_phase_ok():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE + "/pyq-papers", json=_create(
        {"exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-A"}
    ))
    assert r.status_code == 200, r.text


def test_create_exam_level_phase_with_no_cycle_ok():
    # A cycle-agnostic (exam-level) phase on an exam-level paper is consistent
    # (both cycles null) and must remain allowed — the general pyq_papers table
    # supports exam-level phases (unlike the cycle-scoped onboarding modal).
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE + "/pyq-papers", json=_create(
        {"exam_id": "exam-1", "year": 2024, "exam_phase_id": "ph-template"}
    ))
    assert r.status_code == 200, r.text


def test_create_exam_level_phase_with_a_cycle_rejected():
    # Exam-level phase (null cycle) but the paper names a cycle → inconsistent.
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE + "/pyq-papers", json=_create(
        {"exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-A", "exam_phase_id": "ph-template"}
    ))
    assert r.status_code == 422, r.text
    assert "exam_phase_cycle_mismatch" in r.text


# ── create: exam/cycle scope independent of phase (checkpost P1-a) ───────────


def test_create_cross_exam_cycle_without_phase_rejected():
    # exam_id and exam_cycle_id are independent FKs; a cycle owned by another
    # exam must be rejected even when no phase is supplied.
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE + "/pyq-papers", json=_create(
        {"exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-exam2"}
    ))
    assert r.status_code == 422, r.text
    assert "exam_cycle_exam_mismatch" in r.text
    assert len(sb.db["pyq_papers"]) == 0


def test_create_unknown_cycle_rejected():
    sb = TaxSBStub(_seed())
    r = _client(sb).post(_BASE + "/pyq-papers", json=_create(
        {"exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-nope"}
    ))
    assert r.status_code == 422, r.text
    assert "exam_cycle_not_found" in r.text


def test_bulk_import_rejects_cross_exam_cycle_without_phase():
    sb = TaxSBStub(_seed())
    body = {
        "reason": "bulk add pyq papers",
        "entity": "pyq-papers",
        "rows": [
            {"exam_id": "exam-1", "year": 2023, "exam_cycle_id": "cyc-A"},         # ok
            {"exam_id": "exam-1", "year": 2022, "exam_cycle_id": "cyc-exam2"},     # cross-exam cycle
        ],
    }
    r = _client(sb).post(_BASE + "/bulk-import", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok_count"] == 1 and data["error_count"] == 1
    results = {res["index"]: res for res in data["results"]}
    assert "exam_cycle_exam_mismatch" in results[1]["error"]


# ── patch (PATCH /pyq-papers/{id}) ───────────────────────────────────────────


def test_patch_add_cross_cycle_phase_rejected():
    papers = [{"id": "p1", "exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-A", "trust_status": "pending"}]
    sb = TaxSBStub(_seed(papers=papers))
    r = _client(sb).patch(_BASE + "/pyq-papers/p1", json={"reason": "curate paper", "payload": {"exam_phase_id": "ph-B"}})
    assert r.status_code == 422, r.text
    assert "exam_phase_cycle_mismatch" in r.text


def test_patch_change_cycle_to_conflict_with_existing_phase_rejected():
    papers = [{"id": "p1", "exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-A",
               "exam_phase_id": "ph-A", "trust_status": "pending"}]
    sb = TaxSBStub(_seed(papers=papers))
    r = _client(sb).patch(_BASE + "/pyq-papers/p1", json={"reason": "curate paper", "payload": {"exam_cycle_id": "cyc-B"}})
    assert r.status_code == 422, r.text
    assert "exam_phase_cycle_mismatch" in r.text


def test_patch_unrelated_field_on_legacy_mismatch_not_revalidated():
    # A legacy row that already violates the invariant must still accept edits
    # to unrelated fields (the guard only fires when phase/cycle are touched).
    papers = [{"id": "p1", "exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-A",
               "exam_phase_id": "ph-B", "trust_status": "pending"}]
    sb = TaxSBStub(_seed(papers=papers))
    r = _client(sb).patch(_BASE + "/pyq-papers/p1", json={"reason": "curate paper", "payload": {"shift": "Morning"}})
    assert r.status_code == 200, r.text


def test_patch_matching_phase_and_cycle_ok():
    papers = [{"id": "p1", "exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-A", "trust_status": "pending"}]
    sb = TaxSBStub(_seed(papers=papers))
    r = _client(sb).patch(_BASE + "/pyq-papers/p1", json={"reason": "curate paper", "payload": {"exam_phase_id": "ph-A"}})
    assert r.status_code == 200, r.text


def test_patch_exam_id_only_revalidates_retained_cycle():
    # exam_id-only patch must revalidate the RETAINED cycle: cyc-A belongs to
    # exam-1, so moving the paper to exam-2 makes the cycle cross-exam.
    papers = [{"id": "p1", "exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-A", "trust_status": "pending"}]
    sb = TaxSBStub(_seed(papers=papers))
    r = _client(sb).patch(_BASE + "/pyq-papers/p1", json={"reason": "curate paper", "payload": {"exam_id": "exam-2"}})
    assert r.status_code == 422, r.text
    assert "exam_cycle_exam_mismatch" in r.text


def test_patch_exam_id_only_revalidates_retained_phase():
    # No cycle on the row, but a retained phase belongs to exam-1 → moving to
    # exam-2 makes the phase cross-exam.
    papers = [{"id": "p1", "exam_id": "exam-1", "year": 2024, "exam_cycle_id": None,
               "exam_phase_id": "ph-template", "trust_status": "pending"}]
    sb = TaxSBStub(_seed(papers=papers))
    r = _client(sb).patch(_BASE + "/pyq-papers/p1", json={"reason": "curate paper", "payload": {"exam_id": "exam-2"}})
    assert r.status_code == 422, r.text
    assert "exam_phase_exam_mismatch" in r.text


def test_patch_consistent_three_field_correction_ok():
    papers = [{"id": "p1", "exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-A",
               "exam_phase_id": "ph-A", "trust_status": "pending"}]
    sb = TaxSBStub(_seed(papers=papers))
    r = _client(sb).patch(_BASE + "/pyq-papers/p1", json={
        "reason": "curate paper",
        "payload": {"exam_id": "exam-1", "exam_cycle_id": "cyc-B", "exam_phase_id": "ph-B"},
    })
    assert r.status_code == 200, r.text


# ── verified-paper scope lock (checkpost P2) ─────────────────────────────────


def test_patch_scope_field_on_verified_paper_rejected():
    papers = [{"id": "p1", "exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-A",
               "exam_phase_id": "ph-A", "trust_status": "verified"}]
    sb = TaxSBStub(_seed(papers=papers))
    r = _client(sb).patch(_BASE + "/pyq-papers/p1", json={"reason": "curate paper", "payload": {"exam_cycle_id": "cyc-B"}})
    assert r.status_code == 422, r.text
    assert "scope_locked" in r.text


def test_patch_non_scope_field_on_verified_paper_ok():
    papers = [{"id": "p1", "exam_id": "exam-1", "year": 2024, "exam_cycle_id": "cyc-A",
               "exam_phase_id": "ph-A", "trust_status": "verified"}]
    sb = TaxSBStub(_seed(papers=papers))
    r = _client(sb).patch(_BASE + "/pyq-papers/p1", json={"reason": "curate paper", "payload": {"shift": "Evening"}})
    assert r.status_code == 200, r.text


# ── bulk-import (POST /bulk-import, entity=pyq-papers) ────────────────────────


def test_bulk_import_rejects_only_cross_cycle_rows():
    sb = TaxSBStub(_seed())
    body = {
        "reason": "bulk add pyq papers",
        "entity": "pyq-papers",
        "rows": [
            {"exam_id": "exam-1", "year": 2023, "exam_cycle_id": "cyc-A", "exam_phase_id": "ph-A"},   # ok
            {"exam_id": "exam-1", "year": 2022, "exam_cycle_id": "cyc-A", "exam_phase_id": "ph-B"},   # cross-cycle
        ],
    }
    r = _client(sb).post(_BASE + "/bulk-import", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok_count"] == 1
    assert data["error_count"] == 1
    results = {res["index"]: res for res in data["results"]}
    assert results[0]["ok"] is True
    assert results[1]["ok"] is False
    assert "exam_phase_cycle_mismatch" in results[1]["error"]
