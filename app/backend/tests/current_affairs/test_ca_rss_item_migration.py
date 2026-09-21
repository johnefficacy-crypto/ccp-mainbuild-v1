"""Migration 294 contract (CA-RSS-01) — item-level RSS ingestion DB parts.

Text-assertion style (matching the other CA migration tests); behavioural apply
is VERIFY DB via app/supabase/validation/validate_ca_rss_item_ingestion.sql.
"""
from __future__ import annotations

from pathlib import Path

_MIGRATIONS = Path(__file__).parents[3] / "supabase/migrations"
_SQL = (_MIGRATIONS / "294_ca_rss_item_level_ingestion.sql").read_text()
_NORM = " ".join(_SQL.lower().split())


def test_migration_number_is_unused_by_any_other_file():
    assert len([p for p in _MIGRATIONS.glob("294_*.sql")]) == 1


def test_adds_canonical_item_url_with_a_partial_unique_index():
    assert ("alter table public.current_affairs_documents "
            "add column if not exists canonical_item_url text") in _NORM
    assert ("create unique index if not exists uq_cad_source_canonical_item "
            "on public.current_affairs_documents(source_id, canonical_item_url) "
            "where canonical_item_url is not null") in _NORM


def test_keeps_the_existing_content_hash_dedup_index():
    # 241's uq_cad_source_content_hash must not be dropped or replaced.
    assert "drop index" not in _NORM
    assert "uq_cad_source_content_hash" not in _NORM


def test_adds_feed_level_conditional_fetch_validators_to_the_source():
    assert "alter table public.current_affairs_sources" in _NORM
    assert "add column if not exists feed_etag text" in _NORM
    assert "add column if not exists feed_last_modified text" in _NORM


def test_sets_a_browser_user_agent_on_the_pib_source_only():
    assert "adapter_config->>'publisher' = 'pib'" in _NORM
    assert "'user_agent'" in _NORM
    assert "mozilla/5.0 (windows nt 10.0; win64; x64)" in _NORM
    # Scoped to the PIB row — no blanket update of every source.
    assert "update public.current_affairs_sources set adapter_config = adapter_config || " in _NORM


def test_seeds_sebi_idempotently_with_the_contracted_shape():
    assert "'securities and exchange board of india'" in _NORM
    assert "'primary_official'" in _NORM and "'statutory_regulator'" in _NORM
    assert "'https://www.sebi.gov.in/sebirss.xml'" in _NORM
    assert '\'{"publisher": "sebi"}\'::jsonb' in _NORM
    assert '"interval_hours": 24' in _NORM
    assert "where not exists ( select 1 from public.current_affairs_sources" in _NORM


def test_legacy_whole_feed_rows_are_deprioritised_not_deleted():
    assert "delete from" not in _NORM
    assert "set ingestion_status = 'deprioritised'" in _NORM
    assert "'prefilter_reason', 'legacy_whole_feed'" in _NORM
    # Structural scope: title IS NULL and the body starts with an XML prolog
    # (BOM tolerated). No hardcoded document ids.
    assert "d.title is null" in _NORM
    assert "ltrim(d.raw_text, chr(65279)" in _NORM
    assert "like '<?xml%'" in _NORM


def test_legacy_jobs_move_to_an_existing_terminal_non_run_status():
    assert "update public.current_affairs_generation_jobs" in _NORM
    assert "set status = 'failed'" in _NORM
    assert "last_error = 'legacy_whole_feed'" in _NORM
    assert "and j.status in ('pending', 'running')" in _NORM
    # No new enum value was needed — 247's CHECK already allows 'failed', and the
    # jobs are never marked 'done' (that would falsely claim generation output).
    assert "check (status in" not in _NORM
    assert "status = 'done'" not in _NORM


def test_expected_scope_is_asserted_in_a_notice_not_hardcoded_ids():
    assert "expected 22 / 22" in _NORM
    assert "get diagnostics" in _NORM


def test_validation_script_exists():
    validation = (
        Path(__file__).parents[3] / "supabase/validation/validate_ca_rss_item_ingestion.sql"
    ).read_text().lower()
    assert "uq_cad_source_canonical_item" in validation
    assert "all pass" in validation
    assert validation.strip().endswith("rollback;")
