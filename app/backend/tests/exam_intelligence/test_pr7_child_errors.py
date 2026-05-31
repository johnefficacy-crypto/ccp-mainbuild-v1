"""PR7-fix: per-child error surfacing with atomic rollback.

Verifies:
- create_pyq_question: options insert failure → ok=False + question row deleted
- create_pyq_question: success path unaffected
- bulk_import: row with bad options → row reported failed, parent deleted,
  surrounding rows committed cleanly
- bulk_import 50 rows, row 17 bad option → rows 1-16 + 18-50 committed
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub
from tests.persona_questions._stub import SBStub, _Query

_BASE = "/api/admin/exam-intelligence-cms"


# ── Stub that can simulate a failing options insert ───────────────────────────


class _FailOnTableQuery(_Query):
    """Raises on insert into `fail_table` (set per test)."""

    def __init__(self, name, db, *, fail_table: str):
        super().__init__(name, db)
        self._fail_table = fail_table

    def execute(self):
        if self._pending_insert is not None and self.name == self._fail_table:
            raise RuntimeError(f"simulated insert failure on {self.name}")
        return super().execute()


class FailSBStub(TaxSBStub):
    def __init__(self, db, *, fail_table: str):
        super().__init__(db)
        self._fail_table = fail_table

    def table(self, name: str):
        return _FailOnTableQuery(name, self.db, fail_table=self._fail_table)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _seed():
    return {
        "pyq_papers": [{"id": "p1", "exam_id": "e1"}],
        "exams": [{"id": "e1"}],
        "pyq_questions": [],
        "pyq_options": [],
        "admin_audit_logs": [],
    }


def _opts():
    return [{"option_label": lbl, "option_text": f"option {lbl}", "is_correct": lbl == "A"}
            for lbl in "ABCD"]


def _client(sb):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": "super_admin", "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


# ── create_pyq_question tests ─────────────────────────────────────────────────


class TestCreatePyqQuestion:
    def test_success_path_ok_true(self):
        sb = TaxSBStub(_seed())
        r = _client(sb).post(f"{_BASE}/pyq-questions", json={
            "reason": "create test question",
            "payload": {"pyq_paper_id": "p1", "question_text": "Q?",
                        "question_type": "mcq", "options": _opts()},
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert len(sb.db["pyq_questions"]) == 1
        assert len(sb.db["pyq_options"]) == 4

    def test_options_failure_returns_ok_false(self):
        sb = FailSBStub(_seed(), fail_table="pyq_options")
        r = _client(sb).post(f"{_BASE}/pyq-questions", json={
            "reason": "create with failing options",
            "payload": {"pyq_paper_id": "p1", "question_text": "Q?",
                        "question_type": "mcq", "options": _opts()},
        })
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is False
        assert "child_errors" in body
        assert len(body["child_errors"]) > 0

    def test_options_failure_rolls_back_question_row(self):
        sb = FailSBStub(_seed(), fail_table="pyq_options")
        _client(sb).post(f"{_BASE}/pyq-questions", json={
            "reason": "rollback test",
            "payload": {"pyq_paper_id": "p1", "question_text": "Q?",
                        "question_type": "mcq", "options": _opts()},
        })
        # Question must have been deleted — no orphan rows
        assert len(sb.db["pyq_questions"]) == 0
        assert len(sb.db["pyq_options"]) == 0

    def test_options_failure_child_errors_contain_labels(self):
        sb = FailSBStub(_seed(), fail_table="pyq_options")
        r = _client(sb).post(f"{_BASE}/pyq-questions", json={
            "reason": "check child_errors labels",
            "payload": {"pyq_paper_id": "p1", "question_text": "Q?",
                        "question_type": "mcq", "options": _opts()},
        })
        body = r.json()
        assert body["ok"] is False
        labels = [e.get("label") for e in body["child_errors"]]
        assert any(lbl in labels for lbl in ("A", "B", "C", "D"))

    def test_no_options_still_ok(self):
        sb = TaxSBStub(_seed())
        r = _client(sb).post(f"{_BASE}/pyq-questions", json={
            "reason": "no options",
            "payload": {"pyq_paper_id": "p1", "question_text": "Q?", "question_type": "mcq"},
        })
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert len(sb.db["pyq_questions"]) == 1


# ── bulk_import inline children tests ────────────────────────────────────────


class TestBulkImportChildErrors:
    def _rows(self, n: int) -> list[dict]:
        return [{"pyq_paper_id": "p1", "question_text": f"Q{i}?",
                 "question_type": "mcq", "options": _opts()} for i in range(n)]

    def test_clean_bulk_unaffected(self):
        sb = TaxSBStub(_seed())
        r = _client(sb).post(f"{_BASE}/bulk-import", json={
            "reason": "clean bulk", "entity": "pyq-questions", "rows": self._rows(5),
        })
        assert r.status_code == 200
        body = r.json()
        assert body["ok_count"] == 5 and body["error_count"] == 0

    def test_row_with_failed_options_reported_as_error(self):
        sb = FailSBStub(_seed(), fail_table="pyq_options")
        r = _client(sb).post(f"{_BASE}/bulk-import", json={
            "reason": "options fail all rows", "entity": "pyq-questions",
            "rows": self._rows(3),
        })
        assert r.status_code == 200
        body = r.json()
        assert body["error_count"] == 3
        for res in body["results"]:
            assert res["ok"] is False
            assert "child_errors" in res

    def test_row_17_fails_rest_committed(self):
        """50 rows; row index 16 (1-based row 17) fails options; others succeed."""

        # Use a counter that only increments forward (not affected by rollback deletes).
        state = {"insert_count": 0, "fail_id": None}

        class _Row17FailQuery(_Query):
            def execute(self):
                if self._pending_insert is not None and self.name == "pyq_questions":
                    res = super().execute()
                    state["insert_count"] += 1
                    if state["insert_count"] == 17:
                        state["fail_id"] = (res.data or [{}])[0].get("id")
                    return res
                if self._pending_insert is not None and self.name == "pyq_options":
                    payload = self._pending_insert
                    items = payload if isinstance(payload, list) else [payload]
                    qid = items[0].get("question_id") if items else None
                    if qid and qid == state["fail_id"]:
                        raise RuntimeError("simulated option failure for row 17")
                return super().execute()

        class Row17FailSB(TaxSBStub):
            def table(self, name):
                return _Row17FailQuery(name, self.db)

        sb = Row17FailSB(_seed())
        rows = self._rows(50)
        r = _client(sb).post(f"{_BASE}/bulk-import", json={
            "reason": "row 17 bad", "entity": "pyq-questions", "rows": rows,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["ok_count"] == 49
        assert body["error_count"] == 1
        bad = [x for x in body["results"] if not x["ok"]]
        assert len(bad) == 1 and bad[0]["index"] == 16
        assert "child_errors" in bad[0]

    def test_failed_row_parent_deleted(self):
        sb = FailSBStub(_seed(), fail_table="pyq_options")
        _client(sb).post(f"{_BASE}/bulk-import", json={
            "reason": "rollback check", "entity": "pyq-questions",
            "rows": self._rows(2),
        })
        # All question rows should have been rolled back
        assert len(sb.db["pyq_questions"]) == 0

    def test_3_of_4_options_fail_still_rolls_back(self):
        """Even one child failure must abort the whole row."""

        class _PartialFailQuery(_Query):
            _count: dict = {}

            def execute(self):
                if self._pending_insert is not None and self.name == "pyq_options":
                    payload = self._pending_insert
                    items = payload if isinstance(payload, list) else [payload]
                    # Fail on any batch that has options (simulates a DB constraint error
                    # after 0 options have been inserted individually).
                    # Here options are batch-inserted so the whole batch fails.
                    raise RuntimeError("partial option failure")
                return super().execute()

        class PartialSB(TaxSBStub):
            def table(self, name):
                return _PartialFailQuery(name, self.db)

        sb = PartialSB(_seed())
        r = _client(sb).post(f"{_BASE}/pyq-questions", json={
            "reason": "partial fail",
            "payload": {"pyq_paper_id": "p1", "question_text": "Q?",
                        "question_type": "mcq", "options": _opts()},
        })
        body = r.json()
        assert body["ok"] is False
        assert len(sb.db["pyq_questions"]) == 0
