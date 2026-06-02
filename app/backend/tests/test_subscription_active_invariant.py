from pathlib import Path


MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "supabase"
    / "migrations"
    / "164_subscription_active_unique_index.sql"
)


def test_subscription_active_unique_index_migration_deduplicates_before_unique_guard():
    sql = MIGRATION.read_text().lower()

    assert "row_number() over" in sql
    assert "partition by user_id" in sql
    assert "status = 'cancelled'" in sql
    assert "drop index if exists public.user_subscriptions_user_active_idx" in sql
    assert "create unique index user_subscriptions_user_active_idx" in sql
    assert "on public.user_subscriptions(user_id)" in sql
    assert "where status in ('active', 'past_due')" in sql
