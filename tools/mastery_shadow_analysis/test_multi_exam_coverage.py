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

    def _matches(self, row: dict) -> bool:
        for k, op, v in self.filters:
            cell = row.get(k)
            if op == "eq" and cell != v:
                return False
            if op == "neq" and cell == v:
                return False
            if op == "in" and cell not in v:
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


# ─── Helpers ──────────────────────────────────────────────────────────────────

EXAM_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
EXAM_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
SUBJ_1 = "11111111-1111-1111-1111-111111111111"
TOPIC_1 = "t1111111-1111-1111-1111-111111111111"
ATTEMPT_1 = "att11111-1111-1111-1111-111111111111"


def _audit_row(attempt_id: str = ATTEMPT_1, topic_id: str = TOPIC_1) -> dict:
    return {
        "id": f"{attempt_id}-{topic_id}",
        "user_id": "user-1",
        "topic_id": topic_id,
        "attempt_id": attempt_id,
        "delta_applied_db": "5.0",
        "reason": "mock_submit",
        "before_mastery_db": "50.0",
        "after_mastery_db": "55.0",
    }


def _response_row(attempt_id: str, exam_id: str, source_kind: str = "authored", subject_id: str = SUBJ_1) -> dict:
    return {
        "id": f"resp-{attempt_id}-{exam_id}",
        "attempt_id": attempt_id,
        "question_id": "q-1",
        "question_snapshot": {
            "id": "q-1",
            "exam_id": exam_id,
            "subject_id": subject_id,
            "source_kind": source_kind,
            "source_type": "authored",
            "topic_id": TOPIC_1,
            "difficulty": "medium",
        },
    }


def _exam_row(exam_id: str, slug: str, name: str) -> dict:
    return {"id": exam_id, "slug": slug, "name": name}


def _seed_db(
    audit_rows: list | None = None,
    response_rows: list | None = None,
    exam_rows: list | None = None,
) -> dict:
    return {
        "user_topic_mastery_audit": audit_rows or [_audit_row()],
        "mock_attempt_responses": response_rows or [_response_row(ATTEMPT_1, EXAM_A)],
        "exams": exam_rows or [_exam_row(EXAM_A, "upsc-cse", "UPSC CSE")],
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
    def test_no_audit_rows_insufficient(self):
        sb = SBStub({"user_topic_mastery_audit": [], "mock_attempt_responses": [], "exams": []})
        r = _run(sb, required_exam_ids=[], required_exam_slugs=[], min_questions=1)
        assert r["result"]["status"] == "INSUFFICIENT_DATA"
        assert r["exit_code"] == sa._EXIT_INSUFFICIENT

    def test_query_failure_exits_error(self):
        class _FailSB(SBStub):
            def table(self, name):
                q = _Query(name, self.db)
                if name == "user_topic_mastery_audit":
                    orig_execute = q.execute
                    def fail_execute():
                        raise RuntimeError("DB down")
                    q.execute = fail_execute
                return q
        sb = _FailSB({})
        r = _run(sb, required_exam_ids=[], required_exam_slugs=[], min_questions=1)
        assert r["result"]["status"] == "ERROR"
        assert r["exit_code"] == sa._EXIT_ERROR


class TestMultiExamCoveragePass:
    def test_pass_when_no_requirements(self):
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[], required_exam_slugs=[], min_questions=1)
        assert r["result"]["status"] == "PASS"
        assert r["exit_code"] == sa._EXIT_OK

    def test_pass_when_exam_meets_threshold(self):
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[EXAM_A], required_exam_slugs=[], min_questions=1)
        assert r["result"]["status"] == "PASS"
        assert r["exit_code"] == sa._EXIT_OK

    def test_exam_coverage_populated(self):
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[], required_exam_slugs=[], min_questions=1)
        coverage = r["result"]["exam_coverage"]
        assert len(coverage) == 1
        assert coverage[0]["exam_id"] == EXAM_A
        assert coverage[0]["question_count"] >= 1

    def test_source_split_populated(self):
        db = _seed_db(
            response_rows=[
                _response_row(ATTEMPT_1, EXAM_A, source_kind="pyq"),
            ]
        )
        sb = SBStub(db)
        r = _run(sb, required_exam_ids=[], required_exam_slugs=[], min_questions=1)
        split = r["result"]["exam_coverage"][0]["source_split"]
        assert split.get("pyq", 0) >= 1

    def test_multiple_exams_tracked(self):
        attempt_b = "att22222-2222-2222-2222-222222222222"
        db = _seed_db(
            audit_rows=[_audit_row(ATTEMPT_1), _audit_row(attempt_b)],
            response_rows=[
                _response_row(ATTEMPT_1, EXAM_A),
                _response_row(attempt_b, EXAM_B),
            ],
            exam_rows=[
                _exam_row(EXAM_A, "upsc-cse", "UPSC CSE"),
                _exam_row(EXAM_B, "upsc-csat", "UPSC CSAT"),
            ],
        )
        sb = SBStub(db)
        r = _run(sb, required_exam_ids=[], required_exam_slugs=[], min_questions=1)
        assert r["result"]["total_exams_in_shadow"] == 2

    def test_slug_resolved_to_exam_id(self):
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[], required_exam_slugs=["upsc-cse"], min_questions=1)
        assert r["result"]["status"] == "PASS"

    def test_unknown_slug_counts_as_insufficient(self):
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[], required_exam_slugs=["unknown-exam"], min_questions=1)
        assert r["result"]["status"] == "INSUFFICIENT_DATA"
        assert any(e.get("exam_slug") == "unknown-exam" for e in r["result"]["insufficient_exams"])


class TestMultiExamCoverageInsufficient:
    def test_required_exam_missing_from_shadow(self):
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[EXAM_B], required_exam_slugs=[], min_questions=1)
        assert r["result"]["status"] == "INSUFFICIENT_DATA"
        assert r["exit_code"] == sa._EXIT_INSUFFICIENT
        insuf = r["result"]["insufficient_exams"]
        assert any(e["exam_id"] == EXAM_B for e in insuf)

    def test_min_questions_threshold_not_met(self):
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[EXAM_A], required_exam_slugs=[], min_questions=999)
        assert r["result"]["status"] == "INSUFFICIENT_DATA"
        insuf = r["result"]["insufficient_exams"]
        assert insuf[0]["required_minimum"] == 999


class TestMultiExamCoverageOutput:
    def test_result_has_required_fields(self):
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[], required_exam_slugs=[], min_questions=1)
        res = r["result"]
        assert res["schema_version"] == 1
        assert res["command"] == "multi_exam_coverage"
        assert "status" in res
        assert "exam_coverage" in res
        assert "insufficient_exams" in res
        assert "thresholds" in res

    def test_exam_slug_included_when_known(self):
        sb = SBStub(_seed_db())
        r = _run(sb, required_exam_ids=[], required_exam_slugs=[], min_questions=1)
        coverage = r["result"]["exam_coverage"]
        assert coverage[0].get("exam_slug") == "upsc-cse"

    def test_attempt_count_deduplicated(self):
        # Two audit rows for same attempt → attempt_count should be 1, not 2
        db = _seed_db(
            audit_rows=[
                _audit_row(ATTEMPT_1, TOPIC_1),
                {**_audit_row(ATTEMPT_1, TOPIC_1), "id": "row-2", "topic_id": "topic-2"},
            ],
            response_rows=[
                _response_row(ATTEMPT_1, EXAM_A),
            ],
        )
        sb = SBStub(db)
        r = _run(sb, required_exam_ids=[], required_exam_slugs=[], min_questions=1)
        coverage = r["result"]["exam_coverage"]
        assert coverage[0]["attempt_count"] == 1
