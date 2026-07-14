"""Migration 263 contract (GQR-S7) — governed Reasoning stimulus links.

Live PostgreSQL privilege/application proof remains an operator VERIFY-DB step; this
suite pins the schema, FK, review-gate, and service-role-only posture in CI.
"""
from __future__ import annotations

from pathlib import Path


_SQL = (
    Path(__file__).parents[3]
    / "supabase/migrations/263_reasoning_stimulus_strategy_authority.sql"
).read_text()
_NORM = " ".join(_SQL.lower().split())


def test_creates_canonical_stimulus_strategy_link_authority():
    assert "create table if not exists public.reasoning_stimulus_strategies" in _NORM
    assert (
        "stimulus_id uuid not null references public.pyq_stimuli(id) on delete cascade"
        in _NORM
    )
    assert (
        "strategy_id uuid not null references public.reasoning_strategies(id) on delete cascade"
        in _NORM
    )
    assert "unique (stimulus_id, strategy_id)" in _NORM
    assert "relevance in ('primary', 'secondary', 'related')" in _NORM
    assert "reviewer_status in ('pending', 'verified', 'rejected')" in _NORM


def test_indexes_cover_runtime_and_review_reads():
    assert "idx_rss_stimulus" in _NORM
    assert "idx_rss_strategy" in _NORM
    assert "idx_rss_reviewer_status" in _NORM


def test_authority_is_service_role_only():
    assert (
        "alter table public.reasoning_stimulus_strategies enable row level security"
        in _NORM
    )
    assert "create policy" not in _NORM
    for role in ("public", "anon", "authenticated"):
        assert (
            f"revoke all on public.reasoning_stimulus_strategies from {role}"
            in _NORM
        )
    assert (
        "grant select, insert, update, delete on public.reasoning_stimulus_strategies to service_role"
        in _NORM
    )


def test_migration_reloads_postgrest_schema():
    assert "notify pgrst, 'reload schema'" in _NORM
