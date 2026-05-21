"""Task 2 — the cached Supabase clients pin a 30s httpx keepalive window.

Supabase's pooler RSTs idle connections at ~60s; httpx's default keepalive
leaves them in the pool longer, so the next request grabs a dead socket and
fails with RemoteProtocolError. We close our side at 30s.
"""
from __future__ import annotations

from types import SimpleNamespace

from app.db import supabase_client as sc


def _pool(httpx_client):
    # httpx.Client has no public ``.limits``; the configured values live on
    # the transport's connection pool.
    return httpx_client._transport._pool


def test_limits_constant_values():
    assert sc._LIMITS.keepalive_expiry == 30.0
    assert sc._LIMITS.max_keepalive_connections == 20
    assert sc._LIMITS.max_connections == 40


def test_sync_options_httpx_pool_uses_limits():
    opts = sc._sync_options()
    pool = _pool(opts.httpx_client)
    try:
        assert pool._keepalive_expiry == 30.0
        assert pool._max_keepalive_connections == 20
        assert pool._max_connections == 40
        # HTTP/2 is OFF on the sync client to dodge httpcore's sync HTTP/2
        # stream-cleanup KeyError race (httpcore 1.0.9, no upstream fix).
        assert pool._http2 is False
    finally:
        opts.httpx_client.close()


def test_sync_client_http1_latency_tradeoff():
    """Sync client runs HTTP/1.1: no multiplexing (~10-15% slower per request)
    is the deliberate trade for eliminating the stream-state KeyError 500s.
    Pinned here so a re-enable of HTTP/2 on the sync path trips this test."""
    opts = sc._sync_options()
    pool = _pool(opts.httpx_client)
    try:
        assert pool._http2 is False
    finally:
        opts.httpx_client.close()


def test_async_options_httpx_pool_uses_limits():
    opts = sc._async_options()
    pool = _pool(opts.httpx_client)
    assert pool._keepalive_expiry == 30.0
    assert pool._max_keepalive_connections == 20
    # Async client keeps HTTP/2 — the race is sync-only; this PR does not
    # touch the async path.
    assert pool._http2 is True


def test_admin_client_passes_keepalive_options(monkeypatch):
    captured = {}

    def _fake_create_client(url, key, options=None):
        captured["options"] = options
        return SimpleNamespace(url=url)

    monkeypatch.setattr(sc, "create_client", _fake_create_client)
    monkeypatch.setattr(
        sc, "settings",
        SimpleNamespace(
            NEXT_PUBLIC_SUPABASE_URL="https://proj.supabase.co",
            SUPABASE_SERVICE_ROLE_KEY="service-role-key",
        ),
    )
    sc.reset_supabase_clients()
    try:
        sc.get_supabase_admin()
        opts = captured["options"]
        assert opts is not None
        pool = _pool(opts.httpx_client)
        assert pool._keepalive_expiry == 30.0
        assert pool._max_keepalive_connections == 20
        opts.httpx_client.close()
    finally:
        sc.reset_supabase_clients()


def test_admin_client_is_process_cached(monkeypatch):
    calls = {"n": 0}

    def _fake_create_client(url, key, options=None):
        calls["n"] += 1
        if options is not None:
            options.httpx_client.close()
        return SimpleNamespace(url=url)

    monkeypatch.setattr(sc, "create_client", _fake_create_client)
    monkeypatch.setattr(
        sc, "settings",
        SimpleNamespace(
            NEXT_PUBLIC_SUPABASE_URL="https://proj.supabase.co",
            SUPABASE_SERVICE_ROLE_KEY="service-role-key",
        ),
    )
    sc.reset_supabase_clients()
    try:
        sc.get_supabase_admin()
        sc.get_supabase_admin()
        assert calls["n"] == 1  # one pool per process, not per call
    finally:
        sc.reset_supabase_clients()
