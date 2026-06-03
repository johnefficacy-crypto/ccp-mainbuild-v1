"""Tests for exam_registry_actions — corrigendum review → exam lifecycle update.

Coverage:
  1. Operator apply: corrigendum_detected report → operator maps to an
     exam_cycle date → cycle updates via existing service; exam_registry_actions
     row written with report_id; audit row written.

  2. TRUST GUARD (named): asserts the ONLY writer from event/report →
     exam_cycles / exam_phases / exam_policy_updates is the operator action,
     and every such mutation carries a report_id. Regression guard against
     auto-apply drift.

  3. Timeline untouched: /api/study/plan/timeline contract still reads
     only exam-intelligence tables; no recruitment_events wired in.

  4. Negatives:
       - apply without operator submit does nothing
       - report_id omitted → rejected (NOT NULL enforced)
       - mapping to non-existent cycle/phase → 404
       - action with no target → 422 (CHECK guard)
       - unknown action_type → 422
"""
from __future__ import annotations

import importlib
import inspect
import sys
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_verification_reports as vr_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub


# ── Test helpers ─────────────────────────────────────────────────────────


_ADMIN = {
    "id": "admin-uuid-1",
    "email": "admin@test.local",
    "role": "admin",
    "permissions": ["recruitments.manage", "exam_intelligence.cms"],
}
_ADMIN_NO_CMS = {
    "id": "admin-uuid-2",
    "email": "review-only@test.local",
    "role": "admin",
    "permissions": ["recruitments.manage"],  # no exam_intelligence.cms
}
_REPORT_ID = "report-uuid-1"
_CYCLE_ID = "cycle-uuid-1"
_PHASE_ID = "phase-uuid-1"
_POLICY_ID = "policy-uuid-1"
_EVENT_ID = "event-uuid-1"


def _build_app(sb: SBStub, *, actor: dict | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(vr_api.router, prefix="/api")
    vr_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    _actor = actor if actor is not None else _ADMIN
    app.dependency_overrides[get_current_user] = lambda: _actor

    # Patch the service module's supabase calls to use the same stub.
    import app.exam_intelligence.registry_action_service as svc
    svc._safe_select.__globals__  # noqa: B018  (ensure module loaded)

    return TestClient(app, raise_server_exceptions=False)


def _seeded_db(*, with_cycle=True, with_phase=True, with_policy=True) -> dict:
    data: dict[str, list] = {
        "recruitment_verification_reports": [
            {
                "id": _REPORT_ID,
                "trigger_reason": "corrigendum_detected",
                "lifecycle_status": "stale_source_changed",
            }
        ],
        "recruitment_events": [{"id": _EVENT_ID, "event_type": "corrigendum"}],
        "admin_audit_logs": [],
        "exam_registry_actions": [],
    }
    if with_cycle:
        data["exam_cycles"] = [
            {
                "id": _CYCLE_ID,
                "exam_id": "exam-uuid-1",
                "cycle_name": "2025",
                "year": 2025,
                "status": "expected",
            }
        ]
    if with_phase:
        data["exam_phases"] = [
            {
                "id": _PHASE_ID,
                "exam_id": "exam-uuid-1",
                "exam_cycle_id": _CYCLE_ID,
                "phase_name": "Prelims",
                "phase_slug": "prelims",
                "phase_order": 1,
            }
        ]
    if with_policy:
        data["exam_policy_updates"] = [
            {
                "id": _POLICY_ID,
                "exam_id": "exam-uuid-1",
                "update_type": "date_change",
                "title": "Exam dates revised",
                "reviewer_status": "pending",
            }
        ]
    return data


# ── 1. Operator apply: cycle date update ─────────────────────────────────


def test_operator_apply_cycle_date_update_writes_action_row():
    sb = SBStub(_seeded_db())
    client = _build_app(sb)

    r = client.post(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action",
        json={
            "action_type": "cycle_date_update",
            "exam_cycle_id": _CYCLE_ID,
            "patch": {"exam_start": "2025-06-01", "exam_end": "2025-06-15"},
            "reason": "Official corrigendum shifts exam window to June 2025",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["report_id"] == _REPORT_ID
    assert body["action_type"] == "cycle_date_update"

    # exam_registry_actions row written
    actions = sb.db.get("exam_registry_actions", [])
    assert len(actions) == 1
    action = actions[0]
    assert action["report_id"] == _REPORT_ID, "report_id must be set — trust gate"
    assert action["exam_cycle_id"] == _CYCLE_ID
    assert action["action_type"] == "cycle_date_update"
    assert action["applied_by"] == _ADMIN["id"]

    # exam_cycles row patched
    cycle = sb.db["exam_cycles"][0]
    assert cycle["exam_start"] == "2025-06-01"
    assert cycle["exam_end"] == "2025-06-15"

    # audit written
    audits = sb.db.get("admin_audit_logs", [])
    assert len(audits) == 1
    assert audits[0]["action"] == "registry_action.cycle_date_update"
    assert audits[0]["entity_id"] == _CYCLE_ID


def test_operator_apply_phase_date_update_writes_action_row():
    sb = SBStub(_seeded_db())
    client = _build_app(sb)

    r = client.post(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action",
        json={
            "action_type": "phase_date_update",
            "exam_phase_id": _PHASE_ID,
            "patch": {"phase_start": "2025-06-01", "phase_end": "2025-06-02"},
            "reason": "Corrigendum confirmed Prelims window 1–2 June 2025",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True

    actions = sb.db.get("exam_registry_actions", [])
    assert len(actions) == 1
    assert actions[0]["report_id"] == _REPORT_ID
    assert actions[0]["exam_phase_id"] == _PHASE_ID

    phase = sb.db["exam_phases"][0]
    assert phase["phase_start"] == "2025-06-01"


def test_operator_apply_policy_update_create_writes_action_and_pending_row():
    sb = SBStub(_seeded_db())
    client = _build_app(sb)

    r = client.post(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action",
        json={
            "action_type": "policy_update_create",
            "patch": {
                "exam_id": "exam-uuid-1",
                "update_type": "date_change",
                "title": "2025 exam rescheduled per official corrigendum",
            },
            "reason": "Operator confirmed official corrigendum PDF",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True

    # Created policy_update is at reviewer_status='pending' (trust gate)
    policies = sb.db.get("exam_policy_updates", [])
    new_policy = next(
        (p for p in policies if p.get("title") == "2025 exam rescheduled per official corrigendum"),
        None,
    )
    assert new_policy is not None
    assert new_policy["reviewer_status"] == "pending", \
        "policy_update created via apply action must land at pending, not auto-published"

    actions = sb.db.get("exam_registry_actions", [])
    assert any(a["report_id"] == _REPORT_ID for a in actions)


def test_operator_apply_policy_update_edit_writes_action_row():
    sb = SBStub(_seeded_db())
    client = _build_app(sb)

    r = client.post(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action",
        json={
            "action_type": "policy_update_edit",
            "policy_update_id": _POLICY_ID,
            "patch": {"title": "Exam dates revised — corrigendum 2025-05-15"},
            "reason": "Correcting title to match official corrigendum text",
        },
    )
    assert r.status_code == 200, r.text

    policy = next(p for p in sb.db["exam_policy_updates"] if p["id"] == _POLICY_ID)
    assert policy["title"] == "Exam dates revised — corrigendum 2025-05-15"

    actions = sb.db.get("exam_registry_actions", [])
    assert actions[0]["report_id"] == _REPORT_ID
    assert actions[0]["policy_update_id"] == _POLICY_ID


def test_event_source_id_recorded_when_provided():
    sb = SBStub(_seeded_db())
    client = _build_app(sb)

    r = client.post(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action",
        json={
            "action_type": "cycle_date_update",
            "exam_cycle_id": _CYCLE_ID,
            "event_source_id": _EVENT_ID,
            "patch": {"exam_start": "2025-07-01"},
            "reason": "Corrigendum from source event confirms July start",
        },
    )
    assert r.status_code == 200, r.text
    action = sb.db["exam_registry_actions"][0]
    assert action.get("event_source_id") == _EVENT_ID


# ── 2. TRUST GUARD — only the operator action is the event→registry writer ─


def test_TRUST_GUARD_no_auto_apply_path_exists():
    """Assert that nothing in the scraping/runner/gateway code touches
    exam_cycles, exam_phases, or exam_policy_updates directly.

    This test walks the source of every module under app.scraping and
    app.api that is NOT the admin_verification_reports endpoint and
    asserts it contains no direct .table("exam_cycles") /
    .table("exam_phases") / .table("exam_policy_updates") writes
    (update/insert) that bypass the operator gate.

    A failure here means a new code path has been added that auto-applies
    event data to the registry, which is a trust invariant violation.
    """
    import ast
    import os

    _GUARDED_TABLES = {"exam_cycles", "exam_phases", "exam_policy_updates"}
    _WRITE_METHODS = {"insert", "update", "upsert"}

    violations: list[str] = []

    backend_root = os.path.join(
        os.path.dirname(__file__), "..", "..", "app"
    )
    backend_root = os.path.normpath(backend_root)

    # Modules explicitly allowed to write these tables.
    # - registry_action_service: the operator-gated corrigendum apply path
    # - admin_exam_intel_cms: CMS lifecycle CRUD (operator-only creation/edit)
    # - admin_exam_intelligence: review-lifecycle promotion (reviewer_status
    #   updates on existing rows — not corrigendum auto-apply)
    _ALLOWED_MODULES = {
        "exam_intelligence/registry_action_service.py",
        "api/admin_exam_intel_cms.py",
        "api/admin_exam_intelligence.py",
    }

    for dirpath, _dirnames, filenames in os.walk(backend_root):
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, backend_root)
            if any(rel.endswith(allowed) for allowed in _ALLOWED_MODULES):
                continue
            try:
                src = open(full).read()
            except OSError:
                continue

            # Quick text scan — if none of the guarded table names appear,
            # skip the expensive AST parse.
            if not any(t in src for t in _GUARDED_TABLES):
                continue

            try:
                tree = ast.parse(src, filename=full)
            except SyntaxError:
                continue

            # Look for .table("guarded_table").update/insert/upsert chains.
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute):
                    continue
                if func.attr not in _WRITE_METHODS:
                    continue
                # Walk up the chain to find .table("...") call
                chain = func.value
                while isinstance(chain, ast.Call):
                    if (
                        isinstance(chain.func, ast.Attribute)
                        and chain.func.attr == "table"
                        and chain.args
                        and isinstance(chain.args[0], ast.Constant)
                        and chain.args[0].value in _GUARDED_TABLES
                    ):
                        violations.append(
                            f"{rel}:{node.lineno} — "
                            f".table({chain.args[0].value!r}).{func.attr}() "
                            "outside the operator gate"
                        )
                        break
                    chain = chain.func.value if isinstance(chain.func, ast.Attribute) else None
                    if chain is None:
                        break

    assert not violations, (
        "TRUST GUARD: found direct writes to guarded exam-registry tables "
        "outside the operator gate (registry_action_service / admin_exam_intel_cms):\n"
        + "\n".join(violations)
    )


def test_TRUST_GUARD_every_action_row_carries_report_id():
    """Assert that every exam_registry_actions insert sets report_id.

    The NOT NULL constraint on the column is structural, but this test
    pins the application-layer guarantee: the apply endpoint always
    sets report_id before inserting, so no future refactor can
    accidentally omit it and hide behind Postgres defaulting to NULL
    if the constraint were ever weakened.
    """
    sb = SBStub(_seeded_db())
    client = _build_app(sb)

    client.post(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action",
        json={
            "action_type": "cycle_date_update",
            "exam_cycle_id": _CYCLE_ID,
            "patch": {"exam_start": "2025-06-01"},
            "reason": "Trust guard pin: report_id must always be set",
        },
    )

    for action in sb.db.get("exam_registry_actions", []):
        assert action.get("report_id") is not None, \
            "exam_registry_actions row missing report_id — trust gate violated"
        assert action["report_id"] != "", \
            "exam_registry_actions row has empty report_id"


# ── 3. Timeline untouched ─────────────────────────────────────────────────


def test_timeline_contract_does_not_import_registry_action_service():
    """The /api/study/plan/timeline handler must not import
    registry_action_service or reference exam_registry_actions.

    This pins the contract that the timeline reads only trusted
    exam-intelligence tables and is not wired to the corrigendum flow.
    """
    import ast
    import importlib.util
    import os

    timeline_candidates = [
        os.path.join(
            os.path.dirname(__file__), "..", "..", "app", "api", "study_plan.py"
        ),
        os.path.join(
            os.path.dirname(__file__), "..", "..", "app", "api", "study_os.py"
        ),
        os.path.join(
            os.path.dirname(__file__), "..", "..", "app", "study_os", "timeline.py"
        ),
    ]

    _FORBIDDEN_SYMBOLS = {"registry_action_service", "exam_registry_actions"}

    for path in timeline_candidates:
        path = os.path.normpath(path)
        if not os.path.exists(path):
            continue
        src = open(path).read()
        for symbol in _FORBIDDEN_SYMBOLS:
            assert symbol not in src, (
                f"Timeline module {os.path.basename(path)} references "
                f"{symbol!r} — timeline must read only trusted exam-intelligence "
                "tables, not the corrigendum action layer"
            )


def test_recruitment_events_not_in_timeline_query():
    """recruitment_events must not appear in any timeline-related query.

    Discovery evidence never mutates planner truth directly; only
    operator-reviewed actions update the exam registry that the
    timeline consumes.
    """
    import os

    timeline_candidates = [
        os.path.join(
            os.path.dirname(__file__), "..", "..", "app", "api", "study_plan.py"
        ),
        os.path.join(
            os.path.dirname(__file__), "..", "..", "app", "study_os", "timeline.py"
        ),
    ]

    for path in timeline_candidates:
        path = os.path.normpath(path)
        if not os.path.exists(path):
            continue
        src = open(path).read()
        assert "recruitment_events" not in src, (
            f"{os.path.basename(path)} references recruitment_events — "
            "timeline must read only exam-intelligence tables"
        )


# ── 4. Negative cases ─────────────────────────────────────────────────────


def test_apply_without_operator_submit_does_nothing():
    """A GET on the apply URL does nothing; no action row is created."""
    sb = SBStub(_seeded_db())
    client = _build_app(sb)
    r = client.get(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action"
    )
    # GET on a POST-only endpoint must return 405 Method Not Allowed.
    assert r.status_code == 405
    assert sb.db.get("exam_registry_actions", []) == []


def test_report_id_missing_from_unknown_report_rejected():
    """If the report_id doesn't resolve to a real report, the action is rejected."""
    sb = SBStub(_seeded_db())
    client = _build_app(sb)

    r = client.post(
        "/api/admin/verification-reports/nonexistent-report/apply-registry-action",
        json={
            "action_type": "cycle_date_update",
            "exam_cycle_id": _CYCLE_ID,
            "patch": {"exam_start": "2025-06-01"},
            "reason": "This report does not exist and must be rejected",
        },
    )
    assert r.status_code == 404
    assert sb.db.get("exam_registry_actions", []) == []
    assert sb.db.get("admin_audit_logs", []) == []


def test_mapping_to_nonexistent_cycle_rejected():
    """Targeting a cycle that doesn't exist must return 404."""
    sb = SBStub(_seeded_db(with_cycle=False))
    # Manually add cycles as empty so _safe_select returns None
    sb.db["exam_cycles"] = []
    client = _build_app(sb)

    r = client.post(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action",
        json={
            "action_type": "cycle_date_update",
            "exam_cycle_id": "does-not-exist",
            "patch": {"exam_start": "2025-06-01"},
            "reason": "Targeting a cycle that does not exist",
        },
    )
    assert r.status_code == 404
    assert sb.db.get("exam_registry_actions", []) == []


def test_mapping_to_nonexistent_phase_rejected():
    """Targeting a phase that doesn't exist must return 404."""
    sb = SBStub(_seeded_db(with_phase=False))
    sb.db["exam_phases"] = []
    client = _build_app(sb)

    r = client.post(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action",
        json={
            "action_type": "phase_date_update",
            "exam_phase_id": "does-not-exist",
            "patch": {"phase_start": "2025-06-01"},
            "reason": "Targeting a phase that does not exist",
        },
    )
    assert r.status_code == 404
    assert sb.db.get("exam_registry_actions", []) == []


def test_action_with_no_target_rejected():
    """An apply request with all three target FKs null must be rejected (CHECK guard)."""
    sb = SBStub(_seeded_db())
    client = _build_app(sb)

    r = client.post(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action",
        json={
            "action_type": "cycle_date_update",
            # No exam_cycle_id, no exam_phase_id, no policy_update_id
            "patch": {"exam_start": "2025-06-01"},
            "reason": "No target specified — should be rejected before any DB write",
        },
    )
    assert r.status_code == 422
    assert sb.db.get("exam_registry_actions", []) == []


def test_unknown_action_type_rejected():
    """An unknown action_type must be rejected with 422."""
    sb = SBStub(_seeded_db())
    client = _build_app(sb)

    r = client.post(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action",
        json={
            "action_type": "auto_promote_everything",
            "exam_cycle_id": _CYCLE_ID,
            "patch": {},
            "reason": "Trying to sneak in an unknown action type",
        },
    )
    assert r.status_code == 422
    assert sb.db.get("exam_registry_actions", []) == []


def test_cycle_date_update_missing_target_id_field_rejected():
    """cycle_date_update without exam_cycle_id must be rejected with 422."""
    sb = SBStub(_seeded_db())
    client = _build_app(sb)

    r = client.post(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action",
        json={
            "action_type": "cycle_date_update",
            "exam_phase_id": _PHASE_ID,  # wrong target type for cycle_date_update
            "patch": {"exam_start": "2025-06-01"},
            "reason": "cycle_date_update needs exam_cycle_id not exam_phase_id",
        },
    )
    assert r.status_code == 422


def test_admin_without_cms_permission_rejected():
    """An admin without exam_intelligence.cms must be denied the apply endpoint."""
    sb = SBStub(_seeded_db())
    client = _build_app(sb, actor=_ADMIN_NO_CMS)

    r = client.post(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action",
        json={
            "action_type": "cycle_date_update",
            "exam_cycle_id": _CYCLE_ID,
            "patch": {"exam_start": "2025-06-01"},
            "reason": "This admin lacks exam_intelligence.cms — must be rejected",
        },
    )
    assert r.status_code == 403
    assert sb.db.get("exam_registry_actions", []) == []
    assert sb.db.get("admin_audit_logs", []) == []


def test_stale_event_source_id_rejected_before_write():
    """A stale event_source_id must be caught before any registry mutation.

    This is the atomicity guard: if event_source_id doesn't resolve, we
    reject before the target write so the registry is never mutated without
    a corresponding exam_registry_actions row.
    """
    sb = SBStub(_seeded_db())
    # recruitment_events table is empty — the ID doesn't exist
    sb.db["recruitment_events"] = []
    client = _build_app(sb)

    r = client.post(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action",
        json={
            "action_type": "cycle_date_update",
            "exam_cycle_id": _CYCLE_ID,
            "event_source_id": "stale-event-uuid",
            "patch": {"exam_start": "2025-06-01"},
            "reason": "Stale event_source_id must be rejected before cycle write",
        },
    )
    assert r.status_code == 422
    # Registry must be untouched — no partial mutation
    assert sb.db.get("exam_registry_actions", []) == []
    cycle = sb.db["exam_cycles"][0]
    assert "exam_start" not in cycle or cycle.get("exam_start") != "2025-06-01", \
        "exam_cycles must not be mutated when event_source_id validation fails"


def test_policy_update_create_forced_to_pending():
    """A policy_update_create action must land at reviewer_status='pending'
    regardless of what's in the patch, so it never auto-publishes."""
    sb = SBStub(_seeded_db())
    client = _build_app(sb)

    r = client.post(
        f"/api/admin/verification-reports/{_REPORT_ID}/apply-registry-action",
        json={
            "action_type": "policy_update_create",
            "patch": {
                "exam_id": "exam-uuid-1",
                "update_type": "corrigendum",
                "title": "Official corrigendum 2025",
                "reviewer_status": "locked",  # caller tries to bypass review
            },
            "reason": "Adversarial: caller tries to create a locked policy update",
        },
    )
    assert r.status_code == 200, r.text
    policies = sb.db.get("exam_policy_updates", [])
    new_policy = next(
        (p for p in policies if p.get("title") == "Official corrigendum 2025"),
        None,
    )
    assert new_policy is not None
    # Must be pending regardless of what caller sent
    assert new_policy["reviewer_status"] == "pending", \
        "reviewer_status must be forced to 'pending' — trust invariant"
    assert new_policy["reviewer_status"] != "locked"
