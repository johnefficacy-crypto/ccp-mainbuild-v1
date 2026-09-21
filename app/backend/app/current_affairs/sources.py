"""Current-affairs source adapters + document pre-filter.

The source rows live in ``current_affairs_sources`` (migration 241). This module
holds the thin adapter layer on top of them: how to resolve the fetch URL for a
source's ``adapter_type``, the per-publisher defaults for the seeded
primary-official sources (PIB, RBI, SEBI), item-link canonicalisation +
published-date parsing for the RSS item-split ingest path, and a deterministic
pre-filter that records a machine-readable reason for documents that must not
enter the extraction queue (pipeline §2, §4).

No LLM here — the pre-filter is purely structural (empty/too-short bodies) plus a
per-publisher title deny-list of strictly administrative notices. Both are
deterministic string rules; semantic "routine/ceremonial" filtering remains an
LLM concern deferred to GQR-G3.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

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
    "SEBI": AdapterDefaults(document_type="press_release", category="economy"),
}


# Per-publisher title deny-list. These are purely administrative instruments —
# party-specific enforcement paperwork that carries no examinable general-awareness
# claim — so they are deprioritised BEFORE any page fetch cost or extraction call.
# Matching is case-insensitive substring on the feed entry title. Deterministic by
# design: no LLM, no heuristics scoring. Pipeline §4 requires the row still be
# snapshotted with a machine-readable reason, never silently dropped.
_TITLE_DENYLIST: dict[str, tuple[str, ...]] = {
    "SEBI": (
        "recovery certificate",
        "notice of attachment",
        "release order",
        "general remittance order",
        "adjudication order",
        "settlement order",
        "order for compliance",
    ),
}

DENYLIST_REASON_PREFIX = "publisher_denylist:"


def publisher_of(source: dict[str, Any]) -> str | None:
    """The ``adapter_config.publisher`` marker for a source, or ``None``."""
    publisher = (source.get("adapter_config") or {}).get("publisher")
    return str(publisher) if publisher else None


def user_agent_of(source: dict[str, Any]) -> str | None:
    """Per-source User-Agent override from ``adapter_config.user_agent``.

    ``None`` means "send the default bot UA" — the recruitment scraper's identity
    is never changed by a current-affairs source row. PIB needs an override because
    it 403s the bot UA (42 consecutive http_403 before this knob existed).
    """
    ua = (source.get("adapter_config") or {}).get("user_agent")
    ua = str(ua).strip() if ua else ""
    return ua or None


# Tracking parameters carry no identity — two links differing only by these are the
# same item. Kept deliberately short: an unknown query param may well be the item id.
_TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "mc_cid", "mc_eid",
})


def canonical_item_link(link: str | None) -> str | None:
    """Canonical dedup key for one feed item's link.

    Lowercases scheme/host, drops the fragment and known tracking params, strips a
    trailing slash on non-root paths, and normalises ``http`` → ``https`` (publishers
    flip these between feed refreshes and would otherwise re-snapshot every item).
    Returns ``None`` for an unusable link so the caller can skip the entry.
    """
    raw = (link or "").strip()
    if not raw:
        return None
    try:
        parts = urlsplit(raw)
    except ValueError:
        return None
    if not parts.netloc:
        return None
    scheme = "https" if parts.scheme in ("", "http", "https") else parts.scheme.lower()
    netloc = parts.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    query = "&".join(
        part for part in parts.query.split("&")
        if part and part.split("=", 1)[0].lower() not in _TRACKING_PARAMS
    )
    return urlunsplit((scheme, netloc, path, query, ""))


_ISO_TRAILING_Z = re.compile(r"[Zz]$")


def parse_published_at(value: str | None) -> str | None:
    """Parse a feed entry's publication date into an ISO-8601 UTC string.

    Accepts RFC 2822 (``<pubDate>`` in RSS 2.0) and ISO-8601 (``<published>`` /
    ``<updated>`` in Atom). Returns ``None`` when the value is missing or
    unparseable — the caller stores NULL. It must NEVER fall back to ``now()``:
    a fabricated publication date would silently corrupt the relevance window.
    """
    raw = (value or "").strip()
    if not raw:
        return None
    for parse in (_parse_rfc2822, _parse_iso8601):
        dt = parse(raw)
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat()
    return None


def _parse_rfc2822(raw: str) -> datetime | None:
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None


def _parse_iso8601(raw: str) -> datetime | None:
    try:
        return datetime.fromisoformat(_ISO_TRAILING_Z.sub("+00:00", raw))
    except ValueError:
        return None


def denylisted_title(publisher: str | None, title: str | None) -> str | None:
    """Return the matched deny-list pattern for ``title``, or ``None``.

    Case-insensitive substring match against the publisher's patterns. An unknown
    publisher has no deny-list and always returns ``None``.
    """
    if not publisher or not title:
        return None
    patterns = _TITLE_DENYLIST.get(str(publisher))
    if not patterns:
        return None
    lowered = title.lower()
    for pattern in patterns:
        if pattern in lowered:
            return pattern
    return None


def adapter_defaults(source: dict[str, Any]) -> AdapterDefaults | None:
    """Return the publisher defaults for ``source`` or ``None`` when unknown.

    Unknown publishers are not an error — the source's own ``default_category``
    still applies; they simply have no built-in document typing yet.
    """
    publisher = publisher_of(source)
    if not publisher:
        return None
    return _ADAPTERS.get(publisher)


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


def prefilter_document(
    *,
    raw_text: str | None,
    title: str | None = None,
    publisher: str | None = None,
) -> tuple[bool, str | None]:
    """Structural pre-filter: decide whether a fetched body is worth snapshotting
    as an examinable document.

    Returns ``(accept, reason)``. ``accept=True`` → snapshot normally;
    ``accept=False`` → the caller stores the snapshot with a non-``snapshotted``
    ingestion_status and the machine-readable ``reason`` (pipeline §4 requires
    every exclusion to record a reason). Content dedup is handled separately by
    the ingest content-hash check, not here.

    The publisher title deny-list is checked FIRST: it is the most specific signal
    and it is evaluable from the feed entry alone, so the caller can skip the item
    page fetch entirely for an administrative notice.
    """
    pattern = denylisted_title(publisher, title)
    if pattern:
        return False, f"{DENYLIST_REASON_PREFIX}{pattern}"

    text = (raw_text or "").strip()
    if not text:
        return False, "empty_body"
    if len(text) < _MIN_EXAMINABLE_CHARS:
        return False, "below_min_examinable_length"
    return True, None
