"""Tests for the PYQ paper list + difficulty heatmap."""
from __future__ import annotations

from app.exam_intelligence import pyq_papers
from app.exam_intelligence.pyq_papers import (
    difficulty_heatmap,
    verified_pyq_papers,
)
from tests.exam_intelligence._capping_stub import CappingSB
from tests.persona_questions._stub import SBStub


def _heatmap_db(n_a: int, n_b: int, n_untagged: int = 0) -> dict:
    """One verified paper with ``n_a`` questions primary-tagged to subject A,
    ``n_b`` to subject B, and ``n_untagged`` verified questions with no primary
    tag. Zero-padded ids give a stable ``.order('id')`` for range pagination.
    ``_DIFFICULTY_BUCKETS`` are cycled so every bucket is exercised."""
    buckets = ["easy", "Medium", "hard", None]
    questions: list[dict] = []
    tags: list[dict] = []
    i = 0
    for _ in range(n_a):
        qid = f"q{i:06d}"
        questions.append({"id": qid, "pyq_paper_id": "p1", "observed_difficulty": buckets[i % 4], "reviewer_status": "verified"})
        tags.append({"question_id": qid, "topic_id": "t-a", "tag_role": "primary", "reviewer_status": "verified"})
        i += 1
    for _ in range(n_b):
        qid = f"q{i:06d}"
        questions.append({"id": qid, "pyq_paper_id": "p1", "observed_difficulty": buckets[i % 4], "reviewer_status": "verified"})
        tags.append({"question_id": qid, "topic_id": "t-b", "tag_role": "primary", "reviewer_status": "verified"})
        i += 1
    for _ in range(n_untagged):
        qid = f"q{i:06d}"
        questions.append({"id": qid, "pyq_paper_id": "p1", "observed_difficulty": buckets[i % 4], "reviewer_status": "verified"})
        i += 1
    return {
        "pyq_papers": [{"id": "p1", "exam_id": "exam-1", "exam_phase_id": None, "year": 2024, "trust_status": "verified"}],
        "pyq_questions": questions,
        "pyq_question_topic_tags": tags,
        "topics": [
            {"id": "t-a", "subject_id": "s-a", "is_active": True},
            {"id": "t-b", "subject_id": "s-b", "is_active": True},
        ],
        "subjects": [
            {"id": "s-a", "name": "Subject A", "slug": "sa", "is_active": True},
            {"id": "s-b", "name": "Subject B", "slug": "sb", "is_active": True},
        ],
    }


def _seed():
    return {
        "pyq_papers": [
            {"id": "p-2023", "exam_id": "exam-1", "exam_phase_id": "ph-prelims",
             "year": 2023, "paper_date": "2023-05-28", "shift": "I", "paper_code": "GS-1",
             "source_url": "https://upsc.gov.in/p23.pdf", "source_type": "official",
             "trust_status": "verified"},
            {"id": "p-2022", "exam_id": "exam-1", "exam_phase_id": "ph-prelims",
             "year": 2022, "paper_date": "2022-06-05", "shift": "I", "paper_code": "GS-1",
             "source_type": "official", "trust_status": "verified"},
            {"id": "p-2024-pending", "exam_id": "exam-1", "exam_phase_id": "ph-prelims",
             "year": 2024, "trust_status": "pending"},  # must be excluded
        ],
        "exam_phases": [
            {"id": "ph-prelims", "phase_name": "Prelims", "phase_slug": "prelims"},
        ],
        "pyq_questions": [
            # 2023 verified questions
            {"id": "q1", "pyq_paper_id": "p-2023", "observed_difficulty": "easy", "reviewer_status": "verified"},
            {"id": "q2", "pyq_paper_id": "p-2023", "observed_difficulty": "Medium", "reviewer_status": "verified"},
            {"id": "q3", "pyq_paper_id": "p-2023", "observed_difficulty": "hard", "reviewer_status": "verified"},
            {"id": "q4", "pyq_paper_id": "p-2023", "observed_difficulty": None, "reviewer_status": "verified"},
            # 2022 verified
            {"id": "q5", "pyq_paper_id": "p-2022", "observed_difficulty": "medium", "reviewer_status": "verified"},
            # Unverified — excluded
            {"id": "q6", "pyq_paper_id": "p-2023", "observed_difficulty": "easy", "reviewer_status": "pending"},
        ],
        "pyq_question_topic_tags": [
            {"question_id": "q1", "topic_id": "t-quant", "tag_role": "primary", "reviewer_status": "verified"},
            {"question_id": "q2", "topic_id": "t-quant", "tag_role": "primary", "reviewer_status": "verified"},
            {"question_id": "q3", "topic_id": "t-poli", "tag_role": "primary", "reviewer_status": "verified"},
            {"question_id": "q4", "topic_id": "t-quant", "tag_role": "primary", "reviewer_status": "verified"},
            {"question_id": "q5", "topic_id": "t-poli", "tag_role": "primary", "reviewer_status": "verified"},
            # Secondary tag — must not be counted as the primary subject row
            {"question_id": "q1", "topic_id": "t-poli", "tag_role": "secondary", "reviewer_status": "verified"},
        ],
        "topics": [
            {"id": "t-quant", "subject_id": "s-quant", "is_active": True},
            {"id": "t-poli", "subject_id": "s-poli", "is_active": True},
        ],
        "subjects": [
            {"id": "s-quant", "name": "Quantitative Aptitude", "slug": "quant", "is_active": True},
            {"id": "s-poli", "name": "Polity", "slug": "polity", "is_active": True},
        ],
    }


def test_verified_pyq_papers_sorted_newest_first_and_filters_pending():
    sb = SBStub(_seed())
    papers = verified_pyq_papers(sb, "exam-1")
    assert [p["id"] for p in papers] == ["p-2023", "p-2022"]
    assert papers[0]["phase_name"] == "Prelims"
    assert papers[0]["source_url"].endswith("p23.pdf")


def test_verified_pyq_papers_empty_when_no_exam():
    assert verified_pyq_papers(SBStub({}), "") == []


def test_difficulty_heatmap_groups_by_subject_and_difficulty():
    sb = SBStub(_seed())
    heatmap = difficulty_heatmap(sb, "exam-1")
    assert heatmap["verified_question_count"] == 5
    rows = {r["subject_slug"]: r for r in heatmap["rows"]}
    assert rows["quant"]["counts"] == {"easy": 1, "medium": 1, "hard": 0, "unknown": 1}
    assert rows["quant"]["total"] == 3
    assert rows["poli" if "poli" in rows else "polity"]["counts"]["hard"] == 1
    assert rows["polity"]["counts"]["medium"] == 1


def test_difficulty_heatmap_empty_when_no_verified_questions():
    db = _seed()
    for q in db["pyq_questions"]:
        q["reviewer_status"] = "pending"
    heatmap = difficulty_heatmap(SBStub(db), "exam-1")
    assert heatmap == {
        "buckets": ["easy", "medium", "hard", "unknown"],
        "rows": [],
        "verified_question_count": 0,
    }


def test_difficulty_heatmap_paginates_past_server_row_cap():
    """The true verified count exceeds one server page, so a single unordered
    ``.limit()`` read would truncate it (and leave rows sampling a different,
    non-overlapping subset). With deterministic ``.order('id').range()``
    pagination the count is exact and rows agree with it."""
    cap = pyq_papers._PAGE
    n_a, n_b = cap - 200, 500  # (cap - 200) + 500 = cap + 300 → forces a 2nd page
    sb = CappingSB(_heatmap_db(n_a, n_b), server_cap=cap)
    hm = difficulty_heatmap(sb, "exam-1")

    assert hm["verified_question_count"] == n_a + n_b  # not capped at `cap`
    assert n_a + n_b > cap
    rows = {r["subject_slug"]: r for r in hm["rows"]}
    assert rows, "rows must be non-empty whenever verified_question_count > 0"
    assert rows["sa"]["total"] == n_a
    assert rows["sb"]["total"] == n_b
    # rows sum to the count, and each row's buckets sum to its own total.
    assert sum(r["total"] for r in hm["rows"]) == hm["verified_question_count"]
    for r in hm["rows"]:
        assert sum(r["counts"].values()) == r["total"]


def test_difficulty_heatmap_untagged_verified_questions_counted_but_excluded_from_rows():
    """Documented deliberate gap: a verified question with no verified primary
    tag is counted in ``verified_question_count`` but excluded from ``rows``.
    So ``sum(row totals) < verified_question_count`` when untagged rows exist —
    this is a real distinction, not a silent truncation."""
    cap = pyq_papers._PAGE
    n_a, n_untagged = cap - 100, 400  # total = cap + 300 → multi-page
    sb = CappingSB(_heatmap_db(n_a, 0, n_untagged=n_untagged), server_cap=cap)
    hm = difficulty_heatmap(sb, "exam-1")

    assert hm["verified_question_count"] == n_a + n_untagged  # untagged still counted
    assert hm["rows"], "rows non-empty since tagged verified questions exist"
    tagged_total = sum(r["total"] for r in hm["rows"])
    assert tagged_total == n_a  # only the primary-tagged questions break down into rows
    assert tagged_total < hm["verified_question_count"]  # the deliberate, documented gap
