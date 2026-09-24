#!/usr/bin/env python3
r"""Per-subject corpus readiness — what each feature can actually be built on.

READ-ONLY. This script never writes to the database and never calls a review
or promotion routine. Its only outputs are two files under ``docs/status/``.

WHY IT EXISTS
-------------
"Can we ship MCQ practice for Reasoning?" is a question about the corpus, not
about the code, and the answer moves every time a paper is imported, a topic is
re-parented or a batch is projected. Nobody could answer it without a dozen ad
hoc queries, so it got answered from memory and the memory went stale.

This reports, per subject and exam: how much corpus exists, how much has passed
review, how much is projected, and — derived from those counts, never asserted —
which features the corpus can currently support.

MODES
-----
``--from-fixture <path>``  build the report from a JSON fixture. No network, no
                           database. This is the mode the tests use, and the
                           only mode CI or an agent ever runs.
``--live``                 operator-only. Reads a live database over asyncpg
                           using ``DATABASE_URL``. Read-only queries; every one
                           paginates. Never called by CI.

THE GATE'S VERDICT IS NEVER COMPUTED HERE
-----------------------------------------
``review_pyq_paper`` is the authority, and it is PL/pgSQL (migration 271,
previously 185/186). It is a review ACTION, not a predicate: it takes row
locks, writes an ``admin_audit_logs`` row and updates ``trust_status``, and it
exposes no dry-run or check-only path. So this script never calls it — and
never re-implements or imports the Python re-statement at
``app/backend/app/api/admin_exam_intel_cms.py:1266-1298``.

Section 3's verdict is therefore always supplied, never derived:

``--live``          OBSERVED. Read back from each paper's recorded
                    ``trust_status`` — the value the gate itself wrote —
                    alongside the columns the gate reads. ``pending`` is not a
                    failure, it is the absence of a ruling, and renders as
                    "gate verdict unavailable".
``--from-fixture``  OPERATOR-SUPPLIED. A paper may carry
                    ``gate_verdict {passes, reason, source}``. A paper without
                    one has no verdict; it never defaults to passing.

Section 3 names, per exam, where its verdict came from and which migration was
in force. A gate that moves cannot silently desync this document, because this
document transcribes none of its logic.

PRIOR ART
---------
``scripts/ssc_cgl_readiness.py`` is the older per-exam version of this question
and goes far deeper on one corpus (duplicate stems, catalogue fit, per-paper
blocking fields). It re-states the gate's logic in Python — the transcription
this script refuses to make a fifth of. Read it when you need depth on a single
exam; read this one when you need breadth across subjects.

The asyncpg/DATABASE_URL shape of ``--live`` follows
``scripts/syllabus_theme_coverage.py``, the closest read-only report.

USAGE
    python scripts/corpus_readiness_report.py --from-fixture path/to.json
    export DATABASE_URL=postgresql://...
    python scripts/corpus_readiness_report.py --live --source demo
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

SCRIPT_VERSION = "1.0"

# ── Constants block ─────────────────────────────────────────────────────────
# Every threshold and predicate this report applies lives here. Nothing below
# hard-codes a number or a status string; a reviewer who disagrees with a rule
# changes it once, here.

#: A question counts as reviewed only at this status.
VERIFIED = "verified"
#: A topic tag counts only when verified AND primary — the same primary-only
#: contract the frequency pipeline uses.
PRIMARY = "primary"
#: Coverage is planner-ready, and counts toward topic mastery, only when locked.
COVERAGE_LOCKED = "locked"
#: Topic tree levels. A subject needs both layers to be navigable.
LEVEL_MACRO = "topic"
LEVEL_MICRO = "microtopic"
#: Question kinds. Descriptive questions are never projected into the mock bank.
KIND_DESCRIPTIVE = "descriptive"
#: metadata.corpus_half marking the thematic optional corpus: real questions,
#: but no paper order, so they are counted as questions and never as papers.
CORPUS_HALF_THEMATIC = "thematic"
#: Papers whose metadata.retired is truthy are excluded from every section.
META_RETIRED = "retired"
#: Provenance fields section 3 reports. These are the fields the PL/pgSQL gate
#: reads; reporting them is not the same as reporting its verdict.
PROVENANCE_SOURCE_TYPE_OFFICIAL = "official"
#: A paper the gate ruled against. Distinct from 'pending', which is no ruling.
TRUST_REJECTED = "rejected"

#: The migration that defines the provenance gate. This script does not
#: implement that gate; it records which revision was in force, so a reader can
#: tell whether a verdict predates a change to it. A fixture may override this
#: with a top-level ``gate_migration``.
GATE_MIGRATION = "271_review_pyq_paper_question_count_gate.sql"

#: Where an observed verdict came from. Never "computed" — this script computes
#: none, in either mode.
GATE_SOURCE_OBSERVED = "observed:pyq_papers.trust_status"

#: Rendered wherever a paper carries no verdict. This is not a failure; it is
#: the absence of a ruling, and it must never render as passing.
GATE_VERDICT_UNAVAILABLE = "gate verdict unavailable"

#: Feature predicates, each a pure function of one subject's counts.
#: Keep the keys stable: they are CSV column names.
FEATURES: dict[str, str] = {
    "mcq_practice": "projected > 0",
    "topic_mastery": "projected rows carrying microtopic_id AND >=1 locked coverage row",
    "answer_writing": "verified descriptive questions AND tags present",
    "syllabus_navigation": "macro AND micro layers both present",
}


def feature_flags(counts: dict[str, int]) -> dict[str, bool]:
    """Which features this subject's corpus can support. Derived, never given.

    ``counts`` is one subject's totals across every exam. Each rule is the
    minimum the feature genuinely needs, not a guess at product readiness.
    """
    return {
        "mcq_practice": counts["projected"] > 0,
        "topic_mastery": counts["projected_with_microtopic"] > 0
        and counts["locked_coverage_rows"] > 0,
        "answer_writing": counts["verified_descriptive"] > 0 and counts["tagged"] > 0,
        "syllabus_navigation": counts["macro_topics"] > 0 and counts["microtopics"] > 0,
    }


# ── The gate's verdict: read, never computed ────────────────────────────────


def observed_gate_verdict(trust_status: Any) -> dict[str, Any] | None:
    """One paper's verdict, read back from the row the gate itself wrote.

    This is an observation. ``review_pyq_paper`` sets ``trust_status``, and
    that value is the only verdict this script will ever report for a live
    read. Nothing here inspects the provenance columns to decide what the gate
    *would* say — that is the transcription this script exists to avoid.

    ``pending`` yields no verdict rather than ``passes=False``: a paper nobody
    has reviewed has not failed the gate, and collapsing the two would be the
    one lie this section cannot afford.
    """
    status = trust_status.strip().lower() if isinstance(trust_status, str) else ""
    if status == VERIFIED:
        return {"passes": True, "reason": "trust_status='verified'",
                "source": GATE_SOURCE_OBSERVED}
    if status == TRUST_REJECTED:
        return {"passes": False, "reason": "trust_status='rejected'",
                "source": GATE_SOURCE_OBSERVED}
    return None


def gate_verdict_of(paper: dict[str, Any]) -> dict[str, Any] | None:
    """The verdict attached to one paper, or ``None`` when it carries none.

    Absent, not a mapping, or missing a boolean ``passes`` all mean the same
    thing: unavailable. There is deliberately no fallback that infers a verdict
    from ``source_type`` / ``source_url`` / question counts, because that
    fallback IS the gate, re-stated a fifth time.

    ``--live`` attaches this from :func:`observed_gate_verdict`; a fixture
    supplies it directly, operator-authored.
    """
    v = paper.get("gate_verdict")
    if not isinstance(v, dict) or not isinstance(v.get("passes"), bool):
        return None
    return {
        "passes": v["passes"],
        "reason": str(v.get("reason") or "").strip(),
        "source": str(v.get("source") or "").strip() or "unspecified",
    }


# ── Pure derivation ─────────────────────────────────────────────────────────


def _meta(row: dict[str, Any]) -> dict[str, Any]:
    m = row.get("metadata")
    if isinstance(m, str):
        try:
            m = json.loads(m)
        except ValueError:
            m = {}
    return m if isinstance(m, dict) else {}


def _is_retired(row: dict[str, Any]) -> bool:
    return bool(_meta(row).get(META_RETIRED))


def _is_thematic(row: dict[str, Any]) -> bool:
    return _meta(row).get("corpus_half") == CORPUS_HALF_THEMATIC


def _is_descriptive(q: dict[str, Any]) -> bool:
    """Descriptive by explicit kind, never inferred from the absence of options."""
    kind = (q.get("question_type") or q.get("kind") or "").strip().lower()
    return kind == KIND_DESCRIPTIVE


def build_report(data: dict[str, Any]) -> dict[str, Any]:
    """The whole report as plain data. Pure: no IO, no clock, no database.

    Exclusions, applied here once and stated once in the markdown:
      * papers with truthy ``metadata.retired`` are dropped, and so is
        everything hanging off them;
      * thematic rows (``metadata.corpus_half='thematic'``) count as questions
        but never as papers — they have no paper order to count;
      * topics with ``is_active = false`` are dropped, and never appear in a
        tree count or supply a subject to a question.
    """
    subjects = {s["id"]: s for s in data.get("subjects", [])}
    exams = {e["id"]: e for e in data.get("exams", [])}

    # Topics: active only. subject_id is how every count reaches a subject —
    # never metadata.exams, which the shared body-agnostic subjects do not
    # carry and which would empty them.
    topics = {
        t["id"]: t
        for t in data.get("topics", [])
        if t.get("is_active") is not False and t.get("subject_id") in subjects
    }

    papers_all = [p for p in data.get("papers", []) if not _is_retired(p)]
    papers = {p["id"]: p for p in papers_all}
    # A thematic paper row is not a paper for counting purposes.
    countable_paper_ids = {p["id"] for p in papers_all if not _is_thematic(p)}

    questions = [
        q
        for q in data.get("questions", [])
        if q.get("pyq_paper_id") in papers  # retired buckets excluded here
    ]
    q_by_id = {q["id"]: q for q in questions}

    # Primary verified tags only; a tag to an inactive or unknown topic is
    # dropped with its topic.
    tags = [
        t
        for t in data.get("tags", [])
        if t.get("tag_role") == PRIMARY
        and t.get("reviewer_status") == VERIFIED
        and t.get("topic_id") in topics
        and t.get("question_id") in q_by_id
    ]
    subject_of_question: dict[str, str] = {}
    for t in tags:
        subject_of_question.setdefault(
            t["question_id"], topics[t["topic_id"]]["subject_id"]
        )

    projected_by_question: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in data.get("projected", []):
        qid = row.get("pyq_question_id")
        if qid in q_by_id:
            projected_by_question[qid].append(row)

    locked_topic_ids = {
        c["topic_id"]
        for c in data.get("coverage", [])
        if c.get("reviewer_status") == COVERAGE_LOCKED and c.get("topic_id") in topics
    }

    # ── section 1: subject x exam ──────────────────────────────────────────
    cells: dict[tuple[str, str], dict[str, int]] = defaultdict(
        lambda: dict(
            microtopics=0, macro_topics=0, tagged=0, verified=0,
            descriptive=0, verified_descriptive=0, projected=0,
            projected_with_microtopic=0, questions=0, papers=0,
            locked_coverage_rows=0,
        )
    )

    for q in questions:
        sid = subject_of_question.get(q["id"])
        paper = papers.get(q["pyq_paper_id"], {})
        eid = q.get("exam_id") or paper.get("exam_id")
        if sid is None or eid not in exams:
            continue  # untagged questions are counted in section 3, not here
        c = cells[(sid, eid)]
        c["questions"] += 1
        c["tagged"] += 1
        if q.get("reviewer_status") == VERIFIED:
            c["verified"] += 1
        if _is_descriptive(q):
            c["descriptive"] += 1
            if q.get("reviewer_status") == VERIFIED:
                c["verified_descriptive"] += 1
        rows = projected_by_question.get(q["id"], [])
        # Belt and braces: a descriptive question must never be counted as
        # projected even if a stray row exists for it.
        if rows and not _is_descriptive(q):
            c["projected"] += len(rows)
            c["projected_with_microtopic"] += sum(
                1 for r in rows if r.get("microtopic_id")
            )

    # Topic-tree counts attach to (subject, exam) through locked coverage where
    # it exists, and to the subject's own exam-agnostic row otherwise.
    topics_by_subject: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for t in topics.values():
        topics_by_subject[t["subject_id"]].append(t)

    coverage_exams_by_subject: dict[str, set[str]] = defaultdict(set)
    for c in data.get("coverage", []):
        tid, eid = c.get("topic_id"), c.get("exam_id")
        if tid in topics and eid in exams and c.get("reviewer_status") == COVERAGE_LOCKED:
            coverage_exams_by_subject[topics[tid]["subject_id"]].add(eid)

    # papers per exam (thematic and retired already excluded)
    papers_per_exam: dict[str, int] = defaultdict(int)
    for pid in countable_paper_ids:
        eid = papers[pid].get("exam_id")
        if eid in exams:
            papers_per_exam[eid] += 1

    for sid, tlist in topics_by_subject.items():
        macro = sum(1 for t in tlist if t.get("level") == LEVEL_MACRO)
        micro = sum(1 for t in tlist if t.get("level") == LEVEL_MICRO)
        locked = sum(1 for t in tlist if t["id"] in locked_topic_ids)
        targets = {e for (s, e) in cells if s == sid} | coverage_exams_by_subject[sid]
        for eid in targets or {""}:
            if eid:
                c = cells[(sid, eid)]
                c["microtopics"] = micro
                c["macro_topics"] = macro
                c["locked_coverage_rows"] = locked
                c["papers"] = papers_per_exam.get(eid, 0)

    rows_s1 = []
    for (sid, eid) in sorted(
        cells, key=lambda k: (subjects[k[0]]["name"].lower(), exams[k[1]]["slug"])
    ):
        c = cells[(sid, eid)]
        rows_s1.append(
            {"subject": subjects[sid]["name"], "subject_id": sid,
             "exam": exams[eid]["slug"], "exam_id": eid, **c}
        )

    # ── section 2: feature readiness per subject ───────────────────────────
    per_subject: dict[str, dict[str, int]] = {}
    for r in rows_s1:
        agg = per_subject.setdefault(
            r["subject_id"],
            dict(projected=0, projected_with_microtopic=0, locked_coverage_rows=0,
                 verified_descriptive=0, tagged=0, macro_topics=0, microtopics=0),
        )
        for k in ("projected", "projected_with_microtopic", "verified_descriptive", "tagged"):
            agg[k] += r[k]
        for k in ("locked_coverage_rows", "macro_topics", "microtopics"):
            agg[k] = max(agg[k], r[k])

    rows_s2 = [
        {"subject": subjects[sid]["name"], "subject_id": sid, **feature_flags(counts)}
        for sid, counts in sorted(per_subject.items(), key=lambda kv: subjects[kv[0]]["name"].lower())
    ]

    # ── section 3: blocked corpora — gate INPUTS, never a verdict ──────────
    blocked = []
    for eid, exam in sorted(exams.items(), key=lambda kv: kv[1]["slug"]):
        eq = [q for q in questions if (q.get("exam_id") or papers.get(q["pyq_paper_id"], {}).get("exam_id")) == eid]
        if not eq:
            continue
        unverified = sum(1 for q in eq if q.get("reviewer_status") != VERIFIED)
        untagged = sum(1 for q in eq if q["id"] not in subject_of_question)
        unprojected = sum(
            1 for q in eq if not _is_descriptive(q) and not projected_by_question.get(q["id"])
        )
        if not (unverified or untagged or unprojected):
            continue
        ep = [p for p in papers_all if p.get("exam_id") == eid and p["id"] in countable_paper_ids]
        obs = {
            "papers": len(ep),
            "not_official": sum(1 for p in ep if p.get("source_type") != PROVENANCE_SOURCE_TYPE_OFFICIAL),
            "no_source_url": sum(1 for p in ep if not (p.get("source_url") or "").strip()),
            "no_source_document_id": sum(1 for p in ep if not p.get("source_document_id")),
            "trust_pending": sum(1 for p in ep if p.get("trust_status") != VERIFIED),
            "zero_questions": sum(
                1 for p in ep if not any(q.get("pyq_paper_id") == p["id"] for q in questions)
            ),
        }
        verdicts = [gate_verdict_of(p) for p in ep]
        gate = {
            "passing": sum(1 for v in verdicts if v and v["passes"]),
            "failing": sum(1 for v in verdicts if v and not v["passes"]),
            "unavailable": sum(1 for v in verdicts if v is None),
            "sources": sorted({v["source"] for v in verdicts if v}),
            "reasons": sorted(
                {v["reason"] for v in verdicts if v and not v["passes"] and v["reason"]}
            ),
        }
        blocked.append(
            {"exam": exam["slug"], "questions": len(eq), "unverified": unverified,
             "untagged": untagged, "unprojected": unprojected, "provenance": obs,
             "gate": gate}
        )

    # ── section 4: catalogues with zero questions ──────────────────────────
    subjects_with_questions = {sid for (sid, _e) in cells}
    empty_catalogues = sorted(
        (subjects[sid]["name"] for sid in subjects if sid not in subjects_with_questions),
        key=str.lower,
    )

    # ── section 5: trees ───────────────────────────────────────────────────
    trees = []
    for sid, tlist in sorted(topics_by_subject.items(), key=lambda kv: subjects[kv[0]]["name"].lower()):
        macro = sum(1 for t in tlist if t.get("level") == LEVEL_MACRO)
        micro = sum(1 for t in tlist if t.get("level") == LEVEL_MICRO)
        trees.append({"subject": subjects[sid]["name"], "macro": macro, "micro": micro,
                      "micro_without_macro": micro > 0 and macro == 0})

    return {"section1": rows_s1, "section2": rows_s2, "section3": blocked,
            "section4": empty_catalogues, "section5": trees,
            # Recorded, not enforced: this script cannot check which revision a
            # live database actually has, so it reports what it was told.
            "gate_migration": str(data.get("gate_migration") or GATE_MIGRATION)}


# ── Rendering ───────────────────────────────────────────────────────────────

QUERIES_USED = """\
subjects        select id, name, slug from subjects
exams           select id, slug, name, is_active from exams
topics          select id, subject_id, parent_topic_id, level, is_active from topics
                  where is_active is not false
papers          select id, exam_id, trust_status, source_type, source_url,
                       source_document_id, metadata from pyq_papers
questions       select id, pyq_paper_id, exam_id, reviewer_status, question_type,
                       metadata from pyq_questions
tags            select question_id, topic_id, tag_role, reviewer_status
                  from pyq_question_topic_tags
                  where tag_role = 'primary' and reviewer_status = 'verified'
projection      select id, pyq_question_id, topic_id, microtopic_id
                  from mock_question_bank
coverage        select exam_id, topic_id, reviewer_status, exam_phase_id
                  from exam_topic_coverage
Every read paginates via app/common/pagination.py — a short page is not the
last page. No statement in this script writes, and none calls a review RPC.
The gate verdict in section 3 is READ from pyq_papers.trust_status (--live) or
supplied per paper by the fixture; it is never computed from the columns above.\
"""


# A generated doc is read by people; "1 have no source_url" reads as a bug in
# the report rather than a fact about the corpus.
def _plural(n: int, word: str) -> str:
    return word if n == 1 else word + "s"


def _is_are(n: int) -> str:
    return "is" if n == 1 else "are"


def _has_have(n: int) -> str:
    return "has" if n == 1 else "have"


def _carry(n: int) -> str:
    return "carries" if n == 1 else "carry"


def render_markdown(report: dict[str, Any], *, generated_at: str, mode: str,
                    source: str, seed: bool = False) -> str:
    o: list[str] = []
    w = o.append
    w("# Corpus readiness")
    w("")
    if seed:
        w("> **Example output — fixture data, not live counts.** Every number below"
          " comes from a committed test fixture. An operator regenerates this file"
          " against a real database with"
          " `python scripts/corpus_readiness_report.py --live --source demo`.")
        w("")
    w(f"- generated-at: {generated_at}")
    w(f"- mode: {mode}")
    w(f"- source: {source}")
    w(f"- script version: {SCRIPT_VERSION}")
    w("")
    w("<details><summary>Exact queries used</summary>")
    w("")
    w("```sql")
    w(QUERIES_USED)
    w("```")
    w("")
    w("</details>")
    w("")
    w("**Exclusions, applied in every section below.** Retired buckets"
      " (`metadata.retired` truthy) are dropped along with everything hanging off"
      " them. Thematic optional rows (`metadata.corpus_half='thematic'`) are"
      " counted as questions but never as papers — they carry no paper order."
      " Topics with `is_active = false` are dropped, and never supply a subject"
      " to a question. Subjects reach their counts through `topics.subject_id`,"
      " never through `metadata.exams`: the shared body-agnostic subjects do not"
      " carry that key and any exam filter would empty them.")
    w("")

    w("## 1. Corpus per subject × exam")
    w("")
    w("| subject | exam | micro | macro | tagged | verified | descriptive | projected |")
    w("|---|---|---:|---:|---:|---:|---:|---:|")
    for r in report["section1"]:
        w(f"| {r['subject']} | {r['exam']} | {r['microtopics']} | {r['macro_topics']} |"
          f" {r['tagged']} | {r['verified']} | {r['descriptive']} | {r['projected']} |")
    if not report["section1"]:
        w("| _none_ | | | | | | | |")
    w("")

    w("## 2. Feature readiness per subject")
    w("")
    w("Derived from the counts in section 1, never asserted. The rule for each"
      " column, in one line:")
    w("")
    for name, rule in FEATURES.items():
        w(f"- `{name}` — {rule}")
    w("")
    w("| subject | " + " | ".join(FEATURES) + " |")
    w("|---" * (len(FEATURES) + 1) + "|")
    for r in report["section2"]:
        w(f"| {r['subject']} | " + " | ".join("yes" if r[f] else "no" for f in FEATURES) + " |")
    if not report["section2"]:
        w("| _none_ |" + " |" * len(FEATURES))
    w("")

    w("## 3. Blocked corpora")
    w("")
    mig = report["gate_migration"]
    w("**This section never computes the gate's verdict.** `review_pyq_paper` is"
      " the authority, and it is PL/pgSQL (migration"
      f" `{mig}`, previously 185/186). It is a review action rather than a"
      " predicate — it locks rows, writes an audit row and updates"
      " `trust_status` — and it offers no dry-run path, so this report does not"
      " call it. Nor does it re-implement the Python re-statement at"
      " `admin_exam_intel_cms.py:1266-1298`.")
    w("")
    w("So what follows is the observable provenance fields the gate reads, plus a"
      " verdict that was **observed or operator-supplied, never derived here**."
      " Each exam names its own source below. A paper carrying no verdict is"
      f" reported as \"{GATE_VERDICT_UNAVAILABLE}\" — never as passing. A gate"
      " that moves cannot silently desync this document, because this document"
      " transcribes none of its logic.")
    w("")
    w("`scripts/ssc_cgl_readiness.py` is the older single-exam report over this"
      " same ground for SSC CGL; it does re-state the gate in Python, and this"
      " report deliberately does not.")
    w("")
    for b in report["section3"]:
        w(f"### {b['exam']}")
        w("")
        w(f"- {b['questions']} questions exist; {b['unverified']} are not verified,"
          f" {b['untagged']} carry no verified primary tag,"
          f" {b['unprojected']} objective questions are not projected.")
        p = b["provenance"]
        w(f"- {p['papers']} {_plural(p['papers'], 'paper')} in scope."
          f" Observed provenance fields:"
          f" {p['not_official']} {_is_are(p['not_official'])} not"
          f" `source_type='official'`;"
          f" {p['no_source_url']} {_has_have(p['no_source_url'])} no `source_url`;"
          f" {p['no_source_document_id']}"
          f" {_has_have(p['no_source_document_id'])} no `source_document_id`;"
          f" {p['trust_pending']} {_is_are(p['trust_pending'])} not"
          f" `trust_status='verified'`;"
          f" {p['zero_questions']} {_carry(p['zero_questions'])} no questions.")
        g = b["gate"]
        if g["passing"] or g["failing"]:
            line = (f"- Gate verdict, migration `{mig}` in force:"
                    f" {g['passing']} passing, {g['failing']} failing,"
                    f" {g['unavailable']} unavailable."
                    f" Source: {', '.join(f'`{x}`' for x in g['sources'])}."
                    " Observed or supplied — not computed by this report.")
            if g["reasons"]:
                line += " Recorded reasons: " + "; ".join(g["reasons"]) + "."
            w(line)
        else:
            w(f"- Gate verdict, migration `{mig}` in force:"
              f" {GATE_VERDICT_UNAVAILABLE} for all {p['papers']}"
              f" {_plural(p['papers'], 'paper')} — none was observed or supplied.")
        w("")
    if not report["section3"]:
        w("_No exam has unverified, untagged or unprojected questions._")
        w("")

    w("## 4. Catalogues with zero questions")
    w("")
    if report["section4"]:
        for name in report["section4"]:
            w(f"- {name}")
    else:
        w("_None._")
    w("")

    w("## 5. Topic trees")
    w("")
    w("| subject | macro | micro | micro without a macro layer |")
    w("|---|---:|---:|---|")
    for t in report["section5"]:
        w(f"| {t['subject']} | {t['macro']} | {t['micro']} |"
          f" {'**yes**' if t['micro_without_macro'] else 'no'} |")
    if not report["section5"]:
        w("| _none_ | | | |")
    w("")
    return "\n".join(o) + "\n"


CSV_COLUMNS = [
    "subject", "exam", "microtopics", "macro_topics", "tagged", "verified",
    "descriptive", "projected", *FEATURES,
]


def render_csv(report: dict[str, Any]) -> str:
    flags = {r["subject_id"]: r for r in report["section2"]}
    buf = io.StringIO()
    # newline="" semantics: force \n so the file is byte-identical on any OS.
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for r in report["section1"]:
        f = flags.get(r["subject_id"], {})
        writer.writerow({
            **{k: r[k] for k in CSV_COLUMNS if k in r},
            **{name: str(bool(f.get(name))).lower() for name in FEATURES},
        })
    return buf.getvalue()


# ── IO ──────────────────────────────────────────────────────────────────────

MD_PATH = Path("docs/status/corpus-readiness.md")
CSV_PATH = Path("docs/status/corpus-readiness.csv")


def _write(md: str, csv_text: str, out_dir: Path) -> tuple[Path, Path]:
    md_path, csv_path = out_dir / MD_PATH.name, out_dir / CSV_PATH.name
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8", newline="\n")
    csv_path.write_text(csv_text, encoding="utf-8", newline="\n")
    return md_path, csv_path


async def _run_live(source: str) -> dict[str, Any]:  # pragma: no cover - operator only
    """Read every input over asyncpg. Read-only; paginated; never called by CI."""
    try:
        import asyncpg
    except ImportError:
        print("asyncpg is required (it is in app/backend/requirements.txt)", file=sys.stderr)
        raise SystemExit(2)
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr)
        raise SystemExit(2)

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app" / "backend"))
    from app.common.pagination import PAGE  # noqa: PLC0415 — operator path only

    conn = await asyncpg.connect(dsn)
    try:
        async def page_all(sql: str) -> list[dict[str, Any]]:
            """Walk one relation in PAGE-sized slices, ordered by id.

            A short page is NOT the last page: the loop stops only on an empty
            one, so a page trimmed by a server-side row cap cannot truncate the
            report silently.
            """
            out: list[dict[str, Any]] = []
            offset = 0
            while True:
                rows = await conn.fetch(f"{sql} order by 1 limit {PAGE} offset {offset}")
                if not rows:
                    break
                out.extend(dict(r) for r in rows)
                offset += PAGE
            return out

        papers = await page_all(
            "select id, exam_id, trust_status, source_type, source_url,"
            " source_document_id, metadata from public.pyq_papers")
        for row in papers:
            # OBSERVED, not computed: the gate wrote trust_status; this reads it
            # back. No provenance column is inspected to guess a verdict.
            row["gate_verdict"] = observed_gate_verdict(row.get("trust_status"))

        return {
            "source": source,
            "subjects": await page_all("select id, name, slug from public.subjects"),
            "exams": await page_all("select id, slug, name, is_active from public.exams"),
            "topics": await page_all(
                "select id, subject_id, parent_topic_id, level, is_active from public.topics"
                " where is_active is not false"),
            "papers": papers,
            "questions": await page_all(
                "select id, pyq_paper_id, exam_id, reviewer_status, question_type,"
                " metadata from public.pyq_questions"),
            "tags": await page_all(
                "select question_id, topic_id, tag_role, reviewer_status"
                " from public.pyq_question_topic_tags"),
            "projected": await page_all(
                "select id, pyq_question_id, topic_id, microtopic_id"
                " from public.mock_question_bank"),
            "coverage": await page_all(
                "select exam_id, topic_id, reviewer_status, exam_phase_id"
                " from public.exam_topic_coverage"),
        }
    finally:
        await conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--from-fixture", metavar="PATH",
                   help="build from a JSON fixture; no network, no database")
    g.add_argument("--live", action="store_true",
                   help="operator-only: read a live database over DATABASE_URL")
    ap.add_argument("--source", default=None, help="demo | prod (labels the header)")
    ap.add_argument("--generated-at", default=None,
                   help="UTC date for the header; defaults to the fixture's own value")
    ap.add_argument("--out-dir", default=str(MD_PATH.parent))
    ap.add_argument("--seed", action="store_true",
                   help="mark the output as example fixture data, not live counts")
    args = ap.parse_args(argv)

    if args.live:
        data = asyncio.run(_run_live(args.source or "prod"))
        mode, source = "live", args.source or "prod"
        generated_at = args.generated_at or ""
    else:
        data = json.loads(Path(args.from_fixture).read_text(encoding="utf-8"))
        mode = "fixture"
        source = args.source or data.get("source") or "fixture"
        generated_at = args.generated_at or data.get("generated_at") or ""

    report = build_report(data)
    md = render_markdown(report, generated_at=generated_at, mode=mode,
                         source=source, seed=args.seed)
    md_path, csv_path = _write(md, render_csv(report), Path(args.out_dir))
    print(f"wrote {md_path}")
    print(f"wrote {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
