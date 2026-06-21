"""_apply_error_patterns schema-compatibility regression tests.

Asserts that MasteryWriter._apply_error_patterns writes columns that exist
in user_topic_error_patterns (migration 033):
  - uses 'frequency_count', not the non-existent 'error_count'
  - does NOT write 'microtopic_id' as a top-level column (not in schema)
  - stores microtopic_id inside the 'evidence' JSONB field
  - stores evidence_question_ids and signal_strength in evidence

Stub-only (in-memory SBStub); no live DB.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from app.study_os import mastery_writer as mw
from app.study_os.mastery_engine.schemas import ErrorPatternSignal
from tests.persona_questions._stub import SBStub

USER = "u-schema-test"
TOPIC = "t-schema-test"
MICRO = "micro-1"


def _make_signal(**kwargs) -> ErrorPatternSignal:
    defaults = dict(
        user_id=USER,
        topic_id=TOPIC,
        microtopic_id=MICRO,
        error_type="concept_gap",
        count=2,
        evidence_question_ids=["q-1", "q-2"],
        signal_strength=Decimal("0.75"),
    )
    defaults.update(kwargs)
    return ErrorPatternSignal(**defaults)


def _make_db() -> dict:
    return {
        "user_topic_error_patterns": [],
    }


# ── column name fix ──────────────────────────────────────────────────────────

def test_uses_frequency_count_not_error_count():
    sb = SBStub(_make_db())
    writer = mw.MasteryWriter(sb, "live")
    writer._apply_error_patterns([_make_signal()])
    rows = sb.db["user_topic_error_patterns"]
    assert rows, "expected at least one row inserted"
    row = rows[0]
    assert "frequency_count" in row, "frequency_count column must be present"
    assert "error_count" not in row, "error_count is not a schema column — must not be written"
    assert row["frequency_count"] == 2


def test_does_not_write_microtopic_id_as_top_level_column():
    sb = SBStub(_make_db())
    writer = mw.MasteryWriter(sb, "live")
    writer._apply_error_patterns([_make_signal()])
    row = sb.db["user_topic_error_patterns"][0]
    assert "microtopic_id" not in row, "microtopic_id is not a schema column — must not be a top-level key"


def test_stores_microtopic_id_in_evidence():
    sb = SBStub(_make_db())
    writer = mw.MasteryWriter(sb, "live")
    writer._apply_error_patterns([_make_signal(microtopic_id="micro-42")])
    row = sb.db["user_topic_error_patterns"][0]
    assert "evidence" in row, "evidence JSONB field must be present"
    assert row["evidence"]["microtopic_id"] == "micro-42"


def test_stores_evidence_question_ids_in_evidence():
    sb = SBStub(_make_db())
    writer = mw.MasteryWriter(sb, "live")
    writer._apply_error_patterns([_make_signal(evidence_question_ids=["q-x", "q-y"])])
    row = sb.db["user_topic_error_patterns"][0]
    assert row["evidence"]["evidence_question_ids"] == ["q-x", "q-y"]


def test_stores_signal_strength_in_evidence():
    sb = SBStub(_make_db())
    writer = mw.MasteryWriter(sb, "live")
    writer._apply_error_patterns([_make_signal(signal_strength=Decimal("0.85"))])
    row = sb.db["user_topic_error_patterns"][0]
    assert abs(row["evidence"]["signal_strength"] - 0.85) < 1e-6


def test_null_microtopic_id_stored_in_evidence():
    sb = SBStub(_make_db())
    writer = mw.MasteryWriter(sb, "live")
    writer._apply_error_patterns([_make_signal(microtopic_id=None)])
    row = sb.db["user_topic_error_patterns"][0]
    assert row["evidence"]["microtopic_id"] is None


def test_writes_user_id_topic_id_error_type():
    sb = SBStub(_make_db())
    writer = mw.MasteryWriter(sb, "live")
    writer._apply_error_patterns([_make_signal()])
    row = sb.db["user_topic_error_patterns"][0]
    assert row["user_id"] == USER
    assert row["topic_id"] == TOPIC
    assert row["error_type"] == "concept_gap"


def test_multiple_signals_each_insert_a_row():
    sb = SBStub(_make_db())
    writer = mw.MasteryWriter(sb, "live")
    signals = [
        _make_signal(error_type="concept_gap"),
        _make_signal(error_type="memory_gap"),
    ]
    writer._apply_error_patterns(signals)
    rows = sb.db["user_topic_error_patterns"]
    assert len(rows) == 2
    error_types = {r["error_type"] for r in rows}
    assert error_types == {"concept_gap", "memory_gap"}


def test_empty_signals_list_does_not_insert():
    sb = SBStub(_make_db())
    writer = mw.MasteryWriter(sb, "live")
    writer._apply_error_patterns([])
    assert sb.db["user_topic_error_patterns"] == []
