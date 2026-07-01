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
        "ewp_complete_mastery_outbox": None,
    })
    result = mastery_outbox_worker.run_outbox_pass(sb)
    assert result["status"] == "done"

    p = sb.params_for("ewp_complete_mastery_outbox")
    assert p["p_claim_token"] == "outbox-tok-1"
    evidence, shadow = p["p_evidence"], p["p_shadow"]
    assert isinstance(evidence, dict) and isinstance(shadow, dict)
    assert evidence["evidence_key"] == shadow["evidence_key"]
    assert _HEX64.match(evidence["evidence_key"])


def test_noop_blocking_answer():
    sb = FakeSupabase({
        "ewp_claim_mastery_outbox": _terminal(has_unresolved_must_fix=True),
        "ewp_complete_mastery_outbox": None,
    })
    result = mastery_outbox_worker.run_outbox_pass(sb)
    assert result["status"] == "done_noop"
    p = sb.params_for("ewp_complete_mastery_outbox")
    assert p["p_claim_token"] == "outbox-tok-1"
    assert p["p_evidence"] is None


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
