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
from datetime import datetime, timezone
from typing import Any

from app.study_os import syllabus

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
    "time_spent_seconds, timer_target_seconds, pasted_chars, self_scores, "
    "self_total, notes, started_at, submitted_at, updated_at"
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


def question_payload(
    question: dict[str, Any],
    *,
    paper: dict[str, Any] | None = None,
    parent_text: str | None = None,
    attempt_count: int = 0,
) -> dict[str, Any]:
    """One question as the practice surface renders it."""
    meta = _meta(question)
    marks = _as_int(meta.get("marks"))
    return {
        "id": question.get("id"),
        "pyq_paper_id": question.get("pyq_paper_id"),
        "question_number": question.get("question_number"),
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
        lambda: (
            supabase.table("pyq_papers")
            .select(_PAPER_COLUMNS)
            .eq("exam_id", exam_id)
            .execute()
            .data
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
            lambda ids=chunk: (
                supabase.table("pyq_questions")
                .select(_QUESTION_COLUMNS)
                .in_("pyq_paper_id", ids)
                .eq("question_type", QUESTION_TYPE)
                .eq("reviewer_status", QUESTION_REVIEWER_STATUS)
                .execute()
                .data
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
            lambda ids=chunk: (
                supabase.table("pyq_question_topic_tags")
                .select("question_id, topic_id, tag_role, reviewer_status")
                .in_("question_id", ids)
                .eq("tag_role", "primary")
                .eq("reviewer_status", "verified")
                .execute()
                .data
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
            lambda ids=chunk: (
                supabase.table("topics")
                .select("id, name, level, parent_topic_id, subject_id, metadata")
                .in_("id", ids)
                .execute()
                .data
            ),
            default=[],
        ) or []
        for r in rows:
            if r.get("id"):
                topics[str(r["id"])] = r

    out: dict[str, dict[str, Any]] = {}
    for t in tags:
        qid = str(t.get("question_id") or "")
        tid = str(t.get("topic_id") or "")
        if qid and tid and tid in topics:
            # First verified primary tag wins; a question with two is an
            # ambiguity the tagging lifecycle owns, not this surface.
            out.setdefault(qid, topics[tid])
    return out


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
                "_sort": spot["paper_sort"],
                "_sections": {},
            },
        )
        paper["question_count"] += count
        sec = paper["_sections"].setdefault(
            section,
            {
                "section": section,
                "part": spot["section_part"],
                "question_count": 0,
                "_sort": spot["section_sort"],
                "themes": [],
            },
        )
        sec["question_count"] += count
        sec["themes"].append(
            {"theme": name, "question_count": count, "_sort": spot["theme_sort"]}
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
        }
        for p in out
    ]
    return out, tabs


def get_catalog(
    supabase: Any,
    exam_id: str,
    *,
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
        paper_items.append(
            {
                "id": pid,
                "label": _paper_label(paper),
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

    topics_by_question = _primary_topics(
        supabase, [str(q["id"]) for q in thematic_half if q.get("id")]
    )
    theme_items, theme_papers = _syllabus_themes(thematic_half, topics_by_question)
    if wanted_paper is not None:
        # The tabs keep every paper — they are how the aspirant switches — but
        # the tree shows only the selected one.
        theme_items = [p for p in theme_items if p["paper_number"] == wanted_paper]

    year_counts: dict[int, int] = {}
    for q in real_half:
        if not subject_of(q, paper_of(q)):
            continue
        y = _as_int(paper_of(q).get("year"))
        if y:
            year_counts[y] = year_counts.get(y, 0) + 1

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
            {"year": y, "question_count": c}
            for y, c in sorted(year_counts.items(), reverse=True)
        ],
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
    exclude_attempted: bool = False,
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

    parents = _parent_texts(supabase, live, page)
    items = [
        question_payload(
            q,
            paper=live.get(str(q.get("pyq_paper_id"))),
            parent_text=parents.get(str(q.get("id"))),
            attempt_count=attempts.get(str(q.get("id")), 0),
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


def _parent_texts(
    supabase: Any, papers: dict[str, Any], page: list[dict[str, Any]]
) -> dict[str, str]:
    """question_id → its parent stem's text, for sub-parts only.

    `parent_question_number` is a number within the same paper, not an id, so the
    lookup is (paper, number) → text.
    """
    wanted: dict[str, tuple[str, int]] = {}
    for q in page:
        parent = _as_int(_meta(q).get("parent_question_number"))
        pid = str(q.get("pyq_paper_id") or "")
        if parent is not None and pid:
            wanted[str(q.get("id"))] = (pid, parent)
    if not wanted:
        return {}

    paper_ids = sorted({pid for pid, _ in wanted.values()})
    rows: list[dict[str, Any]] = []
    for chunk in _chunks(paper_ids):
        got = _safe(
            lambda ids=chunk: (
                supabase.table("pyq_questions")
                .select("id, pyq_paper_id, question_number, question_text")
                .in_("pyq_paper_id", ids)
                .execute()
                .data
            ),
            default=[],
        ) or []
        rows.extend(got)
    by_key = {
        (str(r.get("pyq_paper_id")), _as_int(r.get("question_number"))): r.get("question_text")
        for r in rows
    }
    out: dict[str, str] = {}
    for qid, key in wanted.items():
        text = by_key.get(key)
        if text:
            out[qid] = text
    return out


def _attempt_counts(
    supabase: Any, user_id: str, question_ids: list[str]
) -> dict[str, int]:
    """How many times THIS user has attempted each question. Never another's."""
    if not question_ids or not user_id:
        return {}
    counts: dict[str, int] = {}
    for chunk in _chunks(question_ids):
        rows = _safe(
            lambda ids=chunk: (
                supabase.table("descriptive_attempts")
                .select("pyq_question_id")
                .eq("user_id", user_id)
                .in_("pyq_question_id", ids)
                .execute()
                .data
            ),
            default=[],
        ) or []
        for r in rows:
            qid = str(r.get("pyq_question_id") or "")
            if qid:
                counts[qid] = counts.get(qid, 0) + 1
    return counts


# ── attempts ─────────────────────────────────────────────────────────────


def attempt_payload(row: dict[str, Any]) -> dict[str, Any]:
    """One attempt as the client sees it. ``user_id`` never leaves the server."""
    return {
        "id": row.get("id"),
        "pyq_question_id": row.get("pyq_question_id"),
        "status": row.get("status") or "draft",
        "answer_text": row.get("answer_text") or "",
        "word_count": _as_int(row.get("word_count")) or 0,
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
        patch["word_count"] = word_count(text)
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
        # actually in the column.
        "word_count": word_count(attempt.get("answer_text")),
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


def list_attempts(
    supabase: Any, user_id: str, *, pyq_question_id: str | None = None
) -> dict[str, Any]:
    """This user's attempt history, newest first."""
    query = (
        supabase.table("descriptive_attempts")
        .select(_ATTEMPT_COLUMNS)
        .eq("user_id", user_id)
    )
    if pyq_question_id:
        query = query.eq("pyq_question_id", pyq_question_id)
    rows = _safe(
        lambda: query.order("started_at", desc=True).limit(200).execute().data,
        default=None,
    )
    if rows is None:
        raise DescriptiveError(
            "attempts_read_failed", "Your attempts are unavailable right now.", 503
        )
    return {"items": [attempt_payload(r) for r in rows], "count": len(rows)}
