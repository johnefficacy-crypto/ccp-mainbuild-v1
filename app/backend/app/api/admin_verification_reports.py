"""Admin read API for the Recruitment Verification Gateway.

PR7 scope — read-only listing + detail. No state mutation endpoints
yet (resolver re-run, override-conflict, promote, reject, bulk-apply
all land in PR2/PR3/PR6 as the plan ships them).

Track-3 (PR5 corrigendum continuation) adds:

    POST /api/admin/verification-reports/{report_id}/apply-registry-action

The endpoint is the ONLY path from a verification report/event into
the exam registry. It requires an explicit operator submission (no
auto-apply), writes one ``exam_registry_actions`` row (report_id NOT
NULL), and delegates the actual DB mutation to
``exam_intelligence.registry_action_service`` so the write + audit
logic is single-sourced with the CMS handlers.

Endpoints:

    GET /api/admin/verification-reports
        ?lifecycle=&tier=&recommended_action=&limit=&offset=
    GET /api/admin/verification-reports/{id}

Filters are optional. The default listing returns active
(non-superseded) reports newest-first, fed by the ``idx_verification_reports_attention``
partial index from migration 075.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth import require_admin, require_permission
from app.core.permissions import (
    ACTION_ACK_BATCH,
    ACTION_PROMOTE,
    ACTION_REJECT,
    user_has_action,
)
from app.db.supabase_client import get_supabase_admin
from app.api.admin_scrape import build_effective_extracted_data
from app.core.errors import PromotionError
from app.scraping.promotion_gate import (
    check_gateway_promotion,
    check_gateway_publish,
)
from app.scraping.runner import promote_to_recruitments
from app.scraping.schemas import VerifiedRecruitmentForPromotion
from app.exam_intelligence.registry_action_service import (
    apply_cycle_date_update,
    apply_phase_date_update,
    apply_policy_update_create,
    apply_policy_update_edit,
)
from app.scraping.source_watch import acknowledge_batch
from app.scraping.verification_gateway import run_resolver_stage
from app.scraping.verification_policy import RESOLVER_RERUN_LIMITS
from app.scraping.verification_reports import (
    attach_admin_official_url,
    record_override,
    update_lifecycle_status,
)


logger = logging.getLogger("career_copilot.api.admin_verification_reports")


router = APIRouter()


_ALLOWED_LIFECYCLE = {"classified", "backfilled_needs_review", "superseded", "rejected"}
_ALLOWED_TIER = {"A_HIGH_STAKES", "B_TECHNICAL_CONDITIONAL", "C_STANDARD_LONG_TAIL"}
_ALLOWED_RECOMMENDED = {
    "await_official_proof", "request_admin_review",
    "promote_eligible", "block_publish", "no_action",
    "confirm_suggested_proof",
    # PR3 extension (migration 081):
    "resolve_conflict",
    # PR5 extension (migration 085):
    "await_corrigendum",
}


_ALLOWED_LIFECYCLE = _ALLOWED_LIFECYCLE | {
    # PR3 extension (migration 079):
    "consensus_pending", "conflict", "admin_override_required",
    # PR4 extension (migration 082):
    "complexity_detected",
    # PR5 extension (migration 084):
    "stale_source_changed", "stale_canonical_changed", "needs_reverification",
}


# ── In-process rate-limit state (PR2 stop-gap) ─────────────────────────
#
# Process-local dicts; not durable across restarts. PR2 ships these as
# a stop-gap so a single instance enforces the rate-limit contract
# from the spec. A future PR moves them into Redis / Postgres when the
# service goes multi-instance.

_resolver_last_run_at: dict[str, float] = {}
_resolver_admin_hourly: dict[str, list[float]] = defaultdict(list)


def _check_resolver_rate_limit(report_id: str, admin_id: str) -> None:
    """Raise 429 if the report cooldown or per-admin hourly cap is hit."""
    now = time.time()
    cooldown = RESOLVER_RERUN_LIMITS["per_report_cooldown_seconds"]
    last = _resolver_last_run_at.get(report_id)
    if last is not None and (now - last) < cooldown:
        retry_in = int(cooldown - (now - last))
        raise HTTPException(
            status_code=429,
            detail=f"Resolver cooldown active for this report; retry in {retry_in}s.",
        )
    hourly_cap = RESOLVER_RERUN_LIMITS["per_admin_per_hour"]
    bucket = _resolver_admin_hourly[admin_id]
    cutoff = now - 3600
    bucket[:] = [t for t in bucket if t > cutoff]
    if len(bucket) >= hourly_cap:
        raise HTTPException(
            status_code=429,
            detail=f"Per-admin resolver re-run cap reached ({hourly_cap}/hour).",
        )
    bucket.append(now)
    _resolver_last_run_at[report_id] = now


class VerificationReportListItem(BaseModel):
    """Subset of columns surfaced in the listing view.

    The detail endpoint returns the full row including jsonb columns;
    the list view trims down to what an attention queue actually needs
    so the payload stays small.
    """

    id: str
    scrape_queue_id: str | None
    recruitment_id: str | None
    lifecycle_status: str
    criticality_tier: str
    exam_family_key: str | None
    recommended_action: str
    trigger_reason: str
    report_version: int
    chain_root_id: str | None
    created_at: str
    updated_at: str


class VerificationReportListResponse(BaseModel):
    items: list[VerificationReportListItem]
    total: int | None = None
    limit: int
    offset: int


@router.get(
    "/admin/verification-reports",
    response_model=VerificationReportListResponse,
)
def list_verification_reports(
    lifecycle: str | None = Query(default=None),
    tier: str | None = Query(default=None),
    recommended_action: str | None = Query(default=None),
    include_superseded: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: dict = Depends(require_admin),
) -> VerificationReportListResponse:
    """List verification reports for the admin attention queue.

    Defaults to active (non-superseded) reports newest-first. Filters
    are rejected with 422 if outside the PR1 enum sets.
    """
    if lifecycle is not None and lifecycle not in _ALLOWED_LIFECYCLE:
        raise HTTPException(status_code=422, detail=f"unknown lifecycle: {lifecycle!r}")
    if tier is not None and tier not in _ALLOWED_TIER:
        raise HTTPException(status_code=422, detail=f"unknown tier: {tier!r}")
    if recommended_action is not None and recommended_action not in _ALLOWED_RECOMMENDED:
        raise HTTPException(status_code=422, detail=f"unknown recommended_action: {recommended_action!r}")

    supabase = get_supabase_admin()
    q = (
        supabase.table("recruitment_verification_reports")
        .select(
            "id, scrape_queue_id, recruitment_id, lifecycle_status, "
            "criticality_tier, exam_family_key, recommended_action, "
            "trigger_reason, report_version, chain_root_id, "
            "created_at, updated_at"
        )
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    if not include_superseded:
        q = q.is_("superseded_by", None)
    if lifecycle is not None:
        q = q.eq("lifecycle_status", lifecycle)
    if tier is not None:
        q = q.eq("criticality_tier", tier)
    if recommended_action is not None:
        q = q.eq("recommended_action", recommended_action)

    rows = q.execute().data or []
    items = [VerificationReportListItem(**r) for r in rows]
    return VerificationReportListResponse(items=items, limit=limit, offset=offset)


@router.get("/admin/verification-reports/{report_id}")
def get_verification_report(
    report_id: str,
    _: dict = Depends(require_admin),
) -> dict[str, Any]:
    """Return the full report row including jsonb columns.

    No mutation; safe to call from an admin detail drawer.
    """
    supabase = get_supabase_admin()
    rows = (
        supabase.table("recruitment_verification_reports")
        .select("*")
        .eq("id", report_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(status_code=404, detail="verification_report not found")
    return rows[0]


# ── PR2 mutation endpoints ────────────────────────────────────────────


class RunResolverResponse(BaseModel):
    report_id: str
    classification_outcome: str
    resolver_status: str | None
    resolver_method: str | None
    resolver_confidence: float | None
    suggested_count: int


@router.post(
    "/admin/verification-reports/{report_id}/run-resolver",
    response_model=RunResolverResponse,
)
def run_resolver_for_report(
    report_id: str,
    admin: dict = Depends(require_admin),
) -> RunResolverResponse:
    """Force a resolver re-run for one report.

    Subject to the per-report cooldown and per-admin hourly cap from
    ``verification_policy.RESOLVER_RERUN_LIMITS``. A 429 is the
    cooldown signal — the client should display the retry-in window
    rather than retry immediately.
    """
    admin_id = admin.get("id")
    if not admin_id:
        raise HTTPException(status_code=403, detail="admin id missing")
    _check_resolver_rate_limit(report_id, admin_id)

    supabase = get_supabase_admin()
    try:
        result = run_resolver_stage(supabase, report_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="verification_report not found")
    return RunResolverResponse(
        report_id=result.report_id or report_id,
        classification_outcome=result.classification_outcome,
        resolver_status=result.resolver_status,
        resolver_method=result.resolver_method,
        resolver_confidence=result.resolver_confidence,
        suggested_count=result.suggested_count,
    )


class OverrideConflictRequest(BaseModel):
    conflict_id: str = Field(min_length=1)
    prior_value: Any = None
    chosen_value: Any
    reason: str = Field(min_length=1)
    evidence_url: str | None = None
    override_scope: str = Field(default="field")


@router.post("/admin/verification-reports/{report_id}/override-conflict")
def override_conflict(
    report_id: str,
    payload: OverrideConflictRequest = Body(...),
    admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    """Resolve one verification conflict with an explicit admin choice.

    Permission: ``recruitments.manage`` AND role in (admin, super_admin).
    ``override_scope`` is restricted to ``"field"`` or ``"recruitment"``
    — the plan removed the ``"report"`` scope deliberately.

    Side effects:

    * Inserts a row into ``recruitment_verification_overrides`` with the
      audit trail (prior_value, chosen_value, reason, evidence_url).
    * Marks the matching conflict on the report's jsonb column as
      ``resolved_by_admin`` (the gate uses this to unblock Tier A).
    """
    perms = set(admin.get("permissions") or [])
    if "recruitments.manage" not in perms and admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="recruitments.manage required")
    if payload.override_scope not in {"field", "recruitment"}:
        raise HTTPException(
            status_code=422,
            detail="override_scope must be 'field' or 'recruitment'",
        )

    supabase = get_supabase_admin()
    rows = (
        supabase.table("recruitment_verification_reports")
        .select("id, conflicts")
        .eq("id", report_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(status_code=404, detail="verification_report not found")
    target = next(
        (c for c in rows[0].get("conflicts") or [] if c.get("conflict_id") == payload.conflict_id),
        None,
    )
    if not target:
        raise HTTPException(
            status_code=404,
            detail="conflict_id not present on this report",
        )
    try:
        override_row = record_override(
            supabase,
            verification_report_id=report_id,
            conflict_id=payload.conflict_id,
            conflict_key=target.get("conflict_key", ""),
            field_path=target.get("field_path"),
            prior_value=payload.prior_value,
            chosen_value=payload.chosen_value,
            reason=payload.reason,
            evidence_url=payload.evidence_url,
            override_scope=payload.override_scope,
            created_by=admin["id"],
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return override_row


class ConfirmSuggestedProofRequest(BaseModel):
    chosen_url: str = Field(min_length=1)


@router.post("/admin/verification-reports/{report_id}/confirm-suggested-proof")
def confirm_suggested_proof(
    report_id: str,
    payload: ConfirmSuggestedProofRequest = Body(...),
    _: dict = Depends(require_admin),
) -> dict[str, Any]:
    """Admin confirms one of the suggested URLs.

    The ``chosen_url`` MUST match one of the entries in the report's
    ``suggested_official_urls`` jsonb — anything else would let an
    admin bypass the resolver and inject an arbitrary URL, which is
    explicitly not the contract.

    On success: ``official_resolution_status`` flips to
    ``admin_attached`` and the original suggestion's method is
    preserved on the row for the audit trail.
    """
    supabase = get_supabase_admin()
    rows = (
        supabase.table("recruitment_verification_reports")
        .select("id, suggested_official_urls, official_resolution_method")
        .eq("id", report_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(status_code=404, detail="verification_report not found")
    report = rows[0]
    suggestions = report.get("suggested_official_urls") or []
    match = next((u for u in suggestions if u.get("url") == payload.chosen_url), None)
    if not match:
        raise HTTPException(
            status_code=400,
            detail="chosen_url must match an entry in suggested_official_urls",
        )
    method = match.get("method") or report.get("official_resolution_method") or "direct_link"
    updated = attach_admin_official_url(
        supabase, report_id,
        chosen_url=payload.chosen_url, original_method=method,
    )
    return updated


# ── PR6: promote / reject / bulk / acknowledge-batch ──────────────────


def _fetch_report(supabase, report_id: str) -> dict[str, Any] | None:
    rows = (
        supabase.table("recruitment_verification_reports")
        .select("*")
        .eq("id", report_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def _gate_blocker(report: dict[str, Any] | None, *, mode: str) -> dict[str, Any] | None:
    """Return the gate's blocker shape if blocked, else None.

    ``mode`` is ``"promote"`` (check_gateway_promotion) or ``"publish"``
    (check_gateway_publish). The publish gate is the stricter one; PR6
    exposes only the promote path as a mutation, but the bulk-dry-run
    contract reports both so the UI can show which level a blocker
    fires at.
    """
    gate_fn = check_gateway_promotion if mode == "promote" else check_gateway_publish
    result = gate_fn(report)
    if result.ok:
        return None
    return {
        "id": (report or {}).get("id"),
        "entity_type": "verification_report",
        "reason_code": result.reason_code,
        "message": result.message,
        "blocking_level": result.blocking_level,
    }


class PromoteRequest(BaseModel):
    # Reserved for future explicit notes / overrides; PR6 keeps it empty.
    notes: str | None = None


@router.post("/admin/verification-reports/{report_id}/promote")
def promote_report(
    report_id: str,
    payload: PromoteRequest = Body(default_factory=PromoteRequest),
    admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    """Promote a verification report through the gate.

    Plan §7: the endpoint never bypasses the existing canonical promote
    flow in ``admin_trust.py``. PR6 wires the gateway gate in front of
    it; if the gate blocks, the canonical promote isn't invoked.
    """
    if not user_has_action(admin, ACTION_PROMOTE):
        raise HTTPException(status_code=403, detail="not authorised to promote")
    supabase = get_supabase_admin()
    report = _fetch_report(supabase, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="verification_report not found")
    blocker = _gate_blocker(report, mode="promote")
    if blocker is not None:
        raise HTTPException(status_code=409, detail=blocker)

    queue_id = report.get("scrape_queue_id")
    if queue_id is None:
        raise HTTPException(
            status_code=409,
            detail={
                "id": report_id,
                "entity_type": "verification_report",
                "reason_code": "no_queue_item",
                "message": (
                    "Report has no attached scrape queue item; "
                    "cannot promote from queue."
                ),
                "blocking_level": "promotion_blocker",
            },
        )

    # Resolve source_id from the queue row (not on the report itself).
    queue_row = (
        supabase.table("scrape_queue")
        .select("source_id")
        .eq("id", queue_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    source_id: str | None = queue_row[0]["source_id"] if queue_row else None

    # Build effective extracted data (base + reviewer corrections).
    effective_data = build_effective_extracted_data(supabase, queue_id)
    try:
        extracted = VerifiedRecruitmentForPromotion(**effective_data)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "id": report_id,
                "entity_type": "verification_report",
                "reason_code": "invalid_extraction_data",
                "message": str(exc),
            },
        ) from exc

    # Delegate to the shared canonical promote — RPC-first + compensation
    # fallback inside promote_to_recruitments(); we never reimplement it.
    try:
        rec_id = promote_to_recruitments(
            extracted,
            supabase,
            source_id=source_id,
            queue_id=queue_id,
        )
    except PromotionError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "id": report_id,
                "entity_type": "verification_report",
                "reason_code": "promotion_failed",
                "message": str(exc),
            },
        ) from exc

    updated = (
        supabase.table("recruitment_verification_reports")
        .update({"recommended_action": "promote_eligible", "recruitment_id": rec_id})
        .eq("id", report_id)
        .execute()
        .data
        or [None]
    )[0]
    return updated or report


class RejectRequest(BaseModel):
    reason: str | None = None


@router.post("/admin/verification-reports/{report_id}/reject")
def reject_report(
    report_id: str,
    payload: RejectRequest = Body(default_factory=RejectRequest),
    admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    """Mark a report ``rejected``.

    Lifecycle is updated via :func:`update_lifecycle_status` so the
    transition matrix is enforced (only certain states can transition
    to ``rejected``).
    """
    if not user_has_action(admin, ACTION_REJECT):
        raise HTTPException(status_code=403, detail="not authorised to reject")
    supabase = get_supabase_admin()
    try:
        updated = update_lifecycle_status(supabase, report_id, "rejected")
    except LookupError:
        raise HTTPException(status_code=404, detail="verification_report not found")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    if payload.reason:
        # Note is informational; we don't have a dedicated audit column
        # on the report row, so it goes onto recommended_action context.
        # A future migration can pull this into a proper note column.
        supabase.table("recruitment_verification_reports").update(
            {"recommended_action": "no_action"}
        ).eq("id", report_id).execute()
    return updated


# ── Bulk dry-run + apply ──────────────────────────────────────────────


class BulkRequest(BaseModel):
    selected_ids: list[str] = Field(min_length=1)
    action: str = Field(min_length=1)
    dry_run: bool = True


_BULK_ACTIONS: set[str] = {"bulk_promote", "bulk_reject"}


@router.post("/admin/verification-reports/bulk-dry-run")
def bulk_dry_run(
    payload: BulkRequest,
    admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    """Compute per-row eligibility for a bulk action without mutating.

    Plan §6/§7 contract:

      {
        "selected_ids": ["..."],
        "action": "bulk_promote",
        "dry_run": true,
        "result": {
          "eligible_count": N,
          "blocked_count": M,
          "blockers": [{ id, entity_type, reason_code, message, blocking_level }],
        }
      }

    ``bulk_promote`` runs the gateway promotion gate per report.
    ``bulk_reject`` checks transition-matrix legality per report.
    """
    if payload.action not in _BULK_ACTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"action must be one of {sorted(_BULK_ACTIONS)}",
        )
    supabase = get_supabase_admin()
    rows = (
        supabase.table("recruitment_verification_reports")
        .select("*")
        .execute()
        .data
        or []
    )
    by_id = {r["id"]: r for r in rows}
    blockers: list[dict[str, Any]] = []
    eligible_count = 0
    for rid in payload.selected_ids:
        report = by_id.get(rid)
        if report is None:
            blockers.append({
                "id": rid,
                "entity_type": "verification_report",
                "reason_code": "report_not_found",
                "message": "Report not found.",
                "blocking_level": "promotion_blocker",
            })
            continue
        if payload.action == "bulk_promote":
            blocker = _gate_blocker(report, mode="promote")
            if blocker is None:
                eligible_count += 1
            else:
                blockers.append(blocker)
        else:  # bulk_reject
            from app.scraping.verification_reports import ALLOWED_REPORT_TRANSITIONS
            current = report.get("lifecycle_status")
            allowed = ALLOWED_REPORT_TRANSITIONS.get(current, set())
            if "rejected" in allowed:
                eligible_count += 1
            else:
                blockers.append({
                    "id": rid,
                    "entity_type": "verification_report",
                    "reason_code": "illegal_transition",
                    "message": f"Cannot reject from lifecycle_status={current!r}.",
                    "blocking_level": "promotion_blocker",
                })
    return {
        "selected_ids": payload.selected_ids,
        "action": payload.action,
        "dry_run": True,
        "result": {
            "eligible_count": eligible_count,
            "blocked_count": len(blockers),
            "blockers": blockers,
        },
    }


@router.post("/admin/verification-reports/bulk-apply")
def bulk_apply(
    payload: BulkRequest,
    admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    """Run a bulk action on the eligible subset.

    Plan §6 rule: bulk action runs dry-run first. Mutation applies
    only to the eligible subset. Blocked subset returned unchanged
    with reasons.
    """
    if payload.action == "bulk_promote" and not user_has_action(admin, ACTION_PROMOTE):
        raise HTTPException(status_code=403, detail="not authorised to promote")
    if payload.action == "bulk_reject" and not user_has_action(admin, ACTION_REJECT):
        raise HTTPException(status_code=403, detail="not authorised to reject")

    dry = bulk_dry_run(payload, admin)["result"]
    blocked_ids = {b["id"] for b in dry["blockers"]}
    applied_ids: list[str] = []
    for rid in payload.selected_ids:
        if rid in blocked_ids:
            continue
        try:
            if payload.action == "bulk_promote":
                promote_report(rid, PromoteRequest(), admin)
            else:
                reject_report(rid, RejectRequest(), admin)
            applied_ids.append(rid)
        except HTTPException:
            # Race between dry-run and apply — skip; the dry-run output
            # is still authoritative for what was *intended*.
            continue
    return {
        "action": payload.action,
        "applied_ids": applied_ids,
        "blockers": dry["blockers"],
        "eligible_count": dry["eligible_count"],
        "blocked_count": dry["blocked_count"],
    }


# ── Reverification batches (PR5 paired surface) ──────────────────────


@router.get("/admin/reverification-batches")
def list_reverification_batches(
    acknowledged: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    _: dict = Depends(require_admin),
) -> dict[str, Any]:
    """List reverification batches.

    Defaults to unacknowledged-only so the admin needs-attention feed
    reads off ``idx_reverification_batches_unack``.
    """
    supabase = get_supabase_admin()
    q = (
        supabase.table("reverification_batches")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if not acknowledged:
        q = q.is_("acknowledged_at", None)
    rows = q.execute().data or []
    return {"items": rows, "limit": limit}


@router.post("/admin/verification-reports/acknowledge-batch/{batch_id}")
def acknowledge_reverification_batch(
    batch_id: str,
    admin: dict = Depends(require_admin),
) -> dict[str, Any]:
    """Acknowledge a reverification batch.

    Promotes up to one chunk's worth of pending reports to
    ``needs_reverification``. Repeat invocations chew through the
    queue.
    """
    if not user_has_action(admin, ACTION_ACK_BATCH):
        raise HTTPException(status_code=403, detail="not authorised to acknowledge batches")
    supabase = get_supabase_admin()
    try:
        promoted = acknowledge_batch(supabase, batch_id, acknowledged_by=admin["id"])
    except LookupError:
        raise HTTPException(status_code=404, detail="reverification_batch not found")
    return {"batch_id": batch_id, "promoted": promoted}


# ── Track-3: corrigendum review → exam registry ──────────────────────


_APPLY_ACTION_TYPES = {
    "cycle_date_update",
    "phase_date_update",
    "policy_update_create",
    "policy_update_edit",
}


class ApplyRegistryActionRequest(BaseModel):
    """Body for POST /admin/verification-reports/{report_id}/apply-registry-action.

    Exactly one of ``exam_cycle_id``, ``exam_phase_id``, or
    ``policy_update_id`` must be provided (the DB CHECK enforces it;
    we also validate here for a friendly 422).

    ``patch`` carries the date/field values to write to the target row.
    For ``policy_update_create`` it is the full row payload; for the
    three update variants it is the partial patch.
    """

    action_type: str = Field(..., description="One of the four action_type values.")
    exam_cycle_id: str | None = Field(default=None)
    exam_phase_id: str | None = Field(default=None)
    policy_update_id: str | None = Field(default=None)
    event_source_id: str | None = Field(default=None)
    patch: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = Field(default=None, max_length=2000)
    reason: str = Field(..., min_length=8, max_length=500)


_PERM_REGISTRY_ACTION = "exam_intelligence.cms"


@router.post("/admin/verification-reports/{report_id}/apply-registry-action")
def apply_registry_action(
    report_id: str,
    payload: ApplyRegistryActionRequest = Body(...),
    admin: dict = Depends(require_permission(_PERM_REGISTRY_ACTION)),
) -> dict[str, Any]:
    """Apply a verified corrigendum / lifecycle event to the exam registry.

    This is the ONLY path that moves a value from a verification
    report or recruitment_event into exam_cycles, exam_phases, or
    exam_policy_updates. Nothing auto-applies; every mutation requires
    an explicit operator submission with a report_id.

    The endpoint:
      1. Validates the report exists.
      2. Dispatches to the appropriate registry_action_service function
         (reusing the exact same write + audit logic as the CMS handlers).
      3. Writes one ``exam_registry_actions`` row (report_id NOT NULL,
         enforced structurally).

    The admin_audit_logs row is written inside the service call, so the
    audit trail captures the operator, source report, target row, and
    old→new values regardless of which action_type is used.
    """
    if payload.action_type not in _APPLY_ACTION_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"action_type must be one of {sorted(_APPLY_ACTION_TYPES)}",
        )

    # Validate at least one target is set (mirrors the DB CHECK constraint).
    # policy_update_create is exempt: the policy_update_id is produced by the
    # write itself and is set on the action row after the insert.
    if payload.action_type != "policy_update_create":
        if not any([payload.exam_cycle_id, payload.exam_phase_id, payload.policy_update_id]):
            raise HTTPException(
                status_code=422,
                detail="At least one of exam_cycle_id, exam_phase_id, policy_update_id is required",
            )

    supabase = get_supabase_admin()

    # Confirm the report exists — report_id is the trust gate.
    report_rows = (
        supabase.table("recruitment_verification_reports")
        .select("id, trigger_reason, lifecycle_status")
        .eq("id", report_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not report_rows:
        raise HTTPException(status_code=404, detail="verification_report not found")

    # Pre-validate event_source_id before any registry write so the action
    # row insert cannot fail on a stale FK after the target mutation has
    # already been committed (atomicity guard — Codex P1).
    if payload.event_source_id:
        event_check = (
            supabase.table("recruitment_events")
            .select("id")
            .eq("id", payload.event_source_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not event_check:
            raise HTTPException(
                status_code=422,
                detail="event_source_id does not resolve to a recruitment_events row",
            )

    # Dispatch to the single-sourced write+audit logic.
    action_type = payload.action_type
    write_result: dict[str, Any]

    if action_type == "cycle_date_update":
        if not payload.exam_cycle_id:
            raise HTTPException(status_code=422, detail="exam_cycle_id required for cycle_date_update")
        write_result = apply_cycle_date_update(
            supabase, admin,
            cycle_id=payload.exam_cycle_id,
            patch=payload.patch,
            reason=payload.reason,
        )
        target_id = payload.exam_cycle_id

    elif action_type == "phase_date_update":
        if not payload.exam_phase_id:
            raise HTTPException(status_code=422, detail="exam_phase_id required for phase_date_update")
        write_result = apply_phase_date_update(
            supabase, admin,
            phase_id=payload.exam_phase_id,
            patch=payload.patch,
            reason=payload.reason,
        )
        target_id = payload.exam_phase_id

    elif action_type == "policy_update_create":
        write_result = apply_policy_update_create(
            supabase, admin,
            payload=payload.patch,
            reason=payload.reason,
        )
        target_id = write_result.get("row", {}).get("id")

    else:  # policy_update_edit
        if not payload.policy_update_id:
            raise HTTPException(status_code=422, detail="policy_update_id required for policy_update_edit")
        write_result = apply_policy_update_edit(
            supabase, admin,
            policy_id=payload.policy_update_id,
            patch=payload.patch,
            reason=payload.reason,
        )
        target_id = payload.policy_update_id

    # Record the action — report_id NOT NULL is the structural trust gate.
    action_row_payload: dict[str, Any] = {
        "report_id": report_id,
        "action_type": action_type,
        "applied_by": admin["id"],
        "metadata": {
            "reason": payload.reason,
            "target_id": target_id,
            "audit_id": write_result.get("audit_id"),
        },
    }
    if payload.event_source_id:
        action_row_payload["event_source_id"] = payload.event_source_id
    if payload.exam_cycle_id:
        action_row_payload["exam_cycle_id"] = payload.exam_cycle_id
    if payload.exam_phase_id:
        action_row_payload["exam_phase_id"] = payload.exam_phase_id
    if payload.policy_update_id or (action_type == "policy_update_create" and target_id):
        action_row_payload["policy_update_id"] = payload.policy_update_id or target_id
    if payload.notes:
        action_row_payload["notes"] = payload.notes

    action_rows = (
        supabase.table("exam_registry_actions")
        .insert(action_row_payload)
        .execute()
        .data
        or []
    )
    action_row = action_rows[0] if action_rows else action_row_payload

    return {
        "ok": True,
        "action_id": action_row.get("id"),
        "audit_id": write_result.get("audit_id"),
        "action_type": action_type,
        "report_id": report_id,
        "target_row": write_result.get("row"),
    }
