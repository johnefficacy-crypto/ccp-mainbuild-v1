"""Supabase client factories.

We used to call ``create_client`` on every request, which spun up a
fresh httpx connection pool per call. On a profile-completion fan-out
(seven sequential reads inside a single endpoint) that was creating
seven independent pools and exhausting TCP slots — log evidence:

    04:42:19.629–.644: 5× "supabase call failed: Server disconnected" in 14ms

Caching one client per process keeps a single pool alive across requests,
so keepalive connections are actually re-used and Supabase doesn't see
a burst of fresh handshakes. The cache is process-scoped — multi-worker
deployments still get one pool per worker, which is the right granularity
(each worker has its own event loop / httpx instance).

``reset_supabase_clients()`` is exported for tests that monkey-patch
``settings`` or the underlying ``create_client``.
"""
from __future__ import annotations

import logging
import threading

import httpx
from supabase import AsyncClient, Client, acreate_client, create_client
from supabase.lib.client_options import AsyncClientOptions, SyncClientOptions

from app.core.config import get_settings

logger = logging.getLogger("career_copilot.db.supabase_client")
settings = get_settings()

# Supabase's pooler resets idle keepalive connections at ~60s. httpx's
# default keepalive_expiry leaves a connection in the pool well past that,
# so the next request can grab a half-dead socket and fail the read with
# ``RemoteProtocolError: Server disconnected``. Closing our side at 30s
# keeps every pooled connection comfortably inside Supabase's window.
# Shared by both clients; the sync client additionally runs HTTP/1.1
# (see ``_sync_options``) while the async client keeps HTTP/2.
_LIMITS = httpx.Limits(
    max_keepalive_connections=20,
    max_connections=40,
    keepalive_expiry=30.0,
)


def _log_keepalive(client: Client) -> None:
    """Verify keepalive_expiry actually reached postgrest's httpx pool.

    supabase-py doesn't always thread the passed httpx_client through to every
    sub-client, so log the live value once. If it isn't 30.0 the limits didn't
    apply and the disconnect fix is a no-op. Best-effort: never raise.
    """
    try:
        pool = client.postgrest.session._transport._pool  # type: ignore[attr-defined]
        logger.info(
            "supabase admin client: keepalive_expiry=%s max_keepalive=%s",
            getattr(pool, "_keepalive_expiry", "?"),
            getattr(pool, "_max_keepalive_connections", "?"),
        )
    except Exception as e:  # pragma: no cover - introspection only
        logger.warning("could not introspect supabase keepalive: %r", e)


def _sync_options() -> SyncClientOptions:
    # HTTP/2 is disabled on the sync client only. httpcore's sync HTTP/2 stream
    # cleanup has a stream-state race that raises ``KeyError: <stream_id>`` from
    # ``_response_closed`` (httpcore/_sync/http2.py) under the admin console's
    # rapid-fire reads (e.g. GET /api/admin/scrape/queue). No upstream fix
    # exists — httpcore 1.0.9 (pinned) is the newest release — and the read
    # retry helper deliberately won't catch ``KeyError`` (it would mask real
    # dict-access bugs). HTTP/1.1 sidesteps the race entirely; the cost is
    # ~10-15% more latency per request from losing multiplexing, an acceptable
    # trade for eliminating the 500s. The async client keeps HTTP/2.
    return SyncClientOptions(
        httpx_client=httpx.Client(
            limits=_LIMITS,
            http2=False,
            timeout=httpx.Timeout(30.0),
        )
    )


def _async_options() -> AsyncClientOptions:
    return AsyncClientOptions(httpx_client=httpx.AsyncClient(limits=_LIMITS, http2=True))


_admin_client: Client | None = None
_public_client: Client | None = None
_async_admin_client: AsyncClient | None = None
_client_lock = threading.Lock()


def get_supabase_admin() -> Client:
    global _admin_client
    cached = _admin_client
    if cached is not None:
        return cached
    if not settings.NEXT_PUBLIC_SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY"
        )
    with _client_lock:
        if _admin_client is None:
            _admin_client = create_client(
                settings.NEXT_PUBLIC_SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY,
                _sync_options(),
            )
            _log_keepalive(_admin_client)
        return _admin_client


def get_supabase_public() -> Client:
    global _public_client
    cached = _public_client
    if cached is not None:
        return cached
    if not settings.NEXT_PUBLIC_SUPABASE_URL or not settings.NEXT_PUBLIC_SUPABASE_ANON_KEY:
        raise RuntimeError(
            "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_ANON_KEY"
        )
    with _client_lock:
        if _public_client is None:
            _public_client = create_client(
                settings.NEXT_PUBLIC_SUPABASE_URL,
                settings.NEXT_PUBLIC_SUPABASE_ANON_KEY,
                _sync_options(),
            )
        return _public_client


async def get_supabase_admin_async() -> AsyncClient:
    global _async_admin_client
    cached = _async_admin_client
    if cached is not None:
        return cached
    if not settings.NEXT_PUBLIC_SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError(
            "Missing NEXT_PUBLIC_SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY"
        )
    # acreate_client is async; the lock dance for the sync clients above
    # protects the dict access, not the construction. Concurrent first
    # callers may race to build two clients; the loser is GC'd.
    if _async_admin_client is None:
        _async_admin_client = await acreate_client(
            settings.NEXT_PUBLIC_SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
            _async_options(),
        )
    return _async_admin_client


def reset_supabase_admin() -> None:
    """Drop the cached sync admin client so the next get_supabase_admin()
    rebuilds on a fresh httpx pool.

    Safe under concurrency: in-flight callers keep their own reference to the
    old client; only the next builder gets the new one. Called by the read
    retry helper when a pooled socket is found dead, so the retry runs on a
    live connection instead of the RST'd one.
    """
    global _admin_client
    with _client_lock:
        _admin_client = None


def reset_supabase_clients() -> None:
    """Drop cached clients. Tests-only helper — do not call in app code."""
    global _admin_client, _public_client, _async_admin_client
    with _client_lock:
        _admin_client = None
        _public_client = None
        _async_admin_client = None
