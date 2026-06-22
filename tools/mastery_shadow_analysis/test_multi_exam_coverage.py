"""Tests for the multi-exam-coverage subcommand of shadow_analysis.py."""
from __future__ import annotations

import json
import os
import sys
import uuid
from typing import Any
from unittest.mock import patch

import pytest

# Ensure backend is importable.
_BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../app/backend"))
if _BACKEND_ROOT not in sys.path:
    sys.path.insert(0, _BACKEND_ROOT)

import tools.mastery_shadow_analysis.shadow_analysis as sa

# ─── Lightweight Supabase stub ────────────────────────────────────────────────

class _Exec:
    def __init__(self, data: list) -> None:
        self.data = data


class _Query:
    def __init__(self, name: str, db: dict) -> None:
        self.name = name
        self.db = db
        self.filters: list = []
        self._order_col: str | None = None

    def select(self, *a: Any, **kw: Any) -> "_Query":
        return self

    def eq(self, k: str, v: Any) -> "_Query":
        self.filters.append((k, "eq", v))
        return self

    def neq(self, k: str, v: Any) -> "_Query":
        self.filters.append((k, "neq", v))
        return self

    def in_(self, k: str, vals: list) -> "_Query":
        self.filters.append((k, "in", list(vals)))
        return self

    def order(self, col: str, **kw: Any) -> "_Query":
        self._order_col = col
        return self

    def range(self, start: int, end: int) -> "_Query":
        return self

    def limit(self, n: int) -> "_Query":
        return self

    def gte(self, k: str, v: Any) -> "_Query":
        self.filters.append((k, "gte", v))
        return self

    def lte(self, k: str, v: Any) -> "_Query":
        self.filters.append((k, "lte", v))
        return self

    def _matches(self, row: dict) -> bool:
        for k, op, v in self.filters:
            cell = row.get(k)
            if op == "eq" and cell != v:
                return False
            if op == "neq" and cell == v:
                return False
            if op == "in" and cell not in v:
                return False
            # gte/lte: best-effort string comparison (ISO dates sort correctly)
            if op == "gte" and cell is not None and str(cell) < str(v):
                return False
            if op == "lte" and cell is not None and str(cell) > str(v):
                return False
        return True

    def execute(self) -> _Exec:
        rows = self.db.get(self.name, [])
        matched = [r for r in rows if self._matches(r)]
        if self._order_col:
            matched.sort(key=lambda r: (r.get(self._order_col) or ""))
        return _Exec(matched)


class SBStub:
    def __init__(self, db: dict[str, list[dict]] | None = None) -> None:
        self.db: dict[str, list[dict]] = db or {}

    def table(self, name: str) -> _Query:
        return _Query(name, self.db)


# ─── Constants ────────────────────────────────────────────────────────────────

EXAM_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
EXAM_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
SUBJ_1 = "11111111-1111-1111-1111-111111111111"
TOPIC_1 = "t1111111-1111-1111-1111-111111111111"
ATTEMPT_1 = "att11111-1111-1111-1111-111111111111"
TEMPLATE_1 = "tmpl1111-1111-1111-1111-111111111111"
BLUEPRINT_1 = "bp111111-1111-1111-1111-111111111111"


# ─── Row builders ─────────────────────────────────────────────────────────────

def _shadow_row(
    attempt_id: str = ATTEMPT_1,
    topic_id: str = TOPIC_1,
    user_id: str = "user-1",
) -> dict:
    """Build a mock_mastery_shadow row with flag_state='shadow'."""
    return {
        "id": f"shadow-{attempt_id}-{topic_id}",
        "user_id": user_id,
        "topic_id": topic_id,
        "attempt_id": attempt_id,
        "proposed_delta_db": "5.0",
        "current_mastery_db": "50.0",
        "would_be_mastery_db": "55.0",
        "decided_at": "2026-06-01T00:00:00+00:00",
        "flag_state": "shadow",
    }


def _attempt_row(
    attempt_id: str = ATTEMPT_1,
    user_id: str = "user-1",
    template_id: str | None = TEMPLATE_1,
    generated_blueprint_id: str | None = None,
    status: str = "submitted",
) -> dict:
    """Build a mock_attempts row."""
    return {
        "id": attempt_id,
        "user_id": user_id,
        "template_id": template_id,
        "generated_blueprint_id": generated_blueprint_id,
        "status": status,
    }


def _template_row(
    template_id: str = TEMPLATE_1,
    exam_id: str = EXAM_A,
) -> dict:
    """Build a mock_templates row."""
    return {
        "id": template_id,
        "exam_id": exam_id,
    }


def _blueprint_row(
    blueprint_id: str = BLUEPRINT_1,
    exam_id: str = EXAM_A,
) -> dict:
    """Build a mock_generated_blueprints row."""
    return {
        "id": blueprint_id,
        "exam_id": exam_id,
    }


def _response_row(
    attempt_id: str = ATTEMPT_1,
    source_kind: str = "authored",
    subject_id: str = SUBJ_1,
) -> dict:
    """Build a mock_attempt_responses row."""
    return {
        "id": f"resp-{attempt_id}-{source_kind}",
        "attempt_id": attempt_id,
        "question_snapshot": {
            "id": "q-1",
            "subject_id": subject_id,
            "source_kind": source_kind,
            "topic_id": TOPIC_1,
        },
    }


def _exam_row(exam_id: str, slug: str, name: str) -> dict:
    return {"id": exam_id, "slug": slug, "name": name}


def _seed_db(
    shadow_rows: list | None = None,
    attempt_rows: list | None = None,
    template_rows: list | None = None,
    blueprint_rows: list | None = None,
    response_rows: list | None = None,
    exam_rows: list | None = None,
) -> dict:
    """Return a db dict seeded with sensible defaults for EXAM_A."""
    return {
        "mock_mastery_shadow": shadow_rows if shadow_rows is not None else [_shadow_row()],
        "mock_attempts": attempt_rows if attempt_rows is not None else [_attempt_row()],
        "mock_templates": template_rows if template_rows is not None else [_template_row()],
        "mock_generated_blueprints": blueprint_rows if blueprint_rows is not None else [],
        "mock_attempt_responses": response_rows if response_rows is not None else [_response_row()],
        "exams": exam_rows if exam_rows is not None else [_exam_row(EXAM_A, "upsc-cse", "UPSC CSE")],
    }


def _run(sb: SBStub, **kwargs) -> dict:
    """Run multi_exam_coverage with the given stub and capture stdout JSON."""
    import io
    out = io.StringIO()
    with patch.object(sa, "_get_supabase", return_value=sb):
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.stdout", out):
                sa.multi_exam_coverage(output_json=True, **kwargs)
    result = json.loads(out.getvalue())
    return {"result": result, "exit_code": exc_info.value.code}


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestMultiExamCoverageNoData:
    def test_no_shadow_data_insufficient(self):
        """Empty mock_mastery_shadow → INSUFFICIENT_DATA."""
        sb = SBStub(_seed_db(shadow_rows=[]))
        r = _run(sb, required_exam_ids=[EXAM_A], required_exam_slugs=[], min_questions=1)
        assert r["result"]["status"] == "INSUFFICIENT_DATA"
        assert r["exit_code"] == sa._EXIT_INSUFFICIENT

    def test_query_failure_exits_error(self):
        """DB failure on mock_mastery_shadow table → ERROR."""
        class _FailSB(SBStub):
            def table(self, name):
                q = _Query(name, self.db)
                if name == "mock_mastery_shadow":
                    orig_execute = q.execute
                    def fail_execute():
                        raise RuntimeError("DB down")
                    q.execute = fail_execute
                return q

        sb = _FailSB({})
        r = _run(sb, required_exam_ids=[EXAM_A], required_exam_slugs=[], min_questions=1)
        assert r["result"]["status"] == "ERROR"
        assert r["exit_code"] == sa._EXIT_ERROR

    def test_no_tracks_supplied_exits_error(self):
        """No required_exam_ids or slugs → ERROR with code NO_TRACKS_SUPPLIED."""
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[], required_exam_slugs=[], min_questions=1)
        assert r["result"]["status"] == "ERROR"
        assert r["result"].get("error") == "NO_TRACKS_SUPPLIED"
        assert r["exit_code"] == sa._EXIT_ERROR


class TestMultiExamCoveragePass:
    def test_pass_when_exam_meets_threshold(self):
        """Seed EXAM_A with 1 shadow row; require EXAM_A; min_questions=1 → PASS."""
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[EXAM_A], required_exam_slugs=[], min_questions=1)
        assert r["result"]["status"] == "PASS"
        assert r["exit_code"] == sa._EXIT_OK

    def test_exam_coverage_populated(self):
        """Coverage list has one entry with correct exam_id and shadow_row_count >= 1."""
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[EXAM_A], required_exam_slugs=[], min_questions=1)
        coverage = r["result"]["exam_coverage"]
        assert len(coverage) == 1
        assert coverage[0]["exam_id"] == EXAM_A
        assert coverage[0]["shadow_row_count"] >= 1

    def test_source_split_populated(self):
        """Response with source_kind='pyq' → source_split has pyq >= 1."""
        db = _seed_db(
            response_rows=[_response_row(ATTEMPT_1, source_kind="pyq")],
        )
        sb = SBStub(db)
        r = _run(sb, required_exam_ids=[EXAM_A], required_exam_slugs=[], min_questions=1)
        split = r["result"]["exam_coverage"][0]["source_split"]
        assert split.get("pyq", 0) >= 1

    def test_multiple_exams_tracked(self):
        """Two attempts with different exams → total_exams_in_shadow = 2."""
        ATTEMPT_2 = "att22222-2222-2222-2222-222222222222"
        TEMPLATE_2 = "tmpl2222-2222-2222-2222-222222222222"
        db = _seed_db(
            shadow_rows=[_shadow_row(ATTEMPT_1), _shadow_row(ATTEMPT_2)],
            attempt_rows=[
                _attempt_row(ATTEMPT_1, template_id=TEMPLATE_1),
                _attempt_row(ATTEMPT_2, template_id=TEMPLATE_2),
            ],
            template_rows=[
                _template_row(TEMPLATE_1, EXAM_A),
                _template_row(TEMPLATE_2, EXAM_B),
            ],
            response_rows=[
                _response_row(ATTEMPT_1),
                _response_row(ATTEMPT_2),
            ],
            exam_rows=[
                _exam_row(EXAM_A, "upsc-cse", "UPSC CSE"),
                _exam_row(EXAM_B, "upsc-csat", "UPSC CSAT"),
            ],
        )
        sb = SBStub(db)
        r = _run(sb, required_exam_ids=[EXAM_A], required_exam_slugs=[], min_questions=1)
        assert r["result"]["total_exams_in_shadow"] == 2

    def test_slug_resolved_to_exam_id(self):
        """Require via slug 'upsc-cse' → PASS."""
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[], required_exam_slugs=["upsc-cse"], min_questions=1)
        assert r["result"]["status"] == "PASS"

    def test_unknown_slug_counts_as_insufficient(self):
        """Require via slug 'unknown-exam' → INSUFFICIENT_DATA with slug in insufficient_exams."""
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[], required_exam_slugs=["unknown-exam"], min_questions=1)
        assert r["result"]["status"] == "INSUFFICIENT_DATA"
        assert any(
            e.get("exam_slug") == "unknown-exam"
            for e in r["result"]["insufficient_exams"]
        )


class TestMultiExamCoverageGeneratedBlueprint:
    def test_generated_attempt_exam_resolved(self):
        """Attempt with template_id=None, generated_blueprint_id=BLUEPRINT_1 → exam resolved → PASS."""
        db = _seed_db(
            shadow_rows=[_shadow_row(ATTEMPT_1)],
            attempt_rows=[_attempt_row(ATTEMPT_1, template_id=None, generated_blueprint_id=BLUEPRINT_1)],
            template_rows=[],
            blueprint_rows=[_blueprint_row(BLUEPRINT_1, EXAM_A)],
            response_rows=[_response_row(ATTEMPT_1)],
            exam_rows=[_exam_row(EXAM_A, "upsc-cse", "UPSC CSE")],
        )
        sb = SBStub(db)
        r = _run(sb, required_exam_ids=[EXAM_A], required_exam_slugs=[], min_questions=1)
        assert r["result"]["status"] == "PASS"

    def test_template_attempt_exam_resolved(self):
        """Attempt with template_id=TEMPLATE_1 → exam_id resolved via mock_templates → PASS."""
        db = _seed_db(
            shadow_rows=[_shadow_row(ATTEMPT_1)],
            attempt_rows=[_attempt_row(ATTEMPT_1, template_id=TEMPLATE_1, generated_blueprint_id=None)],
            template_rows=[_template_row(TEMPLATE_1, EXAM_A)],
            blueprint_rows=[],
            response_rows=[_response_row(ATTEMPT_1)],
            exam_rows=[_exam_row(EXAM_A, "upsc-cse", "UPSC CSE")],
        )
        sb = SBStub(db)
        r = _run(sb, required_exam_ids=[EXAM_A], required_exam_slugs=[], min_questions=1)
        assert r["result"]["status"] == "PASS"


class TestMultiExamCoverageInsufficient:
    def test_required_exam_missing_from_shadow(self):
        """Require EXAM_B but only have EXAM_A → INSUFFICIENT_DATA."""
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[EXAM_B], required_exam_slugs=[], min_questions=1)
        assert r["result"]["status"] == "INSUFFICIENT_DATA"
        assert r["exit_code"] == sa._EXIT_INSUFFICIENT
        insuf = r["result"]["insufficient_exams"]
        assert any(e["exam_id"] == EXAM_B for e in insuf)

    def test_min_questions_threshold_not_met(self):
        """min_questions=999 → INSUFFICIENT_DATA with required_minimum=999."""
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[EXAM_A], required_exam_slugs=[], min_questions=999)
        assert r["result"]["status"] == "INSUFFICIENT_DATA"
        insuf = r["result"]["insufficient_exams"]
        assert insuf[0]["required_minimum"] == 999


class TestMultiExamCoverageOutput:
    def test_result_has_required_fields(self):
        """Result has schema_version, command, status, exam_coverage, insufficient_exams, thresholds."""
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[EXAM_A], required_exam_slugs=[], min_questions=1)
        res = r["result"]
        assert res["schema_version"] == 1
        assert res["command"] == "multi_exam_coverage"
        assert "status" in res
        assert "exam_coverage" in res
        assert "insufficient_exams" in res
        assert "thresholds" in res

    def test_exam_slug_included_when_known(self):
        """Coverage entry has exam_slug='upsc-cse'."""
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[EXAM_A], required_exam_slugs=[], min_questions=1)
        coverage = r["result"]["exam_coverage"]
        assert coverage[0].get("exam_slug") == "upsc-cse"

    def test_attempt_count_deduplicated(self):
        """Two shadow rows for same attempt → unique_attempt_count=1."""
        TOPIC_2 = "t2222222-2222-2222-2222-222222222222"
        db = _seed_db(
            shadow_rows=[
                _shadow_row(ATTEMPT_1, TOPIC_1),
                _shadow_row(ATTEMPT_1, TOPIC_2),
            ],
            response_rows=[_response_row(ATTEMPT_1)],
        )
        sb = SBStub(db)
        r = _run(sb, required_exam_ids=[EXAM_A], required_exam_slugs=[], min_questions=1)
        coverage = r["result"]["exam_coverage"]
        assert coverage[0]["unique_attempt_count"] == 1
