"""PRED-01 — predictability as computed and written by the snapshot job.

The measure itself is pinned in `test_predictability.py`. This is about the
wiring: that the year history reaches the measure, that Y is per subject-paper
inside a real compute, that the values land on the row, and that the fingerprint
change forces the recompute this feature depends on.
"""
from __future__ import annotations

from app.exam_intelligence.score_snapshots import (
    MODEL_VERSION,
    _build_fingerprint,
    compute_exam_topic_scores,
)
from tests.persona_questions._stub import SBStub

EXAM = "exam-1"


def _corpus() -> dict:
    """Two subject-papers with DIFFERENT evidence spans, so the per-paper Y is
    actually exercised:

      geog  (subject sg): papers 1986..2025  — topic tg asked 1990/2000/2010
      socio (subject ss): papers 2000..2025  — topic ts asked 2000/2010/2020

    Same three asks each, but geog's span is 40 years and socio's is 26, so the
    same recurrence has to score differently.
    """
    papers, questions, tags = [], [], []

    def add(paper_id: str, year: int, topic: str | None) -> None:
        papers.append(
            {
                "id": paper_id,
                "exam_id": EXAM,
                "exam_phase_id": None,
                "year": year,
                "trust_status": "verified",
            }
        )
        if topic is None:
            return
        qid = f"q-{paper_id}"
        questions.append(
            {"id": qid, "pyq_paper_id": paper_id, "reviewer_status": "verified"}
        )
        tags.append(
            {
                "id": f"tag-{qid}",
                "question_id": qid,
                "topic_id": topic,
                "tag_role": "primary",
                "reviewer_status": "verified",
            }
        )

    # geography: span anchored by two edge papers, topic asked three times
    add("g-edge-lo", 1986, "tg-edge")
    add("g-edge-hi", 2025, "tg-edge2")
    for y in (1990, 2000, 2010):
        add(f"g-{y}", y, "tg")
    # sociology: shorter span
    add("s-edge-lo", 2000, "ts-edge")
    add("s-edge-hi", 2025, "ts-edge2")
    for y in (2000, 2010, 2020):
        add(f"s-{y}", y, "ts")

    return {
        "exams": [{"id": EXAM, "slug": "upsc-cse"}],
        "pyq_papers": papers,
        "pyq_questions": questions,
        "pyq_question_topic_tags": tags,
        "topics": [
            {"id": "tg", "subject_id": "sg"},
            {"id": "tg-edge", "subject_id": "sg"},
            {"id": "tg-edge2", "subject_id": "sg"},
            {"id": "ts", "subject_id": "ss"},
            {"id": "ts-edge", "subject_id": "ss"},
            {"id": "ts-edge2", "subject_id": "ss"},
        ],
        "subjects": [{"id": "sg", "slug": "geog-p1"}, {"id": "ss", "slug": "socio-p1"}],
        "exam_topic_coverage": [],
        "exam_topic_score_snapshots": [],
    }


def _snapshots(sb: SBStub) -> dict[str, dict]:
    return {r["topic_id"]: r for r in sb.db.get("exam_topic_score_snapshots", [])}


def test_compute_writes_predictability_and_a_band():
    sb = SBStub(_corpus())
    result = compute_exam_topic_scores(sb, EXAM)
    assert result["read_error"] is False
    assert result["errors"] == 0

    rows = _snapshots(sb)
    tg = rows["tg"]
    assert tg["predictability"] is not None
    assert tg["predictability_band"] in ("near_certain", "likely", "occasional", "rare")
    # The components a reviewer needs to see why the band was given.
    comp = tg["score_components"]
    assert comp["predictability_years_asked"] == 3
    assert comp["predictability_span_years"] == 40  # 1986..2025, geography's own
    assert comp["predictability_breadth"] == round(3 / 40, 4)


def test_span_is_per_subject_paper_inside_a_real_compute():
    """Same three asks in both papers; sociology's shorter span makes them
    count for more. A global span would give both the same breadth."""
    sb = SBStub(_corpus())
    compute_exam_topic_scores(sb, EXAM)
    rows = _snapshots(sb)

    assert rows["tg"]["score_components"]["predictability_span_years"] == 40
    assert rows["ts"]["score_components"]["predictability_span_years"] == 26
    assert (
        rows["ts"]["score_components"]["predictability_breadth"]
        > rows["tg"]["score_components"]["predictability_breadth"]
    )


def test_exam_priority_score_is_unchanged_by_this_feature():
    """Predictability is a separate axis, not a term in the ranking. The
    published exam_priority_score must be bit-for-bit what it was."""
    sb = SBStub(_corpus())
    compute_exam_topic_scores(sb, EXAM)
    rows = _snapshots(sb)

    # tg and ts have identical evidence (3 primary-tagged questions each) in
    # equally-shaped cohorts, so the v2.0 ranking must treat them identically…
    assert rows["tg"]["exam_priority_score"] == rows["ts"]["exam_priority_score"]
    # …while predictability separates them, because their papers' spans differ.
    assert rows["tg"]["predictability"] != rows["ts"]["predictability"]

    # And the score still reconstructs from the v2.0 terms alone — no
    # predictability term crept into it.
    for r in rows.values():
        c = r["score_components"]
        weight = c["cohort_weight"]
        frequency_term = (
            c["frequency_component"] * 50 * (1 - weight)
            + c["cohort_prominence"] * 50 * weight
        )
        expected = round(
            frequency_term + c["coverage_component"] * 40 + c["evidence_quality"] * 10, 2
        )
        assert abs(r["exam_priority_score"] - expected) < 0.02, r["topic_id"]


def test_repeat_compute_is_still_idempotent():
    sb = SBStub(_corpus())
    first = compute_exam_topic_scores(sb, EXAM)
    second = compute_exam_topic_scores(sb, EXAM)
    assert first["written"] > 0
    assert second["written"] == 0
    assert second["skipped"] == first["written"]


def test_paper_years_are_in_the_fingerprint():
    """G4. Without this, the first recompute after this change would match every
    existing draft's fingerprint, skip all of them, and write no predictability
    at all — the failure would look exactly like success."""
    base = dict(
        exam_id=EXAM,
        model_version=MODEL_VERSION,
        exam_phase_id=None,
        paper_ids=["p1"],
        question_ids=["q1"],
        primary_tag_tuples=[("q1", "t1")],
        locked_cov_rows=[],
        q_to_paper={"q1": "p1"},
        topic_subject={"t1": "s1"},
    )
    without = _build_fingerprint(**base)
    with_1990 = _build_fingerprint(**base, paper_year={"p1": 1990})
    with_2020 = _build_fingerprint(**base, paper_year={"p1": 2020})

    assert without != with_1990
    assert with_1990 != with_2020


def test_a_topic_with_no_year_evidence_gets_no_band_rather_than_a_made_up_one():
    """A topic carried by locked coverage alone has no years behind it. NULL is
    the honest answer; a band would be invented."""
    db = _corpus()
    db["exam_topic_coverage"] = [
        {
            "id": "cov-1",
            "topic_id": "t-coverage-only",
            "exam_id": EXAM,
            "exam_phase_id": None,
            "reviewer_status": "locked",
            "source_basis": "manual",
            "exam_priority_score": 80,
            "is_high_yield": True,
        }
    ]
    db["topics"].append({"id": "t-coverage-only", "subject_id": "sg"})
    sb = SBStub(db)
    compute_exam_topic_scores(sb, EXAM)

    row = _snapshots(sb)["t-coverage-only"]
    assert row["predictability"] is None
    assert row["predictability_band"] is None
    assert row["score_components"]["predictability_years_asked"] == 0
