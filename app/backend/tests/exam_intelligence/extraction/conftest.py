"""Fixtures for extraction integration tests."""
from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest


# Known fixture/smoke document UUIDs and their backfilled classification.
# These documents predate migration 152; we provide the values here so
# the acceptance gate runs even before migration 152 is applied on the
# acceptance test DB. Once migration 152 is live everywhere this can be
# removed — the real fetch will return the same values.
_FIXTURE_CLASSIFICATIONS = {
    "83722a86-610b-471d-8b6b-4a8397aa1791": ("mcq_bilingual_two_column", "upsc_cse_prelims_gs1"),
    "afc8e285-0ea1-41a1-a524-83b8b3121154": ("mcq_bilingual_two_column", "upsc_cse_prelims_gs1"),
}


@pytest.fixture()
def stub_fetch_doc_row_for_fixtures():
    """Patch _fetch_document_assets_row for the known fixture UUIDs.

    Use this fixture in any test that calls extract() with a fixture document
    but does not want to depend on migration 152 being applied.
    """
    from app.exam_intelligence.extraction.dispatch import StructuralFormat, ExamIdentity
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
