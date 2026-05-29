"""Route-prefix regression guard (PR-fix-5).

Introspects the mounted FastAPI app and asserts that admin/study endpoints
are registered under their documented prefixes. This is the canary that fails
CI when a router is misconfigured — either a double ``/api/api/`` prefix
(the ``admin_templates.py`` pattern PR-fix-6 addresses) or a missing path
segment (the ``/questions/`` omission Fix 1 of this PR corrected).

Extend the explicit-path lists below as new admin modules add routes.
"""
from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def app():
    # server.py lives at the backend root and wires every router under /api.
    import server  # noqa: PLC0415 — intentional late import (loads all routers)

    return server.app


def _paths(app) -> set[str]:
    return {r.path for r in app.routes if hasattr(r, "path")}


# Known pre-existing double-prefix: ``admin_templates.py`` declares its router
# with ``prefix="/api/admin/mocks/templates"`` and is then mounted under the
# ``/api`` router, producing ``/api/api/admin/mocks/templates/*``. PR-fix-6
# removes the stray ``/api`` from that router. Until then this is an explicit,
# documented exception so the canary stays green while still catching any *new*
# double-prefix. PR-fix-6 should delete this allowlist entry.
_KNOWN_DOUBLE_PREFIX = "/api/api/admin/mocks/templates"


def test_no_double_api_prefix(app):
    paths = [r.path for r in app.routes if hasattr(r, "path")]
    doubled = [
        p for p in paths
        if "/api/api/" in p and not p.startswith(_KNOWN_DOUBLE_PREFIX)
    ]
    assert not doubled, f"double /api/ prefix in: {doubled}"


def test_admin_mocks_question_routes_under_questions(app):
    expected = [
        "/api/admin/mocks/questions",
        "/api/admin/mocks/questions/{question_id}",
        "/api/admin/mocks/questions/{question_id}/dedup-check",
        "/api/admin/mocks/questions/{question_id}/submit",
        "/api/admin/mocks/questions/{question_id}/approve",
        "/api/admin/mocks/questions/{question_id}/publish",
    ]
    paths = _paths(app)
    missing = [e for e in expected if e not in paths]
    assert not missing, f"missing routes: {missing}"
