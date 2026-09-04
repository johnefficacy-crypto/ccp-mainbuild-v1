"""Per-paper reachability bands, and per-paper topic composition.

Two reads, deliberately in one module because they are the two halves of "what
was this paper made of" — and deliberately with DIFFERENT eligibility, because
they answer different questions from different columns.

READ 1 — reachability (``exam_reachability``)
---------------------------------------------
Per-paper counts of ``pyq_questions.observed_difficulty``, for the papers that
have actually been assessed.

ELIGIBILITY IS COMPUTED, NEVER A LIST. A paper is eligible only when every one
of its verified questions carries a non-NULL ``observed_difficulty`` AND the
paper holds more than one distinct band value. Both halves are load-bearing:

  * NULL means the paper was never assessed. Mains (phase 626ec667…) is 1 131
    questions, all NULL; 2025 CSAT (phase d813043d…) is 80, all NULL.
  * A uniform value means the August 2026 bulk import's default, not a
    judgement. The CSAT archive (phase 1d6611c7…) is 221 questions all
    ``'medium'``; exam aded8ee9… is ~940 the same way.

Neither shape is distinguishable from a judged paper by looking at any single
row, which is why this is computed over the whole paper rather than filtered
per question. Verified live 2026-09-03: only UPSC Prelims GS-I qualifies.

SCOPED BY PAPER, NEVER BY PHASE ALONE. ``exam_phases`` has no unique
constraint and three phases named "Prelims" exist for UPSC. The nine GS-I
papers span two of them — 715de35f… (2018-2025) and 6566d50e… (2026) — so
gathering the series by phase returns eight papers or one, never nine, and
does so silently. ``phase_id`` is therefore an optional NARROWING filter only;
a caller that passes one is opting into that split knowingly.

READ 2 — composition (``paper_composition``)
--------------------------------------------
Verified primary topic tags for ONE paper, grouped under their parent topic.

Different question, different column, different eligibility: a paper is
eligible here when its questions carry primary topic tags, regardless of
whether difficulty was ever assessed. The two must not be conflated — as of
2026-09-04 three of the four CSAT papers and most of Mains have no tags at all.

``topics`` is a two-level tree (``parent_topic_id``, migration 029:29-44) and
tags sit at either level: the nine GS-I papers are tagged to microtopics, while
2025 CSAT's 80 tags are all top-level topics. ``tag_level`` reports which, so
the caller can say so rather than present the two as equivalent.

Both reads are VERIFIED-ONLY and conjunctive across papers, questions and tags.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("career_copilot.exam_intelligence.reachability")

_PAGE = 1000   # rows per pagination page (matches the rest of the package)
_BATCH = 250   # max ids per IN() filter (PostgREST URL-length ceiling)

#: Recognised ``observed_difficulty`` values, in reading order. Anything else
#: stored in that column is an unknown vocabulary, not a fourth band — see
#: ``classify_paper``.
BANDS: tuple[str, ...] = ("easy", "medium", "hard")

#: Why a paper is not plotted. Returned as counts so an empty state can say
#: which of these it is rather than "no data".
NOT_ASSESSED = "not_assessed"
UNIFORM = "uniform"
UNRECOGNISED = "unrecognised"
OFF_SUBJECT = "off_subject"
ELIGIBLE = "eligible"


def _chunks(items: list[Any], n: int) -> list[list[Any]]:
    return [items[i : i + n] for i in range(0, len(items), n)]


def _paginate_all(build_query: Any) -> list[dict[str, Any]]:
    """Range-paginate a PostgREST read so Supabase's ``db-max-rows`` cannot
    silently truncate a bulk read into an arbitrary sample.

    ``build_query(from_n, to_n)`` must carry a stable ``.order(...)`` key so
    successive pages partition the result deterministically. Exceptions
    propagate — a truncated read here would produce a paper that looks
    uniformly 'medium' because the rest of its rows were never fetched, which
    is exactly the failure this module exists to prevent.
    """
    all_rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        rows = build_query(offset, offset + _PAGE - 1) or []
        all_rows.extend(rows)
        if len(rows) < _PAGE:
            break
        offset += _PAGE
    return all_rows


def _band_of(raw: Any) -> str | None:
    """Normalise one stored ``observed_difficulty`` value to a band, or None.

    Returns ``None`` for NULL/blank (never assessed) and the sentinel
    ``"__other__"`` for a non-empty value outside the vocabulary, so the two
    are never collapsed into the same exclusion reason.
    """
    if raw is None:
        return None
    val = str(raw).strip().lower()
    if not val:
        return None
    return val if val in BANDS else "__other__"


def tally_paper(questions: list[dict[str, Any]]) -> dict[str, int]:
    """Band counts plus the two exclusion signals, for one paper's questions."""
    counts = {band: 0 for band in BANDS}
    counts["null"] = 0
    counts["other"] = 0
    for q in questions:
        band = _band_of(q.get("observed_difficulty"))
        if band is None:
            counts["null"] += 1
        elif band == "__other__":
            counts["other"] += 1
        else:
            counts[band] += 1
    counts["total"] = len(questions)
    return counts


def classify_paper(counts: dict[str, int]) -> str:
    """Eligibility verdict for one paper's tally. Deterministic, no heuristics.

    Precedence is deliberate: an unassessed question outranks everything else,
    because a paper that is only partly judged is not a judged paper — plotting
    its judged subset would present a partial pass as a complete one.
    """
    if counts.get("total", 0) == 0:
        return NOT_ASSESSED
    if counts.get("null", 0) > 0:
        return NOT_ASSESSED
    if counts.get("other", 0) > 0:
        return UNRECOGNISED
    if sum(1 for band in BANDS if counts.get(band, 0) > 0) < 2:
        return UNIFORM
    return ELIGIBLE


def _verified_papers(
    supabase: Any, exam_id: str, phase_id: str | None
) -> list[dict[str, Any]]:
    def build(from_n: int, to_n: int):
        q = (
            supabase.table("pyq_papers")
            .select("id, year, exam_phase_id, paper_code, metadata")
            .eq("exam_id", exam_id)
            .eq("trust_status", "verified")
        )
        if phase_id:
            q = q.eq("exam_phase_id", phase_id)
        return q.order("id").range(from_n, to_n).execute().data

    return _paginate_all(build)


def _verified_questions(
    supabase: Any, paper_ids: list[str], columns: str
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chunk in _chunks(paper_ids, _BATCH):
        rows.extend(
            _paginate_all(
                lambda from_n, to_n, c=chunk: (
                    supabase.table("pyq_questions")
                    .select(columns)
                    .in_("pyq_paper_id", c)
                    .eq("reviewer_status", "verified")
                    .order("id")
                    .range(from_n, to_n)
                    .execute()
                    .data
                )
            )
        )
    return rows


def _phase_names(supabase: Any, phase_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not phase_ids:
        return {}
    rows: list[dict[str, Any]] = []
    for chunk in _chunks(phase_ids, _BATCH):
        rows.extend(
            _paginate_all(
                lambda from_n, to_n, c=chunk: (
                    supabase.table("exam_phases")
                    .select("id, phase_name, phase_slug")
                    .in_("id", c)
                    .order("id")
                    .range(from_n, to_n)
                    .execute()
                    .data
                )
            )
        )
    return {r["id"]: r for r in rows if r.get("id")}


def _primary_tag_topics(
    supabase: Any, question_ids: list[str]
) -> tuple[dict[str, str], set[str]]:
    """{question_id → topic_id} from its VERIFIED PRIMARY tags, lowest id wins,
    plus the set of questions that carried more than one.

    Primary only. Every CSAT question also carries a secondary tag to the
    coarse upsc-csat topic, so counting both roles would attribute one question
    to two subjects and double every figure downstream.
    """
    tags: list[dict[str, Any]] = []
    for chunk in _chunks(question_ids, _BATCH):
        tags.extend(
            _paginate_all(
                lambda from_n, to_n, c=chunk: (
                    supabase.table("pyq_question_topic_tags")
                    .select("id, question_id, topic_id, tag_role")
                    .in_("question_id", c)
                    .eq("tag_role", "primary")
                    .eq("reviewer_status", "verified")
                    .order("id")
                    .range(from_n, to_n)
                    .execute()
                    .data
                )
            )
        )
    chosen: dict[str, str] = {}
    twice: set[str] = set()
    for t in sorted(tags, key=lambda r: str(r.get("id") or "")):
        qid, tid = t.get("question_id"), t.get("topic_id")
        if not qid or not tid:
            continue
        if qid in chosen:
            twice.add(qid)
            continue
        chosen[qid] = tid
    return chosen, twice


def _topic_rows(supabase: Any, topic_ids: list[str]) -> dict[str, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chunk in _chunks(sorted(set(topic_ids)), _BATCH):
        rows.extend(
            _paginate_all(
                lambda from_n, to_n, c=chunk: (
                    supabase.table("topics")
                    .select("id, name, subject_id, parent_topic_id")
                    .in_("id", c)
                    .order("id")
                    .range(from_n, to_n)
                    .execute()
                    .data
                )
            )
        )
    return {r["id"]: r for r in rows if r.get("id")}


def _section_subjects(supabase: Any, section_ids: list[str]) -> dict[str, str]:
    """{section_id → subject_id} for ``exam_phase_sections``."""
    ids = sorted({s for s in section_ids if s})
    if not ids:
        return {}
    rows: list[dict[str, Any]] = []
    for chunk in _chunks(ids, _BATCH):
        rows.extend(
            _paginate_all(
                lambda from_n, to_n, c=chunk: (
                    supabase.table("exam_phase_sections")
                    .select("id, subject_id")
                    .in_("id", c)
                    .order("id")
                    .range(from_n, to_n)
                    .execute()
                    .data
                )
            )
        )
    return {r["id"]: r["subject_id"] for r in rows if r.get("id") and r.get("subject_id")}


def resolve_question_subjects(
    supabase: Any, questions: list[dict[str, Any]]
) -> dict[str, str]:
    """{question_id → subject_id} for the questions that can be attributed.

    Section first, primary tag second. Those are the two reliable
    discriminators; ``exam_phase_sections.section_label`` is NOT one — the CSAT
    papers carry three different labels ("CSAT (Paper II)", "General Studies
    Paper II / CSAT", …) and two of them carry NULL, so a label match would
    silently keep or drop papers depending on which spelling an operator typed.

    A question that resolves to neither is simply absent from the map. Callers
    decide what that means; nothing here guesses a subject for it.
    """
    qids = [q["id"] for q in questions if q.get("id")]
    if not qids:
        return {}

    by_section = _section_subjects(
        supabase, [q.get("section_id") for q in questions if q.get("section_id")]
    )
    tag_topics, _ = _primary_tag_topics(supabase, qids)
    topics = _topic_rows(supabase, list(tag_topics.values()))

    out: dict[str, str] = {}
    for q in questions:
        qid = q.get("id")
        if not qid:
            continue
        subject = by_section.get(q.get("section_id") or "")
        if not subject:
            topic = topics.get(tag_topics.get(qid) or "")
            subject = (topic or {}).get("subject_id")
        if subject:
            out[qid] = subject
    return out


def _is_subject_paper(
    questions: list[dict[str, Any]],
    question_subjects: dict[str, str],
    subject_id: str,
) -> bool:
    """Is this whole paper the ``subject_id`` paper?

    Judged over the paper, not per question, for the same reason eligibility is:
    a per-question filter would keep the attributable half of a mixed paper and
    plot it as a complete one. So every question that resolves to a subject must
    resolve to THIS subject, and at least one must resolve at all. A paper whose
    questions resolve to nothing is not identifiable as this series and is
    excluded — CSAT's three subjects make its papers fail the first test, and an
    untagged, unsectioned paper fails the second.
    """
    resolved = {
        question_subjects[q["id"]]
        for q in questions
        if q.get("id") and q["id"] in question_subjects
    }
    return resolved == {subject_id}


def exam_reachability(
    supabase: Any,
    exam_id: str,
    phase_id: str | None = None,
    subject_id: str | None = None,
) -> dict[str, Any]:
    """Per-paper band counts for every ASSESSED paper of ``exam_id``.

    Returns eligible papers oldest-first, plus a breakdown of why the rest were
    excluded so the caller can render a specific empty state instead of a blank
    one. Never raises: a read failure degrades to zero eligible papers, which
    renders the empty state rather than a chart built on a partial read.

    ``subject_id`` PINS THE SERIES TO ONE PAPER. Without it this read plots
    every eligible paper of the exam, and eligibility alone stopped separating
    them once CSAT acquired non-uniform ``observed_difficulty``: three CSAT
    papers then qualified alongside the nine Prelims GS-I ones and landed at
    the same x-positions, so 2023 and 2024 each drew two points and the header
    read "12 assessed papers". Passing the series' subject keeps a paper only
    when every question of it that can be attributed at all attributes to that
    subject — see ``resolve_question_subjects`` for why the discriminator is
    the section or the primary tag and never ``section_label``. A paper holding
    a foreign subject, or holding nothing attributable, is excluded and counted
    under ``off_subject`` rather than dropped silently.
    """
    out: dict[str, Any] = {
        "exam_id": exam_id,
        "verified_only": True,
        "bands": list(BANDS),
        "subject_id": subject_id,
        "papers": [],
        "excluded": {NOT_ASSESSED: 0, UNIFORM: 0, UNRECOGNISED: 0, OFF_SUBJECT: 0},
        "papers_considered": 0,
    }
    if not exam_id:
        return out

    try:
        papers = _verified_papers(supabase, exam_id, phase_id)
        out["papers_considered"] = len(papers)
        if not papers:
            return out

        paper_ids = [p["id"] for p in papers if p.get("id")]
        questions = _verified_questions(
            supabase,
            paper_ids,
            "id, pyq_paper_id, observed_difficulty, section_id"
            if subject_id
            else "id, pyq_paper_id, observed_difficulty",
        )

        by_paper: dict[str, list[dict[str, Any]]] = {pid: [] for pid in paper_ids}
        for q in questions:
            pid = q.get("pyq_paper_id")
            if pid in by_paper:
                by_paper[pid].append(q)

        # Resolved once for the whole exam, not per paper: one section read and
        # one tag read, rather than two per paper.
        q_subjects = (
            resolve_question_subjects(supabase, questions) if subject_id else {}
        )

        phase_meta = _phase_names(
            supabase, list({p.get("exam_phase_id") for p in papers if p.get("exam_phase_id")})
        )

        eligible: list[dict[str, Any]] = []
        for p in papers:
            pid = p["id"]
            paper_questions = by_paper.get(pid, [])
            if subject_id and not _is_subject_paper(
                paper_questions, q_subjects, subject_id
            ):
                out["excluded"][OFF_SUBJECT] += 1
                continue
            counts = tally_paper(paper_questions)
            verdict = classify_paper(counts)
            if verdict != ELIGIBLE:
                out["excluded"][verdict] = out["excluded"].get(verdict, 0) + 1
                continue
            phase = phase_meta.get(p.get("exam_phase_id") or "") or {}
            meta = p.get("metadata") if isinstance(p.get("metadata"), dict) else {}
            eligible.append(
                {
                    "paper_id": pid,
                    "year": p.get("year"),
                    "phase_id": p.get("exam_phase_id"),
                    "phase_name": phase.get("phase_name"),
                    "phase_slug": phase.get("phase_slug"),
                    "paper_code": p.get("paper_code"),
                    # Raw operator-typed fields only; the route turns these into
                    # a display label. The metadata blob itself never ships.
                    "set_code": meta.get("set_code"),
                    "paper_set": meta.get("paper_set"),
                    **{band: counts[band] for band in BANDS},
                    "total": counts["total"],
                }
            )

        # Oldest first: the chart reads left-to-right as a trend. paper_id
        # breaks ties so two eligible papers in one year keep a stable order
        # instead of shuffling between reads.
        eligible.sort(key=lambda r: ((r["year"] is None), r["year"] or 0, r["paper_id"]))
        out["papers"] = eligible
        return out
    except Exception:  # noqa: BLE001
        logger.exception("reachability read failed for exam %s", exam_id)
        return out


def _tag_level(has_parent: bool | None) -> str:
    return "microtopic" if has_parent else "topic"


def paper_composition(supabase: Any, paper_id: str) -> dict[str, Any]:
    """Verified primary-tag topic distribution for ONE verified paper.

    Groups every counted question under its tag's PARENT topic, keeping the
    tagged topic itself as a child when the tag sits at microtopic level. A
    top-level tag is its own group with no children — so a caller can render
    one shape for both, while ``tag_level`` still says which it is looking at.

    One question is counted once. A question carrying more than one verified
    primary tag is attributed to the lowest-id one and reported in
    ``multi_tagged_questions``, so the groups always sum to
    ``tagged_questions`` rather than double-counting a question across topics.
    """
    out: dict[str, Any] = {
        "paper_id": paper_id,
        "verified_only": True,
        "found": False,
        "tag_level": None,
        "total_questions": 0,
        "tagged_questions": 0,
        "untagged_questions": 0,
        "multi_tagged_questions": 0,
        "groups": [],
    }
    if not paper_id:
        return out

    try:
        rows = (
            supabase.table("pyq_papers")
            .select("id, exam_id, year, exam_phase_id, paper_code, metadata")
            .eq("id", paper_id)
            .eq("trust_status", "verified")
            .limit(1)
            .execute()
            .data
        ) or []
        paper = rows[0] if rows else None
        if not paper:
            return out

        phase = (_phase_names(supabase, [paper["exam_phase_id"]]) if paper.get("exam_phase_id") else {})
        phase_row = phase.get(paper.get("exam_phase_id") or "") or {}
        meta = paper.get("metadata") if isinstance(paper.get("metadata"), dict) else {}
        out.update(
            {
                "found": True,
                "exam_id": paper.get("exam_id"),
                "year": paper.get("year"),
                "phase_id": paper.get("exam_phase_id"),
                "phase_name": phase_row.get("phase_name"),
                "paper_code": paper.get("paper_code"),
                "set_code": meta.get("set_code"),
                "paper_set": meta.get("paper_set"),
            }
        )

        questions = _verified_questions(supabase, [paper_id], "id, pyq_paper_id")
        out["total_questions"] = len(questions)
        qids = [q["id"] for q in questions if q.get("id")]
        if not qids:
            return out

        tags: list[dict[str, Any]] = []
        for chunk in _chunks(qids, _BATCH):
            tags.extend(
                _paginate_all(
                    lambda from_n, to_n, c=chunk: (
                        supabase.table("pyq_question_topic_tags")
                        .select("id, question_id, topic_id, tag_role")
                        .in_("question_id", c)
                        .eq("tag_role", "primary")
                        .eq("reviewer_status", "verified")
                        .order("id")
                        .range(from_n, to_n)
                        .execute()
                        .data
                    )
                )
            )

        # One tag per question, deterministically the lowest id.
        chosen: dict[str, str] = {}
        seen_twice: set[str] = set()
        for t in sorted(tags, key=lambda r: str(r.get("id") or "")):
            qid, tid = t.get("question_id"), t.get("topic_id")
            if not qid or not tid:
                continue
            if qid in chosen:
                seen_twice.add(qid)
                continue
            chosen[qid] = tid
        out["multi_tagged_questions"] = len(seen_twice)
        out["tagged_questions"] = len(chosen)
        out["untagged_questions"] = out["total_questions"] - len(chosen)
        if not chosen:
            return out

        topic_ids = sorted(set(chosen.values()))
        topics: list[dict[str, Any]] = []
        for chunk in _chunks(topic_ids, _BATCH):
            topics.extend(
                _paginate_all(
                    lambda from_n, to_n, c=chunk: (
                        supabase.table("topics")
                        .select("id, name, parent_topic_id")
                        .in_("id", c)
                        .order("id")
                        .range(from_n, to_n)
                        .execute()
                        .data
                    )
                )
            )
        topic_by_id = {t["id"]: t for t in topics if t.get("id")}

        # Parents that no tag points at directly still need their names.
        parent_ids = sorted(
            {
                t["parent_topic_id"]
                for t in topics
                if t.get("parent_topic_id") and t["parent_topic_id"] not in topic_by_id
            }
        )
        for chunk in _chunks(parent_ids, _BATCH):
            for row in _paginate_all(
                lambda from_n, to_n, c=chunk: (
                    supabase.table("topics")
                    .select("id, name, parent_topic_id")
                    .in_("id", c)
                    .order("id")
                    .range(from_n, to_n)
                    .execute()
                    .data
                )
            ):
                if row.get("id"):
                    topic_by_id[row["id"]] = row

        levels: set[str] = set()
        groups: dict[str, dict[str, Any]] = {}
        for tid in chosen.values():
            topic = topic_by_id.get(tid)
            if not topic:
                # Tag points at a topic row we could not read. Counting it under
                # an invented group would be a fabricated finding; it stays in
                # tagged_questions and is surfaced as an unresolved remainder.
                continue
            parent_id = topic.get("parent_topic_id")
            levels.add(_tag_level(bool(parent_id)))
            group_id = parent_id or tid
            group = groups.setdefault(
                group_id,
                {
                    "topic_id": group_id,
                    "topic_name": (topic_by_id.get(group_id) or {}).get("name"),
                    "questions": 0,
                    "_children": {},
                },
            )
            group["questions"] += 1
            if parent_id:
                child = group["_children"].setdefault(
                    tid, {"topic_id": tid, "topic_name": topic.get("name"), "questions": 0}
                )
                child["questions"] += 1

        out["tag_level"] = (
            None if not levels else (levels.pop() if len(levels) == 1 else "mixed")
        )

        def _rank(row: dict[str, Any]) -> tuple[int, str]:
            return (-row["questions"], str(row.get("topic_name") or row["topic_id"]))

        ordered = []
        for group in groups.values():
            children = sorted(group.pop("_children").values(), key=_rank)
            ordered.append({**group, "children": children})
        ordered.sort(key=_rank)
        out["groups"] = ordered
        out["unresolved_questions"] = len(chosen) - sum(g["questions"] for g in ordered)
        return out
    except Exception:  # noqa: BLE001
        logger.exception("composition read failed for paper %s", paper_id)
        return out
