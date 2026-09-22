"""CA-RSS-03 — PIB English-version follow, language guard, page dates,
discovery_only enforcement, multi-RBI tolerance.

PIB's only non-empty feed (Regid=3) is Hindi and carries no pubDate. Every PIB
page used here is a real, operator-captured page under ``fixtures/pib/``:

* ``feed_regid3.xml``      — the live Regid=3 feed (20 Hindi items, no pubDate)
* ``hindi_item.html``      — PressReleaseIframePage.aspx?PRID=2313241
* ``hindi_item_full.html`` — PressReleasePage.aspx?PRID=2313241 (language switcher)
* ``english_item.html``    — PressReleasePage.aspx?PRID=2313185&lang=1

No PIB HTML is synthesised. No network — ``fetch`` is injected.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.scraping.fetcher import FetchResult, strip_html
from app.current_affairs import ingestion, sources
from tests.persona_questions._stub import SBStub

_FIX = Path(__file__).parent / "fixtures" / "pib"


def _read(name: str) -> str:
    return (_FIX / name).read_text(encoding="utf-8")


_FEED_URL = "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3"
_HI_IFRAME = "https://pib.gov.in/PressReleaseIframePage.aspx?PRID=2313241"
_HI_FULL = "https://pib.gov.in/PressReleasePage.aspx?PRID=2313241"
_EN = "https://pib.gov.in/PressReleasePage.aspx?PRID=2313185&lang=1"
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"

_FEED = _read("feed_regid3.xml")
_HINDI_IFRAME_HTML = _read("hindi_item.html")
_HINDI_FULL_HTML = _read("hindi_item_full.html")
_ENGLISH_HTML = _read("english_item.html")


def _first_item_feed() -> str:
    """The real feed cut down to its first <item> (PRID=2313241)."""
    head, rest = _FEED.split("<item>", 1)
    first = rest.split("</item>", 1)[0]
    return f"{head}<item>{first}</item></channel></rss>"


def _without_english_anchor(html: str) -> str:
    """The real Hindi full page with its one 'English' switcher anchor removed."""
    anchor = re.search(r"<a\b[^>]*>\s*English\s*</a>\s*,?", html)
    assert anchor, "fixture must carry the English anchor"
    return html[: anchor.start()] + html[anchor.end():]


def _pib_source(**over) -> dict:
    base = {
        "id": "src-pib",
        "name": "Press Information Bureau",
        "authority_level": "primary_official",
        "adapter_type": "rss",
        "rss_url": _FEED_URL,
        "official_url": "https://pib.gov.in/",
        "default_category": "national",
        "default_language": "en",
        "adapter_config": {"publisher": "PIB", "user_agent": _UA},
        "crawl_schedule": {"interval_hours": 12},
        "is_active": True,
        "consecutive_failures": 0,
    }
    base.update(over)
    return base


class _Net:
    def __init__(self, feed_xml: str, *, feed_url: str = _FEED_URL, pages=None):
        self.feed_xml = feed_xml
        self.feed_url = feed_url
        self.pages = pages or {}
        self.calls: list[dict] = []

    def __call__(self, url, **kw):
        self.calls.append({"url": url, **kw})
        if url == self.feed_url:
            return FetchResult(
                ok=True, url=url, status_code=200, final_url=url,
                content_type="application/rss+xml", content_hash="feed", text=self.feed_xml,
            )
        html = self.pages.get(url)
        if html is None:
            return FetchResult(ok=False, url=url, status_code=404, error="http_404")
        if isinstance(html, FetchResult):
            return html
        return FetchResult(
            ok=True, url=url, status_code=200, final_url=url,
            content_type="text/html; charset=utf-8", content_hash=f"pagehash::{url}",
            text=strip_html(html), raw_bytes=html.encode("utf-8"),
        )

    @property
    def fetched(self) -> list[str]:
        return [c["url"] for c in self.calls if c["url"] != self.feed_url]


def _db(*srcs, docs=None) -> SBStub:
    return SBStub({
        "current_affairs_sources": list(srcs) or [_pib_source()],
        "current_affairs_documents": list(docs or []),
    })


def _pib_net(**pages) -> _Net:
    served = {_HI_IFRAME: _HINDI_IFRAME_HTML, _HI_FULL: _HINDI_FULL_HTML, _EN: _ENGLISH_HTML}
    served.update(pages)
    return _Net(_first_item_feed(), pages=served)


# ─── fixture sanity ─────────────────────────────────────────────────────────

def test_real_feed_is_hindi_and_carries_no_pubdate():
    from app.scraping.fetcher import parse_rss_feed

    entries = parse_rss_feed(_FEED)
    assert len(entries) == 20
    assert all(e.published is None for e in entries)
    assert all("PressReleaseIframePage.aspx?PRID=" in e.link for e in entries)
    assert all(sources.detect_language(e.title * 3) == "hi" for e in entries)


# ─── 1. English-version follow ──────────────────────────────────────────────

def test_hindi_item_is_followed_to_its_english_release():
    sb = _db()
    net = _pib_net()

    res = ingestion.ingest_source(sb, _pib_source(), fetch=net)

    assert res["status"] == "snapshotted" and res["items_snapshotted"] == 1
    # Feed Iframe link rewritten to the full page; the Iframe page is never fetched.
    assert net.fetched == [_HI_FULL, _EN]
    # Both hops carry PIB's browser UA (it 403s the bot UA).
    assert all(c.get("user_agent") == _UA for c in net.calls if c["url"] != _FEED_URL)

    [doc] = sb.db["current_affairs_documents"]
    assert doc["ingestion_status"] == "snapshotted"
    assert doc["title"] == (
        "DRI seizes over 845 kg contraband drugs at various locations in "
        "intensified crackdown on drug trafficking;"
    )
    assert doc["source_url"] == _EN
    assert doc["canonical_item_url"] == sources.canonical_item_link(_EN)
    meta = doc["metadata"]
    assert meta["source_prid_hi"] == "2313241"
    assert meta["source_prid_en"] == "2313185"
    assert meta["source_url_hi"] == sources.canonical_item_link(_HI_IFRAME)
    assert meta["detected_language"] == "en"

    # Page date: 'Posted On: 21 SEP 2026 7:44PM' (IST) → 14:14 UTC.
    assert meta["date_source"] == "page"
    assert meta["raw_page_date"] == "21 SEP 2026 7:44PM"
    assert doc["published_at"] == "2026-09-21T14:14:00+00:00"


def test_english_body_is_the_release_text_only():
    sb = _db()
    ingestion.ingest_source(sb, _pib_source(), fetch=_pib_net())
    body = sb.db["current_affairs_documents"][0]["raw_text"]

    assert body.startswith("Continuing its sustained crackdown on illicit drug trafficking")
    assert body.rstrip().endswith("SR/KMN")
    # Header / title block, date line, and everything after "(Release ID: n)":
    # the visitor counter, the "Read this release in" switcher, related-release
    # tags/links, share widgets, the hidden print copy and the footer.
    for chrome in ("Press Information Bureau", "Ministry of Finance", "Posted On",
                   "Release ID", "Visitor Counter", "Read this release in", "हिन्दी",
                   "Share on", "<", "&#39;"):
        assert chrome not in body, chrome
    # The print copy duplicates the release — the body must hold it once.
    assert body.count("Continuing its sustained crackdown") == 1


def test_english_prid_is_chosen_by_anchor_text_never_by_position():
    # The full Hindi page holds several PRIDs: itself (5x), its lang=2 self-link,
    # Urdu, Tamil — and English (2313185) is not the first one in the document.
    prids = re.findall(r"PRID=(\d+)", _HINDI_FULL_HTML)
    assert prids[0] != "2313185" and {"2313220", "2313268", "2313241"} <= set(prids)
    assert sources.pib_english_prid(_HINDI_FULL_HTML) == "2313185"
    # The English page links Urdu / Hindi / Tamil but no 'English' anchor.
    assert sources.pib_english_prid(_ENGLISH_HTML) is None


def test_no_english_anchor_writes_a_language_mismatch_row():
    sb = _db()
    net = _pib_net(**{_HI_FULL: _without_english_anchor(_HINDI_FULL_HTML)})

    res = ingestion.ingest_source(sb, _pib_source(), fetch=net)

    assert res["status"] == "deprioritised"
    assert net.fetched == [_HI_FULL]  # nothing to follow
    [doc] = sb.db["current_affairs_documents"]
    assert doc["ingestion_status"] == "deprioritised"
    assert doc["metadata"]["prefilter_reason"] == "language_mismatch"
    assert doc["metadata"]["language_follow"] == "no_english_link"
    assert doc["metadata"]["detected_language"] == "hi"
    # Keyed on the Hindi FULL page, never on the feed's Iframe link.
    assert doc["canonical_item_url"] == sources.canonical_item_link(_HI_FULL)
    assert doc["metadata"]["source_url_hi"] == sources.canonical_item_link(_HI_IFRAME)
    # Hindi page date parses too ('प्रविष्टि तिथि: 21 SEP 2026 7:44PM').
    assert doc["published_at"] == "2026-09-21T14:14:00+00:00"


def test_thin_english_page_writes_a_language_mismatch_row():
    sb = _db()
    source = _pib_source(crawl_schedule={"min_body_chars": 100000})
    net = _pib_net()

    ingestion.ingest_source(sb, source, fetch=net)

    [doc] = sb.db["current_affairs_documents"]
    assert doc["ingestion_status"] == "deprioritised"
    assert doc["metadata"]["prefilter_reason"] == "language_mismatch"
    assert doc["metadata"]["language_follow"] == "english_page_thin"


def test_transient_english_fetch_failure_writes_no_row_and_retries():
    sb = _db()
    down = FetchResult(ok=False, url=_EN, status_code=503, error="http_503")
    net = _pib_net(**{_EN: down})

    res = ingestion.ingest_source(sb, _pib_source(), fetch=net)
    assert res["status"] == "error"
    assert res["item_errors"] == [{"link": _HI_IFRAME, "error": "http_503"}]
    assert sb.db["current_affairs_documents"] == []

    # Next pass, English is back: the item is still NEW and resolves.
    net2 = _pib_net()
    res2 = ingestion.ingest_source(sb, _pib_source(), fetch=net2)
    assert res2["items_snapshotted"] == 1


def test_transient_hindi_page_failure_writes_no_row():
    sb = _db()
    net = _pib_net(**{_HI_FULL: FetchResult(ok=False, url=_HI_FULL, error="timeout")})
    res = ingestion.ingest_source(sb, _pib_source(), fetch=net)
    assert res["item_errors"] == [{"link": _HI_IFRAME, "error": "timeout"}]
    assert sb.db["current_affairs_documents"] == []


def test_second_pass_on_a_resolved_hindi_item_fetches_nothing():
    sb = _db()
    ingestion.ingest_source(sb, _pib_source(), fetch=_pib_net())
    assert len(sb.db["current_affairs_documents"]) == 1

    net2 = _pib_net()
    res = ingestion.ingest_source(sb, _pib_source(), fetch=net2)
    assert net2.fetched == []  # only the feed
    assert res["items_known"] == 1 and res["items_new"] == 0
    assert len(sb.db["current_affairs_documents"]) == 1


def test_second_pass_on_a_mismatch_item_fetches_nothing():
    sb = _db()
    pages = {_HI_FULL: _without_english_anchor(_HINDI_FULL_HTML)}
    ingestion.ingest_source(sb, _pib_source(), fetch=_pib_net(**pages))

    net2 = _pib_net(**pages)
    ingestion.ingest_source(sb, _pib_source(), fetch=net2)
    assert net2.fetched == []


def test_legacy_hindi_row_re_resolves_to_english():
    # A pre-CA-RSS-03 row: canonical = the Iframe feed link, Hindi body, no
    # source_url_hi — exactly what migration 300 deprioritises.
    legacy = {
        "id": "doc-legacy",
        "source_id": "src-pib",
        "source_url": _HI_IFRAME,
        "canonical_item_url": sources.canonical_item_link(_HI_IFRAME),
        "title": "डीआरआई ने मादक पदार्थों की तस्करी के खिलाफ बड़ी कार्रवाई",
        "raw_text": strip_html(_HINDI_IFRAME_HTML),
        "content_hash": "legacy-iframe-hash",
        "ingestion_status": "deprioritised",
        "metadata": {"publisher": "PIB",
                     "prefilter_reason": "language_mismatch_pre_rss03"},
    }
    sb = _db(docs=[legacy])
    net = _pib_net()

    res = ingestion.ingest_source(sb, _pib_source(), fetch=net)

    assert res["items_snapshotted"] == 1
    assert net.fetched == [_HI_FULL, _EN]
    docs = sb.db["current_affairs_documents"]
    assert len(docs) == 2
    english = next(d for d in docs if d["id"] != "doc-legacy")
    # New slot: English canonical ≠ the legacy row's Iframe canonical.
    assert english["canonical_item_url"] != legacy["canonical_item_url"]
    assert english["metadata"]["source_url_hi"] == legacy["canonical_item_url"]
    # The legacy row is untouched (documents are immutable evidence).
    assert next(d for d in docs if d["id"] == "doc-legacy")["ingestion_status"] == "deprioritised"


def test_iframe_rewrite_and_prid_parsing():
    assert sources.pib_full_page_url(_HI_IFRAME) == _HI_FULL
    assert sources.pib_full_page_url("https://pib.gov.in/PressReleseDetail.aspx?prid=77") == \
        "https://pib.gov.in/PressReleasePage.aspx?PRID=77"
    assert sources.pib_full_page_url("https://pib.gov.in/") is None
    assert sources.pib_english_url("2313185") == _EN


# ─── 2. Language guard (every source) ───────────────────────────────────────

def _rbi_source(**over) -> dict:
    base = {
        "id": "src-rbi-notif",
        "name": "Reserve Bank of India — Notifications",
        "authority_level": "primary_official",
        "adapter_type": "rss",
        "rss_url": "https://rbi.test/notifications_rss.xml",
        "default_language": "en",
        "adapter_config": {"publisher": "RBI", "feed": "notifications"},
        "crawl_schedule": {"interval_hours": 24},
        "is_active": True,
        "consecutive_failures": 0,
    }
    base.update(over)
    return base


def _feed(url_title_pairs, *, pub_date="Mon, 21 Sep 2026 10:00:00 +0530") -> str:
    items = "".join(
        f"<item><title>{t}</title><link>{u}</link><description>Summary of {t}</description>"
        f"<pubDate>{pub_date}</pubDate></item>"
        for u, t in url_title_pairs
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{items}</channel></rss>'


_ENGLISH_BODY = "<html><body><p>" + ("The Reserve Bank of India today notified revised norms. " * 12) + "</p></body></html>"
# A Hindi release body from the real PIB fixture, served on a non-PIB source.
_HINDI_BODY = "<html><body><p>" + (sources.pib_release_body(_HINDI_FULL_HTML) or "") + "</p></body></html>"


def test_language_guard_deprioritises_a_hindi_body_on_an_english_source():
    src = _rbi_source()
    hi_url, en_url = "https://rbi.test/n/hi-1", "https://rbi.test/n/en-1"
    net = _Net(_feed([(hi_url, "Hindi notice"), (en_url, "English notice")]),
               feed_url=src["rss_url"], pages={hi_url: _HINDI_BODY, en_url: _ENGLISH_BODY})
    sb = _db(src)

    res = ingestion.ingest_source(sb, src, fetch=net)

    assert res["items_snapshotted"] == 1 and res["items_deprioritised"] == 1
    docs = {d["canonical_item_url"]: d for d in sb.db["current_affairs_documents"]}
    assert docs[hi_url]["ingestion_status"] == "deprioritised"
    assert docs[hi_url]["metadata"]["prefilter_reason"] == "language_mismatch"
    assert docs[hi_url]["metadata"]["detected_language"] == "hi"
    assert docs[en_url]["ingestion_status"] == "snapshotted"
    assert docs[en_url]["metadata"]["detected_language"] == "en"
    # Feed carried a parseable date → feed wins, page never consulted.
    assert docs[en_url]["metadata"]["date_source"] == "feed"


def test_language_guard_accepts_hindi_on_a_hindi_source():
    src = _rbi_source(default_language="hi")
    url = "https://rbi.test/n/hi-1"
    net = _Net(_feed([(url, "Hindi notice")]), feed_url=src["rss_url"], pages={url: _HINDI_BODY})
    sb = _db(src)
    ingestion.ingest_source(sb, src, fetch=net)
    assert sb.db["current_affairs_documents"][0]["ingestion_status"] == "snapshotted"


def test_language_guard_on_whole_body_sources():
    src = {
        "id": "src-html", "name": "HTML source", "authority_level": "primary_official",
        "adapter_type": "html", "crawl_url": "https://html.test/page",
        "default_language": "en", "adapter_config": {}, "is_active": True,
        "consecutive_failures": 0,
    }
    net = _Net("", feed_url="__none__", pages={"https://html.test/page": _HINDI_BODY})
    sb = _db(src)
    res = ingestion.ingest_source(sb, src, fetch=net)
    assert res["status"] == "deprioritised" and res["reason"] == "language_mismatch"
    assert sb.db["current_affairs_documents"][0]["metadata"]["detected_language"] == "hi"


def test_detect_language_abstains_on_too_little_text():
    assert sources.detect_language("") is None
    assert sources.detect_language("RBI") is None
    assert sources.language_mismatch(None, "en") is False
    assert sources.language_mismatch("hi", "ta") is False  # undetectable target
    assert sources.language_mismatch("hi", "en") is True


# ─── 3. Page dates ──────────────────────────────────────────────────────────

def test_page_date_is_never_invented():
    assert sources.page_published_at("PIB", "no date here") == (None, None)
    assert sources.page_published_at("RBI", strip_html(_ENGLISH_HTML)) == (None, None)
    assert sources.page_published_at(None, strip_html(_ENGLISH_HTML)) == (None, None)
    # Raw whitespace between label and value (newline + indentation) is tolerated.
    raw, iso = sources.page_published_at("PIB", "Posted On:\n            21 SEP 2026 7:44PM by PIB Delhi")
    assert raw == "21 SEP 2026 7:44PM" and iso == "2026-09-21T14:14:00+00:00"
    # AM and midnight/noon edges.
    assert sources.page_published_at("PIB", "Posted On: 1 JAN 2026 12:05AM")[1] == "2025-12-31T18:35:00+00:00"
    assert sources.page_published_at("PIB", "Posted On: 1 JAN 2026 12:05PM")[1] == "2026-01-01T06:35:00+00:00"


def test_no_feed_or_page_date_leaves_published_at_null():
    src = _rbi_source()
    url = "https://rbi.test/n/1"
    feed = _feed([(url, "Notice")]).replace("<pubDate>Mon, 21 Sep 2026 10:00:00 +0530</pubDate>", "")
    net = _Net(feed, feed_url=src["rss_url"], pages={url: _ENGLISH_BODY})
    sb = _db(src)
    ingestion.ingest_source(sb, src, fetch=net)
    doc = sb.db["current_affairs_documents"][0]
    assert doc["published_at"] is None
    assert "date_source" not in doc["metadata"]


# ─── 6. discovery_only ──────────────────────────────────────────────────────

def _hindu_source() -> dict:
    return {
        "id": "src-hindu",
        "name": "The Hindu — National",
        "authority_level": "discovery_only",
        "publisher_type": "news_media",
        "adapter_type": "rss",
        "rss_url": "https://thehindu.test/news/national/feeder/default.rss",
        "default_category": "general",
        "default_language": "en",
        "adapter_config": {"publisher": "THE_HINDU"},
        "crawl_schedule": {"interval_hours": 12},
        "is_active": True,
        "consecutive_failures": 0,
    }


def test_discovery_only_item_stores_title_link_summary_and_nothing_else():
    src = _hindu_source()
    url = "https://thehindu.test/news/national/some-story/article1.ece"
    net = _Net(_feed([(url, "Some national story")]), feed_url=src["rss_url"],
               pages={url: _ENGLISH_BODY})
    sb = _db(src)

    res = ingestion.ingest_source(sb, src, fetch=net)

    assert net.fetched == []  # no item-page fetch, ever
    assert res["status"] == "discovery_only" and res["items_discovery"] == 1
    [doc] = sb.db["current_affairs_documents"]
    assert doc["ingestion_status"] == "discovery_only"
    assert doc["raw_text"] is None  # no article text
    assert doc["title"] == "Some national story"
    assert doc["source_url"] == url and doc["canonical_item_url"] == url
    assert doc["metadata"]["feed_summary"] == "Summary of Some national story"
    assert doc["metadata"]["prefilter_reason"] == "discovery_only"


class _Exec:
    def execute(self):
        return self


def test_discovery_only_items_never_get_a_generation_job():
    src = _hindu_source()
    url = "https://thehindu.test/news/national/x/article2.ece"
    sb = SBStub({
        "current_affairs_sources": [src],
        "current_affairs_documents": [],
        "current_affairs_generation_jobs": [],
    })
    net = _Net(_feed([(url, "Story")]), feed_url=src["rss_url"])
    rpc_calls: list = []
    sb.rpc = lambda name, params=None: rpc_calls.append((name, params)) or _Exec()

    counts = ingestion.run_ingest_pass(sb, fetch=net)

    assert counts["items_discovery"] == 1
    assert counts["enqueued"] == 0
    assert not [c for c in rpc_calls if c[0] == "ca_enqueue_generation_job"]


def test_discovery_only_whole_body_source_is_not_ingested():
    src = {**_hindu_source(), "adapter_type": "html", "crawl_url": "https://thehindu.test/"}
    net = _Net("", feed_url="__none__", pages={"https://thehindu.test/": _ENGLISH_BODY})
    sb = _db(src)
    res = ingestion.ingest_source(sb, src, fetch=net)
    assert res == {"status": "skipped", "reason": "discovery_only_non_rss", "source_id": "src-hindu"}
    assert net.calls == []
    assert sb.db["current_affairs_documents"] == []


def test_validator_still_refuses_discovery_only_as_sole_evidence():
    # ADR 0007 second line of defence (generation/validator.py) is unchanged.
    from app.current_affairs.generation import validator

    assert validator.DISCOVERY_ONLY == sources.DISCOVERY_ONLY == "discovery_only"


# ─── 5. several RBI sources side by side ────────────────────────────────────

def test_multiple_rbi_sources_ingest_independently():
    notif = _rbi_source()
    speech = _rbi_source(
        id="src-rbi-speech", name="Reserve Bank of India — Speeches",
        rss_url="https://rbi.test/speeches_rss.xml",
        adapter_config={"publisher": "RBI", "feed": "speeches"},
    )
    shared = "https://rbi.test/scripts/item?id=1"  # same link in both feeds
    sb = _db(notif, speech)

    for src in (notif, speech):
        net = _Net(_feed([(shared, "Governor's statement")]), feed_url=src["rss_url"],
                   pages={shared: _ENGLISH_BODY.replace("norms", f"norms {src['id']}")})
        res = ingestion.ingest_source(sb, src, fetch=net)
        assert res["items_snapshotted"] == 1, src["id"]

    docs = sb.db["current_affairs_documents"]
    assert {d["source_id"] for d in docs} == {"src-rbi-notif", "src-rbi-speech"}
    # Both share the publisher's defaults; dedup is per source_id, not per publisher.
    assert sources.adapter_defaults(notif) == sources.adapter_defaults(speech)
    assert all(d["document_type"] == "press_release" for d in docs)
