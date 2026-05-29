"""Test fixtures for the extraction package.

Unit tests use synthetic Word lists built here.
Integration tests fetch real PDFs from Supabase Storage (require live creds).
"""
from __future__ import annotations

import json
import os
import pathlib
from unittest.mock import patch

import pytest

FIXTURES_DIR = (
    pathlib.Path(__file__).parent.parent.parent
    / "fixtures"
    / "exam_intelligence_extraction"
    / "upsc_cse_pyq_v1"
)

DOCUMENT_ID_2026 = "83722a86-610b-471d-8b6b-4a8397aa1791"
DOCUMENT_ID_2025 = "afc8e285-0ea1-41a1-a524-83b8b3121154"

# Known fixture/smoke document UUIDs and their backfilled classification.
# These documents predate migration 152; we provide the values here so
# the acceptance gate runs even before migration 152 is applied on the
# acceptance test DB. Once migration 152 is live everywhere this stub
# can be removed — the real fetch will return the same values.
_FIXTURE_CLASSIFICATIONS = {
    DOCUMENT_ID_2026: ("mcq_bilingual_two_column", "upsc_cse_prelims_gs1"),
    DOCUMENT_ID_2025: ("mcq_bilingual_two_column", "upsc_cse_prelims_gs1"),
}


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


@pytest.fixture()
def stub_fetch_doc_row_for_fixtures():
    """Patch _fetch_document_assets_row for the known fixture UUIDs.

    Allows the acceptance gate to run before migration 152 is applied on
    the acceptance test DB. Once migration 152 is live everywhere, this
    stub can be removed — the real fetch will return the same values.
    """
    from app.exam_intelligence.extraction.dispatch import ExamIdentity, StructuralFormat
    from app.exam_intelligence.extraction.pipeline import _DocumentAssetsRow

    def _side_effect(document_id: str):
        if document_id in _FIXTURE_CLASSIFICATIONS:
            sf, ei = _FIXTURE_CLASSIFICATIONS[document_id]
            return _DocumentAssetsRow(
                id=document_id,
                structural_format=StructuralFormat(sf),
                exam_identity=ExamIdentity(ei),
                storage_path="",
            )
        raise ValueError(
            f"_fetch_document_assets_row called with unexpected document_id={document_id!r}. "
            f"Add it to _FIXTURE_CLASSIFICATIONS in conftest.py if it is a known fixture."
        )

    with patch(
        "app.exam_intelligence.extraction.pipeline._fetch_document_assets_row",
        side_effect=_side_effect,
    ):
        yield


def _require_integration_env() -> None:
    # Accept either SUPABASE_URL or NEXT_PUBLIC_SUPABASE_URL (workflow maps both).
    url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        pytest.fail(
            "Integration test requires SUPABASE_URL (or NEXT_PUBLIC_SUPABASE_URL) "
            "and SUPABASE_SERVICE_ROLE_KEY env vars — missing creds must fail loud, "
            "not silently skip the acceptance gate."
        )
