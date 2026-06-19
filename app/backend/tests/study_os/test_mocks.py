"""Production Mocks surface — service-layer + API tests with the in-memory
Supabase stub.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import study_os as study_os_api
from app.core.auth import get_current_user
from app.study_os import mocks as mocks_service
from tests.persona_questions._stub import SBStub


def _client(sb: SBStub):
    app = FastAPI()
    app.include_router(study_os_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": "user-1"}
    study_os_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


# ─────────────────────────── service-level tests ────────────────────────────
def test_create_mock_persists_row_and_breakdowns():
    sb = SBStub({})
    out = mocks_service.create_mock(
        sb,
        "user-1",
        {
            "name": "Mock 13",
            "exam_slug": "ssc-cgl-2026",
            "score": 122,
            "max_score": 200,
            "duration_min": 60,
            "attempted": 100,
            "correct": 80,
            "weak_topics": ["Polity", "Modern History"],
            "error_patterns": {"concept": 4, "time": 2},
            "subject_breakdown": [
                {"subject": "Polity", "total_questions": 40, "correct_answers": 24, "wrong_answers": 16, "accuracy": 0.6},
            ],
        },
    )
    assert out["name"] == "Mock 13"
    assert out["percentage"] == 61.0
    assert out["weak_topics"] == ["Polity", "Modern History"]
    assert out["error_patterns"] == {"concept": 4, "time": 2}
    assert out["wrong"] == 20
    assert len(out["subject_breakdown"]) == 1
    assert sb.db["mock_tests"][0]["user_id"] == "user-1"
    assert sb.db["mock_subject_breakdowns"][0]["subject"] == "Polity"


def test_list_mocks_returns_newest_first():
    sb = SBStub({})
    mocks_service.create_mock(sb, "user-1", {"name": "M1", "score": 100, "max_score": 200, "attempted_at": "2026-01-01T00:00:00Z"})
    mocks_service.create_mock(sb, "user-1", {"name": "M2", "score": 110, "max_score": 200, "attempted_at": "2026-01-08T00:00:00Z"})
    items = mocks_service.list_mocks(sb, "user-1")
    assert [m["name"] for m in items] == ["M2", "M1"]
    trend = mocks_service.mock_trend(items)
    assert [t["name"] for t in trend] == ["M1", "M2"]


def test_set_review_state_only_allows_valid_states():
    sb = SBStub({})
    m = mocks_service.create_mock(sb, "user-1", {"name": "M1", "score": 100, "max_score": 200})
    out = mocks_service.set_review_state(sb, "user-1", m["id"], "reviewed")
    assert out["review_state"] == "reviewed"

    import pytest
    with pytest.raises(ValueError):
        mocks_service.set_review_state(sb, "user-1", m["id"], "not_a_state")


def test_draft_correction_tasks_uses_error_patterns():
    sb = SBStub({})
    m = mocks_service.create_mock(
        sb,
        "user-1",
        {
            "name": "M1",
            "score": 100,
            "max_score": 200,
            "weak_topics": ["Polity"],
            "error_patterns": {"concept": 3, "time": 1, "memory": 0},
        },
    )
    drafts = mocks_service.draft_correction_tasks(sb, "user-1", m["id"])
    categories = [d["category"] for d in drafts]
    # concept_gap from "concept: 3", speed_issue from "time: 1",
    # memory_gap suppressed because count is 0.
    assert "concept_gap" in categories
    assert "speed_issue" in categories
    assert "memory_gap" not in categories
    # Mock review_state should be bumped to correction_drafted.
    refreshed = mocks_service.get_mock(sb, "user-1", m["id"])
    assert refreshed["review_state"] == "correction_drafted"


def test_draft_correction_falls_back_to_first_weak_topic_when_no_errors():
    sb = SBStub({})
    m = mocks_service.create_mock(
        sb,
        "user-1",
        {
            "name": "M1",
            "score": 100,
            "max_score": 200,
            "weak_topics": ["Polity", "Economy", "History", "Geo"],
            "error_patterns": {},
        },
    )
    drafts = mocks_service.draft_correction_tasks(sb, "user-1", m["id"])
    # The shared policy owns weak-topic fallback categorization and emits one
    # category set per normalized evidence input.
    assert len(drafts) == 1
    assert drafts[0]["category"] == "concept_gap"
    assert drafts[0]["topic"] == "Polity"


def test_draft_correction_replaces_prior_drafts():
    sb = SBStub({})
    m = mocks_service.create_mock(
        sb,
        "user-1",
        {"name": "M1", "score": 100, "max_score": 200, "error_patterns": {"concept": 1}},
    )
    first = mocks_service.draft_correction_tasks(sb, "user-1", m["id"])
    second = mocks_service.draft_correction_tasks(sb, "user-1", m["id"])
    # Prior drafted rows wiped; new ones in place. Only one set of drafted
    # rows remains in storage.
    drafted_rows = [r for r in sb.db.get("mock_correction_tasks", []) if r.get("state") == "drafted"]
    assert len(drafted_rows) == len(second)
    assert len(first) == len(second)


def test_apply_correction_task_creates_study_task_and_links():
    sb = SBStub({"study_plans": [{"id": "plan-1", "user_id": "user-1", "status": "active", "created_at": "2026-01-01T00:00:00Z"}]})
    m = mocks_service.create_mock(
        sb,
        "user-1",
        {"name": "M1", "score": 100, "max_score": 200, "error_patterns": {"concept": 1}, "weak_topics": ["Polity"]},
    )
    drafts = mocks_service.draft_correction_tasks(sb, "user-1", m["id"])
    correction = drafts[0]
    applied = mocks_service.apply_correction_task(sb, "user-1", correction["id"])
    assert applied["state"] == "applied"
    assert applied["study_task_id"] is not None
    # study_tasks row was created and tagged.
    task_row = sb.db["study_tasks"][0]
    assert task_row["task_type"] == "mock_correction"
    assert task_row["metadata"]["mock_test_id"] == m["id"]
    assert task_row["plan_id"] == "plan-1"


# ───────────────────────────── API-level tests ──────────────────────────────
def test_api_create_then_list():
    sb = SBStub({})
    client = _client(sb)
    r = client.post(
        "/api/study/mocks",
        json={
            "name": "Mock 13",
            "exam_slug": "ssc-cgl-2026",
            "score": 122,
            "max_score": 200,
            "duration_min": 60,
            "attempted": 100,
            "correct": 80,
            "weak_topics": ["Polity"],
        },
    )
    assert r.status_code == 200
    assert r.json()["percentage"] == 61.0

    listed = client.get("/api/study/mocks").json()
    assert listed["items"][0]["name"] == "Mock 13"
    assert isinstance(listed["trend"], list)


def test_api_set_review_state_validates_value():
    sb = SBStub({})
    client = _client(sb)
    created = client.post("/api/study/mocks", json={"name": "M", "score": 1, "max_score": 1}).json()
    ok = client.patch(
        f"/api/study/mocks/{created['id']}/review-state",
        json={"state": "reviewed"},
    )
    assert ok.status_code == 200
    assert ok.json()["review_state"] == "reviewed"

    bad = client.patch(
        f"/api/study/mocks/{created['id']}/review-state",
        json={"state": "not_a_state"},
    )
    assert bad.status_code == 422


def test_api_correction_flow_end_to_end():
    sb = SBStub({"study_plans": [{"id": "plan-1", "user_id": "user-1", "status": "active", "created_at": "2026-01-01"}]})
    client = _client(sb)
    mock = client.post(
        "/api/study/mocks",
        json={
            "name": "M",
            "score": 1,
            "max_score": 2,
            "weak_topics": ["Polity"],
            "error_patterns": {"concept": 2, "time": 1},
        },
    ).json()

    drafted = client.post(f"/api/study/mocks/{mock['id']}/correction-tasks").json()
    assert len(drafted["items"]) >= 1
    correction_id = drafted["items"][0]["id"]

    applied = client.post(f"/api/study/mocks/correction-tasks/{correction_id}/apply").json()
    assert applied["state"] == "applied"
    assert applied["study_task_id"] is not None


def test_api_analysis_bundle_shape():
    sb = SBStub({})
    client = _client(sb)
    mock = client.post(
        "/api/study/mocks",
        json={
            "name": "M",
            "score": 50,
            "max_score": 100,
            "weak_topics": ["Polity"],
            "error_patterns": {"concept": 1},
            "subject_breakdown": [
                {"subject": "Polity", "total_questions": 10, "correct_answers": 4, "wrong_answers": 6, "accuracy": 0.4}
            ],
        },
    ).json()
    bundle = client.get(f"/api/study/mocks/{mock['id']}/analysis").json()
    assert bundle["mock"]["name"] == "M"
    assert bundle["subject_breakdown"][0]["subject"] == "Polity"
    assert bundle["error_patterns"] == {"concept": 1}
    assert bundle["weak_topics"] == ["Polity"]
    assert bundle["review_state"] == "unreviewed"
    assert bundle["correction_tasks"] == []


# ───────────────────── BLOCKER 3: writer authority tests ────────────────────


def test_draft_correction_platform_attempt_raises_forbidden():
    """draft_correction_tasks must raise PlatformAttemptCorrectionForbiddenError
    for platform_attempt mocks — MasteryWriter owns that pipeline."""
    import pytest
    sb = SBStub({})
    # Insert a platform_attempt mock directly
    from tests.persona_questions._stub import SBStub as _SB
    sb2 = _SB({
        "mock_tests": [{
            "id": "mt-plat",
            "user_id": "user-1",
            "source_type": "platform_attempt",
            "weak_topics": [],
            "error_patterns": {},
            "review_state": "unreviewed",
            "mock_attempt_id": "att-1",
        }]
    })
    with pytest.raises(mocks_service.PlatformAttemptCorrectionForbiddenError):
        mocks_service.draft_correction_tasks(sb2, "user-1", "mt-plat")


def test_draft_correction_manual_log_allowed():
    """manual_log mocks can go through the rule-based correction path."""
    sb = SBStub({})
    m = mocks_service.create_mock(
        sb,
        "user-1",
        {"name": "M1", "score": 100, "max_score": 200,
         "error_patterns": {"concept": 2}, "weak_topics": ["Polity"]},
    )
    # source_type defaults to manual_log — should succeed
    drafts = mocks_service.draft_correction_tasks(sb, "user-1", m["id"])
    assert len(drafts) >= 1


def test_draft_correction_imported_result_allowed():
    """imported_result mocks are also allowed through the manual path."""
    from tests.persona_questions._stub import SBStub as _SB
    sb = _SB({
        "mock_tests": [{
            "id": "mt-imp",
            "user_id": "user-1",
            "source_type": "imported_result",
            "weak_topics": ["Polity"],
            "error_patterns": {"concept": 1},
            "review_state": "unreviewed",
            "mock_attempt_id": None,
        }],
        "mock_correction_tasks": [],
        "mock_subject_breakdowns": [],
    })
    drafts = mocks_service.draft_correction_tasks(sb, "user-1", "mt-imp")
    assert len(drafts) >= 1


def test_api_draft_correction_platform_attempt_returns_409():
    """POST /mocks/{id}/correction-tasks must return 409 for platform_attempt mocks."""
    from tests.persona_questions._stub import SBStub as _SB
    sb = _SB({
        "mock_tests": [{
            "id": "mt-plat",
            "user_id": "user-1",
            "source_type": "platform_attempt",
            "weak_topics": [],
            "error_patterns": {},
            "review_state": "unreviewed",
            "mock_attempt_id": "att-1",
        }],
        "mock_subject_breakdowns": [],
    })
    client = _client(sb)
    r = client.post("/api/study/mocks/mt-plat/correction-tasks")
    assert r.status_code == 409
    body = r.json()
    assert body["detail"]["error"] == "PLATFORM_ATTEMPT_MANUAL_CORRECTION_FORBIDDEN"


def test_api_draft_correction_another_user_mock_returns_404():
    """A mock owned by a different user returns 404, not 403."""
    from tests.persona_questions._stub import SBStub as _SB
    sb = _SB({
        "mock_tests": [{
            "id": "mt-other",
            "user_id": "user-99",
            "source_type": "manual_log",
            "weak_topics": ["Polity"],
            "error_patterns": {"concept": 1},
            "review_state": "unreviewed",
            "mock_attempt_id": None,
        }],
        "mock_subject_breakdowns": [],
    })
    client = _client(sb)
    r = client.post("/api/study/mocks/mt-other/correction-tasks")
    assert r.status_code == 404


# ─────────────── BLOCKER 2: 23505 conflict handling tests ───────────────────


def test_draft_correction_idempotent_when_row_exists():
    """When a drafted row already exists, the RPC upserts it and returns it."""
    from tests.persona_questions._stub import SBStub as _SB

    class _ConflictingInsertQuery:
        def __init__(self, name, db):
            self.name = name
            self.db = db
            self._q = None

        def select(self, *a, **kw):
            from tests.persona_questions._stub import _Query
            self._q = _Query(self.name, self.db)
            return self._q.select(*a, **kw)

        def eq(self, *a, **kw):
            if self._q:
                return self._q.eq(*a, **kw)
            return self

        def delete(self):
            # No-op: simulate concurrent scenario where another request already
            # re-inserted the rows after our delete — they'll be present for
            # the fallback select after insert raises 23505.
            class _Noop:
                def eq(self, *a, **kw): return self
                def execute(self): return type("R", (), {"data": []})()
            return _Noop()

        def insert(self, payload):
            self._payload = payload
            return self

        def execute(self):
            raise RuntimeError("23505 duplicate key value violates unique constraint")

    class _MockSB(_SB):
        def __init__(self, db):
            super().__init__(db)
            self._conflict_table = None

        def set_conflict_table(self, name):
            self._conflict_table = name

        def table(self, name):
            if name == self._conflict_table:
                return _ConflictingInsertQuery(name, self.db)
            return super().table(name)

    sb = _MockSB({
        "mock_tests": [{
            "id": "mt-1",
            "user_id": "user-1",
            "source_type": "manual_log",
            "weak_topics": ["Polity"],
            "error_patterns": {"concept": 1},
            "review_state": "unreviewed",
            "mock_attempt_id": None,
        }],
        "mock_correction_tasks": [
            # Pre-existing drafted correction
            {
                "id": "existing-c1",
                "mock_test_id": "mt-1",
                "user_id": "user-1",
                "category": "concept_gap",
                "topic": "Polity",
                "state": "drafted",
                "title": "Concept Gap",
                "source_questions": [],
            }
        ],
        "mock_subject_breakdowns": [],
    })
    sb.set_conflict_table("mock_correction_tasks")

    result = mocks_service.draft_correction_tasks(sb, "user-1", "mt-1")
    # Should return the existing row, not raise
    assert len(result) >= 1
    assert result[0]["category"] == "concept_gap"


def test_draft_correction_rpc_error_propagates():
    """RPC errors must propagate to the caller — no _safe swallowing (D4 fix)."""
    import pytest
    from tests.persona_questions._stub import SBStub as _SB

    class _ErrorSB(_SB):
        def rpc(self, name, params=None):
            if name == "replace_manual_mock_correction_drafts":
                raise RuntimeError("network timeout")
            return super().rpc(name, params)

    sb = _ErrorSB({
        "mock_tests": [{
            "id": "mt-1", "user_id": "user-1",
            "source_type": "manual_log",
            "weak_topics": ["Polity"], "error_patterns": {"concept": 1},
            "review_state": "unreviewed", "mock_attempt_id": None,
        }],
        "mock_subject_breakdowns": [],
    })
    with pytest.raises(RuntimeError, match="network timeout"):
        mocks_service.draft_correction_tasks(sb, "user-1", "mt-1")


def test_empty_drafts_sets_reviewed_state():
    """Empty draft set (no error patterns, no weak topics): review_state is set to
    'reviewed' and the function returns [].  This is the explicitly documented
    empty-draft contract — the mock has been reviewed but no corrections apply."""
    from tests.persona_questions._stub import SBStub as _SB
    sb = _SB({
        "mock_tests": [{
            "id": "mt-1", "user_id": "user-1",
            "source_type": "manual_log",
            "weak_topics": [], "error_patterns": {},
            "review_state": "unreviewed", "mock_attempt_id": None,
        }],
        "mock_correction_tasks": [],
        "mock_subject_breakdowns": [],
    })
    result = mocks_service.draft_correction_tasks(sb, "user-1", "mt-1")
    assert result == []
    mt = sb.db["mock_tests"][0]
    assert mt.get("review_state") == "reviewed"  # advanced to 'reviewed', not 'correction_drafted'
