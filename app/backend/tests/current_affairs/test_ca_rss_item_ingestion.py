"""CA-RSS-01 — item-level RSS ingestion.

An RSS source must snapshot one document per feed ENTRY (title, item link,
parsed publication date, readable item-page text), never the whole feed body.
Re-reading the same feed must cost zero item-page fetches, a single unreachable
item must not sink the source, and the per-publisher title deny-list must
deprioritise administrative notices deterministically — with the row still
written and a machine-readable reason recorded (pipeline §4).

No network — ``fetch`` is injected.
"""
from __future__ import annotations

from app.scraping.fetcher import FetchResult
from app.current_affairs import ingestion, sources
from tests.persona_questions._stub import SBStub

_BODY = "A readable current-affairs item body with an examinable claim. " * 10


def _feed(*items: tuple[str, str, str]) -> str:
    """RSS 2.0 feed from ``(title, link, pubDate)`` triples."""
    entries = "".join(
        f"<item><title>{t}</title><link>{l}</link>"
        f"<description>Feed blurb for {t}.</description>"
        f"<pubDate>{p}</pubDate></item>"
        for t, l, p in items
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{entries}</channel></rss>'


_ITEMS = (
    ("Item one", "https://rbi.test/press/1", "Mon, 21 Sep 2026 10:00:00 +0530"),
    ("Item two", "https://rbi.test/press/2", "Mon, 21 Sep 2026 11:00:00 +0530"),
    ("Item three", "https://rbi.test/press/3", "Mon, 21 Sep 2026 12:00:00 +0530"),
)

_FEED_URL = "https://rbi.test/feed.xml"


def _source(**over) -> dict:
    base = {
        "id": "src-rbi",
        "name": "RBI",
        "authority_level": "primary_official",
        "adapter_type": "rss",
        "rss_url": _FEED_URL,
        "official_url": "https://rbi.test/",
        "default_category": "economy",
        "adapter_config": {"publisher": "RBI"},
        "crawl_schedule": {"interval_hours": 24},
        "is_active": True,
        "consecutive_failures": 0,
    }
    base.update(over)
    return base


class _Net:
    """Injected fetch: serves the feed for the feed URL and an item page for
    anything else. Records every call so tests can assert on fetch cost."""

    def __init__(self, feed_xml: str, *, failing: set[str] | None = None):
        self.feed_xml = feed_xml
        self.failing = failing or set()
        self.calls: list[dict] = []

    def __call__(self, url, **kw):
        self.calls.append({"url": url, **kw})
        if url == _FEED_URL:
            return FetchResult(
                ok=True, url=url, status_code=200, final_url=url,
                content_type="application/rss+xml", etag='"feed-1"',
                last_modified="Mon, 21 Sep 2026 12:30:00 GMT",
                content_hash="feed-hash-1", text=self.feed_xml,
            )
        if url in self.failing:
            return FetchResult(ok=False, url=url, status_code=503, error="http_503")
        return FetchResult(
            ok=True, url=url, status_code=200, final_url=url,
            content_type="text/html", etag=f'"{url}"',
            content_hash=f"hash::{url}", text=f"{_BODY} ({url})",
        )

    @property
    def item_urls(self) -> list[str]:
        return [c["url"] for c in self.calls if c["url"] != _FEED_URL]


def _db(documents=None, source=None) -> SBStub:
    return SBStub({
        "current_affairs_sources": [source or _source()],
        "current_affairs_documents": list(documents or []),
    })


def test_three_feed_items_become_three_item_documents():
    sb = _db()
    net = _Net(_feed(*_ITEMS))
    res = ingestion.ingest_source(sb, _source(), fetch=net)

    assert res["status"] == "snapshotted"
    assert res["items_seen"] == 3 and res["items_new"] == 3
    assert res["items_snapshotted"] == 3

    docs = sb.db["current_affairs_documents"]
    assert len(docs) == 3
    # The whole feed body is NEVER snapshotted.
    assert all(not (d["raw_text"] or "").lstrip().startswith("<?xml") for d in docs)

    first = next(d for d in docs if d["title"] == "Item one")
    assert first["source_url"] == "https://rbi.test/press/1"
    assert first["canonical_item_url"] == "https://rbi.test/press/1"
    assert first["published_at"] == "2026-09-21T04:30:00+00:00"   # IST → UTC
    assert first["ingestion_status"] == "snapshotted"
    assert first["document_type"] == "press_release"              # RBI adapter default
    assert first["metadata"]["feed_summary"] == "Feed blurb for Item one."

    # Feed validators are stored on the SOURCE, not on an item row.
    src = sb.db["current_affairs_sources"][0]
    assert src["feed_etag"] == '"feed-1"'
    assert src["feed_last_modified"] == "Mon, 21 Sep 2026 12:30:00 GMT"
    assert src["last_status"] == "snapshotted" and src["consecutive_failures"] == 0


def test_rerunning_the_same_feed_adds_nothing_and_fetches_no_item_page():
    sb = _db()
    feed = _feed(*_ITEMS)
    ingestion.ingest_source(sb, _source(), fetch=_Net(feed))

    net = _Net(feed)
    res = ingestion.ingest_source(sb, _source(), fetch=net)
    assert res["status"] == "duplicate"
    assert res["items_new"] == 0 and res["items_known"] == 3
    assert len(sb.db["current_affairs_documents"]) == 3
    assert net.item_urls == []          # already-seen links skip the page fetch


def test_one_new_entry_costs_exactly_one_item_page_fetch():
    sb = _db()
    ingestion.ingest_source(sb, _source(), fetch=_Net(_feed(*_ITEMS)))

    grown = _ITEMS + (("Item four", "https://rbi.test/press/4", "Tue, 22 Sep 2026 09:00:00 +0530"),)
    net = _Net(_feed(*grown))
    res = ingestion.ingest_source(sb, _source(), fetch=net)

    assert res["items_new"] == 1 and res["items_snapshotted"] == 1
    assert net.item_urls == ["https://rbi.test/press/4"]
    assert len(sb.db["current_affairs_documents"]) == 4


def test_link_canonicalisation_dedupes_across_feed_shifts():
    # The same item re-listed with www / http / a tracking param is not new.
    sb = _db()
    ingestion.ingest_source(sb, _source(), fetch=_Net(_feed(*_ITEMS)))
    shifted = (
        ("Item one", "http://www.rbi.test/press/1?utm_source=rss", "Mon, 21 Sep 2026 10:00:00 +0530"),
        ("Item two", "https://rbi.test/press/2/", "Mon, 21 Sep 2026 11:00:00 +0530"),
    )
    net = _Net(_feed(*shifted))
    res = ingestion.ingest_source(sb, _source(), fetch=net)
    assert res["items_new"] == 0 and net.item_urls == []


def test_item_page_failure_is_recorded_and_the_others_still_land():
    sb = _db()
    net = _Net(_feed(*_ITEMS), failing={"https://rbi.test/press/2"})
    res = ingestion.ingest_source(sb, _source(), fetch=net)

    assert res["status"] == "snapshotted"
    assert res["items_snapshotted"] == 2
    assert res["item_errors"] == [{"link": "https://rbi.test/press/2", "error": "http_503"}]
    titles = sorted(d["title"] for d in sb.db["current_affairs_documents"])
    assert titles == ["Item one", "Item three"]

    # No row was written for the failed item, so the next pass retries it.
    net2 = _Net(_feed(*_ITEMS))
    ingestion.ingest_source(sb, _source(), fetch=net2)
    assert net2.item_urls == ["https://rbi.test/press/2"]


def test_feed_level_304_short_circuits_without_touching_items():
    src = _source(feed_etag='"feed-1"', feed_last_modified="Mon, 21 Sep 2026 12:30:00 GMT")
    sb = _db(source=src)
    captured = {}

    def fetch(url, **kw):
        captured.update(kw)
        return FetchResult(ok=False, url=url, status_code=304, error="not_modified")

    res = ingestion.ingest_source(sb, src, fetch=fetch)
    assert res["status"] == "not_modified"
    assert captured["if_none_match"] == '"feed-1"'
    assert captured["if_modified_since"] == "Mon, 21 Sep 2026 12:30:00 GMT"
    assert sb.db["current_affairs_documents"] == []


def test_unparseable_pub_date_stores_null_never_now():
    sb = _db()
    net = _Net(_feed(("Item one", "https://rbi.test/press/1", "sometime last week")))
    ingestion.ingest_source(sb, _source(), fetch=net)
    assert sb.db["current_affairs_documents"][0]["published_at"] is None


def test_new_items_are_capped_per_pass():
    items = tuple(
        (f"Item {i}", f"https://rbi.test/press/{i}", "Mon, 21 Sep 2026 10:00:00 +0530")
        for i in range(10)
    )
    src = _source(crawl_schedule={"interval_hours": 24, "max_items_per_pass": 4})
    sb = _db(source=src)
    net = _Net(_feed(*items))
    res = ingestion.ingest_source(sb, src, fetch=net)

    assert res["items_new"] == 4 and res["items_capped"] is True
    assert len(net.item_urls) == 4
    assert len(sb.db["current_affairs_documents"]) == 4

    # The remainder is picked up on the next pass — nothing is lost.
    res2 = ingestion.ingest_source(sb, src, fetch=_Net(_feed(*items)))
    assert res2["items_new"] == 4
    assert len(sb.db["current_affairs_documents"]) == 8


def test_capped_pass_clears_the_feed_validators_so_the_remainder_is_not_stranded():
    # A 304 on the next pass would strand the 6 items this pass could not take.
    items = tuple(
        (f"Item {i}", f"https://rbi.test/press/{i}", "Mon, 21 Sep 2026 10:00:00 +0530")
        for i in range(10)
    )
    src = _source(crawl_schedule={"interval_hours": 24, "max_items_per_pass": 4})
    sb = _db(source=src)
    ingestion.ingest_source(sb, src, fetch=_Net(_feed(*items)))
    stored = sb.db["current_affairs_sources"][0]
    assert stored["feed_etag"] is None and stored["feed_last_modified"] is None


def test_item_failure_clears_the_feed_validators_so_the_item_is_retried():
    sb = _db()
    net = _Net(_feed(*_ITEMS), failing={"https://rbi.test/press/2"})
    ingestion.ingest_source(sb, _source(), fetch=net)
    stored = sb.db["current_affairs_sources"][0]
    assert stored["feed_etag"] is None


def test_entries_without_links_are_an_error_not_a_quiet_no_op():
    sb = _db()
    feed = '<?xml version="1.0"?><rss><channel>' \
           '<item><title>Linkless</title></item></channel></rss>'
    net = _Net(feed)
    res = ingestion.ingest_source(sb, _source(), fetch=net)
    assert res["status"] == "error" and res["reason"] == "no_usable_item_links"
    assert res["items_unusable"] == 1
    assert sb.db["current_affairs_documents"] == []


def test_item_link_lookup_failure_is_an_error_not_a_quiet_no_op():
    # An unreadable dedup lookup must not be reported as "nothing new".
    class _BoomSB(SBStub):
        def table(self, name):
            q = super().table(name)
            if name == "current_affairs_documents":
                def _execute():
                    raise RuntimeError("db down")
                q.execute = _execute
            return q

    sb = _BoomSB({"current_affairs_sources": [_source(consecutive_failures=1)],
                  "current_affairs_documents": []})
    net = _Net(_feed(*_ITEMS))
    res = ingestion.ingest_source(sb, _source(consecutive_failures=1), fetch=net)
    assert res["status"] == "error" and res["reason"] == "item_link_lookup_failed"
    assert net.item_urls == []


def test_empty_or_malformed_feed_is_an_error_not_a_silent_success():
    sb = _db()
    fetch = lambda url, **kw: FetchResult(
        ok=True, url=url, status_code=200, content_hash="h", text="<not-xml",
    )
    res = ingestion.ingest_source(sb, _source(consecutive_failures=1), fetch=fetch)
    assert res["status"] == "error" and res["reason"] == "empty_feed"
    assert sb.db["current_affairs_sources"][0]["consecutive_failures"] == 2


# ─── publisher title deny-list (SEBI) ───────────────────────────────────────

_SEBI_FEED_URL = "https://sebi.test/sebirss.xml"


def _sebi_source(**over) -> dict:
    return _source(
        id="src-sebi", name="SEBI", rss_url=_SEBI_FEED_URL,
        official_url="https://sebi.test/", adapter_config={"publisher": "SEBI"},
        **over,
    )


class _SebiNet(_Net):
    def __call__(self, url, **kw):
        self.calls.append({"url": url, **kw})
        if url == _SEBI_FEED_URL:
            return FetchResult(
                ok=True, url=url, status_code=200, final_url=url,
                content_type="application/rss+xml", etag='"sebi-1"',
                content_hash="sebi-feed-1", text=self.feed_xml,
            )
        return FetchResult(
            ok=True, url=url, status_code=200, final_url=url, content_type="text/html",
            content_hash=f"hash::{url}", text=f"{_BODY} ({url})",
        )

    @property
    def item_urls(self):
        return [c["url"] for c in self.calls if c["url"] != _SEBI_FEED_URL]


def test_sebi_denylisted_title_is_deprioritised_with_a_reason_not_dropped():
    src = _sebi_source()
    sb = SBStub({"current_affairs_sources": [src], "current_affairs_documents": []})
    feed = _feed(
        ("Recovery Certificate No. 9169", "https://sebi.test/orders/9169",
         "Mon, 21 Sep 2026 10:00:00 +0530"),
        ("Relaxations in KYC norms for FPIs", "https://sebi.test/legal/kyc",
         "Mon, 21 Sep 2026 11:00:00 +0530"),
    )
    net = _SebiNet(feed)
    res = ingestion.ingest_source(sb, src, fetch=net)

    assert res["items_snapshotted"] == 1 and res["items_deprioritised"] == 1

    docs = {d["title"]: d for d in sb.db["current_affairs_documents"]}
    denied = docs["Recovery Certificate No. 9169"]
    assert denied["ingestion_status"] == "deprioritised"
    assert denied["metadata"]["prefilter_reason"] == "publisher_denylist:recovery certificate"
    # Still a snapshotted row (pipeline §4) — the item is recorded, never dropped.
    assert denied["canonical_item_url"] == "https://sebi.test/orders/9169"

    assert docs["Relaxations in KYC norms for FPIs"]["ingestion_status"] == "snapshotted"
    # The deny-list decision is made from the feed entry: no page fetch is paid for.
    assert net.item_urls == ["https://sebi.test/legal/kyc"]


def test_denylist_patterns_are_case_insensitive_and_publisher_scoped():
    for title in (
        "NOTICE OF ATTACHMENT of bank accounts",
        "Adjudication Order in respect of XYZ Ltd",
        "Settlement Order in the matter of ABC",
        "General Remittance Order dated 2026-09-01",
        "Release Order for attached property",
        "Order for Compliance in the matter of PQR",
    ):
        assert sources.denylisted_title("SEBI", title) is not None, title

    assert sources.denylisted_title("SEBI", "Relaxations in KYC norms for FPIs") is None
    # RBI has no deny-list — the same wording is not filtered for another publisher.
    assert sources.denylisted_title("RBI", "Recovery Certificate No. 9169") is None
    assert sources.denylisted_title(None, "Recovery Certificate No. 9169") is None


def test_prefilter_denylist_precedes_the_length_floor():
    accept, reason = sources.prefilter_document(
        raw_text=_BODY, title="Recovery Certificate No. 1", publisher="SEBI",
    )
    assert accept is False and reason == "publisher_denylist:recovery certificate"
    # Unchanged legacy behaviour when no title/publisher is supplied.
    assert sources.prefilter_document(raw_text=_BODY) == (True, None)


# ─── per-source User-Agent ──────────────────────────────────────────────────

_PIB_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def test_source_user_agent_is_passed_to_every_fetch():
    src = _source(adapter_config={"publisher": "PIB", "user_agent": _PIB_UA})
    sb = _db(source=src)
    net = _Net(_feed(*_ITEMS))
    ingestion.ingest_source(sb, src, fetch=net)
    assert net.calls and all(c["user_agent"] == _PIB_UA for c in net.calls)


def test_source_without_an_override_sends_no_user_agent_override():
    sb = _db()
    net = _Net(_feed(*_ITEMS))
    ingestion.ingest_source(sb, _source(), fetch=net)
    assert all(c["user_agent"] is None for c in net.calls)


def test_user_agent_of_reads_adapter_config():
    assert sources.user_agent_of({"adapter_config": {"user_agent": _PIB_UA}}) == _PIB_UA
    assert sources.user_agent_of({"adapter_config": {"user_agent": "  "}}) is None
    assert sources.user_agent_of({"adapter_config": {}}) is None
    assert sources.user_agent_of({}) is None


# ─── non-RSS adapters keep the whole-body snapshot ──────────────────────────

def test_html_source_still_snapshots_the_whole_body():
    src = _source(adapter_type="html", crawl_url="https://rbi.test/page", rss_url=None)
    sb = _db(source=src)
    fetch = lambda url, **kw: FetchResult(
        ok=True, url=url, status_code=200, final_url=url, content_type="text/html",
        etag='"p1"', content_hash="page-hash", text=_BODY,
    )
    res = ingestion.ingest_source(sb, src, fetch=fetch)
    assert res["status"] == "snapshotted"
    doc = sb.db["current_affairs_documents"][0]
    assert doc["title"] is None and doc.get("canonical_item_url") is None
