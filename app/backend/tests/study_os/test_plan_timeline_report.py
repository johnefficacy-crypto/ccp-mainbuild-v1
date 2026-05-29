"""Contract + PR5-flag behaviour for GET /api/study/reports/plan-timeline.

The endpoint unions rule-based planner audit (``study_adaptation_events``)
with mastery-shift events (``user_topic_mastery_audit``). Mastery deltas must
only surface when the PR5 write-back flag (``FF_MOCK_MASTERY_WRITES``) is
``live``; in ``off``/``shadow`` every event carries ``mastery_delta_db = None``.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import study_os as study_os_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub

RECENT = "2026-05-20T10:00:00+00:00"
RECENT_2 = "2026-05-21T10:00:00+00:00"
OLD = "2020-01-01T00:00:00+00:00"

_REQUIRED_KEYS = {"id", "at", "kind", "reason_code", "reason_human", "trigger", "mastery_delta_db"}
_VALID_KINDS = {"topic_added", "priority_shift", "topic_removed", "phase_change"}


def _build_app(sb: SBStub, user_id: str = "u-1"):
    app = FastAPI()
    app.include_router(study_os_api.router, prefix="/api")
    study_os_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id, "role": "user"}
    return app


def _adaptation(event_type: str, **over) -> dict:
    row = {
        "id": over.pop("id", f"ev-{event_type}"),
        "user_id": "u-1",
        "event_type": event_type,
        "trigger_source": over.pop("trigger_source", "planner_v1"),
        "trigger_payload": over.pop("trigger_payload", {}),
        "change_summary": over.pop("change_summary", {}),
        "created_at": over.pop("created_at", RECENT),
    }
    row.update(over)
    return row


def _mastery(**over) -> dict:
    row = {
        "id": over.pop("id", "ma-1"),
        "user_id": "u-1",
        "topic_id": over.pop("topic_id", "topic-9"),
        "attempt_id": over.pop("attempt_id", "attempt-7"),
        "before_mastery_db": over.pop("before_mastery_db", 40.0),
        "after_mastery_db": over.pop("after_mastery_db", 52.0),
        "delta_applied_db": over.pop("delta_applied_db", 12.0),
        "reason": "mock_submit",
        "at": over.pop("at", RECENT),
    }
    row.update(over)
    return row


def test_returns_events_envelope_when_empty():
    client = TestClient(_build_app(SBStub({})))
    r = client.get("/api/study/reports/plan-timeline")
    assert r.status_code == 200
    assert r.json() == {"events": []}


def test_adaptation_events_map_to_canonical_shape():
    sb = SBStub({"study_adaptation_events": [_adaptation("manual_regeneration")]})
    client = TestClient(_build_app(sb))
    body = client.get("/api/study/reports/plan-timeline").json()
    assert len(body["events"]) == 1
    ev = body["events"][0]
    assert _REQUIRED_KEYS.issubset(ev.keys())
    assert ev["kind"] in _VALID_KINDS
    assert ev["reason_code"] == "manual_regeneration"
    assert ev["reason_human"] == "Plan regenerated"
    assert ev["trigger"]["type"] == "manual"
    # No PR5 live writes → delta must be null.
    assert ev["mastery_delta_db"] is None


def test_kind_and_trigger_derivation():
    sb = SBStub(
        {
            "study_adaptation_events": [
                _adaptation("deadline_changed", id="e-phase", created_at=RECENT_2),
                _adaptation(
                    "mock_logged",
                    id="e-mock",
                    trigger_payload={"attempt_id": "attempt-3"},
                    created_at=RECENT,
                ),
                _adaptation(
                    "weekly_review",
                    id="e-sched",
                    created_at=OLD,  # filtered out by 90d window
                ),
            ]
        }
    )
    client = TestClient(_build_app(sb))
    body = client.get("/api/study/reports/plan-timeline?days=90").json()
    by_id = {e["id"]: e for e in body["events"]}
    # Old event excluded by the rolling window.
    assert "e-sched" not in by_id
    assert by_id["e-phase"]["kind"] == "phase_change"
    mock_ev = by_id["e-mock"]
    assert mock_ev["trigger"] == {"type": "mock_attempt", "attempt_id": "attempt-3"}
    # Newest first.
    assert body["events"][0]["id"] == "e-phase"


def test_admin_trigger_carries_actor():
    sb = SBStub(
        {
            "study_adaptation_events": [
                _adaptation(
                    "exam_update",
                    trigger_source="admin",
                    trigger_payload={"actor_id": "admin-42"},
                )
            ]
        }
    )
    client = TestClient(_build_app(sb))
    ev = client.get("/api/study/reports/plan-timeline").json()["events"][0]
    assert ev["trigger"] == {"type": "manual", "actor_id": "admin-42"}


def test_flag_off_suppresses_mastery_audit(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "off")
    sb = SBStub(
        {
            "study_adaptation_events": [_adaptation("manual_regeneration")],
            "user_topic_mastery_audit": [_mastery()],
        }
    )
    client = TestClient(_build_app(sb))
    events = client.get("/api/study/reports/plan-timeline").json()["events"]
    # Mastery audit rows are not surfaced and every event's delta is null.
    assert all(e["mastery_delta_db"] is None for e in events)
    assert all(e["reason_code"] != "mastery_shift" for e in events)


def test_flag_shadow_suppresses_mastery_audit(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "shadow")
    sb = SBStub({"user_topic_mastery_audit": [_mastery()]})
    client = TestClient(_build_app(sb))
    events = client.get("/api/study/reports/plan-timeline").json()["events"]
    assert events == []


def test_flag_live_includes_mastery_delta(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
    sb = SBStub(
        {
            "study_adaptation_events": [_adaptation("manual_regeneration", created_at=OLD)],
            "user_topic_mastery_audit": [_mastery()],
        }
    )
    client = TestClient(_build_app(sb))
    events = client.get("/api/study/reports/plan-timeline").json()["events"]
    mastery_events = [e for e in events if e["reason_code"] == "mastery_shift"]
    assert len(mastery_events) == 1
    ev = mastery_events[0]
    assert ev["trigger"] == {"type": "mock_attempt", "attempt_id": "attempt-7"}
    assert ev["mastery_delta_db"] == {
        "topic_id": "topic-9",
        "before": 40.0,
        "after": 52.0,
        "delta": 12.0,
    }


def test_flag_live_derives_missing_delta(monkeypatch):
    monkeypatch.setenv("FF_MOCK_MASTERY_WRITES", "live")
    sb = SBStub(
        {
            "user_topic_mastery_audit": [
                _mastery(delta_applied_db=None, before_mastery_db=30.0, after_mastery_db=45.0)
            ]
        }
    )
    client = TestClient(_build_app(sb))
    ev = client.get("/api/study/reports/plan-timeline").json()["events"][0]
    assert ev["mastery_delta_db"]["delta"] == 15.0
