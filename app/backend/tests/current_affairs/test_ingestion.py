"""GQR-G2 — current-affairs ingestion primitive.

``ingest_source`` must: resolve the fetch URL by adapter, pass prior-snapshot
ETag/Last-Modified as conditional-fetch validators, short-circuit on 304,
content-hash dedup, snapshot an immutable document, pre-filter thin bodies, and
keep source health current on every path. No network — ``fetch`` is injected.
"""
from __future__ import annotations

from app.scraping.fetcher import FetchResult
from app.current_affairs import ingestion, sources
from tests.persona_questions._stub import SBStub

_LONG_BODY = "x" * 500  # comfortably above the examinable-length floor


def _source(**over) -> dict:
    base = {
        "id": "src-pib",
        "name": "PIB",
        "authority_level": "primary_official",
        "adapter_type": "rss",
        "rss_url": "https://pib.gov.in/feed.xml",
        "official_url": "https://pib.gov.in/",
        "default_category": "national",
        "adapter_config": {"publisher": "PIB"},
        "is_active": True,
        "consecutive_failures": 0,
    }
    base.update(over)
    return base


def _ok(text=_LONG_BODY, content_hash="hash-1", **over) -> FetchResult:
    kw = dict(
        ok=True, url="https://pib.gov.in/feed.xml", status_code=200,
        final_url="https://pib.gov.in/feed.xml", content_type="application/rss+xml",
        etag='"abc"', last_modified="Wed, 01 Jul 2026 00:00:00 GMT",
        content_hash=content_hash, text=text,
    )
    kw.update(over)
    return FetchResult(**kw)


def _db(documents=None) -> SBStub:
    return SBStub({
        "current_affairs_sources": [_source()],
        "current_affairs_documents": list(documents or []),
    })


class _DocInsertRaises(SBStub):
    """SBStub whose document-insert raises a given exception (dedup select still works)."""
    def __init__(self, db, exc):
        super().__init__(db)
        self._exc = exc

    def table(self, name):
        q = super().table(name)
        if name == "current_affairs_documents":
            orig = q.execute
            def _execute():
                if q._pending_insert is not None:
                    raise self._exc
                return orig()
            q.execute = _execute
        return q


def test_unique_violation_is_a_benign_duplicate():
    # A concurrent run won the content-hash race (23505) → duplicate, health stays green.
    sb = _DocInsertRaises({"current_affairs_documents": []},
                          Exception("duplicate key value violates unique constraint (23505)"))
    res = ingestion.ingest_source(sb, _source(consecutive_failures=1), fetch=lambda u, **k: _ok())
    assert res["status"] == "duplicate" and res["document_id"] is None
    assert sb.db["current_affairs_sources"] == []  # (no sources seeded) — health write is best-effort


def test_infra_write_failure_is_a_real_error_not_a_duplicate():
    # Any NON-unique exception is a genuine write failure — must NOT be masked as duplicate.
    db = {"current_affairs_sources": [_source(consecutive_failures=2)], "current_affairs_documents": []}
    sb = _DocInsertRaises(db, Exception("connection reset by peer"))
    res = ingestion.ingest_source(sb, _source(consecutive_failures=2), fetch=lambda u, **k: _ok())
    assert res["status"] == "error" and res["reason"] == "write_failed"
    src = sb.db["current_affairs_sources"][0]
    assert src["last_status"] == "error" and src["consecutive_failures"] == 3  # streak bumped


def test_snapshots_new_document():
    sb = _db()
    fetch = lambda url, **kw: _ok()
    res = ingestion.ingest_source(sb, _source(), fetch=fetch)
    assert res["status"] == "snapshotted"
    docs = sb.db["current_affairs_documents"]
    assert len(docs) == 1
    d = docs[0]
    assert d["source_id"] == "src-pib"
    assert d["content_hash"] == "hash-1"
    assert d["etag"] == '"abc"'
    assert d["ingestion_status"] == "snapshotted"
    assert d["document_type"] == "press_release"  # PIB adapter default
    # health updated to success
    src = sb.db["current_affairs_sources"][0]
    assert src["last_status"] == "snapshotted"
    assert src["consecutive_failures"] == 0
    assert src["last_success_at"] is not None


def test_dedup_same_content_hash():
    existing = {"id": "doc-old", "source_id": "src-pib", "content_hash": "hash-1",
                "etag": '"abc"', "last_modified": None, "fetched_at": "2026-07-01T00:00:00Z"}
    sb = _db([existing])
    fetch = lambda url, **kw: _ok(content_hash="hash-1")
    res = ingestion.ingest_source(sb, _source(), fetch=fetch)
    assert res["status"] == "duplicate"
    assert res["document_id"] == "doc-old"
    # no new snapshot written
    assert len(sb.db["current_affairs_documents"]) == 1


def test_not_modified_304_short_circuits():
    existing = {"id": "doc-old", "source_id": "src-pib", "content_hash": "hash-0",
                "etag": '"abc"', "last_modified": "Wed, 01 Jul 2026 00:00:00 GMT",
                "fetched_at": "2026-07-01T00:00:00Z"}
    sb = _db([existing])
    captured = {}

    def fetch(url, **kw):
        captured.update(kw)
        return FetchResult(ok=False, url=url, status_code=304, error="not_modified")

    res = ingestion.ingest_source(sb, _source(), fetch=fetch)
    assert res["status"] == "not_modified"
    # prior snapshot's validators were sent as conditional-fetch headers
    assert captured["if_none_match"] == '"abc"'
    assert captured["if_modified_since"] == "Wed, 01 Jul 2026 00:00:00 GMT"
    # no new document, health green
    assert len(sb.db["current_affairs_documents"]) == 1
    assert sb.db["current_affairs_sources"][0]["last_status"] == "not_modified"


def test_fetch_error_bumps_consecutive_failures():
    sb = _db()
    sb.db["current_affairs_sources"][0]["consecutive_failures"] = 2
    fetch = lambda url, **kw: FetchResult(ok=False, url=url, status_code=503, error="http_503")
    res = ingestion.ingest_source(sb, _source(consecutive_failures=2), fetch=fetch)
    assert res["status"] == "error"
    assert res["reason"] == "http_503"
    src = sb.db["current_affairs_sources"][0]
    assert src["consecutive_failures"] == 3
    assert src["last_error"] == "http_503"
    assert len(sb.db["current_affairs_documents"]) == 0


def test_prefilter_deprioritises_thin_body():
    sb = _db()
    fetch = lambda url, **kw: _ok(text="too short", content_hash="hash-thin")
    res = ingestion.ingest_source(sb, _source(), fetch=fetch)
    assert res["status"] == "deprioritised"
    d = sb.db["current_affairs_documents"][0]
    assert d["ingestion_status"] == "deprioritised"
    assert d["metadata"]["prefilter_reason"] == "below_min_examinable_length"


def test_no_url_configured_skips_and_flags_health():
    src = _source(adapter_type="rss", rss_url=None, crawl_url=None, official_url=None)
    sb = SBStub({"current_affairs_sources": [src], "current_affairs_documents": []})
    called = {"n": 0}

    def fetch(url, **kw):
        called["n"] += 1
        return _ok()

    res = ingestion.ingest_source(sb, src, fetch=fetch)
    assert res["status"] == "skipped"
    assert res["reason"] == "no_fetch_url"
    assert called["n"] == 0  # never fetched
    assert sb.db["current_affairs_sources"][0]["last_status"] == "no_url"


def test_inactive_source_skipped():
    src = _source(is_active=False)
    sb = SBStub({"current_affairs_sources": [src], "current_affairs_documents": []})
    fetch = lambda url, **kw: _ok()
    res = ingestion.ingest_source(sb, src, fetch=fetch)
    assert res["status"] == "skipped"
    assert res["reason"] == "inactive"


def test_resolve_fetch_url_by_adapter():
    assert sources.resolve_fetch_url(_source(adapter_type="rss")) == "https://pib.gov.in/feed.xml"
    assert sources.resolve_fetch_url(
        {"adapter_type": "api", "api_url": "https://x/api"}
    ) == "https://x/api"
    assert sources.resolve_fetch_url(
        {"adapter_type": "pdf", "pdf_bulletin_url": "https://x/b.pdf"}
    ) == "https://x/b.pdf"
    assert sources.resolve_fetch_url(
        {"adapter_type": "html", "official_url": "https://x/"}
    ) == "https://x/"


def test_prefilter_empty_body():
    accept, reason = sources.prefilter_document(raw_text="   ")
    assert accept is False and reason == "empty_body"
