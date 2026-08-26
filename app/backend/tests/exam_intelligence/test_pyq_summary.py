"""Tests for the learner PYQ summary endpoint + /pyqs phase/subject enrichment
(PR #942 P1 — items 8 & 9)."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import exam_intelligence as ei_api
from app.core.auth import get_current_user
from app.exam_intelligence import pyq_papers
from tests.exam_intelligence._capping_stub import CappingSB
from tests.persona_questions._stub import SBStub


def _large_pyq_db(n: int) -> dict[str, Any]:
    """One verified paper carrying ``n`` verified questions, each primary-tagged
    to one subject. Zero-padded ids give a stable ``.order('id')`` window."""
    return {
        "exams": [{"id": "e1", "slug": "upsc-cse"}],
        "pyq_papers": [{"id": "p1", "exam_id": "e1", "year": 2024, "exam_phase_id": None, "trust_status": "verified"}],
        "subjects": [{"id": "s1", "name": "General Studies", "is_active": True}],
        "topics": [{"id": "t1", "subject_id": "s1", "is_active": True}],
        "pyq_questions": [
            {"id": f"q{i:06d}", "pyq_paper_id": "p1", "observed_difficulty": "medium", "reviewer_status": "verified"}
            for i in range(n)
        ],
        "pyq_question_topic_tags": [
            {"question_id": f"q{i:06d}", "topic_id": "t1", "tag_role": "primary", "reviewer_status": "verified"}
            for i in range(n)
        ],
    }


def _build_app(sb: SBStub):
    app = FastAPI()
    app.include_router(ei_api.router, prefix="/api")
    ei_api.get_supabase_admin = lambda: sb  # type: ignore[assignment]
    app.dependency_overrides[get_current_user] = lambda: {"id": "u-1", "role": "user", "permissions": []}
    return app


def _seed() -> dict[str, Any]:
    return {
        "exams": [{"id": "e1", "slug": "upsc-cse"}],
        "exam_phases": [{"id": "ph1", "phase_slug": "prelims", "phase_name": "Prelims"}],
        "subjects": [{"id": "s1", "name": "General Studies"}],
        "topics": [{"id": "t1", "subject_id": "s1", "name": "Polity"}],
        "pyq_papers": [
            {"id": "p1", "exam_id": "e1", "year": 2024, "exam_phase_id": "ph1", "trust_status": "verified"},
            {"id": "p2", "exam_id": "e1", "year": 2023, "exam_phase_id": "ph1", "trust_status": "verified"},
            # unverified paper — must be excluded
            {"id": "p3", "exam_id": "e1", "year": 2022, "exam_phase_id": "ph1", "trust_status": "pending"},
        ],
        "pyq_questions": [
            {"id": "q1", "pyq_paper_id": "p1", "question_number": 1, "question_text": "Q1", "observed_difficulty": "medium", "reviewer_status": "verified"},
            {"id": "q2", "pyq_paper_id": "p1", "question_number": 2, "question_text": "Q2", "observed_difficulty": "hard", "reviewer_status": "verified"},
            {"id": "q3", "pyq_paper_id": "p2", "question_number": 1, "question_text": "Q3", "observed_difficulty": "medium", "reviewer_status": "verified"},
            # unverified / paper-excluded questions
            {"id": "q4", "pyq_paper_id": "p2", "question_number": 2, "question_text": "Q4", "observed_difficulty": "easy", "reviewer_status": "pending"},
            {"id": "q5", "pyq_paper_id": "p3", "question_number": 1, "question_text": "Q5", "observed_difficulty": "easy", "reviewer_status": "verified"},
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t1", "tag_role": "primary", "reviewer_status": "verified"},
            {"question_id": "q2", "topic_id": "t1", "tag_role": "primary", "reviewer_status": "verified"},
            {"question_id": "q3", "topic_id": "t1", "tag_role": "primary", "reviewer_status": "verified"},
        ],
        "pyq_options": [
            {"id": "o1", "question_id": "q1", "option_label": "A", "option_text": "one", "is_correct": True},
        ],
        # Projected bank rows; practice-ready requires an ACTIVE projection AND a
        # snapshot-ready row (options + correct_option_id).
        "mock_question_bank": [
            {"id": "b1", "exam_id": "e1", "pyq_paper_id": "p1", "pyq_question_id": "q1", "reviewer_status": "verified", "valid_until": None, "question_text": "Q1", "question_type": "mcq", "correct_option_id": "mo1a"},
            {"id": "b2", "exam_id": "e1", "pyq_paper_id": "p1", "pyq_question_id": "q2", "reviewer_status": "verified", "valid_until": None, "question_text": "Q2", "question_type": "mcq", "correct_option_id": "mo2a"},
            {"id": "b3", "exam_id": "e1", "pyq_paper_id": "p2", "pyq_question_id": "q3", "reviewer_status": "verified", "valid_until": None, "question_text": "Q3", "question_type": "mcq", "correct_option_id": "mo3a"},
        ],
        "mock_question_options": [
            {"id": "mo1a", "question_id": "b1", "option_index": 0, "option_text": "one", "is_correct": True},
            {"id": "mo1b", "question_id": "b1", "option_index": 1, "option_text": "two", "is_correct": False},
            {"id": "mo2a", "question_id": "b2", "option_index": 0, "option_text": "one", "is_correct": True},
            {"id": "mo2b", "question_id": "b2", "option_index": 1, "option_text": "two", "is_correct": False},
            {"id": "mo3a", "question_id": "b3", "option_index": 0, "option_text": "one", "is_correct": True},
            {"id": "mo3b", "question_id": "b3", "option_index": 1, "option_text": "two", "is_correct": False},
        ],
        "pyq_mock_question_projections": [
            {"mock_question_id": "b1", "sync_status": "active"},
            {"mock_question_id": "b2", "sync_status": "active"},
            # b3 projection is NOT active → p2 has 0 practice-ready
            {"mock_question_id": "b3", "sync_status": "inactive"},
        ],
    }


def _summary(sb: SBStub) -> dict:
    client = TestClient(_build_app(sb))
    r = client.get("/api/exam-intelligence/exams/upsc-cse/pyq-summary")
    assert r.status_code == 200
    return r.json()


def test_pyq_summary_verified_only():
    body = _summary(SBStub(_seed()))
    # p3 (pending paper) and q4 (pending question) / q5 (on pending paper) excluded.
    assert body["totals"]["papers"] == 2
    assert body["totals"]["questions"] == 3
    assert {p["paper_id"] for p in body["papers"]} == {"p1", "p2"}


def test_pyq_summary_counts_by_year_phase_subject_difficulty():
    body = _summary(SBStub(_seed()))
    by_year = {row["year"]: row for row in body["by_year"]}
    assert by_year[2024]["questions"] == 2 and by_year[2024]["papers"] == 1
    assert by_year[2023]["questions"] == 1 and by_year[2023]["papers"] == 1

    by_phase = {row["phase_slug"]: row for row in body["by_phase"]}
    assert by_phase["prelims"]["questions"] == 3
    assert by_phase["prelims"]["phase_name"] == "Prelims"

    by_diff = {row["difficulty"]: row["questions"] for row in body["by_difficulty"]}
    assert by_diff == {"medium": 2, "hard": 1}

    by_subject = {row["subject_name"]: row["questions"] for row in body["by_subject"]}
    assert by_subject == {"General Studies": 3}


def test_pyq_summary_paper_practice_ready_count_uses_active_projection():
    body = _summary(SBStub(_seed()))
    papers = {p["paper_id"]: p for p in body["papers"]}
    # p1: b1 + b2 active → 2 ready, enabled.
    assert papers["p1"]["practice_ready_count"] == 2
    assert papers["p1"]["practice_enabled"] is True
    # p2: b3 projection inactive → 0 ready, disabled (even though q3 is verified).
    assert papers["p2"]["practice_ready_count"] == 0
    assert papers["p2"]["practice_enabled"] is False
    assert body["totals"]["projected_practice_ready"] == 2


def test_practice_ready_ignores_active_projection_on_unverified_paper():
    """An active, snapshot-ready projected bank row on a PENDING paper must not
    inflate the verified-only summary totals (checkpost #944 finding 1)."""
    seed = _seed()
    # b4 is fully launchable BUT its paper p3 is pending (excluded from summary).
    seed["mock_question_bank"].append(
        {"id": "b4", "exam_id": "e1", "pyq_paper_id": "p3", "pyq_question_id": "q5", "reviewer_status": "verified", "valid_until": None, "question_text": "Q5", "question_type": "mcq", "correct_option_id": "mo4a"}
    )
    seed["mock_question_options"] += [
        {"id": "mo4a", "question_id": "b4", "option_index": 0, "option_text": "one", "is_correct": True},
        {"id": "mo4b", "question_id": "b4", "option_index": 1, "option_text": "two", "is_correct": False},
    ]
    seed["pyq_mock_question_projections"].append({"mock_question_id": "b4", "sync_status": "active"})

    body = _summary(SBStub(seed))
    # Still only p1's two ready rows — p3 is not a verified paper.
    assert body["totals"]["projected_practice_ready"] == 2
    assert {p["paper_id"] for p in body["papers"]} == {"p1", "p2"}


def test_practice_ready_excludes_snapshot_unready_row():
    """An active projection whose frozen snapshot lacks options/correct answer
    must not count as practice-ready (checkpost #944 finding 2)."""
    seed = _seed()
    # b5 on p1: active projection, but no options and no correct_option_id.
    seed["mock_question_bank"].append(
        {"id": "b5", "exam_id": "e1", "pyq_paper_id": "p1", "pyq_question_id": "q1", "reviewer_status": "verified", "valid_until": None, "question_text": "broken", "question_type": "mcq", "correct_option_id": None}
    )
    seed["pyq_mock_question_projections"].append({"mock_question_id": "b5", "sync_status": "active"})

    body = _summary(SBStub(seed))
    papers = {p["paper_id"]: p for p in body["papers"]}
    # p1 still only 2 ready (b1, b2) — the broken b5 does not count.
    assert papers["p1"]["practice_ready_count"] == 2
    assert body["totals"]["projected_practice_ready"] == 2


def test_by_subject_untagged_bucket_sums_to_total():
    """Verified questions with no primary-subject mapping fall into an explicit
    'Untagged' bucket so by_subject sums to totals.questions (finding 3)."""
    seed = _seed()
    # q3 loses its primary subject tag → becomes untagged.
    seed["pyq_question_topic_tags"] = [t for t in seed["pyq_question_topic_tags"] if t["question_id"] != "q3"]
    body = _summary(SBStub(seed))
    by_subject = {row["subject_name"]: row["questions"] for row in body["by_subject"]}
    assert by_subject.get("General Studies") == 2
    assert by_subject.get("Untagged") == 1
    assert sum(row["questions"] for row in body["by_subject"]) == body["totals"]["questions"]


def test_pyq_summary_paper_card_exposes_reviewed_set_identity():
    """Two same-year/same-phase papers must be distinguishable on the learner
    card via reviewed paper_code + set label (audit 2026-07-14 defect #1)."""
    seed = _seed()
    # Two CSAT papers, identical year + phase, differing only by set.
    seed["pyq_papers"] = [
        {"id": "p1", "exam_id": "e1", "year": 2025, "exam_phase_id": "ph1",
         "trust_status": "verified", "paper_code": "GS-PAPER-II-CSAT",
         "metadata": {"set_code": "A", "paper_set": "SET-A", "note": "internal-only"}},
        {"id": "p2", "exam_id": "e1", "year": 2025, "exam_phase_id": "ph1",
         "trust_status": "verified", "paper_code": "GS-PAPER-II-CSAT",
         "metadata": {"set_code": "B", "paper_set": "SET-B", "note": "internal-only"}},
    ]
    body = _summary(SBStub(seed))
    cards = {p["paper_id"]: p for p in body["papers"]}
    assert cards["p1"]["paper_code"] == "GS-PAPER-II-CSAT"
    assert cards["p1"]["set_label"] == "Set A"
    assert cards["p2"]["set_label"] == "Set B"
    # Same year + phase, yet each card carries a distinct reviewed identity.
    assert cards["p1"]["year"] == cards["p2"]["year"] == 2025
    assert cards["p1"]["phase_slug"] == cards["p2"]["phase_slug"] == "prelims"
    assert cards["p1"]["set_label"] != cards["p2"]["set_label"]
    # The raw metadata blob (internal notes) is never surfaced on the card.
    assert "metadata" not in cards["p1"]
    assert "note" not in cards["p1"]


def test_pyq_summary_set_label_falls_back_to_paper_set():
    """When only paper_set is present it is normalized to a 'Set X' label; a
    paper with no set identity carries a null label (no set pill)."""
    seed = _seed()
    seed["pyq_papers"] = [
        {"id": "p1", "exam_id": "e1", "year": 2025, "exam_phase_id": "ph1",
         "trust_status": "verified", "paper_code": "GS-PAPER-II-CSAT",
         "metadata": {"paper_set": "SET-B"}},
        {"id": "p2", "exam_id": "e1", "year": 2024, "exam_phase_id": "ph1",
         "trust_status": "verified", "paper_code": "GS-PAPER-I", "metadata": {}},
    ]
    body = _summary(SBStub(seed))
    cards = {p["paper_id"]: p for p in body["papers"]}
    assert cards["p1"]["set_label"] == "Set B"
    assert cards["p2"]["set_label"] is None


def test_pyq_summary_totals_survive_server_row_cap(monkeypatch):
    """The exam's true verified-question total exceeds one server page. A single
    unordered ``.limit()`` read truncates to the cap (~1000); deterministic
    ``.order('id').range()`` pagination reports the exact total."""
    cap = ei_api._PAGE
    n = cap + 300  # > one page → forces a second range() page
    sb = CappingSB(_large_pyq_db(n), server_cap=cap)
    monkeypatch.setattr(ei_api, "get_supabase_admin", lambda: sb)

    body = ei_api.get_exam_pyq_summary("upsc-cse", _user={"id": "u"})
    assert body["totals"]["questions"] == n  # not truncated to `cap`
    assert body["totals"]["papers"] == 1
    # every question is primary-tagged here, so by_subject sums to the total.
    assert sum(row["questions"] for row in body["by_subject"]) == n


def test_all_three_sources_agree_on_verified_count(monkeypatch):
    """The bug was three endpoints reporting three different verified counts for
    one exam. On a corpus larger than one server page, the heatmap count and the
    summary total must now be identical, and the heatmap breakdown must be
    non-empty and sum to that same number."""
    cap = ei_api._PAGE
    assert cap == pyq_papers._PAGE  # both modules page at the same size
    n = cap + 300
    db = _large_pyq_db(n)

    heatmap = pyq_papers.difficulty_heatmap(CappingSB(db, server_cap=cap), "e1")

    sb = CappingSB(db, server_cap=cap)
    monkeypatch.setattr(ei_api, "get_supabase_admin", lambda: sb)
    summary = ei_api.get_exam_pyq_summary("upsc-cse", _user={"id": "u"})

    assert heatmap["verified_question_count"] == n
    assert summary["totals"]["questions"] == n
    assert heatmap["verified_question_count"] == summary["totals"]["questions"]
    assert heatmap["rows"], "breakdown non-empty whenever the count is > 0"
    assert sum(r["total"] for r in heatmap["rows"]) == n


def test_pyq_list_includes_phase_and_subject_metadata():
    client = TestClient(_build_app(SBStub(_seed())))
    r = client.get("/api/exam-intelligence/exams/upsc-cse/pyqs?page=1&page_size=20")
    assert r.status_code == 200
    items = {it["id"]: it for it in r.json()["items"]}
    q1 = items["q1"]
    assert q1["phase_slug"] == "prelims"
    assert q1["phase_name"] == "Prelims"
    assert q1["subject_name"] == "General Studies"
    assert q1["topic_names"] == ["Polity"]
