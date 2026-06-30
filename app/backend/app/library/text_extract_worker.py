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

Design constraints
------------------
- Single-process, single-job-per-pass (FIFO). The APScheduler job runs
  with ``max_instances=1`` and ``coalesce=True``, so only one pass is
  ever in flight within a single process.
- ``claim_next_text_extract_job`` is a FIFO SELECT, not an atomic UPDATE.
  The real conditional claim (``UPDATE … WHERE status='queued' RETURNING``)
  happens inside ``run_text_extract_job → _claim_job``. Two concurrent
  workers could both select the same row; the loser gets ``ExtractConflict``
  and returns ``processed=0, status='conflict'``. With ``max_instances=1``
  this race cannot happen within a single process.
- Failed jobs stay ``status='failed'``. Transient retry with backoff is a
  separate follow-up (see issue #813). Dead-letter handling (alert on
  accumulated failures) is deferred.
- Fallback failure recovery: if ``run_text_extract_job`` raises an
  exception that bypassed its internal ``_fail()`` handler, the worker
  attempts a best-effort fallback UPDATE to keep the job from staying
  stranded in ``running``.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.library.text_extract import ExtractConflict, run_text_extract_job

logger = logging.getLogger("career_copilot.library.text_extract_worker")

# Scopes handled by this worker. Personal-library and other user-owned
# scopes must NOT be included — see module docstring.
_ADMIN_SCOPES = frozenset({"admin_exam_intelligence"})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fallback_fail_job(sb, job_id: str, error: str) -> None:
    """Best-effort: flip a stranded 'running' job to 'failed'.

    Called when run_text_extract_job raises an exception that bypassed
    its internal _fail() handler (e.g. a transport error between _claim_job
    and the first ownership check). This prevents the job from blocking
    future enqueue/retry under the partial unique index.

    Scoped to status='running' so it cannot clobber a job that was
    concurrently recovered by another path.
    """
    try:
        sb.table("document_processing_jobs").update({
            "status": "failed",
            "finished_at": _now_iso(),
            "error_code": "worker_unhandled_error",
            "error_message": error[:500],
        }).eq("id", job_id).eq("status", "running").execute()
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

    Only admin-scoped jobs are returned (scope IN _ADMIN_SCOPES). Personal-
    library jobs are excluded; they have their own /process-text endpoint.

    Returns the oldest matching row, or None if the queue is empty.
    """
    rows = (
        sb.table("document_processing_jobs")
        .select("id, document_id")
        .eq("job_type", "text_extract")
        .eq("status", "queued")
        .in_("scope", list(_ADMIN_SCOPES))
        .order("created_at", desc=False)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def run_worker_pass(sb) -> dict[str, Any]:
    """Claim and run at most one queued admin text_extract job.

    Returns a summary dict for the scheduler's ``_last_run`` log:
    ``{"processed": 0|1, "job_id": str|None, "status": str, "error": str|None}``.

    ``status`` values:
    - ``"idle"``      — queue was empty; nothing to do.
    - ``"succeeded"`` — extraction completed successfully.
    - ``"failed"``    — extraction ran but the job ended in a failed state.
    - ``"conflict"``  — another worker claimed the job first (race); processed=0.

    ``processed=1`` means a job was attempted; ``processed=0`` means no job
    was attempted (idle or conflict). The scheduler's ``_wrap`` logs
    ``ok=False`` for any ``status='failed'`` result so ``/api/admin/jobs``
    reflects the operational failure.
    """
    candidate = claim_next_text_extract_job(sb)
    if candidate is None:
        return {"processed": 0, "job_id": None, "status": "idle", "error": None}

    job_id = candidate["id"]
    document_id = candidate["document_id"]

    try:
        result = run_text_extract_job(
            sb,
            job_id,
            user_id=None,
            admin_scope="admin_exam_intelligence",
        )
        final_status = (result.get("job") or {}).get("status", "succeeded")
        logger.info(
            "text-extract worker: job_id=%s doc=%s → %s",
            job_id, document_id, final_status,
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
        # ownership check), the job may be stranded at status='running'.
        # Apply a best-effort fallback to prevent it from blocking future
        # enqueue under the partial unique index.
        _fallback_fail_job(sb, job_id, error_str)
        logger.exception("text-extract worker: job_id=%s unhandled failure: %s", job_id, exc)
        return {
            "processed": 1,
            "job_id": job_id,
            "status": "failed",
            "error": error_str,
        }
