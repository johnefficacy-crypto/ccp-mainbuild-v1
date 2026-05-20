"""SerpApi discovery client (discovery-only).

SerpApi feeds *candidate* URLs into the aggregator-listing layer with status
``needs_official_source``. It must never call the recruitment extractor or
write to ``recruitments`` / ``posts`` / ``criteria`` — the existing
official-source resolver promotes a listing only after it finds a ``.gov.in``
URL or PDF. See ``runner._run_serpapi_jobs_pass`` / ``_run_serpapi_web_pass``.

Two engines, split by intent. The original design assumed ``engine=google_jobs``
alone would do, but Indian government sites do not publish JobPosting schema
markup, so ``google_jobs`` returns ~0 results for ``site:rbi.org.in`` style
queries:

* :func:`search_google_jobs` (engine=google_jobs) — corporate / PSU careers
  pages that emit JobPosting schema (TCS, Infosys, ISRO, BHEL, ONGC). Reads
  ``payload["jobs_results"]``.
* :func:`search_google_web` (engine=google) — government PDF / notification
  discovery via ``site:`` operators. Reads ``payload["organic_results"]``.

The API key is read from ``SERPAPI_API_KEY`` (never stored in the DB, seed
SQL, or repo). It is never logged and is scrubbed from any exception that
would otherwise interpolate the request URL.

Phase 2 — Scrape.do fallback (DEFER; do NOT implement now)
-----------------------------------------------------------
Scrape.do's Google Search API is ~58x cheaper per 1K requests than SerpApi
($1.16 vs $25), but that saving is irrelevant at our scale: the combined daily
budget is ~7 searches/day (~210/month) against a 250/month free tier we never
hit. A second provider only buys two keys to rotate, two quota counters, two
response schemas, two vendors to monitor, and two runner failure modes.

Re-evaluate Scrape.do as a Google Search fallback only when ALL of these hold:

  1. SerpApi monthly quota hit for 2+ consecutive months.
  2. ``engine=google`` (web) traffic dominates ``engine=google_jobs`` traffic —
     i.e. the cheap path is the hot path.
  3. We have ops bandwidth to maintain two adapters.

When that happens: route ``engine=google`` (govt ``site:`` discovery) queries
to Scrape.do and keep ``engine=google_jobs`` on SerpApi (Scrape.do has no
job-shaped endpoint). The ``serpapi_web`` adapter type is the natural seam —
swap its implementation, keep the registry row and the quota table.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_SERPAPI_ENDPOINT = "https://serpapi.com/search"
# tests/scraping/fixtures lives at app/backend/tests/...; this module is at
# app/backend/app/scraping/serpapi_discovery.py → parents[2] == app/backend.
_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "tests" / "scraping" / "fixtures"


@dataclass
class SerpApiJobLead:
    title: str
    company_name: str
    location: str
    via: str
    description: str
    detected_extensions: dict[str, Any]
    apply_options: list[dict[str, Any]]
    share_link: str
    job_id: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SerpApiWebLead:
    title: str
    link: str
    snippet: str
    displayed_link: str
    raw: dict[str, Any] = field(default_factory=dict)


def _require_api_key() -> str:
    key = os.getenv("SERPAPI_API_KEY")
    if not key:
        raise RuntimeError(
            "SERPAPI_API_KEY is not set; SerpApi discovery is disabled. "
            "Set it in the backend environment (never commit it)."
        )
    return key


def _scrub(text: str, secret: str) -> str:
    return text.replace(secret, "***REDACTED***") if secret else text


def _request(params: dict[str, str], *, api_key: str, timeout: float) -> dict[str, Any]:
    """GET ``serpapi.com/search`` and return the parsed JSON payload.

    SerpApi has no header auth, so the key rides in the query string and
    httpx embeds it in ``response.request.url`` — which ``raise_for_status``
    interpolates into its message. We scrub the key out of any
    ``HTTPStatusError`` (and suppress the original via ``from None``) so it
    never reaches logs or tracebacks.
    """
    with httpx.Client(timeout=timeout) as client:
        response = client.get(_SERPAPI_ENDPOINT, params=params)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise httpx.HTTPStatusError(
            _scrub(str(exc), api_key),
            request=exc.request,
            response=exc.response,
        ) from None
    payload = response.json()
    return payload if isinstance(payload, dict) else {}


def _to_job_lead(item: dict[str, Any]) -> SerpApiJobLead:
    extensions = item.get("detected_extensions")
    apply_options = item.get("apply_options")
    return SerpApiJobLead(
        title=str(item.get("title") or ""),
        company_name=str(item.get("company_name") or ""),
        location=str(item.get("location") or ""),
        via=str(item.get("via") or ""),
        description=str(item.get("description") or ""),
        detected_extensions=extensions if isinstance(extensions, dict) else {},
        apply_options=[o for o in apply_options if isinstance(o, dict)] if isinstance(apply_options, list) else [],
        share_link=str(item.get("share_link") or ""),
        job_id=str(item.get("job_id") or ""),
        raw=item,
    )


def _to_web_lead(item: dict[str, Any]) -> SerpApiWebLead:
    return SerpApiWebLead(
        title=str(item.get("title") or ""),
        link=str(item.get("link") or ""),
        snippet=str(item.get("snippet") or ""),
        displayed_link=str(item.get("displayed_link") or ""),
        raw=item,
    )


def parse_jobs_payload(payload: dict[str, Any], *, max_results: int) -> list[SerpApiJobLead]:
    results = payload.get("jobs_results")
    items = results if isinstance(results, list) else []
    return [_to_job_lead(item) for item in items[:max_results] if isinstance(item, dict)]


def parse_web_payload(payload: dict[str, Any], *, max_results: int) -> list[SerpApiWebLead]:
    results = payload.get("organic_results")
    items = results if isinstance(results, list) else []
    return [_to_web_lead(item) for item in items[:max_results] if isinstance(item, dict)]


def search_google_jobs(
    *, query: str, location: str = "India", max_results: int = 10, timeout: float = 20.0
) -> list[SerpApiJobLead]:
    """Run an ``engine=google_jobs`` search and return typed job leads.

    For corporate / PSU careers pages that emit JobPosting schema markup.
    Reads ``payload["jobs_results"]``; returns ``[]`` (does not raise) when
    the engine finds nothing.
    """
    api_key = _require_api_key()
    params = {
        "engine": "google_jobs",
        "q": query,
        "location": location,
        "google_domain": "google.co.in",
        "hl": "en",
        "gl": "in",
        "api_key": api_key,
    }
    payload = _request(params, api_key=api_key, timeout=timeout)
    leads = parse_jobs_payload(payload, max_results=max_results)
    logger.info("serpapi.google_jobs query=%r returned=%d", query, len(leads))
    return leads


def search_google_web(
    *, query: str, location: str = "India", max_results: int = 10, timeout: float = 20.0
) -> list[SerpApiWebLead]:
    """Run an ``engine=google`` search and return typed organic web leads.

    For government PDF / notification discovery via ``site:`` operators.
    Reads ``payload["organic_results"]``; returns ``[]`` (does not raise) when
    the search finds nothing.
    """
    api_key = _require_api_key()
    params = {
        "engine": "google",
        "q": query,
        "location": location,
        "google_domain": "google.co.in",
        "hl": "en",
        "gl": "in",
        "api_key": api_key,
    }
    payload = _request(params, api_key=api_key, timeout=timeout)
    leads = parse_web_payload(payload, max_results=max_results)
    logger.info("serpapi.google_web query=%r returned=%d", query, len(leads))
    return leads


def _load_fixture(filename: str) -> dict[str, Any]:
    path = _FIXTURES_DIR / filename
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        logger.warning("serpapi fixture missing: %s", path)
        return {}
    return data if isinstance(data, dict) else {}


def mock_job_leads(*, max_results: int = 10) -> list[SerpApiJobLead]:
    """Fixture-backed job leads for ``mock=True`` runs (no network)."""
    return parse_jobs_payload(_load_fixture("serpapi_jobs.json"), max_results=max_results)


def mock_web_leads(*, max_results: int = 10) -> list[SerpApiWebLead]:
    """Fixture-backed web leads for ``mock=True`` runs (no network)."""
    return parse_web_payload(_load_fixture("serpapi_web.json"), max_results=max_results)
