"""``GET /admin/exam-intelligence/topic-coverage`` must page past ``db-max-rows``.

The route used to read ``.limit(limit + offset)`` and slice the window out in
Python. PostgREST caps every select at ``db-max-rows``
(``max_rows = 1000``, ``app/supabase/config.toml:18``), so any request whose
``limit + offset`` exceeded 1000 got 1000 rows back, the Python slice landed
past the end, and the caller received an empty page — with no error and
nothing in the response saying the result had been truncated. Observed live on
2026-09-12: a client paging UPSC CSE Mains coverage stopped at exactly 1000 of
1320 rows.

``CappingSB`` models that server cap AND honours ``.range()``, so it
reproduces the truncation and proves the range-based read defeats it.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as admin_module
from app.core.auth import get_current_user
from tests.exam_intelligence._capping_stub import CappingSB

SERVER_CAP = 1000
TOTAL_ROWS = 1320  # UPSC CSE Mains coverage-row count on 2026-09-12


def _coverage_row(i: int) -> dict:
    # Zero-padded created_at gives a deterministic .order("created_at", desc=True):
    # row 1319 sorts first, row 0 last.
    return {
        "id": f"cov-{i:05d}",
        "exam_id": "e1",
        "exam_cycle_id": None,
        "exam_phase_id": "phase-mains",
        "section_id": None,
        "topic_id": f"t-{i:05d}",
        "coverage_depth": "core",
        "expected_difficulty": "medium",
        "exam_priority_score": 70.0,
        "is_high_yield": False,
        "confidence_score": 0.8,
        "source_basis": "pyq_frequency",
        "reviewer_status": "draft",
        "reviewed_at": None,
        "metadata": {"evidence_count": 3},
        "created_at": f"2026-01-01T00:{i:05d}Z",
    }


def _db() -> dict:
    return {
        "exam_topic_coverage": [_coverage_row(i) for i in range(TOTAL_ROWS)],
        "exams": [{"id": "e1", "slug": "upsc-cse", "name": "UPSC CSE"}],
        "topics": [],
        "subjects": [],
    }


def _build_app(sb: CappingSB) -> FastAPI:
    app = FastAPI()
    app.include_router(admin_module.router, prefix="/api")
    admin_module.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1",
        "role": "super_admin",
        "permissions": [admin_module.ADMIN_PERM],
    }
    return app


def _get(offset: int, limit: int = 50) -> dict:
    client = TestClient(_build_app(CappingSB(_db(), server_cap=SERVER_CAP)))
    r = client.get(
        "/api/admin/exam-intelligence/topic-coverage"
        f"?exam_id=e1&limit={limit}&offset={offset}"
    )
    assert r.status_code == 200, r.text
    return r.json()


def _expected_ids(offset: int, limit: int) -> list[str]:
    """created_at desc → highest index first."""
    ordered = [f"cov-{i:05d}" for i in range(TOTAL_ROWS - 1, -1, -1)]
    return ordered[offset : offset + limit]


def test_page_past_the_server_cap_returns_the_rows_that_exist():
    """offset 1100 sits past ``db-max-rows``. The old `.limit(limit + offset)`
    + Python-slice read returned zero items here; range paging returns the 50
    rows that actually exist."""
    body = _get(offset=1100)
    assert [row["id"] for row in body["items"]] == _expected_ids(1100, 50)
    assert len(body["items"]) == 50


def test_final_partial_page_past_the_cap():
    """1320 rows, offset 1300 → the last 20, not an empty page."""
    body = _get(offset=1300)
    assert [row["id"] for row in body["items"]] == _expected_ids(1300, 50)
    assert len(body["items"]) == 20


def test_page_below_the_cap_is_unaffected():
    body = _get(offset=900)
    assert [row["id"] for row in body["items"]] == _expected_ids(900, 50)


def test_first_page_response_shape_unchanged():
    """`items` + `count` keep their existing meaning for a first page:
    `count` is what the old `len(rows)` evaluated to (offset + rows walked)."""
    body = _get(offset=0)
    assert set(body) == {"items", "count", "total_count"}
    assert body["count"] == 50
    first = body["items"][0]
    assert set(first) == {
        "id", "exam_id", "exam", "exam_slug", "exam_phase_id", "phase",
        "subject", "topic", "topic_id", "coverage_depth", "expected_difficulty",
        "priority_score", "high_yield", "confidence_score", "evidence_count",
        "source_basis", "status", "reviewed_at",
    }
    assert first["exam"] == "UPSC CSE"
    assert first["evidence_count"] == 3


def test_count_matches_legacy_semantics_at_a_deep_offset():
    """Old behaviour (absent truncation) was `len(rows)` over a
    `limit + offset` read — i.e. offset + rows on this page. Preserved."""
    assert _get(offset=1100)["count"] == 1150
    assert _get(offset=1300)["count"] == 1320


def test_total_count_is_the_real_total():
    """New field, so a UI page-count no longer has to misread `count`."""
    for offset in (0, 900, 1100, 1300):
        assert _get(offset=offset)["total_count"] == TOTAL_ROWS
