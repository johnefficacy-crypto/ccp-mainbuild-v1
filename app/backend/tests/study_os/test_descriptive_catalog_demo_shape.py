"""The catalogue against the shape the demo database actually holds.

WHY THESE EXIST. The original fixtures gave every paper `trust_status:
"verified"`, so every test agreed with a catalogue that gated on it. On demo
the split script writes 140 optional papers at `pending` — by design, because
`trust_status` describes whether a paper's COMPOSITION is claimed, not whether
its questions are reviewed. The gate hid all 140 and left the 31 thematic rows
(verified, precisely because they claim no composition) as the only thing on
offer: an aspirant picking Political Science saw twelve year-labelled chips
under "Sat papers, in question order" that were not papers and had no order.

So this fixture is the demo's shape, not a convenient one: pending split
papers, verified thematic rows, two optional subjects, and GS/Essay rows of the
shape the GS split will write.
"""
from __future__ import annotations

from typing import Any

from tests.persona_questions._stub import SBStub

from app.study_os import descriptive as d

EXAM = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
USER = "user-demo"

PSIR = "Political Science and International Relations"
ANTHRO = "Anthropology"


def _paper(pid, year, code, meta, trust="pending"):
    return {
        "id": pid,
        "exam_id": EXAM,
        "year": year,
        "paper_code": code,
        "trust_status": trust,
        "metadata": meta,
    }


def _q(qid, paper, number, text, meta, status="verified"):
    return {
        "id": qid,
        "pyq_paper_id": paper,
        "question_number": number,
        "question_text": text,
        "question_type": "descriptive",
        "reviewer_status": status,
        "metadata": meta,
    }


def _split_meta(subject, number, year):
    """Exactly what scripts/split_optional_buckets.py writes."""
    return {
        "paper_kind": "optional",
        "paper_code": f"UPSC-CSE-MAINS-OPT-{year}-X-P{number}",
        "optional_subject": subject,
        "optional_paper_number": number,
        "year": year,
        "split_from_bucket_id": "bucket-2025",
        "question_count": 2,
    }


def _seed() -> dict[str, Any]:
    return {
        "pyq_papers": [
            # ── the 140's shape: pending, split, real papers ───────────────
            _paper("psir-2025-p1", 2025, "UPSC-CSE-MAINS-OPT-2025-PSIR-P1",
                   _split_meta(PSIR, 1, 2025)),
            _paper("psir-2025-p2", 2025, "UPSC-CSE-MAINS-OPT-2025-PSIR-P2",
                   _split_meta(PSIR, 2, 2025)),
            _paper("psir-2024-p1", 2024, "UPSC-CSE-MAINS-OPT-2024-PSIR-P1",
                   _split_meta(PSIR, 1, 2024)),
            _paper("anthro-2025-p1", 2025, "UPSC-CSE-MAINS-OPT-2025-ANTHRO-P1",
                   _split_meta(ANTHRO, 1, 2025)),
            # ── the 31's shape: verified, thematic, year-labelled ──────────
            _paper("thematic-2019", 2019, "UPSC-CSE-MAINS-OPT-THEMATIC-2019",
                   {"paper_kind": "optional", "corpus_half": "thematic",
                    "paper_reconstructed": False},
                   trust="verified"),
            # A thematic row whose PAPER lost the flag but whose questions kept
            # it. One missing key must not promote a compilation to a sitting.
            _paper("thematic-2018", 2018, "UPSC-CSE-MAINS-OPT-THEMATIC-2018",
                   {"paper_kind": "optional", "paper_reconstructed": False},
                   trust="verified"),
            # ── the retired bucket the splits came from ────────────────────
            _paper("bucket-2025", 2025, "UPSC-CSE-MAINS-OPT-2025",
                   {"paper_kind": "optional", "retired": True,
                    "split_into": ["psir-2025-p1", "psir-2025-p2"]},
                   trust="verified"),
            # ── GS Mains, arriving from its own split ──────────────────────
            _paper("gs-2025-1", 2025, "UPSC-CSE-MAINS-GS-2025-GS1",
                   {"paper_kind": "gs", "gs_paper": 1}),
            _paper("gs-2025-2", 2025, "UPSC-CSE-MAINS-GS-2025-GS2",
                   {"paper_kind": "gs", "gs_paper": 2}),
            _paper("gs-2025-3", 2025, "UPSC-CSE-MAINS-GS-2025-GS3",
                   {"paper_kind": "gs", "gs_paper": 3}),
            _paper("gs-2025-4", 2025, "UPSC-CSE-MAINS-GS-2025-GS4",
                   {"paper_kind": "gs", "gs_paper": 4}),
            _paper("essay-2025", 2025, "UPSC-CSE-MAINS-GS-2025-ESSAY",
                   {"paper_kind": "essay", "gs_paper": "ESSAY"}),
        ],
        "pyq_questions": [
            _q("psir-a", "psir-2025-p1", 1, "Examine sovereignty.",
               {"optional_subject": PSIR, "optional_paper_number": 1}),
            _q("psir-b", "psir-2025-p1", 2, "Discuss federalism.",
               {"optional_subject": PSIR, "optional_paper_number": 1, "marks": 15}),
            _q("psir-c", "psir-2025-p2", 1, "Evaluate non-alignment.",
               {"optional_subject": PSIR, "optional_paper_number": 2}),
            _q("psir-d", "psir-2024-p1", 1, "Assess judicial review.",
               {"optional_subject": PSIR, "optional_paper_number": 1}),
            # A map question on a PSIR paper: never listed, never counted.
            _q("psir-map", "psir-2025-p1", 3, "Mark on the outline map.",
               {"optional_subject": PSIR, "requires_map_sheet": "true"}),
            # Pending review: the one gate that does apply.
            _q("psir-pending", "psir-2025-p1", 4, "Not reviewed yet.",
               {"optional_subject": PSIR}, status="pending"),
            _q("anthro-a", "anthro-2025-p1", 1, "Discuss kinship.",
               {"optional_subject": ANTHRO, "optional_paper_number": 1}),
            _q("anthro-b", "anthro-2025-p1", 2, "Explain fieldwork.",
               {"optional_subject": ANTHRO, "optional_paper_number": 1}),
            # thematic half, BOTH subjects — this is bug 2's evidence
            _q("theme-psir", "thematic-2019", None, "Explain the state.",
               {"optional_subject": PSIR, "corpus_half": "thematic"}),
            _q("theme-anthro", "thematic-2019", None, "Explain totemism.",
               {"optional_subject": ANTHRO, "corpus_half": "thematic"}),
            _q("theme-psir-2", "thematic-2018", None, "Explain legitimacy.",
               {"optional_subject": PSIR, "corpus_half": "thematic"}),
            # the retired bucket's copies — never surfaced
            _q("bucket-a", "bucket-2025", 101, "Examine sovereignty.",
               {"optional_subject": PSIR}),
            # GS: no optional_subject anywhere on the question
            _q("gs1-a", "gs-2025-1", 1, "Discuss the Revolt of 1857.", {"marks": 10}),
            _q("gs2-a", "gs-2025-2", 1, "Examine federal transfers.", {"marks": 15}),
            _q("gs3-a", "gs-2025-3", 1, "Discuss inflation targeting.", {}),
            _q("gs4-a", "gs-2025-4", 1, "A case study on integrity.", {}),
            _q("essay-a", "essay-2025", 1, "Write an essay on forgiveness.", {}),
        ],
        "pyq_question_topic_tags": [
            {"question_id": "theme-psir", "topic_id": "t-state",
             "tag_role": "primary", "reviewer_status": "verified"},
            {"question_id": "theme-anthro", "topic_id": "t-totem",
             "tag_role": "primary", "reviewer_status": "verified"},
            {"question_id": "theme-psir-2", "topic_id": "t-legit",
             "tag_role": "primary", "reviewer_status": "verified"},
        ],
        "topics": [
            {"id": "t-state", "name": "The State"},
            {"id": "t-totem", "name": "Totemism"},
            {"id": "t-legit", "name": "Legitimacy"},
        ],
        "descriptive_attempts": [],
    }


def _sb() -> Any:
    return SBStub(_seed())


def _labels(out):
    return [p["label"] for p in out["papers"]]


def _ids(out):
    return [p["id"] for p in out["papers"]]


# ── BUG 1: pending split papers are the papers ───────────────────────────


def test_pending_split_papers_are_listed():
    """The 140. `trust_status='pending'` is the split script's normal output,
    not a defect, and it says nothing about whether a question is reviewed."""
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)

    assert _ids(out) == ["psir-2025-p1", "psir-2025-p2", "psir-2024-p1"]
    assert all(p["question_count"] > 0 for p in out["papers"])


def test_papers_are_labelled_year_then_paper_number():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    assert _labels(out) == ["2025 · P1", "2025 · P2", "2024 · P1"]


def test_papers_order_is_year_descending_then_paper_ascending():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    order = [(p["year"], p["paper_slot"]) for p in out["papers"]]
    assert order == [(2025, "P1"), (2025, "P2"), (2024, "P1")]


def test_thematic_rows_are_never_papers():
    """The regression as seen: twelve year chips under "Sat papers, in question
    order" that were the thematic compilation, which has no order at all."""
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)

    assert "thematic-2019" not in _ids(out)
    assert "thematic-2018" not in _ids(out)
    # And no chip is a bare year, which is what a thematic row renders as.
    assert all(" · " in label for label in _labels(out))


def test_a_thematic_row_flagged_only_on_its_questions_is_still_thematic():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    assert "thematic-2018" not in _ids(out)
    assert {t["theme"] for t in out["themes"]} == {"The State", "Legitimacy"}


def test_retired_bucket_is_never_a_paper():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    assert "bucket-2025" not in _ids(out)


def test_map_questions_are_not_counted_on_a_paper():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    p1 = next(p for p in out["papers"] if p["id"] == "psir-2025-p1")
    # Two verified, non-map questions. The map one and the pending one are out.
    assert p1["question_count"] == 2


def test_questions_list_opens_a_pending_paper():
    out = d.list_questions(_sb(), USER, exam_id=EXAM, paper_id="psir-2025-p1")
    assert {i["id"] for i in out["items"]} == {"psir-a", "psir-b"}
    assert out["excluded_map_questions"] == 1


# ── BUG 2: themes belong to a subject ────────────────────────────────────


def test_themes_are_filtered_by_subject():
    """Political Science showed Anthropology themes. The thematic loader stamps
    `optional_subject` on every thematic QUESTION — that is the link."""
    psir = d.get_catalog(_sb(), EXAM, subject=PSIR)
    anthro = d.get_catalog(_sb(), EXAM, subject=ANTHRO)

    assert {t["theme"] for t in psir["themes"]} == {"The State", "Legitimacy"}
    assert {t["theme"] for t in anthro["themes"]} == {"Totemism"}


def test_unfiltered_catalog_still_shows_every_theme():
    out = d.get_catalog(_sb(), EXAM)
    assert {t["theme"] for t in out["themes"]} == {"The State", "Totemism", "Legitimacy"}


def test_theme_questions_are_filtered_by_subject_too():
    out = d.list_questions(
        _sb(), USER, exam_id=EXAM, subject=PSIR, theme="The State"
    )
    assert {i["id"] for i in out["items"]} == {"theme-psir"}


# ── BUG 3: subject counts are question counts ────────────────────────────


def test_subject_counts_are_verified_descriptive_question_counts():
    """Anthropology 45 / PolSci 1 was counting something else entirely. A
    subject's number is its questions, both halves, map questions excluded."""
    out = d.get_catalog(_sb(), EXAM)
    counts = {s["subject"]: s["question_count"] for s in out["subjects"]}

    # PSIR: 4 paper questions + 2 thematic. Not the map one, not the pending
    # one, not the retired bucket's copy.
    assert counts[PSIR] == 6
    # Anthropology: 2 paper questions + 1 thematic.
    assert counts[ANTHRO] == 3
    assert counts[d.GENERAL_STUDIES] == 5


def test_subject_count_matches_what_the_list_actually_serves():
    """The count is only meaningful if it predicts the list."""
    for subject in (PSIR, ANTHRO, d.GENERAL_STUDIES):
        catalog = d.get_catalog(_sb(), EXAM)
        promised = next(
            s["question_count"] for s in catalog["subjects"] if s["subject"] == subject
        )
        served = d.list_questions(_sb(), USER, exam_id=EXAM, subject=subject, limit=200)
        assert served["total_matching"] == promised, subject


def test_subject_list_is_never_narrowed_by_the_selected_subject():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    assert {s["subject"] for s in out["subjects"]} == {PSIR, ANTHRO, d.GENERAL_STUDIES}
    assert out["subject"] == PSIR


# ── GS Mains ─────────────────────────────────────────────────────────────


def test_gs_papers_appear_under_general_studies():
    """Keyed on paper_kind + metadata.gs_paper. No subject name is hardcoded:
    GS questions carry no `optional_subject` at all."""
    out = d.get_catalog(_sb(), EXAM, subject=d.GENERAL_STUDIES)

    assert _labels(out) == [
        "2025 · GS1", "2025 · GS2", "2025 · GS3", "2025 · GS4", "2025 · Essay",
    ]


def test_essay_sorts_last_within_its_year():
    out = d.get_catalog(_sb(), EXAM, subject=d.GENERAL_STUDIES)
    assert _labels(out)[-1] == "2025 · Essay"


def test_gs_papers_do_not_leak_into_an_optional_subject():
    out = d.get_catalog(_sb(), EXAM, subject=PSIR)
    assert not any(str(i).startswith(("gs-", "essay-")) for i in _ids(out))


def test_gs_questions_are_listed_under_general_studies():
    out = d.list_questions(
        _sb(), USER, exam_id=EXAM, subject=d.GENERAL_STUDIES, limit=200
    )
    assert {i["id"] for i in out["items"]} == {
        "gs1-a", "gs2-a", "gs3-a", "gs4-a", "essay-a"
    }
    assert all(i["subject"] == d.GENERAL_STUDIES for i in out["items"])


def test_general_studies_is_derived_not_listed():
    """A GS paper with an unfamiliar kind still catalogues correctly as long as
    it carries gs_paper — the catalogue reads shape, not a vocabulary."""
    assert d.is_gs_paper({"metadata": {"paper_kind": "mains", "gs_paper": 2}})
    assert d.paper_slot({"metadata": {"gs_paper": 2}}) == (2, "GS2")
    assert d.subject_of({"metadata": {}}, {"metadata": {"gs_paper": 2}}) == d.GENERAL_STUDIES
    assert d.subject_of({"metadata": {"optional_subject": PSIR}}, {"metadata": {}}) == PSIR
