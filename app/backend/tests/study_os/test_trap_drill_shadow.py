"""PYQ v2 PR-8 — trap-drill → shadow mastery/revision (shadow only).

Proves the trap-drill shadow path: gated behind FF_TRAP_DRILL_MASTERY_SHADOW,
writes ONLY the separate trap_drill_mastery_shadow table (never mock_mastery_shadow
or user_topic_mastery), and can never reach a live write.
"""
from __future__ import annotations

from decimal import Decimal

from app.study_os import trap_drill_shadow as tds
from tests.persona_questions._stub import SBStub

EXAM = "11111111-1111-1111-1111-111111111111"
TOPIC = "55555555-5555-5555-5555-555555555555"


def _db() -> SBStub:
    return SBStub({
        "user_trap_drill_attempts": [
            {"user_id": "u1", "exam_id": EXAM, "drill_seed": "seed-1", "question_id": "pq1", "topic_id": TOPIC, "is_correct": False},
            {"user_id": "u1", "exam_id": EXAM, "drill_seed": "seed-1", "question_id": "pq2", "topic_id": TOPIC, "is_correct": False},
        ],
        "pyq_questions": [
            {"id": "pq1", "observed_difficulty": "medium", "pyq_paper_id": "pp1"},
            {"id": "pq2", "observed_difficulty": "medium", "pyq_paper_id": "pp1"},
        ],
        "pyq_papers": [{"id": "pp1", "year": 2020}],
        "user_topic_mastery": [{"user_id": "u1", "topic_id": TOPIC, "mastery_score": 60}],
        "trap_drill_mastery_shadow": [],
        "mock_mastery_shadow": [],
        "user_topic_mastery_audit": [],
    })


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("FF_TRAP_DRILL_MASTERY_SHADOW", raising=False)
    sb = _db()
    out = tds.record_trap_drill_shadow(sb, user_id="u1", exam_id=EXAM, drill_seed="seed-1")
    assert out["outcome"] == "disabled" and out["rows"] == 0
    assert sb.db["trap_drill_mastery_shadow"] == []


def test_live_flag_value_never_enables(monkeypatch):
    # there is no 'live' — any non-'shadow' value leaves the path off.
    monkeypatch.setenv("FF_TRAP_DRILL_MASTERY_SHADOW", "live")
    sb = _db()
    out = tds.record_trap_drill_shadow(sb, user_id="u1", exam_id=EXAM, drill_seed="seed-1")
    assert out["outcome"] == "disabled"
    assert sb.db["trap_drill_mastery_shadow"] == []


def test_shadow_writes_only_the_shadow_table(monkeypatch):
    monkeypatch.setenv("FF_TRAP_DRILL_MASTERY_SHADOW", "shadow")
    sb = _db()
    out = tds.record_trap_drill_shadow(sb, user_id="u1", exam_id=EXAM, drill_seed="seed-1")
    assert out["outcome"] == "written" and out["rows"] >= 1
    rows = sb.db["trap_drill_mastery_shadow"]
    assert {r["topic_id"] for r in rows} == {TOPIC}
    assert all(r["flag_state"] == "shadow" and r["source"] == "trap_drill" for r in rows)
    assert all(r["revision_bucket"] in ("relearn", "review", "practice") for r in rows)
    assert all(r["trust_level"] == "platform_verified" for r in rows)
    # NEVER the P8-measured mock shadow, NEVER live mastery.
    assert sb.db["mock_mastery_shadow"] == []
    assert sb.db["user_topic_mastery"] == [{"user_id": "u1", "topic_id": TOPIC, "mastery_score": 60}]
    assert sb.db["user_topic_mastery_audit"] == []


def test_no_evidence_when_session_empty(monkeypatch):
    monkeypatch.setenv("FF_TRAP_DRILL_MASTERY_SHADOW", "shadow")
    sb = _db()
    out = tds.record_trap_drill_shadow(sb, user_id="u1", exam_id=EXAM, drill_seed="ghost-seed")
    assert out["outcome"] == "no_evidence" and out["rows"] == 0
    assert sb.db["trap_drill_mastery_shadow"] == []


def test_missing_drill_seed_is_no_evidence(monkeypatch):
    monkeypatch.setenv("FF_TRAP_DRILL_MASTERY_SHADOW", "shadow")
    sb = _db()
    out = tds.record_trap_drill_shadow(sb, user_id="u1", exam_id=EXAM, drill_seed=None)
    assert out["outcome"] == "no_evidence"


def test_idempotent_upsert(monkeypatch):
    monkeypatch.setenv("FF_TRAP_DRILL_MASTERY_SHADOW", "shadow")
    sb = _db()
    tds.record_trap_drill_shadow(sb, user_id="u1", exam_id=EXAM, drill_seed="seed-1")
    n1 = len(sb.db["trap_drill_mastery_shadow"])
    tds.record_trap_drill_shadow(sb, user_id="u1", exam_id=EXAM, drill_seed="seed-1")
    assert len(sb.db["trap_drill_mastery_shadow"]) == n1  # (synthetic_attempt_id, topic_id) dedup


def test_revision_bucket_bands():
    assert tds._revision_bucket(Decimal("40")) == "relearn"
    assert tds._revision_bucket(Decimal("60")) == "practice"
    assert tds._revision_bucket(Decimal("80")) == "review"


def test_is_enabled_only_on_shadow(monkeypatch):
    for value, expected in (("shadow", True), ("live", False), ("on", False), ("off", False)):
        monkeypatch.setenv("FF_TRAP_DRILL_MASTERY_SHADOW", value)
        assert tds.is_enabled() is expected
    monkeypatch.delenv("FF_TRAP_DRILL_MASTERY_SHADOW", raising=False)
    assert tds.is_enabled() is False
