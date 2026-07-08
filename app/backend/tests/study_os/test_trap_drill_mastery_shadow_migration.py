"""Text-contract test for migration 232 (PYQ v2 PR-8, shadow only)."""
from pathlib import Path

_MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase" / "migrations"
MIGRATION = (_MIGRATIONS / "232_trap_drill_mastery_shadow.sql").read_text().lower()


def test_creates_separate_shadow_table():
    assert "create table if not exists public.trap_drill_mastery_shadow" in MIGRATION


def test_has_no_foreign_key_to_mock_attempts():
    # synthetic uuid5 lineage — a real FK would violate on insert (no mock_attempts row).
    assert "references public.mock_attempts" not in MIGRATION
    assert "synthetic_attempt_id" in MIGRATION


def test_flag_state_is_pinned_to_shadow():
    assert "flag_state" in MIGRATION
    assert "check (flag_state = 'shadow')" in MIGRATION


def test_revision_bucket_constraint():
    assert "revision_bucket" in MIGRATION
    for bucket in ("'relearn'", "'review'", "'practice'"):
        assert bucket in MIGRATION


def test_source_column_defaults_and_is_check_pinned():
    assert "source" in MIGRATION
    assert "default 'trap_drill'" in MIGRATION
    # source is a structural invariant, not just a default.
    assert "check (source = 'trap_drill')" in MIGRATION


def test_rls_enabled_and_service_role_grant():
    assert "alter table public.trap_drill_mastery_shadow enable row level security" in MIGRATION
    assert "grant select, insert, update, delete on public.trap_drill_mastery_shadow to service_role" in MIGRATION


def test_idempotency_unique_index():
    assert "trap_drill_mastery_shadow_attempt_topic_uidx" in MIGRATION
    assert "notify pgrst" in MIGRATION or "pg_notify('pgrst'" in MIGRATION


def test_does_not_insert_into_mock_mastery_shadow():
    # must never write the P8-measured mock shadow table.
    assert "insert into public.mock_mastery_shadow" not in MIGRATION
    assert "create table if not exists public.mock_mastery_shadow" not in MIGRATION
