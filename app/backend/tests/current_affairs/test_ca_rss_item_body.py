"""CA-RSS-02 — SEBI path allow-list, embedded-PDF body, entities, pubDate.

The CA-RSS-01 first pass over SEBI produced 30 documents of which one was
useful: the rest were /enforcement/orders/... paperwork, and the one press
release stored 300-odd characters of breadcrumb because SEBI embeds the real
document as a PDF. These tests pin the four fixes:

* an item outside the publisher's URL-path allow-list is retired WITHOUT
  paying for its page fetch, with a machine-readable reason (pipeline §4);
* an allow-listed page whose readable text is chrome pulls its body from the
  embedded PDF, via the same pypdf path ``doc:text_extract`` uses;
* a body that stays thin writes NO row, so the item is retried rather than
  burning its canonical-link slot in the unique index;
* entities are decoded, and Indian-publisher date shapes parse (naive = IST).

No network — ``fetch`` is injected.
"""
from __future__ import annotations

from app.scraping.fetcher import FetchResult, strip_html
from app.current_affairs import ingestion, sources
from tests.persona_questions._stub import SBStub

_SEBI_FEED_URL = "https://sebi.test/sebirss.xml"
_PRESS = "https://sebi.test/media-and-notifications/press-releases/pr-2026-41"
_ORDER = "https://sebi.test/enforcement/orders/sep-2026/appeal-9169"

# Comfortably over the 400-char minimum-body floor.
_REAL_BODY = "SEBI has revised the framework for foreign portfolio investors. " * 16
# Breadcrumb-only chrome, like the live SEBI item pages (290-600 chars).
_CHROME = "Home » Media » Press Releases » Print Share " * 6


def _feed(*items: tuple[str, str, str]) -> str:
    entries = "".join(
        f"<item><title>{t}</title><link>{l}</link>"
        f"<description>Blurb for {t}.</description><pubDate>{p}</pubDate></item>"
        for t, l, p in items
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{entries}</channel></rss>'


def _sebi_source(**over) -> dict:
    base = {
        "id": "src-sebi",
        "name": "Securities and Exchange Board of India",
        "authority_level": "primary_official",
        "adapter_type": "rss",
        "rss_url": _SEBI_FEED_URL,
        "official_url": "https://sebi.test/",
        "default_category": "economy",
        "adapter_config": {"publisher": "SEBI"},
        "crawl_schedule": {"interval_hours": 24},
        "is_active": True,
        "consecutive_failures": 0,
    }
    base.update(over)
    return base


class _Net:
    """Injected fetch serving a feed, item pages, and PDFs.

    ``pages`` maps an item URL to its raw HTML; ``pdfs`` maps a PDF URL to the
    text pypdf would extract (or to an ``FetchResult`` for failure cases).
    """

    def __init__(self, feed_xml: str, *, pages=None, pdfs=None, feed_url=_SEBI_FEED_URL):
        self.feed_xml = feed_xml
        self.feed_url = feed_url
        self.pages = pages or {}
        self.pdfs = pdfs or {}
        self.calls: list[dict] = []

    def __call__(self, url, **kw):
        self.calls.append({"url": url, **kw})
        if url == self.feed_url:
            return FetchResult(
                ok=True, url=url, status_code=200, final_url=url,
                content_type="application/rss+xml", etag='"sebi-1"',
                content_hash="sebi-feed-1", text=self.feed_xml,
            )
        if kw.get("adapter_type") == "pdf":
            configured = self.pdfs.get(url)
            if isinstance(configured, FetchResult):
                return configured
            if configured is None:
                return FetchResult(ok=False, url=url, status_code=404, error="http_404")
            return FetchResult(
                ok=True, url=url, status_code=200, final_url=url,
                content_type="application/pdf", content_hash=f"pdfhash::{url}",
                text=configured, raw_bytes=b"%PDF-1.4",
            )
        html = self.pages.get(url)
        if html is None:
            return FetchResult(ok=False, url=url, status_code=404, error="http_404")
        return FetchResult(
            ok=True, url=url, status_code=200, final_url=url,
            content_type="text/html; charset=utf-8", content_hash=f"pagehash::{url}",
            text=strip_html(html), raw_bytes=html.encode("utf-8"),
        )

    @property
    def fetched(self) -> list[str]:
        return [c["url"] for c in self.calls if c["url"] != self.feed_url]

    @property
    def pdf_calls(self) -> list[dict]:
        return [c for c in self.calls if c.get("adapter_type") == "pdf"]


def _db(source=None) -> SBStub:
    return SBStub({
        "current_affairs_sources": [source or _sebi_source()],
        "current_affairs_documents": [],
    })


def _page(body: str, *, pdf_href: str | None = None, viewer: str | None = None) -> str:
    embed = ""
    if pdf_href:
        embed = f'<iframe src="{pdf_href}" width="100%"></iframe>'
    if viewer:
        embed = f'<iframe src="/viewer.html?file={viewer}"></iframe>'
    return f"<html><head><title>T</title></head><body>{embed}<div>{body}</div></body></html>"


# ─── 1. publisher URL-path allow-list ───────────────────────────────────────

def test_path_excluded_item_is_retired_without_any_page_fetch():
    sb = _db()
    net = _Net(_feed(
        ("Appeal No. 9169 filed by A Person", _ORDER, "21 Sep, 2026"),
        ("SEBI revises FPI framework", _PRESS, "21 Sep, 2026"),
    ), pages={_PRESS: _page(_REAL_BODY)})

    res = ingestion.ingest_source(sb, _sebi_source(), fetch=net)
    assert res["items_snapshotted"] == 1 and res["items_deprioritised"] == 1

    docs = {d["canonical_item_url"]: d for d in sb.db["current_affairs_documents"]}
    order = docs[_ORDER]
    assert order["ingestion_status"] == "deprioritised"
    assert order["metadata"]["prefilter_reason"] == "publisher_path_excluded:/enforcement/orders"
    # Evidence is still recorded (pipeline §4) — the item is never silently dropped.
    assert order["title"] == "Appeal No. 9169 filed by A Person"

    # The decision is made from the feed entry: the excluded page is never fetched.
    assert net.fetched == [_PRESS]
    assert docs[_PRESS]["ingestion_status"] == "snapshotted"


def test_path_excluded_rows_never_reach_the_generation_queue():
    sb = _db()
    net = _Net(_feed(("Appeal No. 1 filed by X", _ORDER, "21 Sep, 2026")))
    ingestion.ingest_source(sb, _sebi_source(), fetch=net)
    # _reconcile_pending_generation only enqueues 'snapshotted' documents.
    assert all(d["ingestion_status"] == "deprioritised"
               for d in sb.db["current_affairs_documents"])


def test_every_allowlisted_section_is_accepted():
    for path in (
        "/media-and-notifications/press-releases/x",
        "/legal/circulars/x",
        "/legal/master-circulars/x",
        "/legal/regulations/x",
        "/reports-and-statistics/reports/x",
    ):
        assert sources.path_allowed("SEBI", f"https://sebi.test{path}") is True, path
    for path in ("/enforcement/orders/x", "/filings/reports/x", "/legal/orders/x", "/"):
        assert sources.path_allowed("SEBI", f"https://sebi.test{path}") is False, path


def test_publishers_without_an_allowlist_are_unfiltered():
    # RBI and PIB page structure is unverified — absence of config must not deny.
    for publisher in ("RBI", "PIB", "UNKNOWN", None):
        assert sources.path_allowed(publisher, "https://rbi.test/anything/at/all") is True
        assert sources.path_excluded_reason(publisher, "https://rbi.test/x/y") is None


def test_path_section_reports_the_first_two_segments():
    assert sources.path_section("https://sebi.test/enforcement/orders/sep/1") == "/enforcement/orders"
    assert sources.path_section("https://sebi.test/legal") == "/legal"
    assert sources.path_section("https://sebi.test/") == "/"


def test_new_sebi_title_denylist_patterns():
    assert sources.denylisted_title("SEBI", "General Remittance Advice dated 01-09-2026")
    assert sources.denylisted_title("SEBI", "Order of AA under the RTI Act, 2005") is not None
    # "Appeal No." AND "filed by" together — either alone is not enough.
    assert sources.denylisted_title(
        "SEBI", "Appeal No. 4321 filed by Mr X") == "appeal no.+filed by"
    assert sources.denylisted_title("SEBI", "Securities Appellate Tribunal appeal no. 12") is None
    assert sources.denylisted_title("SEBI", "Report filed by the committee") is None


# ─── 2. embedded-PDF body extraction ────────────────────────────────────────

def test_chrome_page_with_iframe_pdf_stores_the_pdf_text():
    pdf_url = "https://sebi.test/sites/default/files/pr-2026-41.pdf"
    sb = _db()
    net = _Net(
        _feed(("SEBI revises FPI framework", _PRESS, "21 Sep, 2026")),
        pages={_PRESS: _page(_CHROME, pdf_href=pdf_url)},
        pdfs={pdf_url: _REAL_BODY},
    )
    res = ingestion.ingest_source(sb, _sebi_source(), fetch=net)
    assert res["items_snapshotted"] == 1

    doc = sb.db["current_affairs_documents"][0]
    assert doc["ingestion_status"] == "snapshotted"
    assert doc["metadata"]["body_source"] == "pdf"
    assert doc["metadata"]["pdf_url"] == pdf_url
    assert doc["metadata"]["extracted_chars"] == len(doc["raw_text"])
    # Page title is prepended — the PDF itself usually omits it.
    assert doc["raw_text"].startswith("SEBI revises FPI framework")
    assert "foreign portfolio investors" in doc["raw_text"]
    # Dedup keys on the body actually stored, not on the chrome page.
    assert doc["content_hash"] == f"pdfhash::{pdf_url}"

    # The PDF fetch carried the source's identity and the size cap.
    call = net.pdf_calls[0]
    assert call["max_bytes"] == 10 * 1024 * 1024


def test_viewer_file_param_is_resolved():
    pdf_url = "https://sebi.test/files/circular.pdf"
    sb = _db()
    net = _Net(
        _feed(("Circular on KYC", "https://sebi.test/legal/circulars/c-1", "21 Sep, 2026")),
        pages={"https://sebi.test/legal/circulars/c-1":
               _page(_CHROME, viewer="https%3A%2F%2Fsebi.test%2Ffiles%2Fcircular.pdf")},
        pdfs={pdf_url: _REAL_BODY},
    )
    ingestion.ingest_source(sb, _sebi_source(), fetch=net)
    doc = sb.db["current_affairs_documents"][0]
    assert doc["metadata"]["body_source"] == "pdf"
    assert doc["metadata"]["pdf_url"] == pdf_url


def test_substantial_html_page_is_not_replaced_by_a_linked_pdf():
    pdf_url = "https://sebi.test/files/annexure.pdf"
    sb = _db()
    net = _Net(
        _feed(("SEBI revises FPI framework", _PRESS, "21 Sep, 2026")),
        pages={_PRESS: _page(_REAL_BODY, pdf_href=pdf_url)},
        pdfs={pdf_url: "annexure text"},
    )
    ingestion.ingest_source(sb, _sebi_source(), fetch=net)
    doc = sb.db["current_affairs_documents"][0]
    assert doc["metadata"]["body_source"] == "html"
    assert net.pdf_calls == []          # no PDF fetch paid for


def test_oversized_pdf_on_a_chrome_page_is_a_per_item_error_with_no_row():
    pdf_url = "https://sebi.test/files/huge.pdf"
    sb = _db()
    net = _Net(
        _feed(("SEBI revises FPI framework", _PRESS, "21 Sep, 2026")),
        pages={_PRESS: _page(_CHROME, pdf_href=pdf_url)},
        pdfs={pdf_url: FetchResult(ok=False, url=pdf_url, error="pdf_too_large")},
    )
    res = ingestion.ingest_source(sb, _sebi_source(), fetch=net)
    assert res["item_errors"] == [{"link": _PRESS, "error": "pdf_too_large"}]
    assert sb.db["current_affairs_documents"] == []


def test_pdf_failure_keeps_a_substantial_html_body_and_records_the_error():
    # The PDF is tried because the page links one, but the HTML already carries a
    # real body, so a PDF hiccup must not throw the item away.
    pdf_url = "https://sebi.test/files/x.pdf"
    page_body = "Home » Media » " + ("SEBI board approved the proposal. " * 12)
    sb = _db(_sebi_source(crawl_schedule={"interval_hours": 24,
                                          "pdf_fallback_below_chars": 100000}))
    net = _Net(
        _feed(("SEBI revises FPI framework", _PRESS, "21 Sep, 2026")),
        pages={_PRESS: _page(page_body, pdf_href=pdf_url)},
        pdfs={pdf_url: FetchResult(ok=False, url=pdf_url, error="http_503")},
    )
    ingestion.ingest_source(sb, _sebi_source(crawl_schedule={
        "interval_hours": 24, "pdf_fallback_below_chars": 100000}), fetch=net)
    doc = sb.db["current_affairs_documents"][0]
    assert doc["metadata"]["body_source"] == "html"
    assert doc["metadata"]["pdf_error"] == "http_503"
    assert doc["ingestion_status"] == "snapshotted"


def test_thin_page_with_no_pdf_writes_no_row_and_is_retried_next_pass():
    sb = _db()
    feed = _feed(("SEBI revises FPI framework", _PRESS, "21 Sep, 2026"))
    net = _Net(feed, pages={_PRESS: _page("Home » Media » Print")})

    res = ingestion.ingest_source(sb, _sebi_source(), fetch=net)
    assert res["item_errors"] == [{"link": _PRESS, "error": "thin_body"}]
    assert sb.db["current_affairs_documents"] == []

    # No row means the canonical-link slot is free, so the next pass retries it —
    # and now that the page carries a PDF, it lands.
    pdf_url = "https://sebi.test/files/pr.pdf"
    net2 = _Net(feed, pages={_PRESS: _page(_CHROME, pdf_href=pdf_url)},
                pdfs={pdf_url: _REAL_BODY})
    ingestion.ingest_source(sb, _sebi_source(), fetch=net2)
    assert len(sb.db["current_affairs_documents"]) == 1
    assert sb.db["current_affairs_documents"][0]["metadata"]["body_source"] == "pdf"


def test_off_host_pdf_is_not_treated_as_this_source_s_evidence():
    html = _page(_CHROME, pdf_href="https://cdn.elsewhere.test/doc.pdf")
    assert sources.embedded_pdf_url(html, page_url=_PRESS) is None


def test_non_pdf_iframe_is_ignored():
    html = _page(_CHROME, pdf_href="https://sebi.test/embed/player.html")
    assert sources.embedded_pdf_url(html, page_url=_PRESS) is None


def test_relative_pdf_href_is_resolved_against_the_page():
    html = _page(_CHROME, pdf_href="/sites/files/a.pdf")
    assert sources.embedded_pdf_url(html, page_url=_PRESS) == "https://sebi.test/sites/files/a.pdf"


def test_body_thresholds_are_configurable_per_source():
    src = _sebi_source(crawl_schedule={
        "interval_hours": 24, "min_body_chars": 10,
        "pdf_fallback_below_chars": 100000, "max_pdf_bytes": 1234,
    })
    pdf_url = "https://sebi.test/files/a.pdf"
    sb = _db(src)
    net = _Net(
        _feed(("SEBI revises FPI framework", _PRESS, "21 Sep, 2026")),
        pages={_PRESS: _page(_CHROME, pdf_href=pdf_url)},
        pdfs={pdf_url: "short but allowed"},
    )
    ingestion.ingest_source(sb, src, fetch=net)
    assert net.pdf_calls[0]["max_bytes"] == 1234
    assert sb.db["current_affairs_documents"][0]["metadata"]["body_source"] == "pdf"


# ─── 3. HTML entity unescape ────────────────────────────────────────────────

def test_strip_html_decodes_named_and_numeric_entities():
    out = strip_html("<p>Home &raquo; Media &amp; Notifications&nbsp;&#8377;500 crore</p>")
    assert out == "Home » Media & Notifications ₹500 crore"


def test_strip_html_still_drops_scripts_styles_and_tags():
    out = strip_html(
        "<style>.a{color:red}</style><script>var x='&lt;b&gt;';</script>"
        "<div>Real <b>body</b> text</div>"
    )
    assert out == "Real body text"


def test_entities_reach_the_snapshot_decoded():
    sb = _db()
    body = "SEBI &amp; the FPI framework &raquo; revised. " * 14
    net = _Net(_feed(("SEBI revises FPI framework", _PRESS, "21 Sep, 2026")),
               pages={_PRESS: _page(body)})
    ingestion.ingest_source(sb, _sebi_source(), fetch=net)
    text = sb.db["current_affairs_documents"][0]["raw_text"]
    assert "&amp;" not in text and "&raquo;" not in text
    assert "SEBI & the FPI framework »" in text


# ─── 4. pubDate parsing ─────────────────────────────────────────────────────

_IST_MIDNIGHT = "2026-09-20T18:30:00+00:00"   # 21 Sep 2026 00:00 IST


def test_supported_pub_date_variants():
    cases = {
        "Mon, 21 Sep 2026 10:00:00 +0530": "2026-09-21T04:30:00+00:00",  # RFC 2822
        "2026-09-21T10:00:00Z": "2026-09-21T10:00:00+00:00",             # ISO 8601
        "21 Sep, 2026": _IST_MIDNIGHT,
        "21 Sep,2026": _IST_MIDNIGHT,
        "21 Sept, 2026": _IST_MIDNIGHT,
        "21 September, 2026": _IST_MIDNIGHT,
        "Sep 21, 2026": _IST_MIDNIGHT,
        "September 21, 2026": _IST_MIDNIGHT,
        "21-Sep-2026": _IST_MIDNIGHT,
        "21-09-2026": _IST_MIDNIGHT,
        "21/09/2026": _IST_MIDNIGHT,
        "21 Sep, 2026 IST": _IST_MIDNIGHT,
        "21 Sep, 2026 +0530": _IST_MIDNIGHT,
        "21 Sep, 2026 14:30": "2026-09-21T09:00:00+00:00",
        "21 Sep, 2026 14:30:45": "2026-09-21T09:00:45+00:00",
        "Sep 21, 2026 02:30 PM": "2026-09-21T09:00:00+00:00",
    }
    for raw, expected in cases.items():
        assert sources.parse_published_at(raw) == expected, raw


def test_naive_dates_are_read_as_ist_not_utc():
    # 21 Sep 2026 00:00 IST is 20 Sep 18:30 UTC. Reading it as UTC would have
    # dated every Indian item 5.5 hours early.
    assert sources.parse_published_at("21 Sep, 2026") == _IST_MIDNIGHT
    assert sources.parse_published_at("21 Sep, 2026 UTC") == "2026-09-21T00:00:00+00:00"


def test_unparseable_pub_date_is_null_and_the_raw_value_is_kept():
    assert sources.parse_published_at("sometime last week") is None
    assert sources.parse_published_at("") is None
    assert sources.parse_published_at(None) is None

    sb = _db()
    net = _Net(_feed(("SEBI revises FPI framework", _PRESS, "whenever it was")),
               pages={_PRESS: _page(_REAL_BODY)})
    ingestion.ingest_source(sb, _sebi_source(), fetch=net)
    doc = sb.db["current_affairs_documents"][0]
    assert doc["published_at"] is None                       # never now()
    assert doc["metadata"]["raw_pub_date"] == "whenever it was"


def test_raw_pub_date_is_kept_even_when_parsing_succeeds():
    sb = _db()
    net = _Net(_feed(("SEBI revises FPI framework", _PRESS, "21 Sep, 2026")),
               pages={_PRESS: _page(_REAL_BODY)})
    ingestion.ingest_source(sb, _sebi_source(), fetch=net)
    doc = sb.db["current_affairs_documents"][0]
    assert doc["published_at"] == _IST_MIDNIGHT
    assert doc["metadata"]["raw_pub_date"] == "21 Sep, 2026"


def test_raw_pub_date_is_kept_on_a_path_excluded_row_too():
    sb = _db()
    net = _Net(_feed(("Appeal No. 1 filed by X", _ORDER, "21 Sep, 2026")))
    ingestion.ingest_source(sb, _sebi_source(), fetch=net)
    doc = sb.db["current_affairs_documents"][0]
    assert doc["metadata"]["raw_pub_date"] == "21 Sep, 2026"
    assert doc["published_at"] == _IST_MIDNIGHT
