"""Tests for PYQ → Mock Bank projection service (migration 183).

Covers:
  - compute_content_hash (pure unit)
  - _check_question_eligibility (all disqualifying paths)
  - preview_paper_projection (ineligible, eligible-new, eligible-update, eligible-no-change)
  - sync_paper_projection (RPC happy-path, error path, unknown-question-id guard)
  - get_paper_projection_status (counts, stale detection)
  - API endpoint permission gates (403, 404, 200)
  - MCQ exactly-one-correct validation fix in mock_questions.create_question
"""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin.pyq_mock_projection import (
    _check_question_eligibility,
    compute_content_hash,
    get_paper_projection_status,
    preview_paper_projection,
    sync_paper_projection,
)
from app.admin.mock_questions import create_question
from app.api import admin_mocks as admin_mocks_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub

# ─── Fixtures ─────────────────────────────────────────────────────────────────

PAPER_ID  = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
EXAM_ID   = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
Q_ID      = "11111111-1111-1111-1111-111111111111"
TOPIC_ID  = "tttttttt-tttt-tttt-tttt-tttttttttttt"
ACTOR_ID  = "actor-001"


def _paper(trust_status: str = "verified") -> dict:
    return {"id": PAPER_ID, "exam_id": EXAM_ID, "year": 2023, "trust_status": trust_status}


def _question(
    reviewer_status: str = "verified",
    question_type: str = "mcq",
    question_text: str = "What is X?",
) -> dict:
    return {
        "id": Q_ID,
        "pyq_paper_id": PAPER_ID,
        "question_text": question_text,
        "question_type": question_type,
        "reviewer_status": reviewer_status,
        "correct_option_id": None,
        "observed_difficulty": "medium",
        "expected_solve_time_sec": 60,
    }


def _options(
    n: int = 4,
    correct_idx: int = 0,
    reviewer_status: str = "verified",
) -> list[dict]:
    return [
        {
            "id": f"opt-{i}",
            "question_id": Q_ID,
            "option_text": f"Option {chr(65 + i)}",
            "is_correct": i == correct_idx,
            "reviewer_status": reviewer_status,
        }
        for i in range(n)
    ]


def _primary_tag(reviewer_status: str = "verified") -> list[dict]:
    return [
        {
            "id": "tag-1",
            "question_id": Q_ID,
            "topic_id": TOPIC_ID,
            "tag_role": "primary",
            "reviewer_status": reviewer_status,
        }
    ]


def _seed_sb(
    paper: dict | None = None,
    questions: list[dict] | None = None,
    options: list[dict] | None = None,
    tags: list[dict] | None = None,
    projections: list[dict] | None = None,
) -> SBStub:
    sb = SBStub()
    sb.db["pyq_papers"] = [paper or _paper()]
    sb.db["pyq_questions"] = questions if questions is not None else [_question()]
    sb.db["pyq_options"] = options if options is not None else _options()
    sb.db["pyq_question_topic_tags"] = tags if tags is not None else _primary_tag()
    sb.db["pyq_mock_question_projections"] = projections or []
    return sb


# ─── Unit: compute_content_hash ───────────────────────────────────────────────

class TestComputeContentHash:
    def test_deterministic(self):
        q = _question()
        opts = _options()
        h1 = compute_content_hash(q, opts)
        h2 = compute_content_hash(q, opts)
        assert h1 == h2

    def test_changes_when_question_text_changes(self):
        opts = _options()
        h1 = compute_content_hash(_question(question_text="A"), opts)
        h2 = compute_content_hash(_question(question_text="B"), opts)
        assert h1 != h2

    def test_changes_when_option_text_changes(self):
        q = _question()
        opts_a = _options()
        opts_b = [dict(o, option_text="ZZZ") if i == 0 else o for i, o in enumerate(_options())]
        assert compute_content_hash(q, opts_a) != compute_content_hash(q, opts_b)

    def test_changes_when_correct_option_changes(self):
        q = _question()
        opts_0 = _options(correct_idx=0)
        opts_1 = _options(correct_idx=1)
        assert compute_content_hash(q, opts_0) != compute_content_hash(q, opts_1)

    def test_case_insensitive_question_text(self):
        opts = _options()
        h1 = compute_content_hash(_question(question_text="What IS X?"), opts)
        h2 = compute_content_hash(_question(question_text="what is x?"), opts)
        assert h1 == h2


# ─── Unit: _check_question_eligibility ────────────────────────────────────────

class TestCheckEligibility:
    def _eligible_call(self, **overrides):
        paper = {**_paper(), **overrides.get("paper", {})}
        q     = {**_question(), **overrides.get("question", {})}
        opts  = overrides.get("options", _options())
        tags  = overrides.get("tags", _primary_tag())
        return _check_question_eligibility(paper, q, opts, tags)

    def test_fully_eligible(self):
        eligible, reason = self._eligible_call()
        assert eligible is True
        assert reason == "eligible"

    def test_paper_not_verified(self):
        eligible, reason = self._eligible_call(paper={"trust_status": "pending"})
        assert eligible is False
        assert "paper_not_verified" in reason

    def test_question_not_verified(self):
        eligible, reason = self._eligible_call(question={"reviewer_status": "draft"})
        assert eligible is False
        assert "question_not_verified" in reason

    def test_not_mcq(self):
        eligible, reason = self._eligible_call(question={"question_type": "msq"})
        assert eligible is False
        assert "not_mcq" in reason

    def test_empty_question_text(self):
        eligible, reason = self._eligible_call(question={"question_text": "  "})
        assert eligible is False
        assert "empty_question_text" in reason

    def test_too_few_verified_options(self):
        # Only 1 verified option
        opts = [
            {**_options()[0], "reviewer_status": "verified"},
            {**_options()[1], "reviewer_status": "draft"},
            {**_options()[2], "reviewer_status": "draft"},
        ]
        eligible, reason = self._eligible_call(options=opts)
        assert eligible is False
        assert "too_few_verified_options" in reason

    def test_zero_correct_options(self):
        opts = [dict(o, is_correct=False) for o in _options()]
        eligible, reason = self._eligible_call(options=opts)
        assert eligible is False
        assert "not_exactly_one_correct" in reason

    def test_two_correct_options(self):
        opts = _options()
        opts[0] = dict(opts[0], is_correct=True)
        opts[1] = dict(opts[1], is_correct=True)
        eligible, reason = self._eligible_call(options=opts)
        assert eligible is False
        assert "not_exactly_one_correct" in reason

    def test_unverified_correct_blocks_eligibility(self):
        """Unverified option with is_correct=True must not count; no verified correct → blocked."""
        opts = [
            {"id": "opt-0", "question_id": Q_ID, "option_text": "A", "is_correct": False, "reviewer_status": "verified"},
            {"id": "opt-1", "question_id": Q_ID, "option_text": "B", "is_correct": False, "reviewer_status": "verified"},
            {"id": "opt-2", "question_id": Q_ID, "option_text": "C", "is_correct": True,  "reviewer_status": "draft"},
        ]
        eligible, reason = self._eligible_call(options=opts)
        assert eligible is False
        assert "not_exactly_one_correct" in reason

    def test_empty_verified_option_text_blocked(self):
        """Verified option with blank text must block projection."""
        opts = [
            {"id": "opt-0", "question_id": Q_ID, "option_text": "  ", "is_correct": True,  "reviewer_status": "verified"},
            {"id": "opt-1", "question_id": Q_ID, "option_text": "B",  "is_correct": False, "reviewer_status": "verified"},
        ]
        eligible, reason = self._eligible_call(options=opts)
        assert eligible is False
        assert "empty_verified_option_text" in reason

    def test_correct_option_id_mismatch_blocked(self):
        """correct_option_id pointing to a non-correct verified option must block."""
        opts = _options(correct_idx=0)  # opt-0 is the verified correct
        q = {**_question(), "correct_option_id": "opt-3"}  # pointer disagrees
        eligible, reason = self._eligible_call(question=q, options=opts)
        assert eligible is False
        assert "correct_option_id_mismatch" in reason

    def test_correct_option_id_matching_passes(self):
        """correct_option_id that matches the verified correct option must pass."""
        opts = _options(correct_idx=0)  # opt-0 is correct
        q = {**_question(), "correct_option_id": "opt-0"}
        eligible, reason = self._eligible_call(question=q, options=opts)
        assert eligible is True

    def test_correct_option_id_null_skips_check(self):
        """correct_option_id = None must not trigger the mismatch check."""
        opts = _options(correct_idx=1)
        q = {**_question(), "correct_option_id": None}
        eligible, reason = self._eligible_call(question=q, options=opts)
        assert eligible is True

    def test_no_primary_tag(self):
        eligible, reason = self._eligible_call(tags=[])
        assert eligible is False
        assert "not_exactly_one_verified_primary_tag" in reason

    def test_unverified_primary_tag(self):
        tags = [dict(_primary_tag()[0], reviewer_status="draft")]
        eligible, reason = self._eligible_call(tags=tags)
        assert eligible is False
        assert "not_exactly_one_verified_primary_tag" in reason

    def test_secondary_tag_does_not_count_as_primary(self):
        tags = [dict(_primary_tag()[0], tag_role="secondary")]
        eligible, reason = self._eligible_call(tags=tags)
        assert eligible is False
        assert "not_exactly_one_verified_primary_tag" in reason


# ─── preview_paper_projection ────────────────────────────────────────────────

class TestPreviewPaperProjection:
    def test_paper_not_found_raises_lookup(self):
        sb = SBStub()
        with pytest.raises(LookupError):
            preview_paper_projection(sb, PAPER_ID)

    def test_empty_paper(self):
        sb = _seed_sb(questions=[])
        result = preview_paper_projection(sb, PAPER_ID)
        assert result["total"] == 0
        assert result["eligible_count"] == 0

    def test_eligible_new_question(self):
        sb = _seed_sb()
        result = preview_paper_projection(sb, PAPER_ID)
        assert result["eligible_count"] == 1
        assert result["would_create_count"] == 1
        assert result["already_projected_count"] == 0
        q_entry = result["questions"][0]
        assert q_entry["eligible"] is True
        assert q_entry["content_hash"] is not None

    def test_ineligible_unverified_paper(self):
        sb = _seed_sb(paper=_paper(trust_status="pending"))
        result = preview_paper_projection(sb, PAPER_ID)
        assert result["eligible_count"] == 0
        assert result["ineligible_count"] == 1
        assert "paper_not_verified" in result["questions"][0]["reason"]

    def test_already_projected_no_change(self):
        content_hash = compute_content_hash(_question(), _options())
        projection = {
            "pyq_question_id": Q_ID,
            "mock_question_id": "mock-1",
            "sync_status": "active",
            "source_content_hash": content_hash,
            "projected_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
        sb = _seed_sb(projections=[projection])
        result = preview_paper_projection(sb, PAPER_ID)
        q_entry = result["questions"][0]
        assert q_entry["eligible"] is True
        assert q_entry["would_update"] is False
        assert result["would_update_count"] == 0

    def test_already_projected_stale(self):
        projection = {
            "pyq_question_id": Q_ID,
            "mock_question_id": "mock-1",
            "sync_status": "stale",
            "source_content_hash": "old-hash",
            "projected_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
        sb = _seed_sb(projections=[projection])
        result = preview_paper_projection(sb, PAPER_ID)
        q_entry = result["questions"][0]
        assert q_entry["eligible"] is True
        assert q_entry["would_update"] is True
        assert result["would_update_count"] == 1


# ─── sync_paper_projection ────────────────────────────────────────────────────

class TestSyncPaperProjection:
    def _sb_with_rpc(self, rpc_return: Any = None, rpc_raises: Exception | None = None) -> SBStub:
        sb = _seed_sb()
        original_rpc = sb.rpc

        def patched_rpc(name, params=None):
            if name == "project_pyq_question_to_mock_bank":
                if rpc_raises:
                    class _R:
                        def execute(self):
                            raise rpc_raises
                    return _R()
                data = rpc_return if rpc_return is not None else [{"outcome": "created", "mock_question_id": "mock-new"}]
                class _R:
                    def execute(self_inner):
                        class _Exec:
                            data = rpc_return if rpc_return is not None else [{"outcome": "created", "mock_question_id": "mock-new"}]
                        return _Exec()
                return _R()
            return original_rpc(name, params)

        sb.rpc = patched_rpc
        return sb

    def test_paper_not_found_raises_lookup(self):
        sb = SBStub()
        with pytest.raises(LookupError):
            sync_paper_projection(sb, PAPER_ID, ACTOR_ID)

    def test_rpc_called_for_each_question(self):
        calls = []
        sb = _seed_sb()
        original_rpc = sb.rpc

        def track_rpc(name, params=None):
            if name == "project_pyq_question_to_mock_bank":
                calls.append(params)
                class _R:
                    def execute(self):
                        class _E:
                            data = [{"outcome": "created", "mock_question_id": "mock-new"}]
                        return _E()
                return _R()
            return original_rpc(name, params)

        sb.rpc = track_rpc
        result = sync_paper_projection(sb, PAPER_ID, ACTOR_ID)
        assert result["attempted"] == 1
        assert len(calls) == 1
        assert calls[0]["p_pyq_question_id"] == Q_ID
        assert calls[0]["p_actor_id"] == ACTOR_ID

    def test_rpc_exception_propagates(self):
        """Internal RPC errors must propagate as exceptions, not silently return outcome='error'."""
        sb = _seed_sb()
        original_rpc = sb.rpc

        def fail_rpc(name, params=None):
            if name == "project_pyq_question_to_mock_bank":
                class _R:
                    def execute(self):
                        raise RuntimeError("DB error")
                return _R()
            return original_rpc(name, params)

        sb.rpc = fail_rpc
        with pytest.raises(RuntimeError):
            sync_paper_projection(sb, PAPER_ID, ACTOR_ID)

    def test_unknown_question_id_rejected(self):
        sb = _seed_sb()
        with pytest.raises(ValueError, match="not in paper"):
            sync_paper_projection(sb, PAPER_ID, ACTOR_ID, question_ids=["99999999-9999-9999-9999-999999999999"])

    def test_outcome_counted_correctly(self):
        sb = _seed_sb()
        original_rpc = sb.rpc

        def ok_rpc(name, params=None):
            if name == "project_pyq_question_to_mock_bank":
                class _R:
                    def execute(self):
                        class _E:
                            data = [{"outcome": "unchanged", "mock_question_id": "mock-1"}]
                        return _E()
                return _R()
            return original_rpc(name, params)

        sb.rpc = ok_rpc
        result = sync_paper_projection(sb, PAPER_ID, ACTOR_ID)
        assert result["outcomes"]["unchanged"] == 1


# ─── get_paper_projection_status ─────────────────────────────────────────────

class TestGetPaperProjectionStatus:
    def test_paper_not_found(self):
        with pytest.raises(LookupError):
            get_paper_projection_status(SBStub(), PAPER_ID)

    def test_no_projections(self):
        sb = _seed_sb()
        result = get_paper_projection_status(sb, PAPER_ID)
        assert result["total_questions"] == 1
        assert result["unprojected_count"] == 1
        assert result["projection_counts"]["active"] == 0

    def test_active_projection(self):
        projection = {
            "pyq_question_id": Q_ID,
            "mock_question_id": "mock-1",
            "sync_status": "active",
            "updated_at": "2026-01-01T00:00:00",
            "last_sync_result": {},
        }
        sb = _seed_sb(projections=[projection])
        result = get_paper_projection_status(sb, PAPER_ID)
        assert result["projection_counts"]["active"] == 1
        assert result["unprojected_count"] == 0
        assert result["stale_projections"] == []

    def test_stale_projection_listed(self):
        projection = {
            "pyq_question_id": Q_ID,
            "mock_question_id": "mock-1",
            "sync_status": "stale",
            "updated_at": "2026-01-01T00:00:00",
            "last_sync_result": {},
        }
        sb = _seed_sb(projections=[projection])
        result = get_paper_projection_status(sb, PAPER_ID)
        assert result["projection_counts"]["stale"] == 1
        assert len(result["stale_projections"]) == 1


# ─── API endpoint tests ───────────────────────────────────────────────────────

def _make_app(sb: SBStub, actor: dict) -> TestClient:
    app = FastAPI()
    app.include_router(admin_mocks_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: actor
    admin_mocks_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app, raise_server_exceptions=False)


def _author_actor():
    return {"id": ACTOR_ID, "role": "admin", "permissions": ["mock_questions:author"]}


def _publisher_actor():
    return {"id": ACTOR_ID, "role": "admin", "permissions": ["mock_questions:author", "mock_questions:publish"]}


class TestProjectionAPIEndpoints:
    def test_preview_returns_200_for_author(self):
        sb = _seed_sb()
        client = _make_app(sb, _author_actor())
        resp = client.get(f"/api/admin/mocks/pyq-papers/{PAPER_ID}/projection/preview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["paper_id"] == PAPER_ID

    def test_preview_404_for_unknown_paper(self):
        sb = SBStub()
        client = _make_app(sb, _author_actor())
        missing = "ffffffff-ffff-ffff-ffff-ffffffffffff"
        resp = client.get(f"/api/admin/mocks/pyq-papers/{missing}/projection/preview")
        assert resp.status_code == 404

    def test_sync_requires_publisher(self):
        sb = _seed_sb()
        client = _make_app(sb, _author_actor())  # only author, not publisher
        resp = client.post(
            f"/api/admin/mocks/pyq-papers/{PAPER_ID}/projection/sync",
            json={"audit_reason": "operator_test_sync"},
        )
        assert resp.status_code == 403

    def test_sync_returns_200_for_publisher(self):
        sb = _seed_sb()
        original_rpc = sb.rpc

        def ok_rpc(name, params=None):
            if name == "project_pyq_question_to_mock_bank":
                class _R:
                    def execute(self):
                        class _E:
                            data = [{"outcome": "created", "mock_question_id": "mock-new"}]
                        return _E()
                return _R()
            return original_rpc(name, params)

        sb.rpc = ok_rpc
        client = _make_app(sb, _publisher_actor())
        resp = client.post(
            f"/api/admin/mocks/pyq-papers/{PAPER_ID}/projection/sync",
            json={"audit_reason": "operator_manual_sync"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["attempted"] == 1

    def test_sync_audit_reason_required(self):
        """POST /sync without body must return 422 (audit_reason is required)."""
        sb = _seed_sb()
        client = _make_app(sb, _publisher_actor())
        resp = client.post(f"/api/admin/mocks/pyq-papers/{PAPER_ID}/projection/sync")
        assert resp.status_code == 422

    def test_sync_audit_reason_too_short(self):
        """audit_reason shorter than 8 chars must return 422."""
        sb = _seed_sb()
        client = _make_app(sb, _publisher_actor())
        resp = client.post(
            f"/api/admin/mocks/pyq-papers/{PAPER_ID}/projection/sync",
            json={"audit_reason": "short"},
        )
        assert resp.status_code == 422

    def test_sync_conflict_outcome_returns_409(self):
        """RPC returning outcome='conflict' must surface as 409 from the endpoint."""
        sb = _seed_sb()
        original_rpc = sb.rpc

        def conflict_rpc(name, params=None):
            if name == "project_pyq_question_to_mock_bank":
                class _R:
                    def execute(self):
                        class _E:
                            data = [{
                                "outcome": "conflict",
                                "mock_question_id": "mock-1",
                                "conflicting_pyq_id": "other-pyq",
                            }]
                        return _E()
                return _R()
            return original_rpc(name, params)

        sb.rpc = conflict_rpc
        client = _make_app(sb, _publisher_actor())
        resp = client.post(
            f"/api/admin/mocks/pyq-papers/{PAPER_ID}/projection/sync",
            json={"audit_reason": "operator_manual_sync"},
        )
        assert resp.status_code == 409

    def test_status_returns_200_for_author(self):
        sb = _seed_sb()
        client = _make_app(sb, _author_actor())
        resp = client.get(f"/api/admin/mocks/pyq-papers/{PAPER_ID}/projection/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "projection_counts" in data

    def test_invalid_paper_uuid_returns_422(self):
        sb = _seed_sb()
        client = _make_app(sb, _author_actor())
        resp = client.get("/api/admin/mocks/pyq-papers/not-a-uuid/projection/preview")
        assert resp.status_code == 422


# ─── MCQ exactly-one-correct validation fix ──────────────────────────────────

class TestMCQExactlyOneCorrect:
    """Verify create_question now rejects MCQ with 0 or 2+ correct options."""

    def _actor(self) -> dict:
        return {"id": ACTOR_ID, "role": "admin", "permissions": []}

    def _base_data(self, options=None) -> dict:
        return {
            "question_text": "Test question?",
            "question_type": "mcq",
            "options": options or [
                {"option_text": "A", "is_correct": True},
                {"option_text": "B", "is_correct": False},
            ],
        }

    def test_zero_correct_options_raises(self):
        sb = SBStub()
        opts = [{"option_text": "A", "is_correct": False}, {"option_text": "B", "is_correct": False}]
        with pytest.raises(ValueError, match="exactly one correct"):
            create_question(sb, self._actor(), self._base_data(options=opts))

    def test_two_correct_options_raises(self):
        sb = SBStub()
        opts = [{"option_text": "A", "is_correct": True}, {"option_text": "B", "is_correct": True}]
        with pytest.raises(ValueError, match="exactly one correct"):
            create_question(sb, self._actor(), self._base_data(options=opts))

    def test_exactly_one_correct_succeeds(self):
        sb = SBStub()
        opts = [{"option_text": "A", "is_correct": True}, {"option_text": "B", "is_correct": False}]
        result = create_question(sb, self._actor(), self._base_data(options=opts))
        assert result["question_type"] == "mcq"
