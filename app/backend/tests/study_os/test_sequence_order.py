"""Signed sequence answers (parajumbles): freeze, redaction, fail-to-MCQ.

The drag-to-order drill grades by submitting the option that names the
learner's arrangement; the reviewed order only reaches the learner after
submit. These tests pin: an untampered verified record freezes; ANY
inconsistency (digest, answer key drift, unmapped option, ambiguous orders,
unverified) freezes nothing so the question stays a plain MCQ; get_attempt
never exposes the correct order.
"""
from __future__ import annotations

import copy

from app.study_os import generated_mock_attempt as gma
from app.study_os import mock_engine as engine
from app.study_os.sequence_order import (
    freeze_sequence,
    public_sequence,
    record_digest,
    validate_record,
)
from tests.persona_questions._stub import SBStub

PYQ_Q = "11111111-0000-0000-0000-000000000001"
LABELS = ["A", "B", "C", "D", "E"]  # SSC CGL: five sentences
PYQ_OPTS = {
    "po-1": ["B", "A", "D", "C", "E"],  # correct
    "po-2": ["A", "B", "C", "D", "E"],
    "po-3": ["E", "D", "C", "B", "A"],
    "po-4": ["C", "A", "B", "E", "D"],
}


def _record(**over):
    rec = {
        "version": 1,
        "verified": True,
        "order": ["B", "A", "D", "C", "E"],
        "segments": [{"label": lb, "text": f"Sentence {lb}."} for lb in LABELS],
        "lead": "Arrange the sentences in a logical order.",
        "tail": "",
        "option_orders": copy.deepcopy(PYQ_OPTS),
        "correct_pyq_option_id": "po-1",
    }
    rec.update(over)
    rec["digest"] = record_digest(rec, PYQ_Q)
    return rec


def _bank_options(mapping=None):
    mapping = mapping or {"mo-1": "po-1", "mo-2": "po-2", "mo-3": "po-3", "mo-4": "po-4"}
    return [
        {"id": mid, "option_text": "x", "option_index": i, "pyq_option_id": pid}
        for i, (mid, pid) in enumerate(mapping.items())
    ]


def test_valid_record_freezes_n_segments_and_rekeys_to_bank_options():
    out = freeze_sequence(_record(), pyq_question_id=PYQ_Q, options=_bank_options(), correct_option_id="mo-1")
    assert out is not None
    assert [s["label"] for s in out["segments"]] == LABELS  # N=5, not truncated to 4
    assert out["option_orders"]["mo-1"] == ["B", "A", "D", "C", "E"]
    assert set(out["option_orders"]) == {"mo-1", "mo-2", "mo-3", "mo-4"}
    assert out["correct_order"] == ["B", "A", "D", "C", "E"]


def test_public_view_never_carries_the_correct_order():
    frozen = freeze_sequence(_record(), pyq_question_id=PYQ_Q, options=_bank_options(), correct_option_id="mo-1")
    pub = public_sequence(frozen)
    assert "correct_order" not in pub
    assert pub["segments"] and pub["option_orders"]
    assert public_sequence(None) is None


def test_tampered_record_is_refused():
    rec = _record()
    rec["order"] = ["A", "B", "C", "D", "E"]  # edited after signing
    rec["option_orders"]["po-2"], rec["correct_pyq_option_id"] = rec["order"], "po-2"
    assert not validate_record(rec, PYQ_Q)
    assert freeze_sequence(rec, pyq_question_id=PYQ_Q, options=_bank_options(), correct_option_id="mo-2") is None


def test_digest_is_bound_to_the_question():
    assert not validate_record(_record(), "some-other-question")


def test_unverified_record_is_refused():
    rec = _record(verified=False)
    assert freeze_sequence(rec, pyq_question_id=PYQ_Q, options=_bank_options(), correct_option_id="mo-1") is None


def test_answer_key_drift_drops_to_mcq():
    # The bank now says mo-2 is correct; the signed order backs mo-1. Key wins.
    assert freeze_sequence(_record(), pyq_question_id=PYQ_Q, options=_bank_options(), correct_option_id="mo-2") is None


def test_unmapped_bank_option_drops_to_mcq():
    opts = _bank_options()
    opts[3]["pyq_option_id"] = None  # projected before migration 307
    assert freeze_sequence(_record(), pyq_question_id=PYQ_Q, options=opts, correct_option_id="mo-1") is None


def test_two_options_naming_one_order_is_refused():
    orders = copy.deepcopy(PYQ_OPTS)
    orders["po-3"] = list(orders["po-2"])
    assert not validate_record(_record(option_orders=orders), PYQ_Q)


def test_non_permutation_is_refused():
    orders = copy.deepcopy(PYQ_OPTS)
    orders["po-4"] = ["A", "A", "B", "C", "D"]
    assert not validate_record(_record(option_orders=orders), PYQ_Q)


# ── wiring: _load_questions → _question_snapshot → get_attempt ───────────────


def _db(record):
    return {
        "mock_question_bank": [{
            "id": "mq-1", "question_text": "Arrange", "question_type": "mcq",
            "correct_option_id": "mo-1", "pyq_question_id": PYQ_Q,
        }],
        "mock_question_options": [
            {"id": mid, "question_id": "mq-1", "option_text": " ".join(PYQ_OPTS[pid]),
             "option_index": i, "display_order": i, "pyq_option_id": pid}
            for i, (mid, pid) in enumerate({"mo-1": "po-1", "mo-2": "po-2", "mo-3": "po-3", "mo-4": "po-4"}.items())
        ],
        "mock_question_stimuli": [],
        "pyq_questions": [{"id": PYQ_Q, "metadata": {"correct_order": record} if record else {}}],
    }


def test_load_questions_freezes_sequence_and_get_attempt_redacts_it():
    sb = SBStub(_db(_record()))
    q = gma._load_questions(sb, ["mq-1"])["mq-1"]
    snap = engine._question_snapshot(q)
    assert snap["sequence"]["correct_order"] == ["B", "A", "D", "C", "E"]

    sb.db["mock_attempts"] = [{
        "id": "att-1", "user_id": "u1", "status": "in_progress",
        "template_snapshot": {"question_ids": ["mq-1"], "sections": []},
        "expires_at": "2999-01-01T00:00:00+00:00",
    }]
    sb.db["mock_attempt_responses"] = [{"attempt_id": "att-1", "question_id": "mq-1", "question_snapshot": snap}]
    sb.db["mock_attempt_section_state"] = []
    state = engine.get_attempt(sb, "u1", "att-1")
    seq = state["questions"][0]["sequence"]
    assert [s["label"] for s in seq["segments"]] == LABELS
    assert "correct_order" not in seq
    assert "correct_option_id" not in state["questions"][0]


def test_question_without_record_stays_plain_mcq():
    sb = SBStub(_db(None))
    q = gma._load_questions(sb, ["mq-1"])["mq-1"]
    assert engine._question_snapshot(q)["sequence"] is None
