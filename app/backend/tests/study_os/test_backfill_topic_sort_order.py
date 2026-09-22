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
