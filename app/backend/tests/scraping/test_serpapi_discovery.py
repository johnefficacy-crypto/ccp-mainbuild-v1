"""SerpApi discovery client tests.

No respx / pytest-httpx in the dev deps, so we monkeypatch
``httpx.Client.get`` to return real ``httpx.Response`` objects (so
``raise_for_status`` / ``.json()`` behave authentically) instead of adding a
new test dependency.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import httpx
import pytest

from app.scraping.serpapi_discovery import (
    SerpApiJobLead,
    SerpApiWebLead,
    search_google_jobs,
    search_google_web,
)

_FIXTURES = Path(__file__).parent / "fixtures"
_FAKE_KEY = "fixture-secret-key-do-not-use-1234567890"


def _load(name: str) -> dict:
    with (_FIXTURES / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _patch_get(monkeypatch, *, payload: dict | None = None, status_code: int = 200):
    """Replace ``httpx.Client.get`` with a stub returning a real Response.

    The request URL is built from the passed params (which include the
    api_key) so a non-2xx ``raise_for_status`` would naturally interpolate
    the key — letting us prove it gets scrubbed.
    """

    def _get(self, url, params=None, **kwargs):  # noqa: ANN001
        request = httpx.Request("GET", httpx.URL(url, params=params or {}))
        return httpx.Response(status_code=status_code, request=request, json=payload or {})

    monkeypatch.setattr(httpx.Client, "get", _get)


# ── Parsing ──────────────────────────────────────────────────────────────


def test_search_google_jobs_parses_jobs_results(monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", _FAKE_KEY)
    _patch_get(monkeypatch, payload=_load("serpapi_jobs.json"))

    leads = search_google_jobs(query="PSU recruitment India 2026")

    assert len(leads) == 3
    assert all(isinstance(lead, SerpApiJobLead) for lead in leads)
    first = leads[0]
    assert first.title == "Scientist/Engineer - SC"
    assert first.company_name.startswith("ISRO")
    assert first.apply_options[0]["link"].startswith("https://in.linkedin.com/")
    assert first.detected_extensions.get("schedule_type") == "Full-time"
    assert first.raw  # full item retained for debugging


def test_search_google_web_parses_organic_results(monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", _FAKE_KEY)
    _patch_get(monkeypatch, payload=_load("serpapi_web.json"))

    leads = search_google_web(query="site:rbi.org.in recruitment 2026 filetype:pdf")

    assert len(leads) == 3
    assert all(isinstance(lead, SerpApiWebLead) for lead in leads)
    first = leads[0]
    assert first.link.endswith(".pdf")
    assert "rbi.org.in" in first.displayed_link
    assert first.snippet


# ── Missing key ────────────────────────────────────────────────────────────


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    # get must never be reached — assert that too.
    monkeypatch.setattr(
        httpx.Client, "get",
        lambda *a, **k: pytest.fail("network must not be touched without a key"),
    )
    with pytest.raises(RuntimeError, match="SERPAPI_API_KEY"):
        search_google_jobs(query="anything")
    with pytest.raises(RuntimeError, match="SERPAPI_API_KEY"):
        search_google_web(query="anything")


# ── max_results truncation ──────────────────────────────────────────────────


def test_max_results_truncates(monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", _FAKE_KEY)
    _patch_get(monkeypatch, payload=_load("serpapi_jobs.json"))
    assert len(search_google_jobs(query="q", max_results=1)) == 1

    _patch_get(monkeypatch, payload=_load("serpapi_web.json"))
    assert len(search_google_web(query="q", max_results=2)) == 2


# ── Empty results ────────────────────────────────────────────────────────────


def test_empty_results_returns_empty_list(monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", _FAKE_KEY)

    _patch_get(monkeypatch, payload={"jobs_results": []})
    assert search_google_jobs(query="q") == []

    _patch_get(monkeypatch, payload={"organic_results": []})
    assert search_google_web(query="q") == []

    # Missing key entirely (engine returned nothing) → still [] (no raise).
    _patch_get(monkeypatch, payload={"search_metadata": {"status": "Success"}})
    assert search_google_jobs(query="q") == []
    assert search_google_web(query="q") == []


# ── HTTP errors ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("status_code", [400, 401, 429, 500, 503])
def test_http_error_raises(monkeypatch, status_code):
    monkeypatch.setenv("SERPAPI_API_KEY", _FAKE_KEY)
    _patch_get(monkeypatch, payload={"error": "boom"}, status_code=status_code)
    with pytest.raises(httpx.HTTPStatusError):
        search_google_web(query="q")


# ── Key never leaks ──────────────────────────────────────────────────────────


def test_api_key_never_in_exception_or_logs(monkeypatch, caplog):
    monkeypatch.setenv("SERPAPI_API_KEY", _FAKE_KEY)
    _patch_get(monkeypatch, payload={"error": "forbidden"}, status_code=403)

    with caplog.at_level(logging.DEBUG):
        with pytest.raises(httpx.HTTPStatusError) as excinfo:
            search_google_jobs(query="q")

    assert _FAKE_KEY not in str(excinfo.value)
    assert "***REDACTED***" in str(excinfo.value)
    assert _FAKE_KEY not in caplog.text


def test_api_key_not_logged_on_success(monkeypatch, caplog):
    monkeypatch.setenv("SERPAPI_API_KEY", _FAKE_KEY)
    _patch_get(monkeypatch, payload=_load("serpapi_web.json"))
    with caplog.at_level(logging.DEBUG):
        search_google_web(query="site:rbi.org.in notification 2026")
    assert _FAKE_KEY not in caplog.text
