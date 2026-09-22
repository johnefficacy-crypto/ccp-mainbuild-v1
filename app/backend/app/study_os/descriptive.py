"""Descriptive answer-writing practice — catalogue, questions, attempts.

The mock engine is MCQ-only and cannot host the ~12k verified descriptive PYQ
rows (`pyq_questions.question_type = 'descriptive'`), mostly UPSC CSE Mains
optionals. This module is their runtime: pick a question, write prose against an
optional timer, then judge it yourself against a six-criterion rubric.

**Human decision authority.** Nothing here scores an answer. `self_scores` is
the aspirant's own 0..2 judgement per criterion and `self_total` is its sum. v1
adds no AI evaluation, and the word-limit criterion is the only one with an
objective input — and even that one the aspirant decides.

Where the shape lives:

* `pyq_questions.metadata` carries `optional_subject`, `optional_paper_number`,
  `marks` (~13% present), `marks_source`, `word_limit` (mostly null = no limit),
  `parent_question_number`, `requires_map_sheet`, `map_item`,
  `verified_against_official`, `question_format`, `section_ref`.
* `pyq_papers.metadata` carries `paper_kind`, `corpus_half`, `retired` and
  `split_from_bucket_id`.

Neither set is a column; both are jsonb, so every read below goes through
`_meta()` rather than assuming a key exists.
"""
from __future__ import annotations

import logging
import re
from datetime import date as _date, timedelta as _timedelta
from datetime import datetime, timezone
from typing import Any

from app.study_os import syllabus
from app.common.pagination import paginate

logger = logging.getLogger("career_copilot.study_os.descriptive")

#: `pyq_questions.question_type` value this surface serves.
QUESTION_TYPE = "descriptive"

#: The verified gate is on the QUESTION, not the paper.
#:
#: `pyq_papers.trust_status` describes the provenance of a paper's *composition*
#: — whether we can claim these questions were the paper, in this order. It is
#: orthogonal to whether a question has been reviewed. Every paper the split
#: script writes lands `pending` by design, so gating the catalogue on it hid
#: all 140 split optional papers while leaving the thematic rows (verified,
#: because their composition is not claimed) as the only thing on offer.
#:
#: A question the reviewer has verified is practisable wherever it sits.
QUESTION_REVIEWER_STATUS = "verified"

#: Paper kinds that are General Studies rather than an optional subject.
#: Keyed on `paper_kind` + `metadata.gs_paper`, never on a list of subject
#: names: the subject vocabulary is corpus data and grows without this file.
GS_PAPER_KINDS = frozenset({"gs", "essay"})

#: The subject GS and Essay papers are catalogued under.
GENERAL_STUDIES = "General Studies"

#: Seconds of writing time per mark. UPSC Mains GS is 250 marks in 180 minutes —
#: roughly 43s/mark of pure writing, but an optional paper's 250 marks in the
#: same window with longer answers lands nearer 72s/mark once reading and
#: planning are counted. Advisory only; the UI never enforces it.
SECONDS_PER_MARK = 72

#: The six rubric criteria, each scored 0, 1 or 2 by the aspirant.
RUBRIC_KEYS: tuple[str, ...] = (
    "structure",
    "relevance",
    "coverage",
    "examples",
    "conclusion",
    "within_limit",
)
RUBRIC_MAX_PER_KEY = 2
RUBRIC_MAX_TOTAL = len(RUBRIC_KEYS) * RUBRIC_MAX_PER_KEY  # 12

_ATTEMPT_COLUMNS = (
    "id, user_id, pyq_question_id, status, answer_text, word_count, "
    "time_spent_seconds, timer_target_seconds, pasted_chars, answer_mode, "
    "self_scores, self_total, notes, started_at, submitted_at, updated_at"
)

_QUESTION_COLUMNS = (
    "id, pyq_paper_id, question_number, question_text, question_type, "
    "reviewer_status, metadata"
)

_PAPER_COLUMNS = (
    "id, exam_id, year, paper_code, trust_status, metadata"
)

#: PostgREST URL-length ceiling for an IN() filter.
_IN_CHUNK = 200

#: Rows per range-pagination page. Matches the exam_intelligence package.
#: The walk does not depend on this matching the server ceiling — see
#: `_paginate_all` — so it is a request-size choice, not a correctness one.
_PAGE = 1000

#: Hard stop for the pagination walk. 20k pages is far past any real
#: corpus; reaching it means the server is not honouring `range`.
_MAX_PAGES = 2_000

_DEFAULT_QUESTION_LIMIT = 50
_MAX_QUESTION_LIMIT = 200


class DescriptiveError(Exception):
    """A refusal, carrying the HTTP status the route should return."""

    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


# ── the shared word rule ─────────────────────────────────────────────────
#
# THE SAME RULE RUNS ON BOTH SIDES. The frontend imports `wordCount` from
# `features/study/essay/spineSlots.js`; this is its transliteration, and
# `test_descriptive_word_count.py` pins them against one shared fixture list.
# A live counter that disagrees with the stored one is worse than no counter:
# the aspirant would watch it cross the word limit and then be told it hadn't.

_WHITESPACE = re.compile(r"\s+")


def word_count(text: Any) -> int:
    """Words in ``text``: trim, then split on runs of whitespace.

    Deliberately naive, and deliberately identical to the JS. A hyphenated
    compound is ONE word ("self-reliance"), a newline is a separator like any
    other whitespace, and Devanagari runs count the same as Latin ones because
    neither side looks at the script. Anything cleverer would have to be clever
    identically in two languages.
    """
    trimmed = str(text or "").strip()
    if not trimmed:
        return 0
    return len(_WHITESPACE.split(trimmed))


def timer_target_for(marks: Any) -> int | None:
    """Advisory writing time for a question, or ``None`` when marks are unknown.

    ~87% of descriptive rows carry no `marks`, so ``None`` is the common case,
    not an error. The UI hides the timer target rather than inventing one.
    """
    value = _as_int(marks)
    if value is None or value <= 0:
        return None
    return round(value * SECONDS_PER_MARK)


# ── small helpers ────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _meta(row: dict[str, Any] | None) -> dict[str, Any]:
    """A row's metadata jsonb as a dict, whatever it actually holds."""
    raw = (row or {}).get("metadata")
    return raw if isinstance(raw, dict) else {}


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool:
    """Truthiness of a jsonb value that may be a real bool or a string.

    Extractor output is not uniformly typed: `requires_map_sheet` has arrived as
    both `true` and `"true"`. Treating `"true"` as false would put a map question
    on a surface that cannot render a map sheet.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "t", "yes", "1"}
    if isinstance(value, (int, float)):
        return bool(value)
    return False


def _safe(call: Any, default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("descriptive read failed: %s", exc)
        return default


def _chunks(items: list[Any], size: int = _IN_CHUNK) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _paginate_all(build_query: Any) -> list[dict[str, Any]]:
    """Range-paginate a PostgREST read. See :mod:`app.common.pagination`.

    THIS IS THE BUG THAT MADE 1,351 QUESTIONS LOOK LIKE 19. Every bulk read in
    this module called ``.execute()`` with no ``.range()`` and no ``.order()``,
    so the server returned its first page and the module treated that page as
    the whole corpus. The catalogue then counted a slice: a subject chip read
    19, two papers read 5 each, and the thematic half — whose papers never
    survived the papers read — read "no themes". Nothing errored, because a
    truncated read is a successful one.

    The walk, and the reason it stops on a page that adds nothing new rather
    than on a short one, now live in the shared module; this module was where
    the rule was worked out.
    """
    return paginate(build_query, page_size=_PAGE, max_pages=_MAX_PAGES,
                    table="descriptive").rows

def is_thematic(paper: dict[str, Any]) -> bool:
    """`corpus_half = 'thematic'` — a topic-wise compilation, not a real paper.

    A thematic paper has no sitting, no question order worth honouring and no
    year that means anything, so it is grouped by theme instead of listed as a
    paper.
    """
    return str(_meta(paper).get("corpus_half") or "").strip().lower() == "thematic"


def is_retired(paper: dict[str, Any]) -> bool:
    """`retired = true` — a bucket row whose questions were split into real papers.

    `split_from_bucket_id` on the real rows points back here. Serving a bucket
    would double every question it was split into.
    """
    return _as_bool(_meta(paper).get("retired"))


def is_thematic_question(question: dict[str, Any]) -> bool:
    """The thematic flag as the loader also stamps it on the QUESTION.

    `workbench/scripts/load_thematic.py` writes `corpus_half: "thematic"` onto
    both the paper row and every question row it creates. Reading both is not
    belt-and-braces for its own sake: a question that says it is thematic must
    never be offered as a sat paper, whichever row carries the flag, and a
    single missing key on one paper row is the difference between "no paper
    order" and a year label that claims a sitting.
    """
    return str(_meta(question).get("corpus_half") or "").strip().lower() == "thematic"


def question_is_thematic(question: dict[str, Any], paper: dict[str, Any] | None) -> bool:
    return is_thematic(paper or {}) or is_thematic_question(question)


def paper_kind(paper: dict[str, Any]) -> str:
    return str(_meta(paper).get("paper_kind") or "").strip().lower()


def is_gs_paper(paper: dict[str, Any]) -> bool:
    """A General Studies or Essay paper, by shape rather than by name.

    Keyed on `paper_kind` in {'gs', 'essay'} or the presence of
    `metadata.gs_paper`. No hardcoded subject list: GS papers arrive from a
    separate split, and a catalogue that had to be edited to admit them would
    be wrong again the next time the corpus grew.
    """
    meta = _meta(paper)
    return paper_kind(paper) in GS_PAPER_KINDS or bool(
        str(meta.get("gs_paper") or "").strip()
    )


def subject_of(question: dict[str, Any], paper: dict[str, Any] | None) -> str | None:
    """The subject this question is catalogued under.

    GS and Essay papers are "General Studies"; everything else carries its
    optional subject on the question. The thematic half carries it too — the
    loader stamps `optional_subject` on every thematic question — which is what
    lets themes be filtered by the subject the aspirant picked instead of
    showing Anthropology themes to a Political Science aspirant.
    """
    if paper is not None and is_gs_paper(paper):
        return GENERAL_STUDIES
    name = _meta(question).get("optional_subject")
    text = str(name or "").strip()
    return text or None


#: Short forms for the subjects whose full names are too wide to sit inside a
#: label. Only the ones that actually need it: a name that reads fine at chip
#: width is left alone rather than abbreviated into something an aspirant has
#: to decode.
SUBJECT_SHORT_NAMES = {
    "Political Science and International Relations": "PSIR",
    "Political Science & International Relations": "PSIR",
    "Public Administration": "Pub Ad",
    "General Studies": "GS",
}

#: The longest a subject name may be before it is shortened by initials.
_SHORT_NAME_CUT = 14


def subject_short(name: Any) -> str | None:
    """A subject name short enough to sit inside a paper label.

    "PSIR · 2025 · P1" has to fit on a phone. A known subject uses its real
    abbreviation; an unknown long one is reduced to initials, which is worse
    than a real abbreviation and better than a truncation that could mean two
    different subjects. A short name is returned unchanged.
    """
    text = str(name or "").strip()
    if not text:
        return None
    if text in SUBJECT_SHORT_NAMES:
        return SUBJECT_SHORT_NAMES[text]
    if len(text) <= _SHORT_NAME_CUT:
        return text
    initials = "".join(w[0] for w in re.split(r"[\s&]+", text) if w and w[0].isalpha())
    return initials.upper() if len(initials) >= 2 else text[:_SHORT_NAME_CUT]


#: Every paper an optional subject has, and every paper General Studies has.
#: The tabs come from THIS, not from the questions that happen to exist, so a
#: paper with nothing in it yet is still a tab that says so. A missing tab
#: reads as "this paper does not exist"; an empty tab reads as "not loaded
#: yet", and only one of those is true.
OPTIONAL_PAPER_SLOTS = (
    {"paper_number": 1, "label": "Paper I", "slot": "P1"},
    {"paper_number": 2, "label": "Paper II", "slot": "P2"},
)
GS_PAPER_SLOTS = (
    {"paper_number": 1, "label": "GS1", "slot": "GS1"},
    {"paper_number": 2, "label": "GS2", "slot": "GS2"},
    {"paper_number": 3, "label": "GS3", "slot": "GS3"},
    {"paper_number": 4, "label": "GS4", "slot": "GS4"},
    {"paper_number": 99, "label": "Essay", "slot": "Essay"},
)


def paper_slots_for(subject: Any) -> tuple[dict[str, Any], ...]:
    """The canonical tab list for a subject. Empty when no subject is chosen."""
    if not subject:
        return ()
    return GS_PAPER_SLOTS if str(subject).strip() == GENERAL_STUDIES else OPTIONAL_PAPER_SLOTS


def paper_slot(paper: dict[str, Any]) -> tuple[int, str | None]:
    """(sort key, short label) for the paper's position within its year.

    "P1"/"P2" for an optional, "GS1".."GS4" and "Essay" for General Studies.
    Essay sorts last within its year because it is sat last.
    """
    meta = _meta(paper)
    gs = str(meta.get("gs_paper") or "").strip()
    if gs or paper_kind(paper) in GS_PAPER_KINDS:
        if gs.lower() == "essay" or paper_kind(paper) == "essay":
            return (99, "Essay")
        number = _as_int(gs)
        if number:
            return (number, f"GS{number}")
        return (98, "General Studies")
    number = _as_int(meta.get("optional_paper_number"))
    if number:
        return (number, f"P{number}")
    return (0, None)


# ── question shaping ─────────────────────────────────────────────────────


#: Sub-part letters, in order. Beyond 26 sub-parts a paper is not a paper.
_SUB_LETTERS = "abcdefghijklmnopqrstuvwxyz"


def paper_question_labels(rows: list[dict[str, Any]]) -> dict[str, str]:
    """question_id → "Q5(b)", for every question in ONE paper that has one.

    `question_number` IS NOT A LABEL. The optional corpus is block-encoded:
    each subject's questions start at a hundreds boundary, so the seventh
    question of a paper can be numbered 108. "Q108" told an aspirant nothing
    except that the platform was showing them an internal key, and there is no
    eighth-of-a-hundred-and-eight to compare it to.

    So the label is POSITIONAL, derived from the paper itself:

    * a question nobody names as a parent, and which names no parent, is a main
      question — its label is its rank among the paper's main questions;
    * a question naming `metadata.parent_question_number` is a sub-part — its
      label is the parent's rank plus a letter for its rank among siblings.

    A question the paper cannot place — no `question_number`, as every thematic
    row has by design — gets no label and no entry here. Showing nothing is
    correct; the thematic half has no question order to report.
    """
    numbered = [r for r in rows if _as_int(r.get("question_number")) is not None]
    if not numbered:
        return {}

    parents_named = {
        _as_int(_meta(r).get("parent_question_number"))
        for r in numbered
        if _as_int(_meta(r).get("parent_question_number")) is not None
    }

    mains = sorted(
        (
            r
            for r in numbered
            if _as_int(_meta(r).get("parent_question_number")) is None
        ),
        key=lambda r: _as_int(r.get("question_number")) or 0,
    )
    # A stem row is a main question even though its own children point at it.
    main_rank: dict[int, int] = {}
    for index, row in enumerate(mains, start=1):
        number = _as_int(row.get("question_number"))
        if number is not None:
            main_rank[number] = index

    # A parent named by a sub-part but absent from this paper's rows still
    # needs a rank, or its children would be unlabelled. Rank it by where its
    # number falls among the mains.
    for number in sorted(parents_named - set(main_rank)):
        ahead = sum(1 for n in main_rank if n < number)
        main_rank[number] = ahead + 1

    out: dict[str, str] = {}
    children: dict[int, list[dict[str, Any]]] = {}
    for row in numbered:
        parent = _as_int(_meta(row).get("parent_question_number"))
        if parent is None:
            rank = main_rank.get(_as_int(row.get("question_number")))
            if rank:
                out[str(row.get("id"))] = f"Q{rank}"
        else:
            children.setdefault(parent, []).append(row)

    for parent, kids in children.items():
        rank = main_rank.get(parent)
        if not rank:
            continue
        kids.sort(key=lambda r: _as_int(r.get("question_number")) or 0)
        for index, kid in enumerate(kids):
            letter = _SUB_LETTERS[index] if index < len(_SUB_LETTERS) else None
            out[str(kid.get("id"))] = (
                f"Q{rank}({letter})" if letter else f"Q{rank}"
            )
    return out


def breadcrumb_for(
    question: dict[str, Any],
    *,
    paper: dict[str, Any] | None,
    label: str | None,
    topic: str | None = None,
) -> dict[str, Any]:
    """Where this question came from, in words an aspirant recognises.

    Two shapes, because the corpus has two halves and only one of them was sat:

    * a real paper — "2019 · P1 · Q5(b) · 15 marks", with the subject, paper
      and syllabus section above it;
    * a thematic compilation — "Theme compilation · 2019", and nothing about
      paper order, because there is none.

    Every level is omitted when unknown. A breadcrumb with a blank in it is
    worse than a shorter one: it invites the reader to wonder what is missing.
    """
    meta = _meta(question)
    thematic = question_is_thematic(question, paper)
    year = _as_int((paper or {}).get("year"))
    marks = _as_int(meta.get("marks"))

    trail: list[str] = []
    subject = subject_of(question, paper)
    if subject:
        trail.append(subject)
    if not thematic:
        _, slot = paper_slot(paper or {})
        if slot:
            trail.append(slot)
    section = str(meta.get("section_ref") or "").strip()
    if section:
        trail.append(section)
    if topic:
        trail.append(topic)

    if thematic:
        source = ["Theme compilation"]
        if year:
            source.append(str(year))
    else:
        source = []
        if year:
            source.append(str(year))
        _, slot = paper_slot(paper or {})
        if slot:
            source.append(slot)
        if label:
            source.append(label)
        if marks is not None:
            source.append(f"{marks} marks")

    return {"trail": trail, "source": " · ".join(source) or None}


def question_payload(
    question: dict[str, Any],
    *,
    paper: dict[str, Any] | None = None,
    parent_text: str | None = None,
    attempt_count: int = 0,
    label: str | None = None,
    topic: str | None = None,
) -> dict[str, Any]:
    """One question as the practice surface renders it."""
    meta = _meta(question)
    marks = _as_int(meta.get("marks"))
    return {
        "id": question.get("id"),
        "pyq_paper_id": question.get("pyq_paper_id"),
        # RAW, FOR SORTING AND DEBUGGING ONLY. Block-encoded, so "108" is the
        # seventh question of a subject block, not question 108 of anything an
        # aspirant can see. `label` is what a surface renders.
        "question_number": question.get("question_number"),
        "label": label,
        "breadcrumb": breadcrumb_for(
            question, paper=paper, label=label, topic=topic
        ),
        "text": question.get("question_text") or "",
        # A sub-part is meaningless without its stem — "(b) Examine this" needs
        # the question it is part (b) of.
        "parent_question_number": meta.get("parent_question_number"),
        "parent_text": parent_text,
        "marks": marks,
        "marks_source": meta.get("marks_source"),
        "word_limit": _as_int(meta.get("word_limit")),
        "timer_target_seconds": timer_target_for(marks),
        # Defaults TRUE only when the key is absent would be wrong here: an
        # unverified row must look unverified. Absent means unknown, and unknown
        # is shown to the aspirant as not-yet-verified.
        "verified_against_official": _as_bool(meta.get("verified_against_official")),
        "question_format": meta.get("question_format"),
        "section_ref": meta.get("section_ref"),
        "optional_subject": meta.get("optional_subject"),
        # The subject as the CATALOGUE files it: "General Studies" for a GS
        # or Essay paper, which carries no optional_subject at all.
        "subject": subject_of(question, paper),
        "optional_paper_number": _as_int(meta.get("optional_paper_number")),
        "year": (paper or {}).get("year"),
        "attempt_count": attempt_count,
    }


def requires_map_sheet(question: dict[str, Any]) -> bool:
    """Whether this question needs a map sheet the surface cannot provide.

    Geography optional carries "mark on the outline map" questions. A text
    editor cannot host one, so they are excluded from the practice list — and
    COUNTED, so the aspirant is told what is missing rather than silently served
    a shorter list.
    """
    return _as_bool(_meta(question).get("map_item")) or _as_bool(
        _meta(question).get("requires_map_sheet")
    )


# ── reads ────────────────────────────────────────────────────────────────


def _papers_for_exam(supabase: Any, exam_id: str) -> list[dict[str, Any]] | None:
    """Every paper for this exam, at any `trust_status`.

    Deliberately unfiltered on trust: see QUESTION_REVIEWER_STATUS above. The
    verified gate lives on the question rows this returns paper ids for.
    """
    rows = _safe(
        lambda: _paginate_all(
            lambda a, b: (
                supabase.table("pyq_papers")
                .select(_PAPER_COLUMNS)
                .eq("exam_id", exam_id)
                .order("id")
                .range(a, b)
                .execute()
                .data
            )
        ),
        default=None,
    )
    return None if rows is None else list(rows)


def _verified_questions_for_papers(
    supabase: Any, paper_ids: list[str]
) -> list[dict[str, Any]] | None:
    """Every verified descriptive question on these papers, or ``None`` on error.

    Fails closed as ``None``: an empty catalogue and an unreadable one must not
    look alike, or a transient error would read as "this exam has no descriptive
    questions" on a corpus of twelve thousand.
    """
    out: list[dict[str, Any]] = []
    for chunk in _chunks([str(p) for p in paper_ids]):
        rows = _safe(
            lambda ids=chunk: _paginate_all(
                lambda a, b, ids=ids: (
                    supabase.table("pyq_questions")
                    .select(_QUESTION_COLUMNS)
                    .in_("pyq_paper_id", ids)
                    .eq("question_type", QUESTION_TYPE)
                    .eq("reviewer_status", QUESTION_REVIEWER_STATUS)
                    .order("id")
                    .range(a, b)
                    .execute()
                    .data
                )
            ),
            default=None,
        )
        if rows is None:
            return None
        out.extend(rows)
    return out


def _primary_topics(
    supabase: Any, question_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """question_id → its verified PRIMARY topic ROW (id, name, metadata).

    THE THEME FIELD. There is no dedicated theme column on a thematic paper.
    `essay_pyq_tags.theme_id` exists but is the Essay-paper taxonomy
    (quote_abstract / issue_concrete), wrong for Mains optionals. The general,
    already-governed grouping is `pyq_question_topic_tags`, verified + primary
    only, exactly as `verified_pyq_topic_counts` reads it.

    `metadata` comes back with the row because it is what places the theme in
    the syllabus: `scripts/ingest_upsc_gs_syllabus.py` stamps `paper_id` and
    `macro_topic` on every microtopic it writes. See `study_os/syllabus.py`.

    A question with no verified primary tag is simply absent here; the caller
    groups it under an explicit "Untagged" bucket rather than dropping it.
    """
    if not question_ids:
        return {}
    tags: list[dict[str, Any]] = []
    for chunk in _chunks([str(q) for q in question_ids]):
        rows = _safe(
            lambda ids=chunk: _paginate_all(
                lambda a, b, ids=ids: (
                    supabase.table("pyq_question_topic_tags")
                    .select("question_id, topic_id, tag_role, reviewer_status")
                    .in_("question_id", ids)
                    .eq("tag_role", "primary")
                    .eq("reviewer_status", "verified")
                    .order("question_id")
                    .range(a, b)
                    .execute()
                    .data
                )
            ),
            default=[],
        ) or []
        tags.extend(rows)
    if not tags:
        return {}

    topic_ids = sorted({str(t["topic_id"]) for t in tags if t.get("topic_id")})
    topics: dict[str, dict[str, Any]] = {}
    for chunk in _chunks(topic_ids):
        rows = _safe(
            lambda ids=chunk: _paginate_all(
                lambda a, b, ids=ids: (
                    supabase.table("topics")
                    .select("id, name, level, parent_topic_id, subject_id, metadata")
                    .in_("id", ids)
                    .order("id")
                    .range(a, b)
                    .execute()
                    .data
                )
            ),
            default=[],
        ) or []
        for r in rows:
            if r.get("id"):
                topics[str(r["id"])] = r

    _attach_tree_position(supabase, topics)

    out: dict[str, dict[str, Any]] = {}
    for t in tags:
        qid = str(t.get("question_id") or "")
        tid = str(t.get("topic_id") or "")
        if qid and tid and tid in topics:
            # First verified primary tag wins; a question with two is an
            # ambiguity the tagging lifecycle owns, not this surface.
            out.setdefault(qid, topics[tid])
    return out


def _attach_tree_position(supabase: Any, topics: dict[str, dict[str, Any]]) -> None:
    """Stamp `subject_slug`, `parent_topic_name` and `parent_official_line`.

    THIS IS WHERE THE SYLLABUS TREE COMES FROM ON REAL DATA. A primary tag
    points at a microtopic; the microtopic's PARENT is the numbered syllabus
    section, and its SUBJECT is the paper — `upsc-cse-mains-opt-psir-p1`,
    `upsc-cse-mains-gs3`. Both are ordinary columns, so placement needs no
    metadata stamp and no name matching, and it works for the thematic half
    exactly as it does for a sat paper.

    Two extra reads per catalogue build, both small: distinct parents and
    distinct subjects of the topics already fetched. Failures degrade to an
    unplaced theme rather than raising.
    """
    if not topics:
        return

    parent_ids = sorted({
        str(t["parent_topic_id"]) for t in topics.values() if t.get("parent_topic_id")
    })
    parents: dict[str, dict[str, Any]] = {}
    for chunk in _chunks(parent_ids):
        rows = _safe(
            lambda ids=chunk: _paginate_all(
                lambda a, b, ids=ids: (
                    supabase.table("topics")
                    .select("id, name, metadata")
                    .in_("id", ids)
                    .order("id")
                    .range(a, b)
                    .execute()
                    .data
                )
            ),
            default=[],
        ) or []
        for r in rows:
            if r.get("id"):
                parents[str(r["id"])] = r

    subject_ids = sorted({
        str(t["subject_id"]) for t in topics.values() if t.get("subject_id")
    })
    subjects: dict[str, str] = {}
    for chunk in _chunks(subject_ids):
        rows = _safe(
            lambda ids=chunk: _paginate_all(
                lambda a, b, ids=ids: (
                    supabase.table("subjects")
                    .select("id, slug")
                    .in_("id", ids)
                    .order("id")
                    .range(a, b)
                    .execute()
                    .data
                )
            ),
            default=[],
        ) or []
        for r in rows:
            if r.get("id"):
                subjects[str(r["id"])] = r.get("slug") or ""

    for topic in topics.values():
        topic["subject_slug"] = subjects.get(str(topic.get("subject_id") or ""))
        parent = parents.get(str(topic.get("parent_topic_id") or "")) or {}
        topic["parent_topic_name"] = parent.get("name")
        parent_meta = parent.get("metadata")
        topic["parent_official_line"] = (
            parent_meta.get("official_syllabus_line")
            if isinstance(parent_meta, dict)
            else None
        )


def _primary_topic_names(
    supabase: Any, question_ids: list[str]
) -> dict[str, str]:
    """question_id → its verified primary topic NAME. The filtering view."""
    return {
        qid: (row.get("name") or str(row.get("id")))
        for qid, row in _primary_topics(supabase, question_ids).items()
    }


#: Bucket label for a thematic question carrying no verified primary tag.
UNTAGGED_THEME = "Untagged"


def _syllabus_themes(
    thematic: list[dict[str, Any]],
    topics_by_question: dict[str, dict[str, Any]],
    attempted_ids: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Themes nested paper → section → theme, in syllabus order.

    Returns the nested papers and a flat tab list. Counts are question counts
    at every level, so a section's number is the sum of its themes and a
    paper's is the sum of its sections.

    Two explicit buckets, both visible:

    * a theme the syllabus index cannot place goes under "Other" WITHIN its
      paper when the paper is known, or under a trailing "Other" paper when it
      is not — never hidden, never guessed into a section;
    * a question with no verified primary tag stays "Untagged", as before.

    Both sort last. An aspirant who cannot find a theme should be able to see
    that it exists and where it is not, rather than conclude the corpus is
    missing it.
    """
    counts: dict[tuple[str, str, str], int] = {}
    # Attempted counts ride alongside the question counts at every level, so a
    # microtopic can read "7 · 3 done" without a second pass over the tree.
    done_counts: dict[tuple[str, str, str], int] = {}
    attempted_ids = attempted_ids or set()
    placements: dict[str, dict[str, Any]] = {}

    for q in thematic:
        topic = topics_by_question.get(str(q.get("id")))
        if topic is None:
            name = UNTAGGED_THEME
            spot = {
                "paper_id": None,
                "paper_label": syllabus.UNPLACED_PAPER_LABEL,
                "paper_sort": 10**6,
                "paper_number": None,
                "section": syllabus.UNPLACED_SECTION,
                "section_part": None,
                "section_line": None,
                "section_sort": 10**6,
                "theme_sort": 10**6,
                "placed": False,
            }
        else:
            name = str(topic.get("name") or "").strip() or UNTAGGED_THEME
            spot = syllabus.place(topic)
        placements.setdefault(name, spot)
        spot = placements[name]
        key = (spot["paper_id"] or syllabus.UNPLACED_PAPER, spot["section"], name)
        counts[key] = counts.get(key, 0) + 1
        if str(q.get("id")) in attempted_ids:
            done_counts[key] = done_counts.get(key, 0) + 1

    papers: dict[str, dict[str, Any]] = {}
    for (paper_key, section, name), count in counts.items():
        spot = placements[name]
        paper = papers.setdefault(
            paper_key,
            {
                "paper_id": spot["paper_id"],
                "paper_label": spot["paper_label"],
                "paper_number": spot["paper_number"],
                "question_count": 0,
                "attempted_count": 0,
                "_sort": spot["paper_sort"],
                "_sections": {},
            },
        )
        done = done_counts.get((paper_key, section, name), 0)
        paper["question_count"] += count
        paper["attempted_count"] += done
        sec = paper["_sections"].setdefault(
            section,
            {
                "section": section,
                "part": spot["section_part"],
                # The official syllabus line, shown under the section heading.
                "line": spot.get("section_line"),
                "question_count": 0,
                "attempted_count": 0,
                "_sort": spot["section_sort"],
                "themes": [],
            },
        )
        sec["question_count"] += count
        sec["attempted_count"] += done
        sec["themes"].append(
            {
                "theme": name,
                "question_count": count,
                "attempted_count": done,
                "_sort": spot["theme_sort"],
            }
        )

    out: list[dict[str, Any]] = []
    for paper in sorted(papers.values(), key=lambda p: (p["_sort"], p["paper_label"])):
        sections = []
        for sec in sorted(paper["_sections"].values(), key=lambda s: (s["_sort"], s["section"])):
            sec["themes"].sort(key=lambda t: (t["_sort"], t["theme"]))
            for theme in sec["themes"]:
                theme.pop("_sort", None)
            sec.pop("_sort", None)
            sections.append(sec)
        paper.pop("_sort", None)
        paper.pop("_sections", None)
        paper["sections"] = sections
        out.append(paper)

    tabs = [
        {
            "paper_id": p["paper_id"],
            "paper_label": p["paper_label"],
            "paper_number": p["paper_number"],
            "question_count": p["question_count"],
            "attempted_count": p["attempted_count"],
        }
        for p in out
    ]
    return out, tabs


def _attempted_question_ids(
    supabase: Any, user_id: Any, question_ids: list[str]
) -> set[str]:
    """Which of these questions this user has SUBMITTED an answer to.

    Submitted, not every attempt — the same rule coverage uses, so the two
    surfaces cannot disagree about what "done" means. No user, no attempts.
    """
    if not user_id or not question_ids:
        return set()
    done: set[str] = set()
    for chunk in _chunks(sorted(set(question_ids))):
        rows = _safe(
            lambda ids=chunk: _paginate_all(
                lambda a, b, ids=ids: (
                    supabase.table("descriptive_attempts")
                    .select("id, pyq_question_id")
                    .eq("user_id", user_id)
                    .eq("status", "submitted")
                    .in_("pyq_question_id", ids)
                    .order("id")
                    .range(a, b)
                    .execute()
                    .data
                )
            ),
            default=[],
        ) or []
        for r in rows:
            qid = str(r.get("pyq_question_id") or "")
            if qid:
                done.add(qid)
    return done


def _paper_slot_counts(
    subject: Any,
    real_half: list[dict[str, Any]],
    thematic_half: list[dict[str, Any]],
    paper_of: Any,
    attempted_ids: set[str],
) -> list[dict[str, Any]]:
    """The canonical tabs for this subject, each with its counts.

    Counts span BOTH halves, because a tab is a paper and a paper's questions
    are wherever they are: a Paper II tab reading 0 while Paper II themes exist
    would be a tab contradicting the tree beneath it.
    """
    slots = paper_slots_for(subject)
    if not slots:
        return []
    real_by_slot: dict[int, list[dict[str, Any]]] = {}
    for q in real_half:
        real_by_slot.setdefault(paper_slot(paper_of(q))[0], []).append(q)
    # The thematic half has no sitting, so its paper comes off the theme's
    # syllabus placement, which `_syllabus_themes` already resolved.
    thematic_by_slot: dict[int, int] = {}
    for q in thematic_half:
        number = _as_int(_meta(q).get("optional_paper_number")) or _as_int(
            _meta(paper_of(q)).get("optional_paper_number")
        )
        if number:
            thematic_by_slot[number] = thematic_by_slot.get(number, 0) + 1

    out = []
    for slot in slots:
        number = slot["paper_number"]
        rows = real_by_slot.get(number, [])
        out.append({
            **slot,
            "question_count": len(rows) + thematic_by_slot.get(number, 0),
            "attempted_count": sum(
                1 for q in rows if str(q.get("id")) in attempted_ids
            ),
        })
    return out


def get_catalog(
    supabase: Any,
    exam_id: str,
    *,
    user_id: Any = None,
    subject: str | None = None,
    paper_number: Any = None,
) -> dict[str, Any]:
    """Subjects, papers, themes and years, each with a question count.

    Papers are the real-paper half: non-retired, non-thematic, holding at least
    one verified descriptive question — at ANY paper trust_status. Themes are
    the thematic half, grouped by verified primary topic tag.

    ``subject`` narrows papers, themes and years to one subject. It does not
    narrow ``subjects`` itself, which always lists every subject with a count,
    because that list is how the aspirant changes their mind.

    ``paper_number`` narrows to one paper within the subject — Paper I, or GS3 —
    and narrows BOTH halves: the themes of that paper's syllabus AND the
    sittings of that paper. A Paper I tab that left Paper II sittings on screen
    would be a filter that only half applies.

    Map questions are excluded from every count here, the same way
    ``list_questions`` excludes them from the list: a count that includes
    questions the surface refuses to open is a promise it cannot keep.
    """
    if not exam_id:
        raise DescriptiveError("exam_required", "Pick an exam first.", 400)

    papers = _papers_for_exam(supabase, exam_id)
    if papers is None:
        raise DescriptiveError(
            "catalog_read_failed", "Question papers are unavailable right now.", 503
        )
    live = [p for p in papers if not is_retired(p)]
    if not live:
        return _empty_catalog(exam_id, subject)

    by_id = {str(p["id"]): p for p in live if p.get("id")}
    questions = _verified_questions_for_papers(supabase, list(by_id))
    if questions is None:
        raise DescriptiveError(
            "catalog_read_failed", "Question papers are unavailable right now.", 503
        )
    questions = [q for q in questions if not requires_map_sheet(q)]
    if not questions:
        return _empty_catalog(exam_id, subject)

    def paper_of(q: dict[str, Any]) -> dict[str, Any]:
        return by_id.get(str(q.get("pyq_paper_id") or "")) or {}

    # Subjects span BOTH halves and every trust status: an aspirant picks their
    # optional first, and the subject is on the question, not the paper.
    subjects: dict[str, int] = {}
    for q in questions:
        name = subject_of(q, paper_of(q))
        if name:
            subjects[name] = subjects.get(name, 0) + 1

    wanted = str(subject).strip() if subject else None
    if wanted:
        scoped = [q for q in questions if subject_of(q, paper_of(q)) == wanted]
    else:
        scoped = questions

    real_half = [q for q in scoped if not question_is_thematic(q, paper_of(q))]
    thematic_half = [q for q in scoped if question_is_thematic(q, paper_of(q))]

    wanted_paper = _as_int(paper_number)
    if wanted_paper is not None:
        # A sitting's number comes off the paper row (`optional_paper_number`
        # for a split optional, `gs_paper` for GS) — the same integer the
        # syllabus index gives a theme's paper.
        real_half = [
            q for q in real_half if paper_slot(paper_of(q))[0] == wanted_paper
        ]

    paper_counts: dict[str, int] = {}
    for q in real_half:
        pid = str(q.get("pyq_paper_id") or "")
        # A PAPER IS ONLY EVER LISTED UNDER A SUBJECT ITS QUESTIONS CLAIM.
        #
        # An unsplit GS bucket (paper_code NULL, paper_kind NULL, not thematic)
        # carries questions with no `optional_subject` and sits on no GS paper
        # kind, so `subject_of` returns None for every one of them. With a
        # subject selected the scope already excluded it; with NO subject
        # selected it used to be counted anyway, and 80 GS questions surfaced
        # as a 2023 paper under an optional subject. An unplaceable question
        # cannot name the paper it belongs to, so it names none.
        if pid and subject_of(q, paper_of(q)):
            paper_counts[pid] = paper_counts.get(pid, 0) + 1

    paper_items = []
    for pid, count in paper_counts.items():
        paper = by_id.get(pid) or {}
        meta = _meta(paper)
        slot_key, slot_label = paper_slot(paper)
        # The subject its questions claim — carried so a `paper_id` arriving in
        # a URL can resolve the subject it implies, and so a label rendered
        # outside subject context can say which subject it is.
        paper_subject = next(
            (subject_of(q, paper) for q in real_half
             if str(q.get("pyq_paper_id") or "") == pid and subject_of(q, paper)),
            None,
        )
        paper_items.append(
            {
                "id": pid,
                "label": _paper_label(paper),
                # THE LABEL FOR ANYWHERE THERE IS NO SUBJECT ON SCREEN —
                # "PSIR · 2025 · P1". `label` alone is "2025 · P1", which names
                # six different papers across six subjects, so any surface
                # rendering a paper outside its subject uses this one. Composed
                # here so the two never disagree.
                "label_with_subject": " · ".join(
                    b for b in (subject_short(paper_subject), _paper_label(paper)) if b
                ),
                "subject": paper_subject,
                "subject_short": subject_short(paper_subject),
                "year": _as_int(paper.get("year")),
                "paper_kind": meta.get("paper_kind"),
                "paper_slot": slot_label,
                "optional_paper_number": _as_int(meta.get("optional_paper_number")),
                "gs_paper": meta.get("gs_paper"),
                "question_count": count,
                "_slot_key": slot_key,
            }
        )
    # Year descending, paper number ascending: the most recent sitting first,
    # and within it Paper I before Paper II.
    paper_items.sort(key=lambda p: (-(p["year"] or 0), p["_slot_key"], str(p["label"])))
    for item in paper_items:
        item.pop("_slot_key", None)

    attempted_ids = _attempted_question_ids(
        supabase, user_id, [str(q["id"]) for q in scoped if q.get("id")]
    )

    topics_by_question = _primary_topics(
        supabase, [str(q["id"]) for q in thematic_half if q.get("id")]
    )
    theme_items, theme_papers = _syllabus_themes(
        thematic_half, topics_by_question, attempted_ids
    )
    if wanted_paper is not None:
        # The tabs keep every paper — they are how the aspirant switches — but
        # the tree shows only the selected one.
        theme_items = [p for p in theme_items if p["paper_number"] == wanted_paper]

    # THE BY-YEAR LENS. One row per year for the selected paper tab, carrying
    # the paper ids that row opens and how many of its questions are done — a
    # year the aspirant has finished should say so before they open it.
    year_counts: dict[int, int] = {}
    year_papers: dict[int, set[str]] = {}
    year_questions: dict[int, list[str]] = {}
    for q in real_half:
        if not subject_of(q, paper_of(q)):
            continue
        y = _as_int(paper_of(q).get("year"))
        if y:
            year_counts[y] = year_counts.get(y, 0) + 1
            pid = str(q.get("pyq_paper_id") or "")
            if pid:
                year_papers.setdefault(y, set()).add(pid)
            year_questions.setdefault(y, []).append(str(q.get("id")))

    return {
        "exam_id": exam_id,
        "subject": wanted,
        "paper_number": wanted_paper,
        "subjects": [
            {"subject": name, "question_count": count}
            for name, count in sorted(subjects.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "papers": paper_items,
        "themes": theme_items,
        # The Paper I / Paper II (or GS1..GS4) tabs. Derived from the themes
        # actually present, not from a fixed list, so a subject with only one
        # paper's worth of thematic questions gets one tab.
        "theme_papers": theme_papers,
        "years": [
            {
                "year": y,
                "question_count": c,
                "attempted_count": sum(
                    1 for qid in year_questions.get(y, []) if qid in attempted_ids
                ),
                "paper_ids": sorted(year_papers.get(y, ())),
            }
            for y, c in sorted(year_counts.items(), reverse=True)
        ],
        # The canonical tabs for this subject — Paper I / Paper II, or
        # GS1..GS4 / Essay — each with what it actually holds. A slot with
        # nothing in it is still a tab: a missing tab reads as "this paper does
        # not exist", an empty one reads as "not loaded yet", and only the
        # second is true.
        "paper_slots": _paper_slot_counts(
            wanted, real_half, thematic_half, paper_of, attempted_ids
        ),
        "subject_short": subject_short(wanted),
        "total_questions": len(scoped),
    }


def _empty_catalog(exam_id: str, subject: str | None = None) -> dict[str, Any]:
    return {
        "exam_id": exam_id,
        "subject": (str(subject).strip() if subject else None) or None,
        "paper_number": None,
        "subjects": [],
        "papers": [],
        "themes": [],
        "theme_papers": [],
        "years": [],
        "paper_slots": list(paper_slots_for(subject)),
        "subject_short": subject_short(subject),
        "total_questions": 0,
    }


def _paper_label(paper: dict[str, Any]) -> str:
    """"2025 · P1", "2025 · GS3", "2025 · Essay".

    Year and slot only. The subject is not repeated in the label because the
    papers list is already scoped to one subject, and "Political Science and
    International Relations · optional · Paper 1 · 2019" was a chip too wide to
    read at a glance.
    """
    year = _as_int(paper.get("year"))
    _, slot = paper_slot(paper)
    bits = [str(year) if year else "", slot or ""]
    label = " · ".join(b for b in bits if b)
    return label or (paper.get("paper_code") or str(paper.get("id") or "Paper"))


def list_questions(
    supabase: Any,
    user_id: str,
    *,
    exam_id: str,
    subject: str | None = None,
    paper_id: str | None = None,
    paper_number: Any = None,
    theme: str | None = None,
    year: Any = None,
    year_from: Any = None,
    year_to: Any = None,
    exclude_attempted: bool = False,
    has_marks: bool = False,
    limit: Any = _DEFAULT_QUESTION_LIMIT,
) -> dict[str, Any]:
    """Verified descriptive questions matching the filters.

    Map questions are excluded and counted separately — the surface tells the
    aspirant how many it could not show rather than quietly serving fewer.
    """
    if not exam_id:
        raise DescriptiveError("exam_required", "Pick an exam first.", 400)
    cap = _as_int(limit) or _DEFAULT_QUESTION_LIMIT
    cap = max(1, min(cap, _MAX_QUESTION_LIMIT))

    papers = _papers_for_exam(supabase, exam_id)
    if papers is None:
        raise DescriptiveError(
            "questions_read_failed", "Questions are unavailable right now.", 503
        )
    live = {str(p["id"]): p for p in papers if p.get("id") and not is_retired(p)}
    if paper_id:
        live = {k: v for k, v in live.items() if k == str(paper_id)}
        if not live:
            raise DescriptiveError("paper_not_found", "That paper isn't available.", 404)
    if not live:
        return _empty_questions()

    questions = _verified_questions_for_papers(supabase, list(live))
    if questions is None:
        raise DescriptiveError(
            "questions_read_failed", "Questions are unavailable right now.", 503
        )

    # A theme filter selects the thematic half; a paper or year filter selects
    # the real-paper half. Asking for neither returns both.
    def paper_of(q: dict[str, Any]) -> dict[str, Any]:
        return live.get(str(q.get("pyq_paper_id") or "")) or {}

    if theme:
        questions = [q for q in questions if question_is_thematic(q, paper_of(q))]
        names = _primary_topic_names(supabase, [str(q["id"]) for q in questions if q.get("id")])
        questions = [
            q
            for q in questions
            if names.get(str(q.get("id")), UNTAGGED_THEME) == str(theme)
        ]
    elif paper_id or year is not None:
        questions = [q for q in questions if not question_is_thematic(q, paper_of(q))]

    if subject:
        # `subject_of`, not the raw metadata key: a GS paper carries no
        # `optional_subject`, and matching on the key alone would make
        # "General Studies" select nothing.
        wanted_subject = str(subject).strip()
        questions = [q for q in questions if subject_of(q, paper_of(q)) == wanted_subject]

    wanted_paper = _as_int(paper_number)
    if wanted_paper is not None and not theme:
        # Only the sittings half has a paper number; a theme filter has already
        # picked its paper through the theme itself.
        questions = [q for q in questions if paper_slot(paper_of(q))[0] == wanted_paper]
    wanted_year = _as_int(year)
    if wanted_year is not None:
        questions = [
            q
            for q in questions
            if _as_int((live.get(str(q.get("pyq_paper_id")), {}) or {}).get("year"))
            == wanted_year
        ]

    # A YEAR RANGE, for the by-year lens. Inclusive at both ends, and each end
    # is independent: "since 2019" is a range with no upper bound, not a
    # request for one year.
    low, high = _as_int(year_from), _as_int(year_to)
    if low is not None or high is not None:
        def in_range(q: dict[str, Any]) -> bool:
            y = _as_int((live.get(str(q.get("pyq_paper_id")), {}) or {}).get("year"))
            if y is None:
                # The thematic half has no sitting and therefore no year. A
                # year range is a question about sittings, so a row without one
                # is outside every range rather than inside all of them.
                return False
            return (low is None or y >= low) and (high is None or y <= high)
        questions = [q for q in questions if in_range(q)]

    if has_marks:
        # ~87% of the corpus carries no marks. This is the filter that finds
        # the questions a timed attempt can actually be timed against.
        questions = [q for q in questions if _as_int(_meta(q).get("marks"))]

    map_questions = [q for q in questions if requires_map_sheet(q)]
    questions = [q for q in questions if not requires_map_sheet(q)]

    attempts = _attempt_counts(supabase, user_id, [str(q["id"]) for q in questions if q.get("id")])
    if exclude_attempted:
        questions = [q for q in questions if attempts.get(str(q.get("id")), 0) == 0]

    # Question-number order within a paper is the order the aspirant sat them.
    # The thematic half has no paper order at all, so it falls back to the text.
    questions.sort(
        key=lambda q: (
            str((live.get(str(q.get("pyq_paper_id")), {}) or {}).get("id") or ""),
            _as_int(q.get("question_number")) if _as_int(q.get("question_number")) is not None else 10**6,
            str(q.get("question_text") or ""),
        )
    )
    page = questions[:cap]

    parents, labels = _paper_context(supabase, page)
    # The theme a question sits under, for the breadcrumb's last level. Only
    # the thematic half has one, and only when it carries a verified primary
    # tag — the same rule the catalogue groups by.
    page_topics = _primary_topics(supabase, [str(q["id"]) for q in page if q.get("id")])
    items = [
        question_payload(
            q,
            paper=live.get(str(q.get("pyq_paper_id"))),
            parent_text=parents.get(str(q.get("id"))),
            attempt_count=attempts.get(str(q.get("id")), 0),
            label=labels.get(str(q.get("id"))),
            topic=(page_topics.get(str(q.get("id"))) or {}).get("name"),
        )
        for q in page
    ]
    return {
        "items": items,
        "count": len(items),
        "total_matching": len(questions),
        # Named `excluded_map_questions`, not folded into the count: the number
        # is the point. "3 map questions aren't shown here" is information.
        "excluded_map_questions": len(map_questions),
    }


def _empty_questions() -> dict[str, Any]:
    return {"items": [], "count": 0, "total_matching": 0, "excluded_map_questions": 0}


def _paper_context(
    supabase: Any, page: list[dict[str, Any]]
) -> tuple[dict[str, str], dict[str, str]]:
    """(parent stem text, positional label) for every question on this page.

    ONE READ FOR BOTH, because both need the same thing: every question on the
    papers this page touches. A label is a question's rank within its paper, so
    it cannot be computed from the page alone — the page is a filtered slice
    and ranks would shift with the filter.

    `parent_question_number` is a number within the same paper, not an id, so
    the stem lookup is (paper, number) → text.
    """
    paper_ids = sorted({str(q.get("pyq_paper_id") or "") for q in page if q.get("pyq_paper_id")})
    if not paper_ids:
        return {}, {}

    rows: list[dict[str, Any]] = []
    for chunk in _chunks(paper_ids):
        got = _safe(
            lambda ids=chunk: _paginate_all(
                lambda a, b, ids=ids: (
                    supabase.table("pyq_questions")
                    .select("id, pyq_paper_id, question_number, question_text, metadata")
                    .in_("pyq_paper_id", ids)
                    .order("id")
                    .range(a, b)
                    .execute()
                    .data
                )
            ),
            default=[],
        ) or []
        rows.extend(got)

    by_paper: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_paper.setdefault(str(r.get("pyq_paper_id") or ""), []).append(r)

    labels: dict[str, str] = {}
    for paper_rows in by_paper.values():
        labels.update(paper_question_labels(paper_rows))

    by_key = {
        (str(r.get("pyq_paper_id")), _as_int(r.get("question_number"))): r.get("question_text")
        for r in rows
    }
    parents: dict[str, str] = {}
    for q in page:
        parent = _as_int(_meta(q).get("parent_question_number"))
        pid = str(q.get("pyq_paper_id") or "")
        if parent is None or not pid:
            continue
        text = by_key.get((pid, parent))
        if text:
            parents[str(q.get("id"))] = text
    return parents, labels


def _attempt_counts(
    supabase: Any, user_id: str, question_ids: list[str]
) -> dict[str, int]:
    """How many times THIS user has attempted each question. Never another's."""
    if not question_ids or not user_id:
        return {}
    counts: dict[str, int] = {}
    for chunk in _chunks(question_ids):
        rows = _safe(
            lambda ids=chunk: _paginate_all(
                lambda a, b, ids=ids: (
                    supabase.table("descriptive_attempts")
                    .select("pyq_question_id, id")
                    .eq("user_id", user_id)
                    .in_("pyq_question_id", ids)
                    .order("id")
                    .range(a, b)
                    .execute()
                    .data
                )
            ),
            default=[],
        ) or []
        for r in rows:
            qid = str(r.get("pyq_question_id") or "")
            if qid:
                counts[qid] = counts.get(qid, 0) + 1
    return counts


# ── analytics (P5) ───────────────────────────────────────────────────────
#
# Everything here is computed from `descriptive_attempts` rows that already
# exist. No new tracking, no new column, no event stream: what an aspirant
# wrote, when, for how long, and how they judged it is the whole input.

#: A topic needs this many submitted attempts before it is called strong or
#: weak. Two answers is a mood; three is the smallest number from which a
#: direction can be read at all, and saying "your weakest topic" off one
#: attempt would be an accusation rather than a finding.
MIN_ATTEMPTS_PER_TOPIC = 3

#: How many weeks the trend covers. Long enough to see a direction, short
#: enough that a month off does not bury this month.
ANALYTICS_WEEKS = 8


def _week_start(stamp: Any) -> str | None:
    """The Monday of the ISO week this timestamp falls in, as YYYY-MM-DD."""
    text = str(stamp or "")[:10]
    if len(text) != 10:
        return None
    try:
        day = _date.fromisoformat(text)
    except ValueError:
        return None
    return (day - _timedelta(days=day.weekday())).isoformat()


def _mean(values: list[float]) -> float | None:
    """The average, or None over nothing. Never 0 for an empty list."""
    return round(sum(values) / len(values), 1) if values else None


def _rubric_means(attempts: list[dict[str, Any]]) -> dict[str, float | None]:
    """Mean score per rubric criterion, over the attempts that scored it."""
    buckets: dict[str, list[float]] = {k: [] for k in RUBRIC_KEYS}
    for a in attempts:
        scores = a.get("self_scores")
        if not isinstance(scores, dict):
            continue
        for key in RUBRIC_KEYS:
            value = _as_int(scores.get(key))
            if value is not None:
                buckets[key].append(value)
    return {k: _mean(v) for k, v in buckets.items()}


def _streak_weeks(weeks: list[dict[str, Any]], today: Any = None) -> int:
    """Consecutive weeks with at least one submitted answer, ending now.

    Counted BACKWARDS from the current week, and the current week does not
    break it while it is still running: it is Tuesday for everyone at some
    point, and a streak that resets every Monday morning measures the calendar
    rather than the habit.
    """
    written = {w["week"] for w in weeks if w["submitted"] > 0}
    if not written:
        return 0
    now = _date.fromisoformat(str(today)[:10]) if today else _date.today()
    cursor = now - _timedelta(days=now.weekday())
    # This week not being written yet is not a broken streak.
    if cursor.isoformat() not in written:
        cursor -= _timedelta(days=7)
    count = 0
    while cursor.isoformat() in written:
        count += 1
        cursor -= _timedelta(days=7)
    return count


def analytics(
    supabase: Any, user_id: str, *, weeks: Any = ANALYTICS_WEEKS, today: Any = None
) -> dict[str, Any]:
    """How the aspirant's answer writing is going, week by week.

    EVERY NUMBER IS OVER THE ATTEMPTS THAT CARRY IT. A question with no marks
    has no time target, a question with no word limit has no over/under, and
    ~87% of the corpus carries no marks — so an average "vs target" computed
    over everything would be an average over a target that mostly does not
    exist. Each comparison therefore states its own sample size, and is absent
    when the sample is empty.
    """
    if not user_id:
        raise DescriptiveError("user_required", "Sign in to see your progress.", 401)
    span = max(1, min(_as_int(weeks) or ANALYTICS_WEEKS, 52))

    rows = [
        r for r in _owned_attempts(supabase, user_id)
        if (r.get("status") or "draft") == "submitted"
    ]
    if not rows:
        return _empty_analytics(span)

    questions, _papers = _attempt_questions(
        supabase, [str(r.get("pyq_question_id")) for r in rows if r.get("pyq_question_id")]
    )
    topics = _primary_topic_names(supabase, list(questions))

    by_week: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        week = _week_start(row.get("submitted_at") or row.get("started_at"))
        if week:
            by_week.setdefault(week, []).append(row)

    recent = sorted(by_week)[-span:]
    weekly = []
    for week in recent:
        attempts = by_week[week]
        # Words only where the question states a limit: "260 words" against no
        # limit is a number with nothing to compare it to.
        word_pairs = []
        time_pairs = []
        for a in attempts:
            question = questions.get(str(a.get("pyq_question_id") or "")) or {}
            meta = _meta(question)
            limit = _as_int(meta.get("word_limit"))
            words = _as_int(a.get("word_count"))
            if limit and words is not None:
                word_pairs.append((words, limit))
            target = timer_target_for(meta.get("marks"))
            spent = _as_int(a.get("time_spent_seconds"))
            if target and spent:
                time_pairs.append((spent, target))
        weekly.append({
            "week": week,
            "submitted": len(attempts),
            "avg_self_total": _mean(
                [s for s in (_as_int(a.get("self_total")) for a in attempts) if s is not None]
            ),
            "avg_words": _mean([float(w) for w, _ in word_pairs]),
            "avg_word_limit": _mean([float(l) for _, l in word_pairs]),
            "words_sample": len(word_pairs),
            "avg_seconds": _mean([float(t) for t, _ in time_pairs]),
            "avg_target_seconds": _mean([float(t) for _, t in time_pairs]),
            "time_sample": len(time_pairs),
            "rubric": _rubric_means(attempts),
        })

    overall_rubric = _rubric_means(rows)
    scored = {k: v for k, v in overall_rubric.items() if v is not None}
    # The weakest dimension is the lowest mean, and ties are reported as ties
    # rather than resolved by dictionary order.
    weakest = None
    if scored:
        low = min(scored.values())
        weakest = sorted(k for k, v in scored.items() if v == low)

    per_topic: dict[str, list[int]] = {}
    for row in rows:
        name = topics.get(str(row.get("pyq_question_id") or ""))
        total = _as_int(row.get("self_total"))
        if name and total is not None:
            per_topic.setdefault(name, []).append(total)
    ranked = sorted(
        (
            {"topic": name, "attempts": len(scores), "avg_self_total": _mean([float(s) for s in scores])}
            for name, scores in per_topic.items()
            if len(scores) >= MIN_ATTEMPTS_PER_TOPIC
        ),
        key=lambda t: (-(t["avg_self_total"] or 0), t["topic"]),
    )

    return {
        "weeks": weekly,
        "window_weeks": span,
        "submitted_total": len(rows),
        "streak_weeks": _streak_weeks(weekly, today=today),
        "rubric": overall_rubric,
        "weakest_dimensions": weakest,
        "strongest_topics": ranked[:5],
        "weakest_topics": list(reversed(ranked[-5:])) if ranked else [],
        # Stated so the surface can say WHY a topic list is short, instead of
        # looking like the aspirant has written in only two topics.
        "min_attempts_per_topic": MIN_ATTEMPTS_PER_TOPIC,
        "topics_below_threshold": sum(
            1 for scores in per_topic.values() if len(scores) < MIN_ATTEMPTS_PER_TOPIC
        ),
    }


def _empty_analytics(span: int) -> dict[str, Any]:
    return {
        "weeks": [],
        "window_weeks": span,
        "submitted_total": 0,
        "streak_weeks": 0,
        "rubric": {k: None for k in RUBRIC_KEYS},
        "weakest_dimensions": None,
        "strongest_topics": [],
        "weakest_topics": [],
        "min_attempts_per_topic": MIN_ATTEMPTS_PER_TOPIC,
        "topics_below_threshold": 0,
    }


# ── coverage (P4) ────────────────────────────────────────────────────────


def _submitted_question_stats(
    supabase: Any, user_id: str, question_ids: list[str]
) -> dict[str, dict[str, Any]]:
    """question_id → {attempts, scores} over this user's SUBMITTED attempts.

    SUBMITTED, not every attempt. An open draft is a question the aspirant is
    in the middle of, not one they have covered, and counting it would let the
    coverage number go up by opening questions and closing the tab.
    """
    if not question_ids or not user_id:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for chunk in _chunks(sorted(set(question_ids))):
        rows = _safe(
            lambda ids=chunk: _paginate_all(
                lambda a, b, ids=ids: (
                    supabase.table("descriptive_attempts")
                    .select("id, pyq_question_id, self_total, status")
                    .eq("user_id", user_id)
                    .eq("status", "submitted")
                    .in_("pyq_question_id", ids)
                    .order("id")
                    .range(a, b)
                    .execute()
                    .data
                )
            ),
            default=[],
        ) or []
        for r in rows:
            qid = str(r.get("pyq_question_id") or "")
            if not qid:
                continue
            entry = out.setdefault(qid, {"attempts": 0, "scores": []})
            entry["attempts"] += 1
            score = _as_int(r.get("self_total"))
            if score is not None:
                entry["scores"].append(score)
    return out


def _coverage_bucket(label: str, *, sort: Any = 0) -> dict[str, Any]:
    return {
        "label": label,
        "available": 0,
        "attempted": 0,
        "_scores": [],
        "_sort": sort,
        "unattempted": [],
    }


def _seal_bucket(bucket: dict[str, Any], *, unattempted_cap: int) -> dict[str, Any]:
    scores = bucket.pop("_scores")
    bucket.pop("_sort", None)
    unattempted = bucket["unattempted"]
    return {
        **bucket,
        # An average over nothing is not 0, it is absent. A 0 here would read
        # as "everything they wrote scored zero".
        "avg_self_score": round(sum(scores) / len(scores), 1) if scores else None,
        "scored_attempts": len(scores),
        # The list is capped and the REMAINDER is stated, because "and 340
        # more" is information and a silently shortened list is not.
        "unattempted": unattempted[:unattempted_cap],
        "unattempted_total": len(unattempted),
    }


#: How many not-yet-attempted questions a group names before it starts
#: counting instead. A list longer than this is a corpus, not a to-do list.
_UNATTEMPTED_SHOWN = 20


def coverage(
    supabase: Any,
    user_id: str,
    *,
    exam_id: str,
    subject: str | None = None,
) -> dict[str, Any]:
    """What this aspirant has written, and what is still waiting, by group.

    THREE GROUPINGS, IN ORDER OF HOW MUCH THEY KNOW:

    1. the syllabus tree, when the question's verified primary tag places it
       (`study_os/syllabus.py`, from the compiled index);
    2. the topic tag's own name, when the tag exists but the syllabus cannot
       place it;
    3. the paper and year, when there is no verified primary tag at all.

    Nothing is dropped between them. A question the first two cannot reach
    still appears under its paper, because an aspirant deciding what to write
    next needs the whole corpus, not the well-tagged part of it.
    """
    if not exam_id:
        raise DescriptiveError("exam_required", "Pick an exam first.", 400)

    papers = _papers_for_exam(supabase, exam_id)
    if papers is None:
        raise DescriptiveError("coverage_read_failed", "Coverage is unavailable right now.", 503)
    live = {str(p["id"]): p for p in papers if p.get("id") and not is_retired(p)}
    if not live:
        return {"exam_id": exam_id, "subjects": [], "totals": _coverage_totals([])}

    questions = _verified_questions_for_papers(supabase, list(live))
    if questions is None:
        raise DescriptiveError("coverage_read_failed", "Coverage is unavailable right now.", 503)
    # Map questions cannot be practised here, so counting them as "available"
    # would make a subject permanently incompletable.
    questions = [q for q in questions if not requires_map_sheet(q)]
    if subject:
        questions = [
            q for q in questions
            if subject_of(q, live.get(str(q.get("pyq_paper_id")))) == str(subject).strip()
        ]

    topics = _primary_topics(supabase, [str(q["id"]) for q in questions if q.get("id")])
    _attach_tree_position(supabase, topics)
    stats = _submitted_question_stats(
        supabase, user_id, [str(q["id"]) for q in questions if q.get("id")]
    )
    _, labels = _paper_context(supabase, questions)

    tree: dict[str, dict[str, Any]] = {}
    for question in questions:
        qid = str(question.get("id") or "")
        paper = live.get(str(question.get("pyq_paper_id") or ""))
        subject_name = subject_of(question, paper) or "Unfiled"
        topic = topics.get(qid)

        spot = syllabus.place(topic) if topic else None
        if spot and spot.get("placed"):
            group_key = f"{spot['paper_label']} · {spot['section']}"
            group_sort = (spot["paper_sort"], spot["section_sort"])
            source = "syllabus"
        elif topic and (topic.get("name") or "").strip():
            group_key = str(topic["name"]).strip()
            group_sort = (10**5, 0)
            source = "topic"
        else:
            # No verified primary tag. The paper is still a true statement
            # about where the question came from.
            group_key = _paper_label(paper or {})
            group_sort = (10**6, -(_as_int((paper or {}).get("year")) or 0))
            source = "paper"

        subject_bucket = tree.setdefault(subject_name, {
            "subject": subject_name, "groups": {}, "available": 0,
            "attempted": 0, "_scores": [],
        })
        group = subject_bucket["groups"].setdefault(
            group_key, {**_coverage_bucket(group_key, sort=group_sort), "source": source}
        )

        done = stats.get(qid)
        for bucket in (subject_bucket, group):
            bucket["available"] += 1
            if done:
                bucket["attempted"] += 1
                bucket["_scores"].extend(done["scores"])
        if not done:
            group["unattempted"].append({
                "id": qid,
                "label": labels.get(qid),
                "excerpt": _excerpt(question.get("question_text"), 120),
                "paper_id": question.get("pyq_paper_id"),
                "marks": _as_int(_meta(question).get("marks")),
            })

    subjects = []
    for bucket in tree.values():
        groups = sorted(bucket.pop("groups").values(), key=lambda g: (g["_sort"], g["label"]))
        scores = bucket.pop("_scores")
        subjects.append({
            **bucket,
            "avg_self_score": round(sum(scores) / len(scores), 1) if scores else None,
            "scored_attempts": len(scores),
            "groups": [_seal_bucket(g, unattempted_cap=_UNATTEMPTED_SHOWN) for g in groups],
        })
    subjects.sort(key=lambda s: s["subject"])
    return {"exam_id": exam_id, "subjects": subjects, "totals": _coverage_totals(subjects)}


def _coverage_totals(subjects: list[dict[str, Any]]) -> dict[str, Any]:
    available = sum(s["available"] for s in subjects)
    attempted = sum(s["attempted"] for s in subjects)
    scored = sum(s["scored_attempts"] for s in subjects)
    weighted = sum(
        (s["avg_self_score"] or 0) * s["scored_attempts"]
        for s in subjects if s["avg_self_score"] is not None
    )
    return {
        "available": available,
        "attempted": attempted,
        # Stated as a fraction, never as a bare percentage: "18 of 1,351" is
        # honest about the size of what is left in a way that "1%" is not.
        "unattempted": available - attempted,
        "avg_self_score": round(weighted / scored, 1) if scored else None,
        "subjects": len(subjects),
    }


# ── attempts ─────────────────────────────────────────────────────────────


def attempt_payload(row: dict[str, Any]) -> dict[str, Any]:
    """One attempt as the client sees it. ``user_id`` never leaves the server."""
    return {
        "id": row.get("id"),
        "pyq_question_id": row.get("pyq_question_id"),
        "status": row.get("status") or "draft",
        "answer_text": row.get("answer_text") or "",
        # None, not 0, for a handwritten attempt: nothing has read the pages,
        # and 0 would read as "they wrote nothing".
        "word_count": (
            None if _answer_mode(row) == "handwritten"
            else (_as_int(row.get("word_count")) or 0)
        ),
        "time_spent_seconds": _as_int(row.get("time_spent_seconds")) or 0,
        "timer_target_seconds": _as_int(row.get("timer_target_seconds")),
        # Null and 0 are different answers: null is "this attempt predates
        # paste tracking", 0 is "nothing was pasted". Only 0 and above
        # justify the history line.
        "pasted_chars": _as_int(row.get("pasted_chars")),
        "self_scores": row.get("self_scores"),
        "self_total": _as_int(row.get("self_total")),
        "notes": row.get("notes"),
        "started_at": row.get("started_at"),
        "submitted_at": row.get("submitted_at"),
        "updated_at": row.get("updated_at"),
    }


def _load_question(supabase: Any, question_id: str) -> dict[str, Any]:
    rows = (
        _safe(
            lambda: (
                supabase.table("pyq_questions")
                .select(_QUESTION_COLUMNS)
                .eq("id", question_id)
                .eq("question_type", QUESTION_TYPE)
                .eq("reviewer_status", QUESTION_REVIEWER_STATUS)
                .limit(1)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    if not rows:
        raise DescriptiveError(
            "question_not_found", "That question isn't available for practice.", 404
        )
    return rows[0]


def _load_owned_attempt(supabase: Any, user_id: str, attempt_id: str) -> dict[str, Any]:
    """One attempt belonging to THIS user, or 404.

    Scoped by `user_id` here, not only by RLS: every query in this module runs on
    the service-role client, which bypasses RLS entirely. Another aspirant's id
    matches no row and 404s — existence never leaks.
    """
    rows = (
        _safe(
            lambda: (
                supabase.table("descriptive_attempts")
                .select(_ATTEMPT_COLUMNS)
                .eq("id", attempt_id)
                .eq("user_id", user_id)
                .limit(1)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    if not rows:
        raise DescriptiveError("attempt_not_found", "Attempt not found.", 404)
    return rows[0]


def open_attempt(supabase: Any, user_id: str, question_id: str) -> dict[str, Any]:
    """The user's open draft for this question, creating one if there is none.

    Idempotent by design and by index: `uq_descriptive_attempts_open_draft`
    permits one draft per (user, question), so a second tab returns the first
    tab's draft rather than forking the answer.
    """
    question = _load_question(supabase, question_id)
    if requires_map_sheet(question):
        raise DescriptiveError(
            "map_question",
            "This question needs a map sheet, so it can't be practised here.",
            422,
        )

    existing = (
        _safe(
            lambda: (
                supabase.table("descriptive_attempts")
                .select(_ATTEMPT_COLUMNS)
                .eq("user_id", user_id)
                .eq("pyq_question_id", question_id)
                .eq("status", "draft")
                .limit(1)
                .execute()
                .data
            ),
            default=[],
        )
        or []
    )
    if existing:
        return attempt_payload(existing[0])

    row = {
        "user_id": user_id,
        "pyq_question_id": question_id,
        "status": "draft",
        "answer_text": "",
        "word_count": 0,
        "time_spent_seconds": 0,
        "pasted_chars": 0,
        "timer_target_seconds": timer_target_for(_meta(question).get("marks")),
        "started_at": _now_iso(),
        "updated_at": _now_iso(),
    }
    created = _safe(
        lambda: supabase.table("descriptive_attempts").insert(row).execute().data,
        default=None,
    )
    if not created:
        raise DescriptiveError("attempt_create_failed", "Couldn't start that attempt.", 503)
    return attempt_payload(created[0])


def monotonic_counter(existing: Any, incoming: Any) -> int | None:
    """``max(existing, incoming)``, or None when there is nothing to write.

    Both counters this guards — elapsed time and pasted characters — only ever
    go up. The client sends a running total, and requests do not arrive in the
    order they were sent: a 10s autosave that overtakes a 20s one would
    otherwise rewind the clock, and reloading a tab with a fresh counter would
    erase the whole first sitting. Taking the max makes a late or restarted
    client harmless.
    """
    value = _as_int(incoming)
    if value is None:
        return None
    return max(0, value, _as_int(existing) or 0)


def save_attempt(
    supabase: Any,
    user_id: str,
    attempt_id: str,
    *,
    answer_text: Any = None,
    time_spent_seconds: Any = None,
    pasted_chars: Any = None,
) -> dict[str, Any]:
    """Autosave. The SERVER computes `word_count` — the client never sends one.

    A submitted attempt is closed: it is the aspirant's record of what they wrote
    under time, and letting a later edit rewrite it would make every stored
    word count and self-score describe text that no longer exists.
    """
    attempt = _load_owned_attempt(supabase, user_id, attempt_id)
    if (attempt.get("status") or "draft") != "draft":
        raise DescriptiveError(
            "attempt_submitted", "This attempt is already submitted.", 409
        )

    patch: dict[str, Any] = {"updated_at": _now_iso()}
    if answer_text is not None:
        text = str(answer_text)
        patch["answer_text"] = text
        # A handwritten attempt keeps its NULL count whatever text is saved
        # beside the pages; nothing has read the answer itself.
        patch["word_count"] = (
            None if _answer_mode(attempt) == "handwritten" else word_count(text)
        )
    seconds = monotonic_counter(attempt.get("time_spent_seconds"), time_spent_seconds)
    if seconds is not None:
        patch["time_spent_seconds"] = seconds
    pasted = monotonic_counter(attempt.get("pasted_chars"), pasted_chars)
    if pasted is not None:
        patch["pasted_chars"] = pasted

    updated = _safe(
        lambda: (
            supabase.table("descriptive_attempts")
            .update(patch)
            .eq("id", attempt_id)
            .eq("user_id", user_id)
            .execute()
            .data
        ),
        default=None,
    )
    if not updated:
        raise DescriptiveError("attempt_save_failed", "Couldn't save that answer.", 503)
    return attempt_payload(updated[0])


def validate_self_scores(raw: Any) -> tuple[dict[str, int], int]:
    """Every rubric key present, each 0..2. Returns the scores and their sum.

    Strict on purpose. A partial rubric would produce a total that looks like a
    score out of 12 while measuring four criteria, and a 3 would mean the
    aspirant was using a scale the descriptors do not define.
    """
    if not isinstance(raw, dict):
        raise DescriptiveError(
            "self_scores_invalid",
            f"Score all six criteria: {', '.join(RUBRIC_KEYS)}.",
            422,
        )
    missing = [k for k in RUBRIC_KEYS if k not in raw]
    if missing:
        raise DescriptiveError(
            "self_scores_incomplete",
            f"Missing a score for: {', '.join(missing)}.",
            422,
        )
    unknown = [k for k in raw if k not in RUBRIC_KEYS]
    if unknown:
        raise DescriptiveError(
            "self_scores_unknown_key",
            f"Not rubric criteria: {', '.join(sorted(unknown))}.",
            422,
        )
    scores: dict[str, int] = {}
    for key in RUBRIC_KEYS:
        value = raw[key]
        if isinstance(value, bool):
            raise DescriptiveError(
                "self_scores_invalid", f"{key} must be 0, 1 or 2.", 422
            )
        number = _as_int(value)
        if number is None or number < 0 or number > RUBRIC_MAX_PER_KEY:
            raise DescriptiveError(
                "self_scores_invalid", f"{key} must be 0, 1 or 2.", 422
            )
        scores[key] = number
    return scores, sum(scores.values())


def submit_attempt(
    supabase: Any,
    user_id: str,
    attempt_id: str,
    *,
    self_scores: Any,
    notes: Any = None,
    time_spent_seconds: Any = None,
    pasted_chars: Any = None,
) -> dict[str, Any]:
    """Close the attempt with the aspirant's own rubric judgement.

    Takes the final counters too. The last autosave can be up to ten seconds
    old, and the submit is the one moment the elapsed time must be right.
    """
    attempt = _load_owned_attempt(supabase, user_id, attempt_id)
    if (attempt.get("status") or "draft") != "draft":
        raise DescriptiveError(
            "attempt_submitted", "This attempt is already submitted.", 409
        )
    scores, total = validate_self_scores(self_scores)

    now = _now_iso()
    patch = {
        "status": "submitted",
        "self_scores": scores,
        "self_total": total,
        "notes": (str(notes) if notes is not None else None),
        "submitted_at": now,
        "updated_at": now,
        # Recomputed from the stored text rather than trusted from the last
        # autosave: the count that goes into the record is the count of what is
        # actually in the column. A handwritten attempt has no text to count —
        # nothing reads the pages — so it keeps its NULL.
        "word_count": (
            None if _answer_mode(attempt) == "handwritten"
            else word_count(attempt.get("answer_text"))
        ),
    }
    seconds = monotonic_counter(attempt.get("time_spent_seconds"), time_spent_seconds)
    if seconds is not None:
        patch["time_spent_seconds"] = seconds
    pasted = monotonic_counter(attempt.get("pasted_chars"), pasted_chars)
    if pasted is not None:
        patch["pasted_chars"] = pasted
    updated = _safe(
        lambda: (
            supabase.table("descriptive_attempts")
            .update(patch)
            .eq("id", attempt_id)
            .eq("user_id", user_id)
            .eq("status", "draft")
            .execute()
            .data
        ),
        default=None,
    )
    if not updated:
        raise DescriptiveError("attempt_submit_failed", "Couldn't submit that answer.", 503)
    return attempt_payload(updated[0])


#: How much of the answer's own question a history row shows. Long enough to
#: recognise the question, short enough that a hundred rows are still a list.
_EXCERPT_CHARS = 180

#: Attempt history page size. The surface pages; it never silently truncates.
_ATTEMPT_PAGE = 50
_MAX_ATTEMPT_PAGE = 200


def _excerpt(text: Any, limit: int = _EXCERPT_CHARS) -> str:
    """One line of a question, cut on a word boundary with an ellipsis."""
    body = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(body) <= limit:
        return body
    cut = body[:limit]
    space = cut.rfind(" ")
    return (cut[: space if space > limit * 0.6 else limit]).rstrip(" ,;:") + "…"


def _answer_mode(row: dict[str, Any]) -> str:
    """'typed' or 'handwritten'.

    Defaults to typed rather than to unknown: every attempt written before the
    upload path existed was typed, and there is no third thing it could have
    been.
    """
    mode = str(row.get("answer_mode") or "").strip().lower()
    return mode if mode in {"typed", "handwritten"} else "typed"


def _attempt_questions(
    supabase: Any, question_ids: list[str]
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """(question rows, paper rows) for a page of attempts, by id.

    The history is not scoped to an exam — it is everything this aspirant has
    written — so the questions are fetched by id rather than walked down from a
    paper list. `reviewer_status` is deliberately NOT filtered: an attempt at a
    question whose verification was later revoked is still the aspirant's
    answer, and hiding their own work because the corpus changed under them
    would be the surface lying about their history.
    """
    if not question_ids:
        return {}, {}
    questions: dict[str, dict[str, Any]] = {}
    for chunk in _chunks(sorted(set(question_ids))):
        rows = _safe(
            lambda ids=chunk: _paginate_all(
                lambda a, b, ids=ids: (
                    supabase.table("pyq_questions")
                    .select(_QUESTION_COLUMNS)
                    .in_("id", ids)
                    .order("id")
                    .range(a, b)
                    .execute()
                    .data
                )
            ),
            default=[],
        ) or []
        for r in rows:
            questions[str(r.get("id"))] = r

    paper_ids = sorted({
        str(q.get("pyq_paper_id")) for q in questions.values() if q.get("pyq_paper_id")
    })
    papers: dict[str, dict[str, Any]] = {}
    for chunk in _chunks(paper_ids):
        rows = _safe(
            lambda ids=chunk: _paginate_all(
                lambda a, b, ids=ids: (
                    supabase.table("pyq_papers")
                    .select(_PAPER_COLUMNS)
                    .in_("id", ids)
                    .order("id")
                    .range(a, b)
                    .execute()
                    .data
                )
            ),
            default=[],
        ) or []
        for r in rows:
            papers[str(r.get("id"))] = r
    return questions, papers


def attempt_history_row(
    attempt: dict[str, Any],
    *,
    question: dict[str, Any] | None,
    paper: dict[str, Any] | None,
    label: str | None,
    topic: str | None,
    page_count: int | None = None,
) -> dict[str, Any]:
    """One row of the answer history.

    Carries the attempt's own facts and enough of the question to recognise it.
    The full answer text is NOT here: a hundred-row page would carry a hundred
    essays, and the row's job is to get the aspirant to the one they meant.
    """
    base = attempt_payload(attempt)
    base.pop("answer_text", None)
    question = question or {}
    meta = _meta(question)
    thematic = question_is_thematic(question, paper)
    return {
        **base,
        "answer_mode": _answer_mode(attempt),
        # How many pages a handwritten attempt has, so the row can read
        # "3 pages" where a typed row reads "260 words".
        "page_count": page_count,
        # 0 and null are different answers, so the badge is a tri-state: pasted
        # (>0), clean (0), unknown (null, predating paste tracking).
        "has_pasted_text": (
            None if base.get("pasted_chars") is None else base["pasted_chars"] > 0
        ),
        "question": {
            "id": question.get("id"),
            "excerpt": _excerpt(question.get("question_text")),
            "label": label,
            "breadcrumb": breadcrumb_for(question, paper=paper, label=label, topic=topic),
            "subject": subject_of(question, paper),
            "paper_id": question.get("pyq_paper_id"),
            "paper_number": paper_slot(paper or {})[0] or None,
            "year": (paper or {}).get("year"),
            "marks": _as_int(meta.get("marks")),
            "word_limit": _as_int(meta.get("word_limit")),
            "theme": topic if thematic else None,
            "is_thematic": thematic,
        },
    }


def _attempt_matches(row: dict[str, Any], **filters: Any) -> bool:
    """Whether one enriched history row survives the surface's filters.

    Applied here rather than in SQL because every axis but status and date
    lives on the QUESTION, not on the attempt — subject, paper and theme are
    all properties of what was answered. Pushing them into the attempts query
    would mean a join PostgREST cannot express and a second round trip either
    way.
    """
    q = row.get("question") or {}
    if (subject := filters.get("subject")) and q.get("subject") != subject:
        return False
    if (paper_id := filters.get("paper_id")) and str(q.get("paper_id") or "") != str(paper_id):
        return False
    if (theme := filters.get("theme")) and q.get("theme") != theme:
        return False
    if (status := filters.get("status")) and row.get("status") != status:
        return False
    stamp = str(row.get("submitted_at") or row.get("started_at") or "")
    if (since := filters.get("since")) and stamp[:10] < str(since)[:10]:
        return False
    if (until := filters.get("until")) and stamp[:10] > str(until)[:10]:
        return False
    return True


def _attempt_facets(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The filter values that actually occur in this history.

    Built from the aspirant's own attempts, not from the catalogue: offering a
    subject they have never written in is a filter that can only return
    nothing.
    """
    subjects: dict[str, int] = {}
    papers: dict[str, dict[str, Any]] = {}
    themes: dict[str, int] = {}
    statuses: dict[str, int] = {}
    for row in rows:
        q = row.get("question") or {}
        if subject := q.get("subject"):
            subjects[subject] = subjects.get(subject, 0) + 1
        if paper_id := q.get("paper_id"):
            key = str(paper_id)
            entry = papers.setdefault(
                key,
                {
                    "paper_id": key,
                    "label": " · ".join(
                        str(p) for p in (q.get("year"), f"P{q['paper_number']}"
                                         if q.get("paper_number") else None) if p
                    ) or "Paper",
                    "count": 0,
                },
            )
            entry["count"] += 1
        if theme := q.get("theme"):
            themes[theme] = themes.get(theme, 0) + 1
        statuses[row.get("status") or "draft"] = statuses.get(row.get("status") or "draft", 0) + 1
    return {
        "subjects": [{"value": k, "count": v} for k, v in sorted(subjects.items())],
        "papers": sorted(papers.values(), key=lambda p: p["label"], reverse=True),
        "themes": [{"value": k, "count": v} for k, v in sorted(themes.items())],
        "statuses": [{"value": k, "count": v} for k, v in sorted(statuses.items())],
    }


def _page_counts(supabase: Any, attempt_ids: list[str]) -> dict[str, int]:
    """attempt_id → how many pages it has. Only for handwritten attempts."""
    if not attempt_ids:
        return {}
    counts: dict[str, int] = {}
    for chunk in _chunks(sorted(set(attempt_ids))):
        rows = _safe(
            lambda ids=chunk: _paginate_all(
                lambda a, b, ids=ids: (
                    supabase.table("descriptive_attempt_pages")
                    .select("id, attempt_id")
                    .in_("attempt_id", ids)
                    .order("id")
                    .range(a, b)
                    .execute()
                    .data
                )
            ),
            default=[],
        ) or []
        for r in rows:
            key = str(r.get("attempt_id") or "")
            if key:
                counts[key] = counts.get(key, 0) + 1
    return counts


def _owned_attempts(supabase: Any, user_id: str, **eq: Any) -> list[dict[str, Any]]:
    """Every attempt this user owns, paginated. Never another user's."""
    def _page(a: int, b: int) -> Any:
        query = (
            supabase.table("descriptive_attempts")
            .select(_ATTEMPT_COLUMNS)
            .eq("user_id", user_id)
        )
        for key, value in eq.items():
            if value:
                query = query.eq(key, value)
        # `started_at` is not unique, so it cannot partition the pages on its
        # own; `id` breaks the tie and keeps newest-first.
        return query.order("started_at", desc=True).order("id").range(a, b).execute().data

    rows = _safe(lambda: _paginate_all(_page), default=None)
    if rows is None:
        raise DescriptiveError(
            "attempts_read_failed", "Your attempts are unavailable right now.", 503
        )
    return rows


def _enrich_attempts(
    supabase: Any, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Attach question, paper, label and topic to each attempt row."""
    qids = [str(r.get("pyq_question_id")) for r in rows if r.get("pyq_question_id")]
    questions, papers = _attempt_questions(supabase, qids)
    pages = _page_counts(supabase, [str(r.get("id")) for r in rows
                                    if _answer_mode(r) == "handwritten"])
    _, labels = _paper_context(supabase, list(questions.values()))
    topics = _primary_topic_names(supabase, list(questions))
    out = []
    for row in rows:
        qid = str(row.get("pyq_question_id") or "")
        question = questions.get(qid)
        paper = papers.get(str((question or {}).get("pyq_paper_id") or ""))
        out.append(
            attempt_history_row(
                row,
                question=question,
                paper=paper,
                label=labels.get(qid),
                topic=topics.get(qid),
                page_count=pages.get(str(row.get("id"))),
            )
        )
    return out


def list_attempts(
    supabase: Any,
    user_id: str,
    *,
    pyq_question_id: str | None = None,
    subject: str | None = None,
    paper_id: str | None = None,
    theme: str | None = None,
    status: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: Any = _ATTEMPT_PAGE,
    offset: Any = 0,
) -> dict[str, Any]:
    """This user's answer history, newest first, with the filters applied.

    EVERY ATTEMPT IS KEPT. A submitted attempt is never replaced by a later one
    — that is the point of the surface, and the whole history is what makes a
    comparison possible. Only the open draft is unique, one per question.
    """
    if not user_id:
        raise DescriptiveError("user_required", "Sign in to see your answers.", 401)
    cap = max(1, min(_as_int(limit) or _ATTEMPT_PAGE, _MAX_ATTEMPT_PAGE))
    start = max(0, _as_int(offset) or 0)

    rows = _owned_attempts(supabase, user_id, pyq_question_id=pyq_question_id)
    enriched = _enrich_attempts(supabase, rows)

    # Facets describe the WHOLE history, not the filtered page: a filter list
    # that shrinks as you use it cannot be used to widen a selection again.
    facets = _attempt_facets(enriched)
    matched = [
        r for r in enriched
        if _attempt_matches(
            r, subject=subject, paper_id=paper_id, theme=theme,
            status=status, since=since, until=until,
        )
    ]
    page = matched[start : start + cap]
    return {
        "items": page,
        "count": len(page),
        "total": len(matched),
        "offset": start,
        "limit": cap,
        "has_more": start + len(page) < len(matched),
        "facets": facets,
    }


# ── handwritten pages (P3) ───────────────────────────────────────────────
#
# NO OCR. Nothing reads these images. They are the aspirant's own record, shown
# back to them beside the same rubric a typed answer gets.

#: What a phone camera and a scanner actually produce. HEIC is here because it
#: is the iPhone default and an aspirant should not have to convert a photo to
#: practise; nothing decodes it server-side, so it costs only the allowlist.
PAGE_MIME_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/heic": "heic",
    "image/heif": "heif",
    "application/pdf": "pdf",
}

#: Per page. A phone photo of an A4 sheet is 2-5 MB; 10 leaves room for a
#: high-resolution scan without letting a video through.
MAX_PAGE_BYTES = 10 * 1024 * 1024

#: A Mains answer is 150-250 words. Eight sides is a very long answer and a
#: generous ceiling; past it, something other than an answer is being uploaded.
MAX_ATTEMPT_PAGES = 8

#: How long a view URL lives. Long enough to read the answer, short enough that
#: a copied URL is not a permanent share.
PAGE_URL_TTL_SECONDS = 900

ANSWER_PAGES_BUCKET = "answer-pages"

_PAGE_COLUMNS = (
    "id, attempt_id, page_no, storage_bucket, storage_path, mime_type, bytes, "
    "created_at"
)


def page_storage_path(user_id: str, attempt_id: str, page_no: int, mime: str) -> str:
    """`<user_id>/<attempt_id>/page_<n>.<ext>`.

    THE FIRST SEGMENT IS THE OWNER, and that is load-bearing: the storage
    policy in migration 298 compares `(storage.foldername(name))[1]` to
    `auth.uid()`, so the path itself is what makes one aspirant's folder
    unreadable to another. Building it from anything the client sends would
    hand them someone else's folder.
    """
    ext = PAGE_MIME_TYPES.get(mime, "bin")
    return f"{user_id}/{attempt_id}/page_{int(page_no)}.{ext}"


def page_payload(row: dict[str, Any], *, url: str | None = None) -> dict[str, Any]:
    """One page as the client sees it. The bucket and path never leave the server.

    A client that knows the object path knows another aspirant's path too —
    they differ only by a user id. The surface needs a URL, not a location.
    """
    return {
        "id": row.get("id"),
        "page_no": _as_int(row.get("page_no")),
        "mime_type": row.get("mime_type"),
        "bytes": _as_int(row.get("bytes")),
        "created_at": row.get("created_at"),
        "url": url,
    }


def validate_page_upload(*, page_no: Any, mime_type: Any, size_bytes: Any) -> tuple[int, str, int]:
    """(page_no, mime, bytes), or a DescriptiveError naming what is wrong.

    Every limit is checked here, before a signed URL exists. A limit enforced
    only in the browser is not a limit.
    """
    number = _as_int(page_no)
    if number is None or number < 1 or number > MAX_ATTEMPT_PAGES:
        raise DescriptiveError(
            "page_number_invalid",
            f"Pages are numbered 1 to {MAX_ATTEMPT_PAGES}.",
            422,
        )
    mime = str(mime_type or "").strip().lower()
    if mime not in PAGE_MIME_TYPES:
        raise DescriptiveError(
            "page_type_unsupported",
            "Upload a photo or PDF — JPG, PNG, HEIC or PDF.",
            422,
        )
    size = _as_int(size_bytes)
    if size is None or size <= 0:
        raise DescriptiveError("page_empty", "That file is empty.", 422)
    if size > MAX_PAGE_BYTES:
        raise DescriptiveError(
            "page_too_large",
            f"Each page must be under {MAX_PAGE_BYTES // (1024 * 1024)} MB.",
            422,
        )
    return number, mime, size


def _attempt_pages(supabase: Any, attempt_id: str) -> list[dict[str, Any]]:
    rows = _safe(
        lambda: (
            supabase.table("descriptive_attempt_pages")
            .select(_PAGE_COLUMNS)
            .eq("attempt_id", attempt_id)
            .order("page_no")
            .execute()
            .data
        ),
        default=None,
    )
    if rows is None:
        raise DescriptiveError(
            "pages_read_failed", "Your uploaded pages are unavailable right now.", 503
        )
    return rows


def _signed_page_url(supabase: Any, row: dict[str, Any]) -> str | None:
    """A short-lived read URL, or None when storage cannot issue one.

    None rather than a raise: one unreadable page must not take down the view
    of the other seven, and the surface renders a page it cannot show as
    missing rather than pretending the attempt is broken.
    """
    bucket = row.get("storage_bucket") or ANSWER_PAGES_BUCKET
    path = row.get("storage_path")
    if not path:
        return None
    try:
        signed = supabase.storage.from_(bucket).create_signed_url(
            path, PAGE_URL_TTL_SECONDS
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("answer page signed url failed for %s: %s", path, exc)
        return None
    if isinstance(signed, dict):
        return signed.get("signedURL") or signed.get("signedUrl") or signed.get("url")
    return getattr(signed, "signed_url", None) or getattr(signed, "signedURL", None)


def list_attempt_pages(supabase: Any, user_id: str, attempt_id: str) -> dict[str, Any]:
    """This attempt's pages, each with a freshly signed view URL."""
    attempt = _load_owned_attempt(supabase, user_id, attempt_id)
    rows = _attempt_pages(supabase, attempt_id)
    return {
        "attempt_id": attempt_id,
        "answer_mode": _answer_mode(attempt),
        "pages": [page_payload(r, url=_signed_page_url(supabase, r)) for r in rows],
        "max_pages": MAX_ATTEMPT_PAGES,
        "max_bytes": MAX_PAGE_BYTES,
        "accepted_types": sorted(PAGE_MIME_TYPES),
    }


def request_page_upload(
    supabase: Any,
    user_id: str,
    attempt_id: str,
    *,
    page_no: Any,
    mime_type: Any,
    size_bytes: Any,
) -> dict[str, Any]:
    """A signed URL to PUT one page to, and the row that will point at it.

    The attempt must still be a draft. A submitted attempt is the record of
    what was written under time; adding a page to it afterwards would let an
    answer grow after it was scored, which is exactly what the rubric is meant
    to be honest about.
    """
    attempt = _load_owned_attempt(supabase, user_id, attempt_id)
    if (attempt.get("status") or "draft") != "draft":
        raise DescriptiveError(
            "attempt_submitted", "This attempt is already submitted.", 409
        )
    number, mime, size = validate_page_upload(
        page_no=page_no, mime_type=mime_type, size_bytes=size_bytes
    )

    existing = {_as_int(r.get("page_no")): r for r in _attempt_pages(supabase, attempt_id)}
    # A REPLACEMENT is not a new page. Re-shooting a blurry page 3 must stay
    # page 3, so the ceiling counts pages that do not exist yet.
    if number not in existing and len(existing) >= MAX_ATTEMPT_PAGES:
        raise DescriptiveError(
            "too_many_pages",
            f"An answer can have at most {MAX_ATTEMPT_PAGES} pages.",
            422,
        )

    path = page_storage_path(user_id, attempt_id, number, mime)
    try:
        signed = supabase.storage.from_(ANSWER_PAGES_BUCKET).create_signed_upload_url(path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("answer page upload url failed for %s: %s", path, exc)
        raise DescriptiveError(
            "page_upload_unavailable", "Couldn't start that upload. Try again.", 503
        ) from None
    upload_url = None
    token = None
    if isinstance(signed, dict):
        upload_url = signed.get("signedURL") or signed.get("signedUrl") or signed.get("url")
        token = signed.get("token")
    if not upload_url:
        raise DescriptiveError(
            "page_upload_unavailable", "Couldn't start that upload. Try again.", 503
        )

    row = {
        "attempt_id": attempt_id,
        "page_no": number,
        "storage_bucket": ANSWER_PAGES_BUCKET,
        "storage_path": path,
        "mime_type": mime,
        "bytes": size,
    }
    # Replacing a page removes the old ROW; the object at that path is
    # overwritten by the upload itself, because the path is derived from the
    # page number rather than from the filename.
    if number in existing:
        _safe(
            lambda: (
                supabase.table("descriptive_attempt_pages")
                .delete()
                .eq("id", existing[number].get("id"))
                .execute()
            ),
            default=None,
        )
    inserted = _safe(
        lambda: supabase.table("descriptive_attempt_pages").insert(row).execute().data,
        default=None,
    )
    if not inserted:
        raise DescriptiveError(
            "page_upload_unavailable", "Couldn't start that upload. Try again.", 503
        )

    # An attempt with a page is a handwritten attempt, and its word count is no
    # longer a fact about it.
    _safe(
        lambda: (
            supabase.table("descriptive_attempts")
            .update({"answer_mode": "handwritten", "word_count": None,
                     "updated_at": _now_iso()})
            .eq("id", attempt_id)
            .eq("user_id", user_id)
            .execute()
        ),
        default=None,
    )
    return {
        "page": page_payload(inserted[0]),
        "upload_url": upload_url,
        "upload_token": token,
        # The path is returned so the client can PUT to it, and for no other
        # reason; it is never part of a read payload.
        "storage_path": path,
    }


def delete_attempt_page(
    supabase: Any, user_id: str, attempt_id: str, page_no: Any
) -> dict[str, Any]:
    """Remove one page, and its object. The aspirant can take their images back."""
    attempt = _load_owned_attempt(supabase, user_id, attempt_id)
    if (attempt.get("status") or "draft") != "draft":
        raise DescriptiveError(
            "attempt_submitted", "This attempt is already submitted.", 409
        )
    number = _as_int(page_no)
    rows = _attempt_pages(supabase, attempt_id)
    target = next((r for r in rows if _as_int(r.get("page_no")) == number), None)
    if target is None:
        raise DescriptiveError("page_not_found", "That page isn't there.", 404)

    path = target.get("storage_path")
    if path:
        try:
            supabase.storage.from_(
                target.get("storage_bucket") or ANSWER_PAGES_BUCKET
            ).remove([path])
        except Exception as exc:  # noqa: BLE001
            # The ROW goes either way. An object nothing points at is storage
            # to reclaim; a row pointing at a deleted object is a broken page
            # the aspirant can see.
            logger.warning("answer page object delete failed for %s: %s", path, exc)

    deleted = _safe(
        lambda: (
            supabase.table("descriptive_attempt_pages")
            .delete()
            .eq("id", target.get("id"))
            .execute()
            .data
        ),
        default=None,
    )
    if deleted is None:
        raise DescriptiveError("page_delete_failed", "Couldn't remove that page.", 503)

    remaining = [r for r in rows if r is not target]
    if not remaining:
        # The last page going means this is a typed attempt again — with an
        # empty answer, which is what it has.
        _safe(
            lambda: (
                supabase.table("descriptive_attempts")
                .update({"answer_mode": "typed", "word_count": word_count(
                    attempt.get("answer_text") or ""), "updated_at": _now_iso()})
                .eq("id", attempt_id)
                .eq("user_id", user_id)
                .execute()
            ),
            default=None,
        )
    return {"deleted": number, "remaining": len(remaining)}


def set_answer_mode(
    supabase: Any, user_id: str, attempt_id: str, mode: Any
) -> dict[str, Any]:
    """Switch a draft between typing and uploading.

    Switching to typed with pages still attached is refused rather than silently
    deleting them: eight photographs of an answer are not something to discard
    on a mis-click.
    """
    wanted = str(mode or "").strip().lower()
    if wanted not in {"typed", "handwritten"}:
        raise DescriptiveError("answer_mode_invalid", "Choose typing or upload.", 422)
    attempt = _load_owned_attempt(supabase, user_id, attempt_id)
    if (attempt.get("status") or "draft") != "draft":
        raise DescriptiveError(
            "attempt_submitted", "This attempt is already submitted.", 409
        )
    if wanted == "typed" and _attempt_pages(supabase, attempt_id):
        raise DescriptiveError(
            "pages_present",
            "Remove the uploaded pages first, then switch back to typing.",
            409,
        )
    patch = {"answer_mode": wanted, "updated_at": _now_iso()}
    patch["word_count"] = (
        None if wanted == "handwritten" else word_count(attempt.get("answer_text") or "")
    )
    updated = _safe(
        lambda: (
            supabase.table("descriptive_attempts")
            .update(patch)
            .eq("id", attempt_id)
            .eq("user_id", user_id)
            .execute()
            .data
        ),
        default=None,
    )
    if not updated:
        raise DescriptiveError("attempt_save_failed", "Couldn't switch modes.", 503)
    return attempt_payload(updated[0])


def attempt_detail(supabase: Any, user_id: str, attempt_id: str) -> dict[str, Any]:
    """One attempt of this user's, in full, with the question it answers.

    Read-only by construction: the payload carries no draft affordance. An
    aspirant who wants to write this question again starts a NEW attempt — the
    old text is shown beside the blank editor, never loaded into it, because
    editing last month's answer in place would destroy the record of what they
    could do last month.
    """
    row = _load_owned_attempt(supabase, user_id, attempt_id)
    enriched = _enrich_attempts(supabase, [row])[0]
    pages = _attempt_pages(supabase, attempt_id) if _answer_mode(row) == "handwritten" else []
    return {
        "attempt": {**enriched, "answer_text": row.get("answer_text") or ""},
        # Signed fresh on every read, and short-lived: a copied URL must not be
        # a permanent share of someone's answer.
        "pages": [page_payload(r, url=_signed_page_url(supabase, r)) for r in pages],
        # The aspirant can always write it again; the old attempt stays.
        "can_rewrite": bool(row.get("pyq_question_id")),
    }


def compare_attempts(
    supabase: Any, user_id: str, pyq_question_id: str
) -> dict[str, Any]:
    """Every attempt this user has made at ONE question, oldest first.

    Oldest first, unlike the history list: a comparison is read as a
    progression, and a progression runs forwards.
    """
    if not pyq_question_id:
        raise DescriptiveError("question_required", "Pick a question first.", 400)
    rows = _owned_attempts(supabase, user_id, pyq_question_id=pyq_question_id)
    enriched = _enrich_attempts(supabase, rows)
    by_id = {str(r.get("id")): r for r in rows}
    ordered = sorted(
        enriched,
        key=lambda r: (str(r.get("submitted_at") or r.get("started_at") or ""), str(r.get("id"))),
    )
    attempts = [
        {**r, "answer_text": (by_id.get(str(r.get("id"))) or {}).get("answer_text") or ""}
        for r in ordered
    ]
    submitted = [a for a in attempts if a.get("status") == "submitted"]
    scored = [a["self_total"] for a in submitted if a.get("self_total") is not None]
    words = [a["word_count"] for a in submitted if a.get("word_count") is not None]
    return {
        "question": (attempts[0]["question"] if attempts else None),
        "attempts": attempts,
        "count": len(attempts),
        "submitted_count": len(submitted),
        # Stated rather than computed in the client so two surfaces cannot
        # disagree about what "improved" means.
        "self_total_first": scored[0] if scored else None,
        "self_total_last": scored[-1] if scored else None,
        "word_count_first": words[0] if words else None,
        "word_count_last": words[-1] if words else None,
    }
