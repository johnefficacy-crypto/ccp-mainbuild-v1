"""P0 regression: api_key=<value> must never survive in log output.

httpx logs the full request URL (including the SerpApi api_key query param) at
INFO. ``RedactQuerySecretsFilter`` strips it from every record. These tests log
through the same loggers the filter is attached to and assert the secret is
gone.
"""
from __future__ import annotations

import logging

import httpx
import pytest

from app.core.logging_filters import _REDACTED_LOGGERS, install_log_redaction

_SECRET = "FAKE_SECRET_VALUE_123"


@pytest.fixture
def redaction():
    log_filter = install_log_redaction()
    yield log_filter
    for name in _REDACTED_LOGGERS:
        logging.getLogger(name).removeFilter(log_filter)


def test_httpx_logger_redacts_api_key(redaction, caplog):
    with caplog.at_level(logging.INFO, logger="httpx"):
        logging.getLogger("httpx").info(
            "HTTP Request: GET https://serpapi.com/search?engine=google&api_key=%s&q=x", _SECRET
        )
    assert _SECRET not in caplog.text
    assert "***REDACTED***" in caplog.text


def test_root_logger_redacts_api_key(redaction, caplog):
    with caplog.at_level(logging.INFO):
        logging.getLogger().info("calling https://serpapi.com/search?api_key=%s" % _SECRET)
    assert _SECRET not in caplog.text
    assert "***REDACTED***" in caplog.text


def test_exception_message_redacts_api_key(redaction, caplog):
    with caplog.at_level(logging.ERROR, logger="httpx"):
        try:
            raise ValueError(f"boom for url https://serpapi.com/search?api_key={_SECRET}&q=x")
        except ValueError as exc:
            logging.getLogger("httpx").error("request failed: %s", exc)
    assert _SECRET not in caplog.text
    assert "***REDACTED***" in caplog.text


def test_serpapi_call_does_not_leak_key_end_to_end(redaction, caplog, monkeypatch):
    """A real search_google_web call whose httpx layer logs the request URL
    must not leak the key into captured logs."""
    monkeypatch.setenv("SERPAPI_API_KEY", _SECRET)

    def _get(self, url, params=None, **kwargs):  # noqa: ANN001
        request = httpx.Request("GET", httpx.URL(url, params=params or {}))
        # Simulate httpx's own INFO request logging, which prints the full URL.
        logging.getLogger("httpx").info("HTTP Request: GET %s", request.url)
        return httpx.Response(status_code=200, request=request, json={"organic_results": []})

    monkeypatch.setattr(httpx.Client, "get", _get)

    from app.scraping.serpapi_discovery import search_google_web

    with caplog.at_level(logging.DEBUG):
        search_google_web(query="site:rbi.org.in notification 2026")

    assert _SECRET not in caplog.text
    for record in caplog.records:
        assert _SECRET not in record.getMessage()
