"""Composition of a SERIES of papers, split by subject and by microtopic.

The third read in this area, and deliberately not a variant of the other two.

  * ``exam_reachability`` asks how reachable each question was from standard
    preparation. That rubric is UPSC GS-I's; "reachable from an NCERT textbook"
    means nothing for a percentages question, and CSAT's stored
    ``observed_difficulty`` was assigned by keyword rule rather than judged
    against any rubric. CSAT must therefore never appear on that chart, and
    nothing here reports difficulty at all — no band, no column, no derived
    label.
  * ``paper_composition`` asks what ONE paper was made of, grouped under the
    parent topic. This read is the same question across a SERIES of papers, so
    the year-on-year movement inside a topic is visible: LCM/HCF ran 16, 8, 16,
    8 across the four CSAT papers, an alternation an aggregate hides.

WHAT SCOPES THE SERIES. The subject of each question's VERIFIED PRIMARY tag,
never ``exam_phase_id``: the four CSAT papers sit on three different phases,
``exam_phases`` has no unique constraint, and five phases named "Prelims" exist
for UPSC. Never ``section_label`` either — the CSAT papers carry three
different spellings of it and two carry NULL.

PRIMARY TAGS ONLY. Every CSAT question also carries a SECONDARY tag to the
coarse upsc-csat topic. Counting both roles doubles every figure in this
payload, so ``tag_role='primary'`` is filtered at the query, and a question
carrying two primary tags is attributed to the lowest-id one and counted once.

VERIFIED-ONLY and conjunctive: unverified papers, questions and tags are all
absent, which is also what keeps the rejected 2026 paper (7b18bf8d…, superseded
by b06305ad…) out without naming it.
"""
from __future__ import annotations

import logging
from typing import Any

from app.exam_intelligence.reachability import (
    _BATCH,
    _chunks,
    _paginate_all,
    _phase_names,
    _primary_tag_topics,
    _section_subjects,
    _topic_rows,
    _verified_papers,
    _verified_questions,
)

logger = logging.getLogger("career_copilot.exam_intelligence.subject_composition")

#: The three shared subjects the UPSC CSAT corpus is tagged into, in the order
#: the section presents them. They are shared rows — SSC CGL tags into the same
#: three — so the series is additionally gated on the exam, below.
CSAT_SUBJECT_IDS: tuple[str, ...] = (
    "55555555-5555-5555-5555-555555555551",  # Quantitative Aptitude
    "55555555-5555-5555-5555-555555555553",  # General Intelligence & Reasoning
    "55555555-5555-5555-5555-555555555552",  # English Language
)

#: Which exam has a CSAT series at all. Editorial, not data: an SSC paper tagged
#: into the same three subjects is not a CSAT paper, and an exam absent from this
#: map renders no section rather than a mislabelled one.
CSAT_SERIES_BY_EXAM_SLUG: dict[str, tuple[str, ...]] = {
    "upsc-cse": CSAT_SUBJECT_IDS,
}


def _subject_rows(supabase: Any, subject_ids: list[str]) -> dict[str, dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for chunk in _chunks(sorted(set(subject_ids)), _BATCH):
        rows.extend(
            _paginate_all(
                lambda from_n, to_n, c=chunk: (
                    supabase.table("subjects")
                    .select("id, name, slug")
                    .in_("id", c)
                    .order("id")
                    .range(from_n, to_n)
                    .execute()
                    .data
                )
            )
        )
    return {r["id"]: r for r in rows if r.get("id")}


def subject_composition_series(
    supabase: Any, exam_id: str, subject_ids: tuple[str, ...] | list[str]
) -> dict[str, Any]:
    """Per-paper subject split and per-topic counts for one series of papers.

    A paper joins the series when at least one of its verified questions is
    attributable to one of ``subject_ids`` — by the question's section, or by
    its verified primary tag's subject. A paper that joins but carries no
    primary tags is still returned, with ``tagged_questions`` 0, so the caller
    renders an empty state for that paper rather than an empty chart or a
    silently missing year.

    ``topics`` carries the per-year counts alongside the total, because the
    total alone hides movement: a topic that ran 16, 8, 16, 8 and one that ran
    12, 12, 12, 12 both aggregate to 48.

    Never raises: a read failure degrades to an empty series, which renders no
    section rather than a section built on a partial read.
    """
    wanted = [s for s in (subject_ids or []) if s]
    out: dict[str, Any] = {
        "exam_id": exam_id,
        "verified_only": True,
        "subject_ids": list(wanted),
        "subjects": [],
        "papers": [],
        "topics": [],
        "papers_considered": 0,
    }
    if not exam_id or not wanted:
        return out

    try:
        papers = _verified_papers(supabase, exam_id, None)
        out["papers_considered"] = len(papers)
        if not papers:
            return out

        paper_ids = [p["id"] for p in papers if p.get("id")]
        questions = _verified_questions(
            supabase, paper_ids, "id, pyq_paper_id, section_id"
        )
        if not questions:
            return out

        qids = [q["id"] for q in questions if q.get("id")]
        by_section = _section_subjects(
            supabase, [q.get("section_id") for q in questions if q.get("section_id")]
        )
        tag_topics, multi_tagged = _primary_tag_topics(supabase, qids)
        topics = _topic_rows(supabase, list(tag_topics.values()))

        wanted_set = set(wanted)
        # A question's subject for SCOPING purposes: section first, primary tag
        # second. Its subject for COUNTING purposes is the primary tag's only —
        # a question with no tag is untagged, whatever section it sits in.
        in_series: set[str] = set()
        counted: dict[str, tuple[str, str]] = {}  # qid → (subject_id, topic_id)
        for q in questions:
            qid = q.get("id")
            if not qid:
                continue
            topic = topics.get(tag_topics.get(qid) or "")
            tag_subject = (topic or {}).get("subject_id")
            section_subject = by_section.get(q.get("section_id") or "")
            if (tag_subject in wanted_set) or (section_subject in wanted_set):
                in_series.add(q.get("pyq_paper_id"))
            if tag_subject in wanted_set:
                counted[qid] = (tag_subject, topic["id"])

        by_paper: dict[str, dict[str, Any]] = {}
        topic_totals: dict[str, dict[str, Any]] = {}
        series_papers = [p for p in papers if p.get("id") in in_series]
        if not series_papers:
            return out

        phase_meta = _phase_names(
            supabase,
            list({p.get("exam_phase_id") for p in series_papers if p.get("exam_phase_id")}),
        )
        for p in series_papers:
            phase = phase_meta.get(p.get("exam_phase_id") or "") or {}
            meta = p.get("metadata") if isinstance(p.get("metadata"), dict) else {}
            by_paper[p["id"]] = {
                "paper_id": p["id"],
                "year": p.get("year"),
                "phase_id": p.get("exam_phase_id"),
                "phase_name": phase.get("phase_name"),
                "paper_code": p.get("paper_code"),
                # Raw operator-typed fields only; the route turns these into a
                # display label and the metadata blob itself never ships.
                "set_code": meta.get("set_code"),
                "paper_set": meta.get("paper_set"),
                "total_questions": 0,
                "tagged_questions": 0,
                "untagged_questions": 0,
                "multi_tagged_questions": 0,
                "by_subject": {sid: 0 for sid in wanted},
            }

        for q in questions:
            row = by_paper.get(q.get("pyq_paper_id") or "")
            if row is None:
                continue
            row["total_questions"] += 1
            hit = counted.get(q.get("id") or "")
            if not hit:
                row["untagged_questions"] += 1
                continue
            subject_id, topic_id = hit
            row["tagged_questions"] += 1
            row["by_subject"][subject_id] = row["by_subject"].get(subject_id, 0) + 1
            if q["id"] in multi_tagged:
                row["multi_tagged_questions"] += 1
            entry = topic_totals.setdefault(
                topic_id,
                {
                    "topic_id": topic_id,
                    "topic_name": (topics.get(topic_id) or {}).get("name"),
                    "subject_id": subject_id,
                    "total": 0,
                    "by_paper": {},
                },
            )
            entry["total"] += 1
            entry["by_paper"][row["paper_id"]] = (
                entry["by_paper"].get(row["paper_id"], 0) + 1
            )

        # Oldest first: the section reads left-to-right by year. paper_id breaks
        # ties so two papers in one year keep a stable order between reads.
        ordered_papers = sorted(
            by_paper.values(),
            key=lambda r: ((r["year"] is None), r["year"] or 0, r["paper_id"]),
        )
        ordered_topics = sorted(
            topic_totals.values(),
            key=lambda r: (-r["total"], str(r.get("topic_name") or r["topic_id"])),
        )

        present = {sid for sid in wanted if any(
            p["by_subject"].get(sid, 0) for p in ordered_papers
        )}
        subject_meta = _subject_rows(supabase, wanted)
        out["subjects"] = [
            {
                "subject_id": sid,
                "name": (subject_meta.get(sid) or {}).get("name"),
                "slug": (subject_meta.get(sid) or {}).get("slug"),
            }
            for sid in wanted
            if sid in present
        ]
        out["papers"] = ordered_papers
        out["topics"] = ordered_topics
        return out
    except Exception:  # noqa: BLE001
        logger.exception("subject composition read failed for exam %s", exam_id)
        return {
            "exam_id": exam_id,
            "verified_only": True,
            "subject_ids": list(wanted),
            "subjects": [],
            "papers": [],
            "topics": [],
            "papers_considered": 0,
        }
