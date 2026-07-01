"""Backend regression tests for pyq-options offset pagination (PR #820 amendment).

Verifies that `list_pyq_options` correctly paginates using .range() semantics:
- page 2 returns the next rows rather than page 1 again;
- question_id filter composes correctly with offset;
- limit bounds remain enforced (max 50);
- response total reflects full filtered count, not page slice.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub, _Query, _Exec


class _PaginatingQuery(_Query):
    """Extends SBStub query to implement .range() properly for pagination tests."""

    def __init__(self, name, db):
        super().__init__(name, db)
        self._range_start: int = 0
        self._range_end: int | None = None

    def range(self, start: int, end: int):
        self._range_start = start
        self._range_end = end
        return self

    def execute(self):
        rows_store = self.db.setdefault(self.name, [])
        matching = [r for r in rows_store if self._matches(r)]
        if self._order_key:
            matching.sort(
                key=lambda r: (r.get(self._order_key) if r.get(self._order_key) is not None else ""),
                reverse=self._desc,
            )
        total = len(matching)
        # Apply range-based slicing
        if self._range_end is not None:
            sliced = matching[self._range_start: self._range_end + 1]
        elif self._limit is not None:
            sliced = matching[self._range_start: self._range_start + self._limit]
        else:
            sliced = matching[self._range_start:]
        result = _Exec(sliced)
        result.count = total  # type: ignore[attr-defined]
        return result


class PaginatingSBStub(SBStub):
    """SBStub that returns PaginatingQuery instances."""

    def table(self, name: str):
        return _PaginatingQuery(name, self.db)


def _build_app(sb: PaginatingSBStub):
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1",
        "role": "super_admin",
        "permissions": [cms_api.PERM_CMS],
    }
    return app


def _make_options(question_id: str, count: int) -> list[dict]:
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return [
        {
            "id": f"opt-{question_id}-{i}",
            "question_id": question_id,
            "option_label": labels[i % len(labels)] + (str(i // len(labels)) if i >= len(labels) else ""),
            "option_text": f"Option {i}",
        }
        for i in range(count)
    ]


def test_pyq_options_page1_returns_first_50():
    """First page (offset=0) returns rows 0-49."""
    options = _make_options("q1", 80)
    sb = PaginatingSBStub({"pyq_options": options})
    client = TestClient(_build_app(sb))

    r = client.get("/api/admin/exam-intelligence-cms/pyq-options?limit=50&offset=0")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 80
    assert len(body["items"]) == 50
    # First item in page 1 is the first option (ordered by option_label)
    assert body["items"][0]["id"] == options[0]["id"]


def test_pyq_options_page2_returns_next_rows():
    """Page 2 (offset=50) returns rows 50-79, not page 1 again."""
    options = _make_options("q1", 80)
    sb = PaginatingSBStub({"pyq_options": options})
    client = TestClient(_build_app(sb))

    r1 = client.get("/api/admin/exam-intelligence-cms/pyq-options?limit=50&offset=0")
    r2 = client.get("/api/admin/exam-intelligence-cms/pyq-options?limit=50&offset=50")
    assert r1.status_code == 200
    assert r2.status_code == 200

    ids_p1 = {item["id"] for item in r1.json()["items"]}
    ids_p2 = {item["id"] for item in r2.json()["items"]}

    # Pages must not overlap
    assert ids_p1.isdisjoint(ids_p2), "Page 1 and page 2 share rows — offset not applied"
    assert len(ids_p2) == 30  # 80 - 50
    assert r2.json()["total"] == 80


def test_pyq_options_question_id_filter_composes_with_offset():
    """question_id filter and offset compose correctly."""
    options_q1 = _make_options("q1", 60)
    options_q2 = _make_options("q2", 10)
    sb = PaginatingSBStub({"pyq_options": options_q1 + options_q2})
    client = TestClient(_build_app(sb))

    # Page 1 for q1
    r1 = client.get("/api/admin/exam-intelligence-cms/pyq-options?question_id=q1&limit=50&offset=0")
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["total"] == 60  # q1 only
    assert len(body1["items"]) == 50
    assert all(item["question_id"] == "q1" for item in body1["items"])

    # Page 2 for q1
    r2 = client.get("/api/admin/exam-intelligence-cms/pyq-options?question_id=q1&limit=50&offset=50")
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["total"] == 60
    assert len(body2["items"]) == 10  # remaining 10
    assert all(item["question_id"] == "q1" for item in body2["items"])

    # q2 is entirely separate
    r_q2 = client.get("/api/admin/exam-intelligence-cms/pyq-options?question_id=q2&limit=50&offset=0")
    assert r_q2.json()["total"] == 10
    assert len(r_q2.json()["items"]) == 10


def test_pyq_options_limit_bound_enforced():
    """limit is capped at 50 by the endpoint schema (ge=1, le=50)."""
    options = _make_options("q1", 100)
    sb = PaginatingSBStub({"pyq_options": options})
    client = TestClient(_build_app(sb))

    # limit=51 should be rejected by FastAPI validation
    r = client.get("/api/admin/exam-intelligence-cms/pyq-options?limit=51")
    assert r.status_code == 422


def test_pyq_options_total_reflects_full_count_not_page():
    """total in response is the full filtered count, not just the page slice."""
    options = _make_options("q1", 75)
    sb = PaginatingSBStub({"pyq_options": options})
    client = TestClient(_build_app(sb))

    r = client.get("/api/admin/exam-intelligence-cms/pyq-options?limit=50&offset=0")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 75
    assert len(body["items"]) == 50  # only page slice returned
