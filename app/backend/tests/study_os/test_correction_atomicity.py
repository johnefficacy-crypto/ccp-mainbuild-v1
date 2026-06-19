"""PR-5B — atomic correction-draft persistence tests.

Covers the defects fixed by migration 182 + Python changes:

  D1 (generated path): batch insert skips non-conflicting rows on 23505
  D2 (manual path):    delete-before-insert loses prior drafts on insert failure
  D3 (manual path):    23505 catch fetches existing rows, non-conflicting rows lost
  D4 (manual path):    review_state update wrapped in _safe — failure swallowed
  D5 (both paths):     23505 detection via string search catches unrelated errors

Generated-path tests exercise MasteryWriter._draft_correction_tasks via
ensure_mock_correction_draft RPC.  Manual-path tests exercise
mocks.draft_correction_tasks via replace_manual_mock_correction_drafts RPC.
Both use the in-memory SBStub extended with the new RPC handlers.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest

from app.study_os import mastery_writer as mw
from app.study_os import mocks as mocks_service
from app.study_os.mastery_engine.schemas import CorrectionEvidence, CorrectionTaskDraft
from app.study_os.mocks import (
    VALID_CORRECTION_CATEGORIES,
    PlatformAttemptCorrectionForbiddenError,
)
from tests.persona_questions._stub import SBStub

# ── shared constants ───────────────────────────────────────────────────────────

ATTEMPT = "aaaa0000-0000-0000-0000-000000000001"
USER = "user-atomicity"
MOCK_TEST_ID = "mt-atomicity"
TOPIC_A = "topic-alpha"
TOPIC_B = "topic-beta"


@pytest.fixture(autouse=True)
def _reset_metrics():
    mw.correction_metrics.clear()
    yield
    mw.correction_metrics.clear()


# ── helpers ────────────────────────────────────────────────────────────────────

def _seed_generated(sb: SBStub, *, n: int = 3, error_type: str = "concept_gap") -> None:
    sb.db["mock_attempts"] = [{"id": ATTEMPT, "user_id": USER}]
    sb.db["mock_attempt_responses"] = [
        {
            "attempt_id": ATTEMPT,
            "question_id": f"q{i}",
            "selected_option_id": f"opt-{i}",
            "is_correct": False,
            "time_spent_sec": 5,
            "question_snapshot": {
                "topic_id": TOPIC_A,
                "difficulty": "medium",
                "source_type": "authored",
            },
        }
        for i in range(n)
    ]
    sb.db["mock_attempt_response_classification"] = [
        {"attempt_id": ATTEMPT, "question_id": f"q{i}", "error_type": error_type}
        for i in range(n)
    ]
    sb.db["mock_tests"] = [
        {"id": MOCK_TEST_ID, "mock_attempt_id": ATTEMPT, "trust_level": "platform_verified"}
    ]
    sb.db.setdefault("mock_correction_tasks", [])
    sb.db.setdefault("mock_mastery_shadow", [])
    sb.db.setdefault("user_topic_mastery", [])
    sb.db.setdefault("user_topic_mastery_audit", [])
    sb.db.setdefault("user_topic_error_patterns", [])


def _draft(category: str = "concept_gap", topic: str | None = TOPIC_A) -> CorrectionTaskDraft:
    return CorrectionTaskDraft(
        user_id=USER,
        topic_id=topic,
        microtopic_id=None,
        category=category,
        task_type="concept_review",
        priority=3,
        reason="test",
        evidence=CorrectionEvidence(
            accuracy_pct=Decimal("0"),
            error_types=[],
            related_question_ids=["q1", "q2"],
        ),
        estimated_minutes=30,
        source_attempt_id=uuid.uuid4(),
    )


def _make_manual_mock(sb: SBStub, *, source_type: str = "manual_log") -> str:
    """Insert a mock_tests row directly and return its id."""
    mid = str(uuid.uuid4())
    sb.db.setdefault("mock_tests", []).append({
        "id": mid,
        "user_id": USER,
        "source_type": source_type,
        "weak_topics": [TOPIC_A],
        "error_patterns": {"concept": 2},
        "review_state": "unreviewed",
        "mock_attempt_id": None,
        "scored_marks": 50,
        "total_marks": 100,
        "correct_answers": 5,
        "wrong_answers": 3,
        "questions_attempted": 8,
        "duration_mins": 60,
        "test_name": "Test",
        "title": "Test",
        "exam_name": "",
    })
    sb.db.setdefault("mock_correction_tasks", [])
    sb.db.setdefault("mock_subject_breakdowns", [])
    return mid


# ══════════════════════════════════════════════════════════════════════════════
# Generated path (MasteryWriter._draft_correction_tasks)
# ══════════════════════════════════════════════════════════════════════════════

class test_generated_path:

    def test_existing_key_does_not_block_other_keys(self):
        """D1 fix: when one (category, topic) already exists, the other keys
        still persist.  Old batch-insert approach skipped ALL on first 23505."""
        sb = SBStub()
        _seed_generated(sb)

        # Pre-seed one correction so the RPC will find it on first call.
        sb.db["mock_correction_tasks"] = [{
            "id": "pre-existing",
            "mock_test_id": MOCK_TEST_ID,
            "user_id": USER,
            "category": "concept_gap",
            "topic": TOPIC_A,
            "state": "drafted",
            "title": "old title",
            "source_questions": [],
            "study_task_id": None,
            "created_at": None,
            "applied_at": None,
        }]

        # Add a second draft with a different (category, topic) key.
        drafts = [
            _draft("concept_gap", TOPIC_A),   # conflicts with pre-existing
            _draft("speed_issue", TOPIC_A),    # must still persist
        ]
        mw.MasteryWriter(sb, "live")._draft_correction_tasks(ATTEMPT, drafts)

        categories = {r["category"] for r in sb.db["mock_correction_tasks"]
                      if r.get("state") == "drafted"}
        assert "concept_gap" in categories, "pre-existing row must be preserved"
        assert "speed_issue" in categories, "non-conflicting draft must persist"

    def test_null_topic_duplicate_is_idempotent(self):
        """Null-topic duplicate triggers ON CONFLICT DO NOTHING; no new row inserted."""
        sb = SBStub()
        _seed_generated(sb)

        drafts = [_draft("concept_gap", None)]
        mw.MasteryWriter(sb, "live")._draft_correction_tasks(ATTEMPT, drafts)
        count_after_first = len(sb.db["mock_correction_tasks"])

        # Second call with same null-topic draft must not add another row.
        mw.MasteryWriter(sb, "live")._draft_correction_tasks(ATTEMPT, drafts)
        assert len(sb.db["mock_correction_tasks"]) == count_after_first

    def test_non_null_topic_duplicate_is_idempotent(self):
        """Non-null-topic duplicate triggers ON CONFLICT DO NOTHING; no new row inserted."""
        sb = SBStub()
        _seed_generated(sb)

        drafts = [_draft("concept_gap", TOPIC_A)]
        mw.MasteryWriter(sb, "live")._draft_correction_tasks(ATTEMPT, drafts)
        count_after_first = len(sb.db["mock_correction_tasks"])

        mw.MasteryWriter(sb, "live")._draft_correction_tasks(ATTEMPT, drafts)
        assert len(sb.db["mock_correction_tasks"]) == count_after_first

    def test_unrelated_rpc_error_propagates(self):
        """D5 fix: an unrelated RPC error must propagate, not be swallowed."""
        class _BrokenRpcSB(SBStub):
            def rpc(self, name, params=None):
                if name == "ensure_mock_correction_draft":
                    raise RuntimeError("disk_full_totally_unrelated")
                return super().rpc(name, params)

        sb = _BrokenRpcSB()
        _seed_generated(sb)

        with pytest.raises(RuntimeError, match="disk_full_totally_unrelated"):
            mw.MasteryWriter(sb, "live")._draft_correction_tasks(ATTEMPT, [_draft()])

    def test_all_desired_draft_keys_are_persisted(self):
        """RPC path persists every unique (category, topic) key from the draft list."""
        sb = SBStub()
        _seed_generated(sb)

        drafts = [
            _draft("concept_gap", TOPIC_A),
            _draft("speed_issue", TOPIC_A),
        ]
        mw.MasteryWriter(sb, "live")._draft_correction_tasks(ATTEMPT, drafts)

        categories = {r["category"] for r in sb.db["mock_correction_tasks"]
                      if r.get("state") == "drafted"}
        assert "concept_gap" in categories
        assert "speed_issue" in categories


# ══════════════════════════════════════════════════════════════════════════════
# Manual path (mocks.draft_correction_tasks)
# ══════════════════════════════════════════════════════════════════════════════

class _AtomicFailSB(SBStub):
    """SBStub that models an atomic failure AFTER the UPSERT but BEFORE the
    DELETE by raising on the replace RPC on the first call only.  Used to
    verify that prior drafts are preserved on failure."""

    def __init__(self, db=None):
        super().__init__(db)
        self._fail_replace = True

    def rpc(self, name, params=None):
        if name == "replace_manual_mock_correction_drafts" and self._fail_replace:
            self._fail_replace = False
            raise RuntimeError("transient_rpc_failure")
        return super().rpc(name, params)


class test_manual_path:

    def test_atomic_failure_preserves_original_drafts(self):
        """D2 fix: when the RPC fails, original drafted rows are untouched."""
        sb = SBStub()
        mid = _make_manual_mock(sb)

        # Pre-seed existing drafts.
        existing_id = str(uuid.uuid4())
        sb.db["mock_correction_tasks"].append({
            "id": existing_id,
            "mock_test_id": mid,
            "user_id": USER,
            "category": "concept_gap",
            "topic": TOPIC_A,
            "state": "drafted",
            "title": "original",
            "source_questions": [],
            "study_task_id": None,
            "created_at": None,
            "applied_at": None,
        })

        fail_sb = _AtomicFailSB(sb.db)
        with pytest.raises(RuntimeError, match="transient_rpc_failure"):
            mocks_service.draft_correction_tasks(fail_sb, USER, mid)

        # Original draft must still be present.
        drafts = [r for r in sb.db["mock_correction_tasks"] if r["state"] == "drafted"]
        assert any(r["id"] == existing_id for r in drafts), \
            "pre-existing draft must survive an RPC failure"

    def test_atomic_failure_preserves_review_state(self):
        """D4 fix: review_state must not change on RPC failure."""
        sb = SBStub()
        mid = _make_manual_mock(sb)

        fail_sb = _AtomicFailSB(sb.db)
        with pytest.raises(RuntimeError):
            mocks_service.draft_correction_tasks(fail_sb, USER, mid)

        mock_row = next(r for r in sb.db["mock_tests"] if r["id"] == mid)
        assert mock_row["review_state"] == "unreviewed", \
            "review_state must not advance on RPC failure"

    def test_obsolete_drafted_rows_removed_on_success(self):
        """D3 fix: obsolete drafted rows are removed after successful replacement."""
        sb = SBStub()
        mid = _make_manual_mock(sb)

        # Pre-seed a drafted row for a category that won't appear in the new set.
        stale_id = str(uuid.uuid4())
        sb.db["mock_correction_tasks"].append({
            "id": stale_id,
            "mock_test_id": mid,
            "user_id": USER,
            "category": "careless",   # not generated by the mock's error_patterns
            "topic": TOPIC_B,
            "state": "drafted",
            "title": "stale",
            "source_questions": [],
            "study_task_id": None,
            "created_at": None,
            "applied_at": None,
        })

        mocks_service.draft_correction_tasks(sb, USER, mid)

        still_stale = [r for r in sb.db["mock_correction_tasks"]
                       if r.get("id") == stale_id and r.get("state") == "drafted"]
        assert not still_stale, "stale drafted row must be removed after successful replace"

    def test_applied_and_dismissed_rows_preserved(self):
        """Applied/dismissed rows must never be touched by draft replacement."""
        sb = SBStub()
        mid = _make_manual_mock(sb)

        applied_id = str(uuid.uuid4())
        dismissed_id = str(uuid.uuid4())
        sb.db["mock_correction_tasks"].extend([
            {
                "id": applied_id,
                "mock_test_id": mid,
                "user_id": USER,
                "category": "concept_gap",
                "topic": TOPIC_A,
                "state": "applied",
                "title": "applied",
                "source_questions": [],
                "study_task_id": "st-1",
                "created_at": None,
                "applied_at": None,
            },
            {
                "id": dismissed_id,
                "mock_test_id": mid,
                "user_id": USER,
                "category": "speed_issue",
                "topic": None,
                "state": "dismissed",
                "title": "dismissed",
                "source_questions": [],
                "study_task_id": None,
                "created_at": None,
                "applied_at": None,
            },
        ])

        mocks_service.draft_correction_tasks(sb, USER, mid)

        preserved = {r["id"] for r in sb.db["mock_correction_tasks"]
                     if r["state"] in ("applied", "dismissed")}
        assert applied_id in preserved
        assert dismissed_id in preserved

    def test_empty_drafts_sets_reviewed_state_and_zero_rows(self):
        """Empty draft set: review_state='reviewed', all drafted rows removed."""
        sb = SBStub()
        mid = _make_manual_mock(sb)
        # Override mock to have no error_patterns and no weak_topics so
        # _draft_corrections_from_mock returns [].
        mock_row = next(r for r in sb.db["mock_tests"] if r["id"] == mid)
        mock_row["error_patterns"] = {}
        mock_row["weak_topics"] = []

        # Pre-seed a drafted row to verify it gets deleted.
        sb.db["mock_correction_tasks"].append({
            "id": str(uuid.uuid4()),
            "mock_test_id": mid,
            "user_id": USER,
            "category": "concept_gap",
            "topic": TOPIC_A,
            "state": "drafted",
            "title": "old",
            "source_questions": [],
            "study_task_id": None,
            "created_at": None,
            "applied_at": None,
        })

        result = mocks_service.draft_correction_tasks(sb, USER, mid)

        assert result == [], "empty drafts must return empty list"
        remaining_drafted = [r for r in sb.db["mock_correction_tasks"]
                             if r.get("mock_test_id") == mid and r.get("state") == "drafted"]
        assert remaining_drafted == [], "all drafted rows must be removed"
        assert mock_row["review_state"] == "reviewed", \
            "review_state must be 'reviewed' (not 'correction_drafted') for empty drafts"

    def test_platform_attempt_raises_forbidden(self):
        """Platform-attempt mock must raise PlatformAttemptCorrectionForbiddenError."""
        sb = SBStub()
        mid = _make_manual_mock(sb, source_type="platform_attempt")

        with pytest.raises(PlatformAttemptCorrectionForbiddenError):
            mocks_service.draft_correction_tasks(sb, USER, mid)

    def test_wrong_owner_raises_lookup_error(self):
        """mock_id not owned by user_id must raise LookupError."""
        sb = SBStub()
        mid = _make_manual_mock(sb)

        with pytest.raises(LookupError):
            mocks_service.draft_correction_tasks(sb, "wrong-user", mid)

    def test_replacement_sets_correction_drafted_state(self):
        """Successful replacement sets review_state='correction_drafted'."""
        sb = SBStub()
        mid = _make_manual_mock(sb)

        mocks_service.draft_correction_tasks(sb, USER, mid)

        mock_row = next(r for r in sb.db["mock_tests"] if r["id"] == mid)
        assert mock_row["review_state"] == "correction_drafted"

    def test_returned_rows_match_stored_rows(self):
        """Returned list must match the drafted rows in the DB."""
        sb = SBStub()
        mid = _make_manual_mock(sb)

        result = mocks_service.draft_correction_tasks(sb, USER, mid)

        stored = [r for r in sb.db["mock_correction_tasks"]
                  if r.get("mock_test_id") == mid and r.get("state") == "drafted"]
        assert len(result) == len(stored)
        returned_ids = {r["id"] for r in result}
        stored_ids = {r["id"] for r in stored}
        assert returned_ids == stored_ids


# ══════════════════════════════════════════════════════════════════════════════
# RPC privilege checks (VERIFY DB — unit stub cannot enforce REVOKE/GRANT)
# ══════════════════════════════════════════════════════════════════════════════
#
# To verify in Supabase Studio (single BEGIN/ROLLBACK block per AGENTS.md):
#
#   begin;
#     select set_config('role', 'anon', true);
#     select public.ensure_mock_correction_draft(
#         gen_random_uuid(), gen_random_uuid(),
#         'concept_gap', null, 'title', '[]'::jsonb
#     );
#   rollback;
#   -- must error: permission denied for function ensure_mock_correction_draft
#
#   begin;
#     select set_config('role', 'authenticated', true);
#     select public.replace_manual_mock_correction_drafts(
#         gen_random_uuid(), gen_random_uuid(), '[]'::jsonb
#     );
#   rollback;
#   -- must error: permission denied for function replace_manual_mock_correction_drafts
#
# service_role may EXECUTE both functions (tested via FastAPI integration).
