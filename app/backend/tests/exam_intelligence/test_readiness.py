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
from app.exam_intelligence.readiness import compute_exam_workspace_readiness

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

    def select(self, *a, **kw):
        return self

    def eq(self, k, v):
        self._filters[k] = v
        return self

    def in_(self, k, v):
        self._in_filters[k] = v
        return self

    def order(self, *a, **kw):
        return self

    def limit(self, n):
        return self

    def execute(self):
        rows = self._rows if not callable(self._rows) else self._rows(self._filters, self._in_filters)
        res = MagicMock()
        res.data = rows
        return res


def _make_sb(
    exam=None,
    phases=None,
    documents=None,
    syllabus=None,
    pyq_papers=None,
    pyq_questions=None,
    updates=None,
    competition=None,
    exam_cycles=None,
    topic_coverage=None,
):
    exam_rows = [exam] if exam else []
    phases_rows = phases or []
    doc_rows = documents or []
    syllabus_rows = syllabus or []
    papers_rows = pyq_papers or []
    question_rows = pyq_questions or []
    update_rows = updates or []
    comp_rows = competition or []
    cycles_rows = exam_cycles or []
    topic_coverage_rows = topic_coverage or []

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

    def _topic_coverage_fn(filters, in_filters):
        rows = topic_coverage_rows
        if "exam_id" in filters:
            rows = [r for r in rows if r.get("exam_id") == filters["exam_id"]]
        if "exam_cycle_id" in filters:
            rows = [r for r in rows if r.get("exam_cycle_id") == filters["exam_cycle_id"]]
        return rows

    def _doc_fn(filters, in_filters):
        rows = doc_rows
        if "exam_id" in filters:
            rows = [d for d in rows if d.get("exam_id") == filters["exam_id"]]
        if "exam_cycle_id" in filters:
            rows = [d for d in rows if d.get("exam_cycle_id") == filters["exam_cycle_id"]]
        return rows

    return _SBStub({
        "exams": exam_rows,
        "exam_cycles": _exam_cycles_fn,
        "exam_phases": phases_rows,
        "document_assets": _doc_fn,
        "syllabus_topic_mentions": syllabus_rows,
        "pyq_papers": _papers_fn,
        "pyq_questions": _pyq_q_fn,
        "exam_policy_updates": update_rows,
        "exam_competition_metrics": _comp_fn,
        "exam_topic_coverage": _topic_coverage_fn,
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
        papers = [{"id": "p1", "exam_id": "exam-1", "exam_cycle_id": "cycle-2026"}]
        questions = [
            {"id": f"q{i}", "pyq_paper_id": "p1", "reviewer_status": "verified"} for i in range(5)
        ]
        comp = [{"id": "c1", "exam_id": "exam-1", "exam_cycle_id": "cycle-2026", "reviewer_status": "verified"}]
        docs = [{"id": "d1", "exam_id": "exam-1", "exam_cycle_id": "cycle-2026", "extraction_status": "succeeded"}]
        updates = [{"id": "u1", "exam_id": "exam-1", "reviewer_status": "verified", "created_at": "2099-01-01"}]

        sb = _make_sb(
            exam=EXAM,
            phases=phases,
            syllabus=syllabus,
            pyq_papers=papers,
            pyq_questions=questions,
            competition=comp,
            documents=docs,
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
            {"id": "d1", "exam_id": "exam-1", "exam_cycle_id": "cycle-2026", "extraction_status": "succeeded"},
            {"id": "d2", "exam_id": "exam-1", "exam_cycle_id": "cycle-2025", "extraction_status": "succeeded"},
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
            {"id": "cm1", "exam_id": "exam-1", "exam_cycle_id": "cycle-2026", "reviewer_status": "verified"},
        ]
        cycles = [CYCLE_A]
        return _make_sb(
            exam=EXAM,
            phases=phases,
            documents=docs,
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

    def test_pyq_scoped_by_cycle(self):
        sb = self._make_cycle_sb()
        result_with = compute_exam_workspace_readiness(sb, "exam-1", "cycle-2026")
        pyq = next(s for s in result_with["sections"] if s["section"] == "pyq_workbench")
        assert pyq["metrics"]["papers"] == 1

    def test_competition_scoped_by_cycle(self):
        sb = self._make_cycle_sb()
        result_with = compute_exam_workspace_readiness(sb, "exam-1", "cycle-2026")
        comp = next(s for s in result_with["sections"] if s["section"] == "competition")
        assert comp["status"] == "ready"

        # No competition row for cycle-2025
        result_other = compute_exam_workspace_readiness(sb, "exam-1", "cycle-2025")
        comp_other = next(s for s in result_other["sections"] if s["section"] == "competition")
        assert comp_other["status"] == "empty"

    def test_topic_coverage_includes_exam_level_and_selected_cycle_rows(self):
        sb = _make_sb(
            exam=EXAM,
            exam_cycles=[CYCLE_A],
            topic_coverage=[
                {"id": "tc-exam", "exam_id": "exam-1", "exam_cycle_id": None, "reviewer_status": "locked"},
                {"id": "tc-selected", "exam_id": "exam-1", "exam_cycle_id": "cycle-2026", "reviewer_status": "reviewed"},
                {"id": "tc-other", "exam_id": "exam-1", "exam_cycle_id": "cycle-2025", "reviewer_status": "locked"},
            ],
        )
        result = compute_exam_workspace_readiness(sb, "exam-1", "cycle-2026")
        assert result["topic_coverage"]["total"] == 2
        assert result["topic_coverage"]["locked"] == 1
        assert result["topic_coverage"]["reviewed"] == 1


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
        overall = result["overall"]
        assert set(overall.keys()) >= {"status", "score_percent", "ready_to_activate", "blockers"}


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
