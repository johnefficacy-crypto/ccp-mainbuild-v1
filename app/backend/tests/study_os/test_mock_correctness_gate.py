"""PR-fix-3 correctness gate — the four fixes, each covered individually.

Fix 1: auto-submit sweeper for expired in-progress attempts (consolidated jobs).
Fix 2: per-attempt ±0.15-unit delta cap, separate from the [0,100] safety clamp.
Fix 3: mastery_writer idempotency — duplicate apply is a silent no-op.
Fix 4: mastery_writer derives from persisted raw data (implementation B), so a
        derivation failure cannot silently suppress the write-back.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import mock_engine as mock_engine_api
from app.core.auth import get_current_user
from app.study_os import mock_engine as svc
from app.study_os.mastery_writer import MasteryWriter
from app.study_os.mastery_engine.schemas import MasteryDelta
from tests.persona_questions._stub import SBStub


# ─── helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _past_iso(secs: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=secs)).isoformat()


def _make_option(question_id: str, opt_idx: int) -> dict:
    return {
        "id": f"opt-{question_id}-{opt_idx}",
        "question_id": question_id,
        "option_text": f"Option {opt_idx}",
        "option_index": opt_idx,
        "is_correct": opt_idx == 2,
    }


def _make_question(qid: str, topic_id: str | None = None) -> dict:
    opts = [_make_option(qid, i) for i in range(1, 5)]
    return {
        "id": qid,
        "exam_family": "TEST",
        "topic_id": topic_id,
        "difficulty": "easy",
        "source_type": "authored",
        "question_text": f"Question {qid}",
        "question_type": "mcq",
        "marks": 1.0,
        "negative_marks": 0.25,
        "correct_option_id": opts[1]["id"],
        "explanation": "Because.",
        "reviewer_status": "published",
        "options": opts,
    }


def _seeded_db(slug: str = "gate-mock", topic_id: str | None = None):
    questions = [_make_question(f"q{i}", topic_id=topic_id) for i in range(5)]
    qids = [q["id"] for q in questions]
    template = {
        "id": f"tmpl-{slug}",
        "slug": slug,
        "name": "Gate Mock",
        "exam_family": "TEST",
        "total_questions": len(questions),
        "duration_sec": 300,
        "negative_marking": True,
        "marks_per_correct": 1.0,
        "marks_per_wrong": 0.25,
        "config": {"question_ids": qids},
        "status": "active",
    }
    db = {
        "mock_templates": [template],
        "mock_question_bank": questions,
        "mock_question_options": [o for q in questions for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
        "mock_attempt_events": [],
        "mock_attempt_jobs": [],
        "mock_tests": [],
    }
    return SBStub(db), template, questions


def _client(sb: SBStub, user_id: str = "user-1") -> TestClient:
    app = FastAPI()
    app.include_router(mock_engine_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id}
    mock_engine_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


def _attempt_row(sb: SBStub, attempt_id: str) -> dict:
    return next(a for a in sb.db["mock_attempts"] if a["id"] == attempt_id)


def _delta(capped_unit: str, *, user_id: str = "u1", topic_id: str = "t1") -> MasteryDelta:
    return MasteryDelta(
        user_id=user_id,
        topic_id=topic_id,
        current_mastery=Decimal("0.5"),
        expected_accuracy=Decimal("0.6"),
        observed_accuracy=Decimal("1.0"),
        raw_delta=Decimal(capped_unit),
        capped_delta=Decimal(capped_unit),
        attempted=5,
    )


# ─── Fix 1: auto-submit sweeper ───────────────────────────────────────────────

def test_sweeper_auto_submits_expired_attempt():
    """AC1: an attempt expired >60s ago is flipped to submitted in one cycle,
    stamped with expires_at (not the sweeper's wall clock)."""
    sb, _, _ = _seeded_db()
    start = svc.start_attempt(sb, "user-1", "gate-mock")
    attempt_id = start["attempt_id"]
    expires = _past_iso(120)
    _attempt_row(sb, attempt_id)["expires_at"] = expires

    counts = svc.run_sweeper(sb)

    assert counts["auto_submitted"] == 1
    attempt = _attempt_row(sb, attempt_id)
    assert attempt["status"] == "submitted"
    assert attempt["submitted_at"] == expires  # the moment the window closed

    events = [e for e in sb.db["mock_attempt_events"] if e["event_type"] == "attempt.auto_submitted"]
    assert len(events) == 1

    # Derivation is queued, not run synchronously in the sweeper.
    retry = [j for j in sb.db["mock_attempt_jobs"]
             if j["job_kind"] == "analytics_retry" and j["attempt_id"] == attempt_id]
    assert len(retry) == 1


def test_sweeper_ignores_attempts_within_grace_window():
    """An attempt that expired only 30s ago is left alone (60s grace)."""
    sb, _, _ = _seeded_db()
    start = svc.start_attempt(sb, "user-1", "gate-mock")
    attempt_id = start["attempt_id"]
    _attempt_row(sb, attempt_id)["expires_at"] = _past_iso(30)

    counts = svc.run_sweeper(sb)

    assert counts["auto_submitted"] == 0
    assert _attempt_row(sb, attempt_id)["status"] == "in_progress"


def test_sweeper_auto_submit_is_idempotent():
    """Re-running the sweeper does not double-submit or duplicate Mocks rows."""
    sb, _, _ = _seeded_db()
    start = svc.start_attempt(sb, "user-1", "gate-mock")
    attempt_id = start["attempt_id"]
    _attempt_row(sb, attempt_id)["expires_at"] = _past_iso(120)

    svc.run_sweeper(sb)
    svc.run_sweeper(sb)

    submitted_events = [e for e in sb.db["mock_attempt_events"] if e["event_type"] == "attempt.auto_submitted"]
    assert len(submitted_events) == 1
    mock_rows = [r for r in sb.db["mock_tests"] if r.get("analysis_payload", {}).get("mock_attempt_id") == attempt_id]
    assert len(mock_rows) == 1


def test_sweeper_single_loop_handles_both_job_kinds():
    """AC6: one sweeper drains auto_submit and analytics_retry — no second loop."""
    sb, _, _ = _seeded_db()
    # An expired attempt → auto_submit work.
    start = svc.start_attempt(sb, "user-1", "gate-mock")
    expired_id = start["attempt_id"]
    _attempt_row(sb, expired_id)["expires_at"] = _past_iso(120)

    # A separate submitted attempt with a pending analytics_retry job.
    start2 = svc.start_attempt(sb, "user-2", "gate-mock")
    other_id = start2["attempt_id"]
    svc.submit_attempt(sb, "user-2", other_id)
    svc.schedule_job(sb, svc.JOB_ANALYTICS_RETRY, other_id, scheduled_for=_past_iso(5))

    counts = svc.run_sweeper(sb)

    assert counts["auto_submitted"] == 1
    assert counts["derivations"] == 1


def test_sweeper_reclaims_orphaned_running_job():
    """AC2: a job left 'running' by a crash (scheduled_for in the past) is
    reclaimed and finished on the next cycle — no orphan rows."""
    sb, _, _ = _seeded_db()
    start = svc.start_attempt(sb, "user-1", "gate-mock")
    attempt_id = start["attempt_id"]
    svc.submit_attempt(sb, "user-1", attempt_id)

    sb.db["mock_attempt_jobs"] = [{
        "id": "orphan-1",
        "job_kind": "analytics_retry",
        "attempt_id": attempt_id,
        "status": "running",
        "scheduled_for": _past_iso(10),
        "attempts": 1,
    }]

    counts = svc.run_sweeper(sb)

    assert counts["derivations"] == 1
    assert sb.db["mock_attempt_jobs"][0]["status"] == "done"


def test_sweeper_partial_failure_leaves_no_lost_work(monkeypatch):
    """AC2: when one job in a batch fails, the others still complete and the
    failed one is rescheduled (not dropped) for the next cycle."""
    sb, _, _ = _seeded_db()
    a1 = svc.start_attempt(sb, "user-1", "gate-mock")["attempt_id"]
    a2 = svc.start_attempt(sb, "user-2", "gate-mock")["attempt_id"]
    svc.submit_attempt(sb, "user-1", a1)
    svc.submit_attempt(sb, "user-2", a2)
    svc.schedule_job(sb, svc.JOB_ANALYTICS_RETRY, a1, scheduled_for=_past_iso(5))
    svc.schedule_job(sb, svc.JOB_ANALYTICS_RETRY, a2, scheduled_for=_past_iso(5))

    real = svc.attempt_analytics.compute_and_persist

    def flaky(supabase, attempt_id):
        if attempt_id == a2:
            raise RuntimeError("boom")
        return real(supabase, attempt_id)

    monkeypatch.setattr(svc.attempt_analytics, "compute_and_persist", flaky)
    counts = svc.run_sweeper(sb)

    assert counts["derivations"] == 1
    assert counts["errors"] == 1
    jobs = {j["attempt_id"]: j for j in sb.db["mock_attempt_jobs"]}
    assert jobs[a1]["status"] == "done"
    assert jobs[a2]["status"] == "pending"  # rescheduled, not lost

    # Next cycle, with derivation healthy again, finishes the unfinished work.
    monkeypatch.setattr(svc.attempt_analytics, "compute_and_persist", real)
    jobs[a2]["scheduled_for"] = _past_iso(1)
    svc.run_sweeper(sb)
    assert {j["attempt_id"]: j for j in sb.db["mock_attempt_jobs"]}[a2]["status"] == "done"


# ─── Fix 2: delta cap separate from clamp ─────────────────────────────────────

def test_apply_mastery_caps_extreme_delta_not_clamps():
    """AC3: a proposed +0.50-unit delta writes +15 db (cap), never +50."""
    sb = SBStub({"user_topic_mastery": [], "user_topic_mastery_audit": []})
    writer = MasteryWriter(sb, "live")

    writer._apply_mastery("att-1", [_delta("0.50")])

    audit = sb.db["user_topic_mastery_audit"]
    assert len(audit) == 1
    assert audit[0]["delta_applied_db"] == 15.0  # capped, not 50
    assert sb.db["user_topic_mastery"][0]["mastery_score"] == 65.0  # 50 + 15


def test_apply_mastery_clamp_is_a_separate_invariant():
    """The [0,100] clamp still bounds the result even for an in-cap delta:
    95 + 15 → 100, not 110. Cap and clamp are distinct."""
    sb = SBStub({
        "user_topic_mastery": [{"id": "m1", "user_id": "u1", "topic_id": "t1", "mastery_score": 95.0}],
        "user_topic_mastery_audit": [],
    })
    writer = MasteryWriter(sb, "live")

    writer._apply_mastery("att-1", [_delta("0.15")])

    assert sb.db["user_topic_mastery"][0]["mastery_score"] == 100.0
    assert sb.db["user_topic_mastery_audit"][0]["delta_applied_db"] == 15.0


def test_apply_mastery_negative_cap():
    """A proposed -0.50-unit delta writes -15 db, not -50."""
    sb = SBStub({
        "user_topic_mastery": [{"id": "m1", "user_id": "u1", "topic_id": "t1", "mastery_score": 50.0}],
        "user_topic_mastery_audit": [],
    })
    writer = MasteryWriter(sb, "live")

    writer._apply_mastery("att-1", [_delta("-0.50")])

    assert sb.db["user_topic_mastery_audit"][0]["delta_applied_db"] == -15.0
    assert sb.db["user_topic_mastery"][0]["mastery_score"] == 35.0


# ─── Fix 3: idempotency check-then-skip ───────────────────────────────────────

def test_apply_mastery_is_idempotent():
    """AC4: re-applying the same attempt is a silent no-op — one audit row,
    mastery moved once, no exception."""
    sb = SBStub({"user_topic_mastery": [], "user_topic_mastery_audit": []})
    writer = MasteryWriter(sb, "live")
    delta = _delta("0.10")  # +10 db

    writer._apply_mastery("att-1", [delta])
    writer._apply_mastery("att-1", [delta])  # duplicate — no-op

    assert len(sb.db["user_topic_mastery_audit"]) == 1
    assert sb.db["user_topic_mastery"][0]["mastery_score"] == 60.0  # applied once


def test_double_submit_under_live_flag_no_second_audit(monkeypatch):
    """AC4: submitting the same attempt twice under the live flag yields one
    audit row and identical results, no exception."""
    sb, _, _ = _seeded_db(topic_id="topic-A")
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
    client = _client(sb)

    start = client.post("/api/study/mocks/attempts/start", json={"template_slug": "gate-mock"})
    attempt_id = start.json()["attempt_id"]
    for q in sb.db["mock_question_bank"]:
        client.post(
            f"/api/study/mocks/attempts/{attempt_id}/answer",
            json={"question_id": q["id"], "selected_option_id": q["correct_option_id"], "client_seq": 1},
        )

    r1 = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    r2 = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")

    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["score_raw"] == r2.json()["score_raw"]
    audit = [a for a in sb.db.get("user_topic_mastery_audit", []) if a["topic_id"] == "topic-A"]
    assert len(audit) == 1  # no second audit row from the replay


# ─── Fix 4: derivation ordering (implementation B) ────────────────────────────

def test_mastery_deferred_when_derivation_fails(monkeypatch):
    """AC5 (updated): when analytics derivation fails, mastery is deferred, not
    silently skipped.

    With the classification readiness gate: analytics failure → no classification
    rows → MasteryClassificationNotReady → mastery retry job rescheduled pending.
    Both analytics_retry and mastery_retry are queued so recovery is fully
    automatic once analytics succeeds.
    """
    sb, _, _ = _seeded_db(topic_id="topic-B")
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
    client = _client(sb)

    start = client.post("/api/study/mocks/attempts/start", json={"template_slug": "gate-mock"})
    attempt_id = start.json()["attempt_id"]
    for q in sb.db["mock_question_bank"]:
        client.post(
            f"/api/study/mocks/attempts/{attempt_id}/answer",
            json={"question_id": q["id"], "selected_option_id": q["correct_option_id"], "client_seq": 1},
        )

    # Derivation (PR4) blows up → no classification rows will be written.
    monkeypatch.setattr(
        svc.attempt_analytics,
        "compute_and_persist",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("derivation down")),
    )

    r = client.post(f"/api/study/mocks/attempts/{attempt_id}/submit")
    assert r.status_code == 200

    # No summary written (derivation failed).
    assert not sb.db.get("mock_attempt_summary")
    # Mastery was deferred — no live writes.
    assert not sb.db.get("user_topic_mastery_audit")
    # Both analytics_retry and mastery_retry are queued for automatic recovery.
    jobs_by_kind = {j["job_kind"] for j in sb.db.get("mock_attempt_jobs", [])}
    assert "analytics_retry" in jobs_by_kind
    assert "mastery_retry" in jobs_by_kind
    mastery_jobs = [
        j for j in sb.db.get("mock_attempt_jobs", [])
        if j["job_kind"] == "mastery_retry" and j["attempt_id"] == attempt_id
    ]
    assert mastery_jobs[0]["status"] == "pending"


# ─── mock_tests_retry job (PR-fix-12) ────────────────────────────────────────


class _MockTestsFailStub(SBStub):
    """SBStub whose mock_tests.insert raises, simulating a DB failure."""

    def table(self, name):
        q = super().table(name)
        if name == "mock_tests":
            original_execute = q.execute

            def _raising():
                if q._pending_insert is not None:
                    raise RuntimeError("mock_tests insert failed: column does not exist")
                return original_execute()

            q.execute = _raising  # type: ignore[assignment]
        return q


def _seeded_fail_db():
    """Return a _MockTestsFailStub seeded the same as _seeded_db."""
    _, template, questions = _seeded_db()
    db = {
        "mock_templates": [template],
        "mock_question_bank": questions,
        "mock_question_options": [o for q in questions for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
        "mock_attempt_events": [],
        "mock_attempt_jobs": [],
        "mock_tests": [],
    }
    return _MockTestsFailStub(db), template, questions


def test_emit_mock_tests_row_failure_schedules_retry():
    """When mock_tests INSERT fails, a mock_tests_retry job is enqueued."""
    sb, _, _ = _seeded_fail_db()
    start = svc.start_attempt(sb, "user-1", "gate-mock")
    attempt_id = start["attempt_id"]

    svc.submit_attempt(sb, "user-1", attempt_id)

    assert not [r for r in sb.db.get("mock_tests", []) if r.get("mock_attempt_id") == attempt_id]
    retry_jobs = [j for j in sb.db.get("mock_attempt_jobs", []) if j.get("job_kind") == svc.JOB_MOCK_TESTS_RETRY]
    assert len(retry_jobs) == 1
    assert retry_jobs[0]["attempt_id"] == attempt_id


def test_retry_emit_mock_tests_row_writes_compat_row():
    """Sweeper processes mock_tests_retry and the compat row appears."""
    sb, _, _ = _seeded_db()
    start = svc.start_attempt(sb, "user-1", "gate-mock")
    attempt_id = start["attempt_id"]
    svc.submit_attempt(sb, "user-1", attempt_id)

    # Simulate the initial emit failing: remove the row and plant a retry job.
    sb.db["mock_tests"] = [r for r in sb.db["mock_tests"] if r.get("mock_attempt_id") != attempt_id]
    svc.schedule_job(sb, svc.JOB_MOCK_TESTS_RETRY, attempt_id, scheduled_for=_past_iso(5))

    svc.run_sweeper(sb)

    rows = [r for r in sb.db["mock_tests"] if r.get("mock_attempt_id") == attempt_id]
    assert len(rows) == 1
    assert rows[0]["trust_level"] == "platform_verified"
    assert rows[0]["source_type"] == "platform_attempt"


def test_retry_emit_mock_tests_row_idempotent():
    """Calling _retry_emit_mock_tests_row when a row already exists is a no-op."""
    sb, _, _ = _seeded_db()
    start = svc.start_attempt(sb, "user-1", "gate-mock")
    attempt_id = start["attempt_id"]
    svc.submit_attempt(sb, "user-1", attempt_id)

    before = len([r for r in sb.db["mock_tests"] if r.get("mock_attempt_id") == attempt_id])
    assert before == 1

    svc._retry_emit_mock_tests_row(sb, attempt_id)

    after = len([r for r in sb.db["mock_tests"] if r.get("mock_attempt_id") == attempt_id])
    assert after == 1


@pytest.mark.parametrize(
    ("max_score", "expected"),
    [(200.0, 200), (200, 200), (Decimal("200.0"), 200)],
)
def test_emit_mock_tests_row_coerces_integral_total_marks(max_score, expected):
    """Inline compat writer stores integral numeric totals as integer values."""
    sb = SBStub({"mock_tests": [], "mock_attempt_jobs": []})
    attempt = {
        "id": "attempt-inline-integral",
        "template_snapshot": {
            "name": "Integral Mock",
            "exam_family": "TEST",
            "duration_sec": 300,
        },
    }

    svc._emit_mock_tests_row(
        sb,
        "user-1",
        attempt,
        score_raw=123.45,
        max_score=max_score,
        total_correct=10,
        total_wrong=2,
        total_q=100,
        submitted_at=_now_iso(),
    )

    row = sb.db["mock_tests"][0]
    assert row["total_marks"] == expected
    assert type(row["total_marks"]) is int
    assert row["scored_marks"] == 123.45


def test_retry_emit_mock_tests_row_recreates_after_22p02_with_integer_total_marks():
    """Retry path recomputes 200.0 but emits integer 200 after prior 22P02."""
    sb, template, _ = _seeded_db()
    template["marks_per_correct"] = 40.0
    template["marks_per_wrong"] = 0.0
    start = svc.start_attempt(sb, "user-1", "gate-mock")
    attempt_id = start["attempt_id"]
    svc.submit_attempt(sb, "user-1", attempt_id)

    # Simulate the initial insert failing with Postgres 22P02 before the fix.
    sb.db["mock_tests"] = [
        r for r in sb.db["mock_tests"] if r.get("mock_attempt_id") != attempt_id
    ]
    svc.schedule_job(
        sb,
        svc.JOB_MOCK_TESTS_RETRY,
        attempt_id,
        last_error='invalid input syntax for type integer: "200.0" (22P02)',
        scheduled_for=_past_iso(5),
    )

    svc.run_sweeper(sb)

    rows = [r for r in sb.db["mock_tests"] if r.get("mock_attempt_id") == attempt_id]
    assert len(rows) == 1
    assert rows[0]["total_marks"] == 200
    assert type(rows[0]["total_marks"]) is int




def test_submit_attempt_inline_sums_exact_decimal_marks_to_integral_total():
    """Inline submit emits integer total_marks for ten Decimal('0.10') snapshots."""
    sb, _, questions = _seeded_db()
    for i in range(5, 10):
        question = _make_question(f"q{i}")
        questions.append(question)
        sb.db["mock_question_bank"].append(question)
        sb.db["mock_question_options"].extend(question["options"])
    template = sb.db["mock_templates"][0]
    template["total_questions"] = 10
    template["config"]["question_ids"] = [q["id"] for q in questions]

    start = svc.start_attempt(sb, "user-1", "gate-mock")
    attempt_id = start["attempt_id"]
    attempt_responses = [
        r for r in sb.db["mock_attempt_responses"] if r.get("attempt_id") == attempt_id
    ][:10]
    sb.db["mock_attempt_responses"] = [
        r for r in sb.db["mock_attempt_responses"] if r.get("attempt_id") != attempt_id
    ] + attempt_responses
    assert len(attempt_responses) == 10
    for response in attempt_responses:
        response["question_snapshot"]["marks"] = Decimal("0.10")

    result = svc.submit_attempt(sb, "user-1", attempt_id)

    assert result["status"] == "submitted"
    rows = [r for r in sb.db["mock_tests"] if r.get("mock_attempt_id") == attempt_id]
    assert len(rows) == 1
    assert rows[0]["total_marks"] == 1
    assert type(rows[0]["total_marks"]) is int
    assert rows[0]["scored_marks"] == 0.0
    assert not [
        j for j in sb.db["mock_attempt_jobs"]
        if j.get("job_kind") == svc.JOB_MOCK_TESTS_RETRY
        and j.get("attempt_id") == attempt_id
    ]

def test_retry_emit_mock_tests_row_sums_exact_decimal_marks_to_integral_total():
    """Ten Decimal('0.10') marks sum exactly to integer total_marks 1."""
    attempt_id = "attempt-decimal-tenths"
    sb = SBStub({
        "mock_attempts": [{
            "id": attempt_id,
            "user_id": "user-1",
            "template_snapshot": {"name": "Tenths", "exam_family": "TEST"},
            "score_raw": 0,
            "total_correct": 0,
            "total_wrong": 0,
            "submitted_at": _now_iso(),
        }],
        "mock_attempt_responses": [
            {"attempt_id": attempt_id, "question_snapshot": {"marks": Decimal("0.10")}}
            for _ in range(10)
        ],
        "mock_tests": [],
    })

    svc._retry_emit_mock_tests_row(sb, attempt_id)

    rows = [r for r in sb.db["mock_tests"] if r.get("mock_attempt_id") == attempt_id]
    assert len(rows) == 1
    assert rows[0]["total_marks"] == 1
    assert type(rows[0]["total_marks"]) is int

def test_retry_emit_mock_tests_row_coerces_decimal_integral_total_marks():
    """Retry path accepts Decimal integral marks and persists an int total."""
    sb, template, _ = _seeded_db()
    template["marks_per_correct"] = 40.0
    template["marks_per_wrong"] = 0.0
    start = svc.start_attempt(sb, "user-1", "gate-mock")
    attempt_id = start["attempt_id"]
    svc.submit_attempt(sb, "user-1", attempt_id)
    sb.db["mock_tests"] = [
        r for r in sb.db["mock_tests"] if r.get("mock_attempt_id") != attempt_id
    ]
    for response in sb.db["mock_attempt_responses"]:
        if response.get("attempt_id") == attempt_id:
            response["question_snapshot"]["marks"] = Decimal("40.0")

    svc._retry_emit_mock_tests_row(sb, attempt_id)

    rows = [r for r in sb.db["mock_tests"] if r.get("mock_attempt_id") == attempt_id]
    assert len(rows) == 1
    assert rows[0]["total_marks"] == 200
    assert type(rows[0]["total_marks"]) is int


def test_inline_non_integral_total_succeeds_and_schedules_retry():
    """Post-finalization compatibility failure must not fail submit."""
    sb, template, _ = _seeded_db()
    template["marks_per_correct"] = 40.1
    template["marks_per_wrong"] = 0.0
    start = svc.start_attempt(sb, "user-1", "gate-mock")
    attempt_id = start["attempt_id"]

    result = svc.submit_attempt(sb, "user-1", attempt_id)

    assert result["status"] == "submitted"
    assert result["score_raw"] == 0.0
    assert not [r for r in sb.db["mock_tests"] if r.get("mock_attempt_id") == attempt_id]
    retry_jobs = [
        j for j in sb.db["mock_attempt_jobs"]
        if j.get("job_kind") == svc.JOB_MOCK_TESTS_RETRY
        and j.get("attempt_id") == attempt_id
        and j.get("status") == "pending"
    ]
    assert len(retry_jobs) == 1
    assert "total_marks must be integral" in retry_jobs[0].get("last_error", "")


def test_sweeper_reschedules_non_integral_retry_observably():
    """Retry conversion failures propagate to sweeper backoff/rescheduling."""
    sb, template, _ = _seeded_db()
    template["marks_per_correct"] = 40.1
    template["marks_per_wrong"] = 0.0
    start = svc.start_attempt(sb, "user-1", "gate-mock")
    attempt_id = start["attempt_id"]
    svc.submit_attempt(sb, "user-1", attempt_id)

    counts = svc.run_sweeper(sb)

    assert counts["errors"] == 1
    assert not [r for r in sb.db["mock_tests"] if r.get("mock_attempt_id") == attempt_id]
    retry_jobs = [
        j for j in sb.db["mock_attempt_jobs"]
        if j.get("job_kind") == svc.JOB_MOCK_TESTS_RETRY
        and j.get("attempt_id") == attempt_id
        and j.get("status") == "pending"
    ]
    assert len(retry_jobs) == 1
    assert retry_jobs[0].get("attempts") == 1
    assert "total_marks must be integral" in retry_jobs[0].get("last_error", "")


def test_retry_emit_mock_tests_row_repeated_retry_is_idempotent_with_integer_total():
    """Repeated retry calls do not duplicate the recreated compat row."""
    sb, template, _ = _seeded_db()
    template["marks_per_correct"] = 40.0
    template["marks_per_wrong"] = 0.0
    start = svc.start_attempt(sb, "user-1", "gate-mock")
    attempt_id = start["attempt_id"]
    svc.submit_attempt(sb, "user-1", attempt_id)
    sb.db["mock_tests"] = [
        r for r in sb.db["mock_tests"] if r.get("mock_attempt_id") != attempt_id
    ]

    svc._retry_emit_mock_tests_row(sb, attempt_id)
    svc._retry_emit_mock_tests_row(sb, attempt_id)

    rows = [r for r in sb.db["mock_tests"] if r.get("mock_attempt_id") == attempt_id]
    assert len(rows) == 1
    assert rows[0]["total_marks"] == 200
