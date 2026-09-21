"""Where a theme sits in the official UPSC syllabus.

THE HIERARCHY IS ALREADY IN THE DATABASE. `scripts/ingest_upsc_gs_syllabus.py`
writes it from the thirteen files under `docs/reference/syllabus/`:

* the SUBJECT row is the paper — `upsc-cse-mains-gs1`, `upsc-cse-mains-opt-anthropology-p1`;
* a `topics` row at `level='topic'` is a numbered syllabus unit (the section);
* a `topics` row at `level='microtopic'` under it is a theme.

and it stamps `metadata.paper_id` on both and `metadata.macro_topic` on every
microtopic. So a theme already knows its paper and its section with no join and
no guess. Decision M10-rev3 fixed that shape: the numbered units ARE the topic
level, a syllabus's named parts are metadata, and parts are never
`exam_phase_sections`.

WHAT THE DATABASE CANNOT SAY IS ORDER. `public.topics` has no sort column, so
reading the tree back gives the right nesting in an arbitrary sequence.
Syllabus order is a property of the official document, so it comes from the
document: `syllabus_index.json`, compiled by `scripts/build_syllabus_index.py`
and checked against its sources by `test_syllabus_index.py`.

DETERMINISM OVER HEURISTICS. Placement reads stamped metadata first and the
index by exact theme name second. There is no fuzzy match and no scoring: a
theme this module cannot place is reported as unplaced and shown to the
aspirant in an explicit "Other" group, never guessed into a section it might
not belong to.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger("career_copilot.study_os.syllabus")

_INDEX_PATH = Path(__file__).resolve().parent / "syllabus_index.json"

#: The group unplaced themes fall into. Visible, and last within its paper.
UNPLACED_SECTION = "Other"

#: The pseudo-paper for themes whose paper cannot be determined at all.
UNPLACED_PAPER = "other"
UNPLACED_PAPER_LABEL = "Other"

#: Sorts after every real paper (GS4 = 4, Essay = 99).
_UNPLACED_SORT = 999


@lru_cache(maxsize=1)
def index() -> dict[str, Any]:
    """The compiled syllabus index, or an empty one if it is missing.

    Degrades rather than raises: a missing index costs the nesting, and a flat
    theme list is a worse catalogue but still a working one. An exception here
    would take down the whole answer-writing surface for a build artefact.
    """
    try:
        return json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("syllabus index unavailable (%s); themes will be flat", exc)
        return {"papers": [], "themes": {}}


@lru_cache(maxsize=1)
def _papers_by_id() -> dict[str, dict[str, Any]]:
    return {p["paper_id"]: p for p in index().get("papers", [])}


@lru_cache(maxsize=1)
def _section_order() -> dict[tuple[str, str], int]:
    out: dict[tuple[str, str], int] = {}
    for paper in index().get("papers", []):
        for section in paper.get("sections", []):
            out[(paper["paper_id"], section["section"])] = section["order"]
    return out


@lru_cache(maxsize=1)
def _section_part() -> dict[tuple[str, str], str | None]:
    out: dict[tuple[str, str], str | None] = {}
    for paper in index().get("papers", []):
        for section in paper.get("sections", []):
            out[(paper["paper_id"], section["section"])] = section.get("part")
    return out


def paper_label(paper_id: str | None) -> str:
    if not paper_id:
        return UNPLACED_PAPER_LABEL
    paper = _papers_by_id().get(paper_id)
    return paper["label"] if paper else str(paper_id)


def paper_sort(paper_id: str | None) -> int:
    if not paper_id:
        return _UNPLACED_SORT
    paper = _papers_by_id().get(paper_id)
    return paper["sort"] if paper else _UNPLACED_SORT - 1


def paper_number(paper_id: str | None) -> int | None:
    """The sitting number this paper corresponds to: P1 -> 1, GS3 -> 3.

    This is what ties a Paper I tab to the Paper I sittings in the papers list:
    a split optional paper carries `metadata.optional_paper_number`, a GS paper
    carries `metadata.gs_paper`, and both are the same integer as here.
    """
    sort = paper_sort(paper_id)
    return sort if 1 <= sort <= 10 else None


def _meta(topic: Any) -> dict[str, Any]:
    raw = (topic or {}).get("metadata")
    return raw if isinstance(raw, dict) else {}


def place(topic: dict[str, Any]) -> dict[str, Any]:
    """Where this theme sits: paper id, section, and both sort keys.

    Two sources, tried in order and never blended:

    1. The metadata the ingest stamped on the row. Authoritative, because the
       ingest wrote it from the same syllabus file this index was compiled
       from.
    2. The index, by EXACT theme name, for a topic created outside the ingest.
       A name that appears under two papers is not placed by this route — an
       ambiguous match is not a match.

    A theme neither route places gets `paper_id=None`, which the catalogue
    renders as the explicit "Other" group rather than hiding.
    """
    meta = _meta(topic)
    name = str(topic.get("name") or "").strip()

    paper_id = str(meta.get("paper_id") or "").strip() or None
    section = str(meta.get("macro_topic") or "").strip() or None

    if not (paper_id and section):
        matches = index().get("themes", {}).get(name) or []
        if len(matches) == 1:
            hit = matches[0]
            paper_id = paper_id or hit["paper_id"]
            section = section or hit["section"]

    theme_order: int | None = None
    if paper_id and section:
        for hit in index().get("themes", {}).get(name) or []:
            if hit["paper_id"] == paper_id and hit["section"] == section:
                theme_order = hit["order"]
                break

    return {
        "paper_id": paper_id,
        "paper_label": paper_label(paper_id),
        "paper_sort": paper_sort(paper_id),
        "paper_number": paper_number(paper_id),
        "section": section or UNPLACED_SECTION,
        "section_part": _section_part().get((paper_id or "", section or "")),
        # An unrecognised section sorts after every numbered unit but before
        # the catch-all, so a real-but-unindexed unit is not mixed into "Other".
        "section_sort": _section_order().get((paper_id or "", section or ""), 10**5)
        if section
        else 10**6,
        "theme_sort": theme_order if theme_order is not None else 10**5,
        "placed": bool(paper_id and section),
    }
