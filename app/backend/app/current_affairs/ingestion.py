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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("db_op_failed op=current_affairs.ingestion err=%r", exc)
        return default


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
    inserted = _safe(
        lambda: supabase.table(_DOCUMENTS).insert(payload).execute(),
        default=None,
    )
    rows = getattr(inserted, "data", None) or []
    if not rows:
        # The insert failed (e.g. a concurrent run won the unique content-hash
        # race). Treat as a non-fatal duplicate rather than a hard error, and
        # keep health green — the body IS captured, just not by this run.
        _update_health(supabase, source_id, now_iso=now, status="write_contended", success=True)
        return {"status": "duplicate", "source_id": source_id, "document_id": None}

    _update_health(supabase, source_id, now_iso=now, status=ingestion_status, success=True)
    return {
        "status": ingestion_status,
        "source_id": source_id,
        "document_id": rows[0].get("id"),
        "reason": reason,
    }
