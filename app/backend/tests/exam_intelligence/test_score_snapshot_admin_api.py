"""Admin score-snapshot API tests.

Covers the three score-snapshot endpoints added to
``app.api.admin_exam_intelligence``:

    GET   /admin/exam-intelligence/exams/{exam_id}/score-snapshots
    PATCH /admin/exam-intelligence/score-snapshots/{snapshot_id}/review
    POST  /admin/exam-intelligence/exams/{exam_id}/score-snapshots/compute

The review lifecycle is::

    draft     → reviewed | rejected
    reviewed  → locked | rejected | draft
    locked    → reviewed  (reviewer_notes required)
    rejected  → draft
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.exam_intelligence.score_snapshots import MODEL_VERSION
from tests.exam_intelligence.test_admin_api import _build_app
from tests.persona_questions._stub import SBStub, _Exec


def _seed_snapshots():
    """Snapshots across every lifecycle status plus the parent exam row."""
    return {
        "exams": [
            {"id": "e1", "slug": "ssc-cgl", "name": "SSC CGL",
             "exam_type": "recruitment", "is_active": True},
        ],
        "exam_topic_score_snapshots": [
            {"id": "s-draft", "exam_id": "e1", "topic_id": "t1", "status": "draft",
             "model_version": MODEL_VERSION, "exam_priority_score": 90,
             "is_high_yield": True, "confidence_score": 0.9, "evidence_count": 3,
             "score_components": {}, "input_summary": {},
             "computed_at": "2026-05-04T00:00:00+00:00"},
            {"id": "s-reviewed", "exam_id": "e1", "topic_id": "t2", "status": "reviewed",
             "model_version": MODEL_VERSION, "exam_priority_score": 80,
             "is_high_yield": True, "confidence_score": 0.8, "evidence_count": 2,
             "score_components": {}, "input_summary": {},
             "computed_at": "2026-05-03T00:00:00+00:00"},
            {"id": "s-locked", "exam_id": "e1", "topic_id": "t3", "status": "locked",
             "model_version": MODEL_VERSION, "exam_priority_score": 70,
             "is_high_yield": False, "confidence_score": 0.7, "evidence_count": 1,
             "score_components": {}, "input_summary": {},
             "computed_at": "2026-05-02T00:00:00+00:00"},
            {"id": "s-rejected", "exam_id": "e1", "topic_id": "t4", "status": "rejected",
             "model_version": MODEL_VERSION, "exam_priority_score": 60,
             "is_high_yield": False, "confidence_score": 0.6, "evidence_count": 0,
             "score_components": {}, "input_summary": {},
             "computed_at": "2026-05-01T00:00:00+00:00"},
            # A second exam's snapshot to prove exam scoping on the list endpoint.
            {"id": "s-other", "exam_id": "e2", "topic_id": "t9", "status": "draft",
             "model_version": MODEL_VERSION, "exam_priority_score": 50,
             "is_high_yield": False, "confidence_score": 0.5, "evidence_count": 0,
             "score_components": {}, "input_summary": {},
             "computed_at": "2026-04-30T00:00:00+00:00"},
        ],
    }


def _compute_seed():
    """Minimal valid data so compute writes >=1 snapshot.

    Mirrors test_score_snapshots.py: a verified paper, a verified question,
    a primary verified tag, and a locked coverage row for the same topic.
    """
    return {
        "exams": [
            {"id": "e1", "slug": "ssc-cgl", "name": "SSC CGL",
             "exam_type": "recruitment", "is_active": True},
        ],
        "pyq_papers": [
            {"id": "p1", "exam_id": "e1", "trust_status": "verified"},
        ],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"},
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1",
             "reviewer_status": "verified", "tag_role": "primary"},
        ],
        "exam_topic_coverage": [
            {"topic_id": "t1", "exam_id": "e1", "exam_priority_score": 80,
             "is_high_yield": True, "reviewer_status": "locked"},
        ],
    }


_LIST_BASE = "/api/admin/exam-intelligence/exams/e1/score-snapshots"
_REVIEW_BASE = "/api/admin/exam-intelligence/score-snapshots"
_COMPUTE_BASE = "/api/admin/exam-intelligence/exams/e1/score-snapshots/compute"


# ─── List ──────────────────────────────────────────────────────────────────
def test_list_snapshots_returns_all():
    sb = SBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.get(_LIST_BASE)
    assert r.status_code == 200
    body = r.json()
    assert body["exam_id"] == "e1"
    # Only e1's four snapshots — the e2 row must be scoped out.
    assert body["total"] == 4
    assert len(body["snapshots"]) == 4
    ids = {s["id"] for s in body["snapshots"]}
    assert ids == {"s-draft", "s-reviewed", "s-locked", "s-rejected"}


def test_list_snapshots_status_filter():
    sb = SBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.get(f"{_LIST_BASE}?status=locked")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["snapshots"] and all(s["status"] == "locked" for s in body["snapshots"])
    assert body["snapshots"][0]["id"] == "s-locked"


def test_list_snapshots_blocked_for_non_admin():
    sb = SBStub(_seed_snapshots())
    client = TestClient(_build_app(sb, role="user"))
    r = client.get(_LIST_BASE)
    assert r.status_code == 403


# ─── Review: allowed transitions ─────────────────────────────────────────────
def test_review_draft_to_reviewed():
    sb = SBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/s-draft/review", json={"status": "reviewed"})
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["snapshot_id"] == "s-draft"
    assert body["new_status"] == "reviewed"
    # The stub holds rows by reference, so the mutation is visible in the store.
    row = next(s for s in sb.db["exam_topic_score_snapshots"] if s["id"] == "s-draft")
    assert row["status"] == "reviewed"
    assert row["reviewed_by"] == "admin-1"
    assert row["reviewed_at"]


def test_review_reviewed_to_locked():
    sb = SBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/s-reviewed/review", json={"status": "locked"})
    assert r.status_code == 200
    assert r.json()["new_status"] == "locked"
    row = next(s for s in sb.db["exam_topic_score_snapshots"] if s["id"] == "s-reviewed")
    assert row["status"] == "locked"


# ─── Review: invalid transition ──────────────────────────────────────────────
def test_review_invalid_transition_rejected():
    # draft → locked skips the mandatory reviewed step.
    sb = SBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/s-draft/review", json={"status": "locked"})
    assert r.status_code == 422
    # The row must be untouched after a rejected transition.
    row = next(s for s in sb.db["exam_topic_score_snapshots"] if s["id"] == "s-draft")
    assert row["status"] == "draft"


# ─── Review: locked → reviewed requires notes ────────────────────────────────
def test_review_locked_to_reviewed_requires_notes():
    # Without reviewer_notes → 422.
    sb = SBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/s-locked/review", json={"status": "reviewed"})
    assert r.status_code == 422
    row = next(s for s in sb.db["exam_topic_score_snapshots"] if s["id"] == "s-locked")
    assert row["status"] == "locked"  # unchanged

    # With reviewer_notes → succeeds.
    sb2 = SBStub(_seed_snapshots())
    client2 = TestClient(_build_app(sb2))
    r2 = client2.patch(
        f"{_REVIEW_BASE}/s-locked/review",
        json={"status": "reviewed", "reviewer_notes": "Re-checked PYQ counts."},
    )
    assert r2.status_code == 200
    assert r2.json()["new_status"] == "reviewed"
    row2 = next(s for s in sb2.db["exam_topic_score_snapshots"] if s["id"] == "s-locked")
    assert row2["status"] == "reviewed"
    assert row2["reviewer_notes"] == "Re-checked PYQ counts."


# ─── Review: not found ───────────────────────────────────────────────────────
def test_review_snapshot_not_found():
    sb = SBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/no-such/review", json={"status": "reviewed"})
    assert r.status_code == 404


def test_review_blocked_for_non_admin():
    sb = SBStub(_seed_snapshots())
    client = TestClient(_build_app(sb, role="user"))
    r = client.patch(f"{_REVIEW_BASE}/s-draft/review", json={"status": "reviewed"})
    assert r.status_code == 403


# ─── Review: concurrent modification returns 409 ─────────────────────────────
def test_review_returns_409_on_concurrent_modification():
    """Conditional UPDATE finds no matching row (status changed between SELECT and UPDATE) → 409."""

    class _ConcurrentModStub(SBStub):
        """Simulates a race condition: returns empty data from the UPDATE call."""

        def __init__(self, db):
            super().__init__(db)
            self._snapshots_call_count = 0

        def table(self, name: str):
            q = super().table(name)
            if name != "exam_topic_score_snapshots":
                return q
            # Track which call this is (1st = SELECT, 2nd = UPDATE).
            self._snapshots_call_count += 1
            call_num = self._snapshots_call_count
            original_execute = q.execute

            def _intercepted():
                result = original_execute()
                if call_num == 2:
                    # Simulate the row's status having changed between SELECT and UPDATE.
                    return _Exec([])
                return result

            q.execute = _intercepted
            return q

    sb = _ConcurrentModStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/s-draft/review", json={"status": "reviewed"})
    assert r.status_code == 409, r.text


# ─── Review: DB write failure returns 500 ────────────────────────────────────
def test_review_returns_500_on_write_failure():
    """UPDATE raises an exception (DB failure) → 500."""

    class _WriteFailStub(SBStub):
        def __init__(self, db):
            super().__init__(db)
            self._snapshots_call_count = 0

        def table(self, name: str):
            q = super().table(name)
            if name != "exam_topic_score_snapshots":
                return q
            self._snapshots_call_count += 1
            call_num = self._snapshots_call_count
            original_execute = q.execute

            def _intercepted():
                if call_num == 2:
                    raise RuntimeError("DB connection lost")
                return original_execute()

            q.execute = _intercepted
            return q

    sb = _WriteFailStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(f"{_REVIEW_BASE}/s-draft/review", json={"status": "reviewed"})
    assert r.status_code == 500, r.text


# ─── Compute ─────────────────────────────────────────────────────────────────
def test_compute_blocked_for_non_admin():
    sb = SBStub(_compute_seed())
    client = TestClient(_build_app(sb, role="user"))
    r = client.post(_COMPUTE_BASE, json={})
    assert r.status_code == 403


def test_compute_returns_summary():
    sb = SBStub(_compute_seed())
    client = TestClient(_build_app(sb))
    r = client.post(_COMPUTE_BASE, json={})
    assert r.status_code == 200
    body = r.json()
    # Summary keys from compute_exam_topic_scores plus the endpoint's additions.
    for key in ("written", "skipped", "errors", "total_topics", "exam_id", "model_version"):
        assert key in body, f"missing {key} in compute response: {body}"
    assert body["exam_id"] == "e1"
    # model_version is server-owned; must always equal the deployed constant.
    assert body["model_version"] == MODEL_VERSION
    assert body["written"] >= 0
    # One topic (t1) has a locked coverage row + a primary verified tag.
    assert body["written"] == 1
    assert body["total_topics"] == 1
    snapshots = sb.db.get("exam_topic_score_snapshots", [])
    assert len(snapshots) == 1
    assert snapshots[0]["topic_id"] == "t1"
    assert snapshots[0]["status"] == "draft"


def test_compute_returns_502_on_read_failure():
    """When the DB raises on a critical input read, the endpoint returns 502."""

    class _BrokenSb:
        def table(self, name: str):
            raise RuntimeError(f"table {name!r} not available")

    client = TestClient(_build_app(_BrokenSb()))
    r = client.post(_COMPUTE_BASE, json={})
    assert r.status_code == 502, r.text


def test_compute_rejects_model_version_in_body():
    """Passing model_version in the request body is rejected (server-owned field)."""
    sb = SBStub(_compute_seed())
    client = TestClient(_build_app(sb))
    r = client.post(_COMPUTE_BASE, json={"model_version": "v999"})
    assert r.status_code == 422, (
        "model_version is server-owned and must be rejected when passed by the client"
    )


def test_compute_returns_422_on_invalid_phase():
    """exam_phase_id belonging to a different exam → HTTP 422 (not 502 or 200)."""
    seed = {
        **_compute_seed(),
        "exam_phases": [
            {"id": "phase-x", "exam_id": "exam-other"},  # belongs to the wrong exam
        ],
    }
    sb = SBStub(seed)
    client = TestClient(_build_app(sb))
    r = client.post(_COMPUTE_BASE, json={"exam_phase_id": "phase-x"})
    assert r.status_code == 422, r.text
    assert "exam_phase_id" in r.json().get("detail", "").lower()


def test_review_writes_audit_log_on_locked_reversal():
    """locked → reviewed transition must write a row to admin_audit_logs."""
    sb = SBStub(_seed_snapshots())
    client = TestClient(_build_app(sb))
    r = client.patch(
        f"{_REVIEW_BASE}/s-locked/review",
        json={"status": "reviewed", "reviewer_notes": "Re-checked PYQ counts."},
    )
    assert r.status_code == 200
    logs = sb.db.get("admin_audit_logs", [])
    assert len(logs) == 1
    log = logs[0]
    assert log["action"] == "snapshot_status_transition"
    assert log["entity_type"] == "exam_topic_score_snapshot"
    assert log["entity_id"] == "s-locked"
    assert log["old_value"] == {"status": "locked"}
    assert log["new_value"] == {"status": "reviewed"}
    assert log["notes"] == "Re-checked PYQ counts."
    assert log["actor_id"] == "admin-1"
