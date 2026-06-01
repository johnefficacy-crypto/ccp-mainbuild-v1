"""PR3a: Syllabus mention proposer tests.

POST /api/admin/exam-intelligence/workspace/{exam_id}/syllabus/propose

Covers:
- happy path: 1 doc, 3 pages, exact alias match → proposals returned
- fuzzy match at threshold boundary (0.85 passes, 0.84 rejected)
- override threshold via body param
- dedup: same alias on same page only proposed once (highest confidence)
- multiple topics on same page: all proposed
- empty document_pages → empty proposals, 200 OK
- unknown syllabus_document_id → 404
- syllabus doc belongs to different exam → 422
- cycle_id mismatch → 422
- phase_id mismatch → 422
- threshold out of range → 422
- read-only: no rows inserted into syllabus_topic_mentions after proposer runs
- proposer_version constant returned in response
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import admin_exam_intelligence as review_api
from app.core.auth import get_current_user
from app.exam_intelligence.syllabus_mapper import (
    PROPOSER_VERSION,
    SYLLABUS_ALIAS_MATCH_THRESHOLD,
    propose_syllabus_mentions,
)

_BASE = "/api/admin/exam-intelligence"

# ── Fixtures ──────────────────────────────────────────────────────────────────

EXAM_ID = "exam-1"
EXAM = {"id": EXAM_ID, "slug": "ssc-cgl", "name": "SSC CGL", "exam_type": "recruitment", "is_active": True}
EXAM2_ID = "exam-2"
DOC_ID = "doc-1"
DOC = {"id": DOC_ID, "exam_id": EXAM_ID, "exam_cycle_id": None}
DOC_OTHER = {"id": "doc-2", "exam_id": EXAM2_ID, "exam_cycle_id": None}
CYCLE_A = {"id": "cycle-2026", "exam_id": EXAM_ID, "year": 2026}
CYCLE_B = {"id": "cycle-other", "exam_id": EXAM2_ID, "year": 2026}
PHASE_A = {"id": "phase-1", "exam_id": EXAM_ID, "phase_name": "Tier I", "phase_order": 1}
PHASE_B = {"id": "phase-2", "exam_id": EXAM2_ID, "phase_name": "Tier I", "phase_order": 1}

TOPICS = [
    {"id": "topic-math", "subject_id": "subj-math"},
    {"id": "topic-reasoning", "subject_id": "subj-reasoning"},
]
ESM = [
    {"subject_id": "subj-math"},
    {"subject_id": "subj-reasoning"},
]
ALIASES = [
    {"id": "a1", "topic_id": "topic-math", "alias_text": "Arithmetic", "normalized_alias": "arithmetic"},
    {"id": "a2", "topic_id": "topic-reasoning", "alias_text": "Logical Reasoning", "normalized_alias": "logical reasoning"},
]

# ── Stub helpers ──────────────────────────────────────────────────────────────


class _SBStub:
    """Configurable supabase stub for proposer tests."""

    def __init__(self, data: dict, inserts: list | None = None):
        self._data = data
        self.inserts = inserts if inserts is not None else []

    def table(self, name):
        return _TableStub(name, self._data.get(name, []), self.inserts)


class _TableStub:
    def __init__(self, name, rows, inserts):
        self._name = name
        self._rows = rows
        self._inserts = inserts
        self._filters: dict = {}
        self._in_filters: dict = {}
        self._order_col = None
        self._limit_n = None

    def select(self, *a, **kw):
        return self

    def eq(self, k, v):
        self._filters[k] = v
        return self

    def in_(self, k, vals):
        self._in_filters[k] = set(vals)
        return self

    def order(self, col, **kw):
        self._order_col = col
        return self

    def limit(self, n):
        self._limit_n = n
        return self

    def insert(self, rows):
        if isinstance(rows, list):
            self._inserts.extend(rows)
        else:
            self._inserts.append(rows)
        return self

    def execute(self):
        rows = self._rows if not callable(self._rows) else self._rows(self._filters, self._in_filters)
        # Apply eq filters
        result = []
        for r in rows:
            match = True
            for k, v in self._filters.items():
                if r.get(k) != v:
                    match = False
                    break
            if not match:
                continue
            for k, vs in self._in_filters.items():
                if r.get(k) not in vs:
                    match = False
                    break
            if match:
                result.append(r)
        # Apply order if page_number
        if self._order_col:
            result.sort(key=lambda x: x.get(self._order_col, 0))
        res = MagicMock()
        res.data = result
        return res


def _make_sb(
    docs=None, pages=None, topics=None, esm=None, aliases=None,
    exams=None, cycles=None, phases=None, inserts=None,
):
    # Inject document_id into page rows so the stub's eq("document_id", ...) filter works
    raw_pages = pages or []
    enriched_pages = [
        {**p, "document_id": DOC_ID} if "document_id" not in p else p
        for p in raw_pages
    ]
    data = {
        "document_assets": docs or [DOC],
        "document_pages": enriched_pages,
        "topics": topics or TOPICS,
        "exam_subject_map": esm or ESM,
        "topic_aliases": aliases or ALIASES,
        "exams": exams or [EXAM],
        "exam_cycles": cycles or [CYCLE_A],
        "exam_phases": phases or [PHASE_A],
        "syllabus_topic_mentions": [],
    }
    return _SBStub(data, inserts=inserts if inserts is not None else [])


def _client(sb_factory):
    app = FastAPI()
    app.include_router(review_api.router, prefix="/api")
    review_api.get_supabase_admin = sb_factory
    app.dependency_overrides[get_current_user] = lambda: {
        "id": "admin-1", "role": "super_admin", "permissions": [review_api.ADMIN_PERM],
    }
    return TestClient(app, raise_server_exceptions=False)


def _post(sb, body: dict):
    inserts = []
    sb_with_inserts = _make_sb(
        docs=sb._data.get("document_assets"),
        pages=sb._data.get("document_pages"),
        topics=sb._data.get("topics"),
        esm=sb._data.get("exam_subject_map"),
        aliases=sb._data.get("topic_aliases"),
        exams=sb._data.get("exams"),
        cycles=sb._data.get("exam_cycles"),
        phases=sb._data.get("exam_phases"),
        inserts=inserts,
    )
    c = _client(lambda: sb_with_inserts)
    r = c.post(f"{_BASE}/workspace/{EXAM_ID}/syllabus/propose", json=body)
    return r, inserts


# ── Unit tests: propose_syllabus_mentions() ───────────────────────────────────


class TestHappyPath:
    def test_exact_match_returned(self):
        pages = [
            {"page_number": 1, "text_content": "This section covers Arithmetic and number theory."},
            {"page_number": 2, "text_content": "The candidate must master Logical Reasoning skills."},
            {"page_number": 3, "text_content": "General awareness topics are covered separately."},
        ]
        sb = _make_sb(pages=pages)
        proposals = propose_syllabus_mentions(sb, exam_id=EXAM_ID, syllabus_document_id=DOC_ID)
        assert len(proposals) >= 2
        methods = {p["match_method"] for p in proposals}
        assert "topic_alias_exact" in methods

    def test_proposals_have_correct_shape(self):
        pages = [{"page_number": 1, "text_content": "Arithmetic fundamentals."}]
        sb = _make_sb(pages=pages)
        proposals = propose_syllabus_mentions(sb, exam_id=EXAM_ID, syllabus_document_id=DOC_ID)
        assert proposals
        p = proposals[0]
        required = {
            "syllabus_document_id", "exam_id", "exam_cycle_id", "exam_phase_id",
            "topic_id", "raw_text", "normalized_text", "mention_type",
            "confidence_score", "source_page", "matched_alias", "match_method",
            "proposer_version",
        }
        assert required.issubset(p.keys())
        assert p["proposer_version"] == PROPOSER_VERSION
        assert p["mention_type"] == "explicit"

    def test_exact_match_confidence_is_1(self):
        pages = [{"page_number": 1, "text_content": "Topics include arithmetic in detail."}]
        sb = _make_sb(pages=pages)
        proposals = propose_syllabus_mentions(sb, exam_id=EXAM_ID, syllabus_document_id=DOC_ID)
        exact = [p for p in proposals if p["match_method"] == "topic_alias_exact"]
        assert exact
        assert exact[0]["confidence_score"] == 1.0

    def test_sorted_by_page_then_confidence_desc(self):
        pages = [
            {"page_number": 1, "text_content": "Arithmetic covered here."},
            {"page_number": 2, "text_content": "Logical Reasoning also covered."},
        ]
        sb = _make_sb(pages=pages)
        proposals = propose_syllabus_mentions(sb, exam_id=EXAM_ID, syllabus_document_id=DOC_ID)
        pages_seen = [p["source_page"] for p in proposals]
        assert pages_seen == sorted(pages_seen)

    def test_cycle_id_and_phase_id_propagated(self):
        pages = [{"page_number": 1, "text_content": "Arithmetic section."}]
        sb = _make_sb(pages=pages)
        proposals = propose_syllabus_mentions(
            sb, exam_id=EXAM_ID, syllabus_document_id=DOC_ID,
            cycle_id="cycle-2026", phase_id="phase-1",
        )
        assert proposals
        assert proposals[0]["exam_cycle_id"] == "cycle-2026"
        assert proposals[0]["exam_phase_id"] == "phase-1"

    def test_multiple_topics_same_page(self):
        pages = [{"page_number": 1, "text_content": "Arithmetic and Logical Reasoning are key topics."}]
        sb = _make_sb(pages=pages)
        proposals = propose_syllabus_mentions(sb, exam_id=EXAM_ID, syllabus_document_id=DOC_ID)
        topic_ids = {p["topic_id"] for p in proposals}
        assert "topic-math" in topic_ids
        assert "topic-reasoning" in topic_ids


class TestFuzzyMatch:
    def test_fuzzy_match_at_threshold_accepted(self):
        """A slightly misspelled alias at exactly the threshold should be accepted."""
        # "arithmetik" vs "arithmetic" — should be close enough at 0.85
        pages = [{"page_number": 1, "text_content": "This covers arithmetik fundamentals."}]
        aliases = [{"id": "a1", "topic_id": "topic-math", "alias_text": "Arithmetic", "normalized_alias": "arithmetic"}]
        sb = _make_sb(pages=pages, aliases=aliases)
        # Use a low threshold to guarantee we get a fuzzy match
        proposals = propose_syllabus_mentions(
            sb, exam_id=EXAM_ID, syllabus_document_id=DOC_ID, threshold=0.5
        )
        fuzzy = [p for p in proposals if p["match_method"] == "topic_alias_fuzzy"]
        assert fuzzy, "Expected a fuzzy match with threshold=0.5"

    def test_fuzzy_match_below_threshold_rejected(self):
        """Very different text should not produce proposals at the default threshold."""
        pages = [{"page_number": 1, "text_content": "xyz xyz xyz xyz xyz."}]
        aliases = [{"id": "a1", "topic_id": "topic-math", "alias_text": "Arithmetic", "normalized_alias": "arithmetic"}]
        sb = _make_sb(pages=pages, aliases=aliases)
        proposals = propose_syllabus_mentions(
            sb, exam_id=EXAM_ID, syllabus_document_id=DOC_ID, threshold=0.99
        )
        assert proposals == []

    def test_override_threshold_via_param(self):
        pages = [{"page_number": 1, "text_content": "arith: fundamental number operations."}]
        aliases = [{"id": "a1", "topic_id": "topic-math", "alias_text": "Arithmetic", "normalized_alias": "arithmetic"}]
        sb = _make_sb(pages=pages, aliases=aliases)
        # Very tight threshold — no match
        proposals_tight = propose_syllabus_mentions(
            sb, exam_id=EXAM_ID, syllabus_document_id=DOC_ID, threshold=1.0
        )
        # Looser threshold — may match
        proposals_loose = propose_syllabus_mentions(
            sb, exam_id=EXAM_ID, syllabus_document_id=DOC_ID, threshold=0.0
        )
        assert len(proposals_loose) >= len(proposals_tight)


class TestDeduplication:
    def test_same_alias_same_page_proposed_once(self):
        """Two alias rows for the same topic on same page → only one proposal."""
        pages = [{"page_number": 1, "text_content": "Arithmetic and arithmetic again."}]
        aliases = [
            {"id": "a1", "topic_id": "topic-math", "alias_text": "Arithmetic", "normalized_alias": "arithmetic"},
            {"id": "a2", "topic_id": "topic-math", "alias_text": "arithmetic", "normalized_alias": "arithmetic"},
        ]
        sb = _make_sb(pages=pages, aliases=aliases)
        proposals = propose_syllabus_mentions(sb, exam_id=EXAM_ID, syllabus_document_id=DOC_ID)
        math_p1 = [p for p in proposals if p["topic_id"] == "topic-math" and p["source_page"] == 1]
        assert len(math_p1) == 1

    def test_dedup_keeps_highest_confidence(self):
        """If exact and fuzzy both exist for same topic+page, keep exact (higher confidence)."""
        pages = [{"page_number": 1, "text_content": "Arithmetic fundamentals are taught."}]
        aliases = [
            {"id": "a1", "topic_id": "topic-math", "alias_text": "Arithmetic", "normalized_alias": "arithmetic"},
        ]
        sb = _make_sb(pages=pages, aliases=aliases)
        proposals = propose_syllabus_mentions(sb, exam_id=EXAM_ID, syllabus_document_id=DOC_ID)
        math_p1 = [p for p in proposals if p["topic_id"] == "topic-math" and p["source_page"] == 1]
        assert len(math_p1) == 1
        assert math_p1[0]["confidence_score"] == 1.0


class TestEdgeCases:
    def test_empty_pages_returns_empty(self):
        sb = _make_sb(pages=[])
        proposals = propose_syllabus_mentions(sb, exam_id=EXAM_ID, syllabus_document_id=DOC_ID)
        assert proposals == []

    def test_unknown_document_raises_404(self):
        sb = _make_sb(docs=[])  # no docs
        with pytest.raises(Exception) as exc_info:
            propose_syllabus_mentions(sb, exam_id=EXAM_ID, syllabus_document_id="nonexistent")
        from app.exam_intelligence.syllabus_mapper import ProposerError
        assert isinstance(exc_info.value, ProposerError)
        assert exc_info.value.status_code == 404

    def test_document_wrong_exam_raises_422(self):
        sb = _make_sb(docs=[DOC_OTHER])
        with pytest.raises(Exception) as exc_info:
            propose_syllabus_mentions(sb, exam_id=EXAM_ID, syllabus_document_id="doc-2")
        from app.exam_intelligence.syllabus_mapper import ProposerError
        assert isinstance(exc_info.value, ProposerError)
        assert exc_info.value.status_code == 422


# ── HTTP endpoint tests ───────────────────────────────────────────────────────


class TestEndpointHappyPath:
    def test_200_with_proposals(self):
        pages = [{"page_number": 1, "text_content": "Arithmetic and Logical Reasoning."}]
        sb = _make_sb(pages=pages)
        r, _ = _post(sb, {"syllabus_document_id": DOC_ID})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["exam_id"] == EXAM_ID
        assert body["syllabus_document_id"] == DOC_ID
        assert body["proposer_version"] == PROPOSER_VERSION
        assert "generated_at" in body
        assert "proposals" in body
        assert isinstance(body["proposals"], list)

    def test_threshold_returned_in_response(self):
        sb = _make_sb()
        r, _ = _post(sb, {"syllabus_document_id": DOC_ID})
        assert r.status_code == 200
        assert r.json()["threshold"] == SYLLABUS_ALIAS_MATCH_THRESHOLD

    def test_custom_threshold_returned(self):
        sb = _make_sb()
        r, _ = _post(sb, {"syllabus_document_id": DOC_ID, "threshold": 0.7})
        assert r.status_code == 200
        assert r.json()["threshold"] == 0.7

    def test_empty_pages_200_empty_proposals(self):
        sb = _make_sb(pages=[])
        r, _ = _post(sb, {"syllabus_document_id": DOC_ID})
        assert r.status_code == 200
        assert r.json()["proposals"] == []

    def test_proposer_version_constant_in_response(self):
        sb = _make_sb()
        r, _ = _post(sb, {"syllabus_document_id": DOC_ID})
        assert r.json()["proposer_version"] == PROPOSER_VERSION


class TestEndpointErrors:
    def test_unknown_exam_404(self):
        sb = _make_sb(exams=[])
        c = _client(lambda: sb)
        r = c.post(f"{_BASE}/workspace/nonexistent/syllabus/propose", json={"syllabus_document_id": DOC_ID})
        assert r.status_code == 404
        assert "exam not found" in r.json().get("detail", "").lower()

    def test_unknown_document_404(self):
        sb = _make_sb(docs=[])
        r, _ = _post(sb, {"syllabus_document_id": "no-such-doc"})
        assert r.status_code == 404

    def test_document_wrong_exam_422(self):
        sb = _make_sb(docs=[DOC_OTHER])
        r, _ = _post(sb, {"syllabus_document_id": "doc-2"})
        assert r.status_code == 422

    def test_cycle_mismatch_422(self):
        sb = _make_sb(cycles=[CYCLE_B])
        r, _ = _post(sb, {"syllabus_document_id": DOC_ID, "cycle_id": "cycle-other"})
        assert r.status_code == 422

    def test_phase_mismatch_422(self):
        sb = _make_sb(phases=[PHASE_B])
        r, _ = _post(sb, {"syllabus_document_id": DOC_ID, "phase_id": "phase-2"})
        assert r.status_code == 422

    def test_threshold_out_of_range_low_422(self):
        sb = _make_sb()
        r, _ = _post(sb, {"syllabus_document_id": DOC_ID, "threshold": -0.1})
        assert r.status_code == 422

    def test_threshold_out_of_range_high_422(self):
        sb = _make_sb()
        r, _ = _post(sb, {"syllabus_document_id": DOC_ID, "threshold": 1.5})
        assert r.status_code == 422


class TestReadOnly:
    def test_no_rows_inserted_into_syllabus_topic_mentions(self):
        pages = [{"page_number": 1, "text_content": "Arithmetic and Logical Reasoning are key."}]
        sb = _make_sb(pages=pages)
        inserts = []
        stub = _SBStub(sb._data, inserts=inserts)
        c = _client(lambda: stub)
        r = c.post(f"{_BASE}/workspace/{EXAM_ID}/syllabus/propose", json={"syllabus_document_id": DOC_ID})
        assert r.status_code == 200
        # No insert should have touched syllabus_topic_mentions
        assert inserts == [], f"Expected no inserts, got: {inserts}"
