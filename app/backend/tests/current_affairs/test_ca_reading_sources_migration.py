"""Migration 302 contract (CA-RES-01) — reading sources in the Resources library.

Text-assertion style (matching the other CA migration tests); behavioural apply
is an operator step. The seed's exam slugs and family grouping are cross-checked
against the backend's EXAM_FAMILY_SLUGS constant, so the migration and the API
cannot disagree about which exams a family covers.
"""
from __future__ import annotations

import re
from pathlib import Path

from app.api.community_runtime import EXAM_FAMILY_SLUGS

_ROOT = Path(__file__).parents[3]
_MIGRATIONS = _ROOT / "supabase/migrations"
_SQL = (_MIGRATIONS / "302_ca_reading_sources_in_resources.sql").read_text()
_NORM = " ".join(_SQL.lower().split())

# Sources the current-affairs pipeline already ingests, so ca_source_id resolves.
_INGESTED = [
    "https://pib.gov.in/", "https://www.rbi.org.in/", "https://www.sebi.gov.in/",
    "https://india.mongabay.com/", "https://vidhilegalpolicy.in/", "https://cprindia.org/",
    "https://www.livelaw.in/", "https://www.barandbench.com/", "https://whc.unesco.org/",
    "https://www.isignal.in/",
]
# Referenced for reading but never crawled, so ca_source_id stays NULL.
_NOT_INGESTED = [
    "https://www.indiabudget.gov.in/", "https://mospi.gov.in/", "https://www.mea.gov.in/",
    "https://www.sci.gov.in/", "https://www.eci.gov.in/", "https://prsindia.org/",
    "https://www.scobserver.in/", "https://www.orfonline.org/", "https://www.idsa.in/",
    "https://greentribunal.gov.in/", "https://www.downtoearth.org.in/",
    "https://irdai.gov.in/", "https://www.pfrda.org.in/", "https://ifsca.gov.in/",
    "https://www.nabard.org/", "https://niscpr.res.in/",
]


def test_migration_number_is_unused_by_any_other_file():
    assert len(list(_MIGRATIONS.glob("302_*.sql"))) == 1


def test_check_constraints_are_extended_not_replaced():
    assert "'revision_sheet','reading_source'" in _NORM
    assert "'coaching','unknown','publication'" in _NORM
    # Every pre-existing value survives the rewrite.
    for kept in ("'pyq_paper'", "'current_affairs_digest'", "'mindmap'",
                 "'official'", "'community'", "'coaching'", "'unknown'"):
        assert kept in _NORM, kept


def test_ca_source_id_column_is_nullable_and_indexed():
    assert "add column if not exists ca_source_id uuid" in _NORM
    assert "references public.current_affairs_sources(id) on delete set null" in _NORM
    assert "idx_community_resources_ca_source" in _NORM
    assert "not null" not in _NORM.split("ca_source_id uuid")[1][:120]


def test_ca_source_id_is_resolved_by_lookup_never_hardcoded():
    assert "select cas.id from public.current_affairs_sources cas" in _NORM
    assert "cas.official_url = s.source_url or cas.name = s.title" in _NORM
    # RBI has three feed rows behind one official_url — the pick must be stable.
    assert "order by cas.created_at, cas.id limit 1" in _NORM
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", _NORM), "hardcoded uuid in migration"


def test_exam_id_comes_from_the_exams_table_by_slug():
    assert "join public.exams e on e.slug = g.exam_slug" in _NORM
    assert "e.id," in _NORM


def test_every_seeded_url_is_present():
    for url in _INGESTED + _NOT_INGESTED:
        assert url.lower() in _NORM, url


def test_ingested_sources_can_resolve_and_the_rest_cannot():
    # The lookup matches on official_url or name. For the ingested set those are
    # the URLs migrations 241/299/301 seeded; for the rest nothing can match,
    # which is what leaves ca_source_id NULL.
    ingested_sql = " ".join(
        (_MIGRATIONS / name).read_text().lower()
        for name in ("241_current_affairs_source_evidence.sql",       # PIB, RBI
                     "294_ca_rss_item_level_ingestion.sql",           # SEBI
                     "299_ca_rss03_language_follow_and_wave1_sources.sql",  # UNESCO, The Hindu
                     "301_ca_wave1b_discovery_sources.sql")           # wave-1b six
    )
    for url in _INGESTED:
        assert url.lower() in ingested_sql, f"{url} is not an ingested CA source"
    for url in _NOT_INGESTED:
        assert url.lower() not in ingested_sql, f"{url} IS ingested — expected NULL ca_source_id"


def test_the_hindu_resolves_by_name_because_its_reading_url_is_a_section():
    # The reading URL is the National section, not the site root the CA source
    # row carries, so only the name fallback links them.
    assert "https://www.thehindu.com/news/national/" in _NORM
    assert "the hindu — national" in _NORM


def test_seed_is_idempotent_on_url_exam_type_and_title():
    assert "where not exists (" in _NORM
    for clause in ("cr.source_url = s.source_url", "cr.exam = g.exam_slug",
                   "cr.resource_type = 'reading_source'", "cr.title = s.title"):
        assert clause in _NORM, clause
    # ...and enforced by the DB, not only by the insert's guard.
    assert "create unique index if not exists uq_community_resources_reading_source" in _NORM
    assert "on public.community_resources(source_url, exam, resource_type, title)" in _NORM


def test_title_is_in_the_key_because_two_journals_share_one_url():
    assert _NORM.count("https://www.publicationsdivision.nic.in/journals") == 2
    assert "yojana" in _NORM and "kurukshetra" in _NORM


def test_seed_rows_are_curated_not_user_contributed():
    assert "'ca_reading_list'" in _NORM
    assert "'approved'" in _NORM
    assert "'link'" in _NORM
    assert "-- contributed_by: curated" in _SQL.lower()


def test_group_slugs_match_the_backend_family_map_exactly():
    def group_slugs(name: str) -> set[str]:
        return set(re.findall(rf"\('{name}', '([a-z0-9-]+)'\)", _SQL))

    assert group_slugs("UPSC") == set(EXAM_FAMILY_SLUGS["upsc"])
    assert group_slugs("BANK") == set(EXAM_FAMILY_SLUGS["banking"])
    assert group_slugs("REG") == set(EXAM_FAMILY_SLUGS["regulatory_bodies"])

    all_slugs = group_slugs("ALL")
    assert all_slugs == (
        set(EXAM_FAMILY_SLUGS["upsc"])
        | set(EXAM_FAMILY_SLUGS["banking"])
        | set(EXAM_FAMILY_SLUGS["regulatory_bodies"])
        | {"national-ssc-combined-graduate-level-cgl",
           "national-ssc-combined-higher-secondary-level-chsl"}
    )
    assert len(all_slugs) == 10


def test_inactive_and_superseded_exam_slugs_are_never_seeded():
    assert "ssc-cgl-legacy-sandbox-do-not-use" not in _NORM
    assert not re.search(r"'nabard-grade-a'", _NORM), "superseded NABARD slug seeded"
    assert "national-nabard-grade-a" in _NORM


def test_a_missing_exam_slug_is_reported_rather_than_silently_skipped():
    # The join drops an unknown slug, which would seed nothing for that exam.
    assert "raise warning 'ca-res-01: no exams row for slug(s)" in _NORM
    assert "raise notice 'ca-res-01:" in _NORM
    assert "expected 96" in _NORM


def test_nothing_is_updated_or_deleted():
    for forbidden in ("delete from", "truncate", "update public.community_resources"):
        assert forbidden not in _NORM, forbidden
