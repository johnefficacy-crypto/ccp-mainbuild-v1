"""PYQ v2 PR-5/6 (slice B) — learner PYQ practice attempt assembly.

Practice selects VERIFIED, actively-projected PYQ rows from mock_question_bank by
paper / section / topic and starts an ad-hoc attempt through the generated
blueprint path. The resulting attempt is a normal mock attempt (served by the
existing /attempts/{id} routes) and carries the PR-4/slice-A render fidelity.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import mock_engine as mock_engine_api
from app.core.auth import get_current_user
from app.study_os import mock_engine as engine
from app.study_os import pyq_practice as svc
from tests.persona_questions._stub import SBStub

EXAM = "11111111-1111-1111-1111-111111111111"
EXAM_B = "1b1b1b1b-1b1b-1b1b-1b1b-1b1b1b1b1b1b"
PHASE = "22222222-2222-2222-2222-222222222222"
SECTION = "33333333-3333-3333-3333-333333333333"
PAPER = "44444444-4444-4444-4444-444444444444"
TOPIC = "55555555-5555-5555-5555-555555555555"
# Two microtopics under TOPIC, plus an id that is locked in coverage but has no
# projected rows (migration 270 level-awareness).
MICRO_A = "66666666-6666-6666-6666-6666666666aa"
MICRO_B = "66666666-6666-6666-6666-6666666666bb"
UNRELATED_TOPIC = "88888888-8888-8888-8888-888888888888"


def _opt(qid: str, i: int, correct: bool) -> dict:
    return {
        "id": f"opt-{qid}-{i}",
        "question_id": qid,
        "option_text": f"Option {i}",
        "option_index": i,
        "is_correct": correct,
        "source_label": f"({chr(96 + i)})",
        "display_order": i,
        "reviewer_status": "verified",
    }


def _q(
    qid: str,
    *,
    paper: str = PAPER,
    section: str = SECTION,
    topic: str = TOPIC,
    microtopic: str | None = None,
    year: int = 2024,
    exam: str = EXAM,
) -> dict:
    """A projected bank row.

    ``microtopic=None`` is BOTH a top-level-tagged row (either side of migration
    270) and a pre-270 flattened microtopic row — the two are indistinguishable
    in the bank, which is exactly why matching must consider both columns. Pass
    ``topic=<parent>, microtopic=<child>`` for a post-270 split row.
    """
    return {
        "id": qid,
        "question_text": f"Question {qid}",
        "question_type": "mcq",
        "reviewer_status": "verified",
        "correct_option_id": f"opt-{qid}-2",
        "exam_id": exam,
        "subject_id": "sub-1",
        "pyq_question_id": f"pyqq-{qid}",
        "pyq_paper_id": paper,
        "section_id": section,
        "topic_id": topic,
        "microtopic_id": microtopic,
        "pyq_year": year,
        "difficulty": "medium",
    }


def _db(questions: list[dict], *, active: bool = True, stimuli: list[dict] | None = None, pyq_order: dict[str, int] | None = None) -> SBStub:
    opts = [_opt(q["id"], i, i == 2) for q in questions for i in range(1, 5)]
    pyq_order = pyq_order or {}
    pyq_questions = [
        {
            "id": q["pyq_question_id"],
            "display_order": pyq_order.get(q["id"]),
            "question_number": pyq_order.get(q["id"]),
            "source_question_ref": str(pyq_order[q["id"]]) if q["id"] in pyq_order else None,
        }
        for q in questions
    ]
    db = {
        "mock_question_bank": questions,
        "mock_question_options": opts,
        "mock_question_stimuli": stimuli or [],
        "pyq_questions": pyq_questions,
        "pyq_mock_question_projections": [
            {"mock_question_id": q["id"], "sync_status": "active" if active else "stale"}
            for q in questions
        ],
        "exam_phase_sections": [{"id": SECTION, "exam_phase_id": PHASE}],
        "mock_generated_blueprints": [],
        "mock_attempts": [],
        "mock_attempt_responses": [],
    }
    return SBStub(db)


def test_paper_practice_starts_attempt_with_render_fidelity():
    sb = _db(
        [_q("q1"), _q("q2")],
        stimuli=[{
            "id": "s1", "mock_question_id": "q1", "stimulus_type": "passage",
            "content_text": "A shared passage.", "language": "en", "display_order": 1,
        }],
        pyq_order={"q1": 1, "q2": 2},
    )
    res = svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id=PAPER, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 2
    assert res["source"] == "pyq_practice_paper"
    assert res["exam_id"] == EXAM
    assert res["attempt_id"]

    state = engine.get_attempt(sb, "u1", res["attempt_id"])
    q1 = next(q for q in state["questions"] if q["question_id"] == "q1")
    assert q1["stimuli"] and q1["stimuli"][0]["content_text"] == "A shared passage."
    assert [o["source_label"] for o in q1["options"]] == ["(a)", "(b)", "(c)", "(d)"]


def test_paper_practice_preserves_source_printed_order_not_bank_id():
    # bank id order (q1, q2) is the REVERSE of the source printed order.
    sb = _db([_q("q1"), _q("q2")], pyq_order={"q1": 2, "q2": 1})
    res = svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id=PAPER, exam_id=EXAM)
    state = engine.get_attempt(sb, "u1", res["attempt_id"])
    # served in source display_order → q2 (display_order 1) before q1 (2)
    assert [q["question_id"] for q in state["questions"]] == ["q2", "q1"]


def test_section_practice_filters_by_section():
    sb = _db([_q("q1", section=SECTION), _q("q2", section="99999999-9999-9999-9999-999999999999")], pyq_order={"q1": 1, "q2": 1})
    res = svc.start_pyq_practice(sb, user_id="u1", mode="section", target_id=SECTION, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 1
    assert res["source"] == "pyq_practice_section"


def test_topic_practice_requires_exam_id():
    sb = _db([_q("q1")])
    try:
        svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=TOPIC)
        raise AssertionError("expected PracticeInputError for topic without exam_id")
    except svc.PracticeInputError:
        pass


def test_topic_practice_does_not_mix_exams():
    # same topic_id shared across two exams; exam_id scopes the set to one exam.
    sb = _db([_q("q1", exam=EXAM), _q("q2", exam=EXAM_B)])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 1
    assert res["exam_id"] == EXAM
    state = engine.get_attempt(sb, "u1", res["attempt_id"])
    assert [q["question_id"] for q in state["questions"]] == ["q1"]


# ─── Migration 270: level-aware topic matching ────────────────────────────────
#
# Before 270 the projection flattened a microtopic tag into `topic_id`. After it,
# a microtopic-tagged row carries the PARENT in `topic_id` and the tag in
# `microtopic_id`. The ~800 already-projected rows keep the flattened shape until
# each is re-synced, so both shapes coexist and a target id must match EITHER
# column. Matching `topic_id` alone would return an EMPTY set — silently, as a
# 409 empty_pool rather than an error — for every microtopic-locked target
# (426 of the 469 locks on the live UPSC exam).

def test_microtopic_target_matches_post_270_split_row():
    # post-270: topic_id = parent, microtopic_id = the tag.
    sb = _db([_q("q1", topic=TOPIC, microtopic=MICRO_A)])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=MICRO_A, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 1
    state = engine.get_attempt(sb, "u1", res["attempt_id"])
    assert [q["question_id"] for q in state["questions"]] == ["q1"]


def test_microtopic_target_matches_pre_270_flattened_row():
    # pre-270: the microtopic id sits in topic_id and microtopic_id is NULL.
    sb = _db([_q("q1", topic=MICRO_A)])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=MICRO_A, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 1


def test_microtopic_target_matches_both_row_shapes_in_one_pool():
    # The state during rollout: some rows re-synced, some not. One target, both.
    sb = _db([
        _q("q1", topic=MICRO_A),                        # not yet re-synced
        _q("q2", topic=TOPIC, microtopic=MICRO_A),      # re-synced under 270
    ])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=MICRO_A, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 2
    state = engine.get_attempt(sb, "u1", res["attempt_id"])
    assert sorted(q["question_id"] for q in state["questions"]) == ["q1", "q2"]


def test_top_level_target_still_matches_its_own_rows():
    sb = _db([_q("q1", topic=TOPIC)])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 1


def test_top_level_target_sweeps_in_child_microtopic_rows_post_270():
    """IMPLEMENTED BEHAVIOUR, and a deliberate change from pre-270.

    Pre-270 `topic_id` held the tagged id verbatim, so a top-level target matched
    ONLY questions tagged at exactly that id — never its children. Post-270 a
    child's row carries the parent in `topic_id`, so `topic_id = target` pulls the
    whole subtree in. Topic practice on a parent is therefore subtree-wide.
    Pinned here so the widening is a visible decision, not a silent drift.
    """
    sb = _db([
        _q("q1", topic=TOPIC),                          # tagged at the parent
        _q("q2", topic=TOPIC, microtopic=MICRO_A),      # tagged at a child
        _q("q3", topic=TOPIC, microtopic=MICRO_B),      # tagged at another child
    ])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 3


def test_sibling_microtopic_target_does_not_match():
    sb = _db([_q("q1", topic=TOPIC, microtopic=MICRO_A)])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=MICRO_B, exam_id=EXAM)
    assert res["outcome"] == "empty_pool"
    assert res["question_count"] == 0
    assert sb.db["mock_attempts"] == []


def test_topic_target_with_no_projected_rows_is_still_empty_pool():
    # Empty case unchanged: level-awareness must not invent a match.
    sb = _db([_q("q1", topic=TOPIC, microtopic=MICRO_A)])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=UNRELATED_TOPIC, exam_id=EXAM)
    assert res["outcome"] == "empty_pool"
    assert res["question_count"] == 0
    assert sb.db["mock_attempts"] == []
    assert sb.db["mock_attempt_responses"] == []


def test_microtopic_match_still_scoped_to_one_exam():
    # The single-exam invariant holds on the new match path too.
    sb = _db([
        _q("q1", topic=TOPIC, microtopic=MICRO_A, exam=EXAM),
        _q("q2", topic=TOPIC, microtopic=MICRO_A, exam=EXAM_B),
    ])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=MICRO_A, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 1
    assert res["exam_id"] == EXAM


def test_section_mode_is_not_level_matched():
    # Only topic mode gains the OR; section/paper still match their own column.
    # A row whose microtopic_id happens to equal the requested section id must
    # NOT be pulled into a section set.
    sb = _db([_q("q1", section=SECTION, topic=TOPIC, microtopic=SECTION)], pyq_order={"q1": 1})
    res = svc.start_pyq_practice(sb, user_id="u1", mode="section", target_id=SECTION, exam_id=EXAM)
    assert res["outcome"] == "ready"
    assert res["question_count"] == 1  # matched by section_id, once — not twice


# ─── practiceable_topic_ids: same matching, keyed on the REQUESTED id ──────────

def _practiceable(sb, ids: list[str]) -> set[str]:
    return svc.practiceable_topic_ids(sb, exam_id=EXAM, topic_ids=ids)


def test_practiceable_reports_microtopic_target_post_270_split_row():
    # The row's own topic_id is the PARENT; availability must be reported for the
    # requested MICROTOPIC, not for a parent nobody asked about.
    sb = _db([_q("q1", topic=TOPIC, microtopic=MICRO_A)])
    assert _practiceable(sb, [MICRO_A]) == {MICRO_A}


def test_practiceable_reports_microtopic_target_pre_270_flattened_row():
    sb = _db([_q("q1", topic=MICRO_A)])
    assert _practiceable(sb, [MICRO_A]) == {MICRO_A}


def test_practiceable_reports_top_level_target():
    sb = _db([_q("q1", topic=TOPIC)])
    assert _practiceable(sb, [TOPIC]) == {TOPIC}


def test_practiceable_counts_one_row_for_both_locked_levels():
    # Parent and child both locked in coverage: the split row satisfies both.
    sb = _db([_q("q1", topic=TOPIC, microtopic=MICRO_A)])
    assert _practiceable(sb, [TOPIC, MICRO_A]) == {TOPIC, MICRO_A}


def test_practiceable_omits_a_target_with_no_rows():
    sb = _db([_q("q1", topic=TOPIC, microtopic=MICRO_A)])
    ready = _practiceable(sb, [MICRO_A, MICRO_B, UNRELATED_TOPIC])
    assert ready == {MICRO_A}


def test_practiceable_never_returns_an_unrequested_id():
    # The contract is "a subset of topic_ids". Keying on the row's own topic_id
    # would leak the parent TOPIC into the result for a microtopic-only request.
    sb = _db([_q("q1", topic=TOPIC, microtopic=MICRO_A)])
    ready = _practiceable(sb, [MICRO_A])
    assert ready <= {MICRO_A}
    assert TOPIC not in ready


def test_practiceable_empty_when_nothing_projected():
    sb = _db([])
    assert _practiceable(sb, [TOPIC, MICRO_A]) == set()


def test_timed_practice_freezes_server_owned_countdown():
    # GQR-R10: seconds_per_question × frozen count becomes the attempt's expiry window,
    # so the shared objective attempt shell surfaces a short countdown (not the long
    # learning-mode TTL). duration_sec is also frozen on the template for reports.
    sb = _db([_q("q1", exam=EXAM), _q("q2", exam=EXAM)], pyq_order={"q1": 1, "q2": 2})
    res = svc.start_pyq_practice(
        sb, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM,
        seconds_per_question=30,
    )
    assert res["outcome"] == "ready" and res["question_count"] == 2
    state = engine.get_attempt(sb, "u1", res["attempt_id"])
    # 30s × 2 questions → ~60s countdown (a second or two may have elapsed).
    assert 55 <= state.get("time_remaining_sec") <= 60


def test_untimed_practice_reports_no_countdown():
    sb = _db([_q("q1", exam=EXAM)], pyq_order={"q1": 1})
    res = svc.start_pyq_practice(sb, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM)
    state = engine.get_attempt(sb, "u1", res["attempt_id"])
    # Untimed practice must surface no learner clock — the shell renders "--" and never
    # auto-submits. The long 24h abandonment TTL stays server-side on expires_at.
    assert state.get("time_remaining_sec") is None
    assert state.get("expires_at")


def _attempt_row(sb, attempt_id):
    return next(a for a in sb.db["mock_attempts"] if a["id"] == attempt_id)


def test_timed_deadline_is_the_single_enforced_window():
    # F1 (checkpost #960): the timed countdown is not display-only. The persisted
    # expires_at IS the short timed window (not the 24h abandonment TTL), so the shared
    # runtime paths (save/submit/auto-submit/sweeper) enforce it — untimed practice
    # keeps the long TTL.
    sb = _db([_q("q1", exam=EXAM), _q("q2", exam=EXAM)], pyq_order={"q1": 1, "q2": 2})
    timed = svc.start_pyq_practice(
        sb, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM, seconds_per_question=30,
    )
    assert 0 < engine._time_remaining_sec(_attempt_row(sb, timed["attempt_id"])) <= 60

    sb2 = _db([_q("q1", exam=EXAM)], pyq_order={"q1": 1})
    untimed = svc.start_pyq_practice(sb2, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM)
    assert engine._time_remaining_sec(_attempt_row(sb2, untimed["attempt_id"])) > 3600


def test_late_save_rejected_after_timed_deadline():
    # Advancing beyond the timed deadline: a save is rejected server-side by the shared
    # expires_at guard — the browser auto-submit is convenience, not enforcement.
    sb = _db([_q("q1", exam=EXAM)], pyq_order={"q1": 1})
    res = svc.start_pyq_practice(
        sb, user_id="u1", mode="topic", target_id=TOPIC, exam_id=EXAM, seconds_per_question=30,
    )
    aid = res["attempt_id"]
    q0 = engine.get_attempt(sb, "u1", aid)["questions"][0]
    # simulate the timed window elapsing
    _attempt_row(sb, aid)["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=5)
    ).isoformat()
    with pytest.raises(ValueError, match="expired"):
        engine.save_answer(
            sb, "u1", aid, q0["question_id"], (q0["options"][0] or {}).get("id"),
            is_marked_for_review=False, client_seq=1, time_spent_sec=5,
        )


def test_empty_pool_returns_no_writes():
    sb = _db([_q("q1", paper="66666666-6666-6666-6666-666666666666")])
    res = svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id=PAPER, exam_id=EXAM)
    assert res["outcome"] == "empty_pool"
    assert res["question_count"] == 0
    assert sb.db["mock_attempts"] == []
    assert sb.db["mock_attempt_responses"] == []


def test_stale_projection_is_excluded_from_practice():
    sb = _db([_q("q1")], active=False, pyq_order={"q1": 1})
    res = svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id=PAPER, exam_id=EXAM)
    assert res["outcome"] == "empty_pool"


def test_unverified_bank_row_is_excluded():
    q = _q("q1")
    q["reviewer_status"] = "pending"
    sb = _db([q], pyq_order={"q1": 1})
    res = svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id=PAPER, exam_id=EXAM)
    assert res["outcome"] == "empty_pool"


def test_invalid_uuid_target_is_rejected():
    sb = _db([_q("q1")])
    try:
        svc.start_pyq_practice(sb, user_id="u1", mode="paper", target_id="not-a-uuid", exam_id=EXAM)
        raise AssertionError("expected PracticeInputError for malformed target_id")
    except svc.PracticeInputError:
        pass


def _client(sb: SBStub, user_id: str = "u1") -> TestClient:
    app = FastAPI()
    app.include_router(mock_engine_api.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": user_id}
    mock_engine_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    return TestClient(app)


def test_api_start_practice_ready_and_409_on_empty():
    sb = _db([_q("q1")], pyq_order={"q1": 1})
    client = _client(sb)
    r = client.post("/api/study/mocks/practice/start", json={"mode": "paper", "target_id": PAPER, "exam_id": EXAM})
    assert r.status_code == 200
    assert r.json()["outcome"] == "ready"
    r2 = client.post("/api/study/mocks/practice/start", json={"mode": "paper", "target_id": "66666666-6666-6666-6666-666666666666", "exam_id": EXAM})
    assert r2.status_code == 409


def test_api_rejects_unknown_mode_and_bad_uuid():
    sb = _db([_q("q1")])
    client = _client(sb)
    assert client.post("/api/study/mocks/practice/start", json={"mode": "essay", "target_id": PAPER}).status_code == 422
    assert client.post("/api/study/mocks/practice/start", json={"mode": "paper", "target_id": "nope", "exam_id": EXAM}).status_code == 422
