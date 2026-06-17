"""MasteryWriter correction-task write-back is schema-compatible with migration
063 (the §4b pre-FF-live blocker).

Covers: the legacy-063 payload shape, the task_type→category mapping, the
mock_tests-missing deferral + sweeper recovery + idempotency, FF=shadow/live
behaviour, and an anti-vacuous regression where a 063-ENFORCING stub rejects the
OLD payload and accepts the NEW one.

Stub-only (in-memory SBStub); no live DB.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.study_os import mastery_writer as mw
from app.study_os import mock_engine as engine
from app.study_os.mastery_engine.schemas import CorrectionEvidence, CorrectionTaskDraft
from app.study_os.mocks import VALID_CORRECTION_CATEGORIES
from tests.persona_questions._stub import SBStub

ATTEMPT = "11111111-1111-1111-1111-111111111111"
USER = "u-1"
TOPIC = "t1"
MOCK_TEST_ID = "mt-1"
_DISALLOWED = {"task_type", "priority", "evidence_json", "duration_minutes", "source_attempt_id"}


@pytest.fixture(autouse=True)
def _reset_metrics():
    mw.correction_metrics.clear()
    yield
    mw.correction_metrics.clear()


def _seed(sb: SBStub, *, with_mock_tests: bool = True, error_type: str | None = "concept_gap", n: int = 3) -> None:
    sb.db["mock_attempts"] = [{"id": ATTEMPT, "user_id": USER}]
    sb.db["mock_attempt_responses"] = [
        {
            "attempt_id": ATTEMPT,
            "question_id": f"q{i}",
            "is_correct": False,
            "time_spent_sec": 5,
            "error_type": error_type,
            "question_snapshot": {
                "topic_id": TOPIC,
                "difficulty": "medium",
                "source_type": "authored",
            },
        }
        for i in range(n)
    ]
    sb.db["mock_tests"] = (
        [{"id": MOCK_TEST_ID, "mock_attempt_id": ATTEMPT, "trust_level": "platform_verified"}]
        if with_mock_tests
        else []
    )
    sb.db.setdefault("mock_correction_tasks", [])
    sb.db.setdefault("mock_mastery_shadow", [])
    sb.db.setdefault("user_topic_mastery", [])
    sb.db.setdefault("user_topic_mastery_audit", [])
    sb.db.setdefault("user_topic_error_patterns", [])


def _draft(task_type: str = "concept_review", error_types=None, category: str = "concept_gap") -> CorrectionTaskDraft:
    return CorrectionTaskDraft(
        user_id=USER,
        topic_id=TOPIC,
        microtopic_id=None,
        category=category,  # set by correction_policy in the real path
        task_type=task_type,
        priority=3,
        reason="because",
        evidence=CorrectionEvidence(
            accuracy_pct=Decimal("0"),
            error_types=error_types or [],
            related_question_ids=["q1", "q2"],
        ),
        estimated_minutes=30,
        source_attempt_id=uuid.uuid4(),
    )


# ── 1. payload is 063-schema-compatible ───────────────────────────────────────

def test_draft_payload_matches_063_schema():
    sb = SBStub()
    _seed(sb)
    mw.MasteryWriter(sb, "live")._draft_correction_tasks(ATTEMPT, [_draft()])
    rows = sb.db["mock_correction_tasks"]
    assert len(rows) == 1
    row = rows[0]
    assert row["mock_test_id"] == MOCK_TEST_ID
    assert row["user_id"] == USER
    assert row["category"] in VALID_CORRECTION_CATEGORIES
    assert row["title"]
    assert row["topic"] == TOPIC
    assert row["source_questions"] == ["q1", "q2"]
    assert row["state"] == "drafted"
    for bad in _DISALLOWED:
        assert bad not in row


# (category mapping moved to test_correction_policy.py — MasteryWriter no longer
#  classifies; it persists draft.category from the shared policy.)


# ── 3. mock_tests missing → defer (observable), then recover exactly once ──────

def test_missing_mock_tests_defers_then_recovers_once():
    sb = SBStub()
    _seed(sb, with_mock_tests=False)
    writer = mw.MasteryWriter(sb, "live")

    # First pass: no compat row yet → no corrections, no exception, observable.
    asyncio.run(writer.process_attempt(ATTEMPT))
    assert sb.db["mock_correction_tasks"] == []
    assert mw.correction_metrics["correction_deferred_missing_mock_test"] == 1
    # mastery still applied (does not depend on mock_tests).
    assert any(a["topic_id"] == TOPIC for a in sb.db["user_topic_mastery_audit"])

    # Compat row lands (sweeper re-emit) → recovery drafts the corrections.
    sb.db["mock_tests"] = [
        {"id": MOCK_TEST_ID, "mock_attempt_id": ATTEMPT, "trust_level": "platform_verified"}
    ]
    writer.redraft_corrections(ATTEMPT)
    n_after_first = len(sb.db["mock_correction_tasks"])
    assert n_after_first >= 1

    # Re-run recovery (sweeper fires again): idempotent — no duplicates.
    writer.redraft_corrections(ATTEMPT)
    assert len(sb.db["mock_correction_tasks"]) == n_after_first


def test_run_job_retry_hook_recovers_corrections(monkeypatch):
    # The minimal mock_engine recovery hook: JOB_MOCK_TESTS_RETRY re-emits the row
    # AND re-runs correction drafting.
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
    sb = SBStub()
    _seed(sb, with_mock_tests=True)  # row exists so _retry no-ops; hook still drafts
    engine._run_job(sb, {"job_kind": engine.JOB_MOCK_TESTS_RETRY, "attempt_id": ATTEMPT})
    assert any(r["mock_test_id"] == MOCK_TEST_ID for r in sb.db["mock_correction_tasks"])


# ── 4. FF=shadow writes shadow only, zero corrections ─────────────────────────

def test_shadow_writes_no_corrections():
    sb = SBStub()
    _seed(sb)
    asyncio.run(mw.MasteryWriter(sb, "shadow").process_attempt(ATTEMPT))
    assert sb.db["mock_mastery_shadow"]
    assert sb.db["mock_correction_tasks"] == []
    assert sb.db["user_topic_mastery_audit"] == []


# ── 5. FF=live applies signals + corrections; re-run does not duplicate ────────

def test_live_applies_signals_and_corrections_idempotent():
    sb = SBStub()
    _seed(sb)
    writer = mw.MasteryWriter(sb, "live")
    asyncio.run(writer.process_attempt(ATTEMPT))

    assert any(a["topic_id"] == TOPIC for a in sb.db["user_topic_mastery_audit"])
    assert any(e["topic_id"] == TOPIC for e in sb.db["user_topic_error_patterns"])
    corrections = [r for r in sb.db["mock_correction_tasks"] if r["category"] in VALID_CORRECTION_CATEGORIES]
    assert corrections
    n = len(sb.db["mock_correction_tasks"])

    # Duplicate processing (re-submit) must not duplicate correction drafts.
    asyncio.run(writer.process_attempt(ATTEMPT))
    assert len(sb.db["mock_correction_tasks"]) == n


# ── 8. anti-vacuous: a 063-ENFORCING stub rejects OLD, accepts NEW ────────────

class _Enforcing063SB(SBStub):
    """SBStub that enforces the migration-063 mock_correction_tasks contract on
    insert: mock_test_id/category/title NOT NULL, category in the live CHECK set,
    and NONE of the columns the table does not have."""

    def table(self, name):  # type: ignore[override]
        q = super().table(name)
        if name == "mock_correction_tasks":
            real_insert = q.insert

            def _checked(payload):
                for r in (payload if isinstance(payload, list) else [payload]):
                    if r.get("mock_test_id") is None:
                        raise ValueError("063: mock_test_id NOT NULL")
                    if not r.get("category"):
                        raise ValueError("063: category NOT NULL")
                    if r["category"] not in VALID_CORRECTION_CATEGORIES:
                        raise ValueError("063: category CHECK violation")
                    if not r.get("title"):
                        raise ValueError("063: title NOT NULL")
                    unknown = _DISALLOWED & set(r)
                    if unknown:
                        raise ValueError(f"063: unknown columns {unknown}")
                return real_insert(payload)

            q.insert = _checked  # type: ignore[assignment]
        return q


def test_old_payload_fails_063_enforcing_stub():
    sb = _Enforcing063SB()
    old_payload = {
        "id": "x",
        "user_id": USER,
        "mock_test_id": None,          # NOT NULL violation
        "task_type": "concept_review",  # unknown column
        "priority": 3,
        "evidence_json": {},
        "duration_minutes": 20,
        "source_attempt_id": "a",
        "state": "drafted",
    }
    with pytest.raises(ValueError):
        sb.table("mock_correction_tasks").insert(old_payload).execute()


def test_new_payload_passes_063_enforcing_stub():
    sb = _Enforcing063SB()
    _seed(sb)
    # Must not raise — the new writer payload satisfies the 063 contract.
    mw.MasteryWriter(sb, "live")._draft_correction_tasks(ATTEMPT, [_draft()])
    assert len(sb.db["mock_correction_tasks"]) == 1


# ── true sweeper-level recovery lifecycle (not a direct redraft call) ──────────

class _FlakyCorrectionSB(SBStub):
    """SBStub whose FIRST mock_correction_tasks insert raises a transient error,
    then succeeds — to drive the sweeper's failed-recovery → reschedule → retry
    → success lifecycle."""

    def __init__(self, db=None):
        super().__init__(db)
        self.fail_next_correction_insert = True

    def table(self, name):  # type: ignore[override]
        q = super().table(name)
        if name == "mock_correction_tasks":
            real_insert = q.insert

            def _insert(payload):
                if getattr(self, "fail_next_correction_insert", False):
                    self.fail_next_correction_insert = False
                    raise RuntimeError("transient correction insert failure")
                return real_insert(payload)

            q.insert = _insert  # type: ignore[assignment]
        return q


def test_sweeper_recovers_correction_after_transient_failure(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
    now = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)
    past = (now - timedelta(seconds=60)).isoformat()

    sb = _FlakyCorrectionSB()
    sb.db.update({
        "mock_attempts": [{
            "id": ATTEMPT, "user_id": USER, "status": "submitted",
            "template_snapshot": {}, "score_raw": 0, "total_correct": 0,
            "total_wrong": 3, "submitted_at": past, "expires_at": past,
        }],
        "mock_attempt_responses": [
            {
                "attempt_id": ATTEMPT, "question_id": f"q{i}", "is_correct": False,
                "time_spent_sec": 5, "error_type": "concept_gap",
                "question_snapshot": {
                    "topic_id": TOPIC, "difficulty": "medium",
                    "source_type": "authored", "marks": 1,
                },
            }
            for i in range(3)
        ],
        "mock_tests": [],
        "mock_correction_tasks": [],
        "mock_attempt_jobs": [{
            "id": "job-1", "job_kind": engine.JOB_MOCK_TESTS_RETRY,
            "attempt_id": ATTEMPT, "scheduled_for": past, "attempts": 0,
            "status": "pending", "last_error": None,
        }],
        "user_topic_mastery": [], "user_topic_mastery_audit": [],
        "user_topic_error_patterns": [], "mock_mastery_shadow": [],
    })

    # ── First sweep: mock_tests emitted, correction insert fails once → reschedule
    counts1 = engine.run_sweeper(sb, now=now)
    job = sb.db["mock_attempt_jobs"][0]
    assert len(sb.db["mock_tests"]) == 1            # compat row created
    assert sb.db["mock_correction_tasks"] == []      # correction NOT persisted
    assert job["status"] == "pending"                # NOT done — rescheduled
    assert job["attempts"] == 1                       # attempts increased
    assert job["last_error"]                          # records the correction failure
    assert counts1["errors"] == 1                     # reported error, not success

    # ── Second sweep after backoff, failure no longer fires
    assert sb.fail_next_correction_insert is False    # consumed on the first attempt
    later = now + timedelta(seconds=30)               # past the rescheduled scheduled_for
    engine.run_sweeper(sb, now=later)
    job = sb.db["mock_attempt_jobs"][0]
    assert len(sb.db["mock_tests"]) == 1             # retry reused the row — NO duplicate
    drafts = sb.db["mock_correction_tasks"]
    assert len(drafts) == 1                           # exactly one valid correction
    d = drafts[0]
    assert d["mock_test_id"]
    assert d["category"] in VALID_CORRECTION_CATEGORIES
    assert d["title"] and d["state"] == "drafted"
    for bad in _DISALLOWED:
        assert bad not in d
    assert job["status"] == "done"                    # marked done only after success
    assert job["last_error"] is None                  # cleared

    # ── Third sweep: job done; serial retry must not duplicate the correction
    engine.run_sweeper(sb, now=later + timedelta(seconds=30))
    assert len(sb.db["mock_correction_tasks"]) == 1
    assert len(sb.db["mock_tests"]) == 1
