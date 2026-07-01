"""Unit tests for the EWP-2B language-evaluation worker (run_worker_pass).

Uses a hand-rolled fake Supabase client (no DB). The fake records every
``.rpc(name, params).execute()`` call and returns caller-configured ``.data``.
"""
from __future__ import annotations

import re

import pytest

pytest.importorskip("pydantic")

from app.study_os.writing_practice import evaluation_worker  # noqa: E402
from app.study_os.writing_practice.content_hash import (  # noqa: E402
    compute_content_hash,
)

_HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")

_ISSUE_KEYS = {
    "issue_type",
    "span_start_utf16",
    "span_end_utf16",
    "quoted_text",
    "original_text",
    "suggested_text",
    "explanation",
    "severity",
    "predecessor_issue_event_id",
}


class _Exec:
    def __init__(self, data):
        self._data = data

    def execute(self):
        return self

    @property
    def data(self):
        return self._data


class FakeSupabase:
    """Records (name, params) for every rpc call; returns queued .data by name."""

    def __init__(self, responses: dict | None = None):
        self._responses = responses or {}
        self.calls: list[tuple[str, dict]] = []

    def rpc(self, name, params):
        self.calls.append((name, params))
        return _Exec(self._responses.get(name))

    # test helpers -------------------------------------------------------
    def call_names(self):
        return [n for n, _ in self.calls]

    def params_for(self, name):
        for n, p in self.calls:
            if n == name:
                return p
        raise AssertionError(f"rpc {name} was not called")


def _claim(**overrides):
    answer_text = overrides.get("answer_text", "they is happy")
    base = {
        "job_id": "job-1",
        "claim_token": "tok-abc",
        "answer_text": answer_text,
        "content_hash": compute_content_hash(answer_text),
        "exercise_type": "sentence_construction",
        "is_current": True,
        "user_id": "user-1",
        "evaluation_id": "eval-1",
        "topic_id": "topic-1",
        "session_id": "sess-1",
        "microtopic_id": None,
        "exam_id": None,
        "active_prior_issues": [],
        "resolved_prior_lineages": [],
    }
    base.update(overrides)
    return base


def test_idle_when_no_claim():
    sb = FakeSupabase({"ewp_claim_evaluation_job": None})
    result = evaluation_worker.run_worker_pass(sb)
    assert result == {"processed": 0, "status": "idle"}
    assert sb.call_names() == ["ewp_claim_evaluation_job"]


def test_success_path_shadow(monkeypatch):
    monkeypatch.setenv("FF_WRITING_MASTERY_WRITES", "shadow")
    # A clean (no must_fix) but still-flagged answer: lowercase sentence start
    # yields a should_fix capitalization issue only, so a positive evidence key
    # is derived (a blocking must_fix answer would earn no evidence → None).
    sb = FakeSupabase({
        "ewp_claim_evaluation_job": _claim(answer_text="they are happy"),
        "ewp_complete_language_evaluation": {"ok": True},
    })
    result = evaluation_worker.run_worker_pass(sb)

    assert result["status"] == "succeeded"
    assert sb.call_names().count("ewp_complete_language_evaluation") == 1

    p = sb.params_for("ewp_complete_language_evaluation")
    assert isinstance(p["p_issues"], list) and p["p_issues"]
    for issue in p["p_issues"]:
        assert set(issue.keys()) == _ISSUE_KEYS
    assert p["p_mastery_flag"] == "shadow"
    assert _HEX64.match(p["p_mastery_idempotency_key"])


def test_rubric_path_sets_dimension_scores(monkeypatch):
    monkeypatch.setenv("FF_WRITING_MASTERY_WRITES", "shadow")
    sb = FakeSupabase({
        "ewp_claim_evaluation_job": _claim(exercise_type="paragraph_writing"),
        "ewp_complete_language_evaluation": {"ok": True},
    })
    result = evaluation_worker.run_worker_pass(sb)
    assert result["status"] == "succeeded"
    p = sb.params_for("ewp_complete_language_evaluation")
    assert p["p_dimension_scores"] is not None


def test_mastery_off(monkeypatch):
    monkeypatch.delenv("FF_WRITING_MASTERY_WRITES", raising=False)
    sb = FakeSupabase({
        "ewp_claim_evaluation_job": _claim(),
        "ewp_complete_language_evaluation": {"ok": True},
    })
    result = evaluation_worker.run_worker_pass(sb)
    assert result["status"] == "succeeded"
    p = sb.params_for("ewp_complete_language_evaluation")
    assert p["p_mastery_flag"] == "off"
    assert p["p_mastery_idempotency_key"] is None


def test_failure_path(monkeypatch):
    def _boom(*a, **k):
        raise RuntimeError("evaluator exploded")

    monkeypatch.setattr(evaluation_worker.lang, "evaluate_language", _boom)
    sb = FakeSupabase({
        "ewp_claim_evaluation_job": _claim(),
        "ewp_fail_evaluation_job": None,
    })
    result = evaluation_worker.run_worker_pass(sb)
    assert result["status"] == "failed"
    assert "ewp_fail_evaluation_job" in sb.call_names()
    p = sb.params_for("ewp_fail_evaluation_job")
    assert p["p_claim_token"] == "tok-abc"


def test_content_hash_mismatch_rejects_corrupt_not_recoverable():
    # A hash mismatch is CORRUPTION: it must fail closed through the DISTINCT
    # ewp_reject_corrupt_version path (never scored, never the recoverable
    # ewp_fail_evaluation_job retry path).
    sb = FakeSupabase({
        "ewp_claim_evaluation_job": _claim(content_hash="0" * 64),
        "ewp_reject_corrupt_version": {"status": "rejected_corrupt"},
    })
    result = evaluation_worker.run_worker_pass(sb)
    assert result["status"] == "rejected_corrupt"
    assert "ewp_complete_language_evaluation" not in sb.call_names()
    assert "ewp_fail_evaluation_job" not in sb.call_names()
    assert "ewp_reject_corrupt_version" in sb.call_names()
    p = sb.params_for("ewp_reject_corrupt_version")
    assert p["p_claim_token"] == "tok-abc"
    assert p["p_error"] == "content_hash_mismatch"
