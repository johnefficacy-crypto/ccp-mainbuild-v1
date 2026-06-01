"""Tests for the DB-backed token store in pyq_bulk_import.

Covers
------
- _store_token inserts row with expires_at = created_at + ttl
- _load_token returns row when token+paper match and not expired
- _load_token returns None when token expired
- _load_token returns None when consumed_at is set
- _load_token returns None when paper_id mismatch
- _consume_token sets consumed_at; subsequent _load_token returns None
- preflight → commit happy path through DB store
- commit with expired token returns 404
- commit with unknown token returns 404
- commit with already-consumed token returns 404
- two parallel preflights against same paper get distinct tokens
- token survives a simulated "process restart" (drop in-memory _STORE, refetch from DB)
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from app.exam_intelligence import pyq_bulk_import as _bi
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub
from tests.persona_questions._stub import SBStub

_BASE = "/api/admin/exam-intelligence-cms"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _fresh_sb() -> TaxSBStub:
    return TaxSBStub({
        "pyq_papers": [{"id": "paper-1", "exam_id": "exam-1"}],
        "pyq_questions": [],
        "pyq_options": [],
        "admin_audit_logs": [],
        "pyq_import_tokens": [],
    })


def _client(sb: TaxSBStub) -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-99", "role": "super_admin", "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def _make_csv(rows: list[dict]) -> bytes:
    cols = ["question_number", "question_text", "option_a", "option_b",
            "option_c", "option_d", "correct_option", "question_type",
            "observed_difficulty"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    return buf.getvalue().encode("utf-8")


def _clean_row(n: int, **kwargs) -> dict:
    return {
        "question_number": n,
        "question_text": f"What is question number {n}?",
        "option_a": "Alpha", "option_b": "Beta",
        "option_c": "Gamma", "option_d": "Delta",
        "correct_option": "A",
        "question_type": "mcq",
        "observed_difficulty": "medium",
        **kwargs,
    }


def _preflight(client: TestClient, rows: list[dict], *, paper_id: str = "paper-1") -> dict:
    body = _make_csv(rows)
    r = client.post(
        f"{_BASE}/pyq-papers/{paper_id}/bulk-import/preflight",
        content=body,
        headers={"content-type": "text/csv"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _future(seconds: int = 3600) -> str:
    return _iso(datetime.now(timezone.utc) + timedelta(seconds=seconds))


def _past(seconds: int = 1) -> str:
    return _iso(datetime.now(timezone.utc) - timedelta(seconds=seconds))


# ── Unit tests for store helpers ─────────────────────────────────────────────


class TestStoreToken:
    def test_inserts_row_with_correct_fields(self):
        sb = SBStub({})
        _bi._store_token(sb, token="tok1", paper_id="p1",
                         summary={"ok": 1}, rows={"parsed": [], "preview": []},
                         ttl_seconds=600, created_by="user-1")
        rows = sb.db.get("pyq_import_tokens", [])
        assert len(rows) == 1
        row = rows[0]
        assert row["token"] == "tok1"
        assert row["paper_id"] == "p1"
        assert row["created_by"] == "user-1"
        assert row["consumed_at"] is None

    def test_expires_at_is_roughly_created_at_plus_ttl(self):
        sb = SBStub({})
        before = datetime.now(timezone.utc)
        _bi._store_token(sb, token="tok2", paper_id="p1",
                         summary={}, rows={}, ttl_seconds=3600)
        after = datetime.now(timezone.utc)
        row = sb.db["pyq_import_tokens"][0]
        expires = datetime.fromisoformat(row["expires_at"])
        created = datetime.fromisoformat(row["created_at"])
        delta = (expires - created).total_seconds()
        assert 3599 <= delta <= 3601

    def test_created_by_defaults_to_none(self):
        sb = SBStub({})
        _bi._store_token(sb, token="tok3", paper_id="p1", summary={}, rows={})
        row = sb.db["pyq_import_tokens"][0]
        assert row["created_by"] is None


class TestLoadToken:
    def _insert(self, sb: SBStub, *, token="t", paper_id="p1",
                expires_at=None, consumed_at=None):
        row = {
            "token": token,
            "paper_id": paper_id,
            "preflight_summary": {},
            "preflight_rows": {"parsed": [], "preview": []},
            "created_by": None,
            "created_at": _iso(datetime.now(timezone.utc)),
            "expires_at": expires_at or _future(),
            "consumed_at": consumed_at,
        }
        sb.db.setdefault("pyq_import_tokens", []).append(row)

    def test_returns_row_when_valid(self):
        sb = SBStub({})
        self._insert(sb, token="abc", paper_id="paper-1")
        result = _bi._load_token(sb, token="abc", paper_id="paper-1")
        assert result is not None
        assert result["token"] == "abc"

    def test_returns_none_when_expired(self):
        sb = SBStub({})
        self._insert(sb, token="abc", paper_id="paper-1", expires_at=_past(60))
        result = _bi._load_token(sb, token="abc", paper_id="paper-1")
        assert result is None

    def test_returns_none_when_consumed(self):
        sb = SBStub({})
        self._insert(sb, token="abc", paper_id="paper-1",
                     consumed_at=_iso(datetime.now(timezone.utc)))
        result = _bi._load_token(sb, token="abc", paper_id="paper-1")
        assert result is None

    def test_returns_none_when_paper_id_mismatch(self):
        sb = SBStub({})
        self._insert(sb, token="abc", paper_id="paper-X")
        result = _bi._load_token(sb, token="abc", paper_id="paper-1")
        assert result is None

    def test_returns_none_when_token_unknown(self):
        sb = SBStub({})
        result = _bi._load_token(sb, token="no-such-token", paper_id="paper-1")
        assert result is None


class TestConsumeToken:
    def test_sets_consumed_at(self):
        sb = SBStub({})
        sb.db["pyq_import_tokens"] = [{
            "token": "tok",
            "paper_id": "p1",
            "preflight_summary": {},
            "preflight_rows": {},
            "consumed_at": None,
            "expires_at": _future(),
            "created_at": _iso(datetime.now(timezone.utc)),
        }]
        _bi._consume_token(sb, token="tok")
        row = sb.db["pyq_import_tokens"][0]
        assert row["consumed_at"] is not None

    def test_subsequent_load_returns_none(self):
        sb = SBStub({})
        sb.db["pyq_import_tokens"] = [{
            "token": "tok",
            "paper_id": "p1",
            "preflight_summary": {},
            "preflight_rows": {"parsed": [], "preview": []},
            "consumed_at": None,
            "expires_at": _future(),
            "created_at": _iso(datetime.now(timezone.utc)),
        }]
        _bi._consume_token(sb, token="tok")
        result = _bi._load_token(sb, token="tok", paper_id="p1")
        assert result is None


# ── Integration tests through the HTTP layer ──────────────────────────────────


class TestPreflightCommitIntegration:
    def test_happy_path_through_db_store(self):
        sb = _fresh_sb()
        client = _client(sb)
        rows = [_clean_row(i) for i in range(1, 4)]
        pf = _preflight(client, rows)
        token = pf["import_token"]
        assert token

        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": token, "reason": "db store test"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["committed"] == 3

    def test_token_stored_in_db_table(self):
        sb = _fresh_sb()
        client = _client(sb)
        pf = _preflight(client, [_clean_row(1)])
        token = pf["import_token"]
        stored = sb.db.get("pyq_import_tokens", [])
        assert any(r["token"] == token for r in stored)

    def test_token_consumed_after_commit(self):
        sb = _fresh_sb()
        client = _client(sb)
        pf = _preflight(client, [_clean_row(1)])
        token = pf["import_token"]

        client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": token, "reason": "consume test"},
        )
        row = next(r for r in sb.db["pyq_import_tokens"] if r["token"] == token)
        assert row["consumed_at"] is not None

    def test_commit_with_consumed_token_returns_404(self):
        sb = _fresh_sb()
        client = _client(sb)
        pf = _preflight(client, [_clean_row(1)])
        token = pf["import_token"]

        # First commit succeeds
        r1 = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": token, "reason": "first"},
        )
        assert r1.status_code == 200

        # Second commit with same token → already consumed → 404
        r2 = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": token, "reason": "replay"},
        )
        assert r2.status_code == 404

    def test_commit_with_unknown_token_returns_404(self):
        sb = _fresh_sb()
        client = _client(sb)
        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": "deadbeef" * 4, "reason": "unknown"},
        )
        assert r.status_code == 404

    def test_commit_with_expired_token_returns_404(self):
        sb = _fresh_sb()
        # Manually insert an expired token
        sb.db["pyq_import_tokens"] = [{
            "token": "expired-token",
            "paper_id": "paper-1",
            "preflight_summary": {"ok": 1},
            "preflight_rows": {
                "parsed": [{"question_number": 1, "question_text": "Q?",
                            "options": {"A": "a", "B": "b", "C": "c", "D": "d"},
                            "correct_option": "A", "question_type": "mcq",
                            "observed_difficulty": None,
                            "_normalized_question_hash": "h1"}],
                "preview": [{"row": 1, "status": "ok", "messages": [],
                             "question_number": 1, "question_text": "Q?",
                             "question_type": "mcq", "correct_option": "A",
                             "observed_difficulty": None}],
            },
            "created_by": None,
            "created_at": _past(7200),
            "expires_at": _past(3600),  # expired 1 hour ago
            "consumed_at": None,
        }]
        client = _client(sb)
        r = client.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": "expired-token", "reason": "expired test"},
        )
        assert r.status_code == 404

    def test_two_parallel_preflights_get_distinct_tokens(self):
        sb = _fresh_sb()
        client = _client(sb)
        pf1 = _preflight(client, [_clean_row(1)])
        pf2 = _preflight(client, [_clean_row(2)])
        assert pf1["import_token"] != pf2["import_token"]
        assert len(sb.db["pyq_import_tokens"]) == 2

    def test_token_survives_process_restart(self):
        """Token stored in DB is accessible after in-memory state is gone."""
        sb = _fresh_sb()
        client = _client(sb)
        pf = _preflight(client, [_clean_row(1)])
        token = pf["import_token"]

        # Simulate process restart: the DB stub (sb) still has the token
        # but any in-memory dict is gone. A new client using the same sb
        # (representing a fresh worker with the same DB) can commit.
        client2 = _client(sb)
        r = client2.post(
            f"{_BASE}/pyq-papers/paper-1/bulk-import/commit",
            json={"import_token": token, "reason": "after restart"},
        )
        assert r.status_code == 200
        assert r.json()["committed"] == 1
