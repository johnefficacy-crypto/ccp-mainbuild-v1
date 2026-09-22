"""Migration 301 contract (CA-SRC-01) — wave-1b discovery_only source seeds.

Text-assertion style (matching the other CA migration tests); behavioural apply
is an operator step. The seeded ``feed_format`` is cross-checked against what
the committed fixtures actually contain, so the migration and the captures can
never drift apart silently.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.scraping.fetcher import FEED_RSS, detect_feed_format

_ROOT = Path(__file__).parents[3]
_MIGRATIONS = _ROOT / "supabase/migrations"
_SQL = (_MIGRATIONS / "301_ca_wave1b_discovery_sources.sql").read_text()
_NORM = " ".join(_SQL.lower().split())

_FIXTURES = Path(__file__).parent / "fixtures" / "discovery"

# (fixture stem, publisher key, feed url, category, interval hours, publisher_type)
_SEEDS = [
    ("mongabay_india", "MONGABAY_INDIA", "https://india.mongabay.com/feed/",
     "environment", 12, "news_media"),
    ("vidhi", "VIDHI", "https://vidhilegalpolicy.in/feed/",
     "polity", 24, "think_tank"),
    ("cpr_india", "CPR_INDIA", "https://cprindia.org/feed/",
     "governance", 48, "think_tank"),
    ("barandbench", "BAR_AND_BENCH", "https://www.barandbench.com/feed",
     "polity", 12, "news_media"),
    ("livelaw", "LIVELAW", "https://www.livelaw.in/google_feeds.xml",
     "polity", 12, "news_media"),
    ("indiaspend", "INDIASPEND", "https://www.indiaspend.com/google_feeds.xml",
     "social", 24, "news_media"),
]


def test_migration_number_is_unused_by_any_other_file():
    assert len(list(_MIGRATIONS.glob("301_*.sql"))) == 1


@pytest.mark.parametrize("stem,publisher,url,category,hours,ptype", _SEEDS)
def test_each_source_is_seeded_with_the_contracted_shape(
    stem, publisher, url, category, hours, ptype
):
    assert f'"publisher": "{publisher.lower()}"' in _NORM, publisher
    assert url.lower() in _NORM, url
    assert f"'{category}', 'en'" in _NORM, category
    assert f'"interval_hours": {hours}' in _NORM, hours
    assert f"'{ptype}'" in _NORM, ptype


@pytest.mark.parametrize("stem,publisher,url,category,hours,ptype", _SEEDS)
def test_seeded_feed_format_matches_the_committed_fixture(
    stem, publisher, url, category, hours, ptype
):
    # The whole point of capturing fixtures was to stop guessing the format from
    # the URL. If a capture is ever replaced with a different shape, this fails
    # rather than leaving the seed quietly wrong.
    raw = (_FIXTURES / f"{stem}.xml").read_text(encoding="utf-8")
    assert detect_feed_format(raw) == FEED_RSS
    assert f'"publisher": "{publisher.lower()}", "feed_format": "rss"' in _NORM


def test_every_row_is_discovery_only():
    assert _NORM.count("'discovery_only'") >= len(_SEEDS)
    # No wave-1b row may claim a higher authority than ADR 0007 allows.
    for level in ("'primary_official'", "'official_secondary'"):
        assert level not in _NORM


def test_seeds_are_idempotent_and_additive_only():
    assert _NORM.count("where not exists ( select 1 from public.current_affairs_sources") == len(_SEEDS)
    assert _NORM.count("insert into public.current_affairs_sources") == len(_SEEDS)
    for forbidden in ("delete from", "drop ", "truncate", "update public.current_affairs_sources"):
        assert forbidden not in _NORM, forbidden


def test_guarded_on_rss_url_so_a_rename_cannot_duplicate_a_source():
    for _, _, url, _, _, _ in _SEEDS:
        assert f"where rss_url = '{url.lower()}'" in _NORM, url


def test_no_publisher_type_constraint_is_invented():
    # publisher_type is plain text (migration 241) — there is no CHECK to extend,
    # and adding one here would retroactively constrain every existing row.
    assert "check (publisher_type" not in _NORM
    assert "alter table public.current_affairs_sources" not in _NORM


def test_apply_asserts_the_rows_landed_as_discovery_only():
    assert "raise notice 'ca-src-01:" in _NORM
    assert "expected 6" in _NORM
    assert "raise exception 'ca-src-01: a wave-1b source is not discovery_only'" in _NORM


def test_format_and_identity_caveats_are_recorded_in_the_header():
    # The brief predicted Atom for Bar & Bench and a Google-News sitemap for
    # LiveLaw / IndiaSpend; the fixtures disagree. The reasoning has to survive
    # in the migration, not just in a PR description.
    assert "all six are rss 2.0" in _NORM
    assert "google_feeds.xml but are" in _NORM
    assert "isignal" in _NORM
