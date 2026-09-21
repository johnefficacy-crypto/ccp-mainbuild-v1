"""The sort_order backfill's planning, which is where it can be wrong.

The order source is the thirteen syllabus files, already compiled into
`syllabus_index.json`. This script writes that order onto `topics.metadata`;
these pin that it only ever writes a position the source actually states.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
_SPEC = importlib.util.spec_from_file_location(
    "backfill_topic_sort_order", ROOT / "scripts" / "backfill_topic_sort_order.py"
)
mod = importlib.util.module_from_spec(_SPEC)
sys.modules["backfill_topic_sort_order"] = mod
_SPEC.loader.exec_module(mod)

INDEX = json.loads(
    (ROOT / "app" / "backend" / "app" / "study_os" / "syllabus_index.json").read_text(
        encoding="utf-8"
    )
)


def _row(name, level, slug, current=""):
    return {"id": f"id-{name[:12]}", "name": name, "level": level,
            "parent_id": None, "subject_slug": slug, "current_sort": current}


@pytest.mark.parametrize("slug,paper", [
    ("upsc-cse-mains-opt-psir-p1", "opt-psir-p1"),
    ("upsc-cse-mains-gs2", "GS_2"),
])
def test_paper_of_canonical_slugs(slug, paper):
    assert mod._paper_of(slug) == paper


@pytest.mark.parametrize("slug", [
    "upsc-mains-gs1", "upsc-gs-paper-1", "upsc-mains-essay", "",
])
def test_paper_of_ignores_the_empty_shells(slug):
    assert mod._paper_of(slug) is None


def test_a_section_gets_the_order_the_syllabus_states():
    paper = next(p for p in INDEX["papers"] if p["paper_id"] == "opt-psir-p1")
    first, second = paper["sections"][0], paper["sections"][1]
    rows = [
        _row(second["section"], "topic", "upsc-cse-mains-opt-psir-p1"),
        _row(first["section"], "topic", "upsc-cse-mains-opt-psir-p1"),
    ]
    writes, skipped = mod._plan(INDEX, rows)
    by_id = dict(writes)
    assert by_id[f"id-{first['section'][:12]}"] == first["order"]
    assert by_id[f"id-{second['section'][:12]}"] == second["order"]
    assert skipped == []


def test_a_microtopic_gets_its_position_within_its_section():
    name, hits = next(
        (n, h) for n, h in INDEX["themes"].items() if len(h) == 1
    )
    rows = [_row(name, "microtopic", _slug_for(hits[0]["paper_id"]))]
    writes, skipped = mod._plan(INDEX, rows)
    assert writes and writes[0][1] == hits[0]["order"]
    assert skipped == []


def _slug_for(paper_id):
    if paper_id.startswith("GS_"):
        return f"upsc-cse-mains-gs{paper_id[-1]}"
    return f"upsc-cse-mains-{paper_id}"


def test_an_unknown_name_is_skipped_not_guessed():
    rows = [_row("A section no syllabus contains", "topic", "upsc-cse-mains-gs1")]
    writes, skipped = mod._plan(INDEX, rows)
    assert writes == []
    assert len(skipped) == 1 and "no unique topic" in skipped[0]


def test_a_topic_under_an_empty_shell_is_skipped():
    rows = [_row("Indian Culture", "topic", "upsc-mains-gs1")]
    writes, skipped = mod._plan(INDEX, rows)
    assert writes == []
    assert "is not a paper" in skipped[0]


def test_rerunning_writes_nothing():
    """Idempotent: a row already carrying the right sort_order is not touched."""
    paper = next(p for p in INDEX["papers"] if p["paper_id"] == "GS_1")
    section = paper["sections"][0]
    rows = [_row(section["section"], "topic", "upsc-cse-mains-gs1",
                 current=str(section["order"]))]
    writes, skipped = mod._plan(INDEX, rows)
    assert writes == []
    assert skipped == []


def test_a_name_that_appears_twice_in_one_paper_is_skipped():
    """More than one position for the same name is an ambiguity, not a tie."""
    dupes = [
        (n, h) for n, h in INDEX["themes"].items()
        if len({x["paper_id"] for x in h}) < len(h)
    ]
    if not dupes:
        pytest.skip("no within-paper duplicate theme names in the current files")
    name, hits = dupes[0]
    rows = [_row(name, "microtopic", _slug_for(hits[0]["paper_id"]))]
    writes, _ = mod._plan(INDEX, rows)
    assert writes == []


# ── the short-label vocabulary (the GS skip bug) ───────────────────────────
# A dry run placed 1282 rows and skipped 444, ALL of them GS, all reporting
# "no unique microtopic in GS_n". The subject mapping was fine and the rows
# existed: the syllabus file writes a micro_theme as a full line, while those
# `topics` rows hold only the label before its colon, so whole-string equality
# could never join the two.

GS_SHORT_LABELS = [
    ("French Revolution", "GS_1"),
    ("Aurangzeb", "GS_1"),
    ("Interior of the Earth", "GS_1"),
    ("Indo-Islamic architecture", "GS_1"),
]


@pytest.mark.parametrize("name,paper", GS_SHORT_LABELS)
def test_a_short_gs_label_resolves_to_the_full_micro_theme(name, paper):
    """The exact four names verified present in the demo database."""
    rows = [_row(name, "microtopic", f"upsc-cse-mains-gs{paper[-1]}")]
    writes, skipped = mod._plan(INDEX, rows)

    assert skipped == []
    assert len(writes) == 1
    # The position is the syllabus's, not an invention: the same theme looked
    # up through the catalogue's resolver gives the same number.
    hits = mod.syllabus.theme_hits(name, paper_id=paper)
    assert len(hits) == 1
    assert writes[0][1] == hits[0]["order"]


def test_all_four_verified_names_place_together_in_one_pass():
    rows = [_row(n, "microtopic", f"upsc-cse-mains-gs{p[-1]}") for n, p in GS_SHORT_LABELS]
    writes, skipped = mod._plan(INDEX, rows)
    assert skipped == []
    assert len(writes) == len(GS_SHORT_LABELS)


def test_the_full_micro_theme_line_still_places():
    """The fix adds a second key; it must not cost the first. Rows written by
    `ingest_upsc_gs_syllabus.py` hold the whole line."""
    paper = next(p for p in INDEX["papers"] if p["paper_id"] == "GS_1")
    full = next(n for n, hits in INDEX["themes"].items()
                if any(h["paper_id"] == "GS_1" for h in hits) and ":" in n)
    writes, skipped = mod._plan(INDEX, [_row(full, "microtopic", "upsc-cse-mains-gs1")])
    assert skipped == []
    assert writes[0][1] == next(h["order"] for h in INDEX["themes"][full]
                                if h["paper_id"] == "GS_1")
    assert paper  # the paper exists; guards the fixture above


def test_every_gs_micro_theme_places_by_its_head_except_the_ambiguous_ones():
    """Dry-run expectation, checked against the index rather than the database.

    Four GS labels are shared by more than one syllabus theme and stay skipped,
    because no rule can say which of them a bare row meant:

    * 'Flagship schemes' (GS2) and 'Case studies' (GS4) — several distinct
      themes are written under each;
    * 'Constitutional Bodies' and 'Constitutional bodies' (GS2) — two different
      themes in the same section whose labels differ only in one capital. The
      resolver case-folds, so a row holding the bare label is ambiguous. That is
      the honest answer: a capital B is not a distinction a `topics` row can be
      trusted to preserve, and a row holding the FULL line still places, because
      the whole-line key is tried first and the two lines differ.

    Every other GS theme places from its label alone.
    """
    rows, expected_skips = [], []
    for paper_id in ("GS_1", "GS_2", "GS_3", "GS_4"):
        slug = f"upsc-cse-mains-gs{paper_id[-1]}"
        heads: dict[str, dict[str, set]] = {}
        for name, hits in INDEX["themes"].items():
            for hit in hits:
                if hit["paper_id"] == paper_id:
                    # Build the expectation with the resolver's OWN key, not a
                    # restatement of it — a test that folds differently from the
                    # code is testing its own fixture.
                    slot = heads.setdefault(mod.syllabus.theme_head(name),
                                            {"labels": set(), "orders": set()})
                    slot["labels"].add(name.split(":", 1)[0].strip())
                    slot["orders"].add(hit["order"])
        for slot in heads.values():
            label = sorted(slot["labels"])[0]
            rows.append(_row(label, "microtopic", slug))
            if len(slot["orders"]) > 1:
                expected_skips.append(label)

    writes, skipped = mod._plan(INDEX, rows)
    assert sorted(expected_skips) == [
        "Case studies", "Constitutional Bodies", "Flagship schemes",
    ]
    assert len(skipped) == len(expected_skips)
    for label in expected_skips:
        assert any(line.startswith(label) for line in skipped)
    assert len(writes) == len(rows) - len(expected_skips)


def test_two_themes_differing_only_in_capitalisation_place_from_their_full_lines():
    """The corollary of the case fold: ambiguity costs the bare label, not the
    row that actually carries the syllabus line."""
    lines = sorted(n for n in INDEX["themes"]
                   if n.lower().startswith("constitutional bodies:"))
    assert len(lines) == 2

    writes, skipped = mod._plan(
        INDEX, [_row(line, "microtopic", "upsc-cse-mains-gs2") for line in lines]
    )
    assert skipped == []
    assert sorted(o for _, o in writes) == sorted(
        h["order"] for line in lines for h in INDEX["themes"][line]
    )


def test_an_ambiguous_label_is_skipped_rather_than_given_the_first_position():
    writes, skipped = mod._plan(INDEX, [_row("Case studies", "microtopic",
                                             "upsc-cse-mains-gs4")])
    assert writes == []
    assert skipped and "no unique microtopic in GS_4" in skipped[0]


def test_a_name_in_no_syllabus_at_all_is_still_reported():
    writes, skipped = mod._plan(INDEX, [_row("Nothing In The Syllabus", "microtopic",
                                             "upsc-cse-mains-gs1")])
    assert writes == []
    assert "no unique microtopic in GS_1" in skipped[0]


def test_a_head_does_not_leak_across_papers():
    """`theme_hits` is narrowed by paper, so a GS1 label cannot take a GS3
    position just because the string appears there too."""
    rows = [_row("Aurangzeb", "microtopic", "upsc-cse-mains-gs3")]
    writes, skipped = mod._plan(INDEX, rows)
    assert writes == []
    assert "no unique microtopic in GS_3" in skipped[0]


def test_the_script_uses_the_catalogue_resolver_rather_than_its_own_copy():
    """One resolver. A second copy of the name rules is how the script and the
    catalogue came to disagree in the first place."""
    assert mod._paper_of is mod.syllabus.paper_id_from_subject_slug
