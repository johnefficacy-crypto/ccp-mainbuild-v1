"""English Writing Practice — deterministic runtime API (EWP-2).

Practice-runtime endpoints under ``/api/study/practice/english``. Stage-1
(deterministic) evaluation runs synchronously here; the async language/rubric
worker is EWP-2B. These endpoints never create mock attempts (§2) and never
write live mastery (§10 — shadow only, gated).

DB-touching handlers use the service-role client and scope every read/write to
``user.id``; the schema's RLS is a defence-in-depth backstop, not the primary
authorization here.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.db.supabase_client import get_supabase_admin
from app.study_os.writing_practice import applicability
from app.study_os.writing_practice import coverage_checker
from app.study_os.writing_practice import deterministic as det
from app.study_os.writing_practice import session_state as st
from app.study_os.writing_practice.constraints import validate_unit_constraints
from app.study_os.writing_practice.content_hash import compute_content_hash

logger = logging.getLogger("career_copilot.api.writing_practice")

router = APIRouter(prefix="/study/practice/english", tags=["writing-practice"])


# --- request models -------------------------------------------------------

class CreateSessionRequest(BaseModel):
    prompt_id: UUID
    study_task_id: UUID | None = None
    mode: str = Field(default="learning", pattern="^(learning|exam)$")


class SubmitUnitRequest(BaseModel):
    answer_text: str
    client_word_count: int | None = None
    # Mandatory version CAS token: the version number the caller expects to
    # create (1 for a unit's first submission). Rejects stale/duplicate submits.
    version_number: int = Field(ge=1)


class ReopenUnitRequest(BaseModel):
    expected_latest_version_id: UUID
    reason: str | None = None


# --- helpers --------------------------------------------------------------

def _owned_session(supabase: Any, session_id: str, user_id: str) -> dict:
    row = (
        supabase.table("writing_sessions")
        .select("*")
        .eq("id", session_id)
        .eq("user_id", user_id)
        .maybe_single()
        .execute()
    ).data
    if not row:
        raise HTTPException(status_code=404, detail="writing session not found")
    return row


def _session_prompt(supabase: Any, session: dict) -> dict | None:
    """The prompt view for a session, projected from the IMMUTABLE per-session
    snapshot (migration 221) — never the live writing_prompts row, so a later
    prompt edit cannot retro-change an in-flight or historical session."""
    snap = session.get("prompt_snapshot")
    prompt_id = session.get("prompt_id")
    if not snap or not prompt_id:
        return None
    return {
        "id": prompt_id,
        "exercise_type": snap.get("exercise_type"),
        "prompt_text": snap.get("prompt_text"),
        "source_text": snap.get("source_text"),
        "required_words": snap.get("required_words") or [],
        "required_sentence_count": snap.get("required_sentence_count"),
        "difficulty_level": snap.get("difficulty_level"),
        "min_words": snap.get("min_words"),
        "max_words": snap.get("max_words"),
    }


def _resume_unit_state(supabase: Any, session: dict, unit_ids: list[str]) -> dict[str, dict]:
    """Per-unit resume state: latest version + latest evaluation.

    Returns ``{unit_id: {"latest_version": {...}|None, "previous_version": {...}|None,
    "latest_evaluation": {...}|None}}``.
    Feedback-bearing evaluation fields (``language_result``, ``dimension_scores``)
    are included only when feedback is released for the session (§13 rule 13 —
    learning mode is always released; exam mode gates on ``feedback_released_at``).
    The evaluation id + statuses are always present so the client can poll.
    """
    out: dict[str, dict] = {
        uid: {"latest_version": None, "previous_version": None, "latest_evaluation": None}
        for uid in unit_ids
    }
    if not unit_ids:
        return out

    versions = (
        supabase.table("writing_unit_versions")
        .select("id,unit_id,version_number,answer_text,server_word_count")
        .in_("unit_id", unit_ids)
        .order("version_number", desc=True)
        .execute()
    ).data or []
    # First row per unit is its latest version (query is version_number desc);
    # the second row (if any) is the version immediately before it. The prior
    # version powers the accepted before->after diff on a resumed ready/completed
    # unit (EWP-3) — it is the aspirant's own submission, so it is NOT feedback-gated.
    latest_by_unit: dict[str, dict] = {}
    previous_by_unit: dict[str, dict] = {}
    for v in versions:
        uid = v["unit_id"]
        if uid not in latest_by_unit:
            latest_by_unit[uid] = v
        elif uid not in previous_by_unit:
            previous_by_unit[uid] = v

    released = _feedback_released(session)
    version_ids = [v["id"] for v in latest_by_unit.values()]
    evals_by_version: dict[str, dict] = {}
    if version_ids:
        evals = (
            supabase.table("writing_evaluations")
            .select(
                "id,unit_version_id,evaluation_revision,overall_status,"
                "deterministic_status,language_status,language_result,dimension_scores"
            )
            .in_("unit_version_id", version_ids)
            .order("evaluation_revision", desc=True)
            .execute()
        ).data or []
        for e in evals:
            evals_by_version.setdefault(e["unit_version_id"], e)

    for uid in unit_ids:
        latest = latest_by_unit.get(uid)
        if not latest:
            continue
        out[uid]["latest_version"] = {
            "id": latest["id"],
            "version_number": latest["version_number"],
            "answer_text": latest["answer_text"],
            "server_word_count": latest.get("server_word_count"),
        }
        prev = previous_by_unit.get(uid)
        if prev:
            out[uid]["previous_version"] = {
                "id": prev["id"],
                "version_number": prev["version_number"],
                "answer_text": prev["answer_text"],
            }
        ev = evals_by_version.get(latest["id"])
        if ev:
            projected = {
                "id": ev["id"],
                "overall_status": ev.get("overall_status"),
                "deterministic_status": ev.get("deterministic_status"),
                "language_status": ev.get("language_status"),
            }
            if released:
                projected["language_result"] = ev.get("language_result")
                projected["dimension_scores"] = ev.get("dimension_scores")
            out[uid]["latest_evaluation"] = projected
    return out


def _session_payload(supabase: Any, session: dict) -> dict:
    units = (
        supabase.table("writing_session_units")
        .select("id,unit_number,status,practice_microtopic_id,unit_constraints")
        .eq("session_id", session["id"])
        .order("unit_number")
        .execute()
    ).data or []
    resume = _resume_unit_state(supabase, session, [u["id"] for u in units])
    for u in units:
        state = resume.get(u["id"], {})
        u["latest_version"] = state.get("latest_version")
        u["previous_version"] = state.get("previous_version")
        u["latest_evaluation"] = state.get("latest_evaluation")
    return {
        "session": session,
        "prompt": _session_prompt(supabase, session),
        "units": units,
        "feedback_released": _feedback_released(session),
    }


# --- endpoints ------------------------------------------------------------

@router.post("/sessions")
def create_session(body: CreateSessionRequest, user: dict = Depends(get_current_user)) -> dict:
    user_id = user.get("id")
    # EWP-2 ships learning mode only; the exam-session runtime (§9.2/§9.3 —
    # answer locking, blank versions, feedback release) is a later slice.
    if body.mode != "learning":
        raise HTTPException(status_code=400, detail="exam mode is not available in EWP-2")

    supabase = get_supabase_admin()
    prompt = (
        supabase.table("writing_prompts")
        .select("*")
        .eq("id", str(body.prompt_id))
        .eq("reviewer_status", "verified")
        .eq("is_active", True)
        .maybe_single()
        .execute()
    ).data
    if not prompt:
        raise HTTPException(status_code=404, detail="prompt not found or not verified/active")

    # A supplied study_task must belong to the caller (launch-identity check).
    # It is ALSO the authoritative source of exam context for applicability
    # enforcement (§17 content-scoping): study_tasks carry the exam_id /
    # exam_phase_id the task was scheduled under (migration 034). We never trust
    # an unvalidated client-supplied exam — the context is derived from the
    # owner-validated task, or is absent (fail-closed) when no task is supplied.
    exam_id: str | None = None
    exam_phase_id: str | None = None
    if body.study_task_id is not None:
        task = (
            supabase.table("study_tasks").select("id,user_id,exam_id,exam_phase_id")
            .eq("id", str(body.study_task_id)).maybe_single().execute()
        ).data
        if not task or task.get("user_id") != user_id:
            raise HTTPException(status_code=404, detail="study task not found")
        exam_id = task.get("exam_id")
        exam_phase_id = task.get("exam_phase_id")

    # DEFAULT-DENY applicability (migration 214): the prompt must have an ACTIVE
    # matching target for the authoritative exam context — otherwise it is not
    # launchable, regardless of its verified/active content state. With no task
    # (hence no exam context) only an explicit active GLOBAL target passes; a
    # scoped prompt is denied fail-closed. This is the SOLE launch authority now
    # that migration 214 removed the exam-scope columns from writing_prompts and
    # the raw public-read policy is being locked down (migration 218).
    if not applicability.is_prompt_applicable(
        supabase, str(body.prompt_id), exam_id=exam_id, exam_phase_id=exam_phase_id
    ):
        raise HTTPException(
            status_code=403,
            detail="prompt is not applicable for this exam context",
        )

    constraints = validate_unit_constraints({"schema_version": 1})
    # Atomic: session + all units in one transaction (§8.0). Learning-mode
    # feedback is immediate.
    session = (
        supabase.rpc("ewp_create_writing_session", {
            "p_user": user_id,
            "p_prompt": str(body.prompt_id),
            "p_study_task": str(body.study_task_id) if body.study_task_id else None,
            "p_mode": "learning",
            "p_projection_revision": _current_projection_revision(),
            "p_policy": "immediate",
            "p_delay": None,
            "p_unit_count": prompt.get("required_sentence_count") or 1,
            "p_microtopic": prompt.get("microtopic_id"),
            "p_constraints": constraints,
        }).execute()
    ).data
    return _session_payload(supabase, session)


@router.get("/sessions/{session_id}")
def get_session(session_id: UUID, user: dict = Depends(get_current_user)) -> dict:
    supabase = get_supabase_admin()
    session = _owned_session(supabase, str(session_id), user.get("id"))
    return _session_payload(supabase, session)


@router.post("/sessions/{session_id}/units/{unit_number}/submit")
def submit_unit(
    session_id: UUID, unit_number: int, body: SubmitUnitRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    supabase = get_supabase_admin()
    session = _owned_session(supabase, str(session_id), user.get("id"))
    if session["status"] in (st.SESSION_COMPLETED, st.SESSION_ABANDONED):
        raise HTTPException(status_code=409, detail="session is not open for submission")

    unit = (
        supabase.table("writing_session_units")
        .select("*")
        .eq("session_id", str(session_id))
        .eq("unit_number", unit_number)
        .maybe_single()
        .execute()
    ).data
    if not unit:
        raise HTTPException(status_code=404, detail="unit not found")

    # Read from the session's IMMUTABLE prompt snapshot (migration 221), not the
    # live writing_prompts row — a prompt edit after session creation must not
    # change word-limit/required-word validation for an already-created session.
    snap = session.get("prompt_snapshot") or {}
    required_words = snap.get("required_words") or []
    constraints = unit.get("unit_constraints") or {}

    # Per-unit bounds override prompt-level bounds when present (§4.4a).
    min_words = constraints.get("min_words", snap.get("min_words"))
    max_words = constraints.get("max_words", snap.get("max_words"))

    # Deterministic Stage-1 (pure) — computed before the atomic write.
    siblings = _sibling_latest_texts(supabase, str(session_id), exclude_unit_id=unit["id"])
    result = det.evaluate_unit(
        body.answer_text,
        min_words=min_words,
        max_words=max_words,
        required_words=constraints.get("hint_words"),
        other_unit_texts=siblings,
    )

    # Atomic submit: locks (session -> all units ascending), version CAS,
    # version + evaluation + job insert, unit transition — one transaction (§8.0).
    try:
        submit = (
            supabase.rpc("ewp_submit_writing_unit", {
                "p_user": user.get("id"),
                "p_session": str(session_id),
                "p_unit_number": unit_number,
                "p_answer": body.answer_text,
                "p_client_wc": body.client_word_count,
                "p_server_wc": result.server_word_count,
                "p_content_hash": compute_content_hash(body.answer_text),
                "p_expected_version": body.version_number,
                "p_det_result": result.to_dict(),
                "p_det_version": result.evaluator_version,
            }).execute()
        ).data
    except Exception as exc:  # PostgREST surfaces the RAISE message
        raise _rpc_error(exc)

    # The submission (version + evaluation + job + unit transition) has already
    # committed atomically AND rolled the session up in-transaction inside the
    # RPC, so session status is already consistent here. Writing the authoritative
    # coverage row + re-finalizing under the completion gate (§4.7a, §8.0) is a
    # best-effort REFRESH: both are idempotent and pinned to the version_set_hash,
    # so a failure here is recomputed on the next submit/finalize/read. It must
    # NOT surface as an error — that would leave the client unable to resubmit an
    # already-committed version (duplicate submit is rejected by design).
    coverage: dict | None = None
    try:
        coverage = coverage_checker.run_coverage_check(supabase, str(session_id), required_words)
        supabase.rpc("ewp_finalize_writing_session", {
            "p_user": user.get("id"),
            "p_session": str(session_id),
        }).execute()
    except Exception:  # noqa: BLE001 — submission is durable; refresh is retryable
        logger.warning(
            "post-submit coverage/finalize refresh failed for session %s (submission committed; "
            "status already rolled up in-transaction, refresh is idempotent)",
            session_id, exc_info=True,
        )
    return {
        "evaluation": (submit or {}).get("evaluation"),
        "version_number": (submit or {}).get("version_number"),
        "deterministic_result": result.to_dict(),
        "coverage": coverage,
        "coverage_refresh_deferred": coverage is None,
    }


@router.post("/sessions/{session_id}/units/{unit_id}/reopen")
def reopen_unit(
    session_id: UUID, unit_id: UUID, body: ReopenUnitRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    supabase = get_supabase_admin()
    # Atomic: locks session + all units, validates learning-mode/status/ready +
    # optimistic latest-version, transitions ready -> draft (§7.3, §8.0).
    try:
        out = (
            supabase.rpc("ewp_reopen_writing_unit", {
                "p_user": user.get("id"),
                "p_session": str(session_id),
                "p_unit": str(unit_id),
                "p_expected_latest_version": str(body.expected_latest_version_id),
            }).execute()
        ).data
    except Exception as exc:
        raise _rpc_error(exc)

    # Reopen rolls the session up in the same transaction (ready -> draft ->
    # rollup, §8.0), so no separate finalize call is needed here.
    return out or {"unit_id": str(unit_id), "status": st.UNIT_DRAFT}


def _feedback_released(session: dict) -> bool:
    """Whether feedback is visible for a session (learning=always; exam=gated)."""
    if session.get("mode") == "learning":
        return True
    released = session.get("feedback_released_at")
    if not released:
        return False
    from datetime import datetime, timezone

    try:
        ts = datetime.fromisoformat(str(released).replace("Z", "+00:00"))
    except ValueError:
        return False
    return ts <= datetime.now(timezone.utc)


@router.get("/sessions/{session_id}/evaluations/{evaluation_id}")
def get_evaluation(
    session_id: UUID, evaluation_id: UUID, user: dict = Depends(get_current_user),
) -> dict:
    supabase = get_supabase_admin()
    session = _owned_session(supabase, str(session_id), user.get("id"))

    # Prove the evaluation belongs to THIS owned session: evaluation -> version
    # -> unit -> session. A globally-fetched evaluation is not sufficient.
    evaluation = (
        supabase.table("writing_evaluations").select("*").eq("id", str(evaluation_id)).maybe_single().execute()
    ).data
    if not evaluation:
        raise HTTPException(status_code=404, detail="evaluation not found")
    version = (
        supabase.table("writing_unit_versions").select("unit_id")
        .eq("id", evaluation["unit_version_id"]).maybe_single().execute()
    ).data
    unit = version and (
        supabase.table("writing_session_units").select("session_id")
        .eq("id", version["unit_id"]).maybe_single().execute()
    ).data
    if not unit or unit["session_id"] != str(session_id):
        raise HTTPException(status_code=404, detail="evaluation not found")

    # Exam-mode feedback is gated on release; before release, hide the body.
    if not _feedback_released(session):
        raise HTTPException(status_code=409, detail="feedback not yet released")
    return {"evaluation": evaluation}


def _error_lab_rows(supabase: Any, user_id: str) -> list[dict]:
    """Current-state Error Lab issue rows for the caller, from the SQL read model.

    Delegates the whole session -> unit -> version -> evaluation -> issue walk,
    the effective-review-decision fold (§4.10a), the reclassification remap, and
    the canonical-topic join to ``public.ewp_error_lab`` (migration 213) in a
    SINGLE owner-scoped round-trip — no progressive ``IN (...)`` fan-out. The RPC
    already returns only owner-scoped, feedback-released, ``affects_current_state``
    issues with effective invalidation excluded and effective reclassification
    applied (corrected issue_type + remapped active canonical microtopic), each
    joined to its microtopic name/slug. Read-only; no pending/rejected/stale/
    invalidated leakage.
    """
    if not user_id:
        return []
    rows = (supabase.rpc("ewp_error_lab", {"p_user": user_id}).execute()).data or []
    return rows


@router.get("/error-summary")
def error_summary(user: dict = Depends(get_current_user)) -> dict:
    """Recurring writing issues for the CALLER, grouped by microtopic.

    Counts the caller's current-state issues from the ``ewp_error_lab`` read
    model (owner-scoped, feedback-released, `affects_current_state=true`,
    effective-invalidation aware and reclassification-remapped — §4.8/§4.10a).
    Withdrawn false positives are excluded and reclassified issues are counted
    under their CORRECTED microtopic.
    """
    supabase = get_supabase_admin()
    rows = _error_lab_rows(supabase, user.get("id"))
    counts: dict[str, int] = {}
    for r in rows:
        key = r.get("microtopic_id") or "unmapped"
        counts[key] = counts.get(key, 0) + 1
    return {"by_microtopic": counts}


@router.get("/error-lab")
def error_lab(user: dict = Depends(get_current_user)) -> dict:
    """Error Lab drill-down: the caller's current-state issues by microtopic (EWP-4).

    Reads the ``ewp_error_lab`` server-side model (§4.8/§4.10a gating, effective
    reclassification applied) and shapes it into per-microtopic groups the Error
    Lab renders: issue_type (corrected when reclassified), severity, quoted_text/
    explanation, the UTF-16 span, and the human ``microtopic_name`` +
    ``microtopic_slug`` (never a bare UUID). Ordered busiest-microtopic-first and
    most-recent-first within a group. Read-only; never leaks pending/rejected/
    stale/invalidated findings.

    Response: ``{"items": [{microtopic_id, microtopic_name, microtopic_slug,
    issue_count, issues: [...]}, ...]}`` — ``items`` matches the frontend
    ``useApiCollection`` contract; ``microtopic_id`` is kept only as an internal
    grouping key.
    """
    supabase = get_supabase_admin()
    rows = _error_lab_rows(supabase, user.get("id"))

    groups: dict[str, dict] = {}
    for r in rows:
        mid = r.get("microtopic_id")
        key = mid or "unmapped"
        grp = groups.get(key)
        if grp is None:
            grp = {
                "microtopic_id": mid,
                "microtopic_name": r.get("microtopic_name"),
                "microtopic_slug": r.get("microtopic_slug"),
                "issues": [],
            }
            groups[key] = grp
        grp["issues"].append({
            "id": r.get("id"),
            "issue_type": r.get("issue_type"),
            "severity": r.get("severity"),
            "quoted_text": r.get("quoted_text"),
            "explanation": r.get("explanation"),
            "suggested_text": r.get("suggested_text"),
            "span_start_utf16": r.get("span_start_utf16"),
            "span_end_utf16": r.get("span_end_utf16"),
            "microtopic_id": mid,
            "created_at": r.get("created_at"),
        })

    items = []
    for grp in groups.values():
        issues = grp["issues"]
        issues.sort(key=lambda i: str(i.get("created_at") or ""), reverse=True)
        items.append({
            "microtopic_id": grp["microtopic_id"],
            "microtopic_name": grp["microtopic_name"],
            "microtopic_slug": grp["microtopic_slug"],
            "issue_count": len(issues),
            "issues": issues,
        })
    # Busiest microtopic first; deterministic tiebreak on the group key.
    items.sort(key=lambda g: (-g["issue_count"], str(g["microtopic_id"] or "")))
    return {"items": items}


# --- internals ------------------------------------------------------------

def _current_projection_revision() -> int:
    """Code-defined projection revision pinned at session creation (§4.11)."""
    return 1


# Map the RPC RAISE prefixes to HTTP status codes.
_RPC_STATUS = {
    "ewp_not_found": 404,
    "ewp_stale_version": 409,
    "ewp_not_submittable": 409,
    "ewp_session_closed": 409,
    "ewp_reopen_forbidden": 409,
    "ewp_mode_unsupported": 400,
}


def _rpc_error(exc: Exception) -> HTTPException:
    msg = str(getattr(exc, "message", None) or exc)
    for prefix, code in _RPC_STATUS.items():
        if prefix in msg:
            return HTTPException(status_code=code, detail=msg.split("\n", 1)[0])
    logger.exception("writing-practice RPC failed")
    return HTTPException(status_code=500, detail="writing practice operation failed")


def _sibling_latest_texts(supabase: Any, session_id: str, *, exclude_unit_id: str) -> dict[int, str]:
    units = (
        supabase.table("writing_session_units").select("id,unit_number")
        .eq("session_id", session_id).execute()
    ).data or []
    out: dict[int, str] = {}
    for u in units:
        if u["id"] == exclude_unit_id:
            continue
        latest = (
            supabase.table("writing_unit_versions").select("answer_text,version_number")
            .eq("unit_id", u["id"]).order("version_number", desc=True).limit(1).execute()
        ).data or []
        if latest:
            out[u["unit_number"]] = latest[0]["answer_text"]
    return out
