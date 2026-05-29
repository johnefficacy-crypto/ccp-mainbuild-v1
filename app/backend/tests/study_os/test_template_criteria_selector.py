"""PR-fix-6 Fix 3 — runtime ``criteria`` selector.

``select_questions_for_template`` must resolve a section's ``criteria`` selector
to concrete published questions, honouring bank filters and the optional
``difficulty_mix`` distribution. Before this fix only ``fixed`` selectors were
handled, so every criteria-authored template fell through to PR1's seed.
"""
from __future__ import annotations

import uuid

from app.study_os import mock_engine as svc
from app.study_os.mock_engine import _criteria_difficulty_targets
from tests.persona_questions._stub import SBStub


def _q(difficulty: str, *, exam_family: str = "TEST", topic_id: str | None = None) -> dict:
    qid = str(uuid.uuid4())
    opts = [
        {"id": f"opt-{qid}-{i}", "question_id": qid, "option_text": f"Opt {i}", "option_index": i, "is_correct": i == 2}
        for i in range(1, 5)
    ]
    return {
        "id": qid,
        "exam_family": exam_family,
        "topic_id": topic_id,
        "question_text": f"Q {qid[:8]}",
        "question_type": "mcq",
        "difficulty": difficulty,
        "correct_option_id": opts[1]["id"],
        "reviewer_status": "published",
        "options": opts,
    }


def _db_with_section(selector: dict, question_count: int, questions: list[dict]) -> tuple[SBStub, str]:
    template_id = "tmpl-criteria-1"
    section = {
        "id": "sec-1",
        "template_id": template_id,
        "section_index": 0,
        "name": "Section A",
        "question_count": question_count,
        "selector": selector,
    }
    db = {
        "mock_template_sections": [section],
        "mock_question_bank": [dict(q) for q in questions],
        "mock_question_options": [o for q in questions for o in q["options"]],
    }
    return SBStub(db), template_id


def test_difficulty_targets_sum_to_total():
    targets = _criteria_difficulty_targets({"easy": 0.5, "medium": 0.3, "hard": 0.2}, 10)
    assert sum(targets.values()) == 10
    assert targets == {"easy": 5, "medium": 3, "hard": 2}


def test_difficulty_targets_largest_remainder():
    # 0.333.. each over 10 → floors {3,3,3}=9, remainder 1 to the largest fraction.
    targets = _criteria_difficulty_targets({"easy": 1 / 3, "medium": 1 / 3, "hard": 1 / 3}, 10)
    assert sum(targets.values()) == 10


def test_criteria_selects_by_difficulty_mix():
    questions = (
        [_q("easy") for _ in range(6)]
        + [_q("medium") for _ in range(4)]
        + [_q("hard") for _ in range(3)]
    )
    sb, template_id = _db_with_section(
        {"mode": "criteria", "filters": {"difficulty_mix": {"easy": 0.5, "medium": 0.3, "hard": 0.2}}},
        10,
        questions,
    )
    selected = svc.select_questions_for_template(sb, template_id, "user-1")
    assert len(selected) == 10
    by_diff: dict[str, int] = {}
    for q in selected:
        by_diff[q["difficulty"]] = by_diff.get(q["difficulty"], 0) + 1
    assert by_diff == {"easy": 5, "medium": 3, "hard": 2}
    # options are attached so the attempt can render answer choices
    assert all(q["options"] for q in selected)


def test_criteria_backfills_short_bucket():
    # mix wants all-easy but only 4 easy exist; the rest backfilled from pool.
    questions = [_q("easy") for _ in range(4)] + [_q("medium") for _ in range(8)]
    sb, template_id = _db_with_section(
        {"mode": "criteria", "filters": {"difficulty_mix": {"easy": 1.0}}},
        10,
        questions,
    )
    selected = svc.select_questions_for_template(sb, template_id, "user-1")
    assert len(selected) == 10  # 4 easy + 6 backfilled mediums


def test_criteria_without_mix_takes_question_count():
    questions = [_q("easy") for _ in range(20)]
    sb, template_id = _db_with_section(
        {"mode": "criteria", "filters": {}},
        7,
        questions,
    )
    selected = svc.select_questions_for_template(sb, template_id, "user-1")
    assert len(selected) == 7


def test_criteria_filters_exam_family():
    questions = [_q("easy", exam_family="IBPS") for _ in range(5)] + [_q("easy", exam_family="SSC") for _ in range(5)]
    sb, template_id = _db_with_section(
        {"mode": "criteria", "filters": {"exam_family": "IBPS"}},
        5,
        questions,
    )
    selected = svc.select_questions_for_template(sb, template_id, "user-1")
    assert len(selected) == 5
    assert all(q["exam_family"] == "IBPS" for q in selected)


def test_criteria_excludes_unpublished():
    questions = [_q("easy") for _ in range(3)]
    questions.append({**_q("easy"), "reviewer_status": "draft"})
    sb, template_id = _db_with_section(
        {"mode": "criteria", "filters": {}},
        10,
        questions,
    )
    selected = svc.select_questions_for_template(sb, template_id, "user-1")
    # only the 3 published questions are eligible; the draft is excluded
    assert len(selected) == 3


def test_start_attempt_uses_criteria_template():
    """End-to-end: a criteria-only template no longer needs the PR1 seed fallback."""
    questions = [_q("easy") for _ in range(5)]
    template = {
        "id": "tmpl-criteria-1",
        "slug": "criteria-mock",
        "name": "Criteria Mock",
        "exam_family": "TEST",
        "total_questions": 3,
        "duration_sec": 300,
        "negative_marking": True,
        "marks_per_correct": 1.0,
        "marks_per_wrong": 0.25,
        "config": {},  # no legacy question_ids — must come from the selector
        "status": "active",
    }
    section = {
        "id": "sec-1",
        "template_id": template["id"],
        "section_index": 0,
        "name": "Section A",
        "question_count": 3,
        "selector": {"mode": "criteria", "filters": {}},
    }
    sb = SBStub({
        "mock_templates": [template],
        "mock_template_sections": [section],
        "mock_question_bank": [dict(q) for q in questions],
        "mock_question_options": [o for q in questions for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
    })
    result = svc.start_attempt(sb, "user-1", "criteria-mock")
    assert len(result["questions"]) == 3
