"""Background worker that claims and runs queued text_extract jobs.

Designed to be wired into the APScheduler loop in
``app/notifications/scheduler.py`` via ``_job_text_extract_worker``.

Scope: ADMIN documents only
----------------------------
This worker is scoped to documents whose ``scope`` field is in
``_ADMIN_SCOPES`` (currently ``{'admin_exam_intelligence'}``). Personal-
library documents (``scope='personal_library'``, real ``owner_user_id``)
already have the synchronous ``POST /library/items/{id}/process-text``
endpoint and must NOT be claimed here — the ownership check in
``run_text_extract_job`` would mark every one as ``ownership_mismatch``
because the worker has no ``user_id`` to pass.

Schema note
-----------
``scope`` lives on ``document_assets``, **not** on
``document_processing_jobs``.  ``claim_next_text_extract_job`` uses a
PostgREST inner-join embed (``document_assets!inner(scope)``) so that
the database filters out personal-library rows before any Python code
sees them.  The embedded ``scope`` is also forwarded to
``run_text_extract_job`` as ``admin_scope`` so the service layer can
verify the document belongs to an admin scope.

Design constraints
------------------
- Single-process, single-job-per-pass (FIFO). The APScheduler job runs
  with ``max_instances=1`` and ``coalesce=True``, so only one pass is
  ever in flight within a single process.
- ``claim_next_text_extract_job`` is a FIFO SELECT, not an atomic UPDATE.
  The real conditional claim (``UPDATE … WHERE status IN ('queued','failed')
  RETURNING``) happens inside ``run_text_extract_job → _claim_job``.
  Two concurrent workers could both select the same row; the loser gets
  ``ExtractConflict`` and returns ``processed=0, status='conflict'``. With
  ``max_instances=1`` this race cannot happen within a single process.
- Transient-failure retry (issue #813): jobs whose ``error_code`` is in
  ``_TRANSIENT_ERROR_CODES`` are retried via ``claim_next_retry_job`` up to
  ``MAX_TRANSIENT_ATTEMPTS`` times with per-attempt backoff of
  ``attempt_count × BASE_BACKOFF_SECONDS`` seconds since ``finished_at``.
  (Issue #813 specifies ``updated_at``; ``document_processing_jobs`` has no
  ``updated_at`` column — ``finished_at`` is the correct field, which
  ``_fail()`` always sets on terminal status.)  Terminal error codes are
  never retried.  The attempt cap is enforced server-side via a PostgREST
  ``lt`` filter so capped rows cannot push eligible rows past PostgREST's
  ``max_rows`` ceiling.  Null or malformed ``finished_at`` values cause the
  row to be skipped (fail-closed).
- Fairness: ``run_worker_pass`` picks the candidate whose effective due time
  is earliest — new queued jobs (due = ``created_at``) compete against retry
  candidates (due = ``finished_at + backoff``). This prevents a sustained
  ingestion burst from starving retry candidates indefinitely.
- No pre-claim status mutation: ``text_extract._claim_job`` already accepts
  ``status IN ('queued', 'failed')``. The worker must not touch the job row
  before calling ``run_text_extract_job`` to avoid violating the partial
  unique index ``uq_document_processing_jobs_active_text_extract``.
- Fallback failure recovery: if ``run_text_extract_job`` raises an
  exception that bypassed its internal ``_fail()`` handler, the worker
  attempts a best-effort fallback UPDATE on both the job row and the
  parent ``document_assets`` row so neither stays stranded.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.library.text_extract import ExtractConflict, run_text_extract_job

logger = logging.getLogger("career_copilot.library.text_extract_worker")

# Scopes handled by this worker. Personal-library and other user-owned
# scopes must NOT be included — see module docstring.
_ADMIN_SCOPES = frozenset({"admin_exam_intelligence"})

# Error codes that indicate a transient infrastructure failure (retried).
# All other error codes are terminal and never retried.
_TRANSIENT_ERROR_CODES = frozenset({
    "download_failed",
    "storage_object_missing",
    "page_write_failed",
})

MAX_TRANSIENT_ATTEMPTS = 3
BASE_BACKOFF_SECONDS = 60


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(ts: str) -> datetime:
    """Parse an ISO-8601 timestamp, normalising 'Z' → '+00:00'."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _fallback_fail_job(sb, job_id: str, document_id: str, error: str) -> None:
    """Best-effort: flip a stranded 'running' job and its parent document to 'failed'.

    Called when run_text_extract_job raises an exception that bypassed
    its internal _fail() handler (e.g. a transport error between _claim_job
    and the first ownership check). Mirrors what _fail() does inside
    text_extract.py so both terminal states are always written together.

    Job update is scoped to status='running' so it cannot clobber a job
    already recovered by another path. Document update skips 'archived'
    rows for the same reason.
    """
    try:
        updated = sb.table("document_processing_jobs").update({
            "status": "failed",
            "finished_at": _now_iso(),
            "error_code": "worker_unhandled_error",
            "error_message": error[:500],
        }).eq("id", job_id).eq("status", "running").execute().data or []
        # Only flip the document if we actually claimed the terminal update on
        # the job row.  If updated is empty the job was already terminal (e.g.
        # a concurrent recovery path beat us here), so we must not clobber it.
        if updated:
            sb.table("document_assets").update({
                "status": "failed",
            }).eq("id", document_id).neq("status", "archived").execute()
    except Exception as fb_exc:  # noqa: BLE001
        logger.warning(
            "text-extract worker: fallback fail for job_id=%s also failed: %s",
            job_id, fb_exc,
        )


def claim_next_text_extract_job(sb) -> dict | None:
    """Select the oldest queued admin text_extract job.

    This is a FIFO SELECT, not an atomic UPDATE. The real conditional
    claim happens inside run_text_extract_job → _claim_job. With
    max_instances=1 on the scheduler, only one pass is ever in flight
    within a single process, making the SELECT-then-claim sequence safe.

    Scope is resolved through the parent document_assets row via a
    PostgREST inner-join embed. Because document_processing_jobs carries
    no scope column, the join is the only correct way to filter. Only
    jobs whose parent document has a scope in _ADMIN_SCOPES are returned.

    Returns the oldest matching row (including the embedded document_assets
    dict), or None if the queue is empty.
    """
    rows = (
        sb.table("document_processing_jobs")
        .select("id, document_id, created_at, document_assets!inner(scope)")
        .eq("job_type", "text_extract")
        .eq("status", "queued")
        .in_("document_assets.scope", list(_ADMIN_SCOPES))
        .order("created_at", desc=False)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def claim_next_retry_job(sb) -> dict | None:
    """Select the oldest retry-eligible transient-failed admin text_extract job.

    A job is retry-eligible when ALL of:
    - status = 'failed'
    - error_code is in _TRANSIENT_ERROR_CODES
    - attempt_count < MAX_TRANSIENT_ATTEMPTS  (enforced server-side via lt filter)
    - now() - finished_at >= attempt_count * BASE_BACKOFF_SECONDS

    The attempt cap is enforced in the PostgREST query so that capped
    rows (which remain 'failed' permanently) cannot consume the response
    and hide newer eligible rows behind PostgREST's max_rows ceiling.

    The backoff condition is evaluated in Python because PostgREST cannot
    express computed column arithmetic. Null or malformed finished_at values
    cause the row to be skipped (fail-closed). The result set is bounded
    by an explicit limit so the Python filter loop is always finite.

    Returns the oldest eligible row (ordered by finished_at ascending), or
    None if no eligible job exists.
    """
    rows = (
        sb.table("document_processing_jobs")
        .select("id, document_id, attempt_count, finished_at, document_assets!inner(scope)")
        .eq("job_type", "text_extract")
        .eq("status", "failed")
        .in_("error_code", list(_TRANSIENT_ERROR_CODES))
        .in_("document_assets.scope", list(_ADMIN_SCOPES))
        .lt("attempt_count", MAX_TRANSIENT_ATTEMPTS)
        .order("finished_at", desc=False)
        .limit(100)
        .execute()
        .data
        or []
    )
    now = datetime.now(timezone.utc)
    for row in rows:
        attempt_count = row.get("attempt_count") or 0
        finished_at_str = row.get("finished_at")
        if not finished_at_str:
            # Fail-closed: cannot calculate backoff without a timestamp.
            continue
        try:
            finished_at = _parse_iso(finished_at_str)
        except (ValueError, TypeError):
            # Fail-closed: malformed or timezone-naive timestamp.
            continue
        backoff = timedelta(seconds=attempt_count * BASE_BACKOFF_SECONDS)
        if now - finished_at < backoff:
            continue
        return row
    return None


def run_worker_pass(sb) -> dict[str, Any]:
    """Claim and run at most one text_extract job (queued or retry-eligible).

    Scheduling policy — fair combined due-time ordering:
    Both the normal FIFO queue and the transient-retry queue are checked
    each pass. The candidate whose effective due time is earliest wins:
    - Queued jobs: due = created_at (immediately due on insertion).
    - Retry candidates: due = finished_at + attempt_count * BASE_BACKOFF_SECONDS.
    This prevents a sustained ingestion burst from starving retry candidates.

    Claim path: run_text_extract_job's internal _claim_job already accepts
    status IN ('queued', 'failed'), so no pre-claim status mutation is needed
    or performed. The conditional UPDATE in _claim_job provides the
    atomicity guarantee.

    Returns a summary dict for the scheduler's ``_last_run`` log:
    ``{"processed": 0|1, "job_id": str|None, "status": str, "error": str|None}``.

    ``status`` values:
    - ``"idle"``      — no queued job and no retry candidate; nothing to do.
    - ``"succeeded"`` — extraction completed successfully.
    - ``"failed"``    — extraction ran but the job ended in a failed state.
    - ``"conflict"``  — another worker claimed the job first (race); processed=0.

    ``processed=1`` means a job was attempted; ``processed=0`` means no job
    was attempted (idle or conflict).
    """
    queued = claim_next_text_extract_job(sb)
    retry = claim_next_retry_job(sb)

    is_retry = False

    if queued is None and retry is None:
        return {"processed": 0, "job_id": None, "status": "idle", "error": None}
    elif queued is None:
        candidate = retry
        is_retry = True
    elif retry is None:
        candidate = queued
    else:
        # Fair combined ordering: pick whichever became due earlier.
        # Queued jobs are due at their creation time.
        # Retry candidates are due at finished_at + backoff.
        try:
            queued_due = _parse_iso(queued.get("created_at") or "")
        except (ValueError, TypeError):
            queued_due = datetime.now(timezone.utc)
        try:
            attempt_count = retry.get("attempt_count") or 0
            retry_due = _parse_iso(retry.get("finished_at") or "") + timedelta(
                seconds=attempt_count * BASE_BACKOFF_SECONDS
            )
        except (ValueError, TypeError):
            retry_due = datetime.now(timezone.utc)

        if retry_due <= queued_due:
            candidate = retry
            is_retry = True
        else:
            candidate = queued

    job_id = candidate["id"]
    document_id = candidate["document_id"]
    # Extract admin_scope from the embedded document_assets so we forward
    # the correct scope to run_text_extract_job rather than hard-coding it.
    admin_scope = (candidate.get("document_assets") or {}).get(
        "scope", next(iter(_ADMIN_SCOPES))
    )

    try:
        result = run_text_extract_job(
            sb,
            job_id,
            user_id=None,
            admin_scope=admin_scope,
        )
        final_status = (result.get("job") or {}).get("status") or "failed"
        if final_status not in ("succeeded", "failed", "queued", "running"):
            final_status = "failed"
        logger.info(
            "text-extract worker: job_id=%s doc=%s retry=%s → %s",
            job_id, document_id, is_retry, final_status,
        )
        return {
            "processed": 1,
            "job_id": job_id,
            "status": final_status,
            "error": None,
        }
    except ExtractConflict as exc:
        # Another process claimed the same job between our SELECT and the
        # conditional UPDATE inside run_text_extract_job. Not an error.
        logger.debug("text-extract worker: job_id=%s already claimed: %s", job_id, exc)
        return {
            "processed": 0,
            "job_id": job_id,
            "status": "conflict",
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        error_str = str(exc)
        # run_text_extract_job calls _fail() internally before re-raising
        # _ExtractErrors. For any other exception that escapes before _fail()
        # is reached (e.g. a transport error between _claim_job and the first
        # ownership check), the job and its parent document may be stranded.
        # Apply a best-effort fallback to write both terminal states.
        _fallback_fail_job(sb, job_id, document_id, error_str)
        logger.exception("text-extract worker: job_id=%s unhandled failure: %s", job_id, exc)
        return {
            "processed": 1,
            "job_id": job_id,
            "status": "failed",
            "error": error_str,
        }
