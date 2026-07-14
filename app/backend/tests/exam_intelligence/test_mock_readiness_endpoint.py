"""Wave 4.6D0-BE — GET /api/admin/exam-intelligence/exams/{exam_id}/mock-readiness.

Thin read-only wrapper over the pure ``assemble_mock_readiness_report``
diagnostic (which has its own coverage in test_mock_readiness.py). These tests
pin the endpoint contract: permission gate, exam 404, threshold defaults +
echo, per-phase filter, the aggregated summary, the no-percentage invariant,
and that a real read failure surfaces (never a swallowed "blocked" verdict).
"""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as admin_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub

EXAM = "exam-1"
PHASE = "phase-1"
PHASE2 = "phase-2"
SEC = "sec-1"
SUBJ = "subj-1"

BASE = "/api/admin/exam-intelligence/exams"


def _mcq(idx: int, **over) -> dict:
    row = {
        "id": f"q-{idx}",
        "exam_id": EXAM,
        "subject_id": SUBJ,
        "topic_id": "topic-1",
        "difficulty": "medium",
        "question_type": "mcq",
        "reviewer_status": "verified",
        "is_current": False,
        "is_current_based": False,
        "valid_until": None,
        "source_type": "authored",
        "source_kind": "authored",
    }
    row.update(over)
    return row


def _seed(*, n_questions: int = 40, two_phases: bool = False) -> dict:
    """One exam with a fully-structured, well-stocked phase (verdict=ready).

    With ``two_phases`` a second phase with no sections is added, which the
    diagnostic verdicts as ``blocked`` (no_sections) — useful for the
    phase-filter + summary-aggregation assertions.
    """
    phases = [{"id": PHASE, "exam_id": EXAM, "phase_name": "Prelims", "phase_slug": "prelims"}]
    if two_phases:
        phases.append({"id": PHASE2, "exam_id": EXAM, "phase_name": "Mains", "phase_slug": "mains"})
    return {
        "exams": [{"id": EXAM, "slug": "ssc-cgl", "name": "SSC CGL",
                   "exam_type": "recruitment", "is_active": True}],
        "exam_phases": phases,
        "exam_phase_sections": [
            {"id": SEC, "exam_phase_id": PHASE, "subject_id": SUBJ, "section_label": "A",
             "question_count": 100, "marks": 200, "duration_mins": 120, "sort_order": 0},
        ],
        "mock_question_bank": [_mcq(i) for i in range(n_questions)],
        "exam_topic_coverage": [
            {"id": "cov-1", "exam_id": EXAM, "exam_phase_id": PHASE,
             "section_id": SEC, "reviewer_status": "locked"},
        ],
    }


def _admin_app(sb: SBStub, role: str = "super_admin", *, raise_server_exceptions: bool = True):
    app = FastAPI()
    app.include_router(admin_api.router, prefix="/api")
    admin_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    user = {
        "id": "admin-1",
        "role": role,
        "permissions": ["exam_intelligence.review"] if role == "admin" else [],
    }
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def _iter_strings(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield str(k)
            yield from _iter_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_strings(v)
    else:
        yield str(obj)


# ─── 1. 200 + documented shape; summary equals the per-phase verdicts ──────
def test_returns_documented_shape_and_aggregated_summary():
    client = _admin_app(SBStub(_seed()))
    r = client.get(f"{BASE}/{EXAM}/mock-readiness")
    assert r.status_code == 200
    body = r.json()

    for key in ("exam_id", "exam_phase_id", "generated_at", "thresholds",
                "summary", "phases", "skipped"):
        assert key in body, f"missing top-level key {key!r}"
    assert body["exam_id"] == EXAM
    assert body["summary"] == {"ready": 1, "thin_bank": 0, "blocked": 0}

    phase = body["phases"][0]
    for key in ("exam_phase_id", "phase_slug", "phase_name", "section_structure",
                "locked_coverage", "verified_pyq_tag_depth", "readiness_verdict"):
        assert key in phase, f"missing phase key {key!r}"
    assert phase["readiness_verdict"]["summary"] == {
        "ready": 1, "thin_bank": 0, "blocked": 0, "structural_only": 0,
    }

    # Top-level summary is exactly the element-wise sum of per-phase verdicts
    # (the endpoint aggregates the content-gated ready/thin/blocked buckets).
    agg = {"ready": 0, "thin_bank": 0, "blocked": 0}
    for ph in body["phases"]:
        for k in agg:
            agg[k] += ph["readiness_verdict"]["summary"][k]
    assert body["summary"] == agg


# ─── 2. Permission gate matches sibling reads ──────────────────────────────
def test_permission_gate():
    assert _admin_app(SBStub(_seed()), role="user").get(
        f"{BASE}/{EXAM}/mock-readiness"
    ).status_code == 403
    assert _admin_app(SBStub(_seed()), role="super_admin").get(
        f"{BASE}/{EXAM}/mock-readiness"
    ).status_code == 200
    assert _admin_app(SBStub(_seed()), role="admin").get(
        f"{BASE}/{EXAM}/mock-readiness"
    ).status_code == 200


# ─── 3. exam_phase_id filter narrows the response ──────────────────────────
def test_phase_filter_narrows_response():
    client = _admin_app(SBStub(_seed(two_phases=True)))

    unfiltered = client.get(f"{BASE}/{EXAM}/mock-readiness").json()
    assert {p["exam_phase_id"] for p in unfiltered["phases"]} == {PHASE, PHASE2}
    # phase-2 has no sections → blocked; phase-1 → ready.
    assert unfiltered["summary"] == {"ready": 1, "thin_bank": 0, "blocked": 1}

    filtered = client.get(f"{BASE}/{EXAM}/mock-readiness", params={"exam_phase_id": PHASE}).json()
    assert [p["exam_phase_id"] for p in filtered["phases"]] == [PHASE]
    assert filtered["exam_phase_id"] == PHASE
    assert filtered["summary"] == {"ready": 1, "thin_bank": 0, "blocked": 0}


# ─── 4. Threshold defaults applied + echoed; explicit override echoed ──────
def test_threshold_defaults_and_override_echo():
    client = _admin_app(SBStub(_seed()))

    default_body = client.get(f"{BASE}/{EXAM}/mock-readiness").json()
    assert default_body["thresholds"] == {"min_per_section": 30, "min_locked_coverage": 1}

    override_body = client.get(
        f"{BASE}/{EXAM}/mock-readiness",
        params={"min_per_section": 5, "min_locked_coverage": 2},
    ).json()
    assert override_body["thresholds"] == {"min_per_section": 5, "min_locked_coverage": 2}


# ─── 5. Unknown exam → 404 ─────────────────────────────────────────────────
def test_unknown_exam_returns_404():
    r = _admin_app(SBStub(_seed())).get(f"{BASE}/no-such-exam/mock-readiness")
    assert r.status_code == 404


# ─── 5b. exam_phase_id validation (mirrors cycle strictness) ───────────────
def test_unknown_phase_returns_404():
    r = _admin_app(SBStub(_seed())).get(
        f"{BASE}/{EXAM}/mock-readiness", params={"exam_phase_id": "no-such-phase"}
    )
    assert r.status_code == 404


def test_phase_belonging_to_another_exam_returns_422():
    seed = _seed()
    seed["exams"].append({"id": "other-exam", "slug": "other", "name": "Other",
                          "exam_type": "recruitment", "is_active": True})
    seed["exam_phases"].append({"id": "foreign-phase", "exam_id": "other-exam",
                                "phase_name": "X", "phase_slug": "x"})
    r = _admin_app(SBStub(seed)).get(
        f"{BASE}/{EXAM}/mock-readiness", params={"exam_phase_id": "foreign-phase"}
    )
    assert r.status_code == 422


def test_valid_phase_under_exam_returns_200_narrowed():
    r = _admin_app(SBStub(_seed(two_phases=True))).get(
        f"{BASE}/{EXAM}/mock-readiness", params={"exam_phase_id": PHASE}
    )
    assert r.status_code == 200
    body = r.json()
    assert [p["exam_phase_id"] for p in body["phases"]] == [PHASE]


# ─── 6. No percentage anywhere in the response (D-E) ───────────────────────
def test_no_percentage_in_response():
    body = _admin_app(SBStub(_seed(two_phases=True))).get(f"{BASE}/{EXAM}/mock-readiness").json()
    blob = json.dumps(body).lower()
    assert "percent" not in blob
    assert "%" not in blob
    # No key looks like a percentage field either.
    assert not any("percent" in s.lower() for s in _iter_strings(body))


# ─── 7. A real read failure surfaces (never a swallowed verdict) ───────────
def test_underlying_read_failure_surfaces(monkeypatch):
    def _boom(*_a, **_k):
        raise RuntimeError("supabase exploded")

    monkeypatch.setattr(admin_api, "assemble_mock_readiness_report", _boom)
    client = _admin_app(SBStub(_seed()), raise_server_exceptions=False)
    r = client.get(f"{BASE}/{EXAM}/mock-readiness")
    assert r.status_code == 500
    # The failure is NOT swallowed into a misleading 200 "blocked" verdict.
    assert "summary" not in r.text


# ─── 8. Route uniqueness guard stays green ─────────────────────────────────
def test_route_is_registered_once_without_double_prefix():
    import server  # noqa: PLC0415 — loads every router

    target = "/api/admin/exam-intelligence/exams/{exam_id}/mock-readiness"
    matches = [
        r for r in server.app.routes
        if getattr(r, "path", None) == target and "GET" in (getattr(r, "methods", None) or set())
    ]
    assert len(matches) == 1
    assert not any("/api/api/" in getattr(r, "path", "") for r in server.app.routes)
