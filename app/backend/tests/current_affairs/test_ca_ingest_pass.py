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


def test_pass_skips_not_due_ingests_due_and_enqueues_on_snapshot(monkeypatch):
    db = {"current_affairs_sources": [
        _src("s1", last_fetch_at=None),                                   # due → snapshot
        _src("s2", last_fetch_at=(_NOW - timedelta(hours=1)).isoformat()),  # not due → skipped
        _src("s3", last_fetch_at=(_NOW - timedelta(hours=25)).isoformat()),  # due → duplicate
    ]}
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
    assert out["enqueued"] == 1               # only the snapshot enqueues
    assert sb.enqueued == ["d1"]              # duplicate does NOT enqueue


def test_pass_is_empty_when_no_sources_due(monkeypatch):
    db = {"current_affairs_sources": [
        _src("s2", last_fetch_at=(_NOW - timedelta(hours=1)).isoformat())]}
    monkeypatch.setattr(ingestion, "ingest_source", lambda *a, **k: {"status": "snapshotted"})
    out = ingestion.run_ingest_pass(IngestSB(db), now=_NOW)
    assert out["checked"] == 0 and out["enqueued"] == 0
