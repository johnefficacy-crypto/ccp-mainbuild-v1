"""Scraper quality gates (PR: scraper-org-type-gates).

P1-1  resolved-without-host gate (host-applicable source types only).
P1-3  data_quality_score ceiling observability flag.
plus  the ``_guess_org_type`` word-boundary fix (root cause of the MPSC
      ``org_type=Insurance`` mis-classification: "lic" inside "pubLIC").
"""
from __future__ import annotations

import logging

import pytest

from app.scraping.extractor import _guess_org_type
from app.scraping.runner import run_scraping_pass
from tests.test_scrape_runner_promote import RunnerSB


# ── _guess_org_type: whole-word matching, no substring false positives ──────


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Maharashtra Public Service Commission", "Other"),   # was wrongly "Insurance"
        ("Kerala Public Service Commission", "Other"),
        ("Life Insurance Corporation of India", "Insurance"),  # full word still matches
        ("LIC", "Insurance"),                                  # abbreviation as a word
        ("SSC CGL 2026", "SSC"),
        ("UPSC Civil Services Exam", "UPSC"),                  # abbreviation as a word
        ("Union Public Service Commission", "Other"),          # spelled-out: no 'upsc' token (matches prior behaviour)
        ("Railway Recruitment Board", "Railway"),
        ("State Bank of India", "Banking"),                    # "bank" substring is fine
    ],
)
def test_guess_org_type_word_boundary(name, expected):
    assert _guess_org_type(name) == expected


def test_guess_org_type_public_is_not_insurance():
    """The exact regression: 'Public' must never resolve to Insurance."""
    assert _guess_org_type("Maharashtra Public Service Commission") != "Insurance"


# ── P1-1: resolved-without-host gate ────────────────────────────────────────


def _host_applicable_source(source_type):
    return [{
        "id": "src-h",
        "source_name": "Some State Public Service Commission",
        "source_type": source_type,
        "adapter_type": "html",
        "official_url": "https://psc.example.gov.in/notices",
        "is_active": True,
        # The MPSC misconfig: an official source that does not require
        # official confirmation → else-branch sets resolved=True, host=None.
        "requires_official_confirmation": False,
    }]


def test_p1_resolved_without_host_blocks_official_html():
    sb = RunnerSB()
    sb.db["source_registry"] = _host_applicable_source("official_html")
    run_scraping_pass(sb, source_ids=["src-h"], mock=True)
    rows = sb.db["scrape_queue"]
    assert rows
    row = rows[0]
    # Flipped back to unresolved + evidence required + routed to review +
    # audited in _meta. evidence_required must be forced on so the row cannot
    # land in the resolved=False/host=None/evidence_required=False state that
    # migration 129 had to repair.
    assert row["official_source_resolved"] is False
    assert row["evidence_required"] is True
    assert row["extraction_status"] != "ok"
    assert row["extraction_status"] == "needs_review"
    assert "resolved_without_host_blocked" in (row["extracted_data"]["_meta"]["warnings"])


@pytest.mark.parametrize("source_type", ["official_html", "official_pdf", "aggregator"])
def test_p1_resolved_without_host_warning_not_duplicated(source_type):
    """The resolved_without_host_blocked warning is added exactly once."""
    sb = RunnerSB()
    sb.db["source_registry"] = _host_applicable_source(source_type)
    run_scraping_pass(sb, source_ids=["src-h"], mock=True)
    row = sb.db["scrape_queue"][0]
    warnings = row["extracted_data"]["_meta"]["warnings"] or []
    assert warnings.count("resolved_without_host_blocked") == 1


def test_p1_resolved_with_valid_host_keeps_evidence_optional(monkeypatch):
    """When a host-applicable source DOES resolve to a real official host the
    gate stays off: resolved=True, host populated, evidence not forced. This
    needs a real (non-mock) fetch because the resolver only runs off live
    HTML; in mock mode resolver_result is always None."""
    sb = RunnerSB()  # default src-1 is an aggregator (host-applicable)

    listing_html = '<a href="/ssc-cgl-2026-recruitment/">SSC CGL 2026 Recruitment</a>'
    detail_html = '<a href="https://ssc.nic.in/recruitment/2026/cgl.pdf">Official notification</a>'
    official_html = "<html>Official body of the notice</html>"

    def _fake_html(url):
        if url.endswith("/government-jobs/"):
            return listing_html
        if "ssc-cgl-2026-recruitment" in url:
            return detail_html
        if "ssc.nic.in" in url:
            return official_html
        return None

    monkeypatch.setattr("app.scraping.runner.fetch_page_html", _fake_html)
    monkeypatch.setattr("app.scraping.runner.fetch_page_text", lambda url: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    run_scraping_pass(sb, source_ids=["src-1"], mock=False, limit=5)
    row = sb.db["scrape_queue"][0]
    assert row["official_source_resolved"] is True
    assert row["official_source_host"] == "ssc.nic.in"
    assert row["evidence_required"] is False
    assert "resolved_without_host_blocked" not in (
        row["extracted_data"]["_meta"]["warnings"] or []
    )


def test_p1_api_source_exempt_from_host_gate():
    sb = RunnerSB()
    sb.db["source_registry"] = [{
        "id": "src-api",
        "source_name": "Some API Source",
        "source_type": "api",
        "adapter_type": "api",
        "api_url": "https://example.gov.in/wp-json/wp/v2/posts",
        "is_active": True,
        "requires_official_confirmation": False,
    }]
    run_scraping_pass(sb, source_ids=["src-api"], mock=True)
    rows = sb.db["scrape_queue"]
    assert rows
    # api is intentionally exempt — host may not apply; resolved stays True.
    for row in rows:
        assert row["official_source_resolved"] is True
        assert "resolved_without_host_blocked" not in (row["extracted_data"]["_meta"]["warnings"] or [])


# ── P1-3: data_quality_score ceiling flag ───────────────────────────────────


def test_p1_quality_ceiling_flag_set_and_logged(caplog):
    """The complete mock payload scores a perfect 1.0 → the ceiling flag is
    set on _meta and a greppable warning is logged."""
    sb = RunnerSB()
    caplog.set_level(logging.WARNING, logger="career_copilot.scraping.runner")
    run_scraping_pass(sb, source_ids=["src-1"], mock=True)
    rows = sb.db["scrape_queue"]
    assert rows
    assert all(r["extracted_data"]["_meta"].get("quality_ceiling_flag") is True for r in rows)
    assert any("quality_score_ceiling" in rec.getMessage() for rec in caplog.records)


# ── P1-2: per-source org_type allowlist (fail-open) ─────────────────────────


def _state_psc_source(*, expected_org_types):
    # Mock _guess_org_type("... State Public Service Commission") → "State".
    # source_type='official' is NOT host-applicable, so P1-1 stays out of the
    # way and we can assert P1-2 in isolation.
    return [{
        "id": "src-otype",
        "source_name": "Example State Public Service Commission",
        "source_type": "official",
        "adapter_type": "html",
        "official_url": "https://psc.example.gov.in/notices",
        "is_active": True,
        "requires_official_confirmation": False,
        "trust_config": {"expected_org_types": expected_org_types},
    }]


def test_p1_org_type_mismatch_routes_to_review():
    sb = RunnerSB()
    sb.db["source_registry"] = _state_psc_source(expected_org_types=["UPSC"])
    run_scraping_pass(sb, source_ids=["src-otype"], mock=True)
    row = sb.db["scrape_queue"][0]
    # Extracted org_type is "State"; allowlist is {"UPSC"} → mismatch.
    assert row["extraction_status"] == "needs_review"
    assert any(
        w.startswith("org_type_mismatch:")
        for w in (row["extracted_data"]["_meta"]["warnings"] or [])
    )


def test_p1_org_type_match_passes():
    sb = RunnerSB()
    sb.db["source_registry"] = _state_psc_source(expected_org_types=["State"])
    run_scraping_pass(sb, source_ids=["src-otype"], mock=True)
    row = sb.db["scrape_queue"][0]
    assert row["extraction_status"] == "ok"
    assert not any(
        w.startswith("org_type_mismatch:")
        for w in (row["extracted_data"]["_meta"]["warnings"] or [])
    )


def test_p1_org_type_gate_fail_open_when_unconfigured():
    """A source with no expected_org_types config is never gated on org_type."""
    sb = RunnerSB()
    src = _state_psc_source(expected_org_types=["State"])[0]
    src.pop("trust_config")
    sb.db["source_registry"] = [src]
    run_scraping_pass(sb, source_ids=["src-otype"], mock=True)
    row = sb.db["scrape_queue"][0]
    assert not any(
        w.startswith("org_type_mismatch:")
        for w in (row["extracted_data"]["_meta"]["warnings"] or [])
    )
