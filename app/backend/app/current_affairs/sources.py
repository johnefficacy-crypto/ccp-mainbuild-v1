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

import html as _html
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from urllib.parse import parse_qsl, urljoin, urlsplit, urlunsplit

# Minimum stable body length below which a snapshot cannot carry an examinable
# claim — deprioritised before any (future) extraction call. Deliberately
# conservative: this only catches near-empty fetches, not thin-but-real notices.
_MIN_EXAMINABLE_CHARS = 120

# ADR 0007: a discovery_only source may never be the SOLE evidence for a promoted
# question. Surfaced here so callers can gate evidence without re-deriving it.
DISCOVERY_ONLY = "discovery_only"

# Machine-readable reason for a body whose script does not match the source's
# declared ``default_language`` (CA-RSS-03). Also the reason for a PIB item whose
# English version could not be followed.
LANGUAGE_MISMATCH = "language_mismatch"


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
    "UNESCO_WHC": AdapterDefaults(document_type="news", category="culture"),
    "THE_HINDU": AdapterDefaults(document_type="news_article", category="general"),
}


# Per-publisher title deny-list. These are purely administrative instruments —
# party-specific enforcement paperwork that carries no examinable general-awareness
# claim — so they are deprioritised BEFORE any page fetch cost or extraction call.
# Matching is case-insensitive substring on the feed entry title. Deterministic by
# design: no LLM, no heuristics scoring. Pipeline §4 requires the row still be
# snapshotted with a machine-readable reason, never silently dropped.
# A pattern is either a single substring, or a tuple of substrings that must ALL
# appear (SEBI's RTI appeals are only identifiable by "Appeal No." AND "filed by"
# together — "appeal no." alone would swallow legitimate appellate-tribunal news).
_DenyPattern = "str | tuple[str, ...]"

_TITLE_DENYLIST: dict[str, tuple[Any, ...]] = {
    "SEBI": (
        "recovery certificate",
        "notice of attachment",
        "release order",
        "general remittance order",
        "general remittance advice",
        "adjudication order",
        "settlement order",
        "order for compliance",
        "order of aa under the rti act",
        ("appeal no.", "filed by"),
    ),
}

DENYLIST_REASON_PREFIX = "publisher_denylist:"

# Per-publisher URL-path allow-list, matched as a prefix on the canonical item
# link's PATH. Evaluated before the title deny-list and before any page fetch:
# an item outside these sections is structurally not general-awareness material,
# so paying for its page is waste.
#
# SEBI's feed is ~95% /enforcement/orders/... — party-specific RTI appeals and
# interim orders with no examinable claim. Only the editorial/regulatory sections
# below carry one.
#
# A publisher absent from this table has NO allow-list and is unfiltered by path
# (RBI and PIB: their page structure is unverified until their first item-split
# pass, and guessing a prefix would silently drop every item).
_PATH_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "SEBI": (
        "/media-and-notifications/press-releases/",
        "/legal/circulars/",
        "/legal/master-circulars/",
        "/legal/regulations/",
        "/reports-and-statistics/reports/",
    ),
}

PATH_EXCLUDED_REASON_PREFIX = "publisher_path_excluded:"


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


# India has no DST, so a fixed +05:30 is exactly correct year-round and needs no
# tzdata in the container. Naive feed dates are Indian-publisher local time.
IST = timezone(timedelta(hours=5, minutes=30), "IST")

_ISO_TRAILING_Z = re.compile(r"[Zz]$")

# A trailing timezone token, stripped before the strptime attempts so one format
# list covers "21 Sep, 2026", "21 Sep, 2026 IST" and "21 Sep, 2026 +0530".
# The offset branch REQUIRES leading whitespace: without it, "21-09-2026" ends in
# something that reads exactly like a "-2026" UTC offset and the year gets eaten.
_TZ_SUFFIX = re.compile(
    r"(?:\s*\((?P<paren>[A-Z]{2,5})\)"
    r"|\s*\b(?P<name>IST|UTC|GMT)\b"
    r"|\s+(?P<offset>[+-]\d{2}:?\d{2}))\s*$"
)

_NAMED_ZONES = {"IST": IST, "UTC": timezone.utc, "GMT": timezone.utc}

# Indian government/regulator sites publish dates in a handful of shapes. Ordered
# most-specific first; each is tried with and without a time component.
_DATE_FORMATS: tuple[str, ...] = (
    "%d %b, %Y", "%d %b %Y", "%d %B, %Y", "%d %B %Y",
    "%b %d, %Y", "%b %d %Y", "%B %d, %Y", "%B %d %Y",
    "%d-%b-%Y", "%d-%B-%Y",
    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y",
)
_TIME_SUFFIXES: tuple[str, ...] = ("", " %H:%M", " %H:%M:%S", " %I:%M %p", " %I:%M:%S %p")

# "Sept" is not a %b token; normalise it before parsing rather than adding a
# parallel format list.
_SEPT = re.compile(r"\bSept\b", re.IGNORECASE)


def parse_published_at(value: str | None) -> str | None:
    """Parse a feed entry's publication date into an ISO-8601 UTC string.

    Accepts RFC 2822 (``<pubDate>`` in RSS 2.0), ISO-8601 (Atom
    ``<published>``/``<updated>``), and the day/month-name shapes Indian
    publishers use (``21 Sep, 2026``, ``Sep 21, 2026``, with or without a time,
    with or without a trailing ``IST`` / ``+0530``).

    A value carrying no timezone is read as **Asia/Kolkata**, not UTC: every
    source in scope is an Indian publisher, and assuming UTC silently back-dated
    each item by 5.5 hours.

    Returns ``None`` when the value is missing or unparseable — the caller stores
    NULL and keeps the raw string in ``metadata.raw_pub_date``. It must NEVER
    fall back to ``now()``: a fabricated publication date would corrupt the
    relevance window.
    """
    raw = (value or "").strip()
    if not raw:
        return None
    dt = _parse_rfc2822(raw) or _parse_iso8601(raw) or _parse_common_formats(raw)
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(timezone.utc).isoformat()


# ``parsedate_to_datetime`` is lenient to a fault: "Sep 21, 2026 02:30 PM" comes
# back as 02:30, silently dropping the PM. Only hand it input that actually has
# the RFC 2822 shape — optional day name, then DAY MONTH YEAR.
_RFC2822_SHAPE = re.compile(r"^(?:[A-Za-z]{3,9},\s*)?\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b")


def _parse_rfc2822(raw: str) -> datetime | None:
    if not _RFC2822_SHAPE.match(raw):
        return None
    try:
        return parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None


def _parse_iso8601(raw: str) -> datetime | None:
    try:
        return datetime.fromisoformat(_ISO_TRAILING_Z.sub("+00:00", raw))
    except ValueError:
        return None


def _parse_common_formats(raw: str) -> datetime | None:
    """strptime sweep over the Indian-site date shapes, timezone token first."""
    text = _SEPT.sub("Sep", raw).strip()
    tzinfo: timezone | None = None
    match = _TZ_SUFFIX.search(text)
    if match:
        token = match.group("name") or match.group("paren")
        offset = match.group("offset")
        if token and token.upper() in _NAMED_ZONES:
            tzinfo = _NAMED_ZONES[token.upper()]
        elif offset:
            tzinfo = _parse_offset(offset)
        elif token:
            # An unknown parenthesised zone: drop the token, keep the date, and
            # let the IST default apply rather than failing the whole parse.
            tzinfo = None
        text = text[: match.start()].strip()

    # Normalise separators a publisher may vary on ("21 Sep,2026", double spaces).
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s{2,}", " ", text).strip()

    for fmt in _DATE_FORMATS:
        for suffix in _TIME_SUFFIXES:
            try:
                parsed = datetime.strptime(text, fmt + suffix)
            except ValueError:
                continue
            return parsed.replace(tzinfo=tzinfo) if tzinfo else parsed
    return None


def _parse_offset(offset: str) -> timezone | None:
    cleaned = offset.replace(":", "")
    try:
        sign = -1 if cleaned[0] == "-" else 1
        hours, minutes = int(cleaned[1:3]), int(cleaned[3:5])
    except (IndexError, ValueError):
        return None
    return timezone(sign * timedelta(hours=hours, minutes=minutes))


def denylisted_title(publisher: str | None, title: str | None) -> str | None:
    """Return the matched deny-list pattern for ``title``, or ``None``.

    Case-insensitive substring match against the publisher's patterns. A tuple
    pattern requires EVERY substring to be present and reports itself joined by
    ``+`` so the recorded reason stays machine-readable. An unknown publisher has
    no deny-list and always returns ``None``.
    """
    if not publisher or not title:
        return None
    patterns = _TITLE_DENYLIST.get(str(publisher))
    if not patterns:
        return None
    lowered = title.lower()
    for pattern in patterns:
        if isinstance(pattern, tuple):
            if all(part in lowered for part in pattern):
                return "+".join(pattern)
        elif pattern in lowered:
            return pattern
    return None


# ─── URL-path allow-list ────────────────────────────────────────────────────


def _path_of(canonical_url: str | None) -> str:
    try:
        return urlsplit(canonical_url or "").path or "/"
    except ValueError:
        return "/"


def path_section(canonical_url: str | None) -> str:
    """The first two path segments of ``canonical_url`` (``/a/b``).

    Used as the machine-readable tail of a ``publisher_path_excluded`` reason, so
    an operator can see WHICH section was dropped without re-deriving it from the
    URL. A shorter path reports what it has (``/a``, or ``/`` at the root).
    """
    segments = [seg for seg in _path_of(canonical_url).split("/") if seg][:2]
    return "/" + "/".join(segments) if segments else "/"


def path_allowed(publisher: str | None, canonical_url: str | None) -> bool:
    """Whether this item's path is inside the publisher's allow-list.

    A publisher with NO configured allow-list allows everything — absence of
    config must never be read as "deny all".
    """
    if not publisher:
        return True
    allowed = _PATH_ALLOWLIST.get(str(publisher))
    if not allowed:
        return True
    path = _path_of(canonical_url)
    return any(path.startswith(prefix) for prefix in allowed)


def path_excluded_reason(publisher: str | None, canonical_url: str | None) -> str | None:
    """The ``publisher_path_excluded:<section>`` reason, or ``None`` when allowed."""
    if path_allowed(publisher, canonical_url):
        return None
    return f"{PATH_EXCLUDED_REASON_PREFIX}{path_section(canonical_url)}"


# ─── Embedded-PDF discovery ─────────────────────────────────────────────────

# SEBI (and several other Indian regulators) render the item page as chrome plus
# an embedded PDF viewer: the readable HTML is a breadcrumb, and the document
# itself is the PDF. These are the shapes seen in the wild.
_PDF_EMBED_PATTERNS: tuple[re.Pattern[str], ...] = (
    # <iframe src="...pdf">, <embed src=...>, <object data=...>
    re.compile(r"""<(?:iframe|embed)\b[^>]*\bsrc\s*=\s*["']([^"']+)["']""", re.IGNORECASE),
    re.compile(r"""<object\b[^>]*\bdata\s*=\s*["']([^"']+)["']""", re.IGNORECASE),
    # <a href="...pdf"> — the primary document link on a viewer-less page.
    re.compile(r"""<a\b[^>]*\bhref\s*=\s*["']([^"']+)["']""", re.IGNORECASE),
)

# pdf.js and friends: /viewer.html?file=<url-encoded pdf>
_PDF_VIEWER_PARAM = re.compile(r"""[?&]file=([^"'&]+)""", re.IGNORECASE)


def _looks_like_pdf(candidate: str) -> bool:
    path = _path_of(candidate).lower()
    return path.endswith(".pdf")


def embedded_pdf_url(html: str | None, *, page_url: str) -> str | None:
    """The URL of the PDF this item page embeds or links, or ``None``.

    Checks, in order: a viewer ``?file=`` parameter, then ``iframe``/``embed``/
    ``object`` sources, then anchors — taking the FIRST candidate that resolves to
    a ``.pdf`` on the same host as the page. Same-host is deliberate: an
    off-host PDF is an unvetted third party, not this source's evidence.
    """
    if not html:
        return None
    page_host = (urlsplit(page_url).hostname or "").lower().removeprefix("www.")

    def _resolve(raw: str) -> str | None:
        candidate = _html_attr_unescape(raw).strip()
        if not candidate:
            return None
        absolute = urljoin(page_url, candidate)
        host = (urlsplit(absolute).hostname or "").lower().removeprefix("www.")
        if page_host and host and host != page_host:
            return None
        return absolute if _looks_like_pdf(absolute) else None

    for match in _PDF_VIEWER_PARAM.finditer(html):
        from urllib.parse import unquote
        resolved = _resolve(unquote(match.group(1)))
        if resolved:
            return resolved
    for pattern in _PDF_EMBED_PATTERNS:
        for match in pattern.finditer(html):
            resolved = _resolve(match.group(1))
            if resolved:
                return resolved
    return None


def _html_attr_unescape(value: str) -> str:
    return _html.unescape(value)


def is_discovery_only(source: dict[str, Any]) -> bool:
    """ADR 0007: a ``discovery_only`` source contributes a title + link + feed
    summary and nothing else — no item-page fetch, no article text, no job."""
    return (source.get("authority_level") or "") == DISCOVERY_ONLY


def page_html(page: Any) -> str:
    """Raw HTML of a fetched page.

    ``FetchResult.text`` is already reduced to plain text, which is exactly what
    the readable-body check wants but useless for structural selection (an
    embedded PDF, a language switcher, a release-text block). The untouched
    bytes are on ``raw_bytes``; decode them with the response charset when it
    names one, and never raise on a mis-declared encoding.
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


def _plain(fragment: str) -> str:
    """HTML fragment → collapsed plain text (the fetcher's own reduction)."""
    from app.scraping.fetcher import strip_html
    return strip_html(fragment or "")


# ─── Language guard ─────────────────────────────────────────────────────────

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_LATIN = re.compile(r"[A-Za-z]")

# Below this many script-bearing characters there is too little text to call a
# language; the guard abstains rather than guessing.
_MIN_SCRIPT_CHARS = 40


def detect_language(text: str | None) -> str | None:
    """Dominant script of ``text``: ``'hi'`` (Devanagari) or ``'en'`` (Latin).

    Deliberately a character-ratio count, not a language model: every source in
    scope declares English or Hindi, and the failure being guarded against is a
    Hindi body landing on an English source (PIB's only feed is Hindi). Returns
    ``None`` when there is too little text to decide.
    """
    body = text or ""
    dev = len(_DEVANAGARI.findall(body))
    lat = len(_LATIN.findall(body))
    if dev + lat < _MIN_SCRIPT_CHARS:
        return None
    return "hi" if dev >= lat else "en"


def language_mismatch(detected: str | None, expected: str | None) -> bool:
    """Whether a detected script contradicts the source's ``default_language``.

    Abstains (``False``) when nothing was detected or the source declares a
    language this detector cannot distinguish — absence of signal is never a
    mismatch.
    """
    want = (expected or "en").strip().lower()[:2]
    if detected is None or want not in ("en", "hi"):
        return False
    return detected != want


# ─── Page-date extraction ───────────────────────────────────────────────────

# Per-publisher "posted" line on the item page, matched against the page's
# whitespace-collapsed plain text. PIB English prints "Posted On:" then a newline
# and indentation, then "21 SEP 2026 7:44PM by PIB Delhi"; the Hindi page prints
# the same value after "प्रविष्टि तिथि:".
_PAGE_DATE_PATTERNS: dict[str, re.Pattern[str]] = {
    "PIB": re.compile(
        r"(?:Posted On|प्रविष्टि तिथि)\s*:\s*"
        r"(?P<value>\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\s+\d{1,2}:\d{2}\s*[AaPp][Mm])"
    ),
}

_PAGE_DATE_FORMATS = ("%d %b %Y %I:%M %p", "%d %B %Y %I:%M %p")


def page_published_at(publisher: str | None, page_text: str | None) -> tuple[str | None, str | None]:
    """Publication date printed on the item page, as ``(raw, iso_utc)``.

    Used only when the feed carried no parseable pubDate. The value is naive
    local time and is read as Asia/Kolkata. Returns ``(None, None)`` for a
    publisher with no known page-date shape or a page that lacks it, and
    ``(raw, None)`` for a matched but unparseable value — never ``now()``.
    """
    pattern = _PAGE_DATE_PATTERNS.get(str(publisher)) if publisher else None
    if pattern is None or not page_text:
        return None, None
    match = pattern.search(page_text)
    if not match:
        return None, None
    raw = re.sub(r"\s+", " ", match.group("value")).strip()
    # "7:44PM" → "7:44 PM" so %p has its own token. Deliberately NOT routed
    # through parse_published_at: its RFC 2822 branch accepts "21 SEP 2026 ..."
    # and email.utils drops the PM.
    normalised = re.sub(r"(\d)\s*([AaPp][Mm])$", r"\1 \2", raw).upper()
    for fmt in _PAGE_DATE_FORMATS:
        try:
            parsed = datetime.strptime(normalised, fmt)
        except ValueError:
            continue
        return raw, parsed.replace(tzinfo=IST).astimezone(timezone.utc).isoformat()
    return raw, None


# ─── PIB English-version follow ─────────────────────────────────────────────
#
# PIB's only non-empty feed (Regid=3) lists HINDI releases, and its items link the
# PressReleaseIframePage. The full PressReleasePage for the same PRID carries a
# language switcher; the anchor whose visible text is "English" links the English
# release, which has a DIFFERENT PRID with no arithmetic relation to the Hindi
# one. The page holds several PRIDs (itself, its lang=2 self-link, other
# languages, related releases), so the English one is selected by anchor text
# only — never by position.

LANGUAGE_FOLLOW_PUBLISHERS = frozenset({"PIB"})

_PIB_BASE = "https://pib.gov.in/PressReleasePage.aspx"
_ANCHOR = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<inner>.*?)</a\s*>", re.IGNORECASE | re.DOTALL)
_HREF = re.compile(r"""\bhref\s*=\s*(["'])(?P<href>.*?)\1""", re.IGNORECASE | re.DOTALL)
_PIB_TITLE = re.compile(r"""<h2\b[^>]*\bid\s*=\s*["']Titleh2["'][^>]*>(?P<t>.*?)</h2\s*>""",
                        re.IGNORECASE | re.DOTALL)
# The release text sits between the "Posted On" block and the "(Release ID: n)"
# line. Everything outside it — header/nav, ministry + title block, then the
# Release ID, visitor counter, "Read this release in" switcher, related-release
# tags/links, share widgets, the hidden print copy and the footer — is chrome.
_PIB_BODY_START = re.compile(r"""<div\b[^>]*\bid\s*=\s*["']PrDateTime["'][^>]*>.*?</div\s*>""",
                             re.IGNORECASE | re.DOTALL)
_PIB_BODY_END = re.compile(r"""<span\b[^>]*\bid\s*=\s*["']ReleaseId["']""", re.IGNORECASE)


def pib_prid(url: str | None) -> str | None:
    """The ``PRID`` query value of a PIB URL (key matched case-insensitively)."""
    try:
        query = urlsplit(url or "").query
    except ValueError:
        return None
    for key, value in parse_qsl(query):
        if key.lower() == "prid" and value.strip().isdigit():
            return value.strip()
    return None


def pib_full_page_url(link: str | None) -> str | None:
    """Rewrite a feed item's ``PressReleaseIframePage.aspx?PRID=n`` link to the
    full ``PressReleasePage.aspx?PRID=n`` — the page with the language switcher."""
    prid = pib_prid(link)
    return f"{_PIB_BASE}?PRID={prid}" if prid else None


def pib_english_url(prid: str) -> str:
    return f"{_PIB_BASE}?PRID={prid}&lang=1"


def pib_english_prid(html: str | None) -> str | None:
    """PRID linked by the anchor whose trimmed visible text is ``English``."""
    for match in _ANCHOR.finditer(html or ""):
        if _plain(match.group("inner")).strip().casefold() != "english":
            continue
        href = _HREF.search(match.group("attrs"))
        prid = pib_prid(_html.unescape(href.group("href"))) if href else None
        if prid:
            return prid
    return None


def pib_title(html: str | None) -> str | None:
    match = _PIB_TITLE.search(html or "")
    title = _plain(match.group("t")).strip() if match else ""
    return title or None


def pib_release_body(html: str | None) -> str | None:
    """The release text of a PIB PressReleasePage with the chrome cut.

    ``None`` when either marker is missing — the caller then keeps the whole-page
    text rather than guessing a cut.
    """
    source = html or ""
    start = _PIB_BODY_START.search(source)
    if not start:
        return None
    end = _PIB_BODY_END.search(source, start.end())
    if not end:
        return None
    body = _plain(source[start.end():end.start()]).strip()
    return body or None


@dataclass
class FollowedItem:
    """Outcome of following a feed item to the page whose content is stored.

    ``error`` set → transient failure: record per item, write no row, retry next
    pass. Otherwise ``page`` / ``url`` / ``body`` describe the stored document,
    and ``forced_reason`` (when set) deprioritises it whatever its body.
    """

    error: str | None = None
    page: Any = None
    url: str | None = None
    title: str | None = None
    body: str | None = None
    forced_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def follow_pib_english(
    link: str,
    *,
    fetch: Callable[..., Any],
    user_agent: str | None,
    min_chars: int,
) -> FollowedItem:
    """Resolve a PIB Hindi feed item to its English release.

    Hindi full page → "English" anchor → ``PressReleasePage.aspx?PRID=<en>&lang=1``.
    No English anchor, or an English page too thin to be the release, yields the
    Hindi page as a ``language_mismatch`` row. A failed fetch at either hop is an
    error, retried next pass (CA-RSS-01 semantics).
    """
    hi_url = pib_full_page_url(link) or link
    hi_page = fetch(hi_url, adapter_type="html", user_agent=user_agent)
    if not getattr(hi_page, "ok", False):
        return FollowedItem(error=str(getattr(hi_page, "error", None) or "fetch_failed"))
    hi_html = page_html(hi_page)
    meta: dict[str, Any] = {"source_prid_hi": pib_prid(hi_url)}

    def _mismatch(why: str) -> FollowedItem:
        body = pib_release_body(hi_html) or (getattr(hi_page, "text", None) or "").strip()
        return FollowedItem(
            page=hi_page, url=hi_url, body=body or None,
            forced_reason=LANGUAGE_MISMATCH,
            metadata={**meta, "language_follow": why},
        )

    en_prid = pib_english_prid(hi_html)
    if not en_prid:
        return _mismatch("no_english_link")

    en_url = pib_english_url(en_prid)
    en_page = fetch(en_url, adapter_type="html", user_agent=user_agent)
    if not getattr(en_page, "ok", False):
        return FollowedItem(error=str(getattr(en_page, "error", None) or "fetch_failed"))
    en_html = page_html(en_page)
    trimmed = pib_release_body(en_html)
    body = trimmed or (getattr(en_page, "text", None) or "").strip()
    if len(body) < min_chars:
        return _mismatch("english_page_thin")
    return FollowedItem(
        page=en_page, url=en_url, title=pib_title(en_html), body=body,
        metadata={**meta, "source_prid_en": en_prid, "language_follow": "english",
                  "body_trim": "pib" if trimmed else "none"},
    )


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
