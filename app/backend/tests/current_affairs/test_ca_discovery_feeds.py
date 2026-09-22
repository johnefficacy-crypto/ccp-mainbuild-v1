"""CA-SRC-01 — wave-1b discovery_only feeds: format detection + the ADR 0007 guard.

Every assertion about a real publisher here runs against the committed fixture
in ``fixtures/discovery/``, captured from the live feed. The brief predicted
Atom for Bar & Bench and a Google-News sitemap for LiveLaw / IndiaSpend; the
fixtures say all six are RSS 2.0, and these tests pin what is actually served.

The Atom and Google-News-sitemap branches have NO real capture among the six, so
they are exercised by the two minimal documents below. Those are format-shape
samples written to cover a parser branch — they are explicitly not presented as
captures of any publisher's feed.

No network — ``fetch`` is injected.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.scraping import fetcher
from app.scraping.fetcher import (
    FEED_ATOM,
    FEED_GNEWS_SITEMAP,
    FEED_RSS,
    FEED_UNKNOWN,
    FetchResult,
    detect_feed_format,
    parse_feed,
)
from app.current_affairs import ingestion, sources
from tests.persona_questions._stub import SBStub

_FIXTURES = Path(__file__).parent / "fixtures" / "discovery"

# (fixture stem, publisher key, feed url, minimum entries the capture holds)
_WAVE_1B = [
    ("mongabay_india", "MONGABAY_INDIA", "https://india.mongabay.com/feed/", 20),
    ("vidhi", "VIDHI", "https://vidhilegalpolicy.in/feed/", 40),
    ("cpr_india", "CPR_INDIA", "https://cprindia.org/feed/", 10),
    ("barandbench", "BAR_AND_BENCH", "https://www.barandbench.com/feed", 1),
    ("livelaw", "LIVELAW", "https://www.livelaw.in/google_feeds.xml", 60),
    ("indiaspend", "INDIASPEND", "https://www.indiaspend.com/google_feeds.xml", 3),
]


def _fixture(stem: str) -> str:
    return (_FIXTURES / f"{stem}.xml").read_text(encoding="utf-8")


def _source(publisher: str, feed_url: str, **over) -> dict:
    base = {
        "id": f"src-{publisher.lower()}",
        "name": publisher,
        "authority_level": "discovery_only",
        "publisher_type": "news_media",
        "adapter_type": "rss",
        "rss_url": feed_url,
        "default_category": "general",
        "default_language": "en",
        "adapter_config": {"publisher": publisher, "feed_format": "rss"},
        "crawl_schedule": {"interval_hours": 12},
        "is_active": True,
        "consecutive_failures": 0,
    }
    base.update(over)
    return base


class _Net:
    """Serves the feed for the feed URL and 404s everything else — an item-page
    fetch is a test failure for a discovery_only source, so it must be visible."""

    def __init__(self, feed_xml: str, feed_url: str):
        self.feed_xml = feed_xml
        self.feed_url = feed_url
        self.calls: list[dict] = []

    def __call__(self, url, **kw):
        self.calls.append({"url": url, **kw})
        if url == self.feed_url:
            return FetchResult(
                ok=True, url=url, status_code=200, final_url=url,
                content_type="application/rss+xml", etag='"f1"',
                content_hash="feed-1", text=self.feed_xml,
            )
        return FetchResult(ok=False, url=url, status_code=404, error="http_404")

    @property
    def item_fetches(self) -> list[str]:
        return [c["url"] for c in self.calls if c["url"] != self.feed_url]


# ─── 1. format detection against the real captures ──────────────────────────

@pytest.mark.parametrize("stem,publisher,feed_url,min_items", _WAVE_1B)
def test_every_wave_1b_fixture_is_rss_and_parses(stem, publisher, feed_url, min_items):
    fmt, entries = parse_feed(_fixture(stem))
    assert fmt == FEED_RSS, f"{stem} detected as {fmt}"
    assert len(entries) >= min_items
    for e in entries:
        assert e.title and e.title.strip(), f"{stem}: entry without a title"
        assert e.link and e.link.strip(), f"{stem}: entry without a link"


@pytest.mark.parametrize("stem,publisher,feed_url,min_items", _WAVE_1B)
def test_every_wave_1b_fixture_carries_a_parseable_date(stem, publisher, feed_url, min_items):
    _, entries = parse_feed(_fixture(stem))
    for e in entries:
        assert e.published, f"{stem}: entry without a publication date"
        assert sources.parse_published_at(e.published) is not None, (
            f"{stem}: unparseable date {e.published!r}"
        )


def test_a_filename_never_decides_the_format():
    # LiveLaw and IndiaSpend serve plain RSS from a google_feeds.xml path, and
    # Bar & Bench only declares xmlns:atom for its self-link. Detection reads the
    # root element, so none of these are mistaken for another shape.
    for stem in ("livelaw", "indiaspend", "barandbench"):
        raw = _fixture(stem)
        assert detect_feed_format(raw) == FEED_RSS
        assert "<entry" not in raw and "news:news" not in raw


def test_cpr_india_feed_with_a_whitespace_prologue_still_parses():
    # This capture ships tabs/newlines before <?xml?>. Before CA-SRC-01 that made
    # ET.fromstring raise, the feed parsed to zero entries, and the ingest scored
    # the source as a failure on every single pass.
    raw = _fixture("cpr_india")
    assert raw[0] != "<", "fixture no longer has the leading-whitespace prologue"
    fmt, entries = parse_feed(raw)
    assert fmt == FEED_RSS and len(entries) >= 10


def test_malformed_and_empty_feeds_are_unknown_not_a_guess():
    for bad in ("", None, "<not-xml", "<html><body>nope</body></html>"):
        fmt, entries = parse_feed(bad)
        assert entries == []
        assert fmt in (FEED_UNKNOWN,), f"{bad!r} -> {fmt}"


# ─── format-shape samples for the two branches no capture covers ────────────
#
# Written by hand to exercise a parser branch. NOT a capture of any real feed.

_ATOM_SHAPE = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Shape sample</title>
  <entry>
    <title>First entry</title>
    <link rel="edit" href="https://example.test/edit/1"/>
    <link rel="alternate" href="https://example.test/posts/1"/>
    <summary>A short summary.</summary>
    <content type="html">THE WHOLE ARTICLE BODY</content>
    <published>2026-09-21T10:00:00Z</published>
    <updated>2026-09-22T11:00:00Z</updated>
  </entry>
  <entry>
    <title>Second entry</title>
    <link href="https://example.test/posts/2"/>
    <updated>2026-09-20T09:00:00Z</updated>
  </entry>
</feed>
"""

_GNEWS_SHAPE = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news">
  <url>
    <loc>https://example.test/story/1</loc>
    <news:news>
      <news:publication><news:name>Example</news:name></news:publication>
      <news:publication_date>2026-09-22T04:30:00+05:30</news:publication_date>
      <news:title>A sitemap story</news:title>
    </news:news>
  </url>
</urlset>
"""


def test_atom_shape_maps_onto_rss_entry():
    fmt, entries = parse_feed(_ATOM_SHAPE)
    assert fmt == FEED_ATOM and len(entries) == 2

    first = entries[0]
    assert first.title == "First entry"
    assert first.link == "https://example.test/posts/1"   # rel=alternate wins over rel=edit
    assert first.summary == "A short summary."
    assert first.published == "2026-09-21T10:00:00Z"      # published preferred over updated

    second = entries[1]
    assert second.link == "https://example.test/posts/2"  # bare href when no rel is marked
    assert second.published == "2026-09-20T09:00:00Z"     # falls back to updated


def test_atom_content_is_never_taken_as_the_summary():
    # ADR 0007: the full article body must never become a discovery_only row's
    # stored content, and <content> is exactly that body.
    _, entries = parse_feed(_ATOM_SHAPE)
    assert "WHOLE ARTICLE BODY" not in (entries[0].summary or "")
    assert entries[1].summary == ""        # no summary element, and content is not a fallback


def test_rss_content_encoded_is_never_taken_as_the_summary():
    # Four of the six real captures carry <content:encoded>; none of it is stored.
    for stem in ("mongabay_india", "cpr_india", "indiaspend", "barandbench"):
        raw = _fixture(stem)
        if "<content:encoded" not in raw:
            continue
        _, entries = parse_feed(raw)
        joined = " ".join(e.summary or "" for e in entries)
        assert "<content:encoded" not in joined


def test_gnews_sitemap_shape_maps_onto_rss_entry():
    fmt, entries = parse_feed(_GNEWS_SHAPE)
    assert fmt == FEED_GNEWS_SITEMAP and len(entries) == 1
    e = entries[0]
    assert e.link == "https://example.test/story/1"
    assert e.title == "A sitemap story"
    assert e.published == "2026-09-22T04:30:00+05:30"
    assert e.summary == ""      # a sitemap lists locations, not extracts
    assert sources.parse_published_at(e.published) == "2026-09-21T23:00:00+00:00"


def test_a_plain_sitemap_without_the_news_namespace_is_not_a_news_feed():
    plain = ('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
             "<url><loc>https://example.test/a</loc></url></urlset>")
    assert detect_feed_format(plain) == FEED_UNKNOWN
    assert parse_feed(plain) == (FEED_UNKNOWN, [])


# ─── 2. the ADR 0007 guard, against every real fixture ──────────────────────

@pytest.mark.parametrize("stem,publisher,feed_url,min_items", _WAVE_1B)
def test_discovery_only_stores_pointers_and_never_fetches_an_item_page(
    stem, publisher, feed_url, min_items
):
    src = _source(publisher, feed_url)
    sb = SBStub({"current_affairs_sources": [src], "current_affairs_documents": []})
    net = _Net(_fixture(stem), feed_url)

    res = ingestion.ingest_source(sb, src, fetch=net)
    docs = sb.db["current_affairs_documents"]

    assert res["status"] == "discovery_only"
    assert len(docs) >= min_items
    assert net.item_fetches == [], f"{stem} fetched an item page"

    for d in docs:
        assert d["raw_text"] is None, f"{stem} stored article text"
        assert d["ingestion_status"] == "discovery_only"
        assert d["title"] and d["canonical_item_url"]
        assert d["metadata"]["feed_format"] == "rss"


@pytest.mark.parametrize("stem,publisher,feed_url,min_items", _WAVE_1B)
def test_discovery_only_documents_are_never_enqueued_for_generation(
    stem, publisher, feed_url, min_items
):
    src = _source(publisher, feed_url)
    sb = SBStub({
        "current_affairs_sources": [src],
        "current_affairs_documents": [],
        "current_affairs_generation_jobs": [],
    })
    ingestion.ingest_source(sb, src, fetch=_Net(_fixture(stem), feed_url))
    # _reconcile_pending_generation only ever enqueues 'snapshotted' rows.
    assert all(d["ingestion_status"] == "discovery_only"
               for d in sb.db["current_affairs_documents"])
    assert sb.db["current_affairs_generation_jobs"] == []


def test_the_guard_keys_on_authority_level_not_adapter_config():
    # A row cannot opt back into article capture by editing adapter_config.
    feed_url = "https://cprindia.org/feed/"
    src = _source("CPR_INDIA", feed_url,
                  adapter_config={"publisher": "CPR_INDIA", "discovery_only": False,
                                  "fetch_item_pages": True})
    sb = SBStub({"current_affairs_sources": [src], "current_affairs_documents": []})
    net = _Net(_fixture("cpr_india"), feed_url)
    ingestion.ingest_source(sb, src, fetch=net)
    assert net.item_fetches == []
    assert all(d["raw_text"] is None for d in sb.db["current_affairs_documents"])

    # ...and the converse: dropping discovery_only from authority_level is what
    # actually re-enables the item-page path.
    assert sources.is_discovery_only(src) is True
    assert sources.is_discovery_only({**src, "authority_level": "official_secondary"}) is False


# ─── summary: stripped, unescaped, capped ───────────────────────────────────

def test_discovery_summary_is_reduced_to_text_and_capped():
    feed_url = "https://cprindia.org/feed/"          # ships <p> markup + entities
    src = _source("CPR_INDIA", feed_url)
    sb = SBStub({"current_affairs_sources": [src], "current_affairs_documents": []})
    ingestion.ingest_source(sb, src, fetch=_Net(_fixture("cpr_india"), feed_url))

    summaries = [d["metadata"].get("feed_summary") for d in sb.db["current_affairs_documents"]]
    summaries = [s for s in summaries if s]
    assert summaries, "expected CPR India entries to carry summaries"
    for s in summaries:
        assert len(s) <= 500
        assert "<p>" not in s and "&#8220;" not in s and "&amp;" not in s


def test_summary_cap_is_a_crawl_schedule_knob():
    feed_url = "https://vidhilegalpolicy.in/feed/"
    src = _source("VIDHI", feed_url,
                  crawl_schedule={"interval_hours": 24, "summary_chars": 80})
    sb = SBStub({"current_affairs_sources": [src], "current_affairs_documents": []})
    ingestion.ingest_source(sb, src, fetch=_Net(_fixture("vidhi"), feed_url))
    for d in sb.db["current_affairs_documents"]:
        assert len(d["metadata"].get("feed_summary") or "") <= 80


def test_an_ordinary_source_keeps_the_30_item_page_fetch_cap():
    # The higher discovery cap must not leak into a source that pays a page
    # fetch per item.
    from app.current_affairs.ingestion import _max_items_per_pass

    src = {"crawl_schedule": {"interval_hours": 12}}
    assert _max_items_per_pass(src) == 30
    assert _max_items_per_pass(src, discovery_only=True) == 200
    override = {"crawl_schedule": {"max_items_per_pass": 5}}
    assert _max_items_per_pass(override, discovery_only=True) == 5


def test_a_mostly_pointer_only_feed_is_ingested_without_summaries():
    # Most LiveLaw items ship no <description> at all (52 of 60 in this capture).
    # A missing summary is a pointer-only entry, not an error — the row still
    # lands on its title and link.
    feed_url = "https://www.livelaw.in/google_feeds.xml"
    src = _source("LIVELAW", feed_url)
    sb = SBStub({"current_affairs_sources": [src], "current_affairs_documents": []})
    res = ingestion.ingest_source(sb, src, fetch=_Net(_fixture("livelaw"), feed_url))
    assert res["status"] == "discovery_only"

    docs = sb.db["current_affairs_documents"]
    assert len(docs) >= 60
    assert all(d["title"] and d["canonical_item_url"] for d in docs)

    summaries = [(d["metadata"].get("feed_summary") or "") for d in docs]
    assert sum(1 for x in summaries if not x) > len(docs) // 2   # mostly pointer-only
    for text in (x for x in summaries if x):
        assert len(text) <= 500
        assert "<" not in text and "&#" not in text


def test_raw_pub_date_is_kept_on_discovery_rows():
    feed_url = "https://india.mongabay.com/feed/"
    src = _source("MONGABAY_INDIA", feed_url)
    sb = SBStub({"current_affairs_sources": [src], "current_affairs_documents": []})
    ingestion.ingest_source(sb, src, fetch=_Net(_fixture("mongabay_india"), feed_url))
    for d in sb.db["current_affairs_documents"]:
        assert d["metadata"]["raw_pub_date"]
        assert d["published_at"]


# ─── re-running a discovery feed is free ────────────────────────────────────

def test_second_pass_over_the_same_feed_adds_nothing():
    feed_url = "https://india.mongabay.com/feed/"
    src = _source("MONGABAY_INDIA", feed_url)
    sb = SBStub({"current_affairs_sources": [src], "current_affairs_documents": []})
    raw = _fixture("mongabay_india")

    ingestion.ingest_source(sb, src, fetch=_Net(raw, feed_url))
    first = len(sb.db["current_affairs_documents"])

    net2 = _Net(raw, feed_url)
    res = ingestion.ingest_source(sb, src, fetch=net2)
    assert res["status"] == "duplicate"
    assert len(sb.db["current_affairs_documents"]) == first
    assert net2.item_fetches == []


def test_parse_rss_feed_wrapper_is_unchanged_for_existing_callers():
    # The recruitment scraper and the pre-CA-SRC-01 CA paths call this.
    entries = fetcher.parse_rss_feed(_fixture("mongabay_india"))
    assert len(entries) >= 20
    assert entries == parse_feed(_fixture("mongabay_india"))[1]
