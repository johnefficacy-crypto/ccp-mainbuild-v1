"""The compiled syllabus index, and what it is allowed to be.

`syllabus_index.json` is generated from the thirteen files under
`docs/reference/syllabus/`. It exists for ONE fact the schema cannot express —
order — and these pin that it stays that: in sync with its sources, derived
rather than typed, and never a second copy of the topic tree.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from app.study_os import syllabus as syl

ROOT = Path(__file__).resolve().parents[4]
SOURCE_DIR = ROOT / "docs" / "reference" / "syllabus"

_SPEC = importlib.util.spec_from_file_location(
    "build_syllabus_index", ROOT / "scripts" / "build_syllabus_index.py"
)
builder = importlib.util.module_from_spec(_SPEC)
sys.modules["build_syllabus_index"] = builder
_SPEC.loader.exec_module(builder)


def test_the_committed_index_matches_its_sources():
    """The one way this can rot: a syllabus file is edited and nobody
    regenerates. Then the tree is ordered by a document that no longer exists."""
    expected = builder.serialise(builder.build())
    actual = builder.OUT.read_text(encoding="utf-8")
    assert actual == expected, (
        "syllabus_index.json is stale — run "
        "`python scripts/build_syllabus_index.py --write`"
    )


def test_every_source_file_is_represented():
    index = json.loads(builder.OUT.read_text(encoding="utf-8"))
    on_disk = {
        p.name
        for pattern in builder.SOURCE_GLOBS
        for p in SOURCE_DIR.glob(pattern)
    }
    assert set(index["sources"]) == on_disk


def test_the_twelve_optional_papers_and_four_gs_papers_are_all_there():
    index = json.loads(builder.OUT.read_text(encoding="utf-8"))
    ids = {p["paper_id"] for p in index["papers"]}

    gs = {i for i in ids if i.startswith("GS_")}
    opt = {i for i in ids if i.startswith("opt-")}
    assert gs == {"GS_1", "GS_2", "GS_3", "GS_4"}
    assert len(opt) == 12, sorted(opt)
    # Six subjects, each with Paper I and Paper II.
    subjects = {i.rsplit("-p", 1)[0] for i in opt}
    assert len(subjects) == 6
    assert all(f"{s}-p1" in opt and f"{s}-p2" in opt for s in subjects)


def test_index_carries_order_and_not_a_copy_of_the_tree():
    """It holds paper, section, part and two sort keys. It does NOT hold topic
    ids, slugs or descriptions — those live in `public.topics`, and a second
    copy is a second thing to keep true."""
    index = json.loads(builder.OUT.read_text(encoding="utf-8"))
    section = index["papers"][0]["sections"][0]
    assert set(section) == {"section", "part", "order"}
    placement = next(iter(index["themes"].values()))[0]
    assert set(placement) == {"paper_id", "section", "section_order", "order"}


@pytest.mark.parametrize("paper_id,label,number", [
    ("GS_1", "GS1", 1),
    ("GS_4", "GS4", 4),
    ("opt-psir-p1", "P1", 1),
    ("opt-sociology-p2", "P2", 2),
])
def test_paper_labels_and_numbers(paper_id, label, number):
    assert syl.paper_label(paper_id) == label
    assert syl.paper_number(paper_id) == number


def test_section_parts_are_carried_for_the_four_papers_that_have_them():
    """M10-rev3: a syllabus's named parts are metadata, never topic rows and
    never exam_phase_sections. Four of the twelve optionals carry them."""
    index = json.loads(builder.OUT.read_text(encoding="utf-8"))
    with_parts = {
        p["paper_id"]
        for p in index["papers"]
        if any(s["part"] for s in p["sections"])
    }
    assert with_parts == {
        "opt-geography-p1", "opt-psir-p1", "opt-psir-p2", "opt-sociology-p2"
    }


# ── placement ────────────────────────────────────────────────────────────


def test_stamped_metadata_places_a_theme_without_consulting_the_index():
    """The ingest stamps paper_id and macro_topic on every microtopic. That is
    authoritative — it was written from the same file the index was built from."""
    spot = syl.place({
        "name": "a name the index has never seen",
        "metadata": {"paper_id": "opt-psir-p1", "macro_topic": "Section that is not real"},
    })
    assert spot["placed"] is True
    assert spot["paper_label"] == "P1"
    assert spot["section"] == "Section that is not real"
    # An unindexed section sorts after every numbered unit but before "Other".
    assert spot["section_sort"] < 10**6


def test_an_unstamped_theme_is_placed_by_exact_name():
    index = json.loads(builder.OUT.read_text(encoding="utf-8"))
    name, hits = next(
        (n, h) for n, h in index["themes"].items() if len(h) == 1
    )
    spot = syl.place({"name": name, "metadata": {}})
    assert spot["placed"] is True
    assert spot["paper_id"] == hits[0]["paper_id"]
    assert spot["section"] == hits[0]["section"]


def test_an_ambiguous_name_is_not_placed():
    """A theme name under two papers is not a match. No scoring, no tie-break:
    an ambiguous match is not a match."""
    index = json.loads(builder.OUT.read_text(encoding="utf-8"))
    ambiguous = [n for n, h in index["themes"].items() if len(h) > 1]
    if not ambiguous:
        pytest.skip("no cross-paper name collisions in the current syllabus files")
    spot = syl.place({"name": ambiguous[0], "metadata": {}})
    assert spot["placed"] is False
    assert spot["section"] == syl.UNPLACED_SECTION


def test_an_unknown_theme_is_unplaced_not_guessed():
    spot = syl.place({"name": "Something no syllabus contains", "metadata": {}})
    assert spot["placed"] is False
    assert spot["paper_id"] is None
    assert spot["section"] == syl.UNPLACED_SECTION
    assert spot["paper_label"] == syl.UNPLACED_PAPER_LABEL


def test_a_missing_index_degrades_to_flat_rather_than_raising(monkeypatch):
    """A build artefact must not be able to take down the answer-writing
    surface. Losing it costs the nesting, not the page."""
    syl.reset_caches()
    monkeypatch.setattr(syl, "_INDEX_PATH", ROOT / "does-not-exist.json")
    try:
        assert syl.index() == {"papers": [], "themes": {}}
        assert syl.place({"name": "x", "metadata": {}})["placed"] is False
    finally:
        monkeypatch.undo()
        syl.reset_caches()


# ── the catalogue's GS ordering (the same vocabulary bug) ──────────────────
# A GS theme was PLACED correctly — routes 1 and 2 read the stamped metadata
# and the tree — but `theme_sort` came from an exact whole-line lookup that a
# short label never matched. Every GS theme in a section therefore tied at the
# fallback, and the catalogue showed them in arbitrary order while claiming
# syllabus order.

GS_SHORT_LABELS = [
    ("French Revolution", "GS_1"),
    ("Aurangzeb", "GS_1"),
    ("Interior of the Earth", "GS_1"),
    ("Indo-Islamic architecture", "GS_1"),
]


@pytest.mark.parametrize("name,paper", GS_SHORT_LABELS)
def test_a_short_gs_label_gets_its_real_theme_sort_not_the_fallback(name, paper):
    spot = syl.place({
        "name": name,
        "metadata": {},
        "subject_slug": f"upsc-cse-mains-gs{paper[-1]}",
        "parent_topic_name": None,
    })
    hit = syl.theme_hits(name, paper_id=paper)
    assert len(hit) == 1
    assert spot["paper_id"] == paper
    assert spot["theme_sort"] == hit[0]["order"]
    assert spot["theme_sort"] < 10**5  # the fallback the bug left behind


def test_short_labels_in_one_section_come_out_in_syllabus_order():
    """The user-visible half: two themes of one section must not tie."""
    section = "Indian Culture"
    names = [n for n, hits in syl.index()["themes"].items()
             if any(h["paper_id"] == "GS_1" and h["section"] == section for h in hits)]
    assert len(names) > 2
    placed = [
        (syl.place({"name": n.split(":", 1)[0].strip(), "metadata": {},
                    "subject_slug": "upsc-cse-mains-gs1",
                    "parent_topic_name": section})["theme_sort"], n)
        for n in names
    ]
    sorts = [s for s, _ in placed]
    assert len(set(sorts)) == len(sorts), "themes tied — ordering is arbitrary again"
    expected = [next(h["order"] for h in syl.index()["themes"][n]
                     if h["paper_id"] == "GS_1" and h["section"] == section)
                for n in names]
    assert sorts == expected


def test_the_whole_line_is_preferred_over_a_head_that_matches_elsewhere():
    """Adding the head key must not divert a row that carries the full line."""
    lines = sorted(n for n in syl.index()["themes"]
                   if n.lower().startswith("constitutional bodies:"))
    assert len(lines) == 2
    orders = {syl.place({"name": line, "metadata": {},
                         "subject_slug": "upsc-cse-mains-gs2"})["theme_sort"]
              for line in lines}
    assert len(orders) == 2 and 10**5 not in orders


def test_a_label_shared_by_two_themes_keeps_the_fallback_rather_than_guessing():
    spot = syl.place({"name": "Case studies", "metadata": {},
                      "subject_slug": "upsc-cse-mains-gs4"})
    assert spot["paper_id"] == "GS_4"
    assert spot["theme_sort"] == 10**5


def test_theme_hits_is_narrowed_by_paper():
    assert syl.theme_hits("Aurangzeb", paper_id="GS_1")
    assert syl.theme_hits("Aurangzeb", paper_id="GS_3") == []


def test_theme_key_folds_encoding_and_whitespace_only():
    assert syl.theme_key("  Indo-Islamic   architecture ") == syl.theme_key("indo-islamic architecture")
    assert syl.theme_key("Aurangzeb") != syl.theme_key("Akbar")
    assert syl.theme_head("Aurangzeb: religious policy phases") == syl.theme_key("Aurangzeb")
    assert syl.theme_head("French Revolution") == syl.theme_key("French Revolution")
