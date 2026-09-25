"""REG-CORPUS-02 P4 — structured explanations + common_trap for AUTHORED rows in review.

Authored bank rows carry no ``pyq_question_id``; since migration 310 their
structured explanation lives in the same ``pyq_question_explanations`` table,
keyed by ``mock_question_id``. The review response must surface it under the same
``pyq_explanation`` sibling, through the same verified-only gate and DTO, with
option rationales resolved against the frozen options by bank option id.
"""
from __future__ import annotations

import uuid

import pytest

from app.study_os import mock_engine as svc
from tests.study_os.test_mock_engine import _make_template
from tests.persona_questions._stub import SBStub

PYQ_QID = "pyq-question-1"


def _seeded(explanations: list[dict], *, trap: str | None = "Motion = people; Transport = materials."):
    template, questions = _make_template("authored-expl-1")
    questions[0]["pyq_question_id"] = PYQ_QID  # a PYQ control row
    authored = questions[1]
    authored["pyq_question_id"] = None
    authored["source_kind"] = "authored"
    authored["common_trap"] = trap
    db = {
        "mock_templates": [template],
        "mock_question_bank": questions,
        "mock_question_options": [o for q in questions for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
        "mock_tests": [],
        "pyq_question_explanations": explanations,
        "pyq_options": [],
        "pyq_mock_question_projections": [
            {"mock_question_id": questions[0]["id"], "sync_status": "active"}
        ],
    }
    return SBStub(db), questions


def _authored_expl(mock_question_id: str, options: list[dict], **over) -> dict:
    wrong = [o for o in options if not o.get("is_correct")]
    row = {
        "id": str(uuid.uuid4()),
        "mock_question_id": mock_question_id,
        "explanation_source_type": "platform_original",
        "reviewer_status": "verified",
        "short_explanation": None,
        "explanation_text": None,
        "solution_steps": ["Over-processing: more than the customer values."],
        "option_rationales": {wrong[0]["id"]: "over-processing confused with motion"},
        "formula_used": ["TIMWOOD"],
        "common_traps": ["Motion = people; Transport = materials."],
        "final_answer_mock_option_id": next(o["id"] for o in options if o.get("is_correct")),
        "license_status": "owned",
        "metadata": {"internal": "do not leak"},
    }
    row.update(over)
    return row


def _review(sb):
    start = svc.start_attempt(sb, "user-1", "authored-expl-1")
    svc.submit_attempt(sb, "user-1", start["attempt_id"])
    return svc.get_review(sb, "user-1", start["attempt_id"])


def _q(review, qid):
    return next(q for q in review["questions"] if q["question_id"] == qid)


def test_verified_authored_explanation_reaches_review_with_rationale_on_its_option():
    sb, questions = _seeded([])
    authored = questions[1]
    sb.db["pyq_question_explanations"] = [_authored_expl(authored["id"], authored["options"])]
    payload = _q(_review(sb), authored["id"])["pyq_explanation"]
    assert payload["solution_steps"] == ["Over-processing: more than the customer values."]
    assert payload["formula_used"] == ["TIMWOOD"]
    wrong = next(o for o in authored["options"] if not o.get("is_correct"))
    assert payload["option_rationales"] == [
        {"option_index": wrong["option_index"], "rationale": "over-processing confused with motion"}
    ]
    # governance columns never reach the learner
    for leaked in ("metadata", "license_status", "final_answer_mock_option_id", "mock_question_id",
                   "reviewer_status"):
        assert leaked not in payload


@pytest.mark.parametrize("status", ["pending", "rejected", "needs_correction"])
def test_unverified_authored_explanation_never_reaches_an_aspirant(status):
    sb, questions = _seeded([])
    authored = questions[1]
    sb.db["pyq_question_explanations"] = [
        _authored_expl(authored["id"], authored["options"], reviewer_status=status)
    ]
    assert _q(_review(sb), authored["id"])["pyq_explanation"] is None


def test_pyq_row_never_picks_up_an_explanation_keyed_to_its_bank_id():
    sb, questions = _seeded([])
    pyq_row = questions[0]
    sb.db["pyq_question_explanations"] = [_authored_expl(pyq_row["id"], pyq_row["options"])]
    assert _q(_review(sb), pyq_row["id"])["pyq_explanation"] is None


def test_common_trap_is_frozen_and_returned_in_review():
    sb, questions = _seeded([])
    review = _review(sb)
    assert _q(review, questions[1]["id"])["common_trap"] == "Motion = people; Transport = materials."
    assert _q(review, questions[1]["id"])["question_snapshot"]["common_trap"] == \
        "Motion = people; Transport = materials."
    assert _q(review, questions[0]["id"])["common_trap"] is None


def test_common_trap_is_not_exposed_during_the_attempt():
    sb, questions = _seeded([])
    start = svc.start_attempt(sb, "user-1", "authored-expl-1")
    state = svc.get_attempt(sb, "user-1", start["attempt_id"])
    for q in state["questions"]:
        assert "common_trap" not in q
