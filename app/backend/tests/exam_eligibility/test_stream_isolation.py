"""Regression: the exam-wide baseline evaluator must ignore stream-scoped rules.

After migration 245 a verified stream-specific row can coexist with a common
row for the same (scope, rule_type). Until target-stream evaluation lands, the
exam-wide evaluator must apply ONLY common (stream_id IS NULL) rules, or a
stream rule could knock out every aspirant (PR #967 checkpost P0-1).
"""
from __future__ import annotations

from app.exam_eligibility.evaluator import (
    _load_rules_by_exam,
    invalidate_eligibility_rules_cache,
)
from tests.persona_questions._stub import SBStub


EXAM = "11111111-1111-1111-1111-111111111111"
STREAM = "22222222-2222-2222-2222-222222222222"


def _sb() -> SBStub:
    return SBStub(
        {
            "exam_eligibility_rules": [
                # common rule — must be used
                {
                    "exam_id": EXAM, "stream_id": None, "scope": "all",
                    "rule_type": "age_max", "value_num": 40, "value_text": None,
                    "is_knockout": True, "source_url": None, "reviewer_status": "verified",
                },
                # stream-scoped rule — must be EXCLUDED from exam-wide evaluation
                {
                    "exam_id": EXAM, "stream_id": STREAM, "scope": "all",
                    "rule_type": "age_max", "value_num": 1, "value_text": None,
                    "is_knockout": True, "source_url": None, "reviewer_status": "verified",
                },
            ]
        }
    )


def test_load_rules_excludes_stream_scoped_rows():
    invalidate_eligibility_rules_cache()
    loaded = _load_rules_by_exam(_sb(), [EXAM])
    rules = loaded.get(EXAM, [])
    assert len(rules) == 1, "stream-scoped rule leaked into exam-wide rule set"
    assert rules[0]["stream_id"] is None
    assert rules[0]["value_num"] == 40  # the common rule, not the stream's age_max=1
    invalidate_eligibility_rules_cache()
