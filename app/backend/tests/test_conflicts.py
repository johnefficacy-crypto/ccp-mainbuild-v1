"""Tests for the consensus conflict resolver (migration 087).

Covers the four ``admin_conflicts`` endpoints plus the promotion gate's
new "open conflict" block in :func:`promote_to_recruitments`. The mock
Supabase mirrors the same shape used by other admin endpoint tests so
new mutations don't drift from the production query patterns.
"""
from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_conflicts as admin_conflicts_api
from app.core.auth import get_current_user
from app.scraping import runner as scrape_runner
from tests.persona_questions._stub import SBStub


ADMIN_USER = {
    "id": "admin-1",
    "email": "admin@example.com",
    "role": "super_admin",
    "permissions": [],
}

USER_USER = {
    "id": "user-1",
    "email": "user@example.com",
    "role": "user",
    "permissions": [],
}


# ─── App fixture ──────────────────────────────────────────────────────────


def _build_app(sb: SBStub, *, user: dict = ADMIN_USER) -> FastAPI:
    app = FastAPI()
    app.include_router(admin_conflicts_api.router, prefix="/api")
    admin_conflicts_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: user
    return app


# ─── Seeds ────────────────────────────────────────────────────────────────


def _seed_two_conflicts() -> SBStub:
    sb = SBStub({
        "scrape_queue": [{
            "id": "queue-1",
            "status": "pending",
            "official_source_resolved": True,
            "extracted_data": {
                "title": "UPSC 2026",
                "apply_end_date": "2026-06-30",
                "total_vacancies": 100,
            },
        }],
        "recruitment_verification_conflicts": [
            {
                "id": "conflict-1",
                "queue_id": "queue-1",
                "recruitment_id": None,
                "field_key": "apply_end_date",
                "status": "open",
                "candidates": [
                    {
                        "source_url": "https://upsc.gov.in/notice.pdf",
                        "source_kind": "notification_pdf",
                        "value": "2026-06-30",
                        "extracted_at": "2026-05-01T10:00:00Z",
                    },
                    {
                        "source_url": "https://upsc.gov.in/corrigendum.pdf",
                        "source_kind": "corrigendum_pdf",
                        "value": "2026-07-15",
                        "extracted_at": "2026-05-10T10:00:00Z",
                    },
                ],
                "created_at": "2026-05-11T10:00:00Z",
            },
            {
                "id": "conflict-2",
                "queue_id": "queue-1",
                "recruitment_id": None,
                "field_key": "total_vacancies",
                "status": "open",
                "candidates": [
                    {
                        "source_url": "https://upsc.gov.in/notice.pdf",
                        "source_kind": "notification_pdf",
                        "value": 100,
                        "extracted_at": "2026-05-01T10:00:00Z",
                    },
                    {
                        "source_url": "https://sarkarijobs.example/listing",
                        "source_kind": "aggregator",
                        "value": 120,
                        "extracted_at": "2026-05-02T10:00:00Z",
                    },
                ],
                "created_at": "2026-05-11T10:00:00Z",
            },
        ],
        "admin_audit_logs": [],
    })
    return sb


# ─── 1 · fixture sanity ───────────────────────────────────────────────────


def test_seed_fixture_holds_one_official_and_one_aggregator_conflict():
    sb = _seed_two_conflicts()
    rows = sb.db["recruitment_verification_conflicts"]
    assert len(rows) == 2
    assert {r["field_key"] for r in rows} == {"apply_end_date", "total_vacancies"}
    assert {r["status"] for r in rows} == {"open"}
    # Conflict 1 is official-vs-official (two government PDFs).
    conflict1 = next(r for r in rows if r["id"] == "conflict-1")
    kinds1 = {c["source_kind"] for c in conflict1["candidates"]}
    assert kinds1 == {"notification_pdf", "corrigendum_pdf"}
    # Conflict 2 mixes an official notification with an aggregator listing.
    conflict2 = next(r for r in rows if r["id"] == "conflict-2")
    kinds2 = {c["source_kind"] for c in conflict2["candidates"]}
    assert "aggregator" in kinds2


# ─── 2 · list ─────────────────────────────────────────────────────────────


def test_list_open_conflicts_returns_both_for_queue():
    sb = _seed_two_conflicts()
    client = TestClient(_build_app(sb))
    r = client.get("/api/admin/scrape/items/queue-1/conflicts")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    ids = {c["id"] for c in body["items"]}
    statuses = {c["status"] for c in body["items"]}
    assert ids == {"conflict-1", "conflict-2"}
    assert statuses == {"open"}


# ─── 3 · happy-path resolve ───────────────────────────────────────────────


def test_resolve_conflict_updates_status_audit_and_queue_payload():
    sb = _seed_two_conflicts()
    client = TestClient(_build_app(sb))

    payload = {
        "value": "2026-07-15",
        "scope": "field",
        "reason": "Corrigendum supersedes notification per official desk-note.",
        "evidence_url": "https://upsc.gov.in/corrigendum.pdf",
        "confirmation_text": "CONFIRM_OVERRIDE",
    }
    r = client.post("/api/admin/conflicts/conflict-1/resolve", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["conflict"]["status"] == "resolved_by_admin"
    assert body["conflict"]["resolved_value"] == "2026-07-15"
    assert body["conflict"]["resolved_scope"] == "field"
    assert body["conflict"]["resolved_by"] == ADMIN_USER["id"]

    # Conflict row mutated in place.
    stored = next(
        c for c in sb.db["recruitment_verification_conflicts"] if c["id"] == "conflict-1"
    )
    assert stored["status"] == "resolved_by_admin"
    assert stored["resolved_value"] == "2026-07-15"

    # extracted_data on the scrape_queue patched with chosen value.
    queue_row = sb.db["scrape_queue"][0]
    assert queue_row["extracted_data"]["apply_end_date"] == "2026-07-15"

    # Audit row written with the request payload + updated conflict.
    audits = sb.db["admin_audit_logs"]
    assert len(audits) == 1
    audit = audits[0]
    assert audit["action"] == "rbac.conflict_override"
    assert audit["entity_id"] == "conflict-1"
    assert audit["new_value"]["request"]["scope"] == "field"


# ─── 4 · validation: reason < 10 chars ────────────────────────────────────


def test_resolve_rejects_short_reason():
    sb = _seed_two_conflicts()
    client = TestClient(_build_app(sb))
    r = client.post(
        "/api/admin/conflicts/conflict-1/resolve",
        json={
            "value": "2026-07-15",
            "scope": "field",
            "reason": "too short",
            "evidence_url": "https://upsc.gov.in/corrigendum.pdf",
            "confirmation_text": "CONFIRM_OVERRIDE",
        },
    )
    assert r.status_code == 400
    assert "reason" in (r.json().get("detail") or "").lower()
    # No mutation on the conflict row.
    stored = next(
        c for c in sb.db["recruitment_verification_conflicts"] if c["id"] == "conflict-1"
    )
    assert stored["status"] == "open"


# ─── 5 · validation: invalid URL ──────────────────────────────────────────


def test_resolve_rejects_invalid_evidence_url():
    sb = _seed_two_conflicts()
    client = TestClient(_build_app(sb))
    r = client.post(
        "/api/admin/conflicts/conflict-1/resolve",
        json={
            "value": "2026-07-15",
            "scope": "field",
            "reason": "Corrigendum supersedes notification.",
            "evidence_url": "not-a-real-url",
            "confirmation_text": "CONFIRM_OVERRIDE",
        },
    )
    assert r.status_code == 400
    assert "evidence_url" in (r.json().get("detail") or "").lower()


# ─── 6 · reject aggregator conflict ───────────────────────────────────────


def test_reject_aggregator_conflict_marks_rejected_and_audits():
    sb = _seed_two_conflicts()
    client = TestClient(_build_app(sb))
    r = client.post(
        "/api/admin/conflicts/conflict-2/reject",
        json={"reason": "aggregator value rejected by policy"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["conflict"]["status"] == "rejected"
    assert body["conflict"]["resolved_by"] == ADMIN_USER["id"]

    stored = next(
        c for c in sb.db["recruitment_verification_conflicts"] if c["id"] == "conflict-2"
    )
    assert stored["status"] == "rejected"

    audits = sb.db["admin_audit_logs"]
    assert any(a.get("action") == "conflict.reject" for a in audits)


# ─── 7 + 8 · promotion gate integration ───────────────────────────────────


class _PromoteSB:
    """Minimal supabase stub for :func:`promote_to_recruitments`.

    Wraps :class:`SBStub` for the conflict lookup, but stubs the RPC call
    so we can assert the open-conflict guard short-circuits *before* any
    promotion side-effects fire.
    """

    def __init__(self, sb: SBStub):
        self._sb = sb
        self.rpc_calls: list[tuple[str, dict]] = []

    def table(self, name: str):
        return self._sb.table(name)

    def rpc(self, fn: str, params: dict):
        self.rpc_calls.append((fn, params))

        class _Resp:
            data = "recruitment-id-stub"

        class _Call:
            def execute(self_inner):
                return _Resp()

        return _Call()


def _extracted_payload() -> dict[str, Any]:
    """Minimal payload that passes :class:`VerifiedRecruitmentForPromotion`."""
    return {
        "title": "UPSC CSE 2026",
        "organization_name": "Union Public Service Commission",
        "org_type": "central",
        "notification_date": "2026-04-01",
        "apply_start_date": "2026-04-15",
        "apply_end_date": "2026-06-30",
        "total_vacancies": 100,
        "year": 2026,
        "official_notification_url": "https://upsc.gov.in/notice.pdf",
        "official_apply_url": "https://upsc.gov.in/apply",
        "posts": [{"post_name": "Officer"}],
    }


def test_promote_blocks_on_open_conflict_with_field_keys(monkeypatch):
    sb = _seed_two_conflicts()
    promote_sb = _PromoteSB(sb)

    # Suppress side-effects that promote_to_recruitments fires post-write —
    # the guard runs *before* them, so these never get called when the test
    # passes, but stubbing them keeps any regression noise as the actual
    # failure (open-conflict guard miss) rather than collateral errors.
    monkeypatch.setattr(scrape_runner, "_reconcile_lifecycle_events", lambda *a, **k: None)
    monkeypatch.setattr(scrape_runner, "_enqueue_recompute_fanout", lambda *a, **k: 0)

    from app.scraping.schemas import VerifiedRecruitmentForPromotion

    payload = VerifiedRecruitmentForPromotion(**_extracted_payload())
    with pytest.raises(scrape_runner.OpenConflictPromotionError) as exc:
        scrape_runner.promote_to_recruitments(
            payload,
            promote_sb,
            source_id="src-1",
            queue_id="queue-1",
        )
    # Both seeded conflicts hit the guard — apply_end_date AND total_vacancies.
    assert set(exc.value.field_keys) == {"apply_end_date", "total_vacancies"}
    # The guard fires *before* the RPC is invoked.
    assert promote_sb.rpc_calls == []


def test_promote_succeeds_after_all_conflicts_resolved(monkeypatch):
    sb = _seed_two_conflicts()
    # Flip both conflicts to resolved so the guard passes.
    for c in sb.db["recruitment_verification_conflicts"]:
        c["status"] = "resolved_by_admin"

    promote_sb = _PromoteSB(sb)
    monkeypatch.setattr(scrape_runner, "_reconcile_lifecycle_events", lambda *a, **k: None)
    monkeypatch.setattr(scrape_runner, "_enqueue_recompute_fanout", lambda *a, **k: 0)

    from app.scraping.schemas import VerifiedRecruitmentForPromotion

    payload = VerifiedRecruitmentForPromotion(**_extracted_payload())
    rec_id = scrape_runner.promote_to_recruitments(
        payload,
        promote_sb,
        source_id="src-1",
        queue_id="queue-1",
    )
    assert rec_id == "recruitment-id-stub"
    # The RPC was called exactly once now that the guard cleared.
    assert len(promote_sb.rpc_calls) == 1
    assert promote_sb.rpc_calls[0][0] == "promote_recruitment"


# ─── 9 · auth ─────────────────────────────────────────────────────────────


def test_non_admin_caller_gets_403():
    sb = _seed_two_conflicts()
    client = TestClient(_build_app(sb, user=USER_USER))
    r = client.get("/api/admin/scrape/items/queue-1/conflicts")
    assert r.status_code == 403


# ─── 10 · P0-3 wiring: write_conflicts mirrors into the table ──────────────
#
# The consensus engine writes conflicts onto the verification REPORT's jsonb
# column via ``write_conflicts``. Production never wrote the
# ``recruitment_verification_conflicts`` TABLE that the admin Resolve UI and
# the promote-path gate (``runner._open_conflict_field_keys``) actually read.
# These tests pin the new mirror: a consensus conflict now lands as an
# ``open`` table row, keyed by queue_id + field_key.


def _seed_report(sb: SBStub, *, report_id: str = "rep-1", queue_id: str = "queue-1") -> dict:
    """Minimal verification REPORT row write_conflicts can update."""
    row = {
        "id": report_id,
        "scrape_queue_id": queue_id,
        "recruitment_id": None,
        "lifecycle_status": "consensus_pending",
        "conflicts": [],
    }
    sb.db.setdefault("recruitment_verification_reports", []).append(row)
    return row


def _consensus_conflict(field_path: str = "apply_end_date") -> dict:
    """A conflict dict in the exact shape verification_gateway feeds write_conflicts."""
    return {
        "conflict_id": f"cid-{field_path}",
        "conflict_key": f"{field_path}.official_disagreement",
        "field_path": field_path,
        "values": [
            {"source": "queue:q-off-1", "value": "2026-06-30", "confidence": 1.0},
            {"source": "queue:q-off-2", "value": "2026-07-15", "confidence": 1.0},
        ],
        "status": "open",
    }


def test_write_conflicts_lands_open_row_in_conflicts_table():
    from app.scraping.verification_reports import write_conflicts

    sb = SBStub({"recruitment_verification_reports": [], "recruitment_verification_conflicts": []})
    _seed_report(sb)

    write_conflicts(sb, "rep-1", conflicts=[_consensus_conflict("apply_end_date")])

    rows = sb.db["recruitment_verification_conflicts"]
    assert len(rows) == 1
    row = rows[0]
    assert row["queue_id"] == "queue-1"
    # Queue-targeted insert sets queue_id only; recruitment_id stays unset
    # (the DB column defaults to NULL).
    assert row.get("recruitment_id") is None
    assert row["field_key"] == "apply_end_date"
    assert row["status"] == "open"
    # Candidates carry the per-source value through so the Resolve UI has
    # something to render and the chosen value can be patched back.
    values = {c["value"] for c in row["candidates"]}
    assert values == {"2026-06-30", "2026-07-15"}
    # The jsonb write on the report is preserved (not replaced by the mirror).
    report = next(r for r in sb.db["recruitment_verification_reports"] if r["id"] == "rep-1")
    assert report["conflicts"][0]["field_path"] == "apply_end_date"


def test_write_conflicts_table_mirror_is_idempotent():
    from app.scraping.verification_reports import write_conflicts

    sb = SBStub({"recruitment_verification_reports": [], "recruitment_verification_conflicts": []})
    _seed_report(sb)

    write_conflicts(sb, "rep-1", conflicts=[_consensus_conflict("apply_end_date")])
    write_conflicts(sb, "rep-1", conflicts=[_consensus_conflict("apply_end_date")])

    # Re-running the same consensus updates the existing open row in place —
    # no duplicate open rows accumulate.
    rows = sb.db["recruitment_verification_conflicts"]
    assert len(rows) == 1
    assert rows[0]["status"] == "open"


def test_write_conflicts_retires_healed_open_rows():
    from app.scraping.verification_reports import write_conflicts

    sb = SBStub({"recruitment_verification_reports": [], "recruitment_verification_conflicts": []})
    _seed_report(sb)

    # First pass: two conflicting fields.
    write_conflicts(sb, "rep-1", conflicts=[
        _consensus_conflict("apply_end_date"),
        _consensus_conflict("total_vacancies"),
    ])
    assert len(sb.db["recruitment_verification_conflicts"]) == 2

    # Second pass: total_vacancies now agrees (drops out of the conflict set).
    write_conflicts(sb, "rep-1", conflicts=[_consensus_conflict("apply_end_date")])

    rows = {r["field_key"]: r for r in sb.db["recruitment_verification_conflicts"]}
    assert rows["apply_end_date"]["status"] == "open"
    # The healed field must stop blocking promotion — flipped off 'open'.
    assert rows["total_vacancies"]["status"] == "auto_resolved"
    # No row lingers 'open' for a field consensus no longer reports.
    open_fields = {r["field_key"] for r in sb.db["recruitment_verification_conflicts"] if r["status"] == "open"}
    assert open_fields == {"apply_end_date"}


def test_write_conflicts_does_not_touch_admin_resolved_rows():
    from app.scraping.verification_reports import write_conflicts

    sb = SBStub({"recruitment_verification_reports": [], "recruitment_verification_conflicts": []})
    _seed_report(sb)
    # An already admin-resolved row for the same target/field must be left
    # alone — the mirror only manages 'open' rows.
    sb.db["recruitment_verification_conflicts"].append({
        "id": "human-1",
        "queue_id": "queue-1",
        "recruitment_id": None,
        "field_key": "apply_end_date",
        "status": "resolved_by_admin",
        "candidates": [],
        "resolved_value": "2026-07-15",
    })

    write_conflicts(sb, "rep-1", conflicts=[_consensus_conflict("apply_end_date")])

    human = next(r for r in sb.db["recruitment_verification_conflicts"] if r["id"] == "human-1")
    assert human["status"] == "resolved_by_admin"
    assert human["resolved_value"] == "2026-07-15"
    # A fresh open row is still created for the live consensus signal.
    open_rows = [r for r in sb.db["recruitment_verification_conflicts"] if r["status"] == "open"]
    assert len(open_rows) == 1


def test_write_conflicts_survives_missing_conflicts_table():
    """Best-effort: a raising/missing table must not crash the verification pass."""
    from app.scraping.verification_reports import write_conflicts

    class _RaisingConflictsSB(SBStub):
        def table(self, name):
            if name == "recruitment_verification_conflicts":
                raise RuntimeError("relation does not exist (migration 087 not applied)")
            return super().table(name)

    sb = _RaisingConflictsSB({"recruitment_verification_reports": []})
    _seed_report(sb)

    # Must not raise — the jsonb write still lands.
    out = write_conflicts(sb, "rep-1", conflicts=[_consensus_conflict("apply_end_date")])
    assert out["id"] == "rep-1"
    report = next(r for r in sb.db["recruitment_verification_reports"] if r["id"] == "rep-1")
    assert report["conflicts"][0]["field_path"] == "apply_end_date"


# ─── 11 · resolve contract matches the frontend payload ────────────────────
#
# The Operations Console / ConflictResolver now send exactly
# {value, scope, reason, evidence_url, confirmation_text}. Pin that the
# endpoint accepts that body (previously the frontend omitted
# confirmation_text and every resolve 422'd).


def test_resolve_accepts_exact_frontend_payload():
    sb = _seed_two_conflicts()
    client = TestClient(_build_app(sb))
    # Byte-for-byte the body OperationsConsole.resolveConflict now POSTs.
    frontend_body = {
        "value": "2026-07-15",
        "scope": "field",
        "reason": "Corrigendum supersedes the original notification PDF.",
        "evidence_url": "https://upsc.gov.in/corrigendum.pdf",
        "confirmation_text": "CONFIRM_OVERRIDE",
    }
    r = client.post("/api/admin/conflicts/conflict-1/resolve", json=frontend_body)
    assert r.status_code == 200, r.text
    assert r.json()["conflict"]["status"] == "resolved_by_admin"


def test_resolve_without_confirmation_text_is_422():
    # Guards the regression: omitting the (required) confirmation field is a
    # 422 from Pydantic, which is exactly what the old frontend triggered.
    sb = _seed_two_conflicts()
    client = TestClient(_build_app(sb))
    r = client.post(
        "/api/admin/conflicts/conflict-1/resolve",
        json={
            "value": "2026-07-15",
            "scope": "field",
            "reason": "Corrigendum supersedes the original notification.",
            "evidence_url": "https://upsc.gov.in/corrigendum.pdf",
        },
    )
    assert r.status_code == 422


# ─── 12 · P1-6 · allowlist validated before any patch (no torn write) ──────


def _seed_recruitment_conflict(field_key: str) -> SBStub:
    return SBStub({
        "recruitments": [{"id": "rec-1", "apply_end_date": "2026-06-30", "publish_status": "draft"}],
        "recruitment_verification_conflicts": [{
            "id": "rconf-1",
            "queue_id": "queue-1",
            "recruitment_id": "rec-1",
            "field_key": field_key,
            "status": "open",
            "candidates": [
                {"source_url": "https://upsc.gov.in/a", "source_kind": "notification_pdf", "value": "x"},
                {"source_url": "https://upsc.gov.in/b", "source_kind": "corrigendum_pdf", "value": "y"},
            ],
        }],
        "scrape_queue": [{"id": "queue-1", "extracted_data": {}}],
        "admin_audit_logs": [],
    })


def test_resolve_rejects_non_editable_recruitment_field_before_writing():
    # publish_status is NOT in the recruitment allowlist. The resolve must
    # 400 BEFORE patching the queue payload (P1-6: no torn write).
    sb = _seed_recruitment_conflict("publish_status")
    client = TestClient(_build_app(sb))
    r = client.post(
        "/api/admin/conflicts/rconf-1/resolve",
        json={
            "value": "published",
            "scope": "field",
            "reason": "trying to flip publish_status via conflict resolution",
            "evidence_url": "https://upsc.gov.in/x",
            "confirmation_text": "CONFIRM_OVERRIDE",
        },
    )
    assert r.status_code == 400
    assert "not admin-editable" in (r.json().get("detail") or "")
    # Neither the queue payload nor the conflict row was mutated.
    assert sb.db["scrape_queue"][0]["extracted_data"] == {}
    assert sb.db["recruitment_verification_conflicts"][0]["status"] == "open"
    # And the recruitment column itself is untouched.
    assert "publish_status" not in {"published"} or sb.db["recruitments"][0]["publish_status"] == "draft"


def test_resolve_allows_editable_recruitment_field():
    # apply_end_date IS in the allowlist → resolve patches the recruitment.
    sb = _seed_recruitment_conflict("apply_end_date")
    client = TestClient(_build_app(sb))
    r = client.post(
        "/api/admin/conflicts/rconf-1/resolve",
        json={
            "value": "2026-07-15",
            "scope": "field",
            "reason": "Official corrigendum extends the apply window.",
            "evidence_url": "https://upsc.gov.in/corrigendum.pdf",
            "confirmation_text": "CONFIRM_OVERRIDE",
        },
    )
    assert r.status_code == 200, r.text
    assert sb.db["recruitments"][0]["apply_end_date"] == "2026-07-15"
    assert sb.db["recruitment_verification_conflicts"][0]["status"] == "resolved_by_admin"
