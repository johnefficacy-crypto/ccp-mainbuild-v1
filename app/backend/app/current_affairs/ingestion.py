"""Current-affairs ingestion primitive (GQR-G2).

``ingest_source`` runs one source through: resolve URL → conditional fetch
(reusing ``app.scraping.fetcher``) → 304 short-circuit → content-hash dedup →
immutable document snapshot → source-health update. It is the unit the
``ca:ingest`` scheduler job (pipeline §9) calls per source; keeping it a pure
``(supabase, source) -> result`` function makes it testable without the
scheduler.

RSS sources take the ITEM-SPLIT path (CA-RSS-01): the feed body is a listing, not
evidence. One ``current_affairs_documents`` row is written per feed ENTRY, with
the entry's own title / link / publication date and the readable text of the
entry's own page. Snapshotting the whole feed body produced title-less 54k–253k
char XML rows that re-snapshot on every feed shift and carry no single examinable
claim; those legacy rows are deprioritised by migration 294.

Every other adapter (html / api / pdf / sitemap) keeps the original
whole-body snapshot: their fetch target already IS one document.

No LLM, no extraction, no learner surface — this only lands evidence snapshots
and keeps source health current.
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from app.scraping import fetcher
from app.current_affairs import sources as ca_sources

logger = logging.getLogger("career_copilot.current_affairs.ingestion")

_SOURCES = "current_affairs_sources"
_DOCUMENTS = "current_affairs_documents"


_DEFAULT_INTERVAL_HOURS = 24

# Per-pass cap on NEW feed items fetched for one source. A feed that suddenly
# lists 400 entries must not turn one ingest pass into 400 page fetches; the
# remainder is picked up next pass (entries are deduped on their canonical link,
# so nothing is lost). Overridable per source via
# ``crawl_schedule.max_items_per_pass``.
_DEFAULT_MAX_ITEMS_PER_PASS = 30

# Bound on one ``IN (...)`` link-lookup so a long feed cannot build a giant query.
_LINK_LOOKUP_CHUNK = 100

# The feed summary is kept on the document as context, not as evidence — the item
# page body is the evidence. Truncated so a verbose feed cannot bloat metadata.
_FEED_SUMMARY_CHARS = 2000

# Written to the source when a pass leaves work behind (capped remainder or a
# failed item page): the next pass must re-read the feed rather than 304.
_CLEARED_FEED_VALIDATORS = {"feed_etag": None, "feed_last_modified": None}

# Below this many readable HTML characters an item page is assumed to be chrome
# (breadcrumb + nav) wrapping an embedded document, so the embedded PDF is tried.
# SEBI's live pages measured 290–600 chars of pure chrome.
_DEFAULT_PDF_FALLBACK_CHARS = 800

# Hard floor on the FINAL body. Below this there is no examinable claim, and
# storing the row would burn the item's canonical-link slot in the unique index
# so a later, better extraction could never replace it. Instead: no row, per-item
# error, retried next pass.
_DEFAULT_MIN_BODY_CHARS = 400

# Cap on an embedded PDF. Over this the item records an error rather than
# spending minutes of pypdf on a scanned bulk annexure.
_DEFAULT_MAX_PDF_BYTES = 10 * 1024 * 1024


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
    extra: dict[str, Any] | None = None,
) -> None:
    """Best-effort source-health write. A success resets the failure streak; a
    failure increments it. Never raises — health is operational, not correctness
    critical, and must not sink an otherwise-successful ingest.

    ``extra`` carries source-level columns the ingest owns alongside health —
    today the RSS feed validators (``feed_etag`` / ``feed_last_modified``), which
    cannot live on a document row any more now that one feed fetch produces many
    item rows."""
    patch: dict[str, Any] = {
        "last_fetch_at": now_iso,
        "last_status": status,
        "last_error": None if success else error,
        "consecutive_failures": 0 if success else prev_failures + 1,
        "updated_at": now_iso,
    }
    if success:
        patch["last_success_at"] = now_iso
    if extra:
        patch.update(extra)
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
      - ``error``         — fetch failed (network / HTTP / empty body / empty feed).
      - ``duplicate``     — nothing new: content hash (or, for RSS, every item
                            link) already snapshotted for this source.
      - ``snapshotted``   — at least one new immutable document row was written.
      - ``deprioritised`` — fetched but pre-filtered out (reason recorded).

    RSS sources take the item-split path (one row per feed ENTRY); every other
    adapter snapshots the fetched body as one document. Source health is updated
    on every terminal path. Document rows are immutable; changed content on a
    later run creates a NEW row rather than mutating an existing one.
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

    adapter = (source.get("adapter_type") or "html").lower()
    # Per-source UA override (adapter_config.user_agent). Absent → the default bot
    # UA, so the recruitment scraper's identity is untouched.
    user_agent = ca_sources.user_agent_of(source)

    if adapter == "rss":
        return _ingest_rss_items(
            supabase, source, url=url, fetch=fetch, now=now, user_agent=user_agent,
        )
    return _ingest_whole_body(
        supabase, source, url=url, adapter=adapter, fetch=fetch, now=now,
        user_agent=user_agent,
    )


def _ingest_whole_body(
    supabase: Any,
    source: dict[str, Any],
    *,
    url: str,
    adapter: str,
    fetch: Callable[..., Any],
    now: str,
    user_agent: str | None,
) -> dict[str, Any]:
    """Snapshot the fetched body as ONE document (html / api / pdf / sitemap).

    Unchanged GQR-G2 behaviour: conditional fetch off the source's most recent
    snapshot, 304 short-circuit, content-hash dedup, immutable insert.
    """
    source_id = source.get("id")
    prev = _latest_document(supabase, source_id) or {}
    result = fetch(
        url,
        adapter_type=adapter,
        if_none_match=prev.get("etag"),
        if_modified_since=prev.get("last_modified"),
        user_agent=user_agent,
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
        dupe_id = _document_id_by_content_hash(supabase, source_id, content_hash)
        if dupe_id is not None:
            _update_health(supabase, source_id, now_iso=now, status="duplicate", success=True)
            return {"status": "duplicate", "source_id": source_id, "document_id": dupe_id}

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
    written, err = _insert_document(supabase, payload)
    if err == "duplicate":
        # A concurrent run won the unique content-hash race — the body IS captured,
        # just not by this run. Non-fatal duplicate; health stays green.
        _update_health(supabase, source_id, now_iso=now, status="write_contended", success=True)
        return {"status": "duplicate", "source_id": source_id, "document_id": None}
    if err:
        _update_health(
            supabase, source_id, now_iso=now, status="error", success=False,
            error=err[:200], prev_failures=prev_failures,
        )
        return {
            "status": "error",
            "reason": "empty_insert" if err == "empty_insert" else "write_failed",
            "source_id": source_id,
        }

    _update_health(supabase, source_id, now_iso=now, status=ingestion_status, success=True)
    return {
        "status": ingestion_status,
        "source_id": source_id,
        "document_id": (written or {}).get("id"),
        "reason": reason,
    }


def _document_id_by_content_hash(supabase: Any, source_id: Any, content_hash: str) -> Any:
    """Existing document id for this (source, content_hash), or ``None``."""
    existing = _safe(
        lambda: supabase.table(_DOCUMENTS)
        .select("id")
        .eq("source_id", source_id)
        .eq("content_hash", content_hash)
        .limit(1)
        .execute(),
        default=None,
    )
    rows = getattr(existing, "data", None) or []
    return rows[0].get("id") if rows else None


def _insert_document(supabase: Any, payload: dict[str, Any]) -> tuple[dict | None, str | None]:
    """Insert one immutable document row.

    Returns ``(row, None)`` on success, ``(None, "duplicate")`` for a benign unique
    conflict (content-hash or item-link race won by a concurrent run), and
    ``(None, "<error>")`` for a genuine write failure. Classification matters: a
    fail-open "everything is a duplicate" would hide real infrastructure errors.
    """
    try:
        inserted = supabase.table(_DOCUMENTS).insert(payload).execute()
    except Exception as exc:  # noqa: BLE001 — classify: unique race vs real write failure.
        if _is_unique_violation(exc):
            return None, "duplicate"
        return None, f"write_failed: {exc}"
    rows = getattr(inserted, "data", None) or []
    if not rows:
        return None, "empty_insert"
    return rows[0], None


def _max_items_per_pass(source: dict[str, Any]) -> int:
    """Per-pass new-item cap from ``crawl_schedule.max_items_per_pass``.

    ``crawl_schedule`` is unconstrained JSONB, so a non-object or non-numeric value
    falls back to the default rather than raising."""
    sched = source.get("crawl_schedule")
    if not isinstance(sched, dict):
        return _DEFAULT_MAX_ITEMS_PER_PASS
    try:
        cap = int(sched.get("max_items_per_pass") or _DEFAULT_MAX_ITEMS_PER_PASS)
    except (TypeError, ValueError):
        return _DEFAULT_MAX_ITEMS_PER_PASS
    return cap if cap > 0 else _DEFAULT_MAX_ITEMS_PER_PASS


_LOOKUP_FAILED = object()


def _known_item_links(supabase: Any, source_id: Any, links: list[str]) -> Any:
    """Canonical item links this source has already snapshotted.

    Queried in bounded chunks so a long feed cannot build an unbounded ``IN`` list.
    Returns ``_LOOKUP_FAILED`` when the read fails: the caller must classify that as
    a source error, not as "nothing new". Guessing either way would be wrong —
    treating the links as known hides a DB outage behind a green pass, treating them
    as new re-fetches every item page."""
    known: set[str] = set()
    for start in range(0, len(links), _LINK_LOOKUP_CHUNK):
        chunk = links[start:start + _LINK_LOOKUP_CHUNK]
        rows = _safe(
            lambda c=chunk: supabase.table(_DOCUMENTS)
            .select("canonical_item_url")
            .eq("source_id", source_id)
            .in_("canonical_item_url", c)
            .execute(),
            default=None,
        )
        if rows is None:
            return _LOOKUP_FAILED
        for row in (getattr(rows, "data", None) or []):
            value = row.get("canonical_item_url")
            if value:
                known.add(str(value))
    return known


def _entry_digest(canonical: str, title: str, summary: str) -> str:
    """Stable content hash for an item we never fetched a page for (deny-listed).

    Derived from the feed entry itself so the row still carries a non-null
    content_hash and re-reading the same entry cannot produce a second snapshot."""
    return hashlib.sha256("\n".join((canonical, title or "", summary or "")).encode("utf-8")).hexdigest()


def _schedule_int(source: dict[str, Any], key: str, default: int) -> int:
    """Read an integer knob from ``crawl_schedule``, falling back to ``default``.

    ``crawl_schedule`` is unconstrained JSONB, so a non-object or non-numeric
    value must not raise. A non-positive value means "use the default" rather
    than "disable", because every one of these knobs is a safety floor/ceiling.
    """
    sched = source.get("crawl_schedule")
    if not isinstance(sched, dict):
        return default
    try:
        value = int(sched.get(key) or default)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _page_html(page: Any) -> str:
    """Raw HTML of a fetched page.

    ``FetchResult.text`` is already reduced to plain text, which is exactly what
    the readable-body check wants but useless for finding an embedded PDF. The
    untouched bytes are on ``raw_bytes``; decode them with the response charset
    when it names one, and never raise on a mis-declared encoding.
    """
    raw = getattr(page, "raw_bytes", None)
    if not raw:
        return ""
    charset = "utf-8"
    content_type = (getattr(page, "content_type", None) or "").lower()
    if "charset=" in content_type:
        charset = content_type.split("charset=", 1)[1].split(";")[0].strip() or "utf-8"
    try:
        return raw.decode(charset, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return raw.decode("utf-8", errors="replace")


def _resolve_item_body(
    page: Any,
    *,
    title: str | None,
    link: str,
    fetch: Callable[..., Any],
    user_agent: str | None,
    min_chars: int,
    pdf_threshold: int,
    max_pdf_bytes: int,
) -> tuple[str | None, dict[str, Any], str | None]:
    """Decide what this item's ``raw_text`` is.

    Returns ``(body, metadata, error)``. ``body`` is ``None`` when the item has no
    usable body — the caller then records ``error`` per item and writes NO row.

    The HTML text is used as-is when it is substantial. When it is thin, OR the
    page embeds/links a PDF for this item, the PDF is fetched and its extracted
    text becomes the body (prefixed with the page title, which the PDF itself
    often omits). Extraction reuses ``fetcher.fetch_pdf`` → ``parse_pdf_bytes``,
    the same pypdf path ``doc:text_extract`` runs on library uploads.

    A PDF that cannot be fetched or parsed is NOT automatically fatal: when the
    HTML body alone clears ``min_chars`` it is kept and the PDF error is recorded
    alongside it. Only when neither source yields a usable body does the item
    fail.
    """
    html_text = (getattr(page, "text", None) or "").strip()
    page_url = getattr(page, "final_url", None) or link
    pdf_url = ca_sources.embedded_pdf_url(_page_html(page), page_url=page_url)

    # The PDF is only worth fetching when the page HAS one and its readable HTML
    # is too thin to be the document. A rich HTML body plus a linked PDF means the
    # HTML already IS the document and the PDF is an annexure.
    if not (pdf_url and len(html_text) < pdf_threshold):
        if len(html_text) >= min_chars:
            return html_text, {"body_source": "html", "extracted_chars": len(html_text)}, None
        return None, {}, "thin_body"

    pdf = fetch(
        pdf_url, adapter_type="pdf", user_agent=user_agent, max_bytes=max_pdf_bytes,
    )
    if not getattr(pdf, "ok", False):
        pdf_error = str(getattr(pdf, "error", None) or "pdf_fetch_failed")
        if len(html_text) >= min_chars:
            return html_text, {
                "body_source": "html",
                "extracted_chars": len(html_text),
                "pdf_url": pdf_url,
                "pdf_error": pdf_error,
            }, None
        return None, {}, pdf_error

    pdf_text = (getattr(pdf, "text", None) or "").strip()
    body = f"{title}\n\n{pdf_text}".strip() if title else pdf_text
    if len(body) < min_chars:
        if len(html_text) >= min_chars:
            return html_text, {
                "body_source": "html",
                "extracted_chars": len(html_text),
                "pdf_url": pdf_url,
                "pdf_error": "thin_pdf_text",
            }, None
        return None, {}, "thin_body"

    return body, {
        "body_source": "pdf",
        "pdf_url": pdf_url,
        "extracted_chars": len(body),
        # Popped by the caller: dedup must key on the body actually stored.
        "body_content_hash": getattr(pdf, "content_hash", None),
    }, None


def _ingest_rss_items(
    supabase: Any,
    source: dict[str, Any],
    *,
    url: str,
    fetch: Callable[..., Any],
    now: str,
    user_agent: str | None,
) -> dict[str, Any]:
    """Item-split ingest for an RSS/Atom source (CA-RSS-01).

    Fetch the feed once (conditional on the source's stored feed validators), then
    write ONE document per NEW entry, carrying that entry's own title, link,
    publication date and the readable text of its own page. The feed body itself is
    never snapshotted — it is a listing, not evidence.
    """
    source_id = source.get("id")
    prev_failures = int(source.get("consecutive_failures") or 0)
    publisher = ca_sources.publisher_of(source)
    defaults = ca_sources.adapter_defaults(source)
    document_type = defaults.document_type if defaults else None

    result = fetch(
        url,
        adapter_type="rss",
        if_none_match=source.get("feed_etag"),
        if_modified_since=source.get("feed_last_modified"),
        user_agent=user_agent,
    )

    feed_validators = {
        "feed_etag": getattr(result, "etag", None) or source.get("feed_etag"),
        "feed_last_modified": getattr(result, "last_modified", None) or source.get("feed_last_modified"),
    }

    # Feed-level 304 short-circuit: the feed has not shifted, so no item can be new.
    if getattr(result, "status_code", None) == 304 or getattr(result, "error", None) == "not_modified":
        _update_health(
            supabase, source_id, now_iso=now, status="not_modified", success=True,
            extra=feed_validators,
        )
        return {"status": "not_modified", "source_id": source_id}

    if not getattr(result, "ok", False):
        err = getattr(result, "error", None) or "fetch_failed"
        _update_health(
            supabase, source_id, now_iso=now, status="error", success=False, error=err,
            prev_failures=prev_failures,
        )
        return {"status": "error", "reason": err, "source_id": source_id}

    entries = fetcher.parse_rss_feed(getattr(result, "text", None))
    if not entries:
        # Malformed XML parses to [] — indistinguishable from a genuinely empty
        # feed, and both mean this source produced nothing. Red the health streak.
        _update_health(
            supabase, source_id, now_iso=now, status="error", success=False,
            error="empty_feed", prev_failures=prev_failures,
        )
        return {"status": "error", "reason": "empty_feed", "source_id": source_id}

    # Canonical link is the item identity. Entries without a usable link cannot be
    # deduped or fetched, so they are counted and skipped.
    candidates: list[tuple[str, Any]] = []
    unusable = 0
    seen_in_feed: set[str] = set()
    for entry in entries:
        canonical = ca_sources.canonical_item_link(getattr(entry, "link", None))
        if not canonical:
            unusable += 1
            continue
        if canonical in seen_in_feed:  # the same item listed twice in one feed
            continue
        seen_in_feed.add(canonical)
        candidates.append((canonical, entry))

    if not candidates:
        # Entries parsed but none carried a usable link — a feed-shape problem, not
        # a healthy empty pass. Surface it rather than reporting a quiet no-op.
        _update_health(
            supabase, source_id, now_iso=now, status="error", success=False,
            error="no_usable_item_links", prev_failures=prev_failures,
        )
        return {
            "status": "error", "reason": "no_usable_item_links",
            "source_id": source_id, "items_seen": len(entries),
            "items_unusable": unusable,
        }

    known = _known_item_links(supabase, source_id, [c for c, _ in candidates])
    if known is _LOOKUP_FAILED:
        _update_health(
            supabase, source_id, now_iso=now, status="error", success=False,
            error="item_link_lookup_failed", prev_failures=prev_failures,
        )
        return {"status": "error", "reason": "item_link_lookup_failed", "source_id": source_id}
    fresh = [(c, e) for c, e in candidates if c not in known]
    cap = _max_items_per_pass(source)
    new_items = fresh[:cap]

    counts = {
        "items_seen": len(entries),
        "items_known": len(candidates) - len(fresh),
        "items_unusable": unusable,
        "items_new": len(new_items),
        "items_snapshotted": 0,
        "items_deprioritised": 0,
        "items_duplicate": 0,
        "items_capped": len(fresh) > cap,
    }
    item_errors: list[dict[str, str]] = []
    document_ids: list[Any] = []
    min_body_chars = _schedule_int(source, "min_body_chars", _DEFAULT_MIN_BODY_CHARS)
    pdf_threshold = _schedule_int(source, "pdf_fallback_below_chars", _DEFAULT_PDF_FALLBACK_CHARS)
    max_pdf_bytes = _schedule_int(source, "max_pdf_bytes", _DEFAULT_MAX_PDF_BYTES)

    for canonical, entry in new_items:
        title = (getattr(entry, "title", "") or "").strip() or None
        summary = (getattr(entry, "summary", "") or "").strip()
        raw_pub_date = (getattr(entry, "published", None) or "").strip() or None
        published_at = ca_sources.parse_published_at(raw_pub_date)
        link = (getattr(entry, "link", "") or "").strip() or canonical

        # The raw feed value is kept verbatim ALWAYS, parsed or not: when a
        # publisher changes its date shape, the stored string is what lets the
        # parser be extended and the rows re-derived without re-crawling.
        metadata: dict[str, Any] = {"publisher": publisher, "item_link": link}
        if raw_pub_date:
            metadata["raw_pub_date"] = raw_pub_date
        if summary:
            metadata["feed_summary"] = summary[:_FEED_SUMMARY_CHARS]

        # Both structural filters are decidable from the feed entry alone, so they
        # run BEFORE paying for the item page fetch. Pipeline §4: the row is still
        # written with a machine-readable reason; it is never silently dropped.
        # Path first — it is the coarser, publisher-section-level judgement.
        excluded = ca_sources.path_excluded_reason(publisher, canonical)
        denied = None if excluded else ca_sources.denylisted_title(publisher, title)
        skip_reason = excluded or (
            f"{ca_sources.DENYLIST_REASON_PREFIX}{denied}" if denied else None
        )
        if skip_reason:
            payload = {
                "source_id": source_id,
                "source_url": link,
                "canonical_item_url": canonical,
                "final_url": None,
                "title": title,
                "document_type": document_type,
                "published_at": published_at,
                "fetched_at": now,
                "content_hash": _entry_digest(canonical, title or "", summary),
                "etag": None,
                "last_modified": None,
                "raw_text": summary or None,
                "metadata": {**metadata, "prefilter_reason": skip_reason},
                "ingestion_status": "deprioritised",
            }
            _record_item(supabase, payload, counts, item_errors, document_ids, link)
            continue

        page = fetch(link, adapter_type="html", user_agent=user_agent)
        if not getattr(page, "ok", False):
            # One unreachable item page must not sink the source. No row is written,
            # so the item stays NEW and the next pass retries it.
            err = getattr(page, "error", None) or "fetch_failed"
            item_errors.append({"link": link, "error": str(err)})
            continue

        content_hash = getattr(page, "content_hash", None)
        if content_hash and _document_id_by_content_hash(supabase, source_id, content_hash) is not None:
            counts["items_duplicate"] += 1
            continue

        body, body_meta, body_error = _resolve_item_body(
            page, title=title, link=link, fetch=fetch, user_agent=user_agent,
            min_chars=min_body_chars, pdf_threshold=pdf_threshold,
            max_pdf_bytes=max_pdf_bytes,
        )
        if body is None:
            # No usable body: the item stays NEW so a later pass (or a fixed
            # extractor) can retry it, exactly like an item-page fetch failure.
            item_errors.append({"link": link, "error": body_error or "thin_body"})
            continue
        # Dedup must key on the body that was actually stored, not on the chrome
        # page that merely pointed at it.
        content_hash = body_meta.pop("body_content_hash", None) or content_hash

        accept, reason = ca_sources.prefilter_document(
            raw_text=body, title=title, publisher=publisher,
        )
        item_metadata = {
            **metadata,
            "content_type": getattr(page, "content_type", None),
            **body_meta,
        }
        if not accept and reason:
            item_metadata["prefilter_reason"] = reason

        payload = {
            "source_id": source_id,
            "source_url": link,
            "canonical_item_url": canonical,
            "final_url": getattr(page, "final_url", None),
            "title": title,
            "document_type": document_type,
            "published_at": published_at,
            "fetched_at": now,
            "content_hash": content_hash,
            "etag": getattr(page, "etag", None),
            "last_modified": getattr(page, "last_modified", None),
            "raw_text": body,
            "metadata": item_metadata,
            "ingestion_status": "snapshotted" if accept else "deprioritised",
        }
        _record_item(supabase, payload, counts, item_errors, document_ids, link)

    if counts["items_snapshotted"]:
        status = "snapshotted"
    elif counts["items_deprioritised"]:
        status = "deprioritised"
    elif item_errors and not counts["items_duplicate"]:
        status = "error"
    else:
        status = "duplicate"

    # Feed validators are stored ONLY when this pass fully drained the feed. If
    # items were capped or an item page failed, that work is still outstanding;
    # storing the validators would 304 the next pass and strand it forever.
    drained = not counts["items_capped"] and not item_errors and status != "error"
    _update_health(
        supabase, source_id, now_iso=now,
        status=status, success=status != "error",
        error="item_fetch_failed" if status == "error" else None,
        prev_failures=prev_failures,
        extra=feed_validators if drained else _CLEARED_FEED_VALIDATORS,
    )
    return {
        "status": status,
        "source_id": source_id,
        "document_id": document_ids[0] if document_ids else None,
        "document_ids": document_ids,
        "item_errors": item_errors,
        **counts,
    }


def _record_item(
    supabase: Any,
    payload: dict[str, Any],
    counts: dict[str, Any],
    item_errors: list[dict[str, str]],
    document_ids: list[Any],
    link: str,
) -> None:
    """Insert one item document and fold the outcome into the per-source counters."""
    row, err = _insert_document(supabase, payload)
    if err == "duplicate":
        counts["items_duplicate"] += 1
        return
    if err:
        item_errors.append({"link": link, "error": err[:200]})
        return
    document_ids.append((row or {}).get("id"))
    if payload["ingestion_status"] == "snapshotted":
        counts["items_snapshotted"] += 1
    else:
        counts["items_deprioritised"] += 1


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
        # Item-split totals across RSS sources (documents, not sources).
        "items_new": 0, "items_snapshotted": 0, "items_deprioritised": 0,
        "items_duplicate": 0, "item_errors": 0,
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
                for key in ("items_new", "items_snapshotted",
                            "items_deprioritised", "items_duplicate"):
                    counts[key] += int(result.get(key) or 0)
                counts["item_errors"] += len(result.get("item_errors") or [])
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
    elif counts["error"] or counts["enqueue_failed"] or counts["item_errors"]:
        counts["status"] = "partial"
    return counts
