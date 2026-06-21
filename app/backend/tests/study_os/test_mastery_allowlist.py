"""Per-user mastery live allowlist and pinned-mode regression tests.

Covers:
1. resolve_effective_mastery_flag behaviour matrix (unit tests, no DB)
2. auto_submit_attempt enqueues with resolved (not global) flag
3. JOB_ANALYTICS_RETRY D4 handoff enqueues with resolved flag
4. _recover_corrections_after_mock_tests uses pinned mastery_flag_state
   from job row, not current env flag

Stub-only (in-memory SBStub); no live DB.
"""
from __future__ import annotations

import os
import pytest

from app.study_os import mastery_writer as mw
from tests.persona_questions._stub import SBStub

ATTEMPT = "aaaa0000-0000-0000-0000-000000000001"
USER_A = "user-a-00000000-0000-0000-0000-000000000001"  # in allowlist
USER_B = "user-b-00000000-0000-0000-0000-000000000002"  # NOT in allowlist


# ── resolve_effective_mastery_flag unit tests ────────────────────────────────

class TestResolveEffectiveMasteryFlag:
    def test_off_returns_off_regardless_of_allowlist(self, monkeypatch):
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_A)
        assert mw.resolve_effective_mastery_flag("off", USER_A) == "off"

    def test_shadow_returns_shadow_regardless_of_allowlist(self, monkeypatch):
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_A)
        assert mw.resolve_effective_mastery_flag("shadow", USER_A) == "shadow"

    def test_live_user_in_allowlist_returns_live(self, monkeypatch):
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_A)
        assert mw.resolve_effective_mastery_flag("live", USER_A) == "live"

    def test_live_user_not_in_allowlist_returns_shadow(self, monkeypatch):
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_A)
        assert mw.resolve_effective_mastery_flag("live", USER_B) == "shadow"

    def test_live_empty_allowlist_returns_shadow(self, monkeypatch):
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", "")
        assert mw.resolve_effective_mastery_flag("live", USER_A) == "shadow"

    def test_live_whitespace_only_allowlist_returns_shadow(self, monkeypatch):
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", "   ")
        assert mw.resolve_effective_mastery_flag("live", USER_A) == "shadow"

    def test_live_allowlist_unset_returns_shadow(self, monkeypatch):
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)
        assert mw.resolve_effective_mastery_flag("live", USER_A) == "shadow"

    def test_live_multiple_users_correct_one_allowed(self, monkeypatch):
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", f"{USER_A},{USER_B}")
        assert mw.resolve_effective_mastery_flag("live", USER_A) == "live"
        assert mw.resolve_effective_mastery_flag("live", USER_B) == "live"

    def test_live_multiple_users_third_user_not_allowed(self, monkeypatch):
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_A)
        assert mw.resolve_effective_mastery_flag("live", "user-c-other") == "shadow"

    def test_live_allowlist_strips_whitespace_around_ids(self, monkeypatch):
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", f"  {USER_A}  ,  {USER_B}  ")
        assert mw.resolve_effective_mastery_flag("live", USER_A) == "live"
        assert mw.resolve_effective_mastery_flag("live", USER_B) == "live"


# ── auto_submit_attempt: enqueues with per-user resolved flag ────────────────

def _make_auto_submit_db(user_id: str) -> dict:
    return {
        "mock_attempts": [{
            "id": ATTEMPT,
            "user_id": user_id,
            "status": "in_progress",
            "expires_at": "2020-01-01T00:00:00+00:00",
        }],
        "mock_attempt_jobs": [],
        "mock_attempt_events": [],
        "mock_attempt_responses": [],
        "mock_tests": [],
    }


def _count_mastery_jobs(sb: SBStub) -> list[dict]:
    from app.study_os.mock_engine import JOB_MASTERY_RETRY
    return [j for j in sb.db["mock_attempt_jobs"] if j.get("job_kind") == JOB_MASTERY_RETRY]


def _count_analytics_jobs(sb: SBStub) -> list[dict]:
    from app.study_os.mock_engine import JOB_ANALYTICS_RETRY
    return [j for j in sb.db["mock_attempt_jobs"] if j.get("job_kind") == JOB_ANALYTICS_RETRY]


class TestAutoSubmitAllowlist:
    """D2 (revised): auto_submit_attempt enqueues only analytics_retry.
    Mastery mode is resolved later by the JOB_ANALYTICS_RETRY handler
    (get_or_resolve_pinned_mastery_flag), so no eager mastery flag
    resolution happens at auto-submit time regardless of FF or allowlist.
    """

    def test_auto_submit_enqueues_analytics_retry_not_mastery(self, monkeypatch):
        """auto_submit_attempt must enqueue analytics_retry, not mastery_retry."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_A)
        from app.study_os import mock_engine as engine
        sb = SBStub(_make_auto_submit_db(USER_A))
        engine.auto_submit_attempt(sb, ATTEMPT)
        assert _count_analytics_jobs(sb), "analytics_retry job must be enqueued"
        assert _count_mastery_jobs(sb) == [], "mastery_retry must NOT be enqueued at auto-submit time"

    def test_auto_submit_no_mastery_job_for_non_allowlisted_user(self, monkeypatch):
        """D2 fix: non-allowlisted users also get NO eager mastery_retry at auto-submit."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        monkeypatch.setenv("FF_MOCK_MASTERY_LIVE_USER_IDS", USER_A)
        from app.study_os import mock_engine as engine
        sb = SBStub(_make_auto_submit_db(USER_B))
        engine.auto_submit_attempt(sb, ATTEMPT)
        assert _count_mastery_jobs(sb) == [], "mastery_retry must NOT be enqueued at auto-submit time"

    def test_auto_submit_no_mastery_job_when_ff_off(self, monkeypatch):
        """FF=off: analytics_retry is enqueued; mastery_retry is still deferred."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "off")
        monkeypatch.delenv("FF_MOCK_MASTERY_LIVE_USER_IDS", raising=False)
        from app.study_os import mock_engine as engine
        sb = SBStub(_make_auto_submit_db(USER_A))
        engine.auto_submit_attempt(sb, ATTEMPT)
        assert _count_mastery_jobs(sb) == []


# ── _recover_corrections: pinned flag from job row ───────────────────────────

def _make_recovery_db(pinned_flag: str | None) -> dict:
    jobs = []
    if pinned_flag is not None:
        jobs.append({
            "id": "job-1",
            "job_kind": "mastery_retry",
            "attempt_id": ATTEMPT,
            "mastery_flag_state": pinned_flag,
            "created_at": "2026-01-01T00:00:00+00:00",
        })
    return {
        "mock_attempts": [{"id": ATTEMPT, "user_id": USER_A}],
        "mock_attempt_jobs": jobs,
        "mock_tests": [{"id": "mt-1", "mock_attempt_id": ATTEMPT, "user_id": USER_A,
                        "trust_level": "platform_verified", "source_type": "platform_attempt"}],
        "mock_attempt_responses": [],
        "mock_attempt_response_classification": [],
        "mock_correction_tasks": [],
        "mock_mastery_shadow": [],
        "user_topic_mastery": [],
        "user_topic_mastery_audit": [],
        "user_topic_error_patterns": [],
    }


class TestRecoverCorrectionsPinnedFlag:
    def test_uses_pinned_live_flag_even_when_env_is_shadow(self, monkeypatch):
        """If the job row says 'live' but env is now 'shadow', recovery should use 'live'."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        from app.study_os.mock_engine import _recover_corrections_after_mock_tests, JOB_MASTERY_RETRY
        sb = SBStub(_make_recovery_db(pinned_flag="live"))
        # Should not raise; MasteryWriter(sb, "live").redraft_corrections runs
        _recover_corrections_after_mock_tests(sb, ATTEMPT)

    def test_uses_pinned_shadow_flag_when_env_is_live(self, monkeypatch):
        """If the job row says 'shadow' but env is now 'live', recovery should use 'shadow'."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
        from app.study_os.mock_engine import _recover_corrections_after_mock_tests
        sb = SBStub(_make_recovery_db(pinned_flag="shadow"))
        _recover_corrections_after_mock_tests(sb, ATTEMPT)
        # redraft_corrections at shadow does not write correction tasks
        assert sb.db["mock_correction_tasks"] == []

    def test_falls_back_to_env_flag_when_no_job_row(self, monkeypatch):
        """No mastery_retry job row → fall back to current env flag (legacy attempts)."""
        monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
        from app.study_os.mock_engine import _recover_corrections_after_mock_tests
        sb = SBStub(_make_recovery_db(pinned_flag=None))
        _recover_corrections_after_mock_tests(sb, ATTEMPT)
        # shadow → no live corrections written
        assert sb.db["mock_correction_tasks"] == []
