"""Extraction + routing contract for ``scripts/extract_gs_missing.py``.

Fixtures are small hand-built OCR pages shaped like the real UPSC scans in
``workbench/audit/ocr_cache/``: a Hindi half that OCRs to Latin garble, the
English question below it, a word-limit anchor, and a marks column read after
the page footer. Everything here is pure - no database, no OCR cache.
"""
from __future__ import annotations

import csv
import importlib.util
import pathlib
import sys

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location("extract_gs_missing", _ROOT / "scripts" / "extract_gs_missing.py")
egm = importlib.util.module_from_spec(_spec)
sys.modules["extract_gs_missing"] = egm
_spec.loader.exec_module(egm)

Q = {
    1: "Analyze the importance of Ashokan inscriptions for reconstructing Mauryan history.",
    2: "Discuss the role of aeolian processes in desertification and land degradation.",
    3: "Is caste disappearing in urban India? Illustrate your answer with examples.",
    4: "Critically examine the challenges of demographic transition in contemporary India.",
}


def vocab_for(*texts: str) -> frozenset[str]:
    """What the snapshot would contribute: the English words of real DB rows."""
    words: set[str] = set(egm.BASE_VOCAB)
    for t in texts:
        words.update(egm.words(t))
    return frozenset(words)


VOCAB = vocab_for(*Q.values(), "the importance of history processes land degradation "
                  "urban answer challenges transition contemporary")

HEADER = """Civil Services (Main)
Examination, 2026 KVMS-G-GSA

GENERAL STUDIES (PAPER-I)
QUESTION PAPER SPECIFIC INSTRUCTIONS
There are FOUR questions printed both in HINDI and in ENGLISH.
All questions are compulsory.
Any page or portion of the page left blank in the Question-cum-Answer Booklet must be
clearly struck off.

KVMS-G-GSA/35 1 [ P.T.O.
"""

CLEAN = HEADER + """
df sftera & yaftaia & fee aie & afreral & aera ar fagctarr ifsc)
(Sat 150 Beat F hse)

Analyze the importance of Ashokan inscriptions for reconstructing Mauryan history.
(Answer in 150 words)

meet ait afi srr A arguita wie ft after ht fees if
(Sa 150 Wet 4H <ifste)

Discuss the role of aeolian processes in desertification and land degradation.
(Answer in 150 words)

KVMS-G-GSA/35 2

10

10

ar wet and A sift qa a wa 8? aA SR A serail & ay wae A)
(SRK 250 seat F Af)

Is caste disappearing in urban India? Illustrate your answer with examples.
(Answer in 250 words) 15

waar ad 4 saaiferhta dam A sited ar sneer wha Aire
(SR 250 eat 4 Aifsrz)

Critically examine the challenges of demographic transition in contemporary India.
(Answer in 250 words) 15

KVMS-G-GSA/35 3
"""


def extract(text: str, paper: str = "GS1", vocab: frozenset[str] = VOCAB) -> dict:
    return egm.extract_paper(text, year=2026, paper=paper, source_file="fixture.txt", vocab=vocab)


# ── clean ────────────────────────────────────────────────────────────────


def test_clean_paper_extracts_every_question_in_order():
    staged = extract(CLEAN)
    assert staged["mode"] == "anchored"
    assert staged["printed_question_count"] == 4
    assert staged["paper_flags"] == []
    assert [q["text"] for q in staged["questions"]] == [Q[1], Q[2], Q[3], Q[4]]
    assert [q["official_number"] for q in staged["questions"]] == [1, 2, 3, 4]


def test_word_limit_and_marks_are_read_only_where_printed():
    qs = extract(CLEAN)["questions"]
    assert [q["word_limit"] for q in qs] == [150, 150, 250, 250]
    # Page 1's marks column is OCR'd after its footer; page 2's marks are inline.
    assert [(q["marks"], q["marks_source"]) for q in qs] == [
        ("10", "printed_column"), ("10", "printed_column"),
        ("15", "printed_inline"), ("15", "printed_inline"),
    ]


def test_marks_column_with_the_wrong_count_is_left_unread_not_guessed():
    text = CLEAN.replace("KVMS-G-GSA/35 2\n\n10\n\n10\n", "KVMS-G-GSA/35 2\n\n10\n")
    qs = extract(text)["questions"]
    assert qs[0]["marks"] is None and "marks_unread" in qs[0]["flags"]
    assert qs[1]["marks"] is None and "marks_unread" in qs[1]["flags"]


def test_source_file_and_line_span_point_at_the_ocr():
    q = extract(CLEAN)["questions"][0]
    lines = CLEAN.splitlines()
    first, last = q["line_span"]
    assert q["source_file"] == "fixture.txt"
    assert lines[first - 1] == Q[1]
    assert lines[last - 1] == "(Answer in 150 words)"


def test_content_hash_matches_the_importers_question_hash():
    # Loaded by path: the module is stdlib-only, and the package import would
    # pull in the whole backend.
    spec = importlib.util.spec_from_file_location(
        "option_normalize", _ROOT / "app" / "backend" / "app" / "exam_intelligence" / "option_normalize.py")
    on = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(on)
    text = "Discuss the “Gandhian” movement — its mass base."
    assert egm.content_hash(text) == on.question_hash(text)


# ── bilingual ────────────────────────────────────────────────────────────


def test_bilingual_paper_keeps_english_only():
    qs = extract(CLEAN)["questions"]
    garble = ("sftera", "fagctarr", "Beat", "arguita", "serail", "Aifsrz")
    for q in qs:
        assert not any(tok in q["text"] for tok in garble), q["text"]


def test_hindi_garble_is_never_classified_english():
    lines = egm.classify([
        "df sftera & yaftaia & fee aie & afreral & aera ar fagctarr ifsc)",
        "(Sat 150 Beat F hse)",
        "wes w/a & fee faa sis sae ama feu me 3",
    ], VOCAB)
    assert {ln.kind for ln in lines} <= {"other"}


# ── noisy ────────────────────────────────────────────────────────────────


def test_noisy_line_is_flagged_low_confidence_but_kept():
    noisy = CLEAN.replace(Q[2], "Discuss the role of aeolian | processes in ose desertification and land degradation.")
    q = extract(noisy)["questions"][1]
    assert "low_confidence_ocr" in q["flags"]
    flags = q["low_confidence_lines"][0]["flags"]
    assert "garble_chars" in flags and "suspect_token" in flags


def test_word_limit_split_over_two_lines_is_mended():
    split = CLEAN.replace(f"{Q[4]}\n(Answer in 250 words) 15", f"{Q[4]} (Answer in\n250 words) 15")
    qs = extract(split)["questions"]
    assert qs[3]["text"] == Q[4]
    assert qs[3]["word_limit"] == 250 and qs[3]["marks"] == "15"


def test_question_running_over_a_page_break_is_rejoined():
    broken = CLEAN.replace(
        f"{Q[3]}\n(Answer in 250 words) 15",
        "Is caste disappearing in urban India? Illustrate\n\nKVMS-G-GSA/35 3\n\n"
        "your answer with examples.\n(Answer in 250 words) 15",
    )
    q = extract(broken)["questions"][2]
    assert q["text"] == Q[3]
    assert "possible_truncation" not in q["flags"]


def test_count_mismatch_flags_numbering_for_review():
    missing = CLEAN.replace(f"{Q[4]}\n(Answer in 250 words) 15", "")
    staged = extract(missing)
    assert any(f.startswith("count_mismatch") for f in staged["paper_flags"])
    assert all("numbering_unverified" in q["flags"] for q in staged["questions"])


def test_instruction_paragraph_is_never_a_question():
    block = egm.Block(lines=[egm.Line(no=1, page=1, kind="english", text=(
        "Answer the questions in NOT MORE THAN 200 words each. Contents of the answer "
        "are more important than its length."))], anchored=False)
    assert egm.drop_reason(block, VOCAB) == "instruction"


# ── sub-parts and case studies ───────────────────────────────────────────

SUBPARTS = """There are TWO questions divided in two Sections and printed both in HINDI and
in ENGLISH. Any page must be clearly struck off.

(a)

(b)

wtqus—A / SECTION—A

way > aa 4 feat a ue sen ais gfere Fl yee YUH
Discuss how national security can be balanced with concerns of human rights.
(Answer in 150 words)

Ub stele eat ws Tel oRatSaT we are ae Tar 8, fares TOT WH
Efficiency is doing things right, while effectiveness is doing the right thing.
(Answer in 150 words)

wais—B / SECTION—B

2. aa, Wal rat A ale, sa sears Ie Ye-ad H oe area A wef seen wea)
(a) yea Fe Afs gel wm fear Ai)
Seema is a senior officer with a reputation of honesty and professional efficiency.
(a) What are the ethical issues involved in this case?
(b) Discuss the options open to Seema. Identify the recommended option.
(Answer in 250 words) 20
"""


def test_subparts_number_from_the_label_column_and_case_study_stays_whole():
    vocab = vocab_for(
        "Discuss how national security can be balanced with concerns of human rights.",
        "Efficiency is doing things right, while effectiveness is doing the right thing.",
        "Seema is a senior officer with a reputation of honesty and professional efficiency.",
        "What are the ethical issues involved in this case? Discuss the options open to Seema. "
        "Identify the recommended option.",
    )
    staged = extract(SUBPARTS, paper="GS4", vocab=vocab)
    got = [(q["official_number"], q["sub_part"], q["section"]) for q in staged["questions"]]
    assert got == [(1, "a", "A"), (1, "b", "A"), (2, None, "B")]
    case = staged["questions"][2]["text"]
    assert case.startswith("Seema is") and "(b) Discuss the options" in case
    assert staged["paper_flags"] == []


# ── essay ────────────────────────────────────────────────────────────────

ESSAY = """Examination, 2026 KVMS-G-ESSY
Question Paper Specific Instructions
Any page or portion of the page left blank must be clearly struck off.

KVMS-G-ESSY i

Write two essays, choosing one topic from each of the following Sections A
and B, in about 1000 -— 1200 words each : 125x2=250

aus A
SECTION A

factarmra sfaa Hi fasaaratt ar aarte & |

A grateful mind is very beautiful.

Riel, Het HT ATA SST BT |

When two elephants fight, it is the grass that gets trampled.

wus B
SECTION B

sepia at sfarcat ar setter & |

Nature is the symbol of the spirit.

SAH FAT SS BG AT Bea HT STAT LAT |

A good leader is one who follows the followers.
"""


def test_essay_topics_sections_and_printed_marks():
    vocab = vocab_for("a grateful mind is very beautiful when two elephants fight it is the grass "
                      "that gets trampled nature is the symbol of the spirit a good leader is one "
                      "who follows the followers")
    staged = extract(ESSAY, paper="ESSAY", vocab=vocab)
    got = [(q["official_number"], q["section"], q["text"]) for q in staged["questions"]]
    assert got == [
        (1, "A", "A grateful mind is very beautiful."),
        (2, "A", "When two elephants fight, it is the grass that gets trampled."),
        (3, "B", "Nature is the symbol of the spirit."),
        (4, "B", "A good leader is one who follows the followers."),
    ]
    assert {q["word_limit"] for q in staged["questions"]} == {"1000-1200"}
    assert {q["marks"] for q in staged["questions"]} == {"125"}
    # The real paper has eight topics; a four-topic read is flagged, not trusted.
    assert staged["paper_flags"] == ["count_mismatch:expected=8,extracted=4"]


# ── dedupe + routing ─────────────────────────────────────────────────────


def test_english_part_drops_mojibake_and_word_limits():
    db = "Ã Â¤â¹Ã Â¤â (Ã Â¤â°Ã 150) Ã¢â¬â 10 Underline the changes in society. (Answer in 150 words)"
    english = egm.english_part(db)
    assert english.endswith("Underline the changes in society.")
    assert "Answer" not in english and "Ã" not in english


def test_routing_present_near_and_insert():
    pool = [
        {"id": "exact", "text": Q[1]},
        {"id": "para", "text": "Discuss the role of wind processes in desertification in arid lands."},
    ]
    staged = egm.route_paper(extract(CLEAN), pool)
    routes = {q["official_number"]: (q["route"], q["best_db_match"]["id"]) for q in staged["questions"]}
    assert routes[1] == ("present", "exact")
    assert routes[2][0] == "near_match" and routes[2][1] == "para"
    assert routes[3][0] == "insert" and routes[4][0] == "insert"


def test_subpart_contained_in_a_combined_db_row_counts_as_present():
    part_a = ("Owing to paucity of time, a university professor generates a Ph.D. evaluation "
              "report using Artificial Intelligence and submits it with some modifications.")
    combined = (f"(a) {part_a} (b) Efficiency is doing things right, while effectiveness is "
                "doing the right thing. How do you strike a balance between the two?")
    score, measure = egm.similarity(part_a, combined)
    assert score >= egm.PRESENT_CUT and measure == "containment"


def test_near_matches_are_never_review_rows():
    pool = [{"id": "para", "text": "Discuss the role of wind processes in desertification in arid lands."}]
    staged = egm.route_paper(extract(CLEAN), pool)
    review = egm.review_rows(staged)
    near = egm.near_rows(staged)
    assert [r["official_number"] for r in near] == [2]
    assert 2 not in [r["official_number"] for r in review]
    assert all(r["approved"] == "" for r in review)


def test_staged_output_keeps_insert_route_only():
    pool = [{"id": "exact", "text": Q[1]}]
    out = egm.staged_for_output(egm.route_paper(extract(CLEAN), pool))
    assert [q["official_number"] for q in out["questions"]] == [2, 3, 4]
    assert out["exam_id"] == egm.EXAM_ID and out["paper_code"] == "UPSC-CSE-MAINS-GS-2026-GS1"


def test_rerun_keeps_the_reviewers_columns(tmp_path):
    staged = egm.route_paper(extract(CLEAN), [])
    rows = egm.review_rows(staged)
    path = tmp_path / "review.csv"
    rows[0]["approved"], rows[0]["edited_text"] = "Y", "Edited."
    egm.write_csv(path, egm.REVIEW_FIELDS, rows)
    merged = egm.merge_review(egm.review_rows(staged), path)
    assert merged[0]["approved"] == "Y" and merged[0]["edited_text"] == "Edited."
    assert merged[1]["approved"] == ""
    with path.open(encoding="utf-8") as fh:
        assert list(csv.DictReader(fh))[0]["content_hash"] == merged[0]["content_hash"]


def test_extraction_is_deterministic():
    assert extract(CLEAN) == extract(CLEAN)
