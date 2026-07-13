"""Current-affairs ingestion primitive (GQR-G2).

``ingest_source`` runs one source through: resolve URL → conditional fetch
(reusing ``app.scraping.fetcher``) → 304 short-circuit → content-hash dedup →
immutable document snapshot → source-health update. It is the unit the future
``ca:ingest`` scheduler job (pipeline §9, GQR-G5) will call per source; keeping
it a pure ``(supabase, source) -> result`` function makes it testable now
without the scheduler.

No LLM, no extraction, no learner surface — this only lands evidence snapshots
and keeps source health current.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from app.scraping import fetcher
from app.current_affairs import sources as ca_sources

logger = logging.getLogger("career_copilot.current_affairs.ingestion")

_SOURCES = "current_affairs_sources"
_DOCUMENTS = "current_affairs_documents"


_DEFAULT_INTERVAL_HOURS = 24


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("db_op_failed op=current_affairs.ingestion err=%r", exc)
        return default


def _is_unique_violation(exc: Exception) -> bool:
    """True only for a Postgres unique-constraint conflict (23505) — the benign
    content-hash race. Any OTHER exception is a real infrastructure failure and must
    NOT be silently classified as a duplicate (checkpost fail-open fix)."""
    text = f"{getattr(exc, 'code', '')} {getattr(exc, 'message', '')} {exc}".lower()
    return "23505" in text or "duplicate key" in text or "unique constraint" in text


def _latest_document(supabase: Any, source_id: str) -> dict | None:
    """Most recent snapshot for the source — supplies the conditional-fetch
    validators (ETag / Last-Modified) so an unchanged feed 304s instead of
    re-downloading."""
    rows = _safe(
        lambda: supabase.table(_DOCUMENTS)
        .select("id,etag,last_modified,content_hash")
        .eq("source_id", source_id)
        .order("fetched_at", desc=True)
        .limit(1)
        .execute(),
        default=None,
    )
    data = getattr(rows, "data", None) or []
    return data[0] if data else None


def _update_health(
    supabase: Any,
    source_id: str,
    *,
    now_iso: str,
    status: str,
    success: bool,
    error: str | None = None,
    prev_failures: int = 0,
) -> None:
    """Best-effort source-health write. A success resets the failure streak; a
    failure increments it. Never raises — health is operational, not correctness
    critical, and must not sink an otherwise-successful ingest."""
    patch: dict[str, Any] = {
        "last_fetch_at": now_iso,
        "last_status": status,
        "last_error": None if success else error,
        "consecutive_failures": 0 if success else prev_failures + 1,
        "updated_at": now_iso,
    }
    if success:
        patch["last_success_at"] = now_iso
    _safe(
        lambda: supabase.table(_SOURCES).update(patch).eq("id", source_id).execute(),
        default=None,
    )


def ingest_source(
    supabase: Any,
    source: dict[str, Any],
    *,
    fetch: Callable[..., Any] = fetcher.fetch,
    now_iso: str | None = None,
) -> dict[str, Any]:
    """Ingest one current-affairs source. Returns a structured result dict with a
    ``status`` in:

      - ``skipped``       — inactive source or no usable URL configured.
      - ``not_modified``  — server returned 304; nothing changed.
      - ``error``         — fetch failed (network / HTTP / empty body).
      - ``duplicate``     — content hash already snapshotted for this source.
      - ``snapshotted``   — a new immutable document row was written.
      - ``deprioritised`` — fetched but pre-filtered out (reason recorded).

    Source health is updated on every terminal path. The document row (when
    written) is immutable; a changed body on a later run creates a NEW row rather
    than mutating this one.
    """
    now = now_iso or _now_iso()
    source_id = source.get("id")

    if not source.get("is_active", True):
        return {"status": "skipped", "reason": "inactive", "source_id": source_id}

    url = ca_sources.resolve_fetch_url(source)
    if not url:
        _update_health(
            supabase, source_id, now_iso=now, status="no_url", success=False,
            error="no_fetch_url_configured",
            prev_failures=int(source.get("consecutive_failures") or 0),
        )
        return {"status": "skipped", "reason": "no_fetch_url", "source_id": source_id}

    prev = _latest_document(supabase, source_id) or {}
    result = fetch(
        url,
        adapter_type=(source.get("adapter_type") or "html"),
        if_none_match=prev.get("etag"),
        if_modified_since=prev.get("last_modified"),
    )

    # 304 — the conditional-fetch validators matched; unchanged.
    if getattr(result, "status_code", None) == 304 or getattr(result, "error", None) == "not_modified":
        _update_health(supabase, source_id, now_iso=now, status="not_modified", success=True)
        return {"status": "not_modified", "source_id": source_id}

    if not getattr(result, "ok", False):
        err = getattr(result, "error", None) or "fetch_failed"
        _update_health(
            supabase, source_id, now_iso=now, status="error", success=False, error=err,
            prev_failures=int(source.get("consecutive_failures") or 0),
        )
        return {"status": "error", "reason": err, "source_id": source_id}

    content_hash = getattr(result, "content_hash", None)

    # Content dedup: byte-identical body already snapshotted for this source.
    if content_hash:
        existing = _safe(
            lambda: supabase.table(_DOCUMENTS)
            .select("id")
            .eq("source_id", source_id)
            .eq("content_hash", content_hash)
            .limit(1)
            .execute(),
            default=None,
        )
        dupe = (getattr(existing, "data", None) or [])
        if dupe:
            _update_health(supabase, source_id, now_iso=now, status="duplicate", success=True)
            return {"status": "duplicate", "source_id": source_id, "document_id": dupe[0].get("id")}

    accept, reason = ca_sources.prefilter_document(raw_text=getattr(result, "text", None))
    ingestion_status = "snapshotted" if accept else "deprioritised"

    defaults = ca_sources.adapter_defaults(source)
    document_type = defaults.document_type if defaults else None
    metadata: dict[str, Any] = {"content_type": getattr(result, "content_type", None)}
    if not accept and reason:
        metadata["prefilter_reason"] = reason

    payload = {
        "source_id": source_id,
        "source_url": url,
        "final_url": getattr(result, "final_url", None),
        "title": None,
        "document_type": document_type,
        "fetched_at": now,
        "content_hash": content_hash,
        "etag": getattr(result, "etag", None),
        "last_modified": getattr(result, "last_modified", None),
        "raw_text": getattr(result, "text", None),
        "metadata": metadata,
        "ingestion_status": ingestion_status,
    }
    prev_failures = int(source.get("consecutive_failures") or 0)
    try:
        inserted = supabase.table(_DOCUMENTS).insert(payload).execute()
        rows = getattr(inserted, "data", None) or []
    except Exception as exc:  # noqa: BLE001 — classify: content-race vs real write failure.
        if _is_unique_violation(exc):
            # A concurrent run won the unique content-hash race — the body IS captured,
            # just not by this run. Non-fatal duplicate; health stays green.
            _update_health(supabase, source_id, now_iso=now, status="write_contended", success=True)
            return {"status": "duplicate", "source_id": source_id, "document_id": None}
        # Genuine infrastructure write failure — surface it, red the health streak.
        _update_health(
            supabase, source_id, now_iso=now, status="error", success=False,
            error=f"write_failed: {exc}"[:200], prev_failures=prev_failures,
        )
        return {"status": "error", "reason": "write_failed", "source_id": source_id}
    if not rows:
        _update_health(
            supabase, source_id, now_iso=now, status="error", success=False,
            error="empty_insert", prev_failures=prev_failures,
        )
        return {"status": "error", "reason": "empty_insert", "source_id": source_id}

    _update_health(supabase, source_id, now_iso=now, status=ingestion_status, success=True)
    return {
        "status": ingestion_status,
        "source_id": source_id,
        "document_id": rows[0].get("id"),
        "reason": reason,
    }


def _is_due(source: dict[str, Any], now: datetime) -> bool:
    """Whether a source is due to crawl. Cadence comes from ``crawl_schedule.interval_hours``
    (jsonb config, default 24h) measured against ``last_fetch_at`` — there is no
    ``next_crawl_at`` column, so due-ness is derived here. A source never fetched
    (``last_fetch_at`` null) is always due. ``crawl_schedule`` is unconstrained JSONB, so a
    non-object value is tolerated (falls back to the default cadence) rather than raising."""
    sched = source.get("crawl_schedule")
    if not isinstance(sched, dict):
        sched = {}
    try:
        interval_h = float(sched.get("interval_hours") or _DEFAULT_INTERVAL_HOURS)
    except (TypeError, ValueError):
        interval_h = _DEFAULT_INTERVAL_HOURS
    if interval_h <= 0:
        interval_h = _DEFAULT_INTERVAL_HOURS
    last = source.get("last_fetch_at")
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
    except ValueError:
        return True
    return (now - last_dt).total_seconds() >= interval_h * 3600


_GEN_JOBS = "current_affairs_generation_jobs"
_GEN_JOB_KIND = "ca_generation"


def _iter_active_sources(supabase: Any, *, page_size: int = 200):
    """Yield EVERY active source, paged deterministically by id (no silent 100-row cap).

    Raises on a query failure so the caller can classify the pass as failed rather than
    reporting an all-zero success."""
    cursor: str | None = None
    while True:
        q = (supabase.table(_SOURCES).select("*").eq("is_active", True)
             .order("id").limit(page_size))
        if cursor is not None:
            q = q.gt("id", cursor)
        batch = getattr(q.execute(), "data", None) or []
        if not batch:
            return
        for row in batch:
            yield row
        if len(batch) < page_size:
            return
        cursor = batch[-1].get("id")


def _reconcile_pending_generation(supabase: Any, *, page_size: int = 500) -> dict[str, int]:
    """Durably enqueue a generation job for EVERY snapshotted document that has none.

    Covers freshly-snapshotted docs, this-pass enqueue failures, AND pre-existing G2
    backlog — the crawl loop no longer owns the (lossy) enqueue. ``ca_enqueue_generation_job``
    is only called for documents with NO job row (any status), because it raises a unique
    violation when a job already reached ``done`` (generation is fixed at 1). Enqueue
    failures are counted, not swallowed."""
    # Documents that already have a job (any status) — these are settled, skip them.
    jobs = _safe(
        lambda: supabase.table(_GEN_JOBS).select("document_id")
        .eq("job_kind", _GEN_JOB_KIND).limit(100000).execute(),
        default=None,
    )
    if jobs is None:
        return {"enqueued": 0, "enqueue_failed": 0, "reconcile_failed": 1}
    have_job = {str(r.get("document_id")) for r in (getattr(jobs, "data", None) or [])}

    enqueued = failed = 0
    cursor: str | None = None
    while True:
        q = (supabase.table(_DOCUMENTS).select("id")
             .eq("ingestion_status", "snapshotted").order("id").limit(page_size))
        if cursor is not None:
            q = q.gt("id", cursor)
        try:
            batch = getattr(q.execute(), "data", None) or []
        except Exception:  # noqa: BLE001 — a page read failure fails the reconcile honestly.
            return {"enqueued": enqueued, "enqueue_failed": failed, "reconcile_failed": 1}
        if not batch:
            break
        for doc in batch:
            did = str(doc.get("id"))
            if did in have_job:
                continue
            try:
                supabase.rpc("ca_enqueue_generation_job", {"p_document_id": did}).execute()
                enqueued += 1
            except Exception:  # noqa: BLE001 — surface, don't swallow.
                failed += 1
        if len(batch) < page_size:
            break
        cursor = batch[-1].get("id")
    return {"enqueued": enqueued, "enqueue_failed": failed, "reconcile_failed": 0}


def run_ingest_pass(
    supabase: Any,
    *,
    now: datetime | None = None,
    fetch: Callable[..., Any] = fetcher.fetch,
) -> dict[str, Any]:
    """One ``ca:ingest`` pass: crawl EVERY active source that is due, then durably enqueue
    a generation job for every snapshotted document lacking one.

    Honest classification: a source-query failure or any per-source / enqueue error yields
    ``status='failed'`` (partial or total) so the scheduler records ``ok=False`` instead of
    a silent all-zero success. Per-source exceptions are isolated so one bad source can't
    abort the pass."""
    now = now or datetime.now(timezone.utc)
    now_iso = now.isoformat()
    counts: dict[str, Any] = {
        "checked": 0, "snapshotted": 0, "duplicate": 0, "not_modified": 0,
        "error": 0, "deprioritised": 0, "skipped": 0, "enqueued": 0,
        "enqueue_failed": 0, "source_query_failed": 0, "status": "ok",
    }

    try:
        for source in _iter_active_sources(supabase):
            try:
                if not _is_due(source, now):
                    continue
                counts["checked"] += 1
                result = ingest_source(supabase, source, fetch=fetch, now_iso=now_iso)
                status = result.get("status") or "error"
                counts[status] = counts.get(status, 0) + 1
            except Exception:  # noqa: BLE001 — isolate one source; later sources still run.
                logger.exception("ca:ingest source failed id=%s", source.get("id"))
                counts["error"] += 1
    except Exception:  # noqa: BLE001 — the source query itself failed (DB outage).
        logger.exception("ca:ingest source query failed")
        counts["source_query_failed"] = 1

    recon = _reconcile_pending_generation(supabase)
    counts["enqueued"] += recon["enqueued"]
    counts["enqueue_failed"] += recon["enqueue_failed"]

    if counts["source_query_failed"] or recon.get("reconcile_failed"):
        counts["status"] = "failed"
    elif counts["error"] or counts["enqueue_failed"]:
        counts["status"] = "partial"
    return counts
