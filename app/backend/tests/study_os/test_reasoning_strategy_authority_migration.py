"""Static contract for migration 262's Reasoning strategy authority.

Live apply/RLS proof remains an operator gate.  These assertions pin the
security, lifecycle, and content-CAS DDL so a later edit cannot silently weaken
the governance contract before that proof is run.
"""
from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "supabase/migrations/262_reasoning_strategy_authority.sql"
).read_text(encoding="utf-8").lower()
SQL = " ".join(MIGRATION.split())


def test_reasoning_tables_are_rls_enabled_and_service_role_only():
    for table in ("reasoning_strategies", "reasoning_question_strategies"):
        assert f"alter table public.{table} enable row level security" in SQL

    # The table grants are intentionally generated in the migration's DO loop.
    assert "revoke all on public.%i from anon" in SQL
    assert "revoke all on public.%i from authenticated" in SQL
    assert "grant select, insert, update, delete on public.%i to service_role" in SQL


def test_review_rpc_is_service_role_only():
    signature = (
        "public.cms_review_reasoning_strategy(uuid, text, timestamptz, text, "
        "text, text, uuid, text)"
    )
    for role in ("public", "anon", "authenticated"):
        assert f"revoke execute on function {signature} from {role}" in SQL
    assert f"grant execute on function {signature} to service_role" in SQL


def test_content_cas_token_is_database_maintained():
    assert "create trigger reasoning_strategies_updated_at" in SQL
    assert "before update on public.reasoning_strategies" in SQL
    assert "execute function public.tg_set_updated_at()" in SQL
    assert "v_row.updated_at is distinct from p_expected_updated_at" in SQL


def test_review_rpc_pins_reason_transition_and_audit_contracts():
    assert "char_length(btrim(p_reason)) < 8" in SQL
    assert "char_length(btrim(p_reason)) > 500" in SQL
    assert "transition_not_allowed:" in SQL
    assert "insert into public.admin_audit_logs" in SQL
