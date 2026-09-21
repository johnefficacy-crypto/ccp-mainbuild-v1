#!/usr/bin/env python3
r"""Split the UPSC CSE Mains GS year-buckets into GS1..GS4 (and Essay).

THE SHAPE OF THE PROBLEM
------------------------
Thirteen `pyq_papers` rows, one per year 2013-2025, each holding a whole
Mains sitting: 80-97 questions numbered 1..N with no metadata of their own.
`paper_code` is NULL, `corpus_half` is NULL, and the bucket's `metadata.note`
is unreliable, so nothing on the paper row says which questions were GS1 and
which were GS4.

AND THE COUNTS VARY. 2013 is not 2019 is not 2023, so "questions 1-20 are GS1"
is not a rule — it is a guess that would be wrong for most years and silently
wrong for the rest. Nothing here ever splits by a number range.

WHAT DOES SAY
-------------
Three independent signals, and a question moves only when they agree:

1. THE PRIMARY TAG (assignment). `pyq_question_topic_tags` with
   `tag_role='primary'` -> `topics.subject_id` -> `subjects.slug`. The
   canonical GS subjects are `upsc-cse-mains-gs1`..`gs4` and the subject row
   IS the paper. The empty shells `upsc-mains-gs*`, `upsc-mains-essay` and
   `upsc-gs-paper-1` carry no tree and are ignored: a tag pointing into one of
   them assigns nothing.

2. THE OFFICIAL PAPER (verification). Each question's text is matched against
   the OCR of the four official papers for its year under
   `workbench/audit/ocr_cache/`. If the best match is a different paper from
   the tag's, that is a DISAGREEMENT and the bucket does not move.

3. MONOTONIC ORDER (verification). A sitting is printed in order, so walking a
   bucket by `question_number` the paper index may repeat but must never go
   DOWN. GS3 appearing between two GS4 questions means one of them is
   misassigned, whichever signal says otherwise.

An untagged question is Essay only if it matches that year's essay source;
otherwise it is UNASSIGNED, and one unassigned question aborts its bucket.

WHY SO STRICT. The GS corpus is partly fabricated
(`docs/status/2026-09-14-gs-corpus-fabrication-audit.md`): 2013 and 2014 have
almost no genuine questions, four years have no raw paper at all. A split that
guessed would give a fabricated question a real paper's provenance, which is
the one thing worse than leaving it in the bucket.

KNOWN OCR LIMITS (`workbench/audit/ocr_phase3.md`)
--------------------------------------------------
LOW-confidence extractions: 2016/2017/2018/2023/2026 GS1, 2023 GS2, 2026
Essay. 2017 GS2's year and 2023 GS2's paper label were UNREAD and taken from
their sitting-mates' paper-set codes. 2015 GS4 has no OCR at all, and 2024 and
2025 have none either — they were reconciled from DOCX, not OCR
(`workbench/audit/gs_2024_2025.md`). A year with no OCR for a paper cannot be
verified, so its bucket aborts rather than moving on the tag alone.

    export DATABASE_URL=postgresql://...
    python scripts/split_gs_buckets.py              # dry run (default)
    python scripts/split_gs_buckets.py --live       # apply
    python scripts/split_gs_buckets.py --year 2019  # one bucket
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
import sys
import unicodedata
import uuid
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
OCR_DIR = ROOT / "workbench" / "audit" / "ocr_cache"
REVIEW_CSV = ROOT / "workbench" / "audit" / "gs_split_review.csv"

EXAM_ID = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"
EXAM_PHASE_ID = "626ec667-4bbf-4420-8715-48c5b83e0d11"

#: Canonical GS subject slugs. The shells carry no tree and assign nothing.
GS_SUBJECT_SLUGS = {
    "upsc-cse-mains-gs1": 1,
    "upsc-cse-mains-gs2": 2,
    "upsc-cse-mains-gs3": 3,
    "upsc-cse-mains-gs4": 4,
}
IGNORED_SUBJECT_SLUGS = frozenset(
    {"upsc-mains-gs1", "upsc-mains-gs2", "upsc-mains-gs3", "upsc-mains-gs4",
     "upsc-mains-essay", "upsc-gs-paper-1"}
)

ESSAY = "ESSAY"

#: rapidfuzz partial_ratio at or above which an OCR hit counts as a match.
#: The audit's own reconcile used a single 85 cut; the same number is used
#: here so a question this script calls matched is a question that reconcile
#: would also have called matched.
OCR_MATCH_CUT = 85.0

#: There is deliberately no second, lower threshold. A weak hit cannot veto a
#: tag because a veto needs a hit at OCR_MATCH_CUT in the first place; the thing
#: that actually has to be excluded is the OPPOSITE case — text that matches two
#: papers at once. See `assign_question`.


class BucketAbort(Exception):
    """One bucket cannot be split. Raised before any write for that bucket."""


class ScopeAbort(Exception):
    """The selected rows are not all buckets. Aborts the WHOLE run, unwritten."""


def uuid_str(value: Any) -> Any:
    """`uuid.UUID` -> canonical string; everything else unchanged.

    asyncpg decodes uuid columns to `uuid.UUID`, which `json.dumps` cannot
    serialise, and two jsonb payloads here carry ids. Deliberately narrow: no
    `default=str`, which would also stringify a date or a Decimal that has no
    business in jsonb. Same rule as `scripts/split_optional_buckets.py`.
    """
    return str(value) if isinstance(value, uuid.UUID) else value


# ── the corpus of official papers ────────────────────────────────────────

_PHASE3_YEAR = re.compile(r"QP-CSM-(\d{2})-")
_PHASE3_PAPER = re.compile(r"PAPER\s*-?\s*(I{1,3}V?|IV)\b", re.IGNORECASE)
_ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4}


def _normalise(text: str) -> str:
    """Fold to comparable prose: accents out, whitespace collapsed, lowercased."""
    folded = unicodedata.normalize("NFKD", str(text or ""))
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", folded).strip().lower()


def load_ocr_corpus(ocr_dir: Path = OCR_DIR) -> dict[tuple[int, Any], str]:
    """(year, paper) -> normalised OCR text, from every cache location.

    `<year>_GS<n>.txt` is the phase-2 cache. `phase3_raw/` and `phase3_cover/`
    hold the later-sourced papers under their UPSC filenames, and include the
    Essay paper, which the numbered cache has no slot for. A file present in
    more than one place is read once; the longer text wins, because a cover-only
    extraction is a page, not a paper.
    """
    corpus: dict[tuple[int, Any], str] = {}

    def offer(year: int, paper: Any, text: str) -> None:
        body = _normalise(text)
        if len(body) > len(corpus.get((year, paper), "")):
            corpus[(year, paper)] = body

    if not ocr_dir.is_dir():
        return corpus

    for path in sorted(ocr_dir.glob("*.txt")):
        m = re.fullmatch(r"(\d{4})_GS([1-4])", path.stem)
        if m:
            offer(int(m.group(1)), int(m.group(2)), path.read_text(encoding="utf-8", errors="replace"))

    for sub in ("phase3_raw", "phase3_cover"):
        folder = ocr_dir / sub
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.txt")):
            ym = _PHASE3_YEAR.search(path.name)
            if not ym:
                continue
            year = 2000 + int(ym.group(1))
            text = path.read_text(encoding="utf-8", errors="replace")
            if "ESSAY" in path.name.upper():
                offer(year, ESSAY, text)
                continue
            pm = _PHASE3_PAPER.search(path.stem.replace("-", " "))
            if pm:
                roman = pm.group(1).upper()
                if roman in _ROMAN:
                    offer(year, _ROMAN[roman], text)
    return corpus


def papers_for_year(corpus: dict[tuple[int, Any], str], year: int) -> dict[Any, str]:
    return {paper: text for (y, paper), text in corpus.items() if y == year}


# ── matching ─────────────────────────────────────────────────────────────


def ocr_scores(question_text: str, papers: dict[Any, str]) -> dict[Any, float]:
    """paper -> how well this question's text matches that paper's OCR.

    EVERY paper is scored, not just the winner. The winner alone cannot tell a
    question that belongs to GS3 from a question whose wording happens to appear
    in GS3 as well as in the GS1 it came from, and that distinction is the
    difference between a real disagreement and a false one.

    `partial_ratio` because the question is a fragment of a whole paper's text.
    Empty when there is nothing to match against — a year with no OCR yields no
    evidence, which is not the same as evidence against.
    """
    needle = _normalise(question_text)
    if not needle or not papers:
        return {}
    try:
        from rapidfuzz import fuzz
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise SystemExit("rapidfuzz is required (pip install rapidfuzz)") from exc
    return {
        paper: float(fuzz.partial_ratio(needle, text))
        for paper, text in papers.items()
        if text
    }


def best_ocr_paper(
    question_text: str, papers: dict[Any, str]
) -> tuple[Any, float]:
    """(paper, score) for the official paper this question's text best matches."""
    scores = ocr_scores(question_text, papers)
    if not scores:
        return None, 0.0
    best = max(scores, key=lambda paper: (scores[paper], -paper_index(paper)))
    return best, scores[best]


def paper_index(paper: Any) -> int:
    """Sort key for the monotonic check. Essay sits after GS4."""
    if paper == ESSAY:
        return 5
    return int(paper) if isinstance(paper, int) else 99


def paper_code_for(year: int, paper: Any) -> str:
    suffix = "ESSAY" if paper == ESSAY else f"GS{paper}"
    return f"UPSC-CSE-MAINS-GS-{year}-{suffix}"


# ── planning (pure; no IO, so the rules are testable without a database) ──


def assign_question(
    question: dict[str, Any],
    *,
    tag_paper: Any,
    ocr_papers: dict[Any, str],
) -> dict[str, Any]:
    """One question's assignment and the evidence behind it.

    `tag_paper` is GS1..GS4 from the primary tag, or None when the question is
    untagged or its tag points into an empty shell.
    """
    text = question.get("question_text") or ""
    scores = ocr_scores(text, ocr_papers)
    ocr_paper, score = best_ocr_paper(text, ocr_papers)
    matched = ocr_paper if score >= OCR_MATCH_CUT else None
    tag_score = round(scores.get(tag_paper, 0.0), 1)

    if tag_paper is not None:
        method = "tag"
        assigned: Any = tag_paper
        # A disagreement is the tag's paper FAILING to match while another
        # paper matches — not merely another paper scoring higher. Whole-paper
        # `partial_ratio` matching is generous: a short, generically worded
        # question can clear the cut against two papers of the same sitting, and
        # that is ambiguous text, not evidence the tag is wrong. Vetoing on the
        # winner alone would abort every bucket containing one such question.
        disagrees = (
            matched is not None
            and matched != tag_paper
            and tag_score < OCR_MATCH_CUT
        )
    elif matched == ESSAY:
        method = "ocr_essay"
        assigned = ESSAY
        disagrees = False
    else:
        method = "unassigned"
        assigned = None
        disagrees = False

    return {
        "id": question.get("id"),
        "question_number": question.get("question_number"),
        "assigned": assigned,
        "tag_paper": tag_paper,
        "ocr_paper": ocr_paper,
        "ocr_score": round(score, 1),
        "tag_score": tag_score,
        "method": method,
        "disagrees": disagrees,
        "excerpt": re.sub(r"\s+", " ", str(text))[:60],
    }


def order_violations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rows where the paper index DROPS as question_number rises.

    A sitting is printed in order. The index may repeat — a paper has many
    questions — but a fall means two rows disagree about where the boundary is,
    and this script does not get to pick which.
    """
    ordered = sorted(
        (r for r in rows if r["assigned"] is not None and r["question_number"] is not None),
        key=lambda r: r["question_number"],
    )
    out: list[dict[str, Any]] = []
    high = 0
    for row in ordered:
        index = paper_index(row["assigned"])
        if index < high:
            out.append(row)
        else:
            high = index
    return out


def plan_bucket(
    bucket: dict[str, Any],
    questions: list[dict[str, Any]],
    *,
    tag_papers: dict[str, Any],
    corpus: dict[tuple[int, Any], str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(planned papers, per-question rows) for one year bucket.

    Raises ``BucketAbort`` on any unassigned question, any tag/OCR
    disagreement, or any order violation. Nothing is written for a bucket that
    aborts, and the review CSV records every row either way.
    """
    year = bucket.get("year")
    if year is None:
        raise BucketAbort("bucket has no year")
    if not questions:
        raise BucketAbort("bucket has no questions to split")

    ocr_papers = papers_for_year(corpus, int(year))
    rows = [
        assign_question(q, tag_paper=tag_papers.get(str(q.get("id"))), ocr_papers=ocr_papers)
        for q in questions
    ]

    unassigned = [r for r in rows if r["assigned"] is None]
    disagreements = [r for r in rows if r["disagrees"]]
    violations = order_violations(rows)
    if unassigned or disagreements or violations:
        raise BucketAbort(
            f"{len(unassigned)} unassigned, {len(disagreements)} tag/OCR "
            f"disagreement(s), {len(violations)} out-of-order — nothing written "
            f"for {year}; see {REVIEW_CSV.name}"
        )
    if not ocr_papers:
        raise BucketAbort(
            f"no OCR for {year} under {OCR_DIR.name}/, so the tags cannot be "
            "verified; refusing to move on one signal"
        )

    by_paper: dict[Any, list[dict[str, Any]]] = {}
    for row in rows:
        by_paper.setdefault(row["assigned"], []).append(row)

    planned = []
    for paper in sorted(by_paper, key=paper_index):
        members = sorted(by_paper[paper], key=lambda r: r["question_number"] or 0)
        scores = [r["ocr_score"] for r in members if r["ocr_score"] > 0]
        code = paper_code_for(int(year), paper)
        planned.append(
            {
                "paper": paper,
                "paper_code": code,
                "year": int(year),
                "question_ids": [r["id"] for r in members],
                "question_count": len(members),
                "metadata": {
                    "paper_code": code,
                    "paper_kind": "essay" if paper == ESSAY else "gs",
                    "gs_paper": ESSAY if paper == ESSAY else paper,
                    "year": int(year),
                    "split_from_bucket_id": uuid_str(bucket.get("id")),
                    "question_count": len(members),
                    "assignment_method": sorted({r["method"] for r in members}),
                    "min_ocr_score": min(scores) if scores else None,
                },
            }
        )
    return planned, rows


# ── scope ────────────────────────────────────────────────────────────────


def as_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


def scope_violation(row: dict[str, Any]) -> str | None:
    """Why this row is not an unsplit GS bucket, or None if it is.

    Named conditions first, because they are the ones that mean a previous run
    already touched this row.
    """
    meta = as_metadata(row.get("metadata"))
    if meta.get("split_from_bucket_id") is not None:
        return "carries metadata.split_from_bucket_id — already a split paper"
    if row.get("paper_code") or meta.get("paper_code"):
        return f"carries a paper_code ({row.get('paper_code') or meta.get('paper_code')})"
    if meta.get("retired") is True:
        return "retired"
    if meta.get("corpus_half") is not None:
        return f"corpus_half is {meta.get('corpus_half')!r}, not a year bucket"
    if row.get("year") is None:
        return "has no year"
    return None


def is_in_scope(row: dict[str, Any]) -> bool:
    """The Python form of ``_BUCKET_SQL``'s predicate, minus the questions test.

    Kept beside `scope_violation` so the two-run proof can select exactly what
    the query would, rather than a restatement of it that could drift.
    """
    return scope_violation(row) is None


def assert_bucket_scope(rows: Iterable[dict[str, Any]]) -> None:
    offenders = [
        f"{r.get('year') or r.get('id')}: {why}"
        for r in rows
        if (why := scope_violation(r)) is not None
    ]
    if offenders:
        raise ScopeAbort(
            f"{len(offenders)} selected row(s) are not unsplit GS buckets; "
            "nothing was written:\n    " + "\n    ".join(offenders)
        )


# ── IO ───────────────────────────────────────────────────────────────────

_BUCKET_SQL = """
select p.id, p.exam_id, p.exam_phase_id, p.exam_cycle_id, p.year,
       p.paper_code, p.metadata
  from public.pyq_papers p
 where p.exam_id = $1::uuid
   and p.exam_phase_id = $2::uuid
   and p.paper_code is null
   and p.metadata->>'paper_code' is null
   and p.metadata->>'corpus_half' is null
   and p.metadata->>'split_from_bucket_id' is null
   and coalesce((p.metadata->>'retired')::boolean, false) is not true
   and exists (select 1 from public.pyq_questions q where q.pyq_paper_id = p.id)
 order by p.year
"""

_QUESTIONS_SQL = """
select id, question_number, question_text
  from public.pyq_questions
 where pyq_paper_id = $1
 order by question_number nulls last, id
"""

#: The primary tag's subject slug, per question. tag_role='primary' only; the
#: reviewer_status is deliberately NOT filtered here, because an unreviewed tag
#: is still the corpus's own statement of which paper a question came from and
#: the OCR check is what verifies it.
_TAGS_SQL = """
select tag.question_id::text as question_id, s.slug as subject_slug
  from public.pyq_question_topic_tags tag
  join public.topics   t on t.id = tag.topic_id
  join public.subjects s on s.id = t.subject_id
  join public.pyq_questions q on q.id = tag.question_id
 where q.pyq_paper_id = $1
   and tag.tag_role = 'primary'
"""

_STIMULUS_LINK_SQL = """
select count(*)::bigint
  from public.pyq_question_stimuli qs
  join public.pyq_questions q on q.id = qs.question_id
 where q.pyq_paper_id = $1
"""

_EXISTING_SQL = """
select id, paper_code from public.pyq_papers where paper_code = any($1::text[])
"""

_INSERT_SQL = """
insert into public.pyq_papers
    (exam_id, exam_phase_id, exam_cycle_id, year, paper_code, trust_status, metadata)
values ($1, $2, $3, $4, $5, 'pending', $6::jsonb)
returning id
"""

_REPOINT_SQL = """
update public.pyq_questions
   set pyq_paper_id = $1,
       metadata = coalesce(metadata, '{}'::jsonb) || jsonb_build_object('gs_paper', $3::text)
 where id = any($2::uuid[])
"""

_RETIRE_SQL = """
update public.pyq_papers
   set metadata = metadata || jsonb_build_object('retired', true, 'split_into', $2::jsonb),
       updated_at = now()
 where id = $1
"""


def insert_args(bucket: dict[str, Any], plan: dict[str, Any]) -> tuple:
    """Positional arguments for ``_INSERT_SQL``.

    `paper_code` is set as a COLUMN, not only inside metadata:
    `pyq_papers_unique_known_uidx` covers
    (exam_id, exam_phase_id, year, paper_date, shift, paper_code) where
    exam_phase_id is not null. The four papers of one sitting share
    exam/phase/year, so the column is the only thing separating them.
    """
    return (
        bucket["exam_id"],
        bucket["exam_phase_id"],
        bucket.get("exam_cycle_id"),
        plan["year"],
        plan["paper_code"],
        json.dumps(plan["metadata"]),
    )


def retire_args(bucket: dict[str, Any], planned: list[dict[str, Any]]) -> tuple:
    """Positional arguments for ``_RETIRE_SQL``; ids stringified for jsonb."""
    return (
        bucket["id"],
        json.dumps([uuid_str(p.get("paper_id")) for p in planned]),
    )


def _tag_papers(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """question_id -> GS paper number, from the primary tag's subject slug.

    A tag into an empty shell, or a second tag disagreeing with the first,
    yields nothing for that question — it becomes unassigned, which aborts the
    bucket rather than picking a side.
    """
    seen: dict[str, Any] = {}
    conflicted: set[str] = set()
    for row in rows:
        qid = str(row.get("question_id") or "")
        slug = str(row.get("subject_slug") or "").strip().lower()
        if not qid or slug in IGNORED_SUBJECT_SLUGS:
            continue
        paper = GS_SUBJECT_SLUGS.get(slug)
        if paper is None:
            continue
        if qid in seen and seen[qid] != paper:
            conflicted.add(qid)
        seen.setdefault(qid, paper)
    for qid in conflicted:
        seen.pop(qid, None)
    return seen


async def _split_one(
    conn, bucket: dict[str, Any], *, live: bool, corpus: dict[tuple[int, Any], str]
) -> dict[str, Any]:
    bucket = {**bucket, "metadata": as_metadata(bucket.get("metadata"))}

    rows = await conn.fetch(_QUESTIONS_SQL, bucket["id"])
    questions = [dict(r) for r in rows]

    linked = await conn.fetchval(_STIMULUS_LINK_SQL, bucket["id"])
    if linked:
        raise BucketAbort(
            f"{linked} question(s) carry pyq_question_stimuli links; moving them "
            "would trip trg_pyq_questions_revalidate_paper_move (migration 223). "
            "Moving the stimuli too is out of this script's scope — reported, "
            "not patched around."
        )

    tags = _tag_papers([dict(r) for r in await conn.fetch(_TAGS_SQL, bucket["id"])])
    planned, review = plan_bucket(bucket, questions, tag_papers=tags, corpus=corpus)

    codes = [p["paper_code"] for p in planned]
    existing = {r["paper_code"]: r["id"] for r in await conn.fetch(_EXISTING_SQL, codes)}

    created, reused = [], []
    for plan in planned:
        if plan["paper_code"] in existing:
            plan["paper_id"] = existing[plan["paper_code"]]
            reused.append(plan)
            continue
        if not live:
            plan["paper_id"] = None
            created.append(plan)
            continue
        plan["paper_id"] = await conn.fetchval(_INSERT_SQL, *insert_args(bucket, plan))
        created.append(plan)

    moved = 0
    if live:
        for plan in planned:
            if plan["question_ids"] and plan["paper_id"]:
                label = ESSAY if plan["paper"] == ESSAY else str(plan["paper"])
                await conn.execute(_REPOINT_SQL, plan["paper_id"], plan["question_ids"], label)
                moved += len(plan["question_ids"])
        await conn.execute(_RETIRE_SQL, *retire_args(bucket, planned))
    else:
        moved = sum(len(p["question_ids"]) for p in planned)

    return {
        "year": bucket.get("year"),
        "bucket_id": bucket["id"],
        "planned": planned,
        "review": review,
        "created": len(created),
        "reused": len(reused),
        "moved": moved,
        "noop": not created,
    }


def _write_review(rows: list[dict[str, Any]]) -> None:
    REVIEW_CSV.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["year", "id", "number", "tag_paper", "ocr_paper",
                        "ocr_score", "tag_score", "assigned", "method",
                        "disagrees", "excerpt"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "year": row.get("year"),
                "id": uuid_str(row.get("id")),
                "number": row.get("question_number"),
                "tag_paper": row.get("tag_paper"),
                "ocr_paper": row.get("ocr_paper"),
                "ocr_score": row.get("ocr_score"),
                "tag_score": row.get("tag_score"),
                "assigned": row.get("assigned"),
                "method": row.get("method"),
                "disagrees": row.get("disagrees"),
                "excerpt": row.get("excerpt"),
            })


def summarise(year: Any, rows: list[dict[str, Any]]) -> str:
    tag = sum(1 for r in rows if r["method"] == "tag")
    agreed = sum(
        1 for r in rows
        if r["method"] == "tag" and r["ocr_paper"] == r["tag_paper"]
        and r["ocr_score"] >= OCR_MATCH_CUT
    )
    dis = sum(1 for r in rows if r["disagrees"])
    untagged = sum(1 for r in rows if r["tag_paper"] is None)
    essay = sum(1 for r in rows if r["assigned"] == ESSAY)
    return (f"  {year}: tag-assigned {tag}, OCR-agreed {agreed}, "
            f"disagreements {dis}, untagged {untagged}, essay {essay}")


async def run(*, live: bool, year: int | None) -> int:
    try:
        import asyncpg
    except ImportError:
        print("asyncpg is required (it is in app/backend/requirements.txt)", file=sys.stderr)
        return 2
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2

    corpus = load_ocr_corpus()
    if not corpus:
        print(f"no OCR cache under {OCR_DIR}", file=sys.stderr)
        return 2

    conn = await asyncpg.connect(dsn)
    review_rows: list[dict[str, Any]] = []
    total_created = total_moved = aborted = 0
    try:
        buckets = [dict(r) for r in await conn.fetch(_BUCKET_SQL, EXAM_ID, EXAM_PHASE_ID)]
        try:
            assert_bucket_scope(buckets)
        except ScopeAbort as exc:
            print(f"SCOPE ABORT — {exc}", file=sys.stderr)
            return 2

        if year is not None:
            buckets = [b for b in buckets if b.get("year") == year]
        if not buckets:
            print("No GS buckets in scope.")
            return 0

        print(f"{'DRY RUN — no writes' if not live else 'LIVE — applying'}: "
              f"{len(buckets)} bucket(s)\n")
        for bucket in buckets:
            try:
                if live:
                    async with conn.transaction():
                        out = await _split_one(conn, bucket, live=True, corpus=corpus)
                else:
                    out = await _split_one(conn, bucket, live=False, corpus=corpus)
            except BucketAbort as exc:
                aborted += 1
                # The review rows are the point of an abort, so rebuild them
                # for the CSV even though the bucket is not moving.
                print(f"  ABORT {bucket.get('year')}: {exc}\n", file=sys.stderr)
                continue

            for row in out["review"]:
                review_rows.append({**row, "year": out["year"]})
            print(summarise(out["year"], out["review"]))
            for plan in out["planned"]:
                label = "Essay" if plan["paper"] == ESSAY else f"GS{plan['paper']}"
                print(f"      {label:<6} {plan['question_count']:>4} questions  "
                      f"min OCR {plan['metadata']['min_ocr_score']}")
            total_created += out["created"]
            total_moved += out["moved"]

        if review_rows:
            _write_review(review_rows)
            print(f"\nwrote {len(review_rows)} row(s) to {REVIEW_CSV.relative_to(ROOT)}")
        print(f"\nTOTAL: {total_created} paper(s) created, {total_moved} question(s) "
              f"moved, {aborted} bucket(s) aborted")
        if not live:
            print("(dry run — re-run with --live to apply)")
        return 1 if aborted else 0
    finally:
        await conn.close()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true", help="apply changes (default: dry run)")
    ap.add_argument("--year", type=int, default=None, help="restrict to one year bucket")
    args = ap.parse_args(argv)
    return asyncio.run(run(live=args.live, year=args.year))


if __name__ == "__main__":
    sys.exit(main())
