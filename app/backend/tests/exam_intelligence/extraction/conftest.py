"""Test fixtures for the extraction package.

Unit tests use synthetic Word lists built here.
Integration tests fetch real PDFs from Supabase Storage (require live creds).
"""
from __future__ import annotations

import json
import os
import pathlib

import pytest

FIXTURES_DIR = (
    pathlib.Path(__file__).parent.parent.parent
    / "fixtures"
    / "exam_intelligence_extraction"
    / "upsc_cse_pyq_v1"
)

DOCUMENT_ID_2026 = "83722a86-610b-471d-8b6b-4a8397aa1791"
DOCUMENT_ID_2025 = "afc8e285-0ea1-41a1-a524-83b8b3121154"


@pytest.fixture
def questions_fixture() -> dict:
    """Load the 2026 GS-I questions fixture (92 expected, 8 skipped)."""
    with open(FIXTURES_DIR / "questions.json") as f:
        return json.load(f)


@pytest.fixture
def fixture_questions(questions_fixture) -> list[dict]:
    return questions_fixture["expected_questions"]


@pytest.fixture
def pdf_bytes_2026() -> bytes:
    """Fetch the 2026 PDF from Supabase Storage. Requires live service-role creds."""
    _require_integration_env()
    from app.exam_intelligence.extraction.pipeline import fetch_pdf_from_storage
    return fetch_pdf_from_storage(DOCUMENT_ID_2026)


@pytest.fixture
def pdf_bytes_2025() -> bytes:
    """Fetch the 2025 PDF from Supabase Storage. Requires live service-role creds."""
    _require_integration_env()
    from app.exam_intelligence.extraction.pipeline import fetch_pdf_from_storage
    return fetch_pdf_from_storage(DOCUMENT_ID_2025)


def _require_integration_env() -> None:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        pytest.skip(
            "Integration test requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY env vars"
        )
