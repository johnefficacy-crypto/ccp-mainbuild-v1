"""Regression tests for select_questions_for_template fail-closed behaviour.

A fixed-template section lists explicit question IDs. If ANY of those IDs are
unavailable after status/expiry/lineage filtering, the function must raise
LookupError rather than returning a shortened (or empty) list.  An empty return
would silently fall through to start_attempt's _load_questions_for_template
fallback, producing a non-fixed attempt — which is wrong.

Covered cases:
- unpublished: reviewer_status not in {verified, published, live}
- expired:     valid_until in the past
- stale_pyq:   pyq-derived question whose projection is not active
- blocked_pyq: pyq-derived question whose projection sync_status='blocked'
- missing:     ID listed in section but absent from mock_question_bank entirely
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.study_os.mock_engine import select_questions_for_template
from tests.persona_questions._stub import SBStub


# ─── helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _past_iso(secs: int = 10) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=secs)).isoformat()


TMPL_ID = "tmpl-0001-0000-0000-000000000001"
Q_FIXED = "qfix-0001-0000-0000-000000000001"
Q_OTHER = "qfix-0002-0000-0000-000000000002"


def _base_option(qid: str, idx: int, is_correct: bool) -> dict:
    return {
        "id": f"opt-{qid}-{idx}",
        "question_id": qid,
        "option_text": f"Opt {idx}",
        "option_index": idx,
        "is_correct": is_correct,
    }


def _base_question(qid: str, *, reviewer_status: str = "published",
                   valid_until: str | None = None,
                   pyq_question_id: str | None = None) -> dict:
    return {
        "id": qid,
        "exam_id": "exam-01",
        "subject_id": "subj-01",
        "topic_id": "topic-01",
        "question_text": f"Question {qid[:6]}",
        "question_type": "mcq",
        "difficulty": "medium",
        "reviewer_status": reviewer_status,
        "valid_until": valid_until,
        "pyq_question_id": pyq_question_id,
        "source_kind": "authored",
        "source_type": "authored",
    }


def _fixed_section(question_ids: list[str]) -> dict:
    return {
        "id": "sec-01",
        "template_id": TMPL_ID,
        "section_index": 0,
        "question_count": len(question_ids),
        "selector": {"mode": "fixed", "question_ids": question_ids},
    }


def _build_db(*,
              question: dict,
              projection_rows: list[dict] | None = None) -> dict:
    """Return a minimal seeded db with one fixed section listing Q_FIXED."""
    return {
        "mock_template_sections": [_fixed_section([Q_FIXED])],
        "mock_question_bank": [question],
        "mock_question_options": [
            _base_option(Q_FIXED, i, i == 0) for i in range(4)
        ],
        "pyq_mock_question_projections": projection_rows or [],
    }


# ─── tests ────────────────────────────────────────────────────────────────────

class TestFixedTemplateFail:
    """All cases where the fixed ID is unavailable → LookupError."""

    def test_unpublished_question_raises(self):
        """reviewer_status='draft' is filtered out → LookupError."""
        q = _base_question(Q_FIXED, reviewer_status="draft")
        sb = SBStub(_build_db(question=q))
        with pytest.raises(LookupError, match=Q_FIXED[:8]):
            select_questions_for_template(sb, TMPL_ID, "user-1")

    def test_needs_changes_question_raises(self):
        """reviewer_status='needs_changes' is filtered out → LookupError."""
        q = _base_question(Q_FIXED, reviewer_status="needs_changes")
        sb = SBStub(_build_db(question=q))
        with pytest.raises(LookupError, match=Q_FIXED[:8]):
            select_questions_for_template(sb, TMPL_ID, "user-1")

    def test_expired_question_raises(self):
        """valid_until in the past → filtered out by valid_until check → LookupError."""
        q = _base_question(Q_FIXED, valid_until=_past_iso(60))
        sb = SBStub(_build_db(question=q))
        with pytest.raises(LookupError, match=Q_FIXED[:8]):
            select_questions_for_template(sb, TMPL_ID, "user-1")

    def test_stale_pyq_question_raises(self):
        """PYQ-derived question with no active projection → excluded by guard → LookupError."""
        PYQ_ID = "pyq-src1-0000-0000-000000000001"
        q = _base_question(Q_FIXED, pyq_question_id=PYQ_ID)
        # Projection exists but is stale — not in the active set.
        proj = {
            "pyq_question_id": PYQ_ID,
            "mock_question_id": Q_FIXED,
            "sync_status": "stale",
        }
        sb = SBStub(_build_db(question=q, projection_rows=[proj]))
        with pytest.raises(LookupError, match=Q_FIXED[:8]):
            select_questions_for_template(sb, TMPL_ID, "user-1")

    def test_blocked_pyq_question_raises(self):
        """PYQ-derived question with blocked projection → excluded → LookupError."""
        PYQ_ID = "pyq-src2-0000-0000-000000000002"
        q = _base_question(Q_FIXED, pyq_question_id=PYQ_ID)
        proj = {
            "pyq_question_id": PYQ_ID,
            "mock_question_id": Q_FIXED,
            "sync_status": "blocked",
        }
        sb = SBStub(_build_db(question=q, projection_rows=[proj]))
        with pytest.raises(LookupError, match=Q_FIXED[:8]):
            select_questions_for_template(sb, TMPL_ID, "user-1")

    def test_missing_question_raises(self):
        """ID in fixed section is completely absent from mock_question_bank → LookupError."""
        # Seed with a different question ID — Q_FIXED is not in the bank.
        q = _base_question(Q_OTHER)
        db = {
            "mock_template_sections": [_fixed_section([Q_FIXED])],
            "mock_question_bank": [q],
            "mock_question_options": [],
            "pyq_mock_question_projections": [],
        }
        sb = SBStub(db)
        with pytest.raises(LookupError, match=Q_FIXED[:8]):
            select_questions_for_template(sb, TMPL_ID, "user-1")


class TestFixedTemplatePass:
    """Cases where the fixed ID is available → no exception, question returned."""

    def test_published_question_passes(self):
        """reviewer_status='published' → included → returns the question."""
        q = _base_question(Q_FIXED, reviewer_status="published")
        sb = SBStub(_build_db(question=q))
        result = select_questions_for_template(sb, TMPL_ID, "user-1")
        assert len(result) == 1
        assert result[0]["id"] == Q_FIXED

    def test_active_pyq_question_passes(self):
        """PYQ-derived question with active projection → included → returns question."""
        PYQ_ID = "pyq-src3-0000-0000-000000000003"
        q = _base_question(Q_FIXED, pyq_question_id=PYQ_ID)
        proj = {
            "pyq_question_id": PYQ_ID,
            "mock_question_id": Q_FIXED,
            "sync_status": "active",
        }
        sb = SBStub(_build_db(question=q, projection_rows=[proj]))
        result = select_questions_for_template(sb, TMPL_ID, "user-1")
        assert len(result) == 1
        assert result[0]["id"] == Q_FIXED
