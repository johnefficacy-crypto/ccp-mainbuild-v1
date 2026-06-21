"""PR1: Exam Workspace context endpoint tests.

GET /api/admin/exam-intelligence/workspace/{exam_id}/context
    ?cycle_id=<uuid optional>

Covers:
- happy path: valid exam_id returns {exam, cycles[], cycle:null, phases[], readiness:null}
- with cycle_id: cycle populated, phases scoped to that cycle
- cycle_id belonging to another exam → 422
- unknown exam_id → 404
- unknown cycle_id → 404
- cycles list ordered newest first (by year desc)
- phases correctly scoped by cycle_id presence
"""
from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as review_api
from app.core.auth import get_current_user

_BASE = "/api/admin/exam-intelligence"

# ── Fixtures ──────────────────────────────────────────────────────────────────

EXAM = {"id": "exam-1", "slug": "ssc-cgl", "name": "SSC CGL", "exam_type": "recruitment", "is_active": True}
EXAM_WITH_REFS = {
    **EXAM,
    "conducting_organization_id": "org-1",
    "exam_family_id": "fam-1",
}
EXAM_2 = {"id": "exam-2", "slug": "ibps-po", "name": "IBPS PO", "exam_type": "recruitment", "is_active": True}
ORGANIZATION = {"id": "org-1", "name": "Staff Selection Commission", "type": "central", "trust_tier": "verified"}
FAMILY = {"id": "fam-1", "name": "SSC", "slug": "ssc"}

CYCLES = [
    {"id": "cycle-2026", "exam_id": "exam-1", "year": 2026, "cycle_name": "2026", "status": "open"},
    {"id": "cycle-2025", "exam_id": "exam-1", "year": 2025, "cycle_name": "2025", "status": "completed"},
    {"id": "cycle-2024", "exam_id": "exam-1", "year": 2024, "cycle_name": "2024", "status": "completed"},
]

PHASES = [
    {"id": "ph-1", "exam_id": "exam-1", "exam_cycle_id": "cycle-2026", "phase_name": "Tier I", "phase_order": 1},
    {"id": "ph-2", "exam_id": "exam-1", "exam_cycle_id": "cycle-2026", "phase_name": "Tier II", "phase_order": 2},
    {"id": "ph-3", "exam_id": "exam-1", "exam_cycle_id": "cycle-2025", "phase_name": "Tier I", "phase_order": 1},
]

CYCLE_OTHER_EXAM = {"id": "cycle-other", "exam_id": "exam-2", "year": 2026, "cycle_name": "2026"}

# ── Client helper ─────────────────────────────────────────────────────────────


def _client(sb_factory):
    app = FastAPI()
    app.include_router(review_api.router, prefix="/api")
    review_api.get_supabase_admin = sb_factory
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": "super_admin", "permissions": [review_api.ADMIN_PERM],
    }
    return TestClient(app, raise_server_exceptions=False)


def _make_sb(exam=EXAM, cycles=None, phases=None, cycle_global=None, organization=ORGANIZATION, family=FAMILY):
    """Build a MagicMock supabase that responds to the workspace context queries."""
    if cycles is None:
        cycles = CYCLES
    if phases is None:
        phases = PHASES

    sb = MagicMock()

    def _table_side_effect(name):
        tbl = MagicMock()

        def _select_chain(*args, **kwargs):
            q = MagicMock()
            q.eq.return_value = q
            q.order.return_value = q
            q.limit.return_value = q

            def _execute():
                res = MagicMock()
                if name == "exams":
                    res.data = [exam] if exam else []
                elif name == "exam_cycles":
                    if cycle_global is not None:
                        # First call: exam-scoped cycles; second: global lookup
                        res.data = cycles
                    else:
                        res.data = cycles
                elif name == "exam_phases":
                    res.data = phases
                elif name == "organizations":
                    res.data = [organization] if organization else []
                elif name == "exam_families":
                    res.data = [family] if family else []
                else:
                    res.data = []
                return res

            q.execute.side_effect = _execute
            return q

        tbl.select.side_effect = _select_chain
        return tbl

    sb.table.side_effect = _table_side_effect
    return lambda: sb


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestWorkspaceContextHappyPath:
    def test_returns_exam(self):
        c = _client(_make_sb())
        r = c.get(f"{_BASE}/workspace/exam-1/context")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["exam"]["id"] == "exam-1"
        assert body["exam"]["name"] == "SSC CGL"

    def test_cycle_null_when_no_cycle_id(self):
        c = _client(_make_sb())
        r = c.get(f"{_BASE}/workspace/exam-1/context")
        assert r.status_code == 200
        assert r.json()["cycle"] is None

    def test_cycles_list_returned(self):
        c = _client(_make_sb())
        r = c.get(f"{_BASE}/workspace/exam-1/context")
        assert r.status_code == 200
        body = r.json()
        assert len(body["cycles"]) == len(CYCLES)

    def test_phases_returned(self):
        c = _client(_make_sb())
        r = c.get(f"{_BASE}/workspace/exam-1/context")
        assert r.status_code == 200
        assert len(r.json()["phases"]) == len(PHASES)

    def test_readiness_always_null(self):
        c = _client(_make_sb())
        r = c.get(f"{_BASE}/workspace/exam-1/context")
        assert r.status_code == 200
        assert r.json()["readiness"] is None


class TestWorkspaceContextResolvedObjects:
    def test_includes_organization_when_exam_links_conducting_organization(self):
        c = _client(_make_sb(exam=EXAM_WITH_REFS))
        r = c.get(f"{_BASE}/workspace/exam-1/context")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["organization"] == ORGANIZATION
        assert body["exam"]["id"] == "exam-1"
        assert body["cycle"] is None
        assert body["cycles"] == CYCLES
        assert body["phases"] == PHASES
        assert body["readiness"] is None

    def test_includes_family_when_exam_links_exam_family(self):
        c = _client(_make_sb(exam=EXAM_WITH_REFS))
        r = c.get(f"{_BASE}/workspace/exam-1/context")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["family"] == FAMILY
        assert body["exam"]["id"] == "exam-1"
        assert body["cycle"] is None
        assert body["cycles"] == CYCLES
        assert body["phases"] == PHASES
        assert body["readiness"] is None

    def test_organization_null_when_no_organization_linked(self):
        c = _client(_make_sb(exam={**EXAM, "exam_family_id": "fam-1"}))
        r = c.get(f"{_BASE}/workspace/exam-1/context")
        assert r.status_code == 200, r.text
        assert r.json()["organization"] is None

    def test_family_null_when_no_family_linked(self):
        c = _client(_make_sb(exam={**EXAM, "conducting_organization_id": "org-1"}))
        r = c.get(f"{_BASE}/workspace/exam-1/context")
        assert r.status_code == 200, r.text
        assert r.json()["family"] is None


class TestWorkspaceContextWithCycleId:
    def _sb_with_cycle(self):
        """Stub that correctly scopes phases to cycle-2026."""
        sb = MagicMock()

        def _table(name):
            tbl = MagicMock()

            def _select_chain(*a, **kw):
                q = MagicMock()
                q.order.return_value = q
                q.limit.return_value = q

                _eq_filters: dict = {}

                def _eq(k, v):
                    _eq_filters[k] = v
                    q.eq.return_value = q
                    return q

                q.eq.side_effect = _eq

                def _execute():
                    res = MagicMock()
                    if name == "exams":
                        res.data = [EXAM]
                    elif name == "exam_cycles":
                        if _eq_filters.get("id") == "cycle-2026":
                            res.data = [CYCLES[0]]
                        else:
                            res.data = CYCLES
                    elif name == "exam_phases":
                        cid = _eq_filters.get("exam_cycle_id")
                        if cid:
                            res.data = [p for p in PHASES if p["exam_cycle_id"] == cid]
                        else:
                            res.data = PHASES
                    else:
                        res.data = []
                    return res

                q.execute.side_effect = _execute
                return q

            tbl.select.side_effect = _select_chain
            return tbl

        sb.table.side_effect = _table
        return lambda: sb

    def test_cycle_populated(self):
        c = _client(self._sb_with_cycle())
        r = c.get(f"{_BASE}/workspace/exam-1/context?cycle_id=cycle-2026")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["cycle"]["id"] == "cycle-2026"

    def test_phases_scoped_to_cycle(self):
        c = _client(self._sb_with_cycle())
        r = c.get(f"{_BASE}/workspace/exam-1/context?cycle_id=cycle-2026")
        assert r.status_code == 200
        phases = r.json()["phases"]
        assert all(p["exam_cycle_id"] == "cycle-2026" for p in phases)
        assert len(phases) == 2  # ph-1 and ph-2

    def test_phases_not_scoped_without_cycle_id(self):
        c = _client(self._sb_with_cycle())
        r = c.get(f"{_BASE}/workspace/exam-1/context")
        assert r.status_code == 200
        phases = r.json()["phases"]
        assert len(phases) == len(PHASES)  # all phases


class TestWorkspaceContextErrors:
    def _sb_unknown_exam(self):
        sb = MagicMock()

        def _table(name):
            tbl = MagicMock()
            q = MagicMock()
            q.eq.return_value = q
            q.order.return_value = q
            q.limit.return_value = q
            res = MagicMock()
            res.data = []
            q.execute.return_value = res
            tbl.select.return_value = q
            return tbl

        sb.table.side_effect = _table
        return lambda: sb

    def test_unknown_exam_id_404(self):
        c = _client(self._sb_unknown_exam())
        r = c.get(f"{_BASE}/workspace/nonexistent/context")
        assert r.status_code == 404
        assert "exam not found" in r.json().get("detail", "").lower()

    def _sb_unknown_cycle(self):
        """Exam exists, but cycle is not found anywhere."""
        sb = MagicMock()

        def _table(name):
            tbl = MagicMock()

            def _sel(*a, **kw):
                q = MagicMock()
                q.order.return_value = q
                q.limit.return_value = q

                _eq_data: dict = {}

                def _eq(k, v):
                    _eq_data[k] = v
                    return q

                q.eq.side_effect = _eq

                def _exec():
                    res = MagicMock()
                    if name == "exams":
                        res.data = [EXAM]
                    elif name == "exam_cycles":
                        # No cycles — neither scoped nor global
                        res.data = []
                    else:
                        res.data = []
                    return res

                q.execute.side_effect = _exec
                return q

            tbl.select.side_effect = _sel
            return tbl

        sb.table.side_effect = _table
        return lambda: sb

    def test_unknown_cycle_id_404(self):
        c = _client(self._sb_unknown_cycle())
        r = c.get(f"{_BASE}/workspace/exam-1/context?cycle_id=no-such-cycle")
        assert r.status_code == 404
        assert "cycle not found" in r.json().get("detail", "").lower()

    def _sb_cycle_wrong_exam(self):
        """Exam exists; cycle exists but belongs to a different exam."""
        sb = MagicMock()

        def _table(name):
            tbl = MagicMock()

            def _sel(*a, **kw):
                q = MagicMock()
                q.order.return_value = q
                q.limit.return_value = q

                _eq_data: dict = {}

                def _eq(k, v):
                    _eq_data[k] = v
                    return q

                q.eq.side_effect = _eq

                def _exec():
                    res = MagicMock()
                    if name == "exams":
                        res.data = [EXAM]
                    elif name == "exam_cycles":
                        eid = _eq_data.get("exam_id")
                        cid = _eq_data.get("id")
                        if cid == "cycle-other":
                            # global lookup returns the foreign cycle
                            res.data = [CYCLE_OTHER_EXAM]
                        elif eid == "exam-1":
                            # exam-scoped cycles — does not contain cycle-other
                            res.data = []
                        else:
                            res.data = []
                    else:
                        res.data = []
                    return res

                q.execute.side_effect = _exec
                return q

            tbl.select.side_effect = _sel
            return tbl

        sb.table.side_effect = _table
        return lambda: sb

    def test_cycle_from_another_exam_422(self):
        c = _client(self._sb_cycle_wrong_exam())
        r = c.get(f"{_BASE}/workspace/exam-1/context?cycle_id=cycle-other")
        assert r.status_code == 422
        assert "does not belong to exam" in r.json().get("detail", "").lower()


class TestCyclesOrdering:
    def test_cycles_returned_newest_first(self):
        """cycles[] should be ordered by year desc (DB orders them; we verify endpoint passes through)."""
        # Stub returns cycles already ordered newest-first (DB does it via order clause)
        ordered = [
            {"id": "c3", "exam_id": "exam-1", "year": 2026, "cycle_name": "2026"},
            {"id": "c2", "exam_id": "exam-1", "year": 2025, "cycle_name": "2025"},
            {"id": "c1", "exam_id": "exam-1", "year": 2024, "cycle_name": "2024"},
        ]

        sb = MagicMock()

        def _table(name):
            tbl = MagicMock()
            q = MagicMock()
            q.eq.return_value = q
            q.order.return_value = q
            q.limit.return_value = q
            res = MagicMock()
            if name == "exams":
                res.data = [EXAM]
            elif name == "exam_cycles":
                res.data = ordered
            else:
                res.data = []
            q.execute.return_value = res
            tbl.select.return_value = q
            return tbl

        sb.table.side_effect = _table

        c = _client(lambda: sb)
        r = c.get(f"{_BASE}/workspace/exam-1/context")
        assert r.status_code == 200
        years = [x["year"] for x in r.json()["cycles"]]
        assert years == sorted(years, reverse=True)
