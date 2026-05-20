"""Runner-level SerpApi adapter tests.

Covers dispatch from ``run_scraping_pass`` for both adapters and the
discovery-only contract: rows land in ``aggregator_listings`` with status
``needs_official_source`` and nothing is written to ``recruitments`` /
``scrape_queue``.
"""
from __future__ import annotations

from app.scraping.runner import run_scraping_pass
from tests.test_scrape_runner_promote import RunnerSB


def _web_source():
    return {
        "id": "serp-web-1",
        "source_name": "SerpApi Google Web — Government Discovery",
        "source_type": "aggregator",
        "adapter_type": "serpapi_web",
        "is_active": True,
        "discovery_only": True,
        "requires_official_confirmation": True,
        "is_official_source": False,
        "official_url": "https://serpapi.com/search-api",
        "adapter_config": {
            "location": "India",
            "queries": [
                "site:rbi.org.in recruitment notification 2026 filetype:pdf",
                "site:ssc.gov.in notification 2026",
            ],
        },
        "scrape_config": {"max_items_per_run": 10, "monthly_search_cap": 120, "daily_search_cap": 4},
    }


def _jobs_source():
    return {
        "id": "serp-jobs-1",
        "source_name": "SerpApi Google Jobs — PSU/Corporate Discovery",
        "source_type": "aggregator",
        "adapter_type": "serpapi_jobs",
        "is_active": True,
        "discovery_only": True,
        "requires_official_confirmation": True,
        "is_official_source": False,
        "official_url": "https://serpapi.com/google-jobs-api",
        "adapter_config": {
            "location": "India",
            "queries": ["PSU recruitment India 2026", "ISRO BHEL ONGC engineer recruitment"],
        },
        "scrape_config": {"max_items_per_run": 10, "monthly_search_cap": 80, "daily_search_cap": 3},
    }


def test_serpapi_web_dispatch_creates_needs_official_source_listings():
    sb = RunnerSB()
    sb.db["source_registry"] = [_web_source()]

    summary = run_scraping_pass(sb, mock=True)

    listings = sb.db.get("aggregator_listings", [])
    assert listings, "expected discovery listings"
    assert all(row["status"] == "needs_official_source" for row in listings)
    # Web fixture has 3 unique organic links → 3 listings (deduped across queries).
    assert len(listings) == 3
    # Discovery-only: never writes to recruitments or scrape_queue.
    assert "recruitments" not in sb.db
    assert "scrape_queue" not in sb.db
    assert summary["status"] == "completed"


def test_serpapi_web_flags_pdf_links_in_observation_label():
    sb = RunnerSB()
    sb.db["source_registry"] = [_web_source()]
    run_scraping_pass(sb, mock=True)

    observations = sb.db.get("listing_observations", [])
    pdf_labels = [o for o in observations if "[pdf]" in (o.get("observed_label") or "")]
    # Two of the three web fixture links end in .pdf.
    assert len(pdf_labels) == 2


def test_serpapi_jobs_dispatch_creates_needs_official_source_listings():
    sb = RunnerSB()
    sb.db["source_registry"] = [_jobs_source()]

    run_scraping_pass(sb, mock=True)

    listings = sb.db.get("aggregator_listings", [])
    assert listings
    assert all(row["status"] == "needs_official_source" for row in listings)
    # Jobs fixture has 3 leads, each with an apply/share link → 3 listings.
    assert len(listings) == 3
    assert "recruitments" not in sb.db
    assert "scrape_queue" not in sb.db


def test_serpapi_live_quota_block_is_clean_noop(monkeypatch):
    """A quota block short-circuits without hitting the network and without
    recording a source failure (it's a no-op success, not a strike)."""
    monkeypatch.setattr("app.scraping.quota.can_use_serpapi", lambda *a, **k: False)

    def _boom(*a, **k):
        raise AssertionError("search must not run when quota is blocked")

    monkeypatch.setattr("app.scraping.serpapi_discovery.search_google_web", _boom)

    sb = RunnerSB()
    sb.db["source_registry"] = [_web_source()]
    run_scraping_pass(sb, mock=False)

    assert sb.db.get("aggregator_listings", []) == []
    # Marked success (last_success_at set), not a failure bump.
    updates = sb.db.get("source_registry_updates", [])
    assert any("last_success_at" in u for u in updates)
    assert not any((u.get("last_error_class") or "").startswith("empty_serpapi") for u in updates)
