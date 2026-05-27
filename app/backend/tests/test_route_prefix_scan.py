"""Route-prefix regression guard.

Sub-routers are mounted inside ``APIRouter(prefix="/api")`` in server.py, so a
router that *also* declares a ``/api`` prefix produces a doubled
``/api/api/...`` path that is unreachable from the spec'd URL. This is exactly
the bug that made the PR2d mock-template endpoints dead on arrival.

The check enumerates every mounted route and fails if any path carries the
doubled prefix. It also pins the admin mock-template routes at their correct
single-``/api`` location so a re-introduction of the bug fails here.
"""
from __future__ import annotations


def _mounted_paths() -> set[str]:
    import server  # noqa: PLC0415 — intentional late import (loads every router)

    return {getattr(r, "path", "") for r in server.app.routes}


def test_no_doubled_api_prefix():
    paths = _mounted_paths()
    offenders = sorted(p for p in paths if p.startswith("/api/api"))
    assert not offenders, (
        "Routes mounted under a doubled '/api/api' prefix detected. A sub-router "
        "declared its own '/api' prefix while server.py already mounts it inside "
        "APIRouter(prefix='/api'). Drop the leading '/api' from the router's "
        "prefix.\n  " + "\n  ".join(offenders)
    )


def test_admin_mock_templates_mounted_under_single_api():
    paths = _mounted_paths()
    assert "/api/admin/mocks/templates/" in paths
    assert "/api/admin/mocks/templates/{template_id}/publish" in paths
    assert "/api/admin/mocks/templates/{template_id}/preview-selection" in paths
