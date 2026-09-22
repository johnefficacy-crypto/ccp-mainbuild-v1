"""Migration 296 contract (CA-RSS-02) — SEBI path-allow-list / thin-body backfill.

Text-assertion style (matching the other CA migration tests); behavioural apply
is VERIFY DB via app/supabase/validation/validate_ca_sebi_path_allowlist.sql.
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).parents[3]
_MIGRATIONS = _ROOT / "supabase/migrations"
_SQL = (_MIGRATIONS / "296_ca_sebi_path_allowlist_backfill.sql").read_text()
_NORM = " ".join(_SQL.lower().split())


def test_migration_number_is_unused_by_any_other_file():
    assert len(list(_MIGRATIONS.glob("296_*.sql"))) == 1


def test_scope_is_sebi_item_documents_only():
    assert "s.adapter_config->>'publisher' = 'sebi'" in _NORM
    assert "d.canonical_item_url is not null" in _NORM
    assert "d.ingestion_status = 'snapshotted'" in _NORM


def test_path_predicate_matches_the_code_allowlist():
    # Every prefix in sources._PATH_ALLOWLIST["SEBI"] must appear as a NOT LIKE
    # here, or the backfill and the live ingest would disagree about a section.
    from app.current_affairs.sources import _PATH_ALLOWLIST

    for prefix in _PATH_ALLOWLIST["SEBI"]:
        assert f"item_path not like '{prefix}%'" in _NORM, prefix
    assert len(_PATH_ALLOWLIST["SEBI"]) == _NORM.count("item_path not like")


def test_reason_strings_match_what_the_ingest_writes():
    assert "'publisher_path_excluded:/' || split_part(x.item_path, '/', 2)" in _NORM
    # A one-segment path must not gain a trailing slash the code form never emits.
    assert "case when split_part(x.item_path, '/', 3) <> ''" in _NORM
    assert "'prefilter_reason', 'thin_body_pre_rss02'" in _NORM
    # The path is derived from the URL, never from a hardcoded section name.
    assert "regexp_replace(d.canonical_item_url, '^https?://[^/]+', '')" in _NORM


def test_thin_body_threshold_matches_the_pdf_fallback_threshold():
    from app.current_affairs.ingestion import _DEFAULT_PDF_FALLBACK_CHARS

    assert f"i.body_chars < {_DEFAULT_PDF_FALLBACK_CHARS}" in _NORM
    assert "i.id not in (select id from _sebi_path_excluded)" in _NORM


def test_retired_documents_lose_their_claimable_jobs_only():
    assert _NORM.count("update public.current_affairs_generation_jobs") == 2
    assert "set status = 'failed'" in _NORM
    assert "and j.status in ('pending', 'running')" in _NORM
    assert "last_error = 'publisher_path_excluded'" in _NORM
    assert "last_error = 'thin_body_pre_rss02'" in _NORM
    # 247's CHECK already allows 'failed'; nothing is marked 'done'.
    assert "check (status in" not in _NORM
    assert "status = 'done'" not in _NORM


def test_nothing_is_deleted_and_no_ids_are_hardcoded():
    assert "delete from" not in _NORM
    assert "drop table" not in _NORM
    # No literal uuids anywhere in the migration body.
    import re
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", _NORM)


def test_expected_scope_and_known_limitation_are_documented():
    assert "expected 14 and 1 doc(s)" in _NORM
    assert _NORM.count("get diagnostics") == 4
    assert "known limitation" in _NORM
    assert "uq_cad_source_canonical_item" in _NORM


def test_published_at_is_not_guessed_for_pre_existing_rows():
    # raw_pub_date did not exist before CA-RSS-02, so there is nothing to re-parse.
    assert "published_at" not in _NORM or "published_at is not backfilled" in _NORM


def test_validation_script_exists_and_is_rollback_only():
    validation = (
        _ROOT / "supabase/validation/validate_ca_sebi_path_allowlist.sql"
    ).read_text().lower()
    assert "publisher_path_excluded:/enforcement/orders" in validation
    assert "thin_body_pre_rss02" in validation
    assert "all pass" in validation
    assert validation.strip().endswith("rollback;")
