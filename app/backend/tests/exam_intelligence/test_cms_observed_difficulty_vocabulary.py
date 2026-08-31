"""The CMS write path constrains ``observed_difficulty`` to easy|medium|hard.

``pyq_questions.observed_difficulty`` is bare ``text`` (migration 032, no
CHECK), so this endpoint is the enforcement point for every question written
through the CMS — including the PyqPaperWorkspace difficulty dropdown and the
generic ExamIntelCms entity editor.

Those three are the only values migration 239's projection to
``mock_question_bank`` recognises; it rewrites anything else to ``medium``
without warning. A ``very_hard`` accepted here therefore reads as ``hard`` in
the PYQ difficulty heatmap, ``medium`` in the projected bank, and weights 1.0
instead of 1.5 in ``mastery_delta``. These tests are about rejection.

NULL stays legal: a question with no recorded difficulty is a real state, and
the regulatory corpus is entirely in it.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intel_cms as cms_api
from app.core.auth import get_current_user
from tests.persona_questions._stub import SBStub

_BASE = "/api/admin/exam-intelligence-cms"

# Every value known to have reached, or been offered into, this column outside
# the canonical set. `medium_high` is in the live corpus and no surface ever
# offered it; `very_hard` and `moderate` were offered by the two admin
# dropdowns until this change.
_NON_CANONICAL = ["very_hard", "medium_high", "moderate", "tough", "easy_low", "HARD"]


def _client(sb: SBStub) -> TestClient:
    app = FastAPI()
    app.include_router(cms_api.router, prefix="/api")
    cms_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[cms_api._flag_enabled] = lambda: None
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": "super_admin", "permissions": [cms_api.PERM_CMS],
    }
    return TestClient(app, raise_server_exceptions=False)


def _seed(questions: list[dict] | None = None) -> dict:
    return {
        "pyq_papers": [{"id": "p1", "exam_id": "e1"}],
        "pyq_questions": list(questions or []),
        "pyq_options": [],
        "admin_audit_logs": [],
    }


def _create_payload(**overrides) -> dict:
    body = {
        "pyq_paper_id": "p1",
        "question_text": "Consider the following statements.",
        "question_type": "mcq",
    }
    body.update(overrides)
    return {"reason": "vocabulary test", "payload": body}


class TestCreate:
    @pytest.mark.parametrize("bad", _NON_CANONICAL)
    def test_non_canonical_rejected(self, bad):
        sb = SBStub(_seed())
        r = _client(sb).post(
            f"{_BASE}/pyq-questions", json=_create_payload(observed_difficulty=bad)
        )
        assert r.status_code == 422, r.text
        assert "observed_difficulty" in r.json()["detail"]
        # Rejected means nothing written — not the bad value, not a coerced one.
        assert sb.db["pyq_questions"] == []

    @pytest.mark.parametrize("good", ["easy", "medium", "hard"])
    def test_canonical_accepted(self, good):
        sb = SBStub(_seed())
        r = _client(sb).post(
            f"{_BASE}/pyq-questions", json=_create_payload(observed_difficulty=good)
        )
        assert r.status_code == 200, r.text
        assert sb.db["pyq_questions"][0]["observed_difficulty"] == good

    def test_omitted_and_null_accepted(self):
        sb = SBStub(_seed())
        client = _client(sb)
        assert client.post(f"{_BASE}/pyq-questions", json=_create_payload()).status_code == 200
        r = client.post(
            f"{_BASE}/pyq-questions", json=_create_payload(observed_difficulty=None)
        )
        assert r.status_code == 200, r.text
        assert all(q.get("observed_difficulty") in (None, "") for q in sb.db["pyq_questions"])


class TestUpdate:
    @pytest.mark.parametrize("bad", _NON_CANONICAL)
    def test_non_canonical_patch_rejected(self, bad):
        sb = SBStub(_seed([{
            "id": "q1", "pyq_paper_id": "p1", "question_text": "Q",
            "question_type": "mcq", "observed_difficulty": "medium",
            "reviewer_status": "pending",
        }]))
        r = _client(sb).patch(
            f"{_BASE}/pyq-questions/q1",
            json={"reason": "vocabulary test", "payload": {"observed_difficulty": bad}},
        )
        assert r.status_code == 422, r.text
        assert "observed_difficulty" in r.json()["detail"]
        assert sb.db["pyq_questions"][0]["observed_difficulty"] == "medium"

    def test_canonical_patch_accepted(self):
        sb = SBStub(_seed([{
            "id": "q1", "pyq_paper_id": "p1", "question_text": "Q",
            "question_type": "mcq", "observed_difficulty": "medium",
            "reviewer_status": "pending",
        }]))
        r = _client(sb).patch(
            f"{_BASE}/pyq-questions/q1",
            json={"reason": "vocabulary test", "payload": {"observed_difficulty": "hard"}},
        )
        assert r.status_code == 200, r.text
        assert sb.db["pyq_questions"][0]["observed_difficulty"] == "hard"

    def test_legacy_row_cannot_be_saved_back_unchanged(self):
        """A row already holding a non-canonical value cannot be re-saved with
        that value still in the payload. This is the intended signal: the
        operator has to correct the field rather than carry it forward.
        """
        sb = SBStub(_seed([{
            "id": "q1", "pyq_paper_id": "p1", "question_text": "Q",
            "question_type": "mcq", "observed_difficulty": "very_hard",
            "reviewer_status": "pending",
        }]))
        r = _client(sb).patch(
            f"{_BASE}/pyq-questions/q1",
            json={"reason": "edit something else", "payload": {
                "question_text": "Q revised", "observed_difficulty": "very_hard",
            }},
        )
        assert r.status_code == 422, r.text
        assert sb.db["pyq_questions"][0]["question_text"] == "Q"


class TestBulkCreate:
    """The bulk-create registry is a third writer into the same column."""

    def _post(self, sb: SBStub, rows: list[dict]):
        return _client(sb).post(
            f"{_BASE}/bulk-import",
            json={"reason": "vocabulary test", "entity": "pyq-questions", "rows": rows},
        )

    def _row(self, **overrides) -> dict:
        row = {"pyq_paper_id": "p1", "question_text": "Bulk stem?", "question_type": "mcq"}
        row.update(overrides)
        return row

    @pytest.mark.parametrize("bad", ["very_hard", "medium_high", "moderate"])
    def test_non_canonical_row_rejected(self, bad):
        sb = SBStub(_seed())
        r = self._post(sb, [self._row(observed_difficulty=bad)])
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok_count"] == 0
        assert body["error_count"] == 1
        assert any("observed_difficulty" in (row.get("error") or "") for row in body["results"])
        assert sb.db["pyq_questions"] == []

    def test_canonical_and_null_rows_accepted(self):
        sb = SBStub(_seed())
        r = self._post(sb, [
            self._row(question_text="A?", observed_difficulty="easy"),
            self._row(question_text="B?", observed_difficulty="medium"),
            self._row(question_text="C?", observed_difficulty="hard"),
            self._row(question_text="D?"),
        ])
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok_count"] == 4, body
        assert body["error_count"] == 0
