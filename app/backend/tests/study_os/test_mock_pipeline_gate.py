"""Pipeline gate — verify draft questions cannot reach live without reviewer verify.

Tests the controlled pipeline: resource/PYQ/CA → draft → reviewed → verified
and proves that only verified (or published) questions are selectable by the
template selector.  A question sitting in draft or reviewed state is
invisible to start_attempt.
"""
from __future__ import annotations

import uuid

import pytest

from app.study_os import mock_engine as svc
from tests.persona_questions._stub import SBStub


def _opt(qid: str, idx: int, correct: bool) -> dict:
    return {
        "id": f"opt-{qid}-{idx}",
        "question_id": qid,
        "option_text": f"Option {idx}",
        "option_index": idx,
        "is_correct": correct,
    }


def _question(reviewer_status: str, qid: str | None = None) -> dict:
    qid = qid or str(uuid.uuid4())
    opts = [_opt(qid, i, i == 1) for i in range(4)]
    return {
        "id": qid,
        "exam_family": "TEST",
        "question_text": f"Q {qid[:8]}",
        "question_type": "mcq",
        "difficulty": "easy",
        "correct_option_id": opts[0]["id"],
        "explanation": "Because.",
        "reviewer_status": reviewer_status,
        "options": opts,
    }


def _build_db(question_status: str) -> tuple[SBStub, str]:
    """Return a seeded DB where all questions have *question_status*."""
    questions = [_question(question_status) for _ in range(3)]
    qids = [q["id"] for q in questions]
    template = {
        "id": "tmpl-gate-test",
        "slug": "gate-test",
        "name": "Gate Test Mock",
        "exam_family": "TEST",
        "total_questions": len(questions),
        "duration_sec": 300,
        "negative_marking": True,
        "marks_per_correct": 1.0,
        "marks_per_wrong": 0.25,
        "config": {"question_ids": qids},
        "status": "active",
    }
    db = {
        "mock_templates": [template],
        "mock_question_bank": questions,
        "mock_question_options": [o for q in questions for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
        "mock_attempt_events": [],
        "mock_attempt_jobs": [],
        "mock_tests": [],
    }
    return SBStub(db), "gate-test"


# ── Draft questions cannot start an attempt ────────────────────────────────────

def test_draft_questions_not_selectable():
    """An attempt start fails with LookupError when all bank questions are in draft.
    Fail-closed: the loader now raises immediately listing the unavailable IDs."""
    sb, slug = _build_db("draft")
    with pytest.raises(LookupError, match="unavailable"):
        svc.start_attempt(sb, "user-1", slug)


def test_reviewed_questions_not_selectable():
    """'reviewed' is an intermediate state; questions are not yet selectable.
    Fail-closed: the loader now raises immediately listing the unavailable IDs."""
    sb, slug = _build_db("reviewed")
    with pytest.raises(LookupError, match="unavailable"):
        svc.start_attempt(sb, "user-1", slug)


def test_in_review_questions_not_selectable():
    """'in_review' (authoring pipeline) is not the live gate.
    Fail-closed: the loader now raises immediately listing the unavailable IDs."""
    sb, slug = _build_db("in_review")
    with pytest.raises(LookupError, match="unavailable"):
        svc.start_attempt(sb, "user-1", slug)


# ── Verified and published questions are selectable ───────────────────────────

def test_verified_questions_selectable():
    """Questions that reached reviewer_status='verified' are selectable."""
    sb, slug = _build_db("verified")
    result = svc.start_attempt(sb, "user-1", slug)
    assert result["attempt_id"]
    assert len(result["questions"]) == 3


def test_published_questions_selectable():
    """'published' questions (already past verified) remain selectable (backward compat)."""
    sb, slug = _build_db("published")
    result = svc.start_attempt(sb, "user-1", slug)
    assert result["attempt_id"]
    assert len(result["questions"]) == 3


# ── Mixed bank: only verified rows are served ─────────────────────────────────

def test_fixed_config_with_mixed_statuses_raises_on_unavailable():
    """A fixed-config template that lists unavailable IDs (draft/reviewed) alongside
    available ones must raise LookupError — fail-closed prevents a silently shortened
    attempt.  The error names the specific unavailable IDs."""
    draft_q = _question("draft", "draft-q")
    reviewed_q = _question("reviewed", "reviewed-q")
    verified_q = _question("verified", "verified-q")
    published_q = _question("published", "published-q")

    all_qids = [draft_q["id"], reviewed_q["id"], verified_q["id"], published_q["id"]]
    template = {
        "id": "tmpl-mixed",
        "slug": "mixed",
        "name": "Mixed",
        "exam_family": "TEST",
        "total_questions": 4,
        "duration_sec": 300,
        "negative_marking": True,
        "marks_per_correct": 1.0,
        "marks_per_wrong": 0.25,
        "config": {"question_ids": all_qids},
        "status": "active",
    }
    all_qs = [draft_q, reviewed_q, verified_q, published_q]
    db = {
        "mock_templates": [template],
        "mock_question_bank": all_qs,
        "mock_question_options": [o for q in all_qs for o in q["options"]],
        "mock_attempts": [],
        "mock_attempt_responses": [],
        "mock_attempt_events": [],
        "mock_attempt_jobs": [],
        "mock_tests": [],
    }
    sb = SBStub(db)
    with pytest.raises(LookupError, match="unavailable"):
        svc.start_attempt(sb, "user-1", "mixed")
