"""Migration 256 contract (GQR-G5b) — relevance-window sweep RPC.

Text-assertion style; behavioural apply is VERIFY DB.
"""
from __future__ import annotations

from pathlib import Path

_SQL = (
    Path(__file__).parents[3] / "supabase/migrations/256_ca_relevance_window_sweep.sql"
).read_text()
_NORM = " ".join(_SQL.lower().split())


def test_defines_sweep_function():
    assert "create or replace function public.ca_sweep_expired_current_events()" in _NORM
    assert "returns integer" in _NORM
    assert "security definer set search_path = public" in _NORM


def test_archives_only_expired_active_events():
    assert "update public.current_affairs_events" in _NORM
    assert "set status = 'archived'" in _NORM
    assert "where status = 'active'" in _NORM
    assert "relevance_until < current_date" in _NORM


def test_never_mutates_bank_or_attempts_or_bundles():
    # Expiry must never rewrite/delete history — only the event editorial status flips.
    for forbidden in (
        "update public.mock_question_bank",
        "current_affairs_attempts",
        "current_affairs_bundles",
        "delete from",
    ):
        assert forbidden not in _NORM


def test_service_role_only_grant():
    assert ("revoke all on function public.ca_sweep_expired_current_events() "
            "from public, anon, authenticated") in _NORM
    assert ("grant execute on function public.ca_sweep_expired_current_events() "
            "to service_role") in _NORM
