"""CSAT composition — what each paper was made of, by topic.

A different read from reachability, and the tests exist to keep it that way.
The reachability rubric measures how reachable a question was from standard
preparation; it was written for UPSC GS-I and does not transfer to a
percentages question, and CSAT's stored ``observed_difficulty`` was assigned by
keyword rule rather than judged against any rubric. So nothing this module
returns mentions difficulty, and every fixture below leaves
``observed_difficulty`` NULL to prove the read never touches it.

The fixture is the live corpus's shape as of 2026-09-04: 315 questions across
four verified CSAT papers, every one carrying a primary microtopic tag under one
of three shared subjects, plus the SECONDARY tag to the coarse upsc-csat topic
that every CSAT question also carries — the one that doubles every figure here
if it is ever counted.
"""
from __future__ import annotations

from app.exam_intelligence.subject_composition import (
    CSAT_SUBJECT_IDS,
    subject_composition_series,
)
from tests.exam_intelligence.test_reachability import PagedSB, _client

QUANT, REASONING, ENGLISH = CSAT_SUBJECT_IDS
GS1_SUBJECT = "09db7afb-0864-46c9-b900-1510b60c0011"

YEARS = (2023, 2024, 2025, 2026)

#: The four verified CSAT papers, live ids.
PAPERS = {
    2023: "586d515e-2d3d-485d-a944-3983e4569e53",
    2024: "9e191ae4-68b9-47bf-9121-6d9d468a7bc5",
    2025: "505b29a0-0d4d-5230-88aa-3bbc525a6db5",
    2026: "b06305ad-cc93-4c27-b309-1b590f0a3247",
}

#: The 2026 paper that was REJECTED and superseded by b06305ad…. It is not
#: verified, so nothing here should ever see it.
REJECTED_2026 = "7b18bf8d-2919-4328-9779-8b0fe9a8b22a"

PAPER_SIZE = {2023: 80, 2024: 75, 2025: 80, 2026: 80}

#: Subject split per paper, the finding view 1 draws.
SUBJECT_SPLIT = {
    2023: {QUANT: 46, REASONING: 14, ENGLISH: 20},
    2024: {QUANT: 42, REASONING: 17, ENGLISH: 16},
    2025: {QUANT: 42, REASONING: 22, ENGLISH: 16},
    2026: {QUANT: 40, REASONING: 14, ENGLISH: 26},
}

# ── Microtopics, per subject, with their per-paper counts ────────────────────
# Written as per-year vectors rather than totals because the per-year movement
# is the finding: LCM/HCF runs 16, 8, 16, 8, an alternation the total 48 hides.

QUANT_TOPICS = [
    ("LCM/HCF and divisibility", (16, 8, 16, 8)),
    ("Data sufficiency", (7, 6, 6, 6)),
    ("Percentage increase and decrease", (4, 4, 4, 3)),
    ("Permutations and counting", (3, 3, 3, 3)),
    ("Linear equations", (3, 3, 2, 3)),
    ("Number series", (3, 3, 2, 3)),
    ("Area and perimeter", (2, 3, 2, 3)),
    ("Consecutive and patterned numbers", (2, 2, 2, 2)),
    ("Averages", (1, 1, 0, 0)),
    ("Boats and streams", (0, 0, 1, 1)),
    ("Calendars", (1, 0, 1, 0)),
    ("Clocks", (0, 1, 0, 1)),
    ("Profit and loss", (1, 1, 1, 1)),
    ("Ratio and proportion", (1, 1, 1, 1)),
    ("Simple and compound interest", (1, 1, 0, 1)),
    ("Speed, time and distance", (1, 1, 0, 1)),
    ("Probability", (0, 1, 1, 1)),
    ("Mixtures and alligation", (0, 1, 0, 1)),
    ("Pipes and cisterns", (0, 1, 0, 1)),
    ("Surds and indices", (0, 1, 0, 0)),
]

REASONING_TOPICS = [
    ("Statement and assumption", (8, 8, 9, 8)),
    ("Blood relations", (0, 1, 1, 0)),
    ("Coding and decoding", (0, 1, 1, 0)),
    ("Direction sense", (0, 1, 1, 0)),
    ("Seating arrangement", (0, 1, 1, 0)),
    ("Syllogism", (0, 1, 1, 0)),
    ("Venn diagrams", (0, 1, 1, 0)),
    ("Cubes and dice", (0, 1, 1, 0)),
    ("Analogy", (0, 1, 1, 0)),
    ("Statement and conclusion", (0, 1, 1, 1)),
    ("Course of action", (1, 0, 1, 1)),
    ("Cause and effect", (1, 0, 1, 1)),
    ("Ordering and ranking", (1, 0, 1, 1)),
    ("Series completion", (1, 0, 1, 1)),
    ("Odd one out", (1, 0, 0, 1)),
    ("Input and output", (1, 0, 0, 0)),
]

ENGLISH_TOPICS = [
    ("Inference and implied meaning", (6, 4, 4, 7)),
    ("Explicit detail retrieval", (5, 4, 4, 7)),
    ("Main idea and central point", (5, 4, 4, 7)),
    ("Tone and attitude", (3, 3, 3, 3)),
    ("Vocabulary in context", (1, 0, 0, 0)),
    ("Sentence rearrangement", (0, 1, 0, 0)),
    ("Author's purpose", (0, 0, 1, 0)),
    ("Summary selection", (0, 0, 0, 2)),
]

BY_SUBJECT = {
    QUANT: QUANT_TOPICS,
    REASONING: REASONING_TOPICS,
    ENGLISH: ENGLISH_TOPICS,
}

#: The coarse topic every CSAT question ALSO carries, as a secondary tag.
COARSE_TOPIC = "t-upsc-csat"


def _slug(name):
    return name.lower().replace(" ", "-").replace("/", "-").replace(",", "")


def _csat_db(*, tag_rejected=True):
    questions, tags, topics = [], [], []
    papers = [
        {
            "id": PAPERS[y],
            "exam_id": "e1",
            "year": y,
            # Three different phases across four papers — which is exactly why
            # nothing here scopes by exam_phase_id.
            "exam_phase_id": f"phase-{'a' if y < 2025 else ('b' if y == 2025 else 'c')}",
            "paper_code": "CSAT",
            "trust_status": "verified",
            "metadata": {},
        }
        for y in YEARS
    ]
    # The rejected, superseded 2026 paper. Fully tagged, so only trust_status
    # keeps it out — which is the point.
    papers.append(
        {
            "id": REJECTED_2026,
            "exam_id": "e1",
            "year": 2026,
            "exam_phase_id": "phase-c",
            "paper_code": "CSAT",
            "trust_status": "rejected",
            "metadata": {},
        }
    )

    for subject_id, rows in BY_SUBJECT.items():
        for name, per_year in rows:
            topics.append(
                {
                    "id": _slug(name),
                    "name": name,
                    "subject_id": subject_id,
                    "parent_topic_id": f"parent-{subject_id[-1]}",
                }
            )

    topics.append(
        {
            "id": COARSE_TOPIC,
            "name": "CSAT",
            "subject_id": QUANT,
            "parent_topic_id": None,
        }
    )

    counter = 0
    for i, year in enumerate(YEARS):
        pid = PAPERS[year]
        for subject_id, rows in BY_SUBJECT.items():
            for name, per_year in rows:
                for _ in range(per_year[i]):
                    counter += 1
                    qid = f"q-{counter:05d}"
                    questions.append(
                        {
                            "id": qid,
                            "pyq_paper_id": pid,
                            "section_id": None,
                            # Never assessed. This read must not depend on it.
                            "observed_difficulty": None,
                            "reviewer_status": "verified",
                        }
                    )
                    tags.append(
                        {
                            "id": f"a-tag-{qid}",
                            "question_id": qid,
                            "topic_id": _slug(name),
                            "tag_role": "primary",
                            "reviewer_status": "verified",
                        }
                    )
                    # The secondary tag every CSAT question carries. Counting
                    # both roles doubles every figure in the payload.
                    tags.append(
                        {
                            "id": f"z-tag-{qid}",
                            "question_id": qid,
                            "topic_id": COARSE_TOPIC,
                            "tag_role": "secondary",
                            "reviewer_status": "verified",
                        }
                    )

    if tag_rejected:
        for j in range(80):
            qid = f"q-rejected-{j:03d}"
            questions.append(
                {
                    "id": qid,
                    "pyq_paper_id": REJECTED_2026,
                    "section_id": None,
                    "observed_difficulty": None,
                    "reviewer_status": "verified",
                }
            )
            tags.append(
                {
                    "id": f"a-tag-{qid}",
                    "question_id": qid,
                    "topic_id": _slug("LCM/HCF and divisibility"),
                    "tag_role": "primary",
                    "reviewer_status": "verified",
                }
            )

    return {
        "exams": [{"id": "e1", "slug": "upsc-cse"}],
        "exam_phases": [
            {"id": "phase-a", "phase_name": "Prelims", "phase_slug": "prelims-a"},
            {"id": "phase-b", "phase_name": "Prelims", "phase_slug": "prelims-b"},
            {"id": "phase-c", "phase_name": "Prelims", "phase_slug": "prelims-c"},
        ],
        "exam_phase_sections": [],
        "subjects": [
            {"id": QUANT, "name": "Quantitative Aptitude", "slug": "quantitative-aptitude"},
            {"id": REASONING, "name": "General Intelligence & Reasoning", "slug": "reasoning"},
            {"id": ENGLISH, "name": "English Language", "slug": "english-language"},
        ],
        "pyq_papers": papers,
        "pyq_questions": questions,
        "pyq_question_topic_tags": tags,
        "topics": topics,
    }


def _series(db=None):
    return subject_composition_series(PagedSB(db or _csat_db()), "e1", CSAT_SUBJECT_IDS)


def _paper(out, year):
    return next(p for p in out["papers"] if p["year"] == year)


def _topic(out, name):
    return next(t for t in out["topics"] if t["topic_name"] == name)


# ── The four papers and their subject split ──────────────────────────────────


def test_the_four_verified_csat_papers_render():
    out = _series()
    assert [p["year"] for p in out["papers"]] == list(YEARS)
    assert sum(p["tagged_questions"] for p in out["papers"]) == 315


def test_the_subject_split_per_paper():
    out = _series()
    for year, split in SUBJECT_SPLIT.items():
        assert _paper(out, year)["by_subject"] == split
        assert _paper(out, year)["tagged_questions"] == PAPER_SIZE[year]


def test_the_papers_span_three_phases():
    """Which is why the series is scoped by the primary tag's subject and never
    by exam_phase_id: any single phase returns two papers or one, never four."""
    out = _series()
    assert len({p["phase_id"] for p in out["papers"]}) == 3


def test_the_rejected_2026_paper_is_excluded():
    """7b18bf8d… was superseded by b06305ad…. It is fully tagged here, so only
    its trust_status keeps it out."""
    out = _series()
    assert REJECTED_2026 not in {p["paper_id"] for p in out["papers"]}
    assert PAPERS[2026] in {p["paper_id"] for p in out["papers"]}
    # And its 80 questions never reach any count.
    assert _topic(out, "LCM/HCF and divisibility")["total"] == 48


# ── Topics within a subject ──────────────────────────────────────────────────


def test_quant_topic_totals_and_the_per_year_alternation():
    out = _series()
    lcm = _topic(out, "LCM/HCF and divisibility")
    assert lcm["subject_id"] == QUANT
    assert lcm["total"] == 48
    assert [lcm["by_paper"][PAPERS[y]] for y in YEARS] == [16, 8, 16, 8]


def test_quant_head_of_the_ranking():
    out = _series()
    quant = [t for t in out["topics"] if t["subject_id"] == QUANT]
    assert [(t["topic_name"], t["total"]) for t in quant[:8]] == [
        ("LCM/HCF and divisibility", 48),
        ("Data sufficiency", 25),
        ("Percentage increase and decrease", 15),
        ("Permutations and counting", 12),
        ("Linear equations", 11),
        ("Number series", 11),
        ("Area and perimeter", 10),
        ("Consecutive and patterned numbers", 8),
    ]


def test_distinct_microtopics_per_subject():
    out = _series()
    counts = {
        sid: len([t for t in out["topics"] if t["subject_id"] == sid])
        for sid in CSAT_SUBJECT_IDS
    }
    assert counts == {QUANT: 20, REASONING: 16, ENGLISH: 8}


def test_reasoning_is_one_topic_and_a_tail():
    out = _series()
    reasoning = [t for t in out["topics"] if t["subject_id"] == REASONING]
    assert reasoning[0]["topic_name"] == "Statement and assumption"
    assert reasoning[0]["total"] == 33
    assert sum(t["total"] for t in reasoning) == 67
    assert all(1 <= t["total"] <= 3 for t in reasoning[1:])


def test_english_is_four_topics_and_a_remainder():
    out = _series()
    english = [t for t in out["topics"] if t["subject_id"] == ENGLISH]
    assert [(t["topic_name"], t["total"]) for t in english[:4]] == [
        ("Inference and implied meaning", 21),
        ("Explicit detail retrieval", 20),
        ("Main idea and central point", 20),
        ("Tone and attitude", 12),
    ]
    assert sum(t["total"] for t in english) == 78


# ── The overall ranking ──────────────────────────────────────────────────────


def test_most_tested_topics_overall():
    out = _series()
    assert [(t["topic_name"], t["total"]) for t in out["topics"][:5]] == [
        ("LCM/HCF and divisibility", 48),
        ("Statement and assumption", 33),
        ("Data sufficiency", 25),
        ("Inference and implied meaning", 21),
        ("Explicit detail retrieval", 20),
    ]


# ── Primary tags only ────────────────────────────────────────────────────────


def test_only_primary_tags_are_counted():
    """Every CSAT question also carries a secondary tag to the coarse
    upsc-csat topic. If secondary tags counted, every figure here doubles and
    that one topic appears at 315."""
    out = _series()
    assert COARSE_TOPIC not in {t["topic_id"] for t in out["topics"]}
    assert sum(t["total"] for t in out["topics"]) == 315


def test_a_question_with_a_primary_and_a_secondary_tag_counts_once():
    db = _csat_db()
    qid = db["pyq_questions"][0]["id"]
    assert (
        len([t for t in db["pyq_question_topic_tags"] if t["question_id"] == qid]) == 2
    )
    out = _series(db)
    assert sum(p["tagged_questions"] for p in out["papers"]) == 315
    assert sum(t["total"] for t in out["topics"]) == 315


def test_a_second_primary_tag_is_attributed_once_and_reported():
    db = _csat_db()
    qid = db["pyq_questions"][0]["id"]
    db["pyq_question_topic_tags"].append(
        {
            "id": f"b-tag-{qid}",
            "question_id": qid,
            "topic_id": _slug("Clocks"),
            "tag_role": "primary",
            "reviewer_status": "verified",
        }
    )
    out = _series(db)
    assert sum(t["total"] for t in out["topics"]) == 315
    assert sum(p["multi_tagged_questions"] for p in out["papers"]) == 1


def test_unverified_tags_never_reach_the_count():
    db = _csat_db()
    changed = 0
    for t in db["pyq_question_topic_tags"]:
        if t["tag_role"] == "primary" and t["topic_id"] == _slug("Data sufficiency"):
            t["reviewer_status"] = "pending"
            changed += 1
    assert changed == 25
    out = _series(db)
    assert not [t for t in out["topics"] if t["topic_name"] == "Data sufficiency"]
    assert sum(p["untagged_questions"] for p in out["papers"]) == 25


# ── Eligibility ──────────────────────────────────────────────────────────────


def test_an_untagged_csat_paper_is_returned_for_an_empty_state():
    """It is in the series by its section, but has nothing to break down. The
    caller renders an empty state for it rather than a chart with no bars, or a
    silently missing year."""
    db = _csat_db()
    db["pyq_papers"].append(
        {
            "id": "p-csat-2022",
            "exam_id": "e1",
            "year": 2022,
            "exam_phase_id": "phase-a",
            "paper_code": "CSAT",
            "trust_status": "verified",
            "metadata": {},
        }
    )
    db["exam_phase_sections"].append({"id": "sec-csat", "subject_id": QUANT})
    db["pyq_questions"].extend(
        {
            "id": f"q-2022-{i:03d}",
            "pyq_paper_id": "p-csat-2022",
            "section_id": "sec-csat",
            "observed_difficulty": None,
            "reviewer_status": "verified",
        }
        for i in range(80)
    )
    out = _series(db)
    row = _paper(out, 2022)
    assert row["tagged_questions"] == 0
    assert row["untagged_questions"] == 80
    assert row["by_subject"] == {QUANT: 0, REASONING: 0, ENGLISH: 0}


def test_a_gs1_paper_never_joins_the_csat_series():
    db = _csat_db()
    db["pyq_papers"].append(
        {
            "id": "p-gs1-2026",
            "exam_id": "e1",
            "year": 2026,
            "exam_phase_id": "phase-c",
            "paper_code": "GS-1",
            "trust_status": "verified",
            "metadata": {},
        }
    )
    db["topics"].append(
        {
            "id": "m-gs1",
            "name": "Fundamental Rights",
            "subject_id": GS1_SUBJECT,
            "parent_topic_id": None,
        }
    )
    for i in range(100):
        qid = f"q-gs1-{i:03d}"
        db["pyq_questions"].append(
            {
                "id": qid,
                "pyq_paper_id": "p-gs1-2026",
                "section_id": None,
                "observed_difficulty": "easy",
                "reviewer_status": "verified",
            }
        )
        db["pyq_question_topic_tags"].append(
            {
                "id": f"a-tag-{qid}",
                "question_id": qid,
                "topic_id": "m-gs1",
                "tag_role": "primary",
                "reviewer_status": "verified",
            }
        )
    out = _series(db)
    assert "p-gs1-2026" not in {p["paper_id"] for p in out["papers"]}
    assert "Fundamental Rights" not in {t["topic_name"] for t in out["topics"]}


def test_an_exam_with_no_csat_paper_returns_no_series():
    db = _csat_db()
    for p in db["pyq_papers"]:
        p["trust_status"] = "rejected"
    out = _series(db)
    assert out["papers"] == []
    assert out["topics"] == []


def test_nothing_in_the_payload_reports_difficulty():
    """The reachability rubric does not transfer to CSAT and this corpus was
    never read against it. No band, no column, no derived label."""
    out = _series()
    blob = str(out).lower()
    for word in ("difficulty", "easy", "medium", "hard", "band"):
        assert word not in blob


# ── Endpoint ─────────────────────────────────────────────────────────────────


def test_endpoint_returns_the_four_papers_with_their_subjects():
    client, _ = _client(_csat_db())
    r = client.get("/api/exam-intelligence/exams/upsc-cse/csat-composition")
    assert r.status_code == 200
    body = r.json()
    assert body["verified_only"] is True
    assert [p["year"] for p in body["papers"]] == list(YEARS)
    assert [s["subject_id"] for s in body["subjects"]] == list(CSAT_SUBJECT_IDS)
    assert body["subjects"][0]["name"] == "Quantitative Aptitude"
    # The metadata blob never ships; only the reviewed display label does.
    assert "metadata" not in body["papers"][0]
    assert "set_label" in body["papers"][0]


def test_endpoint_returns_no_series_for_an_exam_without_csat():
    client, _ = _client(_csat_db())
    body = client.get("/api/exam-intelligence/exams/ssc-cgl/csat-composition").json()
    assert body["papers"] == []
    assert body["subject_ids"] == []
