"""Exam-WIDE eligibility must ignore stream-scoped rules.

Migration 248 added stream-scoped rules; migration 249 activates stream-aware
evaluation. The loader now returns both common and stream rows, but the
exam-wide verdict must still use ONLY common (stream_id NULL) rules — a stream
rule may never knock out every aspirant. Stream rules apply only to their own
stream via `_rules_for_stream` (PR #967 checkpost P0, carried into the wiring).
"""
from __future__ import annotations

from app.exam_eligibility.evaluator import (
    _load_rules_by_exam,
    _rules_for_stream,
    invalidate_eligibility_rules_cache,
)
from tests.persona_questions._stub import SBStub


EXAM = "11111111-1111-1111-1111-111111111111"
STREAM = "22222222-2222-2222-2222-222222222222"


def _rows() -> list[dict]:
    return [
        {"exam_id": EXAM, "stream_id": None, "scope": "all", "rule_type": "age_max",
         "value_num": 40, "value_text": None, "is_knockout": True,
         "source_url": None, "reviewer_status": "verified"},
        {"exam_id": EXAM, "stream_id": STREAM, "scope": "all", "rule_type": "age_max",
         "value_num": 1, "value_text": None, "is_knockout": True,
         "source_url": None, "reviewer_status": "verified"},
    ]


def test_loader_returns_both_common_and_stream_rows():
    invalidate_eligibility_rules_cache()
    loaded = _load_rules_by_exam(SBStub({"exam_eligibility_rules": _rows()}), [EXAM])
    assert len(loaded.get(EXAM, [])) == 2
    invalidate_eligibility_rules_cache()


def test_exam_wide_selection_uses_only_common_rules():
    # _rules_for_stream(., None) is what the exam-wide verdict uses.
    common = _rules_for_stream(_rows(), None)
    assert len(common) == 1
    assert common[0]["stream_id"] is None
    assert common[0]["value_num"] == 40  # not the stream's age_max=1


def test_stream_selection_overrides_common_for_that_stream():
    merged = _rules_for_stream(_rows(), STREAM)
    # The stream's age_max overrides the common one for that stream only.
    age_max = [r for r in merged if r["rule_type"] == "age_max"]
    assert len(age_max) == 1
    assert age_max[0]["value_num"] == 1
    assert age_max[0]["stream_id"] == STREAM
