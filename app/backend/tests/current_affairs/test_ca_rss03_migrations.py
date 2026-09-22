"""Migrations 297 + 298 contract (CA-RSS-03).

Text-assertion style (matching the other CA migration tests); behavioural apply
is VERIFY DB via app/supabase/validation/validate_ca_rss03_pib_english.sql.
"""
from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).parents[3]
_MIGRATIONS = _ROOT / "supabase/migrations"
_SQL_297 = (_MIGRATIONS / "297_ca_rss03_language_follow_and_wave1_sources.sql").read_text(encoding="utf-8")
_SQL_298 = (_MIGRATIONS / "298_ca_pib_hindi_backfill.sql").read_text(encoding="utf-8")
_N297 = " ".join(_SQL_297.lower().split())
_N298 = " ".join(_SQL_298.lower().split())
_VALIDATION = _ROOT / "supabase/validation/validate_ca_rss03_pib_english.sql"


def test_migration_numbers_are_unused_by_any_other_file():
    assert len(list(_MIGRATIONS.glob("297_*.sql"))) == 1
    assert len(list(_MIGRATIONS.glob("298_*.sql"))) == 1


# ─── 297 ────────────────────────────────────────────────────────────────────

def test_discovery_only_status_is_added_without_losing_existing_ones():
    for status in ("snapshotted", "duplicate", "superseded", "rejected",
                   "deprioritised", "discovery_only"):
        assert f"'{status}'" in _N297, status
    # The inline 241 CHECK is found by definition, never by a guessed name.
    assert "pg_get_constraintdef(c.oid) ilike '%ingestion_status%'" in _N297
    assert "add constraint current_affairs_documents_ingestion_status_check" in _N297


def test_status_values_match_the_code():
    from app.current_affairs import sources

    assert f"'{sources.DISCOVERY_ONLY}'" in _N297


def test_source_url_hi_lookup_is_indexed_not_a_new_table():
    assert "create index if not exists idx_cad_source_url_hi" in _N297
    assert "(source_id, (metadata->>'source_url_hi'))" in _N297
    assert "create table" not in _N297
    from app.current_affairs import ingestion

    assert ingestion._SOURCE_URL_HI == "metadata->>source_url_hi"


_SEEDS = {
    "https://www.rbi.org.in/notifications_rss.xml": (
        "primary_official", "statutory_regulator", "economy",
        '{"publisher": "rbi", "feed": "notifications"}', '"interval_hours": 24'),
    "https://www.rbi.org.in/speeches_rss.xml": (
        "primary_official", "statutory_regulator", "economy",
        '{"publisher": "rbi", "feed": "speeches"}', '"interval_hours": 48'),
    "https://whc.unesco.org/en/news/rss/": (
        "primary_official", "international_body", "culture",
        '{"publisher": "unesco_whc"}', '"interval_hours": 48'),
    "https://www.thehindu.com/news/national/feeder/default.rss": (
        "discovery_only", "news_media", "general",
        '{"publisher": "the_hindu"}', '"interval_hours": 12'),
}


def _seed_block(rss_url: str) -> str:
    # The statement that inserts this rss_url, up to its WHERE NOT EXISTS guard.
    idx = _N297.index(f"'{rss_url}',")
    start = _N297.rindex("insert into public.current_affairs_sources", 0, idx)
    end = _N297.index(");", _N297.index("where not exists", idx))
    return _N297[start:end]


def test_every_seed_has_the_contracted_shape():
    for rss_url, (authority, ptype, category, config, interval) in _SEEDS.items():
        block = _seed_block(rss_url)
        assert f"'{authority}', '{ptype}', 'rss'" in block, rss_url
        assert f"'{category}', 'en'" in block, rss_url
        assert config in block, rss_url
        assert interval in block, rss_url


def test_seeds_are_idempotent_on_rss_url():
    for rss_url in _SEEDS:
        block = _seed_block(rss_url)
        assert f"where rss_url = '{rss_url}'" in block, rss_url
    assert _N297.count("where not exists ( select 1") == len(_SEEDS)
    # Guarded by rss_url alone: a publisher-marker guard (as 294 used for SEBI)
    # would block the second and third RBI rows behind the 241 press-release row.
    assert "adapter_config->>'publisher' = 'rbi'" not in _N297


def test_the_hindu_is_discovery_only():
    block = _seed_block("https://www.thehindu.com/news/national/feeder/default.rss")
    assert "'discovery_only', 'news_media'" in block


# ─── 298 ────────────────────────────────────────────────────────────────────

def test_backfill_scope_is_pre_rss03_pib_snapshotted_hindi_only():
    assert "s.adapter_config->>'publisher' = 'pib'" in _N298
    assert "d.ingestion_status = 'snapshotted'" in _N298
    assert "(d.metadata->>'source_url_hi') is null" in _N298
    # Devanagari U+0900–U+097F as chr() code points, no regex escape dialect risk.
    assert "chr(2304)" in _N298 and "chr(2431)" in _N298
    assert 0x0900 == 2304 and 0x097F == 2431


def test_backfill_rule_matches_detect_language():
    from app.current_affairs import sources

    assert f">= {sources._MIN_SCRIPT_CHARS}" in _N298
    # detect_language: 'hi' iff dev >= lat.
    assert "x.dev_chars >= x.lat_chars" in _N298


def test_backfill_reason_and_job_termination():
    assert "'prefilter_reason', 'language_mismatch_pre_rss03'" in _N298
    assert "'detected_language', 'hi'" in _N298
    assert _N298.count("update public.current_affairs_generation_jobs") == 1
    assert "set status = 'failed'" in _N298
    assert "and j.status in ('pending', 'running')" in _N298
    assert "last_error = 'language_mismatch_pre_rss03'" in _N298
    assert "status = 'done'" not in _N298


def test_backfill_reports_actual_counts_and_deletes_nothing():
    assert _N298.count("get diagnostics") == 2
    assert "raise notice 'ca-rss-03: deprioritised %" in _N298
    assert "expected ~20 / ~20" in _N298
    assert "delete from" not in _N298
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", _N298)


def test_backfill_documents_re_resolution_behaviour():
    assert "re-resolution" in _N298
    assert "uq_cad_source_canonical_item" in _N298


def test_validation_script_is_rollback_only():
    sql = _VALIDATION.read_text(encoding="utf-8").lower()
    assert sql.strip().endswith("rollback;")
    assert "commit;" not in sql
    assert "all pass" in sql
