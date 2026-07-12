"""Current-affairs source adapters + document pre-filter.

The source rows live in ``current_affairs_sources`` (migration 241). This module
holds the thin adapter layer on top of them: how to resolve the fetch URL for a
source's ``adapter_type``, the per-publisher defaults for the first two seeded
primary-official sources (PIB, RBI), and a deterministic pre-filter that records
a machine-readable reason for documents that must not enter the extraction queue
(pipeline §2, §4).

No LLM here — the pre-filter is purely structural (empty/too-short/duplicate
bodies). Semantic "routine/ceremonial" filtering is an LLM concern deferred to
GQR-G3.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Minimum stable body length below which a snapshot cannot carry an examinable
# claim — deprioritised before any (future) extraction call. Deliberately
# conservative: this only catches near-empty fetches, not thin-but-real notices.
_MIN_EXAMINABLE_CHARS = 120

# ADR 0007: a discovery_only source may never be the SOLE evidence for a promoted
# question. Surfaced here so callers can gate evidence without re-deriving it.
DISCOVERY_ONLY = "discovery_only"


@dataclass(frozen=True)
class AdapterDefaults:
    """Per-publisher defaults applied to a fetched document when the source row
    does not override them. Keeps PIB/RBI document typing consistent without
    hard-coding it in the ingest loop."""

    document_type: str
    category: str


# Keyed by the ``adapter_config.publisher`` marker seeded in migration 241.
_ADAPTERS: dict[str, AdapterDefaults] = {
    "PIB": AdapterDefaults(document_type="press_release", category="national"),
    "RBI": AdapterDefaults(document_type="press_release", category="economy"),
}


def adapter_defaults(source: dict[str, Any]) -> AdapterDefaults | None:
    """Return the publisher defaults for ``source`` or ``None`` when unknown.

    Unknown publishers are not an error — the source's own ``default_category``
    still applies; they simply have no built-in document typing yet.
    """
    publisher = (source.get("adapter_config") or {}).get("publisher")
    if not publisher:
        return None
    return _ADAPTERS.get(str(publisher))


def resolve_fetch_url(source: dict[str, Any]) -> str | None:
    """Resolve the URL to fetch for a source based on its ``adapter_type``.

    RSS/API/PDF read their dedicated column; html/sitemap fall back to
    ``crawl_url`` then ``official_url``. Returns ``None`` when no usable URL is
    configured — the caller records that as a source-health error rather than
    fetching an empty string.
    """
    adapter = (source.get("adapter_type") or "html").lower()
    if adapter == "rss":
        return source.get("rss_url") or source.get("crawl_url") or source.get("official_url")
    if adapter == "api":
        return source.get("api_url") or source.get("crawl_url")
    if adapter == "pdf":
        return source.get("pdf_bulletin_url") or source.get("crawl_url")
    # html / sitemap
    return source.get("crawl_url") or source.get("official_url")


def prefilter_document(*, raw_text: str | None) -> tuple[bool, str | None]:
    """Structural pre-filter: decide whether a fetched body is worth snapshotting
    as an examinable document.

    Returns ``(accept, reason)``. ``accept=True`` → snapshot normally;
    ``accept=False`` → the caller stores the snapshot with a non-``snapshotted``
    ingestion_status and the machine-readable ``reason`` (pipeline §4 requires
    every exclusion to record a reason). Content dedup is handled separately by
    the ingest content-hash check, not here.
    """
    text = (raw_text or "").strip()
    if not text:
        return False, "empty_body"
    if len(text) < _MIN_EXAMINABLE_CHARS:
        return False, "below_min_examinable_length"
    return True, None
