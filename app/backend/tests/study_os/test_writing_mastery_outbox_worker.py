"""Unit tests for the EWP-2B mastery-outbox drain (run_outbox_pass).

Uses the same fake-rpc Supabase client (no DB): records every rpc call and
returns caller-queued ``.data`` by rpc name.
"""
from __future__ import annotations

import re

import pytest

pytest.importorskip("pydantic")

from app.study_os.writing_practice import mastery_outbox_worker  # noqa: E402

_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")


class _Exec:
    def __init__(self, data):
        self._data = data

    def execute(self):
        return self

    @property
    def data(self):
        return self._data


class FakeSupabase:
    def __init__(self, responses: dict | None = None):
        self._responses = responses or {}
        self.calls: list[tuple[str, dict]] = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        return _Exec(self._responses.get(name))

    def call_names(self):
        return [n for n, _ in self.calls]

    def params_for(self, name):
        for n, p in self.calls:
            if n == name:
                return p
        raise AssertionError(f"rpc {name} was not called")


def _terminal(**overrides):
    base = {
        "id": "outbox-1",
        "claim_token": "outbox-tok-1",
        "exercise_type": "sentence_construction",
        "overall_status": "completed",
        "user_id": "user-1",
        "evaluation_id": "eval-1",
        "topic_id": "topic-1",
        "microtopic_id": None,
        "exam_id": None,
        "source_entity_id": "sess-1",
        "has_unresolved_must_fix": False,
        "resolved_issue_count": 0,
        "mastery_flag_state": "shadow",
    }
    base.update(overrides)
    return base


def test_idle_when_no_claim():
    sb = FakeSupabase({"ewp_claim_mastery_outbox": None})
    result = mastery_outbox_worker.run_outbox_pass(sb)
    assert result == {"processed": 0, "status": "idle"}


def test_done_writes_evidence_and_shadow():
    sb = FakeSupabase({
        "ewp_claim_mastery_outbox": _terminal(),
        "ewp_complete_mastery_outbox_batch": None,
    })
    result = mastery_outbox_worker.run_outbox_pass(sb)
    assert result["status"] == "done" and result["rows"] == 1

    p = sb.params_for("ewp_complete_mastery_outbox_batch")
    assert p["p_claim_token"] == "outbox-tok-1"
    pairs = p["p_pairs"]
    assert isinstance(pairs, list) and len(pairs) == 1
    evidence, shadow = pairs[0]["evidence"], pairs[0]["shadow"]
    assert isinstance(evidence, dict) and isinstance(shadow, dict)
    assert evidence["evidence_key"] == shadow["evidence_key"]
    assert _HEX64.match(evidence["evidence_key"])
    assert evidence["issue_projection_id"] is None  # unit-level row


def test_done_emits_per_issue_projection_rows():
    # A must_fix answer earns NO unit-level positive evidence, but the two
    # current-state automatic projections each earn a projection-linked row.
    projs = [
        {"issue_projection_id": "proj-a", "microtopic_id": "mt-a", "evidence_tier": "recognition"},
        {"issue_projection_id": "proj-b", "microtopic_id": None, "evidence_tier": "correction"},
    ]
    sb = FakeSupabase({
        "ewp_claim_mastery_outbox": _terminal(has_unresolved_must_fix=True, issue_projections=projs),
        "ewp_complete_mastery_outbox_batch": None,
    })
    result = mastery_outbox_worker.run_outbox_pass(sb)
    assert result["status"] == "done" and result["rows"] == 2
    pairs = sb.params_for("ewp_complete_mastery_outbox_batch")["p_pairs"]
    linked = {pr["evidence"]["issue_projection_id"]: pr["evidence"] for pr in pairs}
    assert set(linked) == {"proj-a", "proj-b"}
    assert linked["proj-a"]["evidence_tier"] == "recognition"
    assert linked["proj-b"]["evidence_tier"] == "correction"
    # distinct evidence keys per projection.
    assert linked["proj-a"]["evidence_key"] != linked["proj-b"]["evidence_key"]


def test_noop_blocking_answer():
    sb = FakeSupabase({
        "ewp_claim_mastery_outbox": _terminal(has_unresolved_must_fix=True),
        "ewp_complete_mastery_outbox_batch": None,
    })
    result = mastery_outbox_worker.run_outbox_pass(sb)
    assert result["status"] == "done_noop"
    p = sb.params_for("ewp_complete_mastery_outbox_batch")
    assert p["p_claim_token"] == "outbox-tok-1"
    assert p["p_pairs"] is None


def test_review_correction_pass_applies_retract():
    claim = {
        "id": "outbox-c1", "claim_token": "c-tok", "evidence_op": "retract",
        "user_id": "user-1", "evaluation_id": "eval-1", "topic_id": "topic-1",
        "microtopic_id": "mt-a", "exam_id": None, "source_type": "sentence_drill",
        "source_entity_id": "sess-1", "evidence_tier": "recognition",
        "issue_projection_id": "proj-a", "review_event_id": "rev-1",
        "supersedes_evidence_key": "d" * 64, "mastery_flag_state": "shadow",
    }
    sb = FakeSupabase({
        "ewp_claim_review_correction_outbox": claim,
        "ewp_complete_review_correction": None,
    })
    result = mastery_outbox_worker.run_review_correction_pass(sb)
    assert result["status"] == "done" and result["evidence_op"] == "retract"
    p = sb.params_for("ewp_complete_review_correction")
    ev = p["p_evidence"]
    assert ev["evidence_op"] == "retract"
    assert ev["review_event_id"] == "rev-1"
    assert ev["supersedes_evidence_key"] == "d" * 64
    assert ev["issue_projection_id"] == "proj-a"
    assert _HEX64.match(ev["evidence_key"])
    assert ev["evidence_key"] == p["p_shadow"]["evidence_key"]


def test_review_correction_pass_idle():
    sb = FakeSupabase({"ewp_claim_review_correction_outbox": None})
    assert mastery_outbox_worker.run_review_correction_pass(sb) == {"processed": 0, "status": "idle"}


def test_failure_path(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("deriver exploded")

    monkeypatch.setattr(mastery_outbox_worker.ev, "derive_unit_evidence", _boom)
    sb = FakeSupabase({
        "ewp_claim_mastery_outbox": _terminal(),
        "ewp_fail_mastery_outbox": None,
    })
    result = mastery_outbox_worker.run_outbox_pass(sb)
    assert result["status"] == "failed"
    assert "ewp_fail_mastery_outbox" in sb.call_names()
    p = sb.params_for("ewp_fail_mastery_outbox")
    assert p["p_claim_token"] == "outbox-tok-1"
