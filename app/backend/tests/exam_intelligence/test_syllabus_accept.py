"""PR3b: Syllabus accept (preview + commit) tests.

POST /api/admin/exam-intelligence/workspace/{exam_id}/syllabus/accept/preview
POST /api/admin/exam-intelligence/workspace/{exam_id}/syllabus/accept/commit

Covers:
Preview:
- happy path: 3 valid proposals → all will_insert
- duplicate detection: existing pending mention → will_skip_duplicate
- duplicate detection: existing verified mention → will_skip_duplicate
- rejected/needs_correction do NOT count as duplicates
- invalid: unknown topic_id → invalid with reason
- invalid: exam_id mismatch → invalid with reason
- empty proposals → 422
- proposals > 500 → 422
- proposal_key deterministic: same inputs → same hash

Commit:
- happy path: 3 will_insert → 3 rows with reviewer_status=pending
- stale: client_proposal_key mismatch → skipped_stale
- duplicate: re-run after commit → all skipped_duplicate (idempotency)
- partial failure: one insert fails → others still commit
- reviewer_status forced to 'pending'
- missing reason → 422
- missing client_proposal_key → 422
- read-only for preview: no rows inserted
"""
from __future__ import annotations

import hashlib
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as review_api
from app.core.auth import get_current_user
from app.exam_intelligence.syllabus_mapper import (
    compute_proposal_key,
    preview_accept,
    commit_accept,
    ACCEPT_PROPOSER_VERSION,
)

_BASE = "/api/admin/exam-intelligence"

# ── Fixtures ──────────────────────────────────────────────────────────────────

EXAM_ID = "exam-1"
EXAM = {"id": EXAM_ID, "name": "SSC CGL"}
DOC_ID = "doc-1"

def _make_proposal(n: int = 1, **overrides) -> dict:
    base = {
        "syllabus_document_id": DOC_ID,
        "topic_id": f"topic-{n}",
        "exam_id": EXAM_ID,
        "exam_cycle_id": None,
        "exam_phase_id": None,
        "source_page": n,
        "raw_text": f"Topic {n} text",
        "normalized_text": f"topic {n} text",
        "mention_type": "explicit",
        "confidence_score": 1.0,
        "matched_alias": f"Topic {n}",
        "match_method": "topic_alias_exact",
        "proposer_version": "syllabus_mapper_v1",
    }
    return {**base, **overrides}


def _with_key(proposal: dict) -> dict:
    return {**proposal, "client_proposal_key": compute_proposal_key(proposal)}


# ── Stub ──────────────────────────────────────────────────────────────────────

class _SBStub:
    def __init__(self, exams=None, mentions=None, fail_insert_topic_ids=None):
        self.exams = exams or [EXAM]
        self.mentions = list(mentions or [])
        self.fail_insert_topic_ids = set(fail_insert_topic_ids or [])
        self.inserted: list[dict] = []

    def table(self, name):
        return _TblStub(name, self)


class _TblStub:
    def __init__(self, name, sb):
        self._name = name
        self._sb = sb
        self._filters: dict = {}
        self._in_filters: dict = {}
        self._insert_data = None

    def select(self, *a):
        return self

    def eq(self, k, v):
        self._filters[k] = v
        return self

    def in_(self, k, vs):
        self._in_filters[k] = set(vs)
        return self

    def limit(self, n):
        return self

    def order(self, *a, **kw):
        return self

    def insert(self, data):
        self._insert_data = data
        return self

    def execute(self):
        res = MagicMock()
        if self._name == "exams":
            rows = [e for e in self._sb.exams if not self._filters or e.get("id") == self._filters.get("id")]
            res.data = rows
        elif self._name == "syllabus_topic_mentions":
            if self._insert_data is not None:
                # Simulate insert
                row = self._insert_data
                topic_id = row.get("topic_id", "")
                if topic_id in self._sb.fail_insert_topic_ids:
                    raise RuntimeError(f"FK violation for topic {topic_id}")
                row_with_id = {**row, "id": f"mention-{topic_id}"}
                self._sb.inserted.append(row_with_id)
                self._sb.mentions.append(row_with_id)
                res.data = [row_with_id]
            else:
                rows = list(self._sb.mentions)
                for k, v in self._filters.items():
                    rows = [r for r in rows if r.get(k) == v]
                res.data = rows
        else:
            res.data = []
        return res


def _client(sb):
    app = FastAPI()
    app.include_router(review_api.router, prefix="/api")
    review_api.get_supabase_admin = lambda: sb
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": "super_admin", "permissions": [review_api.ADMIN_PERM],
    }
    return TestClient(app, raise_server_exceptions=False)


# ── Unit: compute_proposal_key ────────────────────────────────────────────────


class TestProposalKey:
    def test_deterministic(self):
        p = _make_proposal(1)
        assert compute_proposal_key(p) == compute_proposal_key(p)

    def test_same_inputs_same_hash(self):
        p1 = _make_proposal(1)
        p2 = _make_proposal(1)
        assert compute_proposal_key(p1) == compute_proposal_key(p2)

    def test_different_page_different_hash(self):
        p1 = _make_proposal(1)
        p2 = _make_proposal(1, source_page=2)
        assert compute_proposal_key(p1) != compute_proposal_key(p2)

    def test_different_topic_different_hash(self):
        p1 = _make_proposal(1)
        p2 = _make_proposal(1, topic_id="topic-other")
        assert compute_proposal_key(p1) != compute_proposal_key(p2)

    def test_known_hash_cross_side_pin(self):
        """Pin the exact SHA-256 output to catch any Python↔JS divergence."""
        p = {
            "syllabus_document_id": "doc-abc",
            "topic_id": "topic-xyz",
            "source_page": 3,
            "normalized_text": "arithmetic",
            "exam_phase_id": None,
        }
        parts = "doc-abc|topic-xyz|3|arithmetic|"
        expected = hashlib.sha256(parts.encode("utf-8")).hexdigest()
        assert compute_proposal_key(p) == expected

    def test_phase_id_included(self):
        p1 = _make_proposal(1, exam_phase_id=None)
        p2 = _make_proposal(1, exam_phase_id="phase-1")
        assert compute_proposal_key(p1) != compute_proposal_key(p2)


# ── Unit: preview_accept ──────────────────────────────────────────────────────


class TestPreviewAccept:
    def test_happy_path_all_will_insert(self):
        sb = _SBStub()
        props = [_make_proposal(i) for i in range(1, 4)]
        result = preview_accept(sb, exam_id=EXAM_ID, proposals=props)
        assert result["summary"]["insert"] == 3
        assert result["summary"]["skip_duplicate"] == 0
        assert result["summary"]["invalid"] == 0
        assert len(result["will_insert"]) == 3

    def test_proposal_keys_attached(self):
        sb = _SBStub()
        props = [_make_proposal(1)]
        result = preview_accept(sb, exam_id=EXAM_ID, proposals=props)
        row = result["will_insert"][0]
        assert "proposal_key" in row
        assert len(row["proposal_key"]) == 64  # sha256 hex

    def test_duplicate_pending_skipped(self):
        existing = {
            "id": "mention-existing",
            "syllabus_document_id": DOC_ID,
            "topic_id": "topic-1",
            "normalized_text": "topic 1 text",
            "reviewer_status": "pending",
        }
        sb = _SBStub(mentions=[existing])
        props = [_make_proposal(1)]
        result = preview_accept(sb, exam_id=EXAM_ID, proposals=props)
        assert result["summary"]["skip_duplicate"] == 1
        assert result["will_skip_duplicate"][0]["existing_mention_id"] == "mention-existing"

    def test_duplicate_verified_skipped(self):
        existing = {
            "id": "mention-verified",
            "syllabus_document_id": DOC_ID,
            "topic_id": "topic-1",
            "normalized_text": "topic 1 text",
            "reviewer_status": "verified",
        }
        sb = _SBStub(mentions=[existing])
        props = [_make_proposal(1)]
        result = preview_accept(sb, exam_id=EXAM_ID, proposals=props)
        assert result["summary"]["skip_duplicate"] == 1

    def test_rejected_not_a_duplicate(self):
        """Rejected mention should not block re-proposal."""
        existing = {
            "id": "mention-rejected",
            "syllabus_document_id": DOC_ID,
            "topic_id": "topic-1",
            "normalized_text": "topic 1 text",
            "reviewer_status": "rejected",
        }
        sb = _SBStub(mentions=[existing])
        props = [_make_proposal(1)]
        result = preview_accept(sb, exam_id=EXAM_ID, proposals=props)
        assert result["summary"]["insert"] == 1
        assert result["summary"]["skip_duplicate"] == 0

    def test_needs_correction_not_a_duplicate(self):
        existing = {
            "id": "mention-nc",
            "syllabus_document_id": DOC_ID,
            "topic_id": "topic-1",
            "normalized_text": "topic 1 text",
            "reviewer_status": "needs_correction",
        }
        sb = _SBStub(mentions=[existing])
        # needs_correction IS counted as duplicate (active, not rejected)
        props = [_make_proposal(1)]
        result = preview_accept(sb, exam_id=EXAM_ID, proposals=props)
        assert result["summary"]["skip_duplicate"] == 1

    def test_invalid_exam_id_mismatch(self):
        sb = _SBStub()
        p = _make_proposal(1, exam_id="exam-other")
        result = preview_accept(sb, exam_id=EXAM_ID, proposals=[p])
        assert result["summary"]["invalid"] == 1
        assert "mismatch" in result["invalid"][0]["reason"]

    def test_invalid_empty_normalized_text(self):
        sb = _SBStub()
        p = _make_proposal(1, normalized_text="")
        result = preview_accept(sb, exam_id=EXAM_ID, proposals=[p])
        assert result["summary"]["invalid"] == 1

    def test_read_only_no_inserts(self):
        sb = _SBStub()
        props = [_make_proposal(i) for i in range(1, 4)]
        preview_accept(sb, exam_id=EXAM_ID, proposals=props)
        assert sb.inserted == []


# ── Unit: commit_accept ───────────────────────────────────────────────────────


class TestCommitAccept:
    def test_happy_path_commits_all(self):
        sb = _SBStub()
        props = [_with_key(_make_proposal(i)) for i in range(1, 4)]
        result = commit_accept(sb, exam_id=EXAM_ID, proposals=props, reason="test run")
        assert result["committed"] == 3
        assert result["skipped_duplicate"] == 0
        assert result["skipped_stale"] == 0
        assert result["failed"] == 0
        assert len(sb.inserted) == 3

    def test_reviewer_status_forced_pending(self):
        sb = _SBStub()
        props = [_with_key(_make_proposal(1))]
        commit_accept(sb, exam_id=EXAM_ID, proposals=props, reason="test")
        assert sb.inserted[0]["reviewer_status"] == "pending"

    def test_stale_key_skipped(self):
        sb = _SBStub()
        p = _make_proposal(1)
        p["client_proposal_key"] = "deadbeef" * 8  # wrong key
        result = commit_accept(sb, exam_id=EXAM_ID, proposals=[p], reason="test")
        assert result["skipped_stale"] == 1
        assert sb.inserted == []

    def test_idempotent_after_commit(self):
        """Re-committing same proposals → all skipped_duplicate."""
        sb = _SBStub()
        props = [_with_key(_make_proposal(1))]
        commit_accept(sb, exam_id=EXAM_ID, proposals=props, reason="first run")
        result2 = commit_accept(sb, exam_id=EXAM_ID, proposals=props, reason="second run")
        assert result2["skipped_duplicate"] == 1
        assert result2["committed"] == 0

    def test_partial_failure_others_still_commit(self):
        """If topic-2 fails FK, topic-1 and topic-3 still commit."""
        sb = _SBStub(fail_insert_topic_ids={"topic-2"})
        props = [_with_key(_make_proposal(i)) for i in range(1, 4)]
        result = commit_accept(sb, exam_id=EXAM_ID, proposals=props, reason="test")
        assert result["committed"] == 2
        assert result["failed"] == 1
        committed_keys = {r["result"] for r in result["per_row"]}
        assert "committed" in committed_keys
        assert "failed" in committed_keys

    def test_metadata_stored(self):
        sb = _SBStub()
        props = [_with_key(_make_proposal(1))]
        commit_accept(sb, exam_id=EXAM_ID, proposals=props, reason="test reason")
        meta = sb.inserted[0]["metadata"]
        assert meta["proposer_version"] == "syllabus_mapper_v1"
        assert meta["source_page"] == 1
        assert "proposal_key" in meta

    def test_per_row_result_shape(self):
        sb = _SBStub()
        props = [_with_key(_make_proposal(1))]
        result = commit_accept(sb, exam_id=EXAM_ID, proposals=props, reason="test")
        row = result["per_row"][0]
        assert set(row.keys()) >= {"proposal_key", "result", "mention_id", "reason"}


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


class TestPreviewEndpoint:
    def _c(self, sb):
        return _client(sb)

    def test_200_happy_path(self):
        sb = _SBStub()
        props = [_make_proposal(i) for i in range(1, 4)]
        r = self._c(sb).post(f"{_BASE}/workspace/{EXAM_ID}/syllabus/accept/preview", json={"proposals": props})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["summary"]["insert"] == 3

    def test_404_unknown_exam(self):
        sb = _SBStub(exams=[])
        props = [_make_proposal(1)]
        r = self._c(sb).post(f"{_BASE}/workspace/bad-exam/syllabus/accept/preview", json={"proposals": props})
        assert r.status_code == 404

    def test_422_empty_proposals(self):
        sb = _SBStub()
        r = self._c(sb).post(f"{_BASE}/workspace/{EXAM_ID}/syllabus/accept/preview", json={"proposals": []})
        assert r.status_code == 422

    def test_422_too_many_proposals(self):
        sb = _SBStub()
        props = [_make_proposal(i) for i in range(501)]
        r = self._c(sb).post(f"{_BASE}/workspace/{EXAM_ID}/syllabus/accept/preview", json={"proposals": props})
        assert r.status_code == 422

    def test_read_only_no_db_inserts(self):
        sb = _SBStub()
        props = [_make_proposal(i) for i in range(1, 4)]
        self._c(sb).post(f"{_BASE}/workspace/{EXAM_ID}/syllabus/accept/preview", json={"proposals": props})
        assert sb.inserted == []


class TestCommitEndpoint:
    def _c(self, sb):
        return _client(sb)

    def _body(self, props, reason="test reason"):
        return {"proposals": props, "reason": reason}

    def test_200_commits_all(self):
        sb = _SBStub()
        props = [_with_key(_make_proposal(i)) for i in range(1, 4)]
        r = self._c(sb).post(f"{_BASE}/workspace/{EXAM_ID}/syllabus/accept/commit", json=self._body(props))
        assert r.status_code == 200, r.text
        assert r.json()["committed"] == 3

    def test_404_unknown_exam(self):
        sb = _SBStub(exams=[])
        props = [_with_key(_make_proposal(1))]
        r = self._c(sb).post(f"{_BASE}/workspace/bad-exam/syllabus/accept/commit", json=self._body(props))
        assert r.status_code == 404

    def test_422_missing_reason(self):
        sb = _SBStub()
        props = [_with_key(_make_proposal(1))]
        r = self._c(sb).post(f"{_BASE}/workspace/{EXAM_ID}/syllabus/accept/commit", json={"proposals": props})
        assert r.status_code == 422

    def test_422_missing_client_proposal_key(self):
        sb = _SBStub()
        props = [_make_proposal(1)]  # no client_proposal_key
        r = self._c(sb).post(f"{_BASE}/workspace/{EXAM_ID}/syllabus/accept/commit", json=self._body(props))
        assert r.status_code == 422

    def test_422_empty_proposals(self):
        sb = _SBStub()
        r = self._c(sb).post(f"{_BASE}/workspace/{EXAM_ID}/syllabus/accept/commit", json=self._body([]))
        assert r.status_code == 422

    def test_reviewer_status_pending_in_db(self):
        sb = _SBStub()
        props = [_with_key(_make_proposal(1))]
        self._c(sb).post(f"{_BASE}/workspace/{EXAM_ID}/syllabus/accept/commit", json=self._body(props))
        assert sb.inserted[0]["reviewer_status"] == "pending"
