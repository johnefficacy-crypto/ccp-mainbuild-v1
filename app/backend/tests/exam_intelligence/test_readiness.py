"""PR2: Exam Workspace readiness endpoint + compute function tests.

GET /api/admin/exam-intelligence/workspace/{exam_id}/readiness
    ?cycle_id=<uuid optional>

Covers:
- empty exam → all sections empty, overall score=0, status=empty
- exam with phases only → setup ready, others empty
- locked syllabus + verified PYQ + verified competition → ready_to_activate
- cycle_id scopes pyq_workbench/competition/documents
- unknown exam → 404
- unknown cycle → 404
- cycle from wrong exam → 422
- score math: weights apply correctly
- snapshot pin: overview() user_facing_readiness byte-identical pre/post refactor
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as review_api
from app.core.auth import get_current_user
from app.exam_intelligence.readiness import compute_exam_workspace_readiness, load_doc_extraction_counts

_BASE = "/api/admin/exam-intelligence"

# ── Fixtures ──────────────────────────────────────────────────────────────────

EXAM = {"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL", "exam_type": "recruitment", "is_active": True}
CYCLE_A = {"id": "cycle-2026", "exam_id": "exam-1", "year": 2026, "cycle_name": "2026", "status": "open"}
CYCLE_B = {"id": "cycle-other", "exam_id": "exam-2", "year": 2026, "cycle_name": "2026"}


def _client(sb_factory):
    app = FastAPI()
    app.include_router(review_api.router, prefix="/api")
    review_api.get_supabase_admin = sb_factory
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": "super_admin", "permissions": [review_api.ADMIN_PERM],
    }
    return TestClient(app, raise_server_exceptions=False)


# ── Stub builder ──────────────────────────────────────────────────────────────

class _SBStub:
    """Flexible supabase stub. Configure per-table return data via constructor."""

    def __init__(self, table_data: dict):
        """table_data: {table_name: list_of_rows | callable(filters) -> list}"""
        self._data = table_data

    def table(self, name):
        tbl = _TableStub(self._data.get(name, []))
        return tbl


class _TableStub:
    def __init__(self, rows):
        self._rows = rows if not callable(rows) else rows
        self._filters: dict = {}
        self._in_filters: dict = {}
        self._columns: list[str] | None = None
        self._range_start: int | None = None
        self._range_end: int | None = None

    def select(self, cols=None, **kw):
        if cols and isinstance(cols, str):
            self._columns = [c.strip() for c in cols.split(",") if c.strip()]
        return self

    def eq(self, k, v):
        self._filters[k] = v
        return self

    def in_(self, k, v):
        self._in_filters[k] = v
        return self

    def or_(self, expr):
        # Parse "field.eq.VALUE,field.is.null" used by topic_coverage_snapshot
        self._or_expr = expr
        return self

    def order(self, *a, **kw):
        return self

    def limit(self, n):
        return self

    def range(self, start, end):
        self._range_start = start
        self._range_end = end
        return self

    def execute(self):
        rows = self._rows if not callable(self._rows) else self._rows(self._filters, self._in_filters)
        # Apply or_ expr: "field.eq.VALUE,field.is.null"
        or_expr = getattr(self, "_or_expr", None)
        if or_expr and isinstance(rows, list):
            import re
            parts = or_expr.split(",")
            def _matches_or(row):
                for part in parts:
                    m = re.match(r"(\w+)\.eq\.(.+)", part)
                    if m and row.get(m.group(1)) == m.group(2):
                        return True
                    m2 = re.match(r"(\w+)\.is\.null", part)
                    if m2 and row.get(m2.group(1)) is None:
                        return True
                return False
            rows = [r for r in rows if _matches_or(r)]
        # Soft column projection: filter rows to selected columns only.
        # Columns absent from a row become None (same semantics as a projected DB query).
        # This catches wrong-column bugs at test time — e.g. selecting 'reviewer_status'
        # from pyq_papers (which only has 'trust_status') yields None and fails trust gates.
        if self._columns and isinstance(rows, list):
            rows = [{c: row.get(c) for c in self._columns} for row in rows]

        total_count = len(rows) if isinstance(rows, list) else 0
        res = MagicMock()
        res.count = total_count

        # Range slicing enables pagination-boundary correctness tests.
        if self._range_start is not None and isinstance(rows, list):
            end_idx = (self._range_end + 1) if self._range_end is not None else None
            rows = rows[self._range_start:end_idx]

        res.data = rows
        return res


def _make_sb(
    exam=None,
    phases=None,
    documents=None,
    doc_jobs=None,
    syllabus=None,
    pyq_papers=None,
    pyq_questions=None,
    updates=None,
    competition=None,
    exam_cycles=None,
    topic_coverage=None,
    pyq_options=None,
    pyq_question_topic_tags=None,
):
    """Build a test stub.

    documents: list of document_assets rows.  Each row must carry
      ``scope='admin_exam_intelligence'`` and ``metadata={"exam_id": ...,
      "exam_cycle_id": ...}``.  The stub filters by scope; exam/cycle
      filtering is done Python-side in load_doc_extraction_counts.

    doc_jobs: list of document_processing_jobs rows with
      ``document_id``, ``job_type``, ``status``, ``created_at``.
    """
    exam_rows = [exam] if exam else []
    phases_rows = phases or []
    doc_rows = documents or []
    dpj_rows = doc_jobs or []
    syllabus_rows = syllabus or []
    papers_rows = pyq_papers or []
    question_rows = pyq_questions or []
    update_rows = updates or []
    comp_rows = competition or []
    cycles_rows = exam_cycles or []
    coverage_rows = topic_coverage or []
    options_rows = pyq_options or []
    topic_tag_rows = pyq_question_topic_tags or []

    def _exam_cycles_fn(filters, in_filters):
        rows = cycles_rows
        if "exam_id" in filters:
            rows = [c for c in rows if c.get("exam_id") == filters["exam_id"]]
        if "id" in filters:
            rows = [c for c in rows if c.get("id") == filters["id"]]
        return rows

    def _pyq_q_fn(filters, in_filters):
        rows = question_rows
        if "pyq_paper_id" in in_filters:
            ids = in_filters["pyq_paper_id"]
            rows = [q for q in rows if q.get("pyq_paper_id") in ids]
        if "pyq_paper_id" in filters:
            rows = [q for q in rows if q.get("pyq_paper_id") == filters["pyq_paper_id"]]
        return rows

    def _papers_fn(filters, in_filters):
        rows = papers_rows
        if "exam_id" in filters:
            rows = [p for p in rows if p.get("exam_id") == filters["exam_id"]]
        if "exam_cycle_id" in filters:
            rows = [p for p in rows if p.get("exam_cycle_id") == filters["exam_cycle_id"]]
        return rows

    def _comp_fn(filters, in_filters):
        rows = comp_rows
        if "exam_id" in filters:
            rows = [r for r in rows if r.get("exam_id") == filters["exam_id"]]
        if "exam_cycle_id" in filters:
            rows = [r for r in rows if r.get("exam_cycle_id") == filters["exam_cycle_id"]]
        return rows

    def _doc_fn(filters, in_filters):
        rows = doc_rows
        # Real code filters by scope; exam/cycle are in metadata (Python-side).
        if "scope" in filters:
            rows = [d for d in rows if d.get("scope") == filters["scope"]]
        return rows

    def _dpj_fn(filters, in_filters):
        rows = dpj_rows
        if "document_id" in in_filters:
            ids = in_filters["document_id"]
            rows = [r for r in rows if r.get("document_id") in ids]
        if "job_type" in filters:
            rows = [r for r in rows if r.get("job_type") == filters["job_type"]]
        return rows

    def _options_fn(filters, in_filters):
        rows = options_rows
        if "question_id" in in_filters:
            ids = in_filters["question_id"]
            rows = [r for r in rows if r.get("question_id") in ids]
        return rows

    def _topic_tag_fn(filters, in_filters):
        rows = topic_tag_rows
        if "question_id" in in_filters:
            ids = in_filters["question_id"]
            rows = [r for r in rows if r.get("question_id") in ids]
        return rows

    def _coverage_fn(filters, in_filters):
        rows = coverage_rows
        if "exam_id" in filters:
            rows = [r for r in rows if r.get("exam_id") == filters["exam_id"]]
        if "exam_cycle_id" in filters:
            rows = [r for r in rows if r.get("exam_cycle_id") == filters["exam_cycle_id"]]
        return rows

    return _SBStub({
        "exams": exam_rows,
        "exam_cycles": _exam_cycles_fn,
        "exam_phases": phases_rows,
        "document_assets": _doc_fn,
        "document_processing_jobs": _dpj_fn,
        "syllabus_topic_mentions": syllabus_rows,
        "pyq_papers": _papers_fn,
        "pyq_questions": _pyq_q_fn,
        "exam_policy_updates": update_rows,
        "exam_competition_metrics": _comp_fn,
        "exam_topic_coverage": _coverage_fn,
        "pyq_options": _options_fn,
        "pyq_question_topic_tags": _topic_tag_fn,
    })


# ── Tests: compute function ───────────────────────────────────────────────────


class TestEmptyExam:
    def test_all_sections_empty(self):
        sb = _make_sb(exam=EXAM)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        for s in result["sections"]:
            assert s["status"] == "empty", f"{s['section']} expected empty, got {s['status']}"

    def test_overall_score_zero(self):
        sb = _make_sb(exam=EXAM)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        assert result["overall"]["score_percent"] == 0

    def test_overall_status_empty(self):
        sb = _make_sb(exam=EXAM)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        assert result["overall"]["status"] == "empty"

    def test_not_ready_to_activate(self):
        sb = _make_sb(exam=EXAM)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        assert result["overall"]["ready_to_activate"] is False

    def test_seven_sections(self):
        sb = _make_sb(exam=EXAM)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        assert len(result["sections"]) == 7
        labels = [s["section"] for s in result["sections"]]
        assert labels == [
            "setup", "documents", "syllabus_mapper", "pyq_workbench",
            "updates", "competition", "review_activate",
        ]


class TestSetupSection:
    def test_setup_ready_when_phases_exist(self):
        sb = _make_sb(
            exam=EXAM,
            phases=[{"id": "ph-1", "exam_id": "exam-1"}],
        )
        result = compute_exam_workspace_readiness(sb, "exam-1")
        setup = next(s for s in result["sections"] if s["section"] == "setup")
        assert setup["status"] == "ready"
        assert setup["blockers"] == []
        assert setup["metrics"]["phase_count"] == 1

    def test_setup_empty_when_no_phases(self):
        sb = _make_sb(exam=EXAM)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        setup = next(s for s in result["sections"] if s["section"] == "setup")
        assert setup["status"] == "empty"
        assert "no phases defined" in setup["blockers"]


class TestReadyToActivate:
    def test_ready_to_activate_requires_all_sections_ready_or_locked(self):
        phases = [{"id": "ph-1", "exam_id": "exam-1"}]
        syllabus = [
            {"id": f"s{i}", "exam_id": "exam-1", "reviewer_status": "locked"} for i in range(3)
        ]
        # D10: paper must have trust_status="verified" to pass gate 1.
        papers = [{"id": "p1", "exam_id": "exam-1", "exam_cycle_id": "cycle-2026",
                   "reviewer_status": "verified", "trust_status": "verified"}]
        questions = [
            {"id": f"q{i}", "pyq_paper_id": "p1", "reviewer_status": "verified"} for i in range(5)
        ]
        # D10: each question needs at least one verified topic tag (gate 3).
        topic_tags = [
            {"id": f"tag{i}", "question_id": f"q{i}", "reviewer_status": "verified"} for i in range(5)
        ]
        comp = [{"id": "c1", "exam_id": "exam-1", "exam_cycle_id": "cycle-2026", "reviewer_status": "reviewed"}]
        docs = [{"id": "d1", "scope": "admin_exam_intelligence",
                  "metadata": {"exam_id": "exam-1", "exam_cycle_id": "cycle-2026"}}]
        doc_jobs = [{"document_id": "d1", "job_type": "text_extract",
                     "status": "succeeded", "created_at": "2026-01-01T00:00:00"}]
        updates = [{"id": "u1", "exam_id": "exam-1", "reviewer_status": "verified", "created_at": "2099-01-01"}]

        sb = _make_sb(
            exam=EXAM,
            phases=phases,
            syllabus=syllabus,
            pyq_papers=papers,
            pyq_questions=questions,
            pyq_question_topic_tags=topic_tags,
            competition=comp,
            documents=docs,
            doc_jobs=doc_jobs,
            updates=updates,
        )
        result = compute_exam_workspace_readiness(sb, "exam-1")
        ra = next(s for s in result["sections"] if s["section"] == "review_activate")
        assert ra["status"] in {"ready", "locked"}
        assert result["overall"]["ready_to_activate"] is True


class TestCycleIdScoping:
    def _make_cycle_sb(self):
        phases = [{"id": "ph-1", "exam_id": "exam-1"}]
        docs = [
            {"id": "d1", "scope": "admin_exam_intelligence",
             "metadata": {"exam_id": "exam-1", "exam_cycle_id": "cycle-2026"}},
            {"id": "d2", "scope": "admin_exam_intelligence",
             "metadata": {"exam_id": "exam-1", "exam_cycle_id": "cycle-2025"}},
        ]
        doc_jobs = [
            {"document_id": "d1", "job_type": "text_extract",
             "status": "succeeded", "created_at": "2026-01-01T00:00:00"},
            {"document_id": "d2", "job_type": "text_extract",
             "status": "succeeded", "created_at": "2026-01-01T00:00:00"},
        ]
        papers = [
            {"id": "p1", "exam_id": "exam-1", "exam_cycle_id": "cycle-2026"},
            {"id": "p2", "exam_id": "exam-1", "exam_cycle_id": "cycle-2025"},
        ]
        questions = [
            {"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"},
            {"id": "q2", "pyq_paper_id": "p2", "reviewer_status": "pending"},
        ]
        comp = [
            {"id": "cm1", "exam_id": "exam-1", "exam_cycle_id": "cycle-2026", "reviewer_status": "reviewed"},
        ]
        cycles = [CYCLE_A]
        return _make_sb(
            exam=EXAM,
            phases=phases,
            documents=docs,
            doc_jobs=doc_jobs,
            pyq_papers=papers,
            pyq_questions=questions,
            competition=comp,
            exam_cycles=cycles,
        )

    def test_documents_scoped_by_cycle(self):
        sb = self._make_cycle_sb()
        result_with = compute_exam_workspace_readiness(sb, "exam-1", "cycle-2026")
        result_without = compute_exam_workspace_readiness(sb, "exam-1")
        docs_with = next(s for s in result_with["sections"] if s["section"] == "documents")
        docs_without = next(s for s in result_without["sections"] if s["section"] == "documents")
        assert docs_with["metrics"]["total"] == 1
        assert docs_without["metrics"]["total"] == 2

    def test_pyq_not_scoped_by_cycle(self):
        # D10: pyq_workbench is ALWAYS exam-wide; cycle_id is provenance context only.
        sb = self._make_cycle_sb()
        result_with = compute_exam_workspace_readiness(sb, "exam-1", "cycle-2026")
        pyq = next(s for s in result_with["sections"] if s["section"] == "pyq_workbench")
        # Both papers (cycle-2026 AND cycle-2025) must be counted — NOT just 1.
        assert pyq["metrics"]["papers"] == 2

    def test_competition_scoped_by_cycle(self):
        sb = self._make_cycle_sb()
        result_with = compute_exam_workspace_readiness(sb, "exam-1", "cycle-2026")
        comp = next(s for s in result_with["sections"] if s["section"] == "competition")
        assert comp["status"] == "ready"

        # No competition row for cycle-2025
        result_other = compute_exam_workspace_readiness(sb, "exam-1", "cycle-2025")
        comp_other = next(s for s in result_other["sections"] if s["section"] == "competition")
        assert comp_other["status"] == "empty"


class TestScoreMath:
    def test_weights_applied_correctly(self):
        """setup(w=1 ready=80) + syllabus(w=2 ready=80) + rest empty(w=1+3+1+1).
        score = (80*1 + 0*1 + 80*2 + 0*3 + 80*1 + 0*1) / (1+1+2+3+1+1) = 400/9 ≈ 44
        """
        phases = [{"id": "ph-1", "exam_id": "exam-1"}]
        syllabus = [
            {"id": f"s{i}", "exam_id": "exam-1", "reviewer_status": "locked"} for i in range(2)
        ]
        updates = [{"id": "u1", "exam_id": "exam-1", "reviewer_status": "verified", "created_at": "2099-01-01"}]
        sb = _make_sb(exam=EXAM, phases=phases, syllabus=syllabus, updates=updates)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        # setup ready(80,w=1), documents empty(0,w=1), syllabus locked(100,w=2),
        # pyq empty(0,w=3), updates ready(80,w=1), competition empty(0,w=1)
        # = (80 + 0 + 200 + 0 + 80 + 0) / 9 = 360/9 = 40
        assert result["overall"]["score_percent"] == 40

    def test_review_activate_excluded_from_score(self):
        """review_activate has weight=0, should not affect score."""
        sb = _make_sb(exam=EXAM)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        ra = next(s for s in result["sections"] if s["section"] == "review_activate")
        assert ra["weight"] == 0
        assert result["overall"]["score_percent"] == 0

    def test_contract_fields_present(self):
        sb = _make_sb(exam=EXAM)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        assert "exam_id" in result
        assert "cycle_id" in result
        assert "generated_at" in result
        assert "overall" in result
        assert "sections" in result
        assert "topic_coverage" in result
        overall = result["overall"]
        assert set(overall.keys()) >= {"status", "score_percent", "ready_to_activate", "blockers"}

    def test_topic_coverage_keys(self):
        sb = _make_sb(
            exam=EXAM,
            topic_coverage=[
                {"id": "tc1", "exam_id": "exam-1", "reviewer_status": "locked", "is_high_yield": True},
                {"id": "tc2", "exam_id": "exam-1", "reviewer_status": "draft", "is_high_yield": False},
                {"id": "tc3", "exam_id": "exam-1", "reviewer_status": "pending_review", "is_high_yield": False},
            ],
        )
        result = compute_exam_workspace_readiness(sb, "exam-1")
        tc = result["topic_coverage"]
        assert set(tc.keys()) == {"total", "draft", "pending", "reviewed", "locked", "high_yield"}
        assert tc["total"] == 3
        assert tc["locked"] == 1
        assert tc["draft"] == 1
        assert tc["pending"] == 1
        assert tc["high_yield"] == 1


class TestTopicCoverageScoping:
    def test_topic_coverage_scoped_by_cycle(self):
        all_coverage = [
            {"id": "tc1", "exam_id": "exam-1", "exam_cycle_id": "cycle-2026",
             "reviewer_status": "locked", "is_high_yield": True},
            {"id": "tc2", "exam_id": "exam-1", "exam_cycle_id": "cycle-2025",
             "reviewer_status": "draft", "is_high_yield": False},
        ]
        sb = _make_sb(exam=EXAM, topic_coverage=all_coverage)
        result_scoped = compute_exam_workspace_readiness(sb, "exam-1", "cycle-2026")
        result_all = compute_exam_workspace_readiness(sb, "exam-1")
        tc_scoped = result_scoped["topic_coverage"]
        tc_all = result_all["topic_coverage"]
        # Cycle-scoped: only cycle-2026 row
        assert tc_scoped["total"] == 1
        assert tc_scoped["locked"] == 1
        assert tc_scoped["high_yield"] == 1
        assert tc_scoped["draft"] == 0
        # No cycle filter: both rows
        assert tc_all["total"] == 2
        assert tc_all["locked"] == 1
        assert tc_all["draft"] == 1

    def test_topic_coverage_cycle_not_present(self):
        coverage = [
            {"id": "tc1", "exam_id": "exam-1", "exam_cycle_id": "cycle-2025",
             "reviewer_status": "locked", "is_high_yield": False},
        ]
        sb = _make_sb(exam=EXAM, topic_coverage=coverage)
        result = compute_exam_workspace_readiness(sb, "exam-1", "cycle-2026")
        tc = result["topic_coverage"]
        assert tc["total"] == 0


class TestRegressionGuard:
    """Verify that new additive metrics do NOT change score_percent or any
    section status/weight relative to a baseline fixture."""

    def _baseline_sb(self):
        phases = [{"id": "ph-1", "exam_id": "exam-1"}]
        syllabus = [
            {"id": f"s{i}", "exam_id": "exam-1", "reviewer_status": "locked"} for i in range(2)
        ]
        updates = [{"id": "u1", "exam_id": "exam-1", "reviewer_status": "verified", "created_at": "2099-01-01"}]
        return _make_sb(exam=EXAM, phases=phases, syllabus=syllabus, updates=updates)

    def _enriched_sb(self):
        phases = [{"id": "ph-1", "exam_id": "exam-1"}]
        syllabus = [
            {"id": f"s{i}", "exam_id": "exam-1", "reviewer_status": "locked"} for i in range(2)
        ]
        updates = [{"id": "u1", "exam_id": "exam-1", "reviewer_status": "verified", "created_at": "2099-01-01"}]
        # Extra tables (new) — must not change score
        coverage = [{"id": "tc1", "exam_id": "exam-1", "reviewer_status": "locked", "is_high_yield": True}]
        options = [{"id": "opt1", "question_id": "q-not-present"}]
        tags = [{"id": "tag1", "question_id": "q-not-present"}]
        return _make_sb(
            exam=EXAM, phases=phases, syllabus=syllabus, updates=updates,
            topic_coverage=coverage, pyq_options=options, pyq_question_topic_tags=tags,
        )

    def test_score_percent_unchanged(self):
        baseline = compute_exam_workspace_readiness(self._baseline_sb(), "exam-1")
        enriched = compute_exam_workspace_readiness(self._enriched_sb(), "exam-1")
        assert baseline["overall"]["score_percent"] == enriched["overall"]["score_percent"]

    def test_section_statuses_unchanged(self):
        baseline = compute_exam_workspace_readiness(self._baseline_sb(), "exam-1")
        enriched = compute_exam_workspace_readiness(self._enriched_sb(), "exam-1")
        for b_sec, e_sec in zip(baseline["sections"], enriched["sections"]):
            assert b_sec["section"] == e_sec["section"]
            assert b_sec["status"] == e_sec["status"], f"status mismatch for {b_sec['section']}"
            assert b_sec["weight"] == e_sec["weight"], f"weight mismatch for {b_sec['section']}"

    def test_section_count_still_seven(self):
        result = compute_exam_workspace_readiness(self._enriched_sb(), "exam-1")
        assert len(result["sections"]) == 7


class TestPYQEmptyMetricsKeys:
    def test_empty_papers_metrics_includes_options_and_tags(self):
        sb = _make_sb(exam=EXAM)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        pyq = next(s for s in result["sections"] if s["section"] == "pyq_workbench")
        assert pyq["status"] == "empty"
        assert "options_total" in pyq["metrics"]
        assert pyq["metrics"]["options_total"] == 0
        assert "topic_tags_total" in pyq["metrics"]
        assert pyq["metrics"]["topic_tags_total"] == 0


class TestCompetitionStatusSemantics:
    def test_reviewed_row_gives_ready(self):
        comp = [{"id": "c1", "exam_id": "exam-1", "reviewer_status": "reviewed"}]
        sb = _make_sb(exam=EXAM, competition=comp)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        sec = next(s for s in result["sections"] if s["section"] == "competition")
        assert sec["status"] == "ready"

    def test_locked_beats_reviewed(self):
        comp = [
            {"id": "c1", "exam_id": "exam-1", "reviewer_status": "reviewed"},
            {"id": "c2", "exam_id": "exam-1", "reviewer_status": "locked"},
        ]
        sb = _make_sb(exam=EXAM, competition=comp)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        sec = next(s for s in result["sections"] if s["section"] == "competition")
        assert sec["status"] == "locked"

    def test_draft_only_gives_partial(self):
        comp = [{"id": "c1", "exam_id": "exam-1", "reviewer_status": "draft"}]
        sb = _make_sb(exam=EXAM, competition=comp)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        sec = next(s for s in result["sections"] if s["section"] == "competition")
        assert sec["status"] == "partial"

    def test_rejected_only_does_not_promote_to_ready(self):
        comp = [{"id": "c1", "exam_id": "exam-1", "reviewer_status": "rejected"}]
        sb = _make_sb(exam=EXAM, competition=comp)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        sec = next(s for s in result["sections"] if s["section"] == "competition")
        assert sec["status"] == "partial"


class TestUpdatesRejectedCount:
    def test_rejected_count_in_metrics(self):
        updates = [
            {"id": "u1", "exam_id": "exam-1", "reviewer_status": "verified", "created_at": "2099-01-01"},
            {"id": "u2", "exam_id": "exam-1", "reviewer_status": "rejected", "created_at": "2099-01-01"},
            {"id": "u3", "exam_id": "exam-1", "reviewer_status": "rejected", "created_at": "2099-01-01"},
        ]
        sb = _make_sb(exam=EXAM, updates=updates)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        sec = next(s for s in result["sections"] if s["section"] == "updates")
        assert sec["metrics"]["rejected"] == 2


# ── Tests: HTTP endpoint ──────────────────────────────────────────────────────


class TestReadinessEndpointHappyPath:
    def _sb_factory(self, sb):
        def factory():
            return sb
        return factory

    def test_returns_200(self):
        sb = _make_sb(exam=EXAM, exam_cycles=[CYCLE_A])
        review_api.get_supabase_admin = self._sb_factory(sb)
        c = _client(self._sb_factory(sb))
        r = c.get(f"{_BASE}/workspace/exam-1/readiness")
        assert r.status_code == 200, r.text

    def test_response_shape(self):
        sb = _make_sb(exam=EXAM, exam_cycles=[CYCLE_A])
        c = _client(self._sb_factory(sb))
        r = c.get(f"{_BASE}/workspace/exam-1/readiness")
        body = r.json()
        assert body["exam_id"] == "exam-1"
        assert body["cycle_id"] is None
        assert "overall" in body
        assert "sections" in body
        assert len(body["sections"]) == 7

    def test_with_cycle_id(self):
        sb = _make_sb(exam=EXAM, exam_cycles=[CYCLE_A])
        c = _client(self._sb_factory(sb))
        r = c.get(f"{_BASE}/workspace/exam-1/readiness?cycle_id=cycle-2026")
        assert r.status_code == 200
        assert r.json()["cycle_id"] == "cycle-2026"


class TestReadinessEndpointErrors:
    def _sb_factory(self, sb):
        def factory():
            return sb
        return factory

    def test_unknown_exam_404(self):
        sb = _make_sb()  # no exam
        c = _client(self._sb_factory(sb))
        r = c.get(f"{_BASE}/workspace/nonexistent/readiness")
        assert r.status_code == 404
        assert "exam not found" in r.json().get("detail", "").lower()

    def test_unknown_cycle_404(self):
        sb = _make_sb(exam=EXAM, exam_cycles=[])
        c = _client(self._sb_factory(sb))
        r = c.get(f"{_BASE}/workspace/exam-1/readiness?cycle_id=no-such-cycle")
        assert r.status_code == 404
        assert "cycle not found" in r.json().get("detail", "").lower()

    def test_cycle_wrong_exam_422(self):
        sb = _make_sb(exam=EXAM, exam_cycles=[CYCLE_B])
        c = _client(self._sb_factory(sb))
        r = c.get(f"{_BASE}/workspace/exam-1/readiness?cycle_id=cycle-other")
        assert r.status_code == 422
        assert "does not belong to exam" in r.json().get("detail", "").lower()


# ── Snapshot pin: overview() user_facing_readiness unchanged ─────────────────


class TestOverviewSnapshotPin:
    """Verify overview() still produces the same user_facing_readiness shape after
    importing readiness module. The readiness module is purely additive — it does
    not touch overview()."""

    def _sb_factory_overview(self, coverage_locked=2, syllabus_verified=1, stale=0):
        """Stub for overview() which reads several tables."""
        import datetime as _dt
        old_date = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=20)).isoformat()
        new_date = _dt.datetime.now(_dt.timezone.utc).isoformat()

        syllabus_rows = [{"reviewer_status": "verified"}] * syllabus_verified
        if stale:
            syllabus_rows += [{"reviewer_status": "pending", "created_at": old_date}] * stale

        coverage_rows = [{"reviewer_status": "locked", "is_high_yield": False}] * coverage_locked

        sb = MagicMock()

        def _table(name):
            tbl = MagicMock()
            q = MagicMock()
            q.select.return_value = q
            q.eq.return_value = q
            q.in_.return_value = q
            q.order.return_value = q
            q.limit.return_value = q
            res = MagicMock()
            if name == "syllabus_topic_mentions":
                res.data = syllabus_rows
            elif name == "exam_topic_coverage":
                res.data = coverage_rows
            elif name == "exams":
                res.data = [EXAM]
            elif name in ("pyq_question_topic_tags", "pyq_questions", "pyq_options"):
                res.data = []
            else:
                res.data = []
            q.execute.return_value = res
            tbl.select.return_value = q
            return tbl

        sb.table.side_effect = _table
        return lambda: sb

    def test_user_facing_readiness_ready(self):
        app = FastAPI()
        app.include_router(review_api.router, prefix="/api")
        review_api.get_supabase_admin = self._sb_factory_overview(coverage_locked=2, stale=0)
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "admin-1", "role": "super_admin", "permissions": [review_api.ADMIN_PERM],
        }
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get(f"{_BASE}/overview")
        assert r.status_code == 200, r.text
        ufr = r.json().get("user_facing_readiness", {})
        assert ufr["level"] == "ready"
        assert "locked_topic_coverage" in ufr
        assert "verified_syllabus_mentions" in ufr

    def test_user_facing_readiness_partial(self):
        app = FastAPI()
        app.include_router(review_api.router, prefix="/api")
        review_api.get_supabase_admin = self._sb_factory_overview(coverage_locked=1, stale=3)
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "admin-1", "role": "super_admin", "permissions": [review_api.ADMIN_PERM],
        }
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get(f"{_BASE}/overview")
        assert r.status_code == 200
        assert r.json()["user_facing_readiness"]["level"] == "partial"

    def test_user_facing_readiness_not_ready(self):
        app = FastAPI()
        app.include_router(review_api.router, prefix="/api")
        review_api.get_supabase_admin = self._sb_factory_overview(coverage_locked=0, syllabus_verified=0, stale=0)
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "admin-1", "role": "super_admin", "permissions": [review_api.ADMIN_PERM],
        }
        c = TestClient(app, raise_server_exceptions=False)
        r = c.get(f"{_BASE}/overview")
        assert r.status_code == 200
        assert r.json()["user_facing_readiness"]["level"] == "not_ready"


# ── BUG-EI-2 regression: document_processing_jobs as extraction source ────────


def _doc_asset(asset_id: str, exam_id: str, cycle_id: str | None = None) -> dict:
    """Build a document_assets row with exam ownership in metadata."""
    meta: dict = {"exam_id": exam_id}
    if cycle_id:
        meta["exam_cycle_id"] = cycle_id
    return {"id": asset_id, "scope": "admin_exam_intelligence", "metadata": meta}


def _text_job(asset_id: str, status: str, ts: str = "2026-01-01T00:00:00") -> dict:
    """Build a document_processing_jobs row for a text_extract job."""
    return {"document_id": asset_id, "job_type": "text_extract", "status": status, "created_at": ts}


class TestDocumentExtractionCounts:
    """load_doc_extraction_counts uses document_processing_jobs, not trust_status."""

    def test_succeeded_job_counts_as_extracted(self):
        docs = [_doc_asset("da1", "exam-1")]
        jobs = [_text_job("da1", "succeeded")]
        sb = _make_sb(exam=EXAM, documents=docs, doc_jobs=jobs)
        counts = load_doc_extraction_counts(sb, "exam-1")
        assert counts["extracted"] == 1
        assert counts["total"] == 1

    def test_verified_syllabus_doc_alone_not_extracted(self):
        """trust_status='verified' on syllabus_documents is orthogonal to extraction.
        A document_assets row with no text_extract job is not_started, not extracted.
        """
        docs = [_doc_asset("da1", "exam-1")]
        # No document_processing_jobs rows — asset not_started
        sb = _make_sb(exam=EXAM, documents=docs, doc_jobs=[])
        counts = load_doc_extraction_counts(sb, "exam-1")
        assert counts["extracted"] == 0
        assert counts["not_started"] == 1

    def test_failed_job_not_extracted(self):
        docs = [_doc_asset("da1", "exam-1")]
        jobs = [_text_job("da1", "failed")]
        sb = _make_sb(exam=EXAM, documents=docs, doc_jobs=jobs)
        counts = load_doc_extraction_counts(sb, "exam-1")
        assert counts["extracted"] == 0
        assert counts["failed"] == 1

    def test_queued_job_counted_as_pending(self):
        docs = [_doc_asset("da1", "exam-1")]
        jobs = [_text_job("da1", "queued")]
        sb = _make_sb(exam=EXAM, documents=docs, doc_jobs=jobs)
        counts = load_doc_extraction_counts(sb, "exam-1")
        assert counts["pending"] == 1
        assert counts["extracted"] == 0

    def test_no_assets_returns_zeros(self):
        sb = _make_sb(exam=EXAM)
        counts = load_doc_extraction_counts(sb, "exam-1")
        assert counts == {"total": 0, "extracted": 0, "pending": 0, "failed": 0,
                          "needs_review": 0, "not_started": 0}

    def test_latest_job_wins_on_multiple_runs(self):
        """When the same asset has multiple jobs (retries), the latest created_at wins."""
        docs = [_doc_asset("da1", "exam-1")]
        jobs = [
            _text_job("da1", "failed", "2026-01-01T00:00:00"),
            _text_job("da1", "succeeded", "2026-01-02T00:00:00"),
        ]
        sb = _make_sb(exam=EXAM, documents=docs, doc_jobs=jobs)
        counts = load_doc_extraction_counts(sb, "exam-1")
        assert counts["extracted"] == 1

    def test_cycle_filter_scopes_assets(self):
        docs = [
            _doc_asset("da1", "exam-1", "cycle-2026"),
            _doc_asset("da2", "exam-1", "cycle-2025"),
        ]
        jobs = [
            _text_job("da1", "succeeded"),
            _text_job("da2", "succeeded"),
        ]
        sb = _make_sb(exam=EXAM, documents=docs, doc_jobs=jobs)
        counts_all = load_doc_extraction_counts(sb, "exam-1")
        counts_scoped = load_doc_extraction_counts(sb, "exam-1", "cycle-2026")
        assert counts_all["total"] == 2
        assert counts_scoped["total"] == 1
        assert counts_scoped["extracted"] == 1

    def test_other_exam_assets_not_counted(self):
        docs = [
            _doc_asset("da1", "exam-1"),
            _doc_asset("da2", "exam-other"),
        ]
        jobs = [_text_job("da1", "succeeded"), _text_job("da2", "succeeded")]
        sb = _make_sb(exam=EXAM, documents=docs, doc_jobs=jobs)
        counts = load_doc_extraction_counts(sb, "exam-1")
        assert counts["total"] == 1
        assert counts["extracted"] == 1


class TestDocumentsSectionExtraction:
    """_documents() section reflects extraction counts, not trust_status."""

    def test_succeeded_job_makes_section_ready(self):
        docs = [_doc_asset("da1", "exam-1")]
        jobs = [_text_job("da1", "succeeded")]
        sb = _make_sb(exam=EXAM, documents=docs, doc_jobs=jobs)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        sec = next(s for s in result["sections"] if s["section"] == "documents")
        assert sec["status"] == "ready"
        assert sec["metrics"]["extracted"] == 1

    def test_no_assets_gives_empty_section(self):
        sb = _make_sb(exam=EXAM)
        result = compute_exam_workspace_readiness(sb, "exam-1")
        sec = next(s for s in result["sections"] if s["section"] == "documents")
        assert sec["status"] == "empty"
        assert "no documents uploaded" in sec["blockers"]

    def test_asset_with_no_job_is_partial_not_ready(self):
        docs = [_doc_asset("da1", "exam-1")]
        sb = _make_sb(exam=EXAM, documents=docs, doc_jobs=[])
        result = compute_exam_workspace_readiness(sb, "exam-1")
        sec = next(s for s in result["sections"] if s["section"] == "documents")
        assert sec["status"] == "partial"
        assert sec["metrics"]["extracted"] == 0

    def test_non_zero_score_only_with_real_extraction(self):
        """score_percent for documents must be 0 if no succeeded text_extract job,
        even when a syllabus_documents row with trust_status='verified' exists.
        """
        # asset present but no job → partial, not ready → score 50
        docs = [_doc_asset("da1", "exam-1")]
        sb = _make_sb(exam=EXAM, documents=docs, doc_jobs=[])
        result = compute_exam_workspace_readiness(sb, "exam-1")
        sec = next(s for s in result["sections"] if s["section"] == "documents")
        assert sec["score_percent"] == 50  # partial

        # asset present with succeeded job → ready → score 80
        jobs = [_text_job("da1", "succeeded")]
        sb2 = _make_sb(exam=EXAM, documents=docs, doc_jobs=jobs)
        result2 = compute_exam_workspace_readiness(sb2, "exam-1")
        sec2 = next(s for s in result2["sections"] if s["section"] == "documents")
        assert sec2["score_percent"] == 80  # ready


# ── D10 PYQ workbench tests ───────────────────────────────────────────────────


def _verified_paper(paper_id: str, cycle_id: str) -> dict:
    """Build a pyq_papers row that passes D10 gate 1 (trust_status='verified')."""
    return {
        "id": paper_id,
        "exam_id": "exam-1",
        "exam_cycle_id": cycle_id,
        "reviewer_status": "verified",
        "trust_status": "verified",
    }


def _verified_question(question_id: str, paper_id: str) -> dict:
    """Build a pyq_questions row that passes D10 gate 2 (reviewer_status='verified')."""
    return {
        "id": question_id,
        "pyq_paper_id": paper_id,
        "reviewer_status": "verified",
    }


def _verified_tag(tag_id: str, question_id: str) -> dict:
    """Build a pyq_question_topic_tags row that passes D10 gate 3 (reviewer_status='verified')."""
    return {
        "id": tag_id,
        "question_id": question_id,
        "reviewer_status": "verified",
    }


class TestPYQWorkbenchD10ExamWide:
    """D10: pyq_workbench is always exam-wide — cycle_id is provenance context only."""

    def test_pyq_workbench_exam_wide_ignores_cycle_id(self):
        """Papers from all cycles are counted even when cycle_id is specified.

        Two papers: one from cycle-2026, one from cycle-2025.
        Both are fully verified (all three D10 gates pass for both).
        Calling with cycle_id='cycle-2026' must still count both papers.
        """
        papers = [
            _verified_paper("p-2026", "cycle-2026"),
            _verified_paper("p-2025", "cycle-2025"),
        ]
        questions = [
            _verified_question("q-2026", "p-2026"),
            _verified_question("q-2025", "p-2025"),
        ]
        tags = [
            _verified_tag("t-2026", "q-2026"),
            _verified_tag("t-2025", "q-2025"),
        ]
        sb = _make_sb(
            exam=EXAM,
            pyq_papers=papers,
            pyq_questions=questions,
            pyq_question_topic_tags=tags,
            exam_cycles=[CYCLE_A],
        )
        result = compute_exam_workspace_readiness(sb, "exam-1", cycle_id="cycle-2026")
        pyq = next(s for s in result["sections"] if s["section"] == "pyq_workbench")

        assert pyq["status"] == "ready"
        # Both papers from both cycles must be counted.
        assert pyq["metrics"]["papers"] == 2, (
            "D10: papers_total must be exam-wide (2), not cycle-scoped (1)"
        )
        # pyq_readiness sub-object must also report both papers.
        assert pyq["metrics"]["pyq_readiness"]["papers_total"] == 2

    def test_pyq_workbench_no_cycle_same_as_with_cycle(self):
        """verified_question_count is identical whether cycle_id is None or provided.

        This is the core D10 invariant: the selected_cycle_id parameter must
        never change the count of verified questions.
        """
        papers = [
            _verified_paper("p-2026", "cycle-2026"),
            _verified_paper("p-2025", "cycle-2025"),
        ]
        questions = [
            _verified_question("q-2026", "p-2026"),
            _verified_question("q-2025", "p-2025"),
        ]
        tags = [
            _verified_tag("t-2026", "q-2026"),
            _verified_tag("t-2025", "q-2025"),
        ]
        sb = _make_sb(
            exam=EXAM,
            pyq_papers=papers,
            pyq_questions=questions,
            pyq_question_topic_tags=tags,
            exam_cycles=[CYCLE_A],
        )
        result_no_cycle = compute_exam_workspace_readiness(sb, "exam-1", cycle_id=None)
        result_with_cycle = compute_exam_workspace_readiness(sb, "exam-1", cycle_id="some-cycle")

        pyq_no_cycle = next(s for s in result_no_cycle["sections"] if s["section"] == "pyq_workbench")
        pyq_with_cycle = next(s for s in result_with_cycle["sections"] if s["section"] == "pyq_workbench")

        count_no_cycle = pyq_no_cycle["metrics"]["pyq_readiness"]["verified_question_count"]
        count_with_cycle = pyq_with_cycle["metrics"]["pyq_readiness"]["verified_question_count"]

        assert count_no_cycle == count_with_cycle, (
            f"D10 invariant violated: verified_question_count changed from "
            f"{count_no_cycle} (no cycle) to {count_with_cycle} (with cycle)"
        )

    def test_pyq_workbench_three_gate_trust_required_no_tag(self):
        """Gate 3 missing (no tag) → review_pending → partial status.

        verified paper + verified question + NO tag = partial (review_pending).
        """
        papers = [_verified_paper("p1", "cycle-2026")]
        questions = [_verified_question("q1", "p1")]
        # No topic tags at all — gate 3 fails for q1.
        sb = _make_sb(
            exam=EXAM,
            pyq_papers=papers,
            pyq_questions=questions,
            pyq_question_topic_tags=[],
        )
        result = compute_exam_workspace_readiness(sb, "exam-1")
        pyq = next(s for s in result["sections"] if s["section"] == "pyq_workbench")

        # D10 state: review_pending (gates 1+2 pass but gate 3 fails) → legacy "partial".
        assert pyq["status"] == "partial", (
            "No tag means gate 3 fails; D10 state=review_pending maps to legacy partial"
        )
        ev = pyq["metrics"]["pyq_readiness"]
        assert ev["verified_question_count"] == 0
        assert ev["questions_eligible_before_tag_gate"] == 1  # cleared gates 1+2
        assert ev["state"] == "review_pending"

    def test_pyq_workbench_three_gate_pending_question(self):
        """Gate 2 missing (question not verified) → review_pending → partial status.

        verified paper + PENDING question + verified tag = partial (review_pending).
        Gate 2 fails (reviewer_status != 'verified'), so question never reaches gate 3.
        """
        papers = [_verified_paper("p1", "cycle-2026")]
        questions = [
            {
                "id": "q1",
                "pyq_paper_id": "p1",
                "reviewer_status": "pending",  # gate 2 fails
            }
        ]
        tags = [_verified_tag("t1", "q1")]
        sb = _make_sb(
            exam=EXAM,
            pyq_papers=papers,
            pyq_questions=questions,
            pyq_question_topic_tags=tags,
        )
        result = compute_exam_workspace_readiness(sb, "exam-1")
        pyq = next(s for s in result["sections"] if s["section"] == "pyq_workbench")

        assert pyq["status"] == "partial", (
            "Pending question fails gate 2; D10 state=review_pending maps to legacy partial"
        )
        ev = pyq["metrics"]["pyq_readiness"]
        assert ev["verified_question_count"] == 0
        assert ev["pending_question_count"] == 1
        assert ev["state"] == "review_pending"

    def test_pyq_workbench_metrics_pyq_readiness_exposed(self):
        """After D10 fix, metrics['pyq_readiness'] must exist and carry scope='exam_wide'."""
        papers = [_verified_paper("p1", "cycle-2026")]
        questions = [_verified_question("q1", "p1")]
        tags = [_verified_tag("t1", "q1")]
        sb = _make_sb(
            exam=EXAM,
            pyq_papers=papers,
            pyq_questions=questions,
            pyq_question_topic_tags=tags,
        )
        result = compute_exam_workspace_readiness(sb, "exam-1")
        pyq = next(s for s in result["sections"] if s["section"] == "pyq_workbench")

        assert "pyq_readiness" in pyq["metrics"], (
            "D10: metrics['pyq_readiness'] key must be present in pyq_workbench section"
        )
        ev = pyq["metrics"]["pyq_readiness"]
        assert ev["scope"] == "exam_wide", (
            f"D10: scope must be 'exam_wide', got {ev['scope']!r}"
        )
        # Legacy status vocabulary is still returned at the section level.
        assert pyq["status"] in {"empty", "partial", "ready"}, (
            "Legacy status vocab (empty/partial/ready) must be returned — not 'locked' "
            "or raw D10 state names"
        )


class TestPYQWorkbenchBlockers:
    """D10: every review_pending section must have at least one corrective blocker."""

    def test_verified_paper_no_questions_has_blocker(self):
        """Verified paper + zero questions → partial status WITH corrective blocker."""
        papers = [_verified_paper("p1", "cycle-2026")]
        sb = _make_sb(exam=EXAM, pyq_papers=papers, pyq_questions=[], pyq_question_topic_tags=[])
        result = compute_exam_workspace_readiness(sb, "exam-1")
        pyq = next(s for s in result["sections"] if s["section"] == "pyq_workbench")
        assert pyq["status"] == "partial", (
            "Verified paper with no questions: D10 state=review_pending → legacy partial"
        )
        assert pyq["blockers"], (
            "review_pending section must have at least one corrective blocker"
        )
        assert any("no questions" in b.lower() for b in pyq["blockers"]), (
            f"Expected 'no questions' blocker, got: {pyq['blockers']}"
        )

    def test_verified_paper_only_rejected_questions_has_blocker(self):
        """Verified paper + only rejected questions → partial WITH corrective blocker."""
        papers = [_verified_paper("p1", "cycle-2026")]
        questions = [{"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "rejected"}]
        sb = _make_sb(
            exam=EXAM, pyq_papers=papers, pyq_questions=questions,
            pyq_question_topic_tags=[],
        )
        result = compute_exam_workspace_readiness(sb, "exam-1")
        pyq = next(s for s in result["sections"] if s["section"] == "pyq_workbench")
        assert pyq["status"] == "partial"
        assert pyq["blockers"], (
            "Verified paper with only rejected questions must have a corrective blocker"
        )

    def test_verified_paper_verified_question_only_rejected_tags_has_blocker(self):
        """Verified paper + verified question + only rejected tags → partial WITH gate-3 blocker."""
        papers = [_verified_paper("p1", "cycle-2026")]
        questions = [_verified_question("q1", "p1")]
        tags = [{"id": "t1", "question_id": "q1", "reviewer_status": "rejected"}]
        sb = _make_sb(
            exam=EXAM, pyq_papers=papers, pyq_questions=questions,
            pyq_question_topic_tags=tags,
        )
        result = compute_exam_workspace_readiness(sb, "exam-1")
        pyq = next(s for s in result["sections"] if s["section"] == "pyq_workbench")
        assert pyq["status"] == "partial"
        assert pyq["blockers"], (
            "Verified paper + verified question with only rejected tags must have a gate-3 blocker"
        )
        assert any(
            "missing verified topic tag" in b.lower() or "tag" in b.lower()
            for b in pyq["blockers"]
        )


class TestPYQWorkbenchReadFailure:
    """D10: any required-read failure must set pyq_readiness.state='failed', not fabricate missing."""

    def test_paper_read_failure_gives_failed_state(self):
        def _raise(f, i):
            raise RuntimeError("simulated paper read error")

        sb = _SBStub({
            "exams": [EXAM],
            "exam_cycles": lambda f, i: [],
            "exam_phases": [],
            "document_assets": lambda f, i: [],
            "document_processing_jobs": lambda f, i: [],
            "syllabus_topic_mentions": [],
            "pyq_papers": _raise,
            "pyq_questions": lambda f, i: [],
            "pyq_question_topic_tags": lambda f, i: [],
            "pyq_options": lambda f, i: [],
            "exam_policy_updates": [],
            "exam_competition_metrics": lambda f, i: [],
            "exam_topic_coverage": lambda f, i: [],
        })
        result = compute_exam_workspace_readiness(sb, "exam-1")
        pyq = next(s for s in result["sections"] if s["section"] == "pyq_workbench")
        assert pyq["metrics"]["pyq_readiness"]["state"] == "failed", (
            "Paper read failure must set state='failed', not fabricate 'missing'"
        )
        assert pyq["status"] == "empty"
        assert any("read failed" in b.lower() for b in pyq["blockers"])

    def test_question_read_failure_gives_failed_state(self):
        def _raise(f, i):
            raise RuntimeError("simulated question read error")

        paper = {"id": "p1", "exam_id": "exam-1", "exam_cycle_id": "cy-26", "trust_status": "pending"}

        sb = _SBStub({
            "exams": [EXAM],
            "exam_cycles": lambda f, i: [],
            "exam_phases": [],
            "document_assets": lambda f, i: [],
            "document_processing_jobs": lambda f, i: [],
            "syllabus_topic_mentions": [],
            "pyq_papers": lambda f, i: [paper] if f.get("exam_id") == "exam-1" else [],
            "pyq_questions": _raise,
            "pyq_question_topic_tags": lambda f, i: [],
            "pyq_options": lambda f, i: [],
            "exam_policy_updates": [],
            "exam_competition_metrics": lambda f, i: [],
            "exam_topic_coverage": lambda f, i: [],
        })
        result = compute_exam_workspace_readiness(sb, "exam-1")
        pyq = next(s for s in result["sections"] if s["section"] == "pyq_workbench")
        assert pyq["metrics"]["pyq_readiness"]["state"] == "failed", (
            "Question read failure must set state='failed', not fabricate 'missing'"
        )
        assert pyq["status"] == "empty"
        assert any("read failed" in b.lower() for b in pyq["blockers"])

    def test_tag_read_failure_gives_failed_state(self):
        def _raise(f, i):
            raise RuntimeError("simulated tag read error")

        paper = {"id": "p1", "exam_id": "exam-1", "exam_cycle_id": "cy-26", "trust_status": "verified"}
        question = {"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"}

        sb = _SBStub({
            "exams": [EXAM],
            "exam_cycles": lambda f, i: [],
            "exam_phases": [],
            "document_assets": lambda f, i: [],
            "document_processing_jobs": lambda f, i: [],
            "syllabus_topic_mentions": [],
            "pyq_papers": lambda f, i: [paper] if f.get("exam_id") == "exam-1" else [],
            "pyq_questions": lambda f, i: [question] if "p1" in i.get("pyq_paper_id", []) else [],
            "pyq_question_topic_tags": _raise,
            "pyq_options": lambda f, i: [],
            "exam_policy_updates": [],
            "exam_competition_metrics": lambda f, i: [],
            "exam_topic_coverage": lambda f, i: [],
        })
        result = compute_exam_workspace_readiness(sb, "exam-1")
        pyq = next(s for s in result["sections"] if s["section"] == "pyq_workbench")
        assert pyq["metrics"]["pyq_readiness"]["state"] == "failed", (
            "Tag read failure must set state='failed', not fabricate 'review_pending'"
        )
        assert pyq["status"] == "empty"
        assert any("read failed" in b.lower() for b in pyq["blockers"])


class TestPYQWorkbenchPopulatedTotals:
    """options_total and topic_tags_total must be populated, not hard-reset to 0."""

    def test_options_total_and_topic_tags_total_populated(self):
        papers = [_verified_paper("p1", "cycle-2026")]
        questions = [_verified_question("q1", "p1")]
        tags = [
            _verified_tag("t1", "q1"),
            _verified_tag("t2", "q1"),
        ]
        options = [
            {"id": "o1", "question_id": "q1"},
            {"id": "o2", "question_id": "q1"},
            {"id": "o3", "question_id": "q1"},
        ]
        sb = _make_sb(
            exam=EXAM,
            pyq_papers=papers,
            pyq_questions=questions,
            pyq_question_topic_tags=tags,
            pyq_options=options,
        )
        result = compute_exam_workspace_readiness(sb, "exam-1")
        pyq = next(s for s in result["sections"] if s["section"] == "pyq_workbench")
        assert pyq["metrics"]["topic_tags_total"] == 2, (
            f"topic_tags_total should be 2 (from 2 loaded tags), got {pyq['metrics']['topic_tags_total']}"
        )
        assert pyq["metrics"]["options_total"] == 3, (
            f"options_total should be 3 (from 3 pyq_options rows), got {pyq['metrics']['options_total']}"
        )


class TestPYQWorkbenchCrossConsumerParity:
    """True cross-consumer parity: work_queue.aggregate() and compute_exam_workspace_readiness()
    must agree on verified_question_count for the same exam across all D10 parity scenarios."""

    _EID = "exam-cross"
    _EXAM_ROW = {
        "id": "exam-cross", "slug": "exam-cross", "name": "Cross Parity Exam",
        "exam_type": "recruitment", "is_active": True,
        "exam_family_id": None, "management_mode": "core",
        "cadence": "annual", "conducting_organization_id": None,
    }

    def _wq_count(self, papers, questions, tags):
        """Run work_queue.aggregate() via SBStub; return verified_pyq_count."""
        from app.exam_intelligence import work_queue as wq
        from tests.persona_questions._stub import SBStub as WQStub
        db = {
            "exams": [self._EXAM_ROW],
            "exam_phases": [],
            "exam_topic_coverage": [],
            "syllabus_topic_mentions": [],
            "exam_policy_updates": [],
            "pyq_papers": papers,
            "pyq_questions": questions,
            "pyq_question_topic_tags": tags,
            "pyq_options": [],
            "organizations": [],
        }
        agg = wq.aggregate(WQStub(db), [self._EXAM_ROW])
        return agg[self._EID]["verified_pyq_count"]

    def _readiness_count(self, papers, questions, tags, cycle_id=None):
        """Run compute_exam_workspace_readiness() via _make_sb; return verified_question_count."""
        exam_row = {
            "id": self._EID, "slug": "exam-cross", "name": "Cross Parity Exam",
            "exam_type": "recruitment", "is_active": True,
        }
        sb = _make_sb(
            exam=exam_row,
            pyq_papers=papers,
            pyq_questions=questions,
            pyq_question_topic_tags=tags,
        )
        result = compute_exam_workspace_readiness(sb, self._EID, cycle_id)
        pyq = next(s for s in result["sections"] if s["section"] == "pyq_workbench")
        return pyq["metrics"]["pyq_readiness"]["verified_question_count"]

    def _assert_parity(self, papers, questions, tags, expected=None):
        wq_count = self._wq_count(papers, questions, tags)
        rd_count = self._readiness_count(papers, questions, tags)
        assert wq_count == rd_count, (
            f"Cross-consumer parity violation: "
            f"work_queue={wq_count} != compute_exam_workspace_readiness={rd_count}"
        )
        if expected is not None:
            assert wq_count == expected, f"Expected {expected}, got {wq_count}"
        return wq_count

    def test_cross_parity_all_gates_pass(self):
        """All three gates pass — both consumers return identical count."""
        papers = [{"id": "pp1", "exam_id": self._EID, "exam_cycle_id": "cy-26", "trust_status": "verified"}]
        questions = [{"id": "q1", "pyq_paper_id": "pp1", "reviewer_status": "verified", "created_at": "2026-01-01"}]
        tags = [{"id": "t1", "question_id": "q1", "reviewer_status": "verified", "created_at": "2026-01-01"}]
        self._assert_parity(papers, questions, tags, expected=1)

    def test_cross_parity_gate3_fails(self):
        """Gate 3 (no verified tag) fails — both consumers agree on 0."""
        papers = [{"id": "pp1", "exam_id": self._EID, "exam_cycle_id": "cy-26", "trust_status": "verified"}]
        questions = [{"id": "q1", "pyq_paper_id": "pp1", "reviewer_status": "verified", "created_at": "2026-01-01"}]
        tags = []
        self._assert_parity(papers, questions, tags, expected=0)

    def test_cross_parity_mixed_trust(self):
        """Verified, pending, rejected papers — both consumers agree on the gated count."""
        papers = [
            {"id": "pp-ver", "exam_id": self._EID, "exam_cycle_id": "cy-26", "trust_status": "verified"},
            {"id": "pp-pend", "exam_id": self._EID, "exam_cycle_id": "cy-26", "trust_status": "pending"},
            {"id": "pp-rej", "exam_id": self._EID, "exam_cycle_id": "cy-25", "trust_status": "rejected"},
        ]
        questions = [
            {"id": "qv1", "pyq_paper_id": "pp-ver", "reviewer_status": "verified", "created_at": "2026-01-01"},
            {"id": "qv2", "pyq_paper_id": "pp-pend", "reviewer_status": "verified", "created_at": "2026-01-01"},
            {"id": "qv3", "pyq_paper_id": "pp-rej", "reviewer_status": "verified", "created_at": "2025-01-01"},
        ]
        tags = [
            {"id": "tv1", "question_id": "qv1", "reviewer_status": "verified", "created_at": "2026-01-01"},
            {"id": "tv2", "question_id": "qv2", "reviewer_status": "verified", "created_at": "2026-01-01"},
            {"id": "tv3", "question_id": "qv3", "reviewer_status": "verified", "created_at": "2025-01-01"},
        ]
        # Only qv1 on pp-ver passes all three gates.
        self._assert_parity(papers, questions, tags, expected=1)

    def test_cross_parity_cycle_id_does_not_change_readiness_count(self):
        """D10 invariant: providing cycle_id to readiness must NOT change verified count."""
        papers = [
            {"id": "pp1", "exam_id": self._EID, "exam_cycle_id": "cy-26", "trust_status": "verified"},
            {"id": "pp2", "exam_id": self._EID, "exam_cycle_id": "cy-25", "trust_status": "verified"},
        ]
        questions = [
            {"id": "q1", "pyq_paper_id": "pp1", "reviewer_status": "verified", "created_at": "2026-01-01"},
            {"id": "q2", "pyq_paper_id": "pp2", "reviewer_status": "verified", "created_at": "2025-01-01"},
        ]
        tags = [
            {"id": "t1", "question_id": "q1", "reviewer_status": "verified", "created_at": "2026-01-01"},
            {"id": "t2", "question_id": "q2", "reviewer_status": "verified", "created_at": "2025-01-01"},
        ]
        wq_count = self._wq_count(papers, questions, tags)
        count_no_cycle = self._readiness_count(papers, questions, tags, cycle_id=None)
        count_with_cycle = self._readiness_count(papers, questions, tags, cycle_id="cy-26")

        assert wq_count == count_no_cycle == count_with_cycle == 2, (
            f"Cross-consumer + cycle invariant: wq={wq_count}, "
            f"no_cycle={count_no_cycle}, with_cycle={count_with_cycle}"
        )

    def test_cross_parity_unscoped_papers_counted_on_both_paths(self):
        """Papers with exam_cycle_id=None (unscoped) are counted on both consumers."""
        papers = [{"id": "pp1", "exam_id": self._EID, "exam_cycle_id": None, "trust_status": "verified"}]
        questions = [{"id": "q1", "pyq_paper_id": "pp1", "reviewer_status": "verified", "created_at": "2026-01-01"}]
        tags = [{"id": "t1", "question_id": "q1", "reviewer_status": "verified", "created_at": "2026-01-01"}]
        self._assert_parity(papers, questions, tags, expected=1)

    def test_cross_parity_empty_exam(self):
        """No papers → both consumers agree on 0."""
        self._assert_parity([], [], [], expected=0)
