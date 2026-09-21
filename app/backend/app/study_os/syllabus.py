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
index by theme name second. There is no fuzzy match and no scoring: a theme
this module cannot place is reported as unplaced and shown to the aspirant in
an explicit "Other" group, never guessed into a section it might not belong to.

TWO VOCABULARIES NAME THE SAME THEME. A micro_theme in the syllabus files is a
full descriptive line — "Aurangzeb: religious policy phases, temples/jizyah,
territorial consolidation, popular revolts (Jats, Satnamis, Sikhs), and the
climax/crisis of the empire". Many `topics` rows predating that ingest hold the
short label alone — "Aurangzeb". Matching on the whole string finds neither
from the other, which is why GS themes had no order at all: `theme_sort` fell
back to its default for every one of them and a section came out in arbitrary
sequence.

So a name is resolved on TWO exact keys, tried in order: the whole line, then
its HEAD — the text before the first colon. Both are exact string equality on a
deterministically derived key, not a fuzzy match, and a head that is not unique
within its paper resolves to nothing rather than to a guess. `theme_hits` is
the only place either key is computed; every caller, this module and
`scripts/backfill_topic_sort_order.py` alike, goes through it.
"""
from __future__ import annotations

import json
import logging
import re
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


def theme_key(name: Any) -> str:
    """The comparison key for a theme name: collapsed, case-folded, no colon tail.

    `unicodedata` normalisation and whitespace collapsing only — the same
    string in two encodings or with a doubled space is the same theme, and
    nothing else is treated as equal to anything.
    """
    import unicodedata

    text = unicodedata.normalize("NFKC", str(name or ""))
    return re.sub(r"\s+", " ", text).strip().casefold()


def theme_head(name: Any) -> str:
    """`theme_key` of the text before the first colon.

    The syllabus writes a micro_theme as "<label>: <elaboration>", so the head
    is the label the older `topics` rows hold on their own. A name with no colon
    is its own head, which is why the two indexes below can safely overlap.
    """
    return theme_key(str(name or "").split(":", 1)[0])


@lru_cache(maxsize=1)
def _themes_by_key() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for name, hits in index().get("themes", {}).items():
        out.setdefault(theme_key(name), []).extend(hits)
    return out


@lru_cache(maxsize=1)
def _themes_by_head() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for name, hits in index().get("themes", {}).items():
        out.setdefault(theme_head(name), []).extend(hits)
    return out


def theme_hits(name: Any, *, paper_id: str | None = None) -> list[dict[str, Any]]:
    """Every index entry this theme name refers to, narrowed to one paper.

    The whole line is tried first and the head only if it matched nothing, so a
    row that carries the full micro_theme can never be diverted to a different
    theme that happens to share its label.

    Ambiguity is the caller's to reject, not this function's to resolve: two
    hits are returned as two. `Flagship schemes` in GS2 and `Case studies` in
    GS4 are real examples — several distinct syllabus themes share that label,
    and no rule here can say which one a row named `Case studies` meant.
    """
    key = theme_key(name)
    hits = _themes_by_key().get(key) or _themes_by_head().get(theme_head(name)) or []
    if paper_id:
        hits = [h for h in hits if h.get("paper_id") == paper_id]
    return list(hits)


@lru_cache(maxsize=1)
def _section_part() -> dict[tuple[str, str], str | None]:
    out: dict[tuple[str, str], str | None] = {}
    for paper in index().get("papers", []):
        for section in paper.get("sections", []):
            out[(paper["paper_id"], section["section"])] = section.get("part")
    return out


def reset_caches() -> None:
    """Drop every compiled view of the index.

    Tests that swap the index file call this. It exists so adding a cache here
    does not silently leave a test reading a stale one — enumerate them once,
    in the module that owns them.
    """
    for cached in (index, _papers_by_id, _section_order, _section_part,
                   _themes_by_key, _themes_by_head):
        cached.cache_clear()


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


#: Canonical subject slugs. The GS shells `upsc-mains-gs1..4`,
#: `upsc-mains-essay` and `upsc-gs-paper-1` are empty and are NOT these.
_SLUG_PAPER = {
    "upsc-cse-mains-gs1": "GS_1",
    "upsc-cse-mains-gs2": "GS_2",
    "upsc-cse-mains-gs3": "GS_3",
    "upsc-cse-mains-gs4": "GS_4",
}

_OPT_SLUG = re.compile(r"\Aupsc-cse-mains-(opt-[a-z0-9-]+-p[12])\Z")


def paper_id_from_subject_slug(slug: Any) -> str | None:
    """`upsc-cse-mains-opt-psir-p1` -> `opt-psir-p1`; `...-gs1` -> `GS_1`.

    THE PAPER AXIS IS THE TAG'S SUBJECT. A primary tag points at a microtopic,
    a microtopic belongs to a subject, and for this exam the subject row IS the
    paper. That holds for the thematic half too, which is what lets a theme
    compilation be filed under Paper I without a sitting to read it from.

    Returns None for anything else, including the empty GS shells
    (`upsc-mains-gs1`, `upsc-gs-paper-1`) — they carry no tree, and guessing
    that they mean GS1 would file real questions under a subject nobody tags.
    """
    text = str(slug or "").strip().lower()
    if text in _SLUG_PAPER:
        return _SLUG_PAPER[text]
    m = _OPT_SLUG.match(text)
    return m.group(1) if m else None


def _meta(topic: Any) -> dict[str, Any]:
    raw = (topic or {}).get("metadata")
    return raw if isinstance(raw, dict) else {}


def place(topic: dict[str, Any]) -> dict[str, Any]:
    """Where this theme sits: paper id, section, and both sort keys.

    Three sources, tried in order and never blended:

    1. The metadata the ingest stamped on the row. Authoritative, because the
       ingest wrote it from the same syllabus file this index was compiled
       from.
    2. The row's position in the tree: `subject_slug` gives the paper (the
       subject row IS the paper for this exam) and `parent_topic_name` gives
       the syllabus section. Always present on an ingested microtopic.
    3. The index, by EXACT theme name, for a topic created outside the ingest.
       A name that appears under two papers is not placed by this route — an
       ambiguous match is not a match.

    A theme neither route places gets `paper_id=None`, which the catalogue
    renders as the explicit "Other" group rather than hiding.
    """
    meta = _meta(topic)
    name = str(topic.get("name") or "").strip()

    paper_id = str(meta.get("paper_id") or "").strip() or None
    section = str(meta.get("macro_topic") or "").strip() or None

    # Route 2: the row's own place in the tree. A tag points at a microtopic,
    # whose parent topic is the syllabus section and whose subject is the
    # paper. Both come off the row, so this works for every ingested topic
    # whether or not the metadata stamp is present.
    if not paper_id:
        paper_id = paper_id_from_subject_slug(topic.get("subject_slug"))
    if not section:
        section = str(topic.get("parent_topic_name") or "").strip() or None

    # Route 3: the compiled index, by theme name, for a topic created outside
    # the ingest. An ambiguous name is not a match.
    if not (paper_id and section):
        matches = theme_hits(name)
        if len(matches) == 1:
            hit = matches[0]
            paper_id = paper_id or hit["paper_id"]
            section = section or hit["section"]

    theme_order: int | None = None
    if paper_id:
        within = theme_hits(name, paper_id=paper_id)
        exact = [h for h in within if h.get("section") == section]
        # The section is preferred, but a name unique within its PAPER is still
        # unambiguous — and the two vocabularies disagree about section names
        # more often than about theme names. One hit in the paper is a match;
        # two are not, whatever their sections say.
        chosen = exact if len(exact) == 1 else (within if len(within) == 1 else [])
        if chosen:
            theme_order = chosen[0]["order"]

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
        # The official syllabus line for the section, shown as its subtitle.
        # Stamped on the PARENT topic by the ingest.
        "section_line": str(topic.get("parent_official_line") or "").strip() or None,
        "placed": bool(paper_id and section),
    }
