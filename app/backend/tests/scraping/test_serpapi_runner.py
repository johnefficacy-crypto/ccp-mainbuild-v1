"""Runner-level SerpApi adapter tests.

Covers dispatch from ``run_scraping_pass`` for both adapters and the
discovery-only contract: rows land in ``aggregator_listings`` with status
``needs_official_source`` and nothing is written to ``recruitments`` /
``scrape_queue``.
"""
from __future__ import annotations

from types import SimpleNamespace

from app.scraping.runner import run_scraping_pass
from tests.test_scrape_runner_promote import RunnerSB


def _web_lead(title, link):
    return SimpleNamespace(title=title, link=link)


def _single_query_web_source():
    return {
        "id": "serp-web-counters",
        "source_name": "SerpApi Web Counters",
        "source_type": "aggregator",
        "adapter_type": "serpapi_web",
        "is_active": True,
        "discovery_only": True,
        "requires_official_confirmation": True,
        "official_url": "https://serpapi.com/search-api",
        "adapter_config": {"location": "India", "queries": ["one query"]},
        "scrape_config": {"max_items_per_run": 50, "monthly_search_cap": 120, "daily_search_cap": 4},
    }


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


# ── P1.2: discovery counters ─────────────────────────────────────────────────


def test_discovery_counters_all_new(monkeypatch):
    leads = [_web_lead(f"Recruitment notice {i}", f"https://x{i}.gov.in/n.html") for i in range(25)]
    monkeypatch.setattr("app.scraping.runner._serpapi_fetch_leads", lambda **kw: list(leads))

    sb = RunnerSB()
    sb.db["source_registry"] = [_single_query_web_source()]
    summary = run_scraping_pass(sb, mock=True)

    assert summary["discovery_items_found"] == 25
    assert summary["discovery_items_new"] == 25
    assert summary["discovery_items_lifecycle"] == 0
    assert len(sb.db.get("aggregator_listings", [])) == 25


def test_discovery_counters_split_new_and_lifecycle(monkeypatch):
    leads = [
        _web_lead("SSC CGL 2026 Admit Card", "https://ssc.gov.in/admit.html"),
        _web_lead("Result of RBI Grade B 2025", "https://rbi.org.in/result.html"),
        _web_lead("Answer Key for SSC 2026", "https://ssc.gov.in/answer.html"),
        _web_lead("UPSC CSE 2026 Notification", "https://upsc.gov.in/notif.html"),
        _web_lead("RRB CEN 2026 Recruitment", "https://rrb.gov.in/cen.html"),
    ]
    monkeypatch.setattr("app.scraping.runner._serpapi_fetch_leads", lambda **kw: list(leads))

    sb = RunnerSB()
    sb.db["source_registry"] = [_single_query_web_source()]
    summary = run_scraping_pass(sb, mock=True)

    assert summary["discovery_items_found"] == 5
    assert summary["discovery_items_new"] == 2
    assert summary["discovery_items_lifecycle"] == 3
    # found == new + lifecycle + dedup_skips (no dedup on a single fresh run).
    dedup_skips = (
        summary["discovery_items_found"]
        - summary["discovery_items_new"]
        - summary["discovery_items_lifecycle"]
    )
    assert dedup_skips == 0
    # Only the 2 new_recruitment leads became listings.
    assert len(sb.db.get("aggregator_listings", [])) == 2


def test_discovery_rerun_dedups_to_zero_new(monkeypatch):
    leads = [_web_lead(f"Recruitment {i}", f"https://x{i}.gov.in/n.html") for i in range(4)]
    monkeypatch.setattr("app.scraping.runner._serpapi_fetch_leads", lambda **kw: list(leads))

    sb = RunnerSB()
    sb.db["source_registry"] = [_single_query_web_source()]

    first = run_scraping_pass(sb, mock=True)
    assert first["discovery_items_new"] == 4

    second = run_scraping_pass(sb, mock=True)
    assert second["discovery_items_found"] == 4
    assert second["discovery_items_new"] == 0  # all deduped
    assert len(sb.db.get("aggregator_listings", [])) == 4  # no new rows


# ── P1.4: lifecycle routing ──────────────────────────────────────────────────


def test_lifecycle_lead_routed_to_event_not_listing(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr("app.scraping.runner._record_lifecycle_event", lambda *a, **kw: calls.append(kw))
    monkeypatch.setattr(
        "app.scraping.runner._serpapi_fetch_leads",
        lambda **kw: [_web_lead("SSC CGL 2026 Admit Card", "https://ssc.gov.in/admit.html")],
    )

    sb = RunnerSB()
    sb.db["source_registry"] = [_single_query_web_source()]
    summary = run_scraping_pass(sb, mock=True)

    assert len(calls) == 1
    assert calls[0]["event_type"] == "admit_card"
    assert calls[0]["url"] == "https://ssc.gov.in/admit.html"
    assert calls[0]["listing_id"] is None
    assert sb.db.get("aggregator_listings", []) == []
    assert summary["discovery_items_lifecycle"] == 1
    assert summary["discovery_items_new"] == 0


def test_notification_lead_creates_needs_official_source_listing(monkeypatch):
    monkeypatch.setattr(
        "app.scraping.runner._serpapi_fetch_leads",
        lambda **kw: [_web_lead("UPSC CSE 2026 Notification", "https://upsc.gov.in/notif.html")],
    )

    sb = RunnerSB()
    sb.db["source_registry"] = [_single_query_web_source()]
    summary = run_scraping_pass(sb, mock=True)

    listings = sb.db.get("aggregator_listings", [])
    assert len(listings) == 1
    assert listings[0]["status"] == "needs_official_source"
    assert summary["discovery_items_new"] == 1
    assert summary["discovery_items_lifecycle"] == 0


def test_result_lead_routed_lifecycle(monkeypatch):
    calls: list[dict] = []
    monkeypatch.setattr("app.scraping.runner._record_lifecycle_event", lambda *a, **kw: calls.append(kw))
    monkeypatch.setattr(
        "app.scraping.runner._serpapi_fetch_leads",
        lambda **kw: [_web_lead("Result of RBI Grade B 2025", "https://rbi.org.in/result.html")],
    )

    sb = RunnerSB()
    sb.db["source_registry"] = [_single_query_web_source()]
    run_scraping_pass(sb, mock=True)

    assert len(calls) == 1
    assert calls[0]["event_type"] == "result"
    assert sb.db.get("aggregator_listings", []) == []


def test_all_lifecycle_marks_success_and_advances_cursor(monkeypatch):
    monkeypatch.setattr(
        "app.scraping.runner._serpapi_fetch_leads",
        lambda **kw: [
            _web_lead("SSC CGL 2026 Admit Card", "https://ssc.gov.in/admit.html"),
            _web_lead("Result of RBI Grade B 2025", "https://rbi.org.in/result.html"),
            _web_lead("Answer Key SSC 2026", "https://ssc.gov.in/ak.html"),
        ],
    )

    sb = RunnerSB()
    sb.db["source_registry"] = [_single_query_web_source()]
    summary = run_scraping_pass(sb, mock=True)

    assert sb.db.get("aggregator_listings", []) == []
    assert summary["discovery_items_lifecycle"] == 3
    updates = sb.db.get("source_registry_updates", [])
    # Marked success (not penalised for behaving correctly), and cursor advanced.
    assert any("last_success_at" in u for u in updates)
    assert not any((u.get("last_error_class") or "").startswith("empty_serpapi") for u in updates)
    assert any(
        isinstance(u.get("scrape_config"), dict) and "next_query_index" in u["scrape_config"]
        for u in updates
    )
