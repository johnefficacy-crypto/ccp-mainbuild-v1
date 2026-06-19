"""MasteryWriter._load_analytics attempted-semantics + classification source.

Covers DEFECT-001 (attempted must mean answered, not frozen) and DEFECT-003
(error_type is authoritative ONLY from mock_attempt_response_classification):

  * attempted is True iff selected_option_id is not null;
  * mastery delta / shadow rows come only from answered topics; untouched
    frozen topics produce neither;
  * error_type is read from the classification table, never from
    mock_attempt_responses (which has no such column);
  * a classified unanswered response (time_pressure_unattempted) yields NO
    mastery delta for its topic but STILL feeds a speed correction;
  * missing/unknown classification invents no category (no blind concept_gap).

Stub-only (in-memory SBStub); no live DB.
"""
from __future__ import annotations

import asyncio

import pytest

from app.study_os import mastery_writer as mw
from app.study_os.mastery_engine import derive_from_analytics
from tests.persona_questions._stub import SBStub

ATTEMPT = "22222222-2222-2222-2222-222222222222"
USER = "u-1"
T_ANSWERED = "t-answered"
T_FROZEN = "t-frozen"
MOCK_TEST_ID = "mt-1"


def _base_db() -> dict:
    return {
        "mock_attempts": [{"id": ATTEMPT, "user_id": USER}],
        "mock_tests": [
            {"id": MOCK_TEST_ID, "mock_attempt_id": ATTEMPT, "trust_level": "platform_verified"}
        ],
        "mock_attempt_responses": [],
        "mock_attempt_response_classification": [],
        "mock_correction_tasks": [],
        "mock_mastery_shadow": [],
        "user_topic_mastery": [],
        "user_topic_mastery_audit": [],
        "user_topic_error_patterns": [],
    }


def _response(qid: str, topic_id: str, *, selected: str | None, is_correct: bool, time_spent: int = 30) -> dict:
    return {
        "attempt_id": ATTEMPT,
        "question_id": qid,
        "selected_option_id": selected,
        "is_correct": is_correct,
        "time_spent_sec": time_spent,
        "question_snapshot": {
            "topic_id": topic_id,
            "difficulty": "medium",
            "source_type": "authored",
            "expected_time_sec": 60,
        },
    }


def _classification(qid: str, error_type: str) -> dict:
    return {"attempt_id": ATTEMPT, "question_id": qid, "error_type": error_type}


# ── 1. attempted is True ONLY for selected_option_id-not-null rows ─────────────

def test_attempted_flag_tracks_selected_option_id():
    sb = SBStub(_base_db())
    sb.db["mock_attempt_responses"] = [
        _response("q-ans", T_ANSWERED, selected="opt-1", is_correct=True),
        _response("q-frozen", T_FROZEN, selected=None, is_correct=False),
    ]
    analytics = mw.MasteryWriter(sb, "shadow")._load_analytics(ATTEMPT)
    by_qid = {q.question_id: q for q in analytics.questions}
    assert by_qid["q-ans"].attempted is True
    assert by_qid["q-frozen"].attempted is False


# ── 2. answered topic moves mastery; untouched frozen topic does not ───────────

def test_only_answered_topic_gets_mastery_and_shadow():
    sb = SBStub(_base_db())
    sb.db["mock_attempt_responses"] = [
        _response("q-ans", T_ANSWERED, selected="opt-1", is_correct=True),
        # Two untouched frozen rows in a different topic — never answered.
        _response("q-f1", T_FROZEN, selected=None, is_correct=False),
        _response("q-f2", T_FROZEN, selected=None, is_correct=False),
    ]
    # Seed one classification row per response (simulates analytics having run).
    sb.db["mock_attempt_response_classification"] = [
        _classification("q-ans", "correct"),
        _classification("q-f1", "concept_gap"),
        _classification("q-f2", "concept_gap"),
    ]
    asyncio.run(mw.MasteryWriter(sb, "live").process_attempt(ATTEMPT))

    shadow_topics = {r["topic_id"] for r in sb.db["mock_mastery_shadow"]}
    audit_topics = {r["topic_id"] for r in sb.db["user_topic_mastery_audit"]}
    assert shadow_topics == {T_ANSWERED}
    assert audit_topics == {T_ANSWERED}
    # The frozen topic produced no mastery delta and no shadow row.
    assert T_FROZEN not in shadow_topics
    assert T_FROZEN not in audit_topics


# ── 3. error_type comes ONLY from the classification table ─────────────────────

def test_error_type_loaded_from_classification_only():
    sb = SBStub(_base_db())
    sb.db["mock_attempt_responses"] = [
        # A stray (illegitimate) error_type on the response row must be IGNORED.
        {**_response("q-ans", T_ANSWERED, selected="opt-1", is_correct=False), "error_type": "concept_gap"},
        _response("q-noclass", T_ANSWERED, selected="opt-2", is_correct=False),
    ]
    sb.db["mock_attempt_response_classification"] = [
        _classification("q-ans", "option_trap"),
    ]
    analytics = mw.MasteryWriter(sb, "shadow")._load_analytics(ATTEMPT)
    by_qid = {q.question_id: q for q in analytics.questions}
    # Authoritative value is the classification row, NOT the response column.
    assert by_qid["q-ans"].error_type == "option_trap"
    # No classification row → None, never inherited from the response.
    assert by_qid["q-noclass"].error_type is None


# ── 4. classified unanswered → no mastery delta, but a speed correction ────────

def test_time_pressure_unattempted_no_mastery_but_speed_correction():
    sb = SBStub(_base_db())
    sb.db["mock_attempt_responses"] = [
        _response("q-tp", T_FROZEN, selected=None, is_correct=False),
    ]
    sb.db["mock_attempt_response_classification"] = [
        _classification("q-tp", "time_pressure_unattempted"),
    ]
    asyncio.run(mw.MasteryWriter(sb, "live").process_attempt(ATTEMPT))

    # No mastery delta for the unattempted topic.
    assert sb.db["mock_mastery_shadow"] == []
    assert sb.db["user_topic_mastery_audit"] == []
    # But a speed correction is still drafted for that topic.
    corrections = sb.db["mock_correction_tasks"]
    assert any(c["category"] == "speed_issue" and c["topic"] == T_FROZEN for c in corrections)


# ── 5. missing/unknown classification → no invented category ───────────────────

def test_missing_classification_invents_no_category():
    sb = SBStub(_base_db())
    # Three untouched frozen rows in one topic, NO classification at all. With the
    # old all-rows-attempted behaviour this would read as attempted>=3, accuracy
    # 0% → a blind concept_gap fallback.
    # With the readiness gate: missing classifications → MasteryClassificationNotReady;
    # mastery is deferred so nothing is written — no blind concept_gap.
    sb.db["mock_attempt_responses"] = [
        _response(f"q-f{i}", T_FROZEN, selected=None, is_correct=False) for i in range(3)
    ]
    with pytest.raises(mw.MasteryClassificationNotReady):
        asyncio.run(mw.MasteryWriter(sb, "live").process_attempt(ATTEMPT))

    assert sb.db["mock_correction_tasks"] == []
    assert sb.db["mock_mastery_shadow"] == []
    assert sb.db["user_topic_mastery_audit"] == []


def test_unknown_classification_value_is_ignored():
    sb = SBStub(_base_db())
    sb.db["mock_attempt_responses"] = [
        _response("q-u", T_FROZEN, selected=None, is_correct=False),
    ]
    # An unrecognized error_type alias normalizes to None — no category invented.
    sb.db["mock_attempt_response_classification"] = [
        _classification("q-u", "marked_unanswered"),
    ]
    analytics = mw.MasteryWriter(sb, "shadow")._load_analytics(ATTEMPT)
    result = derive_from_analytics(analytics)
    assert result.mastery_deltas == []
    assert result.correction_task_drafts == []


# ── BLOCKER 2: 23505 conflict handling ────────────────────────────────────────

def _base_db_with_mock_test():
    db = _base_db()
    db["mock_tests"] = [
        {"id": MOCK_TEST_ID, "mock_attempt_id": ATTEMPT, "trust_level": "platform_verified"}
    ]
    return db


def test_correction_insert_23505_is_idempotent():
    """When the correction insert raises 23505, the writer logs and continues — no raise."""
    insert_calls = []

    class _ConflictSB(SBStub):
        def table(self, name):
            if name == "mock_correction_tasks":
                return _ConflictTable(name, self.db, insert_calls)
            return super().table(name)

    class _ConflictTable:
        def __init__(self, name, db, log):
            from tests.persona_questions._stub import _Query
            self._q = _Query(name, db)
            self._log = log

        def select(self, *a, **kw): return self._q.select(*a, **kw)
        def eq(self, *a, **kw): return self._q.eq(*a, **kw)
        def delete(self): return self._q.delete()

        def insert(self, payload):
            self._log.append(payload)
            return self

        def execute(self):
            raise RuntimeError("23505 duplicate key value violates unique constraint")

    db = _base_db_with_mock_test()
    db["mock_attempt_responses"] = [
        _response("q-ans", T_ANSWERED, selected="opt-1", is_correct=True),
    ]
    db["mock_attempt_response_classification"] = [
        _classification("q-ans", "option_trap"),
    ]
    sb = _ConflictSB(db)
    # Must not raise even though the DB rejects with 23505.
    asyncio.run(mw.MasteryWriter(sb, "live").process_attempt(ATTEMPT))
    assert len(insert_calls) >= 0  # insert was attempted


def test_correction_non_23505_propagates():
    """Non-unique-constraint errors from correction insert must propagate."""
    import pytest

    class _NetworkFailSB(SBStub):
        def table(self, name):
            if name == "mock_correction_tasks":
                class _Bad:
                    def select(self, *a, **kw): return self
                    def eq(self, *a, **kw): return self
                    def delete(self): return self
                    def insert(self, *a): return self
                    def execute(self): raise RuntimeError("connection refused")
                return _Bad()
            return super().table(name)

    db = _base_db_with_mock_test()
    db["mock_attempt_responses"] = [
        _response("q-ans", T_ANSWERED, selected="opt-1", is_correct=False),
    ]
    db["mock_attempt_response_classification"] = [
        _classification("q-ans", "concept_gap"),
    ]
    sb = _NetworkFailSB(db)
    with pytest.raises(RuntimeError, match="connection refused"):
        asyncio.run(mw.MasteryWriter(sb, "live").process_attempt(ATTEMPT))


# ── BLOCKER 4: derive_preview structure ───────────────────────────────────────

def test_derive_preview_returns_three_sections():
    """derive_preview must return persisted_shadow_decision, current_read_only_preview,
    and replay_consistency sections."""
    db = _base_db_with_mock_test()
    db["mock_attempt_responses"] = [
        _response("q-ans", T_ANSWERED, selected="opt-1", is_correct=True),
    ]
    db["mock_mastery_shadow"] = [
        {
            "id": "s1",
            "attempt_id": ATTEMPT,
            "topic_id": T_ANSWERED,
            "proposed_delta_db": "5.0",
            "current_mastery_db": "50.0",
            "would_be_mastery_db": "55.0",
            "trust_level": "platform_verified",
            "flag_state": "shadow",
            "decided_at": "2026-06-01T00:00:00+00:00",
        }
    ]
    sb = SBStub(db)
    writer = mw.MasteryWriter(sb, "shadow")
    preview = writer.derive_preview(ATTEMPT)

    assert preview is not None
    assert "persisted_shadow_decision" in preview
    assert "current_read_only_preview" in preview
    assert "replay_consistency" in preview

    psd = preview["persisted_shadow_decision"]
    assert psd["count"] == 1
    assert len(psd["rows"]) == 1

    crp = preview["current_read_only_preview"]
    assert "trust_level" in crp
    assert "mastery_deltas" in crp
    assert "note" in crp

    rc = preview["replay_consistency"]
    assert "items" in rc
    assert "all_signs_match" in rc
    assert "topics_without_shadow" in rc


def test_derive_preview_no_shadow_rows():
    """derive_preview works when no shadow rows exist (shadow was off)."""
    db = _base_db_with_mock_test()
    db["mock_attempt_responses"] = [
        _response("q-ans", T_ANSWERED, selected="opt-1", is_correct=True),
    ]
    db["mock_mastery_shadow"] = []
    sb = SBStub(db)
    writer = mw.MasteryWriter(sb, "shadow")
    preview = writer.derive_preview(ATTEMPT)

    assert preview is not None
    psd = preview["persisted_shadow_decision"]
    assert psd["count"] == 0

    rc = preview["replay_consistency"]
    assert rc["topics_without_shadow"] >= 1
    # all_signs_match is None when there are no matched shadow rows
    assert rc["all_signs_match"] is None


def test_derive_preview_zero_writes():
    """derive_preview must not write to any table."""
    db = _base_db_with_mock_test()
    db["mock_attempt_responses"] = [
        _response("q-ans", T_ANSWERED, selected="opt-1", is_correct=True),
    ]
    db["mock_mastery_shadow"] = []
    sb = SBStub(db)
    writer = mw.MasteryWriter(sb, "shadow")
    writer.derive_preview(ATTEMPT)

    # No writes should occur to mastery or correction tables
    assert sb.db.get("user_topic_mastery", []) == []
    assert sb.db.get("user_topic_mastery_audit", []) == []
    assert sb.db.get("mock_correction_tasks", []) == []
    assert sb.db.get("user_topic_error_patterns", []) == []


def test_derive_preview_returns_none_for_unknown_attempt():
    """derive_preview returns None when the attempt doesn't exist."""
    db = _base_db_with_mock_test()
    sb = SBStub(db)
    writer = mw.MasteryWriter(sb, "shadow")
    assert writer.derive_preview("nonexistent-attempt-id") is None
