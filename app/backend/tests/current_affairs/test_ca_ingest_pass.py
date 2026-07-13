"""ca:ingest pass tests (GQR-G5b): cadence gate + enqueue-on-snapshot + aggregation.

``ingest_source`` (the pure per-source unit) is tested in test_ingestion.py; here it is
stubbed so the tests exercise the PASS logic — which sources are due, the hand-off to the
generation queue, and the result aggregation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.current_affairs import ingestion
from tests.persona_questions._stub import SBStub, _RpcCall

_NOW = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)


class IngestSB(SBStub):
    def __init__(self, db=None):
        super().__init__(db)
        self.enqueued: list = []

    def rpc(self, name, params=None):
        if name == "ca_enqueue_generation_job":
            self.enqueued.append((params or {}).get("p_document_id"))
            return _RpcCall(f"job-{(params or {}).get('p_document_id')}")
        return super().rpc(name, params)


def _src(sid, *, last_fetch_at=None, interval_hours=24):
    return {"id": sid, "is_active": True, "crawl_schedule": {"interval_hours": interval_hours},
            "last_fetch_at": last_fetch_at}


def test_is_due():
    assert ingestion._is_due(_src("s", last_fetch_at=None), _NOW) is True
    assert ingestion._is_due(_src("s", last_fetch_at=(_NOW - timedelta(hours=1)).isoformat()), _NOW) is False
    assert ingestion._is_due(_src("s", last_fetch_at=(_NOW - timedelta(hours=25)).isoformat()), _NOW) is True
    # malformed schedule / timestamp fall back to due.
    assert ingestion._is_due({"id": "s", "crawl_schedule": {"interval_hours": "x"}, "last_fetch_at": "bad"}, _NOW) is True


def _doc(did, status="snapshotted"):
    return {"id": did, "ingestion_status": status}


def test_pass_skips_not_due_crawls_due_and_reconciles_enqueue(monkeypatch):
    db = {
        "current_affairs_sources": [
            _src("s1", last_fetch_at=None),                                   # due → snapshot
            _src("s2", last_fetch_at=(_NOW - timedelta(hours=1)).isoformat()),  # not due → skipped
            _src("s3", last_fetch_at=(_NOW - timedelta(hours=25)).isoformat()),  # due → duplicate
        ],
        # d1 snapshotted with no job → reconciliation enqueues it; d0 already has a job.
        "current_affairs_documents": [_doc("d1"), _doc("d0")],
        "current_affairs_generation_jobs": [
            {"document_id": "d0", "job_kind": "ca_generation", "status": "pending"}],
    }
    outcomes = {
        "s1": {"status": "snapshotted", "source_id": "s1", "document_id": "d1"},
        "s3": {"status": "duplicate", "source_id": "s3", "document_id": "dX"},
    }
    monkeypatch.setattr(ingestion, "ingest_source",
                        lambda sb, source, **kw: outcomes[source["id"]])
    sb = IngestSB(db)
    out = ingestion.run_ingest_pass(sb, now=_NOW)
    assert out["checked"] == 2                # s2 skipped (not due)
    assert out["snapshotted"] == 1 and out["duplicate"] == 1
    assert out["status"] == "ok"
    # Durable reconciliation enqueues the un-jobbed snapshotted doc, and only it.
    assert out["enqueued"] == 1 and sb.enqueued == ["d1"]


def test_reconcile_backfills_preexisting_snapshotted_without_job(monkeypatch):
    # No sources due, but a pre-existing G2 snapshotted doc has no job → still enqueued.
    db = {
        "current_affairs_sources": [],
        "current_affairs_documents": [_doc("old-1"), _doc("old-2"), _doc("dep", status="deprioritised")],
        "current_affairs_generation_jobs": [],
    }
    sb = IngestSB(db)
    out = ingestion.run_ingest_pass(sb, now=_NOW)
    assert out["checked"] == 0
    assert sorted(sb.enqueued) == ["old-1", "old-2"]   # deprioritised doc is NOT enqueued
    assert out["enqueued"] == 2 and out["status"] == "ok"


def test_per_source_exception_is_isolated(monkeypatch):
    db = {"current_affairs_sources": [_src("bad", last_fetch_at=None), _src("good", last_fetch_at=None)],
          "current_affairs_documents": [], "current_affairs_generation_jobs": []}

    def _ingest(sb, source, **kw):
        if source["id"] == "bad":
            raise RuntimeError("boom")
        return {"status": "snapshotted", "source_id": "good", "document_id": "dg"}

    monkeypatch.setattr(ingestion, "ingest_source", _ingest)
    out = ingestion.run_ingest_pass(IngestSB(db), now=_NOW)
    assert out["checked"] == 2 and out["error"] == 1 and out["snapshotted"] == 1  # good still ran
    assert out["status"] == "partial"                                              # error → partial


def test_pass_covers_more_than_one_page(monkeypatch):
    # 250 active due sources must ALL be crawled (no silent 100/200-row cap).
    srcs = [_src(f"s{i:04d}", last_fetch_at=None) for i in range(250)]
    db = {"current_affairs_sources": srcs, "current_affairs_documents": [], "current_affairs_generation_jobs": []}
    monkeypatch.setattr(ingestion, "ingest_source",
                        lambda sb, source, **kw: {"status": "not_modified", "source_id": source["id"]})
    out = ingestion.run_ingest_pass(IngestSB(db), now=_NOW)
    assert out["checked"] == 250


def test_non_dict_crawl_schedule_is_tolerated(monkeypatch):
    # crawl_schedule is unconstrained JSONB — a list value must not abort the pass.
    db = {"current_affairs_sources": [{"id": "s", "is_active": True, "crawl_schedule": ["oops"], "last_fetch_at": None}],
          "current_affairs_documents": [], "current_affairs_generation_jobs": []}
    monkeypatch.setattr(ingestion, "ingest_source", lambda *a, **k: {"status": "not_modified"})
    out = ingestion.run_ingest_pass(IngestSB(db), now=_NOW)
    assert out["checked"] == 1 and out["status"] == "ok"


def test_source_query_failure_is_reported_as_failed(monkeypatch):
    class BoomSB(IngestSB):
        def table(self, name):
            if name == "current_affairs_sources":
                raise RuntimeError("db down")
            return super().table(name)

    out = ingestion.run_ingest_pass(BoomSB({"current_affairs_documents": [], "current_affairs_generation_jobs": []}), now=_NOW)
    assert out["source_query_failed"] == 1 and out["status"] == "failed"


def test_enqueue_failure_is_counted_and_partial(monkeypatch):
    class EnqFailSB(IngestSB):
        def rpc(self, name, params=None):
            if name == "ca_enqueue_generation_job":
                raise RuntimeError("enqueue down")
            return super().rpc(name, params)

    db = {"current_affairs_sources": [], "current_affairs_documents": [_doc("d1")],
          "current_affairs_generation_jobs": []}
    out = ingestion.run_ingest_pass(EnqFailSB(db), now=_NOW)
    assert out["enqueue_failed"] == 1 and out["enqueued"] == 0 and out["status"] == "partial"
