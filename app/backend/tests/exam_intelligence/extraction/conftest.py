"""Fixtures for extraction integration tests."""
from __future__ import annotations

import json
import os

import pytest


@pytest.fixture(scope="session")
def pdf_bytes_2026():
    """Fetch the 2026 GS-I fixture PDF from Supabase Storage."""
    from app.exam_intelligence.extraction.pipeline import fetch_pdf_from_storage
    return fetch_pdf_from_storage("83722a86-610b-471d-8b6b-4a8397aa1791")


@pytest.fixture(scope="session")
def questions_fixture():
    """Load the 2026 GS-I questions fixture JSON."""
    fixture_path = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "2026_gs1_questions.json",
    )
    with open(fixture_path) as f:
        return json.load(f)
