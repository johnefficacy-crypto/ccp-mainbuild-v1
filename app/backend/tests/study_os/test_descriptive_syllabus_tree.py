"""Themes arranged the way the syllabus is arranged.

A flat chip list of 1,493 themes is not a syllabus. The official document is
Subject → Paper → numbered unit → themes, and `scripts/ingest_upsc_gs_syllabus.py`
already writes that shape: the subject row IS the paper, a `level='topic'` row
is a numbered unit, and every microtopic carries `metadata.paper_id` and
`metadata.macro_topic`. Placement therefore reads stamped metadata — no
inference, no fuzzy matching — and anything it cannot place is shown in an
explicit "Other" group rather than guessed into a section.
"""
from __future__ import annotations

from typing import Any

import pytest

from tests.persona_questions._stub import SBStub

from app.study_os import descriptive as d
from app.study_os import syllabus as syl

EXAM = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
USER = "user-syl"
PSIR = "Political Science and International Relations"


def _paper(pid, year, meta, trust="pending"):
    return {"id": pid, "exam_id": EXAM, "year": year, "paper_code": pid,
            "trust_status": trust, "metadata": meta}


def _q(qid, paper, meta, number=None):
    return {"id": qid, "pyq_paper_id": paper, "question_number": number,
            "question_text": f"Question {qid}.", "question_type": "descriptive",
            "reviewer_status": "verified", "metadata": meta}


def _theme_q(qid, subject):
    return _q(qid, "thematic", {"optional_subject": subject, "corpus_half": "thematic"})


def _topic(tid, name, paper_id, macro):
    """A microtopic exactly as the ingest writes one."""
    return {"id": tid, "name": name, "level": "microtopic",
            "parent_topic_id": f"macro-{macro}", "subject_id": f"subj-{paper_id}",
            "metadata": {"paper_id": paper_id, "macro_topic": macro,
                         "source": "upsc_gs_micro_theme_map"}}


def _tag(qid, tid):
    return {"question_id": qid, "topic_id": tid,
            "tag_role": "primary", "reviewer_status": "verified"}


def _seed() -> dict[str, Any]:
    return {
        "pyq_papers": [
            _paper("psir-2025-p1", 2025, {"paper_kind": "optional",
                                          "optional_subject": PSIR,
                                          "optional_paper_number": 1,
                                          "split_from_bucket_id": "b1"}),
            _paper("psir-2025-p2", 2025, {"paper_kind": "optional",
                                          "optional_subject": PSIR,
                                          "optional_paper_number": 2,
                                          "split_from_bucket_id": "b1"}),
            _paper("thematic", 2019, {"paper_kind": "optional",
                                      "corpus_half": "thematic"}, trust="verified"),
            # THE DEMO BUG: an unsplit GS bucket. paper_code and paper_kind
            # NULL, not thematic, questions with no subject of any kind.
            _paper("gs-bucket", 2023, {}, trust="verified"),
        ],
        "pyq_questions": [
            _q("p1-a", "psir-2025-p1", {"optional_subject": PSIR, "optional_paper_number": 1}, 1),
            _q("p1-b", "psir-2025-p1", {"optional_subject": PSIR, "optional_paper_number": 1}, 2),
            _q("p2-a", "psir-2025-p2", {"optional_subject": PSIR, "optional_paper_number": 2}, 1),
            # thematic, one per paper and one unplaceable
            _theme_q("t-p1-late", PSIR),
            _theme_q("t-p1-early", PSIR),
            _theme_q("t-p2", PSIR),
            _theme_q("t-stray", PSIR),
            _theme_q("t-untagged", PSIR),
            # the GS bucket's questions: no optional_subject, no gs paper kind
            _q("gs-1", "gs-bucket", {}, 1),
            _q("gs-2", "gs-bucket", {}, 2),
        ],
        "pyq_question_topic_tags": [
            _tag("t-p1-late", "topic-late"),
            _tag("t-p1-early", "topic-early"),
            _tag("t-p2", "topic-p2"),
            _tag("t-stray", "topic-stray"),
        ],
        "topics": [
            # Paper I, section index 1, theme index 3 in the real syllabus file.
            _topic("topic-late", "Theories of the state: Liberal", "opt-psir-p1",
                   "2. Theories of the state"),
            # Paper I, section index 0 — must sort ABOVE the one above.
            _topic("topic-early", "Meaning and approaches",
                   "opt-psir-p1", "1. Political Theory: meaning and approaches"),
            _topic("topic-p2", "Comparative Politics: nature and major approaches",
                   "opt-psir-p2", "1. Comparative Politics"),
            # No syllabus metadata at all, and a name the index does not know.
            {"id": "topic-stray", "name": "A theme from nowhere",
             "level": "microtopic", "parent_topic_id": None,
             "subject_id": "subj-x", "metadata": {}},
        ],
        "descriptive_attempts": [],
    }


def _sb() -> Any:
    return SBStub(_seed())


def _tree(out):
    return {p["paper_label"]: p for p in out["themes"]}


# ── nesting and order ────────────────────────────────────────────────────


def test_themes_are_nested_paper_then_section_then_theme():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    tree = _tree(out)

    assert set(tree) == {"P1", "P2", syl.UNPLACED_PAPER_LABEL}
    p1_sections = [s["section"] for s in tree["P1"]["sections"]]
    assert p1_sections == [
        "1. Political Theory: meaning and approaches",
        "2. Theories of the state",
    ]
    assert [t["theme"] for t in tree["P1"]["sections"][0]["themes"]] == [
        "Meaning and approaches"
    ]


def test_sections_are_in_syllabus_order_not_alphabetical_or_by_count():
    """Section 1 before section 2, whichever has more questions. The order is
    the official document's, and nothing about counts may disturb it."""
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    p1 = _tree(out)["P1"]
    assert [s["section"][0] for s in p1["sections"]] == ["1", "2"]


def test_counts_roll_up_from_themes_to_sections_to_paper():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    for paper in out["themes"]:
        for section in paper["sections"]:
            assert section["question_count"] == sum(
                t["question_count"] for t in section["themes"]
            )
        assert paper["question_count"] == sum(
            s["question_count"] for s in paper["sections"]
        )


def test_papers_are_in_paper_order_with_other_last():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    assert [p["paper_label"] for p in out["themes"]][-1] == syl.UNPLACED_PAPER_LABEL
    assert [p["paper_label"] for p in out["themes"]][:2] == ["P1", "P2"]


# ── the unmapped group ───────────────────────────────────────────────────


def test_an_unplaceable_theme_is_visible_in_an_other_group_not_hidden():
    """Determinism over heuristics: a theme with no syllabus metadata and no
    exact index match is NOT guessed into a section."""
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    other = _tree(out)[syl.UNPLACED_PAPER_LABEL]

    names = {t["theme"] for s in other["sections"] for t in s["themes"]}
    assert "A theme from nowhere" in names
    assert d.UNTAGGED_THEME in names
    assert all(s["section"] == syl.UNPLACED_SECTION for s in other["sections"])


def test_every_thematic_question_is_somewhere_in_the_tree():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    total = sum(p["question_count"] for p in out["themes"])
    assert total == 5  # four tagged + one untagged


# ── the paper tabs ───────────────────────────────────────────────────────


def test_tabs_are_derived_from_the_themes_present():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    tabs = {t["paper_label"]: t for t in out["theme_papers"]}
    assert set(tabs) == {"P1", "P2", syl.UNPLACED_PAPER_LABEL}
    assert tabs["P1"]["paper_number"] == 1
    assert tabs["P2"]["paper_number"] == 2
    assert tabs[syl.UNPLACED_PAPER_LABEL]["paper_number"] is None


def test_a_paper_tab_filters_the_themes():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR, paper_number=1)
    assert [p["paper_label"] for p in out["themes"]] == ["P1"]
    # The tabs themselves are never filtered — they are how you switch.
    assert {t["paper_label"] for t in out["theme_papers"]} == {
        "P1", "P2", syl.UNPLACED_PAPER_LABEL
    }
    assert out["paper_number"] == 1


def test_a_paper_tab_filters_the_sittings_too():
    """A Paper I tab that left Paper II sittings on screen is a filter that
    only half applies."""
    out = d.get_catalog(_sb(), EXAM, subject=PSIR, paper_number=1)
    assert [p["id"] for p in out["papers"]] == ["psir-2025-p1"]

    out2 = d.get_catalog(_sb(), EXAM, subject=PSIR, paper_number=2)
    assert [p["id"] for p in out2["papers"]] == ["psir-2025-p2"]


def test_the_question_list_honours_the_paper_number():
    out = d.list_questions(_sb(), USER, exam_id=EXAM, subject=PSIR, paper_number=1)
    assert {i["id"] for i in out["items"]} == {"p1-a", "p1-b"}


def test_no_paper_number_means_every_paper():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    assert [p["id"] for p in out["papers"]] == ["psir-2025-p1", "psir-2025-p2"]
    assert out["paper_number"] is None


# ── the GS-bucket leak ───────────────────────────────────────────────────


def test_an_unsplit_gs_bucket_is_not_a_paper_under_an_optional_subject():
    """Seen on demo: paper_id 9b2371d8…, 2023, 80 questions, listed under
    Political Science. paper_code NULL, paper_kind NULL, not thematic — its
    questions claim no subject at all, so it belongs under none."""
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    assert "gs-bucket" not in [p["id"] for p in out["papers"]]
    assert 2023 not in [y["year"] for y in out["years"]]


def test_an_unsplit_gs_bucket_is_not_listed_with_no_subject_selected_either():
    """The leak was here: with no subject chosen the scope was every question,
    so a paper nothing could place was counted anyway."""
    out = d.get_catalog(_sb(), EXAM)
    assert "gs-bucket" not in [p["id"] for p in out["papers"]]
    assert 2023 not in [y["year"] for y in out["years"]]


def test_an_unsplit_gs_bucket_contributes_to_no_subject_count():
    out = d.get_catalog(_sb(), EXAM)
    counts = {s["subject"]: s["question_count"] for s in out["subjects"]}
    assert counts == {PSIR: 8}  # 3 sittings + 5 thematic; the 2 GS-bucket rows are nowhere


def test_a_real_gs_paper_is_still_listed_under_general_studies():
    """The exclusion is about questions that claim no subject, not about GS."""
    seed = _seed()
    seed["pyq_papers"].append(
        _paper("gs-2025-1", 2025, {"paper_kind": "gs", "gs_paper": 1})
    )
    seed["pyq_questions"].append(_q("real-gs", "gs-2025-1", {}, 1))
    out = d.get_catalog(SBStub(seed), EXAM, subject=d.GENERAL_STUDIES)
    assert [p["id"] for p in out["papers"]] == ["gs-2025-1"]
