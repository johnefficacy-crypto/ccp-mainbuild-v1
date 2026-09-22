"""CMS write contract for `essay_pyq_tags.format` (migration 304).

`essay_pyq_tags` was built for the UPSC Essay paper, where every row is an
essay, so `essay_type` was `not null default 'quote_abstract'`
(265_essay_theme_taxonomy.sql:36-37). RBI Grade B Phase II English mixes an
essay, a precis and a comprehension in one paper. Two things had to hold before
that corpus could be written, and these tests pin both:

  * a `format` axis exists and is writable through the CMS — a column the CMS
    cannot write is not a shipped column;
  * a precis row can be written WITHOUT an essay_type and is NOT silently
    defaulted to 'quote_abstract', which is what the old default did.

The format/essay_type pairing is enforced twice on purpose: by
`essay_pyq_tags_essay_type_format_check` in the database, and by the router so
the operator sees a named 422 rather than a raw constraint error surfaced as a
409. These tests cover the router half.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.exam_intelligence.test_cms_taxonomy import TaxSBStub

_BASE = "/api/admin/exam-intelligence-cms"
_TAGS = f"{_BASE}/essay-pyq-tags"


def _client(sb: TaxSBStub) -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": "super_admin", "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed() -> dict:
    return {
        "exams": [{"id": "e1", "slug": "rbi-grade-b", "name": "RBI Grade B", "is_active": True}],
        "pyq_papers": [{"id": "p1", "exam_id": "e1", "year": 2025}],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "reviewer_status": "verified"},
            {"id": "q2", "pyq_paper_id": "p1", "reviewer_status": "verified"},
        ],
        "essay_themes": [
            {"id": "th1", "theme_code": "ECO", "theme_name": "Economy", "status": "active"},
        ],
    }


def _post(sb: TaxSBStub, payload: dict):
    return _client(sb).post(_TAGS, json={"reason": "rbi english tagging", "payload": payload})


# ── the defect this migration exists to close ─────────────────────────────


def test_precis_row_is_written_without_essay_type_and_is_not_defaulted():
    """The G4 regression: a precis has no essay type, and must not acquire one.

    Before migration 304 the column was `not null default 'quote_abstract'`, so
    this insert did not fail — it silently recorded the precis as a
    quote-abstract essay. The row must now persist with essay_type absent or
    None, never the old default.
    """
    sb = TaxSBStub(_seed())
    r = _post(sb, {"question_id": "q1", "theme_id": "th1", "format": "precis"})
    assert r.status_code == 200, r.text

    row = sb.db["essay_pyq_tags"][0]
    assert row["format"] == "precis"
    assert row.get("essay_type") is None, f"precis row was defaulted to {row.get('essay_type')!r}"
    assert row["reviewer_status"] == "pending"


def test_comprehension_row_is_written_without_essay_type():
    sb = TaxSBStub(_seed())
    r = _post(sb, {"question_id": "q1", "theme_id": "th1", "format": "comprehension"})
    assert r.status_code == 200, r.text
    row = sb.db["essay_pyq_tags"][0]
    assert row["format"] == "comprehension"
    assert row.get("essay_type") is None


# ── format is writable, required, and enum-checked ────────────────────────


def test_format_is_accepted_by_the_write_allowlist():
    # A field missing from _ESSAY_TAG_FIELDS is stripped before insert, so the
    # column would silently never be written. Pin that it survives the filter.
    assert "format" in cms_api._ESSAY_TAG_FIELDS
    sb = TaxSBStub(_seed())
    r = _post(sb, {
        "question_id": "q1", "theme_id": "th1",
        "format": "essay", "essay_type": "issue_concrete",
    })
    assert r.status_code == 200, r.text
    assert sb.db["essay_pyq_tags"][0]["format"] == "essay"


def test_format_is_required():
    # Migration 304 gives the column NO default, so an omitted format would be a
    # NOT NULL violation. The router rejects it first, with a named message.
    sb = TaxSBStub(_seed())
    r = _post(sb, {"question_id": "q1", "theme_id": "th1", "essay_type": "issue_concrete"})
    assert r.status_code == 422
    assert "format is required" in r.json()["detail"]
    assert sb.db.get("essay_pyq_tags", []) == []


def test_unknown_format_is_rejected():
    sb = TaxSBStub(_seed())
    r = _post(sb, {"question_id": "q1", "theme_id": "th1", "format": "letter"})
    assert r.status_code == 422
    assert "format must be one of" in r.json()["detail"]
    assert sb.db.get("essay_pyq_tags", []) == []


# ── the pairing CHECK, mirrored at the router ─────────────────────────────


def test_essay_format_requires_an_essay_type():
    sb = TaxSBStub(_seed())
    r = _post(sb, {"question_id": "q1", "theme_id": "th1", "format": "essay"})
    assert r.status_code == 422
    assert "essay_type is required when format is 'essay'" in r.json()["detail"]
    assert sb.db.get("essay_pyq_tags", []) == []


def test_non_essay_format_rejects_an_essay_type():
    sb = TaxSBStub(_seed())
    r = _post(sb, {
        "question_id": "q1", "theme_id": "th1",
        "format": "precis", "essay_type": "quote_abstract",
    })
    assert r.status_code == 422
    assert "essay_type must be omitted when format is 'precis'" in r.json()["detail"]
    assert sb.db.get("essay_pyq_tags", []) == []


# ── bulk path carries the same contract ───────────────────────────────────


def test_bulk_config_requires_and_enum_checks_format():
    cfg = cms_api._IMPORT_CONFIG["essay-pyq-tags"]
    assert "format" in cfg["allowed"]
    assert "format" in cfg["required"]
    assert cfg["enums"]["format"] == ("essay", "precis", "comprehension")


# ── the worksheet's mixed-format batch round-trips ────────────────────────


def test_mixed_format_batch_persists_each_row_with_its_own_shape():
    """The RBI English worksheet is essay 16 / precis 4 / comprehension 4.

    One paper carries all three, so the three shapes must coexist in the table
    rather than one shape winning by default.
    """
    sb = TaxSBStub(_seed())
    rows = [
        {"question_id": "q1", "theme_id": "th1", "format": "essay", "essay_type": "issue_concrete"},
        {"question_id": "q2", "theme_id": "th1", "format": "precis"},
    ]
    for payload in rows:
        assert _post(sb, payload).status_code == 200

    stored = {r["format"]: r for r in sb.db["essay_pyq_tags"]}
    assert set(stored) == {"essay", "precis"}
    assert stored["essay"]["essay_type"] == "issue_concrete"
    assert stored["precis"].get("essay_type") is None
