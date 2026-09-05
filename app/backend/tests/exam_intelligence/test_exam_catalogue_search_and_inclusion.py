"""`GET /api/exam-intelligence/exams` — search predicate and inclusion rule.

Two defects this pins:

1. **``?q=`` was ignored.** The route declared only ``limit``, so FastAPI
   dropped an unknown ``q`` silently: ``?q=rbi`` and ``?q=sebi`` both returned
   the whole catalogue with no error and no hint that the filter had not run.

2. **What decides membership.** The catalogue is gated by ``exams.is_active``
   and nothing else. ``"verified_only": true`` in the payload is a router-wide
   contract marker, NOT a filter here — an exam with zero verified papers and
   zero verified questions is listed if it is active, and an exam with a fully
   published question bank is absent if it is not. These tests fix that rule in
   place so neither half can drift into the other.
"""
from __future__ import annotations

import pytest

from app.exam_intelligence import lookup
from app.exam_intelligence.lookup import (
    exam_matches_query,
    exam_search_haystack,
    filter_exams_by_query,
    list_active_exams,
)
from tests.exam_intelligence._capping_stub import CappingSB


def _exam(slug: str, name: str, *, exam_type: str = "recruitment", is_active: bool = True) -> dict:
    return {
        "id": f"id-{slug}",
        "slug": slug,
        "name": name,
        "exam_type": exam_type,
        "default_difficulty_level": None,
        "exam_family_id": "62e979f9-0e21-4492-8f96-6f2944fc7d82",
        "is_active": is_active,
    }


# The four financial-regulatory siblings from the live report: same family,
# same exam_type, differing only in is_active before the data correction.
REGULATORY = [
    _exam("rbi-grade-b", "RBI Grade B Officer"),
    _exam("sebi-grade-a", "SEBI Grade A Officer"),
    _exam("ifsca-grade-a", "IFSCA Grade A Officer"),
    _exam("pfrda-grade-a", "PFRDA Grade A Officer"),
]


# ── 1. the search predicate ──────────────────────────────────────────────

@pytest.mark.parametrize(
    "query,slug",
    [
        ("rbi", "rbi-grade-b"),
        ("RBI", "rbi-grade-b"),            # case-insensitive
        ("  sebi  ", "sebi-grade-a"),      # surrounding whitespace ignored
        ("ifsca", "ifsca-grade-a"),
        ("pfrda", "pfrda-grade-a"),
        ("pfrda-grade-a", "pfrda-grade-a"),  # a slug pasted verbatim
        ("pfrda grade a", "pfrda-grade-a"),  # separator-flattened form
        ("pfrdagradea", "pfrda-grade-a"),    # collapsed form
        ("Officer", "rbi-grade-b"),          # matches on name
        ("recruitment", "rbi-grade-b"),      # matches on exam_type
    ],
)
def test_query_selects_the_right_exam(query: str, slug: str):
    out = filter_exams_by_query(REGULATORY, query)
    assert slug in {e["slug"] for e in out}


@pytest.mark.parametrize("query", ["rbi", "sebi", "ifsca", "pfrda"])
def test_a_body_specific_query_excludes_the_other_bodies(query: str):
    """The reported symptom: ?q=rbi and ?q=sebi each returned ALL exams."""
    out = filter_exams_by_query(REGULATORY, query)
    assert [e["slug"] for e in out] == [f"{query}-grade-{'b' if query == 'rbi' else 'a'}"]


def test_query_that_matches_nothing_returns_nothing_not_everything():
    assert filter_exams_by_query(REGULATORY, "nabard") == []


@pytest.mark.parametrize("query", [None, "", "   "])
def test_blank_query_means_no_filter_never_no_results(query):
    """An absent filter must return the full catalogue, not an empty one."""
    assert filter_exams_by_query(REGULATORY, query) == REGULATORY


def test_filter_preserves_the_callers_ordering():
    ordered = list(reversed(REGULATORY))
    out = filter_exams_by_query(ordered, "grade")
    assert [e["slug"] for e in out] == [e["slug"] for e in ordered]


def test_haystack_indexes_name_slug_and_exam_type_in_both_forms():
    hay = exam_search_haystack(
        {"name": "Civil Services Examination", "slug": "upsc-cse", "exam_type": "civil_services"}
    )
    assert "upsc cse" in hay          # separators flattened
    assert "upsccse" in hay          # collapsed form also indexed
    assert "civil services" in hay


def test_haystack_tolerates_missing_and_null_fields():
    assert exam_search_haystack({}).strip() == ""
    assert exam_search_haystack(None).strip() == ""
    assert exam_search_haystack({"name": None, "slug": "x-y", "exam_type": None}).startswith("x y")


def test_matcher_is_symmetric_with_the_frontend_contract():
    """Both sides normalize the QUERY as well as the text, so a learner can
    paste `ifsca-grade-a` and a caller can send `?q=IFSCA Grade A`."""
    exam = _exam("ifsca-grade-a", "IFSCA Grade A Officer")
    for q in ("ifsca-grade-a", "IFSCA Grade A", "ifsca_grade_a", "ifscagradea", "IFSCA"):
        assert exam_matches_query(exam, q), q


# ── 2. the inclusion rule ────────────────────────────────────────────────

def test_is_active_is_the_only_gate_verified_content_is_irrelevant():
    """rbi-grade-b is listed with zero verified papers/questions; a fully
    published-but-inactive exam is not. Membership tracks is_active alone."""
    lookup.invalidate_exam_lookup_cache()
    rows = [
        _exam("rbi-grade-b", "RBI Grade B Officer"),                        # no verified content
        _exam("ifsca-grade-a", "IFSCA Grade A Officer", is_active=False),   # 362 published bank rows
        _exam("pfrda-grade-a", "PFRDA Grade A Officer", is_active=False),   # 142 published bank rows
    ]
    out = {r["slug"] for r in list_active_exams(CappingSB({"exams": rows}, server_cap=lookup._PAGE))}
    assert out == {"rbi-grade-b"}


def test_flipping_is_active_true_admits_the_exam_once_the_cache_is_invalidated():
    """The data correction the operator made. Invalidation is the contract for
    any writer that mutates `exams` — a direct-SQL fix bypasses it and is
    invisible until the TTL lapses, which is the staleness window to rule out
    before suspecting the code."""
    lookup.invalidate_exam_lookup_cache()
    rows = [
        _exam("sebi-grade-a", "SEBI Grade A Officer"),
        _exam("ifsca-grade-a", "IFSCA Grade A Officer", is_active=False),
    ]
    sb = CappingSB({"exams": rows}, server_cap=lookup._PAGE)
    assert {r["slug"] for r in list_active_exams(sb)} == {"sebi-grade-a"}

    rows[1]["is_active"] = True
    # Still stale — the cached snapshot is what an operator sees post-fix.
    assert {r["slug"] for r in list_active_exams(sb)} == {"sebi-grade-a"}

    lookup.invalidate_exam_lookup_cache()
    assert {r["slug"] for r in list_active_exams(sb)} == {"sebi-grade-a", "ifsca-grade-a"}


def test_a_failed_page_read_is_never_cached():
    """A partial read must not be pinned for the cache TTL: that presents as
    an exam silently missing from the catalogue with no error anywhere."""
    lookup.invalidate_exam_lookup_cache()
    rows = [_exam(f"exam-{i:04d}", f"Exam {i:04d}") for i in range(3)]
    sb = CappingSB({"exams": rows}, server_cap=lookup._PAGE)

    calls = {"n": 0}
    real_table = sb.table

    def _failing_table(name: str):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("Error 500: transient read failure")
        return real_table(name)

    sb.table = _failing_table  # type: ignore[method-assign]
    assert list_active_exams(sb) == []          # degrades gracefully
    sb.table = real_table                        # type: ignore[method-assign]
    # The failure must NOT have been cached as "the catalogue is empty".
    assert {r["slug"] for r in list_active_exams(sb)} == {r["slug"] for r in rows}


def test_a_complete_read_is_cached():
    """The TTL cache still does its job for a healthy read (one DB walk)."""
    lookup.invalidate_exam_lookup_cache()
    rows = [_exam("sebi-grade-a", "SEBI Grade A Officer")]
    sb = CappingSB({"exams": rows}, server_cap=lookup._PAGE)
    seen = {"n": 0}
    real_table = sb.table

    def _counting_table(name: str):
        seen["n"] += 1
        return real_table(name)

    sb.table = _counting_table  # type: ignore[method-assign]
    list_active_exams(sb)
    first = seen["n"]
    list_active_exams(sb)
    assert seen["n"] == first, "second call must be served from cache"


# ── 3. the route actually applies ?q= ────────────────────────────────────

def _client(sb):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api import exam_intelligence as read_api
    from app.core.auth import get_current_user

    app = FastAPI()
    app.include_router(read_api.router, prefix="/api")
    read_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    return TestClient(app)


@pytest.fixture()
def catalogue_client():
    lookup.invalidate_exam_lookup_cache()
    client = _client(CappingSB({"exams": list(REGULATORY)}, server_cap=lookup._PAGE))
    yield client
    lookup.invalidate_exam_lookup_cache()


def test_route_applies_q_instead_of_dropping_it(catalogue_client):
    """The exact reported call. Before the fix the route declared no `q`, so
    FastAPI discarded it and returned the entire catalogue."""
    body = catalogue_client.get("/api/exam-intelligence/exams", params={"q": "rbi"}).json()
    assert [e["slug"] for e in body["items"]] == ["rbi-grade-b"]
    assert body["count"] == 1
    assert body["query"] == "rbi"


def test_route_without_q_returns_the_whole_catalogue(catalogue_client):
    body = catalogue_client.get("/api/exam-intelligence/exams").json()
    assert len(body["items"]) == len(REGULATORY)
    assert body["count"] == len(REGULATORY)
    assert body["query"] is None


def test_two_different_queries_do_not_return_the_same_set(catalogue_client):
    """?q=rbi and ?q=sebi returning identical payloads was the tell."""
    rbi = catalogue_client.get("/api/exam-intelligence/exams", params={"q": "rbi"}).json()
    sebi = catalogue_client.get("/api/exam-intelligence/exams", params={"q": "sebi"}).json()
    assert rbi["items"] != sebi["items"]


def test_route_reports_an_honest_empty_result(catalogue_client):
    body = catalogue_client.get("/api/exam-intelligence/exams", params={"q": "nabard"}).json()
    assert body["items"] == []
    assert body["count"] == 0
    assert body["query"] == "nabard"


def test_verified_only_stays_true_and_gates_nothing(catalogue_client):
    """rbi-grade-b has no verified papers/questions and is still listed."""
    body = catalogue_client.get("/api/exam-intelligence/exams").json()
    assert body["verified_only"] is True
    assert "rbi-grade-b" in {e["slug"] for e in body["items"]}
