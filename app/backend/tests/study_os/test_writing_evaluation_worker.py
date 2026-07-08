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
        "unit_version_id": "ver-1",
        "evaluation_revision": 1,
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


def test_worker_threads_prompt_and_source_text(monkeypatch):
    # EWP-SP1: the worker must pass the claim's prompt_text/source_text into the
    # evaluator so deterministic source-comparison can run.
    captured = {}

    def _spy(answer_text, **kwargs):
        captured.update(kwargs)
        captured["answer_text"] = answer_text
        return evaluation_worker.lang.LanguageResult(issues=[])

    monkeypatch.setattr(evaluation_worker.lang, "evaluate_language", _spy)
    sb = FakeSupabase({
        "ewp_claim_evaluation_job": _claim(
            exercise_type="sentence_correction",
            prompt_text="Correct the sentence.",
            source_text="He go home.",
        ),
        "ewp_complete_language_evaluation": {"ok": True},
    })
    result = evaluation_worker.run_worker_pass(sb)
    assert result["status"] == "succeeded"
    assert captured["prompt_text"] == "Correct the sentence."
    assert captured["source_text"] == "He go home."


def test_source_uncertain_fails_closed_no_mastery(monkeypatch):
    # A source-dependent submission that can't be deterministically decided routes
    # to needs_human_review with NO positive mastery evidence, even under shadow.
    monkeypatch.setenv("FF_WRITING_MASTERY_WRITES", "shadow")
    sb = FakeSupabase({
        "ewp_claim_evaluation_job": _claim(
            answer_text="He goes to school every day.",
            exercise_type="sentence_correction",
            source_text="He go to school every day.",
        ),
        "ewp_complete_language_evaluation": {"ok": True},
    })
    result = evaluation_worker.run_worker_pass(sb)
    assert result["status"] == "succeeded"
    p = sb.params_for("ewp_complete_language_evaluation")
    assert p["p_needs_human_review"] is True
    assert p["p_mastery_idempotency_key"] is None
    assert p["p_language_result"]["source_comparison"] == "source_comparison_uncertain"


def test_missing_source_fails_closed_no_mastery(monkeypatch):
    monkeypatch.setenv("FF_WRITING_MASTERY_WRITES", "shadow")
    sb = FakeSupabase({
        "ewp_claim_evaluation_job": _claim(
            answer_text="He goes home.",
            exercise_type="sentence_correction",
            source_text=None,
        ),
        "ewp_complete_language_evaluation": {"ok": True},
    })
    evaluation_worker.run_worker_pass(sb)
    p = sb.params_for("ewp_complete_language_evaluation")
    assert p["p_needs_human_review"] is True
    assert p["p_mastery_idempotency_key"] is None


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

def test_worker_runs_semantic_shadow_probe_without_affecting_primary_rpc(monkeypatch):
    monkeypatch.setenv("FF_WRITING_LLM_EVAL", "shadow")
    monkeypatch.delenv("FF_WRITING_MASTERY_WRITES", raising=False)

    calls = {}

    class _ShadowEvaluator:
        def evaluate(self, answer_text, **kwargs):
            calls["answer_text"] = answer_text
            calls["kwargs"] = kwargs
            return evaluation_worker.lang.LanguageResult(
                issues=[
                    evaluation_worker.lang.LanguageIssueOut(
                        issue_type="subject_verb_agreement",
                        span_start_utf16=0,
                        span_end_utf16=4,
                        quoted_text="They",
                        explanation="Shadow-only semantic finding.",
                        severity="must_fix",
                    )
                ],
                evaluator_version="lang-llm-shadow-test",
                source_comparison="meaning_not_preserved",
                needs_human_review=True,
            )

    monkeypatch.setattr(
        evaluation_worker.lang,
        "get_semantic_shadow_evaluator",
        lambda: _ShadowEvaluator(),
    )

    sb = FakeSupabase({
        "ewp_claim_evaluation_job": _claim(
            answer_text="They are happy.",
            exercise_type="sentence_correction",
            prompt_text="Correct the sentence.",
            source_text="They are happy.",
        ),
        "ewp_complete_language_evaluation": {"ok": True},
    })

    result = evaluation_worker.run_worker_pass(sb)

    assert result["status"] == "succeeded"
    assert calls["answer_text"] == "They are happy."
    assert calls["kwargs"]["prompt_text"] == "Correct the sentence."
    assert calls["kwargs"]["source_text"] == "They are happy."

    p = sb.params_for("ewp_complete_language_evaluation")
    assert p["p_evaluator_version"] != "lang-llm-shadow-test"
    assert p["p_language_result"]["evaluator_version"] != "lang-llm-shadow-test"
    assert p["p_language_result"]["source_comparison"] == "source_unchanged"
    assert all(i["explanation"] != "Shadow-only semantic finding." for i in p["p_issues"])


def test_worker_ignores_semantic_shadow_failure(monkeypatch):
    def _job():
        return _claim(
            answer_text="He goes to school.",
            exercise_type="sentence_correction",
            prompt_text="Correct the sentence.",
            source_text="He goes to school.",
        )

    monkeypatch.delenv("FF_WRITING_LLM_EVAL", raising=False)
    baseline_sb = FakeSupabase({
        "ewp_claim_evaluation_job": _job(),
        "ewp_complete_language_evaluation": {"ok": True},
    })

    baseline_result = evaluation_worker.run_worker_pass(baseline_sb)
    assert baseline_result["status"] == "succeeded"
    baseline_p = baseline_sb.params_for("ewp_complete_language_evaluation")

    monkeypatch.setenv("FF_WRITING_LLM_EVAL", "shadow")

    class _FailingShadowEvaluator:
        def evaluate(self, answer_text, **kwargs):
            raise RuntimeError("shadow provider unavailable")

    monkeypatch.setattr(
        evaluation_worker.lang,
        "get_semantic_shadow_evaluator",
        lambda: _FailingShadowEvaluator(),
    )

    sb = FakeSupabase({
        "ewp_claim_evaluation_job": _job(),
        "ewp_complete_language_evaluation": {"ok": True},
    })

    result = evaluation_worker.run_worker_pass(sb)

    assert result["status"] == "succeeded"
    p = sb.params_for("ewp_complete_language_evaluation")
    assert p["p_evaluator_version"] == baseline_p["p_evaluator_version"]
    assert p["p_language_result"] == baseline_p["p_language_result"]
    assert p["p_issues"] == baseline_p["p_issues"]
    assert p["p_needs_human_review"] == baseline_p["p_needs_human_review"]
    assert p.get("p_mastery_signals") == baseline_p.get("p_mastery_signals")
    assert p.get("p_mastery_idempotency_key") == baseline_p.get("p_mastery_idempotency_key")

def test_worker_records_semantic_shadow_telemetry_without_raw_payload(monkeypatch):
    monkeypatch.setenv("FF_WRITING_LLM_EVAL", "shadow")

    class _ShadowEvaluator:
        def evaluate(self, answer_text, **kwargs):
            return evaluation_worker.lang.LanguageResult(
                issues=[
                    evaluation_worker.lang.LanguageIssueOut(
                        issue_type="subject_verb_agreement",
                        span_start_utf16=0,
                        span_end_utf16=15,
                        quoted_text="They are happy.",
                        explanation="Raw semantic shadow snippet must not persist.",
                        severity="must_fix",
                    )
                ],
                evaluator_version="lang-llm-shadow-test",
                source_comparison="source_unchanged",
                needs_human_review=False,
            )

    monkeypatch.setattr(
        evaluation_worker.lang,
        "get_semantic_shadow_evaluator",
        lambda: _ShadowEvaluator(),
    )

    sb = FakeSupabase({
        "ewp_claim_evaluation_job": _claim(
            evaluation_id="eval-1",
            unit_version_id="ver-1",
            evaluation_revision=2,
            answer_text="They are happy.",
            exercise_type="sentence_correction",
            prompt_text="Correct the sentence.",
            source_text="They are happy.",
        ),
        "ewp_record_language_evaluator_run": {"ok": True, "id": "run-1"},
        "ewp_complete_language_evaluation": {"ok": True},
    })

    result = evaluation_worker.run_worker_pass(sb)

    assert result["status"] == "succeeded"
    assert "ewp_record_language_evaluator_run" in sb.call_names()

    telemetry = sb.params_for("ewp_record_language_evaluator_run")
    assert telemetry["p_evaluation_id"] == "eval-1"
    assert telemetry["p_unit_version_id"] == "ver-1"
    assert telemetry["p_evaluation_revision"] == 2
    assert _HEX64.match(telemetry["p_input_hash"])
    assert telemetry["p_deterministic_evaluator_version"] == evaluation_worker.lang.LANGUAGE_EVALUATOR_VERSION
    assert telemetry["p_deterministic_source_comparison"] == "source_unchanged"
    completion = sb.params_for("ewp_complete_language_evaluation")
    assert telemetry["p_deterministic_needs_human_review"] == completion["p_needs_human_review"]
    assert telemetry["p_deterministic_issue_count"] == 0
    assert telemetry["p_adapter_version"] == "lang-llm-shadow-test"
    assert telemetry["p_status"] == "succeeded"
    assert telemetry["p_semantic_source_comparison"] == "source_unchanged"
    assert telemetry["p_semantic_needs_human_review"] is False
    assert telemetry["p_semantic_issue_count"] == 1
    assert telemetry["p_result_json"]["issue_count"] == 1

    serialized = repr(telemetry)
    assert "They are happy." not in serialized
    assert "Correct the sentence." not in serialized
    assert "Raw semantic shadow snippet must not persist." not in serialized
