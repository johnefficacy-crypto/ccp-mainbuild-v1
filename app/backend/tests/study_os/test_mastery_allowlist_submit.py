"""Synchronous submit path — mastery allowlist enforcement tests.

Verifies that the POST /attempts/{attempt_id}/submit endpoint enforces the
per-user live allowlist (FF_MOCK_MASTERY_LIVE_USER_IDS) regardless of the
global FF_MOCK_MASTERY_WRITES value.

Root cause being guarded: before this fix, submit called get_mastery_write_flag()
but NOT resolve_effective_mastery_flag(), so a global FF=live value was passed
directly to mastery_retry_done, claim_mastery_retry_required, and MasteryWriter,
bypassing the per-user allowlist entirely.

Coverage:
  A. off:     global off → no claim, no writer
  B. shadow:  requested shadow → effective shadow; retry_done/claim/writer receive shadow
  C. live allowlisted: requested live; effective live; all three receive live
  D. live non-allowlisted: requested live; effective shadow; all three receive shadow; no live call
  E. empty allowlist: effective shadow; no live writer or claim
  F. already-submitted (idempotency): effective-mode retry already done → no new claim/writer
  G. claim failure: existing 503 mastery_retry_claim_failed preserved
  H. writer/classification failure: retry returned to pending; deferred semantics preserved
"""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import mock_engine as mock_engine_api
from app.core.auth import get_current_user
from app.study_os import mock_engine as svc
from tests.persona_questions._stub import SBStub

# ── constants ─────────────────────────────────────────────────────────────────

USER_ALLOWLISTED = "a0000001-0000-0000-0000-000000000001"
USER_NOT_LISTED = "a0000002-0000-0000-0000-000000000002"
ATTEMPT_ID = "aaaaattt-0000-0000-0000-000000000001"


# ── minimal DB helpers ────────────────────────────────────────────────────────

def _make_option(question_id: str, opt_idx: int, is_correct: bool) -> dict:
    return {
        "id": f"opt-{question_id}-{opt_idx}",
        "question_id": question_id,
        "option_text": f"Option {opt_idx}",
        "option_index": opt_idx,
        "is_correct": is_correct,
    }


def _make_question(qid: str | None = None) -> dict:
    qid = qid or str(uuid.uuid4())
    opts = [_make_option(qid, i, i == 2) for i in range(1, 5)]
    correct_opt_id = opts[1]["id"]
    return {
        "id": qid,
        "exam_family": "TEST",
        "question_text": f"Question {qid[:8]}",
        "question_type": "mcq",
        "difficulty": "easy",
        "marks": 1.0,
        "negative_marks": 0.25,
        "correct_option_id": correct_opt_id,
        "explanation": "Explanation text.",
        "reviewer_status": "published",
        "options": opts,
    }


def _seeded_db_for_user(user_id: str) -> SBStub:
    """Minimal DB with one template and one question for the given user."""
    slug = "test-mock-allowlist"
    questions = [_make_question()]
    template = {
        "id": f"tmpl-{slug}",
        "slug": slug,
        "name": "Allowlist Test Mock",
        "exam_family": "TEST",
        "total_questions": len(questions),
        "duration_sec": 300,
        "negative_marking": True,
        "marks_per_correct": 1.0,
        "marks_per_wrong": 0.25,
        "config": {"question_ids": [q["id"] for q in questions]},
        "status": "active",
    }
    db: dict = {
        "mock_templates": [template],
        "mock_question_bank": questions,
        "mock_question_options": [o for q in questions for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
        "mock_attempt_events": [],
        "mock_tests": [],
        "mock_attempt_jobs": [],
        "mock_mastery_shadow": [],
        "mock_attempt_response_classification": [],
        "user_topic_mastery": [],
        "user_topic_mastery_audit": [],
        "user_topic_error_patterns": [],
        "mock_correction_tasks": [],
    }
    return SBStub(db)


def _client_for_user(sb: SBStub, user_id: str) -> TestClient:
    """Build a TestClient that authenticates as user_id."""
    app = FastAPI()
    app.include_router(mock_engine_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id}
    mock_engine_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


def _start_and_submit(sb: SBStub, user_id: str) -> tuple[str, int]:
    """Start an attempt and call the submit API endpoint.

    Returns (attempt_id, status_code).
    """
    client = _client_for_user(sb, user_id)
    start_r = client.post("/api/study/mocks/attempts/start", json={"template_slug": "test-mock-allowlist"})
    assert start_r.status_code == 200, f"start failed: {start_r.text}"
    attempt_id = start_r.json()["attempt_id"]
    sub_r = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    return attempt_id, sub_r.status_code


def _mastery_jobs(sb: SBStub) -> list[dict]:
    return [j for j in sb.db.get("mock_attempt_jobs", []) if j.get("job_kind") == "mastery_retry"]


# ── test A: FF=off → no mastery work ─────────────────────────────────────────

class TestFlagOff:
    def test_off_no_claim_no_writer(self, monkeypatch):
        """A. global off → no mastery claim, no MasteryWriter constructed."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "off")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _seeded_db_for_user(USER_ALLOWLISTED)

        with (
            patch.object(mock_engine_api, "claim_mastery_retry_required") as mock_claim,
            patch.object(mock_engine_api, "MasteryWriter") as mock_writer_cls,
        ):
            _, status = _start_and_submit(sb, USER_ALLOWLISTED)

        assert status == 200
        mock_claim.assert_not_called()
        mock_writer_cls.assert_not_called()

    def test_off_no_mastery_retry_done_called(self, monkeypatch):
        """A. global off → mastery_retry_done is never consulted."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "off")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _seeded_db_for_user(USER_ALLOWLISTED)

        with patch.object(mock_engine_api, "mastery_retry_done") as mock_done:
            _, status = _start_and_submit(sb, USER_ALLOWLISTED)

        assert status == 200
        mock_done.assert_not_called()


# ── test B: FF=shadow → effective shadow ─────────────────────────────────────

class TestFlagShadow:
    def test_shadow_retry_done_receives_shadow(self, monkeypatch):
        """B. requested shadow → mastery_retry_done called with 'shadow' on re-submit.

        mastery_retry_done is only consulted when was_submitted=True (re-submit path).
        Set the attempt to submitted state first, then call submit again.
        """
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _seeded_db_for_user(USER_ALLOWLISTED)

        # Do a first submit to put the attempt in submitted state
        attempt_id, first_status = _start_and_submit(sb, USER_ALLOWLISTED)
        assert first_status == 200

        # Now re-submit with was_submitted=True → mastery_retry_done is consulted
        with (
            patch.object(mock_engine_api, "mastery_retry_done", return_value=True) as mock_done,
            patch.object(mock_engine_api, "claim_mastery_retry_required") as mock_claim,
        ):
            client = _client_for_user(sb, USER_ALLOWLISTED)
            sub_r = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")

        assert sub_r.status_code == 200
        # mastery_retry_done must be called with effective flag = "shadow"
        mock_done.assert_called_once()
        _, call_args, call_kwargs = mock_done.mock_calls[0]
        effective_flag_passed = call_args[2] if len(call_args) > 2 else call_kwargs.get("flag_state")
        assert effective_flag_passed == "shadow", (
            f"mastery_retry_done received flag '{effective_flag_passed}', expected 'shadow'"
        )
        # Since mastery_retry_done returned True, no new claim should be made
        mock_claim.assert_not_called()

    def test_shadow_claim_receives_shadow(self, monkeypatch):
        """B. requested shadow → claim_mastery_retry_required called with 'shadow'."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _seeded_db_for_user(USER_ALLOWLISTED)
        claimed_job_id = "job-shadow-001"

        with (
            patch.object(mock_engine_api, "mastery_retry_done", return_value=False),
            patch.object(mock_engine_api, "claim_mastery_retry_required", return_value=claimed_job_id) as mock_claim,
            patch.object(mock_engine_api, "MasteryWriter") as mock_writer_cls,
            patch.object(mock_engine_api, "complete_mastery_retry_required"),
        ):
            mock_writer_instance = MagicMock()
            mock_writer_instance.process_attempt = MagicMock(return_value=None)

            import asyncio

            async def _noop(*a, **kw):
                pass

            mock_writer_instance.process_attempt.side_effect = _noop
            mock_writer_cls.return_value = mock_writer_instance

            _, status = _start_and_submit(sb, USER_ALLOWLISTED)

        assert status == 200
        mock_claim.assert_called_once()
        _, call_args, call_kwargs = mock_claim.mock_calls[0]
        effective_flag_passed = call_args[2] if len(call_args) > 2 else call_kwargs.get("flag_state")
        assert effective_flag_passed == "shadow", (
            f"claim_mastery_retry_required received flag '{effective_flag_passed}', expected 'shadow'"
        )

    def test_shadow_writer_receives_shadow(self, monkeypatch):
        """B. requested shadow → MasteryWriter constructed with 'shadow'."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _seeded_db_for_user(USER_ALLOWLISTED)

        with (
            patch.object(mock_engine_api, "mastery_retry_done", return_value=False),
            patch.object(mock_engine_api, "claim_mastery_retry_required", return_value="job-shadow-x"),
            patch.object(mock_engine_api, "MasteryWriter") as mock_writer_cls,
            patch.object(mock_engine_api, "complete_mastery_retry_required"),
        ):
            mock_writer_instance = MagicMock()

            async def _noop(*a, **kw):
                pass

            mock_writer_instance.process_attempt.side_effect = _noop
            mock_writer_cls.return_value = mock_writer_instance

            _, status = _start_and_submit(sb, USER_ALLOWLISTED)

        assert status == 200
        mock_writer_cls.assert_called_once()
        writer_call = mock_writer_cls.call_args
        # MasteryWriter(sb, flag_state) — flag_state is positional arg 1
        flag_in_call = writer_call[0][1] if writer_call[0] else writer_call[1].get("flag_state")
        assert flag_in_call == "shadow", (
            f"MasteryWriter constructed with flag '{flag_in_call}', expected 'shadow'"
        )


# ── test C: FF=live + allowlisted user → effective live ──────────────────────

class TestFlagLiveAllowlisted:
    def test_live_allowlisted_claim_receives_live(self, monkeypatch):
        """C. requested live; user in allowlist → claim receives 'live'."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_ALLOWLISTED)

        sb = _seeded_db_for_user(USER_ALLOWLISTED)

        with (
            patch.object(mock_engine_api, "mastery_retry_done", return_value=False),
            patch.object(mock_engine_api, "claim_mastery_retry_required", return_value="job-live-1") as mock_claim,
            patch.object(mock_engine_api, "MasteryWriter") as mock_writer_cls,
            patch.object(mock_engine_api, "complete_mastery_retry_required"),
        ):
            mock_writer_instance = MagicMock()

            async def _noop(*a, **kw):
                pass

            mock_writer_instance.process_attempt.side_effect = _noop
            mock_writer_cls.return_value = mock_writer_instance

            _, status = _start_and_submit(sb, USER_ALLOWLISTED)

        assert status == 200
        mock_claim.assert_called_once()
        _, call_args, call_kwargs = mock_claim.mock_calls[0]
        effective_flag_passed = call_args[2] if len(call_args) > 2 else call_kwargs.get("flag_state")
        assert effective_flag_passed == "live", (
            f"claim_mastery_retry_required received '{effective_flag_passed}', expected 'live'"
        )

    def test_live_allowlisted_writer_receives_live(self, monkeypatch):
        """C. requested live; user in allowlist → MasteryWriter constructed with 'live'."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_ALLOWLISTED)

        sb = _seeded_db_for_user(USER_ALLOWLISTED)

        with (
            patch.object(mock_engine_api, "mastery_retry_done", return_value=False),
            patch.object(mock_engine_api, "claim_mastery_retry_required", return_value="job-live-2"),
            patch.object(mock_engine_api, "MasteryWriter") as mock_writer_cls,
            patch.object(mock_engine_api, "complete_mastery_retry_required"),
        ):
            mock_writer_instance = MagicMock()

            async def _noop(*a, **kw):
                pass

            mock_writer_instance.process_attempt.side_effect = _noop
            mock_writer_cls.return_value = mock_writer_instance

            _, status = _start_and_submit(sb, USER_ALLOWLISTED)

        assert status == 200
        mock_writer_cls.assert_called_once()
        writer_call = mock_writer_cls.call_args
        flag_in_call = writer_call[0][1] if writer_call[0] else writer_call[1].get("flag_state")
        assert flag_in_call == "live", (
            f"MasteryWriter constructed with flag '{flag_in_call}', expected 'live'"
        )


# ── test D: FF=live + non-allowlisted user → effective shadow ─────────────────

class TestFlagLiveNonAllowlisted:
    def test_live_non_allowlisted_claim_receives_shadow(self, monkeypatch):
        """D. requested live; user NOT in allowlist → claim receives 'shadow', not 'live'."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_ALLOWLISTED)  # only USER_ALLOWLISTED

        sb = _seeded_db_for_user(USER_NOT_LISTED)

        with (
            patch.object(mock_engine_api, "mastery_retry_done", return_value=False),
            patch.object(mock_engine_api, "claim_mastery_retry_required", return_value="job-shadow-nonlist") as mock_claim,
            patch.object(mock_engine_api, "MasteryWriter") as mock_writer_cls,
            patch.object(mock_engine_api, "complete_mastery_retry_required"),
        ):
            mock_writer_instance = MagicMock()

            async def _noop(*a, **kw):
                pass

            mock_writer_instance.process_attempt.side_effect = _noop
            mock_writer_cls.return_value = mock_writer_instance

            _, status = _start_and_submit(sb, USER_NOT_LISTED)

        assert status == 200
        mock_claim.assert_called_once()
        _, call_args, call_kwargs = mock_claim.mock_calls[0]
        effective_flag_passed = call_args[2] if len(call_args) > 2 else call_kwargs.get("flag_state")
        assert effective_flag_passed == "shadow", (
            f"Non-allowlisted user: claim received '{effective_flag_passed}', expected 'shadow' (not 'live')"
        )

    def test_live_non_allowlisted_writer_receives_shadow(self, monkeypatch):
        """D. requested live; user NOT in allowlist → MasteryWriter constructed with 'shadow'."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_ALLOWLISTED)

        sb = _seeded_db_for_user(USER_NOT_LISTED)

        with (
            patch.object(mock_engine_api, "mastery_retry_done", return_value=False),
            patch.object(mock_engine_api, "claim_mastery_retry_required", return_value="job-shadow-nl"),
            patch.object(mock_engine_api, "MasteryWriter") as mock_writer_cls,
            patch.object(mock_engine_api, "complete_mastery_retry_required"),
        ):
            mock_writer_instance = MagicMock()

            async def _noop(*a, **kw):
                pass

            mock_writer_instance.process_attempt.side_effect = _noop
            mock_writer_cls.return_value = mock_writer_instance

            _, status = _start_and_submit(sb, USER_NOT_LISTED)

        assert status == 200
        mock_writer_cls.assert_called_once()
        writer_call = mock_writer_cls.call_args
        flag_in_call = writer_call[0][1] if writer_call[0] else writer_call[1].get("flag_state")
        assert flag_in_call == "shadow", (
            f"Non-allowlisted user: MasteryWriter got '{flag_in_call}', expected 'shadow' (not 'live')"
        )

    def test_live_non_allowlisted_no_live_mode_call(self, monkeypatch):
        """D. requested live; non-allowlisted user → claim is never called with 'live'."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_ALLOWLISTED)

        sb = _seeded_db_for_user(USER_NOT_LISTED)
        live_calls: list[str] = []

        real_claim = svc.claim_mastery_retry_required

        def _spy_claim(supabase: Any, attempt_id: str, flag_state: str) -> Any:
            if flag_state == "live":
                live_calls.append(flag_state)
            return real_claim(supabase, attempt_id, flag_state)

        with patch.object(mock_engine_api, "claim_mastery_retry_required", side_effect=_spy_claim):
            with (
                patch.object(mock_engine_api, "MasteryWriter") as mock_writer_cls,
                patch.object(mock_engine_api, "complete_mastery_retry_required"),
                patch.object(mock_engine_api, "mastery_retry_done", return_value=False),
            ):
                mock_writer_instance = MagicMock()

                async def _noop(*a, **kw):
                    pass

                mock_writer_instance.process_attempt.side_effect = _noop
                mock_writer_cls.return_value = mock_writer_instance

                _, status = _start_and_submit(sb, USER_NOT_LISTED)

        assert status == 200
        assert live_calls == [], (
            "Non-allowlisted user triggered a live-mode claim — the allowlist is not enforced."
        )


# ── test E: FF=live + empty allowlist → effective shadow ─────────────────────

class TestFlagLiveEmptyAllowlist:
    def test_empty_allowlist_claim_receives_shadow(self, monkeypatch):
        """E. FF=live + empty allowlist → effective shadow; claim receives 'shadow'."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", "")

        sb = _seeded_db_for_user(USER_ALLOWLISTED)

        with (
            patch.object(mock_engine_api, "mastery_retry_done", return_value=False),
            patch.object(mock_engine_api, "claim_mastery_retry_required", return_value="job-empty-shadow") as mock_claim,
            patch.object(mock_engine_api, "MasteryWriter") as mock_writer_cls,
            patch.object(mock_engine_api, "complete_mastery_retry_required"),
        ):
            mock_writer_instance = MagicMock()

            async def _noop(*a, **kw):
                pass

            mock_writer_instance.process_attempt.side_effect = _noop
            mock_writer_cls.return_value = mock_writer_instance

            _, status = _start_and_submit(sb, USER_ALLOWLISTED)

        assert status == 200
        mock_claim.assert_called_once()
        _, call_args, call_kwargs = mock_claim.mock_calls[0]
        effective_flag_passed = call_args[2] if len(call_args) > 2 else call_kwargs.get("flag_state")
        assert effective_flag_passed == "shadow", (
            f"Empty allowlist: claim received '{effective_flag_passed}', expected 'shadow'"
        )

    def test_malformed_allowlist_uses_resolver_fail_closed(self, monkeypatch):
        """E. malformed allowlist (spaces/garbage) uses resolver fail-closed → shadow."""
        # The resolver itself handles malformed lists; the API must not re-parse.
        # Whitespace-only is treated as empty by the resolver → shadow.
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", "   ,   ,   ")

        sb = _seeded_db_for_user(USER_ALLOWLISTED)

        with (
            patch.object(mock_engine_api, "mastery_retry_done", return_value=False),
            patch.object(mock_engine_api, "claim_mastery_retry_required", return_value="job-malform") as mock_claim,
            patch.object(mock_engine_api, "MasteryWriter") as mock_writer_cls,
            patch.object(mock_engine_api, "complete_mastery_retry_required"),
        ):
            mock_writer_instance = MagicMock()

            async def _noop(*a, **kw):
                pass

            mock_writer_instance.process_attempt.side_effect = _noop
            mock_writer_cls.return_value = mock_writer_instance

            _, status = _start_and_submit(sb, USER_ALLOWLISTED)

        assert status == 200
        mock_claim.assert_called_once()
        _, call_args, call_kwargs = mock_claim.mock_calls[0]
        effective_flag_passed = call_args[2] if len(call_args) > 2 else call_kwargs.get("flag_state")
        assert effective_flag_passed == "shadow", (
            f"Malformed allowlist: claim received '{effective_flag_passed}', expected 'shadow'"
        )


# ── test F: idempotency — already done with effective flag ────────────────────

class TestIdempotency:
    def test_already_done_with_effective_flag_no_new_claim(self, monkeypatch):
        """F. effective-mode retry already done → no new claim or writer execution."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _seeded_db_for_user(USER_ALLOWLISTED)

        # mastery_retry_done returns True → already completed; skip claim
        with (
            patch.object(mock_engine_api, "mastery_retry_done", return_value=True) as mock_done,
            patch.object(mock_engine_api, "claim_mastery_retry_required") as mock_claim,
            patch.object(mock_engine_api, "MasteryWriter") as mock_writer_cls,
        ):
            # Pre-submit the attempt so was_submitted=True
            start_r_pre = _client_for_user(sb, USER_ALLOWLISTED).post(
                "/api/study/mocks/attempts/start", json={"template_slug": "test-mock-allowlist"}
            )
            attempt_id = start_r_pre.json()["attempt_id"]
            # Force attempt status to "submitted" in the stub
            for row in sb.db["mock_attempts"]:
                if row["id"] == attempt_id:
                    row["status"] = "submitted"
            # Submit again — was_submitted=True, mastery_retry_done=True → no claim
            client = _client_for_user(sb, USER_ALLOWLISTED)
            sub_r = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")

        assert sub_r.status_code == 200
        # mastery_retry_done is called with effective flag = "shadow"
        mock_done.assert_called_once()
        _, call_args, call_kwargs = mock_done.mock_calls[0]
        effective_flag_passed = call_args[2] if len(call_args) > 2 else call_kwargs.get("flag_state")
        assert effective_flag_passed == "shadow"
        # Because done, no new claim
        mock_claim.assert_not_called()
        mock_writer_cls.assert_not_called()

    def test_live_non_allowlisted_done_check_uses_shadow_not_live(self, monkeypatch):
        """F. non-allowlisted user re-submit: idempotency checked with 'shadow', never 'live'.

        mastery_retry_done is only consulted on re-submit (was_submitted=True).
        Set up by running a first submit, then run a second submit with the spy.
        """
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_ALLOWLISTED)

        sb = _seeded_db_for_user(USER_NOT_LISTED)

        # First submit: put the attempt in submitted state
        attempt_id, first_status = _start_and_submit(sb, USER_NOT_LISTED)
        assert first_status == 200

        done_calls: list[str] = []

        def _spy_done(supabase: Any, attempt_id: str, flag_state: str) -> bool:
            done_calls.append(flag_state)
            return True  # already done — no claim should follow

        with (
            patch.object(mock_engine_api, "mastery_retry_done", side_effect=_spy_done),
            patch.object(mock_engine_api, "claim_mastery_retry_required") as mock_claim,
        ):
            client = _client_for_user(sb, USER_NOT_LISTED)
            sub_r = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")

        assert sub_r.status_code == 200
        assert "live" not in done_calls, (
            "mastery_retry_done was called with 'live' for a non-allowlisted user"
        )
        assert "shadow" in done_calls, (
            "mastery_retry_done was never called with 'shadow' for non-allowlisted user"
        )
        # done=True → no new claim
        mock_claim.assert_not_called()


# ── test G: claim failure → 503 preserved ────────────────────────────────────

class TestClaimFailure:
    def test_claim_failure_returns_503(self, monkeypatch):
        """G. claim_mastery_retry_required raises → 503 mastery_retry_claim_failed."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _seeded_db_for_user(USER_ALLOWLISTED)

        def _raise_claim(supabase: Any, attempt_id: str, flag_state: str) -> None:
            raise RuntimeError("DB unavailable")

        with (
            patch.object(mock_engine_api, "mastery_retry_done", return_value=False),
            patch.object(mock_engine_api, "claim_mastery_retry_required", side_effect=_raise_claim),
        ):
            client = _client_for_user(sb, USER_ALLOWLISTED)
            start_r = client.post(
                "/api/study/mocks/attempts/start", json={"template_slug": "test-mock-allowlist"}
            )
            attempt_id = start_r.json()["attempt_id"]
            sub_r = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")

        assert sub_r.status_code == 503
        detail = sub_r.json()["detail"]
        assert detail["error"] == "mastery_retry_claim_failed"
        assert sub_r.headers["Retry-After"] == "1"


# ── test H: writer failure → deferred (mark_pending), not 500 ────────────────

class TestWriterFailure:
    def test_classification_not_ready_defers_to_pending(self, monkeypatch):
        """H. MasteryClassificationNotReady → mark_mastery_retry_pending_required called; HTTP 200."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _seeded_db_for_user(USER_ALLOWLISTED)
        claimed_job_id = "job-class-not-ready"

        async def _raise_not_ready(*a, **kw):
            from app.study_os.mastery_writer import MasteryClassificationNotReady
            raise MasteryClassificationNotReady("missing=3 duplicate=0")

        with (
            patch.object(mock_engine_api, "mastery_retry_done", return_value=False),
            patch.object(mock_engine_api, "claim_mastery_retry_required", return_value=claimed_job_id),
            patch.object(mock_engine_api, "MasteryWriter") as mock_writer_cls,
            patch.object(mock_engine_api, "mark_mastery_retry_pending_required") as mock_pending,
            patch.object(mock_engine_api, "complete_mastery_retry_required") as mock_complete,
        ):
            mock_writer_instance = MagicMock()
            mock_writer_instance.process_attempt.side_effect = _raise_not_ready
            mock_writer_cls.return_value = mock_writer_instance

            client = _client_for_user(sb, USER_ALLOWLISTED)
            start_r = client.post(
                "/api/study/mocks/attempts/start", json={"template_slug": "test-mock-allowlist"}
            )
            attempt_id = start_r.json()["attempt_id"]
            sub_r = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")

        # Classification not ready is a DEFERRAL, not a hard failure — HTTP 200
        assert sub_r.status_code == 200
        # Job rescheduled as pending, not completed
        mock_pending.assert_called_once()
        mock_complete.assert_not_called()

    def test_generic_writer_failure_defers_and_returns_200(self, monkeypatch):
        """H. Generic writer failure → mark_mastery_retry_pending_required; HTTP 200."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _seeded_db_for_user(USER_ALLOWLISTED)
        claimed_job_id = "job-generic-fail"

        async def _raise_generic(*a, **kw):
            raise RuntimeError("Something went wrong in mastery")

        with (
            patch.object(mock_engine_api, "mastery_retry_done", return_value=False),
            patch.object(mock_engine_api, "claim_mastery_retry_required", return_value=claimed_job_id),
            patch.object(mock_engine_api, "MasteryWriter") as mock_writer_cls,
            patch.object(mock_engine_api, "mark_mastery_retry_pending_required") as mock_pending,
            patch.object(mock_engine_api, "complete_mastery_retry_required") as mock_complete,
        ):
            mock_writer_instance = MagicMock()
            mock_writer_instance.process_attempt.side_effect = _raise_generic
            mock_writer_cls.return_value = mock_writer_instance

            client = _client_for_user(sb, USER_ALLOWLISTED)
            start_r = client.post(
                "/api/study/mocks/attempts/start", json={"template_slug": "test-mock-allowlist"}
            )
            attempt_id = start_r.json()["attempt_id"]
            sub_r = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")

        # Generic failure → deferred to pending retry; HTTP 200 (mastery failure non-blocking)
        assert sub_r.status_code == 200
        mock_pending.assert_called_once()
        mock_complete.assert_not_called()

    def test_reschedule_failure_returns_503(self, monkeypatch):
        """H. If mark_mastery_retry_pending_required also fails → 503 mastery_retry_enqueue_failed."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _seeded_db_for_user(USER_ALLOWLISTED)

        async def _raise_writer(*a, **kw):
            raise RuntimeError("writer failed")

        def _raise_pending(*a, **kw):
            raise RuntimeError("DB unavailable for reschedule")

        with (
            patch.object(mock_engine_api, "mastery_retry_done", return_value=False),
            patch.object(mock_engine_api, "claim_mastery_retry_required", return_value="job-reschedule-fail"),
            patch.object(mock_engine_api, "MasteryWriter") as mock_writer_cls,
            patch.object(mock_engine_api, "mark_mastery_retry_pending_required", side_effect=_raise_pending),
        ):
            mock_writer_instance = MagicMock()
            mock_writer_instance.process_attempt.side_effect = _raise_writer
            mock_writer_cls.return_value = mock_writer_instance

            client = _client_for_user(sb, USER_ALLOWLISTED)
            start_r = client.post(
                "/api/study/mocks/attempts/start", json={"template_slug": "test-mock-allowlist"}
            )
            attempt_id = start_r.json()["attempt_id"]
            sub_r = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")

        assert sub_r.status_code == 503
        detail = sub_r.json()["detail"]
        assert detail["error"] == "mastery_retry_enqueue_failed"
        assert sub_r.headers["Retry-After"] == "1"


# ── get_or_resolve_pinned_mastery_flag integration ───────────────────────────

class TestGetOrResolvePinnedMasteryFlagCalledCorrectly:
    def test_pinned_flag_called_with_sb_attempt_user(self, monkeypatch):
        """Confirm the endpoint calls get_or_resolve_pinned_mastery_flag(sb, attempt_id, user_id).

        With no existing mastery jobs (fresh submit), the function falls through
        to resolve_effective_mastery_flag(get_mastery_write_flag(), user_id) and
        returns 'live' for an allowlisted user.
        """
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_ALLOWLISTED)

        sb = _seeded_db_for_user(USER_ALLOWLISTED)
        pinned_calls: list[tuple] = []

        from app.study_os import mock_engine as svc_mod
        real_pinned = svc_mod.get_or_resolve_pinned_mastery_flag

        def _spy_pinned(supabase: Any, attempt_id: str, user_id: str) -> str:
            pinned_calls.append((attempt_id, user_id))
            return real_pinned(supabase, attempt_id, user_id)

        with (
            patch.object(mock_engine_api, "get_or_resolve_pinned_mastery_flag", side_effect=_spy_pinned),
            patch.object(mock_engine_api, "mastery_retry_done", return_value=False),
            patch.object(mock_engine_api, "claim_mastery_retry_required", return_value=None),
        ):
            attempt_id, status = _start_and_submit(sb, USER_ALLOWLISTED)

        assert status == 200
        assert len(pinned_calls) == 1, "get_or_resolve_pinned_mastery_flag must be called exactly once"
        called_attempt, called_user = pinned_calls[0]
        assert called_attempt == attempt_id, f"Expected attempt_id in call, got '{called_attempt}'"
        assert called_user == USER_ALLOWLISTED, f"Expected user_id in call, got '{called_user}'"

    def test_pinned_flag_off_skips_mastery(self, monkeypatch):
        """When pinned flag resolves to 'off', mastery_retry_done is not consulted."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "off")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _seeded_db_for_user(USER_ALLOWLISTED)

        with (
            patch.object(mock_engine_api, "mastery_retry_done") as mock_done,
        ):
            _start_and_submit(sb, USER_ALLOWLISTED)

        # get_or_resolve_pinned_mastery_flag returns 'off' → mastery_retry_done not called
        mock_done.assert_not_called()
