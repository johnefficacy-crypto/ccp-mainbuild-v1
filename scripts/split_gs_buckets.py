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

3. MONOTONIC ORDER (a WARNING, not a veto). A sitting is printed in order, so
   walking a bucket by `question_number` the paper index may repeat but should
   not go DOWN. On the real corpus it does, in many years — the first dry run
   rejected up to 51 rows in a bucket whose tags the OCR agreed with, against
   29 disagreements in the entire corpus. An assumption that fires that often
   against evidence that agrees is the assumption that is wrong, so the drop is
   recorded in the review sheet and does not stop the bucket.

THE ESSAY PAPER IS TAGGED IN A DIFFERENT TABLE. Essay questions carry no GS
topic tag — they are not GS topics — so the first pass read all 100 of them as
untagged and every one of the thirteen buckets aborted. Their tag was never
missing: it is in `essay_pyq_tags`, which IS the statement "this is an Essay
question". A question with no GS primary tag and a row there is Essay; the
essay OCR verifies it for 2026, the one year that has an essay page. Anything
still unplaced is UNASSIGNED, and one unassigned question aborts its bucket.

A HUMAN CAN OVERRULE ALL OF IT. `workbench/audit/gs_split_overrides.csv`
(question_id, paper, reason) places a question by hand, wins over every signal,
and is recorded as `assignment_method='override'` so the row says how it was
decided.

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
#: How much of a question the review CSV carries. Enough to recognise it
#: without opening the database.
REVIEW_EXCERPT_CHARS = 80

OCR_MATCH_CUT = 85.0

#: There is deliberately no second, lower threshold. A weak hit cannot veto a
#: tag because a veto needs a hit at OCR_MATCH_CUT in the first place; the thing
#: that actually has to be excluded is the OPPOSITE case — text that matches two
#: papers at once. See `assign_question`.


class BucketAbort(Exception):
    """One bucket cannot be split. Raised before any write for that bucket.

    CARRIES ITS REVIEW ROWS. The rows are the entire point of an abort — they
    are what a human uses to fix the bucket — and the caller only ever saw them
    on the success path, so a run where every bucket aborted wrote an empty
    CSV. The evidence is attached to the refusal rather than left behind it.
    """

    def __init__(self, message: str, rows: list[dict[str, Any]] | None = None):
        super().__init__(message)
        self.rows = rows or []


#: A human's decision about one question, read from
#: `workbench/audit/gs_split_overrides.csv`. This is the escape hatch for the
#: cases the three signals cannot settle: someone reads the paper, writes the
#: answer down, and the script stops arguing.
OVERRIDES_CSV = ROOT / "workbench" / "audit" / "gs_split_overrides.csv"

#: The DOCX reconciliation of 2024 and 2025 — the one independent statement of
#: which paper those questions came from. Those two years have no OCR at all
#: (`workbench/audit/gs_2024_2025.md`), so without this they are tag-only; with
#: it they have a real second signal, just not an optical one.
VERDICT_CSV = ROOT / "workbench" / "audit" / "gs_2024_2025_verdict.csv"

#: A verdict that CORROBORATES the source file's paper claim. `unverifiable`
#: (2024 GS4, no raw DOCX) and `orphan` say the text was not matched, so the
#: paper is the source file's word alone — which is what the tag already is,
#: and one claim repeated twice is not two signals.
CORROBORATING_VERDICTS = frozenset({"exact", "variant"})

#: Below this share of tag/verification agreement, a year is not verified in
#: any meaningful sense and the script refuses it unless a human names it.
TAG_ONLY_CUT = 0.50


class ScopeAbort(Exception):
    """The selected rows are not all buckets. Aborts the WHOLE run, unwritten."""


def load_overrides(path: Path = OVERRIDES_CSV) -> dict[str, Any]:
    """question_id -> paper, from the human override sheet.

    Columns: `question_id`, `paper` (GS1..GS4 or ESSAY), `reason`. The reason
    is not read by the script — it is there so the next person to open the file
    knows why the row is in it, which is the only thing that makes an override
    sheet safe to keep.

    A missing file is the normal case and is not an error. A row naming a paper
    outside the vocabulary is refused loudly rather than silently ignored: a
    typo in an override is a human decision that did not happen.
    """
    out: dict[str, Any] = {}
    if not path.is_file():
        return out
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        for line_no, row in enumerate(csv.DictReader(fh), start=2):
            qid = str(row.get("question_id") or "").strip()
            raw = str(row.get("paper") or "").strip().upper()
            if not qid:
                continue
            if raw == ESSAY:
                out[qid] = ESSAY
                continue
            m = re.fullmatch(r"GS([1-4])", raw)
            if not m:
                raise ScopeAbort(
                    f"{path.name} line {line_no}: paper {raw!r} is not one of "
                    "GS1, GS2, GS3, GS4, ESSAY"
                )
            out[qid] = int(m.group(1))
    return out


def load_verdict_papers(path: Path = VERDICT_CSV) -> dict[tuple[int, int], Any]:
    """(year, question_number) -> the paper the DOCX reconciliation places it on.

    Only corroborated rows. `global_number` is not unique — a question with
    sub-parts shares one — but every duplicate resolves to the SAME paper, so
    the mapping is well defined even though it is not injective. That is
    checked here rather than assumed: a global number claimed by two papers
    would mean the reconciliation disagrees with itself, and this must not
    quietly pick one.
    """
    out: dict[tuple[int, int], Any] = {}
    if not path.is_file():
        return out
    claims: dict[tuple[int, int], set[str]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if str(row.get("verdict") or "").strip() not in CORROBORATING_VERDICTS:
                continue
            year = _as_int(row.get("year"))
            number = _as_int(row.get("global_number"))
            paper = str(row.get("paper") or "").strip().upper()
            if year is None or number is None or not paper:
                continue
            claims.setdefault((year, number), set()).add(paper)
    for key, papers in claims.items():
        if len(papers) > 1:
            raise ScopeAbort(
                f"{path.name}: {key[0]} question {key[1]} is claimed by "
                f"{', '.join(sorted(papers))} — the reconciliation disagrees "
                "with itself and cannot verify anything"
            )
        name = next(iter(papers))
        if name == ESSAY:
            out[key] = ESSAY
            continue
        m = re.fullmatch(r"GS([1-4])", name)
        if m:
            out[key] = int(m.group(1))
    return out


def _as_int(value: Any) -> int | None:
    """Best-effort int, for CSV cells and database columns alike."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def agreement_rate(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """(agreed, checkable) over the TAG-PLACED rows a verification signal reached.

    The denominator is rows the signal actually covered, not every row: a year
    whose OCR failed to extract has no opinion about most of its questions, and
    counting those as disagreement would read as evidence against the tags when
    it is only an absence of evidence.

    Only rows that HAVE a tag count, because the question this rate answers is
    whether the second signal corroborates the TAGS. An override is a human
    contradicting the signals on purpose — counting the 27 of them as
    disagreement would drive a year below the bar for the very reason a human
    already fixed it.
    """
    checkable = [
        r for r in rows
        if r.get("tag_paper") is not None and r.get("verified_against") is not None
    ]
    agreed = sum(1 for r in checkable if r["verified_against"] == r["tag_paper"])
    return agreed, len(checkable)


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
    has_essay_tag: bool = False,
    override: Any = None,
    verdict_paper: Any = None,
) -> dict[str, Any]:
    """One question's assignment and the evidence behind it.

    `tag_paper` is GS1..GS4 from the primary tag, or None when the question is
    untagged or its tag points into an empty shell.

    `has_essay_tag` is whether the question has a row in `essay_pyq_tags`. THE
    ESSAY PAPER IS TAGGED IN A DIFFERENT TABLE. Essay questions carry no GS
    topic tag — they are not GS topics — so the first pass read all 100 of them
    as untagged and every bucket aborted. Their tag exists; it is in the Essay
    taxonomy, which is exactly the statement "this is an Essay question".

    `override` is a human's decision and beats every signal below it.

    `verdict_paper` is the DOCX reconciliation's placement, used INSTEAD of OCR
    where it exists. 2024 and 2025 have no OCR at all, so it is the only second
    signal those two years have; where both exist the OCR is the one on disk
    for that year and the verdict file covers no other year, so they never
    compete.
    """
    text = question.get("question_text") or ""
    scores = ocr_scores(text, ocr_papers)
    ocr_paper, score = best_ocr_paper(text, ocr_papers)
    matched = ocr_paper if score >= OCR_MATCH_CUT else None
    tag_score = round(scores.get(tag_paper, 0.0), 1)

    # THE VERIFICATION SIGNAL, whichever exists for this year. `verified_against`
    # is what the second signal says the paper is, or None when it has no
    # opinion — which is different from saying the tag is wrong.
    if verdict_paper is not None:
        verified_against: Any = verdict_paper
    else:
        verified_against = matched

    if override is not None:
        method = "override"
        assigned: Any = override
        disagrees = False
    elif tag_paper is not None:
        method = "tag"
        assigned = tag_paper
        # A disagreement is the tag's paper FAILING to match while another
        # paper matches — not merely another paper scoring higher. Whole-paper
        # `partial_ratio` matching is generous: a short, generically worded
        # question can clear the cut against two papers of the same sitting, and
        # that is ambiguous text, not evidence the tag is wrong. Vetoing on the
        # winner alone would abort every bucket containing one such question.
        if verdict_paper is not None:
            # The reconciliation matched this question's text against the
            # official DOCX for the paper it names. There is no "the wording
            # also appears elsewhere" escape here, because it did not score the
            # other papers — it either placed the question or said it could not.
            disagrees = verdict_paper != tag_paper
        else:
            disagrees = (
                matched is not None
                and matched != tag_paper
                and tag_score < OCR_MATCH_CUT
            )
    elif has_essay_tag:
        method = "essay_tag"
        assigned = ESSAY
        # The essay OCR verifies where it exists — which is 2026 alone. A GS
        # page matching this text while the essay page does not is the same
        # disagreement the tag path refuses on; everywhere else there is no
        # essay page to check against, and an absent page is not evidence.
        essay_score = round(scores.get(ESSAY, 0.0), 1)
        disagrees = (
            ESSAY in ocr_papers
            and matched is not None
            and matched != ESSAY
            and essay_score < OCR_MATCH_CUT
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
        "verified_against": verified_against,
        "disagrees": disagrees,
        "has_essay_tag": bool(has_essay_tag),
        "excerpt": re.sub(r"\s+", " ", str(text))[:REVIEW_EXCERPT_CHARS],
    }


def order_violations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rows where the paper index DROPS as question_number rises.

    A WARNING, NOT A REFUSAL — which is a correction. The rule assumed a
    bucket's `question_number` runs in printed paper order; on the real corpus
    it does not, in many years, and the check was rejecting up to 51 rows in a
    bucket whose tags the OCR agreed with. An assumption that fires 51 times
    against evidence that agrees 29-out-of-1200 times is the assumption that is
    wrong.

    So the drop is still computed and still written to the review CSV — a real
    boundary error would show here — but it no longer stops a bucket. Only an
    unassigned question or a tag/OCR disagreement does.
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
    essay_tagged: set[str] | None = None,
    overrides: dict[str, Any] | None = None,
    verdict_papers: dict[tuple[int, int], Any] | None = None,
    tag_only_years: frozenset[int] = frozenset(),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(planned papers, per-question rows) for one year bucket.

    Raises ``BucketAbort`` on any unassigned question or any tag/OCR
    disagreement, WITH the review rows attached to the exception. An
    out-of-order row is a warning: it is written to the review CSV and does not
    stop the bucket — see `order_violations`.
    """
    year = bucket.get("year")
    if year is None:
        raise BucketAbort("bucket has no year")
    if not questions:
        raise BucketAbort("bucket has no questions to split")

    essay_tagged = essay_tagged or set()
    overrides = overrides or {}
    verdict_papers = verdict_papers or {}
    ocr_papers = papers_for_year(corpus, int(year))
    rows = [
        assign_question(
            q,
            tag_paper=tag_papers.get(str(q.get("id"))),
            ocr_papers=ocr_papers,
            has_essay_tag=str(q.get("id")) in essay_tagged,
            override=overrides.get(str(q.get("id"))),
            verdict_paper=verdict_papers.get(
                (int(year), _as_int(q.get("question_number")) or -1)
            ),
        )
        for q in questions
    ]

    # THE TAG-ONLY RULE, one rule for every year. When the second signal agrees
    # with the tags less than half the time it is not verifying them — 2013
    # agreed on 1 of 93 — and calling such a year "verified" is the lie this
    # rule exists to stop. The year can still be split, but only when a human
    # has named it, and its questions are stamped `tag_only` so the row says
    # the tag was the only thing that placed it.
    agreed, checkable = agreement_rate(rows)
    rate = (agreed / checkable) if checkable else 0.0
    tag_only = checkable == 0 or rate < TAG_ONLY_CUT
    if tag_only and int(year) not in tag_only_years:
        raise BucketAbort(
            f"{year}: the verification signal agrees with the tags on "
            f"{agreed}/{checkable} questions"
            + (f" ({rate:.0%})" if checkable else " (nothing to check against)")
            + f" — below the {TAG_ONLY_CUT:.0%} bar, so this year is tag-only. "
            f"Re-run with --tag-only-years {year} to split it on the tags "
            "alone; its questions will be stamped 'tag_only'.",
            rows=rows,
        )
    if tag_only:
        for row in rows:
            if row["method"] == "tag":
                row["method"] = "tag_only"

    unassigned = [r for r in rows if r["assigned"] is None]
    disagreements = [r for r in rows if r["disagrees"]]
    violations = order_violations(rows)
    out_of_order = {id(r) for r in violations}
    for row in rows:
        row["reason"] = (
            "unassigned" if row["assigned"] is None
            else "disagreement" if row["disagrees"]
            else "order_warning" if id(row) in out_of_order
            else ""
        )

    if unassigned or disagreements:
        raise BucketAbort(
            f"{len(unassigned)} unassigned, {len(disagreements)} tag/OCR "
            f"disagreement(s) — nothing written for {year}; see "
            f"{REVIEW_CSV.name} ({len(violations)} out-of-order warning(s) "
            "recorded, not blocking)",
            rows=rows,
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
                # Parallel to `question_ids`, and zipped with it by the UPDATE.
                "methods": [r["method"] for r in members],
                # None where nothing scored it — 2024 and 2025 have no OCR at
                # all, and a 0.0 there would read as "scored, and scored zero".
                "ocr_scores": [
                    (r["ocr_score"] if r["ocr_score"] > 0 else None) for r in members
                ],
                "question_count": len(members),
                "metadata": {
                    "paper_code": code,
                    "paper_kind": "essay" if paper == ESSAY else "gs",
                    "gs_paper": ESSAY if paper == ESSAY else paper,
                    "year": int(year),
                    "split_from_bucket_id": uuid_str(bucket.get("id")),
                    "question_count": len(members),
                    # 'override' appears here when a human placed any of this
                    # paper's questions by hand, so the row says how it was
                    # decided rather than implying the signals agreed.
                    "assignment_method": sorted({r["method"] for r in members}),
                    "min_ocr_score": min(scores) if scores else None,
                },
            }
        )
    for row in rows:
        row["_agreed"] = agreed
        row["_checkable"] = checkable
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

#: Which of this bucket's questions are tagged in the ESSAY taxonomy. No
#: reviewer_status filter, for the same reason the GS tag read has none: the
#: tag's existence is the corpus's own statement that this is an Essay
#: question, and the OCR is what verifies it where a page exists.
_ESSAY_TAGS_SQL = """
select distinct t.question_id::text as question_id
  from public.essay_pyq_tags t
  join public.pyq_questions q on q.id = t.question_id
 where q.pyq_paper_id = $1
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

#: THE STAMP. The previous version wrote `gs_paper` and nothing else, so a
#: moved question said which paper it was on and not how that was decided — and
#: the 27 operator overrides became invisible the moment they were applied.
#: `assignment_method` lived only on the PAPER's metadata, where it is a set
#: over the whole paper and cannot answer "why is THIS question here".
#:
#: Per-question values arrive as parallel arrays and are zipped by `unnest`, so
#: this is still one statement per paper rather than one per question.
#: `jsonb_strip_nulls` drops `ocr_score` when nothing scored it: a null there
#: would claim a measurement that was never made.
_REPOINT_SQL = """
update public.pyq_questions q
   set pyq_paper_id = $1,
       metadata = coalesce(q.metadata, '{}'::jsonb) || jsonb_strip_nulls(
         jsonb_build_object(
           'gs_paper', $2::text,
           'assignment_method', s.method,
           'ocr_score', s.score
         ))
  from unnest($3::uuid[], $4::text[], $5::float8[]) as s(id, method, score)
 where q.id = s.id
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
    conn,
    bucket: dict[str, Any],
    *,
    live: bool,
    corpus: dict[tuple[int, Any], str],
    overrides: dict[str, Any] | None = None,
    verdict_papers: dict[tuple[int, int], Any] | None = None,
    tag_only_years: frozenset[int] = frozenset(),
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
    essay_tagged = {
        str(r["question_id"])
        for r in await conn.fetch(_ESSAY_TAGS_SQL, bucket["id"])
    }
    planned, review = plan_bucket(
        bucket, questions, tag_papers=tags, corpus=corpus,
        essay_tagged=essay_tagged, overrides=overrides,
        verdict_papers=verdict_papers, tag_only_years=tag_only_years,
    )

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
                await conn.execute(
                    _REPOINT_SQL,
                    plan["paper_id"],
                    label,
                    plan["question_ids"],
                    plan["methods"],
                    plan["ocr_scores"],
                )
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
    """The review sheet. Written on EVERY run, including a dry run.

    A dry run that refuses every bucket and writes nothing has told the
    operator that something is wrong and given them no way to see what — which
    is what happened: 13 aborts, 0 rows on disk. It is also written when there
    is nothing to report, because a stale file from a previous run is worse
    than an empty one.
    """
    REVIEW_CSV.parent.mkdir(parents=True, exist_ok=True)
    with REVIEW_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["year", "question_id", "question_number", "tag_paper",
                        "ocr_paper", "ocr_score", "method", "verified_against",
                        "reason", "excerpt"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "year": row.get("year"),
                "question_id": uuid_str(row.get("id")),
                "question_number": row.get("question_number"),
                "tag_paper": row.get("tag_paper"),
                "ocr_paper": row.get("ocr_paper"),
                "ocr_score": row.get("ocr_score"),
                # The stamp this row will carry, and what the second signal
                # said — the two columns that make a disagreement readable
                # without opening the database.
                "method": row.get("method"),
                "verified_against": row.get("verified_against"),
                "reason": row.get("reason") or "",
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
    # Broken out because it is the rule that unblocked the corpus: how many of
    # this year's Essay questions were placed by essay_pyq_tags rather than by
    # an OCR page that, for twelve of the thirteen years, does not exist.
    essay_tagged = sum(1 for r in rows if r["method"] == "essay_tag")
    overridden = sum(1 for r in rows if r["method"] == "override")
    unassigned = sum(1 for r in rows if r["assigned"] is None)
    warnings = sum(1 for r in rows if r.get("reason") == "order_warning")
    tag_only = sum(1 for r in rows if r["method"] == "tag_only")
    checkable = rows[0].get("_checkable", 0) if rows else 0
    verified = rows[0].get("_agreed", 0) if rows else 0
    rate = f"{verified}/{checkable}" + (
        f" = {verified / checkable:.0%}" if checkable else " (nothing to check)"
    )
    bits = [
        f"  {year}: agreement {rate}; tag-assigned {tag}, OCR-agreed {agreed}, "
        f"disagreements {dis}, untagged {untagged}, essay {essay} "
        f"({essay_tagged} via essay_pyq_tags), unassigned {unassigned}"
    ]
    if tag_only:
        bits.append(f", TAG-ONLY {tag_only}")
    if overridden:
        bits.append(f", overrides {overridden}")
    if warnings:
        bits.append(f", out-of-order warnings {warnings}")
    return "".join(bits)


async def run(
    *, live: bool, year: int | None, tag_only_years: frozenset[int] = frozenset()
) -> int:
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

    try:
        verdict_papers = load_verdict_papers()
    except ScopeAbort as exc:
        print(f"VERDICT SHEET — {exc}", file=sys.stderr)
        return 2
    if verdict_papers:
        years = sorted({y for y, _ in verdict_papers})
        print(f"{len(verdict_papers)} corroborated placement(s) from "
              f"{VERDICT_CSV.name} for {', '.join(str(y) for y in years)} "
              "— used instead of OCR for those years\n")

    try:
        overrides = load_overrides()
    except ScopeAbort as exc:
        print(f"OVERRIDE SHEET — {exc}", file=sys.stderr)
        return 2
    if overrides:
        print(f"{len(overrides)} human override(s) from {OVERRIDES_CSV.name}\n")

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
                        out = await _split_one(
                            conn, bucket, live=True, corpus=corpus,
                            overrides=overrides, verdict_papers=verdict_papers,
                            tag_only_years=tag_only_years)
                else:
                    out = await _split_one(
                        conn, bucket, live=False, corpus=corpus,
                        overrides=overrides, verdict_papers=verdict_papers,
                        tag_only_years=tag_only_years)
            except BucketAbort as exc:
                aborted += 1
                # THE ROWS ARE THE POINT OF AN ABORT. They ride on the
                # exception, so a run where every bucket refuses still leaves
                # the operator the sheet that says why.
                for row in exc.rows:
                    review_rows.append({**row, "year": bucket.get("year")})
                # The agreement rate is printed for EVERY year, refused or
                # not. A bucket that aborts on disagreements is exactly the
                # one whose rate the operator needs to decide what to do next.
                agreed, checkable = agreement_rate(exc.rows)
                rate = f"{agreed}/{checkable}" + (
                    f" = {agreed / checkable:.0%}" if checkable
                    else " (nothing to check)"
                )
                print(f"  ABORT {bucket.get('year')} [agreement {rate}]: {exc}\n",
                      file=sys.stderr)
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

        # Always, including an empty result: a stale sheet from a previous run
        # is worse than one that says there is nothing to review.
        _write_review(review_rows)
        print(f"\nwrote {len(review_rows)} row(s) to {REVIEW_CSV.relative_to(ROOT)}")
        flagged = sum(1 for r in review_rows if r.get("reason"))
        if flagged:
            print(f"  of which {flagged} flagged "
                  f"({sum(1 for r in review_rows if r.get('reason') == 'unassigned')} "
                  "unassigned, "
                  f"{sum(1 for r in review_rows if r.get('reason') == 'disagreement')} "
                  "disagreement, "
                  f"{sum(1 for r in review_rows if r.get('reason') == 'order_warning')} "
                  "order warning)")
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
    ap.add_argument(
        "--tag-only-years", type=int, nargs="*", default=[],
        help="years to split on the tags alone, when the verification signal "
             "agrees on less than half. Their questions are stamped 'tag_only'.",
    )
    args = ap.parse_args(argv)
    return asyncio.run(run(live=args.live, year=args.year,
                           tag_only_years=frozenset(args.tag_only_years)))


if __name__ == "__main__":
    sys.exit(main())
