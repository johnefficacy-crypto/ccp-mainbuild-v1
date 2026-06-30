"""Background worker that claims and runs queued text_extract jobs.

Designed to be wired into the APScheduler loop in
``app/notifications/scheduler.py`` via ``_job_text_extract_worker``.

Design constraints (from issue #540):
- Single-process, single-job-per-pass (FIFO). Current load does not
  require distributed workers or priority queues.
- Claim is atomic: ``UPDATE … WHERE status='queued' … RETURNING *`` via
  PostgREST ensures at most one runner executes each job.
- Failed jobs (``status='failed'``) are NOT automatically retried by this
  worker — they stay failed for operator review. Operators can reset them
  manually or via the stuck-doc cleanup endpoint (issue #542).
- Dead-letter: jobs that fail extraction stay in ``status='failed'``.
  No infinite retry loop.
- Admin-scoped documents (``scope='admin_exam_intelligence'``, ``owner_user_id=NULL``)
  are handled via ``admin_scope='admin_exam_intelligence'`` on the
  underlying ``run_text_extract_job`` call.
"""
from __future__ import annotations

import logging
from typing import Any

from app.library.text_extract import ExtractConflict, run_text_extract_job

logger = logging.getLogger("career_copilot.library.text_extract_worker")

# Scopes that are treated as admin-owned (no owner_user_id check).
_ADMIN_SCOPES = frozenset({"admin_exam_intelligence"})


def claim_next_text_extract_job(sb) -> dict | None:
    """Atomically claim the oldest queued text_extract job.

    Uses a conditional UPDATE (status='queued' → 'running') so only one
    worker wins when multiple processes race. Returns the claimed row, or
    None if the queue is empty.

    Note: PostgREST does not support ``attempt_count = attempt_count + 1``
    arithmetic in a single UPDATE. The increment is handled inside
    ``_claim_job`` in text_extract.py; here we just identify the next
    candidate and let ``run_text_extract_job`` do the actual claim.
    """
    rows = (
        sb.table("document_processing_jobs")
        .select("id, document_id")
        .eq("job_type", "text_extract")
        .eq("status", "queued")
        .order("created_at", desc=False)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def _get_document_scope(sb, document_id: str) -> str | None:
    """Return the ``scope`` field of the document_asset row, or None."""
    rows = (
        sb.table("document_assets")
        .select("scope")
        .eq("id", document_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0].get("scope") if rows else None


def run_worker_pass(sb) -> dict[str, Any]:
    """Claim and run at most one queued text_extract job.

    Returns a summary dict suitable for the scheduler's ``_last_run`` log:
    ``{"processed": 0|1, "job_id": str|None, "status": str, "error": str|None}``.

    Callers should schedule this at the desired polling interval (default 60s).
    To drain a backlog, call in a loop until ``processed == 0``.
    """
    candidate = claim_next_text_extract_job(sb)
    if candidate is None:
        return {"processed": 0, "job_id": None, "status": "idle", "error": None}

    job_id = candidate["id"]
    document_id = candidate["document_id"]

    scope = _get_document_scope(sb, document_id)
    admin_scope = scope if scope in _ADMIN_SCOPES else None

    try:
        result = run_text_extract_job(
            sb,
            job_id,
            user_id=None,
            admin_scope=admin_scope,
        )
        final_status = (result.get("job") or {}).get("status", "succeeded")
        logger.info(
            "text-extract worker: job_id=%s doc=%s scope=%s → %s",
            job_id, document_id, scope, final_status,
        )
        return {
            "processed": 1,
            "job_id": job_id,
            "status": final_status,
            "error": None,
        }
    except ExtractConflict as exc:
        # Another process claimed the same job between our SELECT and the
        # UPDATE inside run_text_extract_job. Not an error — just a race.
        logger.debug("text-extract worker: job_id=%s already claimed: %s", job_id, exc)
        return {
            "processed": 0,
            "job_id": job_id,
            "status": "conflict",
            "error": str(exc),
        }
    except Exception as exc:  # noqa: BLE001
        # run_text_extract_job already wrote status='failed' on the job row
        # before raising. Log here so the scheduler sees it too.
        logger.exception("text-extract worker: job_id=%s failed: %s", job_id, exc)
        return {
            "processed": 1,
            "job_id": job_id,
            "status": "failed",
            "error": str(exc),
        }
