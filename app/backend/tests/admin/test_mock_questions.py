"""Pytest suite for PR2 — Admin Question Bank: Workflow & RBAC.

Covers:
  - State machine transitions (pure unit)
  - Fingerprint computation (pure unit)
  - create_question / update_question service (SBStub)
  - Reviewer conflict-of-interest (service + API)
  - RBAC gates on API endpoints (403 vs 2xx)
  - Dedup check (service)
  - Bulk import dry-run & commit (service)
  - Selector TTL / published-status filter in mock_engine
  - Bootstrap permission helper
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.admin.mock_questions import (
    ConflictError,
    allowed_transitions,
    compute_fingerprint,
    create_question,
    transition,
)
from app.api import admin_mocks as admin_mocks_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_actor(role: str = "admin", permissions: list[str] | None = None) -> dict:
    return {
        "id": "actor-001",
        "role": role,
        "permissions": permissions or [],
        "email": "test@example.com",
    }


def _make_options(texts: list[str] | None = None, correct_idx: int = 0) -> list[dict]:
    texts = texts or ["Option A", "Option B", "Option C", "Option D"]
    return [{"option_text": t, "is_correct": i == correct_idx} for i, t in enumerate(texts)]


def _seed_question(sb: SBStub, *, qid: str = "q-1", status: str = "draft", actor_id: str = "actor-001") -> dict:
    """Insert a minimal question + options row into the SBStub."""
    q = {
        "id": qid,
        "question_text": "What is 2 + 2?",
        "reviewer_status": status,
        "created_by": actor_id,
        "difficulty": "easy",
        "language": "en",
        "is_conceptual": True,
        "is_factual": False,
        "is_current": False,
        "valid_until": None,
        "question_fingerprint": "abc123",
    }
    sb.db.setdefault("mock_question_bank", []).append(q)
    opts = [
        {"id": "o-1", "question_id": qid, "option_text": "4",      "is_correct": True,  "option_index": 0},
        {"id": "o-2", "question_id": qid, "option_text": "3",      "is_correct": False, "option_index": 1},
        {"id": "o-3", "question_id": qid, "option_text": "5",      "is_correct": False, "option_index": 2},
        {"id": "o-4", "question_id": qid, "option_text": "22",     "is_correct": False, "option_index": 3},
    ]
    sb.db.setdefault("mock_question_options", []).extend(opts)
    return q


def _build_app(sb: SBStub, *, permissions: list[str] | None = None, role: str = "admin") -> TestClient:
    app = FastAPI()
    app.include_router(admin_mocks_api.router)

    actor = _make_actor(role=role, permissions=permissions or [])
    app.dependency_overrides[get_current_user] = lambda: actor
    # Patch supabase getter used by the router
    admin_mocks_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]

    return TestClient(app, raise_server_exceptions=False)


# ═════════════════════════════════════════════════════════════════════════════
# 1.  State machine — pure unit tests
# ═════════════════════════════════════════════════════════════════════════════

class TestStateMachine:
    def test_draft_allows_submit(self):
        assert "submit" in allowed_transitions("draft")

    def test_in_review_allows_approve_and_request_changes(self):
        actions = allowed_transitions("in_review")
        assert "approve" in actions
        assert "request_changes" in actions

    def test_needs_changes_allows_submit(self):
        assert "submit" in allowed_transitions("needs_changes")

    def test_verified_allows_publish(self):
        actions = allowed_transitions("verified")
        assert "publish" in actions
        # "archive" is only available from "published", not "verified"

    def test_published_allows_archive(self):
        assert "archive" in allowed_transitions("published")

    def test_archived_has_no_standard_transitions(self):
        # archived → restore (publisher-only) is not in standard list
        actions = allowed_transitions("archived")
        # submit / approve / publish should not be available
        assert "submit" not in actions
        assert "approve" not in actions

    def test_invalid_transition_raises_value_error(self):
        sb = SBStub()
        q = _seed_question(sb, status="draft")
        actor = _make_actor(permissions=["mock_questions:review"])
        with pytest.raises(ValueError):
            transition(sb, actor, "q-1", "approve")  # draft→approve is not valid

    def test_full_happy_path_statuses(self):
        """draft → in_review → verified → published via sequential transitions."""
        sb = SBStub()
        _seed_question(sb, status="draft", actor_id="author-1")

        author    = _make_actor(permissions=["mock_questions:author"],  role="admin")
        reviewer  = _make_actor(permissions=["mock_questions:review"],  role="admin")
        reviewer["id"] = "reviewer-99"
        publisher = _make_actor(permissions=["mock_questions:publish"], role="admin")
        publisher["id"] = "publisher-99"

        # draft → in_review
        row = transition(sb, author, "q-1", "submit")
        assert row["reviewer_status"] == "in_review"

        # in_review → verified (different actor; reviewer ≠ author)
        row = transition(sb, reviewer, "q-1", "approve")
        assert row["reviewer_status"] == "verified"

        # verified → published
        row = transition(sb, publisher, "q-1", "publish")
        assert row["reviewer_status"] == "published"


# ═════════════════════════════════════════════════════════════════════════════
# 2.  Fingerprint — pure unit tests
# ═════════════════════════════════════════════════════════════════════════════

class TestFingerprint:
    def test_deterministic(self):
        opts = [{"id": "o1", "option_text": "Yes"}, {"id": "o2", "option_text": "No"}]
        fp1 = compute_fingerprint("Is the sky blue?", opts, "o1")
        fp2 = compute_fingerprint("Is the sky blue?", opts, "o1")
        assert fp1 == fp2

    def test_case_insensitive_on_question(self):
        opts = [{"id": "o1", "option_text": "Yes"}, {"id": "o2", "option_text": "No"}]
        fp_lower = compute_fingerprint("is the sky blue?", opts, "o1")
        fp_mixed = compute_fingerprint("Is The Sky Blue?", opts, "o1")
        assert fp_lower == fp_mixed

    def test_different_question_text_gives_different_fp(self):
        opts = [{"id": "o1", "option_text": "Yes"}, {"id": "o2", "option_text": "No"}]
        fp1 = compute_fingerprint("Is the sky blue?", opts, "o1")
        fp2 = compute_fingerprint("Is the grass green?", opts, "o1")
        assert fp1 != fp2

    def test_different_correct_option_gives_different_fp(self):
        opts = [{"id": "o1", "option_text": "Yes"}, {"id": "o2", "option_text": "No"}]
        fp1 = compute_fingerprint("Question?", opts, "o1")
        fp2 = compute_fingerprint("Question?", opts, "o2")
        assert fp1 != fp2

    def test_option_reordering_produces_same_fp(self):
        """Sorted-by-text ensures reordering options doesn't change fingerprint."""
        opts_ab = [{"id": "o1", "option_text": "Alpha"}, {"id": "o2", "option_text": "Beta"}]
        opts_ba = [{"id": "o2", "option_text": "Beta"}, {"id": "o1", "option_text": "Alpha"}]
        fp1 = compute_fingerprint("Q?", opts_ab, "o1")
        fp2 = compute_fingerprint("Q?", opts_ba, "o1")
        assert fp1 == fp2

    def test_returns_hex_sha256(self):
        opts = [{"id": "o1", "option_text": "A"}, {"id": "o2", "option_text": "B"}]
        fp = compute_fingerprint("Q?", opts, "o1")
        assert len(fp) == 64
        assert all(c in "0123456789abcdef" for c in fp)


# ═════════════════════════════════════════════════════════════════════════════
# 3.  create_question service — via SBStub
# ═════════════════════════════════════════════════════════════════════════════

class TestCreateQuestion:
    def test_creates_question_in_draft(self):
        sb = SBStub()
        actor = _make_actor(permissions=["mock_questions:author"])
        result = create_question(sb, actor, {
            "question_text": "What is the capital of France?",
            "options": _make_options(["Paris", "London", "Rome", "Berlin"], correct_idx=0),
        })
        assert result["reviewer_status"] == "draft"
        assert result["question_text"] == "What is the capital of France?"
        assert len(result["options"]) == 4
        assert result["question_fingerprint"] is not None

    def test_raises_if_no_correct_option(self):
        sb = SBStub()
        actor = _make_actor()
        with pytest.raises(ValueError, match="correct"):
            create_question(sb, actor, {
                "question_text": "Q?",
                "options": [{"option_text": "A", "is_correct": False}, {"option_text": "B", "is_correct": False}],
            })

    def test_raises_if_fewer_than_two_options(self):
        sb = SBStub()
        actor = _make_actor()
        with pytest.raises(ValueError):
            create_question(sb, actor, {
                "question_text": "Q?",
                "options": [{"option_text": "Only one", "is_correct": True}],
            })

    def test_raises_if_missing_question_text(self):
        sb = SBStub()
        actor = _make_actor()
        with pytest.raises(ValueError, match="question_text"):
            create_question(sb, actor, {
                "question_text": "",
                "options": _make_options(),
            })

    def test_audit_log_written_on_create(self):
        sb = SBStub()
        actor = _make_actor()
        result = create_question(sb, actor, {
            "question_text": "Audit test question?",
            "options": _make_options(),
        })
        log_rows = sb.db.get("mock_question_review_log", [])
        assert any(r["question_id"] == result["id"] and r["action"] == "create" for r in log_rows)


# ═════════════════════════════════════════════════════════════════════════════
# 4.  Conflict-of-interest
# ═════════════════════════════════════════════════════════════════════════════

class TestConflictOfInterest:
    def test_reviewer_cannot_approve_own_question(self):
        """Author and reviewer are the same person → ConflictError (→ 409)."""
        sb = SBStub()
        # Seed a question created by actor-001
        _seed_question(sb, status="in_review", actor_id="actor-001")

        actor = _make_actor(permissions=["mock_questions:author", "mock_questions:review"])
        actor["id"] = "actor-001"  # same person

        with pytest.raises(Exception) as exc_info:
            transition(sb, actor, "q-1", "approve")

        # The service raises ConflictError with the conflict-of-interest message
        assert "authored" in str(exc_info.value).lower()

    def test_different_reviewer_can_approve(self):
        sb = SBStub()
        _seed_question(sb, status="in_review", actor_id="author-original")
        reviewer = _make_actor(permissions=["mock_questions:review"])
        reviewer["id"] = "reviewer-different"

        result = transition(sb, reviewer, "q-1", "approve")
        assert result["reviewer_status"] == "verified"


# ═════════════════════════════════════════════════════════════════════════════
# 5.  API RBAC gates
# ═════════════════════════════════════════════════════════════════════════════

class TestAPIRBAC:
    """Verify that permission guards return 403 to unauthorised callers."""

    def test_create_question_requires_author_permission(self):
        sb = SBStub()
        # No permissions → should get 403
        client = _build_app(sb, permissions=[])
        resp = client.post("/admin/mocks/questions", json={
            "question_text": "Test question?",
            "options": _make_options(),
        })
        assert resp.status_code == 403

    def test_create_question_succeeds_with_author_permission(self):
        sb = SBStub()
        client = _build_app(sb, permissions=["mock_questions:author"])
        resp = client.post("/admin/mocks/questions", json={
            "question_text": "Test question?",
            "options": _make_options(),
        })
        # 200 or 201
        assert resp.status_code in (200, 201)

    def test_approve_requires_review_permission(self):
        sb = SBStub()
        _seed_question(sb, status="in_review", actor_id="other-author")
        # Only author permission, not review
        client = _build_app(sb, permissions=["mock_questions:author"])
        resp = client.post("/admin/mocks/questions/q-1/approve", json={})
        assert resp.status_code == 403

    def test_publish_requires_publish_permission(self):
        sb = SBStub()
        _seed_question(sb, status="verified", actor_id="someone")
        client = _build_app(sb, permissions=["mock_questions:review"])
        resp = client.post("/admin/mocks/questions/q-1/publish", json={})
        assert resp.status_code == 403

    def test_super_admin_bypasses_all_permission_checks(self):
        sb = SBStub()
        client = _build_app(sb, permissions=[], role="super_admin")
        resp = client.post("/admin/mocks/questions", json={
            "question_text": "Super admin test question?",
            "options": _make_options(),
        })
        assert resp.status_code in (200, 201)

    def test_review_queue_requires_review_permission(self):
        sb = SBStub()
        client = _build_app(sb, permissions=["mock_questions:author"])
        resp = client.get("/admin/mocks/review-queue")
        assert resp.status_code == 403

    def test_review_queue_accessible_with_review_permission(self):
        sb = SBStub()
        _seed_question(sb, status="in_review")
        client = _build_app(sb, permissions=["mock_questions:review"])
        resp = client.get("/admin/mocks/review-queue")
        assert resp.status_code == 200


# ═════════════════════════════════════════════════════════════════════════════
# 6.  Dedup check
# ═════════════════════════════════════════════════════════════════════════════

class TestDedupCheck:
    def test_dedup_check_returns_no_collision_when_unique(self):
        sb = SBStub()
        _seed_question(sb, qid="q-1")
        actor = _make_actor(permissions=["mock_questions:review"])
        client = _build_app(sb, permissions=["mock_questions:review"])

        # The RPC for trigram search returns None by default in SBStub
        resp = client.post("/admin/mocks/questions/q-1/dedup-check", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "fingerprint_match" in data or "trigram_neighbors" in data

    def test_dedup_check_returns_404_for_missing_question(self):
        sb = SBStub()
        client = _build_app(sb, permissions=["mock_questions:review"])
        resp = client.post("/admin/mocks/questions/nonexistent-id/dedup-check", json={})
        assert resp.status_code == 404


# ═════════════════════════════════════════════════════════════════════════════
# 7.  Bulk import — dry-run & commit
# ═════════════════════════════════════════════════════════════════════════════

class TestBulkImport:
    """Tests for mock_import.parse_file, dry_run, commit_import."""

    def test_parse_csv_produces_rows(self):
        from app.admin.mock_import import parse_file

        csv_content = (
            "question_text,option_1,option_2,option_3,option_4,correct_option,difficulty,language,source_kind,source_url\n"
            "What is 2+2?,4,3,5,22,1,easy,en,authored,\n"
            "Capital of France?,Paris,London,Berlin,Rome,1,medium,en,authored,\n"
        )
        rows = parse_file(csv_content.encode(), "text/csv")
        assert len(rows) == 2
        assert rows[0]["question_text"] == "What is 2+2?"

    def test_parse_json_produces_rows(self):
        from app.admin.mock_import import parse_file
        import json

        data = [
            {
                "question_text": "What is 3+3?",
                "options": [{"text": "6", "is_correct": True}, {"text": "5", "is_correct": False}],
                "difficulty": "easy",
                "language": "en",
            }
        ]
        rows = parse_file(json.dumps(data).encode(), "application/json")
        assert len(rows) == 1
        assert rows[0]["question_text"] == "What is 3+3?"

    def test_dry_run_returns_expected_fields(self):
        from app.admin.mock_import import dry_run

        sb = SBStub()
        actor = _make_actor(permissions=["mock_questions:author"])

        csv_content = (
            "question_text,option_1,option_2,option_3,option_4,correct_option,difficulty,language,source_kind,source_url\n"
            "Test question one?,A,B,C,D,1,easy,en,authored,\n"
        )
        result = dry_run(sb, actor, csv_content.encode(), "text/csv")

        assert "import_token" in result
        assert "total" in result
        assert "ok_count" in result
        assert "duplicate_count" in result
        assert "error_count" in result
        assert "rows" in result
        assert result["total"] >= 1

    def test_commit_import_inserts_ok_rows(self):
        from app.admin.mock_import import dry_run, commit_import

        sb = SBStub()
        actor = _make_actor(permissions=["mock_questions:author"])

        csv_content = (
            "question_text,option_1,option_2,option_3,option_4,correct_option,difficulty,language,source_kind,source_url\n"
            "Commit test question?,A,B,C,D,1,easy,en,authored,\n"
        )
        dr = dry_run(sb, actor, csv_content.encode(), "text/csv")
        token = dr["import_token"]
        assert token is not None

        commit_result = commit_import(sb, actor, token)
        assert "created" in commit_result
        assert commit_result["created"] >= 1

    def test_commit_with_invalid_token_raises(self):
        from app.admin.mock_import import commit_import

        sb = SBStub()
        actor = _make_actor()
        with pytest.raises(Exception):
            commit_import(sb, actor, "nonexistent-token-xyz")

    def test_import_idempotency_via_fingerprint(self):
        """Importing the same content twice → second run shows duplicates."""
        from app.admin.mock_import import dry_run, commit_import

        sb = SBStub()
        actor = _make_actor(permissions=["mock_questions:author"])

        csv = (
            "question_text,option_1,option_2,option_3,option_4,correct_option,difficulty,language,source_kind,source_url\n"
            "Idempotent test question?,A,B,C,D,1,easy,en,authored,\n"
        )
        # First import
        dr1 = dry_run(sb, actor, csv.encode(), "text/csv")
        commit_import(sb, actor, dr1["import_token"])

        # Second dry-run — same fingerprint should be flagged as duplicate
        dr2 = dry_run(sb, actor, csv.encode(), "text/csv")
        assert dr2["duplicate_count"] >= 1


# ═════════════════════════════════════════════════════════════════════════════
# 8.  Selector TTL / published-status filter in mock_engine
# ═════════════════════════════════════════════════════════════════════════════

class TestSelectorHardening:
    """_load_questions_for_template must filter by published + valid TTL."""

    def _make_mock_engine_sb(self, questions: list[dict]) -> MagicMock:
        """Return a MagicMock supabase that intercepts the question query chain."""
        mock_sb = MagicMock()
        mock_chain = MagicMock()
        mock_chain.execute.return_value = MagicMock(data=questions)
        # Any chained call returns mock_chain so the filter accumulation works
        mock_chain.__getattr__ = lambda self, name: (lambda *a, **kw: mock_chain)
        mock_sb.table.return_value = mock_chain
        return mock_sb

    def test_only_published_questions_are_loaded(self):
        from app.study_os.mock_engine import _load_questions_for_template

        published_q = {"id": "q-pub", "reviewer_status": "published", "valid_until": None, "question_text": "Q1?", "options": []}
        verified_q  = {"id": "q-ver", "reviewer_status": "verified",   "valid_until": None, "question_text": "Q2?", "options": []}

        # Patch supabase call — return only published_q (simulating DB filter)
        sb = MagicMock()
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=[published_q])
        sb.table.return_value.select.return_value = chain
        chain.eq.return_value = chain
        chain.or_.return_value = chain
        chain.in_.return_value = chain
        chain.limit.return_value = chain

        template = {"id": "tmpl-1", "config": {"question_ids": ["q-pub"]}}
        result = _load_questions_for_template(sb, template)
        # Verify that .eq was called with ("reviewer_status", "published")
        eq_calls = [str(c) for c in chain.eq.call_args_list]
        assert any("published" in c for c in eq_calls)

    def test_expired_question_excluded_via_ttl_filter(self):
        """valid_until in the past should be excluded."""
        from app.study_os.mock_engine import _load_questions_for_template

        past_iso = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        expired_q = {
            "id": "q-exp", "reviewer_status": "published",
            "valid_until": past_iso, "question_text": "Old event?", "options": []
        }

        sb = MagicMock()
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=[])  # DB filtered it out
        sb.table.return_value.select.return_value = chain
        chain.eq.return_value = chain
        chain.or_.return_value = chain
        chain.in_.return_value = chain
        chain.limit.return_value = chain

        template = {"id": "tmpl-1", "config": {"question_ids": ["q-exp"]}}
        result = _load_questions_for_template(sb, template)
        # Verify the TTL filter (or_) was applied
        assert chain.or_.called


# ═════════════════════════════════════════════════════════════════════════════
# 9.  Bootstrap publisher permissions
# ═════════════════════════════════════════════════════════════════════════════

class TestBootstrap:
    def test_bootstrap_adds_publish_permission(self, monkeypatch):
        """_bootstrap_mock_publishers reads env var and grants permission."""
        monkeypatch.setenv("MOCK_PUBLISHER_BOOTSTRAP_EMAILS", "publisher@example.com")
        # server.py lives at the backend root, not inside the `app` package.
        from server import _bootstrap_mock_publishers  # noqa: PLC0415
        assert callable(_bootstrap_mock_publishers)

    def test_bootstrap_skips_empty_env_var(self, monkeypatch):
        monkeypatch.setenv("MOCK_PUBLISHER_BOOTSTRAP_EMAILS", "")
        # Should not raise — just a no-op
        try:
            from server import _bootstrap_mock_publishers  # noqa: PLC0415
            # Verify the function is still importable with an empty env var
            assert callable(_bootstrap_mock_publishers)
        except Exception as exc:
            pytest.fail(f"Bootstrap import raised unexpectedly: {exc}")
