"""Pinned-mode mastery flag regression tests.

Verifies that get_or_resolve_pinned_mastery_flag correctly pins the mastery
mode for an attempt, preventing races where a FF or allowlist change between
submit and a later analytics_retry produces conflicting live+shadow jobs.

Coverage:
  1. Manual submit pins live → analytics defers → FF changes → analytics retry reuses live
  2. Manual submit pins shadow → user added to allowlist → analytics retry stays shadow
  3. Auto-submit: schedules only analytics_retry, no eager mastery enqueue
  4. Conflicting modes: get_or_resolve_pinned_mastery_flag returns shadow (fail closed)
  5. Correction recovery uses pinned mode, not "latest" env resolution
"""
from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.study_os import mock_engine as svc
from app.study_os.mock_engine import (
    JOB_ANALYTICS_RETRY,
    JOB_MASTERY_RETRY,
    get_or_resolve_pinned_mastery_flag,
)
from tests.persona_questions._stub import SBStub

# ── UUID-shaped constants ──────────────────────────────────────────────────────

USER_LIVE = "b0000001-0000-0000-0000-000000000001"
USER_SHADOW = "b0000002-0000-0000-0000-000000000002"
ATTEMPT_A = "aaaaaaaa-1111-0000-0000-000000000001"
ATTEMPT_B = "aaaaaaaa-2222-0000-0000-000000000002"


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_mastery_job(attempt_id: str, flag_state: str, status: str = "pending") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "job_kind": JOB_MASTERY_RETRY,
        "attempt_id": attempt_id,
        "mastery_flag_state": flag_state,
        "status": status,
        "scheduled_for": "2026-01-01T00:00:00+00:00",
        "attempts": 0,
        "last_error": None,
    }


def _make_sb_with_jobs(jobs: list[dict]) -> SBStub:
    return SBStub({
        "mock_attempt_jobs": jobs,
        "mock_attempts": [
            {"id": ATTEMPT_A, "user_id": USER_LIVE, "status": "submitted"},
            {"id": ATTEMPT_B, "user_id": USER_SHADOW, "status": "submitted"},
        ],
    })


# ── Test 1: pinned live survives FF change ─────────────────────────────────────

class TestPinnedLiveSurvivesFFChange:
    def test_existing_live_job_returns_live_even_if_ff_is_off(self, monkeypatch):
        """1. Existing live mastery_retry job → returns 'live' regardless of current FF."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "off")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _make_sb_with_jobs([
            _make_mastery_job(ATTEMPT_A, "live", status="pending"),
        ])
        result = get_or_resolve_pinned_mastery_flag(sb, ATTEMPT_A, USER_LIVE)
        assert result == "live", (
            f"Expected 'live' (pinned from job), got '{result}'"
        )

    def test_existing_live_job_returns_live_even_if_ff_is_shadow(self, monkeypatch):
        """1. FF flipped to shadow after live submit → pinned job keeps 'live'."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _make_sb_with_jobs([
            _make_mastery_job(ATTEMPT_A, "live", status="running"),
        ])
        result = get_or_resolve_pinned_mastery_flag(sb, ATTEMPT_A, USER_LIVE)
        assert result == "live"

    def test_existing_live_job_done_returns_live(self, monkeypatch):
        """1. A done live mastery job is still not cancelled → pinned 'live'."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _make_sb_with_jobs([
            _make_mastery_job(ATTEMPT_A, "live", status="done"),
        ])
        result = get_or_resolve_pinned_mastery_flag(sb, ATTEMPT_A, USER_LIVE)
        assert result == "live"

    def test_cancelled_job_ignored_falls_through_to_env(self, monkeypatch):
        """1. Only cancelled jobs → no pin → resolve from env."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _make_sb_with_jobs([
            _make_mastery_job(ATTEMPT_A, "live", status="cancelled"),
        ])
        result = get_or_resolve_pinned_mastery_flag(sb, ATTEMPT_A, USER_LIVE)
        # No pin → resolve from env: FF=shadow → returns shadow
        assert result == "shadow"

    def test_permanently_failed_job_ignored_falls_through_to_env(self, monkeypatch):
        """1. Only failed_permanent jobs → no pin → resolve from env."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_LIVE)

        sb = _make_sb_with_jobs([
            _make_mastery_job(ATTEMPT_A, "shadow", status="failed_permanent"),
        ])
        result = get_or_resolve_pinned_mastery_flag(sb, ATTEMPT_A, USER_LIVE)
        # No pin → resolve from env: FF=live, user in allowlist → returns live
        assert result == "live"


# ── Test 2: pinned shadow survives allowlist change ───────────────────────────

class TestPinnedShadowSurvivesAllowlistChange:
    def test_existing_shadow_job_returns_shadow_even_after_user_added_to_allowlist(
        self, monkeypatch
    ):
        """2. Shadow job pinned → user added to allowlist later → stays shadow."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_SHADOW)  # now in allowlist

        sb = _make_sb_with_jobs([
            _make_mastery_job(ATTEMPT_B, "shadow", status="pending"),
        ])
        result = get_or_resolve_pinned_mastery_flag(sb, ATTEMPT_B, USER_SHADOW)
        assert result == "shadow", (
            f"Expected 'shadow' (pinned from original job), got '{result}'"
        )

    def test_no_jobs_with_live_ff_and_user_in_allowlist_returns_live(self, monkeypatch):
        """2. No existing job → fall through to env: FF=live + in allowlist → live."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_SHADOW)

        sb = _make_sb_with_jobs([])
        result = get_or_resolve_pinned_mastery_flag(sb, ATTEMPT_B, USER_SHADOW)
        assert result == "live"

    def test_no_jobs_with_live_ff_and_user_not_in_allowlist_returns_shadow(
        self, monkeypatch
    ):
        """2. No existing job → fall through to env: FF=live + NOT in allowlist → shadow."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_LIVE)  # only USER_LIVE

        sb = _make_sb_with_jobs([])
        result = get_or_resolve_pinned_mastery_flag(sb, ATTEMPT_B, USER_SHADOW)
        assert result == "shadow"


# ── Test 3: auto_submit schedules only analytics_retry ────────────────────────

class TestAutoSubmitNoEagerMastery:
    def test_auto_submit_schedules_analytics_not_mastery(self, monkeypatch):
        """3. auto_submit_attempt enqueues analytics_retry only, not mastery_retry."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        import uuid as _uuid
        from datetime import datetime, timezone, timedelta

        attempt_id = str(_uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = (now - timedelta(minutes=5)).isoformat()

        sb = SBStub({
            "mock_attempts": [{
                "id": attempt_id,
                "user_id": USER_SHADOW,
                "status": "in_progress",
                "expires_at": expires_at,
                "template_snapshot": {"negative_marking": False},
            }],
            "mock_attempt_responses": [],
            "mock_attempt_events": [],
            "mock_tests": [],
            "mock_attempt_jobs": [],
            "mock_mastery_shadow": [],
            "mock_attempt_response_classification": [],
            "user_topic_mastery": [],
            "user_topic_mastery_audit": [],
            "user_topic_error_patterns": [],
        })

        svc.auto_submit_attempt(sb, attempt_id)

        all_jobs = sb.db.get("mock_attempt_jobs", [])
        job_kinds = [j.get("job_kind") for j in all_jobs]

        assert JOB_ANALYTICS_RETRY in job_kinds, (
            "auto_submit_attempt did not enqueue analytics_retry"
        )
        assert JOB_MASTERY_RETRY not in job_kinds, (
            "auto_submit_attempt eagerly enqueued mastery_retry (should not)"
        )

    def test_auto_submit_no_mastery_even_when_ff_live(self, monkeypatch):
        """3. FF=live + user in allowlist → auto_submit still only enqueues analytics."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_LIVE)

        import uuid as _uuid
        from datetime import datetime, timezone, timedelta

        attempt_id = str(_uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = (now - timedelta(minutes=5)).isoformat()

        sb = SBStub({
            "mock_attempts": [{
                "id": attempt_id,
                "user_id": USER_LIVE,
                "status": "in_progress",
                "expires_at": expires_at,
                "template_snapshot": {"negative_marking": False},
            }],
            "mock_attempt_responses": [],
            "mock_attempt_events": [],
            "mock_tests": [],
            "mock_attempt_jobs": [],
            "mock_mastery_shadow": [],
            "mock_attempt_response_classification": [],
            "user_topic_mastery": [],
            "user_topic_mastery_audit": [],
            "user_topic_error_patterns": [],
        })

        svc.auto_submit_attempt(sb, attempt_id)

        all_jobs = sb.db.get("mock_attempt_jobs", [])
        mastery_jobs = [j for j in all_jobs if j.get("job_kind") == JOB_MASTERY_RETRY]

        assert mastery_jobs == [], (
            f"auto_submit_attempt enqueued {len(mastery_jobs)} mastery_retry jobs — expected none"
        )


# ── Test 4: conflicting modes → shadow (fail closed) ─────────────────────────

class TestConflictingModes:
    def test_both_live_and_shadow_jobs_returns_shadow(self, monkeypatch):
        """4. Both live and shadow mastery_retry jobs → fail closed to 'shadow'."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_LIVE)

        sb = _make_sb_with_jobs([
            _make_mastery_job(ATTEMPT_A, "live", status="pending"),
            _make_mastery_job(ATTEMPT_A, "shadow", status="pending"),
        ])
        result = get_or_resolve_pinned_mastery_flag(sb, ATTEMPT_A, USER_LIVE)
        assert result == "shadow", (
            f"Conflicting modes: expected 'shadow' (fail closed), got '{result}'"
        )

    def test_both_live_and_shadow_jobs_logs_error(self, monkeypatch, caplog):
        """4. Both live and shadow mastery_retry jobs → logs MASTERY_MODE_CONFLICT."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_LIVE)

        sb = _make_sb_with_jobs([
            _make_mastery_job(ATTEMPT_A, "live", status="running"),
            _make_mastery_job(ATTEMPT_A, "shadow", status="done"),
        ])

        import logging
        with caplog.at_level(logging.ERROR, logger="career_copilot.study_os.mock_engine"):
            get_or_resolve_pinned_mastery_flag(sb, ATTEMPT_A, USER_LIVE)

        assert any("MASTERY_MODE_CONFLICT" in r.message for r in caplog.records), (
            "Expected MASTERY_MODE_CONFLICT error log"
        )

    def test_single_mode_with_multiple_jobs_same_flag_returns_that_flag(self, monkeypatch):
        """4. Multiple jobs all with same flag → returns that flag (not a conflict)."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "off")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = _make_sb_with_jobs([
            _make_mastery_job(ATTEMPT_A, "shadow", status="pending"),
            _make_mastery_job(ATTEMPT_A, "shadow", status="done"),
        ])
        result = get_or_resolve_pinned_mastery_flag(sb, ATTEMPT_A, USER_LIVE)
        assert result == "shadow"


# ── Test 5: correction recovery uses pinned mode ──────────────────────────────

class TestCorrectionRecoveryPinnedMode:
    def test_recover_corrections_uses_pinned_mode_not_current_env(self, monkeypatch):
        """5. _recover_corrections_after_mock_tests uses get_or_resolve_pinned_mastery_flag."""
        # FF is currently shadow, but the attempt had a live mastery job — so the
        # correction recovery must use 'live' (the pinned mode).
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = SBStub({
            "mock_attempt_jobs": [
                _make_mastery_job(ATTEMPT_A, "live", status="done"),
            ],
            "mock_attempts": [
                {"id": ATTEMPT_A, "user_id": USER_LIVE, "status": "submitted"},
            ],
            "mock_mastery_shadow": [],
        })

        writer_calls: list[str] = []

        class _FakeMasteryWriter:
            def __init__(self, supabase: Any, flag_state: str):
                self._flag = flag_state

            def redraft_corrections(self, attempt_id: str) -> None:
                writer_calls.append(self._flag)

        # MasteryWriter is imported lazily inside _recover_corrections_after_mock_tests,
        # so patch it at its source module (mastery_writer).
        with patch("app.study_os.mastery_writer.MasteryWriter", _FakeMasteryWriter):
            # Also patch _retry_emit_mock_tests_row since sb has no compat row path
            with patch("app.study_os.mock_engine._retry_emit_mock_tests_row"):
                svc._recover_corrections_after_mock_tests(sb, ATTEMPT_A)

        assert writer_calls == ["live"], (
            f"Expected correction recovery to use 'live' (pinned), but used {writer_calls}"
        )

    def test_recover_corrections_conflict_uses_shadow(self, monkeypatch):
        """5. Conflicting modes → correction recovery fails closed to shadow."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_LIVE)

        sb = SBStub({
            "mock_attempt_jobs": [
                _make_mastery_job(ATTEMPT_A, "live", status="done"),
                _make_mastery_job(ATTEMPT_A, "shadow", status="done"),
            ],
            "mock_attempts": [
                {"id": ATTEMPT_A, "user_id": USER_LIVE, "status": "submitted"},
            ],
            "mock_mastery_shadow": [],
        })

        writer_calls: list[str] = []

        class _FakeMasteryWriter:
            def __init__(self, supabase: Any, flag_state: str):
                self._flag = flag_state

            def redraft_corrections(self, attempt_id: str) -> None:
                writer_calls.append(self._flag)

        with patch("app.study_os.mastery_writer.MasteryWriter", _FakeMasteryWriter):
            with patch("app.study_os.mock_engine._retry_emit_mock_tests_row"):
                svc._recover_corrections_after_mock_tests(sb, ATTEMPT_A)

        assert writer_calls == ["shadow"], (
            f"Expected conflict to fail closed to 'shadow', but got {writer_calls}"
        )

    def test_recover_corrections_no_mastery_job_falls_through_to_env(self, monkeypatch):
        """5. No mastery job → correction recovery resolves from env (shadow when FF=off)."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "off")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)

        sb = SBStub({
            "mock_attempt_jobs": [],
            "mock_attempts": [
                {"id": ATTEMPT_A, "user_id": USER_LIVE, "status": "submitted"},
            ],
            "mock_mastery_shadow": [],
        })

        writer_calls: list[str] = []

        class _FakeMasteryWriter:
            def __init__(self, supabase: Any, flag_state: str):
                self._flag = flag_state

            def redraft_corrections(self, attempt_id: str) -> None:
                writer_calls.append(self._flag)

        with patch("app.study_os.mastery_writer.MasteryWriter", _FakeMasteryWriter):
            with patch("app.study_os.mock_engine._retry_emit_mock_tests_row"):
                svc._recover_corrections_after_mock_tests(sb, ATTEMPT_A)

        # FF=off → resolves to "off" → MasteryWriter("off") → redraft_corrections is a no-op
        # But we still call it with "off"; redraft_corrections on live check returns early.
        assert writer_calls == ["off"]
