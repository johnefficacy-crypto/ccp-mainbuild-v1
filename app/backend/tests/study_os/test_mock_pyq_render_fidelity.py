"""PYQ v2 PR-5/6 — projected-PYQ render fidelity in the mock attempt path.

Migration 229 (PR-4) makes the PYQ→mock projection STORE a question's source
section, per-option printed label/order, and its shared passage/stimulus
snapshot (``mock_question_stimuli``). This suite pins that the mock attempt
engine now FREEZES those fields into ``question_snapshot`` at attempt start and
SURFACES them through the attempt-taking, result, and review reads — so a learner
practising a projected PYQ sees its passage and printed option labels, served
straight from the frozen snapshot (never the live bank).
"""
from __future__ import annotations

from app.study_os import mock_engine as svc
from tests.persona_questions._stub import SBStub
from tests.study_os.test_mock_engine import (
    _make_question,
    _make_template,
)

_SECTION_ID = "sec-csat-2"
_STIM_ID = "mstim-1"


def _seeded_pyq_db() -> tuple[SBStub, dict, str]:
    """One template whose first question is a projected PYQ with a section, a
    shared passage snapshot, and printed option labels. Returns (sb, template,
    pyq_question_id)."""
    template, questions = _make_template("pyq-render-1")
    pyq_q = questions[0]
    pyq_q["pyq_question_id"] = "pyqq-1"
    pyq_q["pyq_paper_id"] = "pyqp-1"
    pyq_q["pyq_year"] = 2025
    pyq_q["section_id"] = _SECTION_ID
    # printed labels/order on the projected options
    for i, o in enumerate(pyq_q["options"]):
        o["source_label"] = f"({chr(ord('a') + i)})"
        o["display_order"] = i + 1

    db: dict = {
        "mock_templates": [template],
        "mock_question_bank": questions,
        "mock_question_options": [o for q in questions for o in q["options"]],
        "mock_question_stimuli": [
            {
                "id": _STIM_ID,
                "mock_question_id": pyq_q["id"],
                "pyq_stimulus_id": "pstim-1",
                "stimulus_type": "passage",
                "content_text": "Read the following passage and answer.",
                "language": "en",
                "display_order": 1,
            }
        ],
        # projection lineage must be active or the lineage guard drops the row
        "pyq_mock_question_projections": [
            {"mock_question_id": pyq_q["id"], "sync_status": "active"}
        ],
        "mock_attempts": [],
        "mock_attempt_responses": [],
        "mock_tests": [],
    }
    return SBStub(db), template, pyq_q["id"]


def _attempt_question(sb: SBStub, attempt_id: str, mock_qid: str) -> dict:
    state = svc.get_attempt(sb, "user-1", attempt_id)
    return next(q for q in state["questions"] if q["question_id"] == mock_qid)


def test_start_freezes_stimuli_section_and_option_labels_into_snapshot():
    sb, _template, pyq_qid = _seeded_pyq_db()
    started = svc.start_attempt(sb, "user-1", "pyq-render-1")
    attempt_id = started["attempt_id"]

    q = _attempt_question(sb, attempt_id, pyq_qid)

    assert q["section_id"] == _SECTION_ID
    assert len(q["stimuli"]) == 1
    stim = q["stimuli"][0]
    assert stim["stimulus_type"] == "passage"
    assert stim["content_text"] == "Read the following passage and answer."
    assert stim["display_order"] == 1
    # printed option labels/order carried per option
    assert [o["source_label"] for o in q["options"]] == ["(a)", "(b)", "(c)", "(d)"]
    assert [o["display_order"] for o in q["options"]] == [1, 2, 3, 4]


def test_authored_question_has_empty_stimuli_and_null_section():
    sb, _template, _pyq_qid = _seeded_pyq_db()
    started = svc.start_attempt(sb, "user-1", "pyq-render-1")
    # a non-PYQ authored question in the same template (index > 0, no stimuli)
    state = svc.get_attempt(sb, "user-1", started["attempt_id"])
    authored = [q for q in state["questions"] if not q["stimuli"]]
    assert authored, "expected at least one authored question with no stimuli"
    for q in authored:
        assert q["stimuli"] == []
        assert q["section_id"] is None


def test_snapshot_is_frozen_against_live_bank_edits():
    """Render fidelity must come from the frozen snapshot, not the live bank —
    editing the passage after attempt start must not change what the learner
    sees (mirrors the engine's AC7 freeze guarantee)."""
    sb, _template, pyq_qid = _seeded_pyq_db()
    started = svc.start_attempt(sb, "user-1", "pyq-render-1")

    # mutate the live stimulus snapshot after the attempt froze
    sb.db["mock_question_stimuli"][0]["content_text"] = "TAMPERED"

    q = _attempt_question(sb, started["attempt_id"], pyq_qid)
    assert q["stimuli"][0]["content_text"] == "Read the following passage and answer."


def test_result_and_review_surface_stimuli_and_labels():
    sb, _template, pyq_qid = _seeded_pyq_db()
    started = svc.start_attempt(sb, "user-1", "pyq-render-1")
    attempt_id = started["attempt_id"]
    svc.submit_attempt(sb, "user-1", attempt_id, claimed_answered_count=None)

    result = svc.get_result(sb, "user-1", attempt_id)
    pq = next(p for p in result["per_question"] if p["question_id"] == pyq_qid)
    assert pq["section_id"] == _SECTION_ID
    assert pq["stimuli"] and pq["stimuli"][0]["stimulus_type"] == "passage"
    assert [o["source_label"] for o in pq["options"]] == ["(a)", "(b)", "(c)", "(d)"]

    review = svc.get_review(sb, "user-1", attempt_id)
    rq = next(q for q in review["questions"] if q["question_id"] == pyq_qid)
    snap = rq["question_snapshot"]
    assert snap["section_id"] == _SECTION_ID
    assert snap["stimuli"][0]["content_text"] == "Read the following passage and answer."
