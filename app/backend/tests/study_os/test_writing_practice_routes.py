"""EWP-2 route-registration wiring test.

Asserts the deterministic practice-runtime endpoints are mounted under
``/api/study/practice/english``. Skips if the full server import graph's
optional deps are unavailable in the local environment (they are present in CI).
"""
from __future__ import annotations

import pytest

pytest.importorskip("cachetools")
fastapi_testclient = pytest.importorskip("fastapi.testclient")


def _paths():
    from fastapi.testclient import TestClient
    from server import app

    with TestClient(app) as client:
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        return set(resp.json().get("paths", {}))


def test_writing_practice_routes_registered():
    paths = _paths()
    expected = {
        "/api/study/practice/english/sessions",
        "/api/study/practice/english/sessions/{session_id}",
        "/api/study/practice/english/sessions/{session_id}/units/{unit_number}/submit",
        "/api/study/practice/english/sessions/{session_id}/units/{unit_id}/reopen",
        "/api/study/practice/english/sessions/{session_id}/evaluations/{evaluation_id}",
        "/api/study/practice/english/error-summary",
    }
    missing = expected - paths
    assert not missing, f"missing writing-practice routes: {sorted(missing)}"
