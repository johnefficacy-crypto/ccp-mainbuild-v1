"""Tests for mock review and correction-task endpoints in canonical.py."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import canonical as canonical_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub, _Exec


def _seed() -> dict:
    return {
        "mock_tests": [
            {"id": "m1", "user_id": "u-1", "exam_id": "exam-1", "test_name": "M1", "source_type": "manual_log"},
            {"id": "m2", "user_id": "other-user", "exam_id": "exam-1", "source_type": "manual_log"},
            {"id": "m3", "user_id": "u-1", "exam_id": "exam-1", "test_name": "M3-platform", "source_type": "platform_attempt"},
        ],
        "study_plans": [{"id": "p1", "user_id": "u-1", "status": "active"}],
        "topics": [
            {"id": "t1", "name": "Percentage", "subject_id": "s1"},
            {"id": "t2", "name": "Profit", "subject_id": "s1"},
        ],
        "profiles": [{"id": "u-1"}],
    }


def _client(sb: SBStub, user_id: str = "u-1") -> TestClient:
    app = FastAPI()
    app.include_router(canonical_api.router, prefix="/api")
    canonical_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id, "role": "user"}
    return app, TestClient(app)


# ─── /mocks/:id/review ────────────────────────────────────────────────────
def test_review_persists_error_types_and_status():
    sb = SBStub(_seed())
    _, client = _client(sb)
    r = client.post(
        "/api/study/mocks/m1/review",
        json={
            "review_status": "reviewed",
            "error_types": {"concept_gap": 3, "time_pressure": 1},
            "notes": "Need to revisit percentages.",
        },
    )
    assert r.status_code == 200
    mock = sb.db["mock_tests"][0]
    assert mock["review_status"] == "reviewed"
    assert mock["error_types"] == {"concept_gap": 3, "time_pressure": 1}
    assert mock["notes"] == "Need to revisit percentages."


def test_review_404_for_another_users_mock():
    sb = SBStub(_seed())
    _, client = _client(sb)
    r = client.post(
        "/api/study/mocks/m2/review",
        json={"review_status": "reviewed"},
    )
    assert r.status_code == 404


def test_review_5xx_when_mock_tests_update_fails_and_does_not_continue():
    """X-PR0: a silent mock_tests update failure must 5xx, not 200, and must NOT
    fall through into the breakdown / mastery / regeneration writes."""
    sb = SBStub(_seed())

    # Force only the mock_tests UPDATE to report an empty write (the ownership
    # SELECT must still succeed so we reach the hardened update).
    class _FailUpdateQuery:
        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, name):
            attr = getattr(self._inner, name)
            if callable(attr):
                def wrapper(*a, **k):
                    res = attr(*a, **k)
                    return self if res is self._inner else res
                return wrapper
            return attr

        def execute(self):
            i = self._inner
            if i._pending_update not in (None, "__delete__"):
                return _Exec([])
            return i.execute()

    class _FailSB:
        def __init__(self, inner):
            self.db = inner.db
            self._inner = inner

        def table(self, name):
            q = self._inner.table(name)
            return _FailUpdateQuery(q) if name == "mock_tests" else q

        def rpc(self, *a, **k):
            return self._inner.rpc(*a, **k)

    _, client = _client(_FailSB(sb))
    r = client.post(
        "/api/study/mocks/m1/review",
        json={
            "review_status": "reviewed",
            "topic_breakdowns": [{"topic_id": "t1", "wrong_answers": 2}],
        },
    )
    assert r.status_code == 503
    # No continuation: breakdown rows must not have been written.
    assert sb.db.get("mock_topic_breakdowns", []) == []


def test_review_with_topic_breakdowns_aggregates_errors():
    sb = SBStub(_seed())
    _, client = _client(sb)
    r = client.post(
        "/api/study/mocks/m1/review",
        json={
            "review_status": "reviewed",
            "topic_breakdowns": [
                {"topic_id": "t1", "wrong_answers": 2,
                 "error_types": {"concept_gap": 2}},
                {"topic_id": "t2", "wrong_answers": 1,
                 "error_types": {"concept_gap": 1, "misread": 1}},
            ],
        },
    )
    assert r.status_code == 200
    mock = sb.db["mock_tests"][0]
    # error counts aggregated server-side
    assert mock["error_types"] == {"concept_gap": 3, "misread": 1}
    # breakdowns persisted
    assert len(sb.db["mock_topic_breakdowns"]) == 2


def test_review_replaces_prior_breakdowns_idempotently():
    sb = SBStub(_seed())
    _, client = _client(sb)
    client.post(
        "/api/study/mocks/m1/review",
        json={
            "review_status": "reviewed",
            "topic_breakdowns": [
                {"topic_id": "t1", "wrong_answers": 5},
            ],
        },
    )
    # Second call with a different breakdown set must replace, not append.
    client.post(
        "/api/study/mocks/m1/review",
        json={
            "review_status": "reviewed",
            "topic_breakdowns": [
                {"topic_id": "t2", "wrong_answers": 1},
            ],
        },
    )
    assert len(sb.db["mock_topic_breakdowns"]) == 1
    assert sb.db["mock_topic_breakdowns"][0]["topic_id"] == "t2"


# ─── Source-based mastery writer authority (PR2) ─────────────────────────────

def test_platform_attempt_rejects_topic_breakdowns_with_409():
    """A platform_attempt mock must not accept topic_breakdowns (409)."""
    sb = SBStub(_seed())
    _, client = _client(sb)
    r = client.post(
        "/api/study/mocks/m3/review",
        json={
            "review_status": "reviewed",
            "topic_breakdowns": [{"topic_id": "t1", "wrong_answers": 2}],
        },
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "platform_attempt_authoritative_fields_rejected"


def test_platform_attempt_breakdown_rejection_writes_nothing():
    """On 409 no mock_tests update, no breakdowns, no mastery writes occur."""
    sb = SBStub(_seed())
    _, client = _client(sb)
    client.post(
        "/api/study/mocks/m3/review",
        json={
            "review_status": "reviewed",
            "topic_breakdowns": [{"topic_id": "t1", "wrong_answers": 2}],
        },
    )
    # mock_tests row must not have been mutated
    platform_mock = next(m for m in sb.db["mock_tests"] if m["id"] == "m3")
    assert platform_mock.get("review_status") is None
    # no breakdown rows
    assert sb.db.get("mock_topic_breakdowns", []) == []


def test_metadata_only_platform_review_allowed():
    """A platform_attempt mock accepts metadata (review_status, notes) without 409."""
    sb = SBStub(_seed())
    _, client = _client(sb)
    r = client.post(
        "/api/study/mocks/m3/review",
        json={"review_status": "reviewed", "notes": "Good attempt."},
    )
    assert r.status_code == 200
    platform_mock = next(m for m in sb.db["mock_tests"] if m["id"] == "m3")
    assert platform_mock["review_status"] == "reviewed"
    assert platform_mock["notes"] == "Good attempt."
    # no breakdowns written
    assert sb.db.get("mock_topic_breakdowns", []) == []


def test_manual_mock_review_with_breakdowns_persists_and_no_409():
    """A manual_log mock with topic_breakdowns still returns 200 and writes breakdowns."""
    sb = SBStub(_seed())
    _, client = _client(sb)
    r = client.post(
        "/api/study/mocks/m1/review",
        json={
            "review_status": "reviewed",
            "topic_breakdowns": [{"topic_id": "t1", "wrong_answers": 3}],
        },
    )
    assert r.status_code == 200
    assert len(sb.db["mock_topic_breakdowns"]) == 1


# ─── Empty body (FIX-2) ───────────────────────────────────────────────────────

def test_review_empty_body_rejected_422():
    sb = SBStub(_seed())
    _, client = _client(sb)
    r = client.post("/api/study/mocks/m1/review", json={})
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "mock_review_empty_payload"


# ─── model_fields_set-driven patch (BUG-A regression) ────────────────────────

def test_review_notes_only_does_not_mutate_review_status():
    """Omitting review_status must not overwrite the existing DB value (BUG-A)."""
    sb = SBStub(_seed())
    sb.db["mock_tests"][0]["review_status"] = "unreviewed"
    _, client = _client(sb)
    r = client.post("/api/study/mocks/m1/review", json={"notes": "Practice more."})
    assert r.status_code == 200
    mock = sb.db["mock_tests"][0]
    assert mock.get("review_status") == "unreviewed"
    assert mock["notes"] == "Practice more."


def test_review_notes_null_clears_existing_note():
    """Explicit null for notes must be persisted (clears the field)."""
    sb = SBStub(_seed())
    sb.db["mock_tests"][0]["notes"] = "Old note."
    _, client = _client(sb)
    r = client.post("/api/study/mocks/m1/review", json={"notes": None})
    assert r.status_code == 200
    assert sb.db["mock_tests"][0].get("notes") is None


def test_review_explicit_zero_wrong_answers_persists():
    """An explicit 0 in a numeric field must be written, not discarded."""
    sb = SBStub(_seed())
    _, client = _client(sb)
    r = client.post("/api/study/mocks/m1/review", json={"wrong_answers": 0})
    assert r.status_code == 200
    assert sb.db["mock_tests"][0]["wrong_answers"] == 0


# ─── Ownership lookup failure (FIX-3) ────────────────────────────────────────

def test_review_503_when_ownership_lookup_raises():
    """An exception during ownership SELECT must produce 503, not 500."""
    sb = SBStub(_seed())

    class _AlwaysRaiseQuery:
        def select(self, *a, **k): return self
        def update(self, *a, **k): return self
        def eq(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self): raise RuntimeError("Network timeout")

    class _LookupRaiseSB:
        def __init__(self, inner):
            self.db = inner.db
            self._inner = inner

        def table(self, name):
            return _AlwaysRaiseQuery() if name == "mock_tests" else self._inner.table(name)

        def rpc(self, *a, **k):
            return self._inner.rpc(*a, **k)

    _, client = _client(_LookupRaiseSB(sb))
    r = client.post("/api/study/mocks/m1/review", json={"review_status": "reviewed"})
    assert r.status_code == 503
    assert r.json()["detail"]["error"] == "mock_review_lookup_failed"


# ─── Scoped update failures (FIX-4 / TOCTOU hardening) ──────────────────────

def test_review_503_when_update_raises():
    """An exception during the scoped UPDATE must produce 503."""
    sb = SBStub(_seed())

    class _UpdateRaiseQuery:
        def __init__(self, inner):
            self._inner = inner
            self._will_raise = False

        def select(self, *a, **k): self._inner.select(*a, **k); return self
        def eq(self, k, v): self._inner.eq(k, v); return self
        def limit(self, n): self._inner.limit(n); return self
        def delete(self): return self._inner.delete()
        def update(self, patch): self._inner.update(patch); self._will_raise = True; return self

        def execute(self):
            if self._will_raise:
                raise RuntimeError("DB write failed")
            return self._inner.execute()

    class _UpdateRaiseSB:
        def __init__(self, inner):
            self.db = inner.db
            self._inner = inner

        def table(self, name):
            return (
                _UpdateRaiseQuery(self._inner.table(name))
                if name == "mock_tests"
                else self._inner.table(name)
            )

        def rpc(self, *a, **k):
            return self._inner.rpc(*a, **k)

    _, client = _client(_UpdateRaiseSB(sb))
    r = client.post("/api/study/mocks/m1/review", json={"review_status": "reviewed"})
    assert r.status_code == 503
    assert r.json()["detail"]["error"] == "mock_review_update_failed"
    assert sb.db.get("mock_topic_breakdowns", []) == []


def test_review_404_when_row_deleted_between_select_and_update():
    """Zero-row update where diagnostic also finds no row → 404."""
    sb = SBStub(_seed())
    call_counter = {"n": 0}

    class _DeleteBetweenQuery:
        def __init__(self, inner):
            self._inner = inner

        def select(self, *a, **k): self._inner.select(*a, **k); return self
        def eq(self, k, v): self._inner.eq(k, v); return self
        def limit(self, n): self._inner.limit(n); return self
        def delete(self): return self._inner.delete()
        def update(self, patch): self._inner.update(patch); return self

        def execute(self):
            call_counter["n"] += 1
            if call_counter["n"] == 1:
                return self._inner.execute()  # ownership SELECT: row found
            return _Exec([])  # scoped UPDATE + diagnostic SELECT both return empty

    class _DeleteBetweenSB:
        def __init__(self, inner):
            self.db = inner.db
            self._inner = inner

        def table(self, name):
            return (
                _DeleteBetweenQuery(self._inner.table(name))
                if name == "mock_tests"
                else self._inner.table(name)
            )

        def rpc(self, *a, **k):
            return self._inner.rpc(*a, **k)

    _, client = _client(_DeleteBetweenSB(sb))
    r = client.post("/api/study/mocks/m1/review", json={"review_status": "reviewed"})
    assert r.status_code == 404


def test_review_409_when_source_type_changes_mid_flight():
    """Zero-row update where diagnostic shows source_type changed → 409."""
    sb = SBStub(_seed())
    call_counter = {"n": 0}

    class _SourceChangedQuery:
        def __init__(self, inner):
            self._inner = inner

        def select(self, *a, **k): self._inner.select(*a, **k); return self
        def eq(self, k, v): self._inner.eq(k, v); return self
        def limit(self, n): self._inner.limit(n); return self
        def delete(self): return self._inner.delete()
        def update(self, patch): self._inner.update(patch); return self

        def execute(self):
            call_counter["n"] += 1
            if call_counter["n"] == 1:
                # Ownership SELECT: row has source_type=manual_log.
                return _Exec([{"id": "m1", "user_id": "u-1", "source_type": "manual_log"}])
            if call_counter["n"] == 2:
                # Scoped UPDATE returns 0 rows (source_type filter now mismatches).
                return _Exec([])
            # Diagnostic SELECT: row now shows platform_attempt.
            return _Exec([{"id": "m1", "user_id": "u-1", "source_type": "platform_attempt"}])

    class _SourceChangedSB:
        def __init__(self, inner):
            self.db = inner.db
            self._inner = inner

        def table(self, name):
            return (
                _SourceChangedQuery(self._inner.table(name))
                if name == "mock_tests"
                else self._inner.table(name)
            )

        def rpc(self, *a, **k):
            return self._inner.rpc(*a, **k)

    _, client = _client(_SourceChangedSB(sb))
    r = client.post("/api/study/mocks/m1/review", json={"review_status": "reviewed"})
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "mock_source_type_changed"


# ─── Platform path sentinel (FIX-5 / FIX-6) ─────────────────────────────────

def test_platform_attempt_forbidden_scalar_409_and_no_writes():
    """Forbidden scalar (total_questions) on platform mock → 409 + zero writes (sentinel)."""
    sb = SBStub(_seed())
    _, client = _client(sb)
    r = client.post(
        "/api/study/mocks/m3/review",
        json={"review_status": "reviewed", "total_questions": 100},
    )
    assert r.status_code == 409
    detail = r.json()["detail"]
    assert detail["error"] == "platform_attempt_authoritative_fields_rejected"
    assert "total_questions" in detail["fields"]
    # Sentinel: mock_tests row must be completely unmodified.
    platform_mock = next(m for m in sb.db["mock_tests"] if m["id"] == "m3")
    assert platform_mock.get("review_status") is None
    assert platform_mock.get("total_questions") is None
    assert sb.db.get("mock_topic_breakdowns", []) == []


# Phase 5: POST /api/study/mocks/{mock_id}/correction-tasks tests that
# previously pinned canonical.py's direct-to-study_tasks behavior have
# been removed. That handler was a pre-Phase-6 duplicate of
# app/api/study_os.py's service-backed flow, which writes to
# mock_correction_tasks (a staging table requiring an explicit apply
# step), not directly to study_tasks. Coverage of the surviving
# study_os.py implementation lives in tests/study_os/test_mocks.py
# (test_draft_correction_tasks_uses_error_patterns,
# test_apply_correction_task_creates_study_task_and_links, etc.).
