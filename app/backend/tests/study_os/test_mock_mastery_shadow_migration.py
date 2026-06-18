from __future__ import annotations

from pathlib import Path


def test_shadow_idempotency_migration_dedupes_before_unique_index():
    migration = Path(__file__).parents[3] / "supabase/migrations/180_mock_mastery_shadow_idempotency.sql"
    sql = migration.read_text()

    assert "row_number() over" in sql
    assert "partition by attempt_id, topic_id, flag_state" in sql
    assert "order by decided_at asc, id asc" in sql
    assert "delete from public.mock_mastery_shadow" in sql
    assert "create unique index if not exists mock_mastery_shadow_attempt_topic_flag_unique" in sql
    assert "on public.mock_mastery_shadow(attempt_id, topic_id, flag_state)" in sql
