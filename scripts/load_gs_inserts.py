#!/usr/bin/env python3
r"""Load human-approved GS questions from ``workbench/audit/gs_inserts/``.

P2 of the GS gap repair. Reads ``review.csv`` (written by
``scripts/extract_gs_missing.py``) and loads ONLY rows a human marked
``approved=Y``. Dry run is the default; ``--live`` writes.

WHAT IT WRITES
--------------
* 2026 papers, created directly in the split shape: ``paper_code`` column +
  metadata (``paper_code``, ``paper_kind`` gs|essay, ``gs_paper`` as a string,
  ``year``, ``question_count``), ``trust_status='pending'``, and the provenance
  the verify gate needs (``source_type`` + ``source_document_id`` or
  ``source_url``, from ``provenance.json``). A paper with no provenance anchor
  is refused, never created bare.
* Other years: into the EXISTING split paper ``UPSC-CSE-MAINS-GS-<year>-<paper>``.
  A missing split paper is refused - this script never creates a pre-2026
  paper, because that would bypass the split's verification.
* Questions: ``question_type='descriptive'``, ``reviewer_status='pending'``,
  metadata ``marks``, ``marks_source``, ``word_limit``, ``official_number``,
  ``sub_part``, ``extraction_source``, ``assignment_method='official_ocr'``.
* ``metadata.question_count`` on each touched paper, recounted from the table.
* With ``--tags-csv``: approved primary tags from
  ``scripts/propose_gs_insert_tags.py``, written ``reviewer_status='verified'``
  (a human approved each one) and only onto questions this loader inserted.

WHAT IT NEVER DOES
------------------
Update or delete an existing question, or tag one it did not insert. The only
UPDATE is ``pyq_papers.metadata.question_count``.

IDEMPOTENT: a question is skipped when its paper already holds the same
``normalized_question_hash`` or the same ``metadata.extraction_content_hash``;
``idempotency_key`` (paper_code + extraction hash) backs that up in the DB.
Before inserting, every row is scored again against the LIVE year (same scorer
as the extractor): >= 0.85 is ``present_live`` (skipped), 0.60-0.85 is
``near_match_live`` (refused - a human must look). One transaction per paper.

    export DATABASE_URL=postgresql://...
    python scripts/load_gs_inserts.py                     # dry run (plans against the DB)
    python scripts/load_gs_inserts.py --live
    python scripts/load_gs_inserts.py --live --tags-csv workbench/audit/gs_inserts/tag_review.csv \
        --reviewer-id <profiles.id>

Without DATABASE_URL a dry run still validates the CSV, the staging files and
the provenance offline.
"""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import csv
import hashlib
import importlib.util
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("extract_gs_missing", ROOT / "scripts" / "extract_gs_missing.py")
egm = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault("extract_gs_missing", egm)
_SPEC.loader.exec_module(egm)

STAGING_DIR = egm.OUT_DIR
REVIEW_CSV = STAGING_DIR / "review.csv"
PROVENANCE_JSON = STAGING_DIR / "provenance.json"

EXAM_ID = egm.EXAM_ID
EXAM_PHASE_ID = egm.EXAM_PHASE_ID
NEW_PAPER_YEAR = egm.FULL_YEAR

LOADER_VERSION = "gs-insert-loader-v1"
ASSIGNMENT_METHOD = "official_ocr"
SOURCE_KIND = "bulk_import"
PROVENANCE_SOURCE_TYPE = "official"
APPROVED_VALUES = frozenset({"Y", "YES"})

SKIP_ALREADY = "already_loaded"
SKIP_PRESENT = "present_live"
SKIP_NEAR = "near_match_live"
SKIP_BATCH_DUP = "duplicate_in_batch"


class LoadError(Exception):
    """Input the loader refuses outright (bad CSV, missing staging, bad provenance)."""


# ── inputs (pure) ────────────────────────────────────────────────────────


def gs_paper_value(paper: str) -> str:
    """``metadata.gs_paper`` as a string: '1'..'4' or 'ESSAY'."""
    return egm.ESSAY if paper == egm.ESSAY else paper.removeprefix("GS")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fh)]


def load_staging(staging_dir: Path) -> dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]]:
    """(paper_code, content_hash) -> (paper header, staged question)."""
    out: dict[tuple[str, str], tuple[dict[str, Any], dict[str, Any]]] = {}
    for path in sorted(staging_dir.glob("20*_*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        header = {k: v for k, v in doc.items() if k != "questions"}
        for q in doc.get("questions", []):
            out[(doc["paper_code"], q["content_hash"])] = (header, q)
    return out


@dataclass
class Record:
    paper_code: str
    year: int
    paper: str
    text: str
    extraction_hash: str
    normalized_hash: str
    metadata: dict[str, Any]


def build_records(review_rows: list[dict[str, str]], staging) -> dict[str, list[Record]]:
    """Approved review rows -> insert records grouped by paper_code (file order)."""
    out: dict[str, list[Record]] = {}
    for line_no, row in enumerate(review_rows, start=2):
        if row.get("approved", "").upper() not in APPROVED_VALUES:
            continue
        key = (row.get("paper_code", ""), row.get("content_hash", ""))
        if key not in staging:
            raise LoadError(f"review.csv line {line_no}: {key} has no staged question")
        header, q = staging[key]
        if q.get("route") != egm.ROUTE_INSERT:
            raise LoadError(f"review.csv line {line_no}: staged route is {q.get('route')!r}, not insert")
        edited = row.get("edited_text", "")
        text = edited or q["text"]
        if not text.strip():
            raise LoadError(f"review.csv line {line_no}: empty question text")
        edited_marks = row.get("edited_marks", "")
        if edited_marks:
            marks, marks_source = edited_marks, "reviewer"
        elif q.get("marks"):
            marks, marks_source = q["marks"], "printed"
        else:
            marks, marks_source = None, None
        meta = {
            "marks": marks,
            "marks_source": marks_source,
            "word_limit": q.get("word_limit"),
            "official_number": q.get("official_number"),
            "sub_part": q.get("sub_part"),
            "section": q.get("section"),
            "gs_paper": gs_paper_value(header["paper"]),
            "assignment_method": ASSIGNMENT_METHOD,
            "extraction_source": {
                "file": q.get("source_file"),
                "line_span": q.get("line_span"),
                "page": q.get("page"),
                "extractor_version": header.get("extractor_version"),
                "flags": q.get("flags", []),
            },
            "extraction_content_hash": q["content_hash"],
            "text_edited_by_reviewer": bool(edited),
            "loader_version": LOADER_VERSION,
        }
        out.setdefault(header["paper_code"], []).append(Record(
            paper_code=header["paper_code"],
            year=int(header["year"]),
            paper=header["paper"],
            text=text,
            extraction_hash=q["content_hash"],
            normalized_hash=egm.content_hash(text),
            metadata=meta,
        ))
    return out


def paper_provenance(provenance: dict[str, Any], paper_code: str) -> dict[str, Any]:
    """The verify gate's anchor for one new paper, or LoadError.

    ``source_type`` must be 'official' and at least one of
    ``source_document_id`` / ``source_url`` must be set. No default is ever
    filled in: an anchor nobody checked is worse than none.
    """
    entry = (provenance.get("papers") or {}).get(paper_code) or {}
    doc_id = (entry.get("source_document_id") or "").strip() or None
    url = (entry.get("source_url") or "").strip() or None
    source_type = (entry.get("source_type") or PROVENANCE_SOURCE_TYPE).strip()
    if source_type != PROVENANCE_SOURCE_TYPE:
        raise LoadError(f"{paper_code}: provenance source_type must be 'official', got {source_type!r}")
    if not (doc_id or url):
        raise LoadError(f"{paper_code}: provenance needs source_document_id or source_url (provenance.json)")
    if doc_id:
        uuid.UUID(doc_id)  # raises on a malformed id
    return {"source_type": source_type, "source_document_id": doc_id, "source_url": url,
            "source_file": entry.get("source_file")}


def new_paper_row(year: int, paper: str, paper_code: str, prov: dict[str, Any]) -> dict[str, Any]:
    return {
        "exam_id": EXAM_ID,
        "exam_phase_id": EXAM_PHASE_ID,
        "year": year,
        "paper_code": paper_code,
        "trust_status": "pending",
        "source_type": prov["source_type"],
        "source_url": prov["source_url"],
        "source_document_id": prov["source_document_id"],
        "metadata": {
            "paper_code": paper_code,
            "paper_kind": "essay" if paper == egm.ESSAY else "gs",
            "gs_paper": gs_paper_value(paper),
            "year": year,
            "question_count": 0,
            "created_by": LOADER_VERSION,
            "source_file": prov.get("source_file"),
        },
    }


def idempotency_key(paper_code: str, extraction_hash: str) -> str:
    return hashlib.sha256(f"{LOADER_VERSION}|{paper_code}|{extraction_hash}".encode()).hexdigest()


# ── DB seam ──────────────────────────────────────────────────────────────


class Repo(Protocol):
    async def get_paper(self, paper_code: str) -> dict[str, Any] | None: ...
    async def year_questions(self, year: int) -> list[dict[str, Any]]: ...
    async def create_paper(self, row: dict[str, Any]) -> str: ...
    async def insert_question(self, row: dict[str, Any]) -> str | None: ...
    async def recount(self, paper_id: str) -> int: ...
    def transaction(self) -> contextlib.AbstractAsyncContextManager: ...
    async def resolve_topic(self, subject_slug: str, topic_slug: str) -> dict[str, Any] | None: ...
    async def resolve_theme(self, theme_code: str) -> dict[str, Any] | None: ...
    async def question_tags(self, question_id: str) -> dict[str, int]: ...
    async def insert_topic_tag(self, row: dict[str, Any]) -> bool: ...
    async def insert_essay_tag(self, row: dict[str, Any]) -> bool: ...


def as_meta(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


class PgRepo:
    """asyncpg implementation. Reads and writes are scoped to the Mains GS exam/phase."""

    def __init__(self, conn: Any):
        self.conn = conn

    async def get_paper(self, paper_code):
        rows = await self.conn.fetch(
            """select id, year, paper_code, trust_status, metadata
                 from public.pyq_papers
                where exam_id = $1 and exam_phase_id = $2 and paper_code = $3""",
            EXAM_ID, EXAM_PHASE_ID, paper_code,
        )
        if len(rows) > 1:
            raise LoadError(f"{paper_code}: {len(rows)} papers carry this code")
        if not rows:
            return None
        row = dict(rows[0])
        row["id"] = str(row["id"])
        row["metadata"] = as_meta(row["metadata"])
        return row

    async def year_questions(self, year):
        rows = await self.conn.fetch(
            """select q.id, q.pyq_paper_id, q.question_number, q.question_text,
                      q.normalized_question_hash, q.metadata
                 from public.pyq_questions q
                 join public.pyq_papers p on p.id = q.pyq_paper_id
                where p.exam_id = $1 and p.exam_phase_id = $2 and p.year = $3""",
            EXAM_ID, EXAM_PHASE_ID, year,
        )
        out = []
        for r in rows:
            d = dict(r)
            d["id"], d["pyq_paper_id"] = str(d["id"]), str(d["pyq_paper_id"])
            d["metadata"] = as_meta(d["metadata"])
            out.append(d)
        return out

    async def create_paper(self, row):
        return str(await self.conn.fetchval(
            """insert into public.pyq_papers
                   (exam_id, exam_phase_id, year, paper_code, trust_status,
                    source_type, source_url, source_document_id, metadata)
               values ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
               returning id""",
            row["exam_id"], row["exam_phase_id"], row["year"], row["paper_code"],
            row["trust_status"], row["source_type"], row["source_url"],
            row["source_document_id"], json.dumps(row["metadata"]),
        ))

    async def insert_question(self, row):
        # `on conflict do nothing` covers every unique index (paper+hash,
        # paper+number, idempotency_key): a conflict inserts nothing and
        # returns no id, which the caller treats as fatal for the paper.
        value = await self.conn.fetchval(
            """insert into public.pyq_questions
                   (pyq_paper_id, question_number, question_text, normalized_question_hash,
                    content_hash, idempotency_key, question_type, language,
                    reviewer_status, source_kind, extractor_version, metadata)
               values ($1, $2, $3, $4, $5, $6, 'descriptive', 'en',
                       'pending', $7, $8, $9::jsonb)
               on conflict do nothing
               returning id""",
            row["pyq_paper_id"], row["question_number"], row["question_text"],
            row["normalized_question_hash"], row["content_hash"], row["idempotency_key"],
            SOURCE_KIND, LOADER_VERSION, json.dumps(row["metadata"]),
        )
        return str(value) if value else None

    async def recount(self, paper_id):
        return int(await self.conn.fetchval(
            """update public.pyq_papers p
                  set metadata = coalesce(p.metadata, '{}'::jsonb) || jsonb_build_object(
                        'question_count',
                        (select count(*) from public.pyq_questions q where q.pyq_paper_id = p.id)),
                      updated_at = now()
                where p.id = $1
            returning (p.metadata->>'question_count')::int""",
            paper_id,
        ))

    def transaction(self):
        return self.conn.transaction()

    async def resolve_topic(self, subject_slug, topic_slug):
        row = await self.conn.fetchrow(
            """select t.id, t.level, t.is_active
                 from public.topics t join public.subjects s on s.id = t.subject_id
                where s.slug = $1 and t.slug = $2""",
            subject_slug, topic_slug,
        )
        return {**dict(row), "id": str(row["id"])} if row else None

    async def resolve_theme(self, theme_code):
        row = await self.conn.fetchrow(
            "select id, status from public.essay_themes where theme_code = $1", theme_code,
        )
        return {**dict(row), "id": str(row["id"])} if row else None

    async def question_tags(self, question_id):
        primary = await self.conn.fetchval(
            """select count(*) from public.pyq_question_topic_tags
                where question_id = $1 and tag_role = 'primary'""", question_id)
        essay = await self.conn.fetchval(
            "select count(*) from public.essay_pyq_tags where question_id = $1", question_id)
        return {"primary": int(primary), "essay": int(essay)}

    async def insert_topic_tag(self, row):
        value = await self.conn.fetchval(
            """insert into public.pyq_question_topic_tags
                   (question_id, topic_id, tag_weight, tag_role, tagging_source,
                    confidence_score, reviewer_status, reviewed_by, reviewed_at,
                    source_kind, metadata)
               values ($1, $2, 1, 'primary', $3, $4, 'verified', $5, now(), $6, $7::jsonb)
               on conflict (question_id, topic_id, tag_role) do nothing
               returning id""",
            row["question_id"], row["topic_id"], row["tagging_source"], row["confidence_score"],
            row["reviewed_by"], SOURCE_KIND, json.dumps(row["metadata"]),
        )
        return value is not None

    async def insert_essay_tag(self, row):
        value = await self.conn.fetchval(
            """insert into public.essay_pyq_tags
                   (question_id, theme_id, essay_type, tagging_source, confidence_score,
                    reviewer_status, reviewed_by, reviewed_at, metadata)
               values ($1, $2, coalesce($3, 'quote_abstract'), $4, $5, 'verified', $6, now(), $7::jsonb)
               on conflict (question_id, theme_id) do nothing
               returning id""",
            row["question_id"], row["theme_id"], row["essay_type"], row["tagging_source"],
            row["confidence_score"], row["reviewed_by"], json.dumps(row["metadata"]),
        )
        return value is not None


# ── planning + loading ───────────────────────────────────────────────────


@dataclass
class PaperReport:
    paper_code: str
    action: str = ""  # create | existing | blocked
    inserted: list[str] = field(default_factory=list)
    would_insert: int = 0
    skipped: dict[str, int] = field(default_factory=dict)
    near: list[dict[str, Any]] = field(default_factory=list)
    question_count: int | None = None
    error: str | None = None

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1


def plan_paper(records: list[Record], paper: dict[str, Any] | None,
               year_pool: list[dict[str, Any]], report: PaperReport) -> list[Record]:
    """Which records to insert. Pure: no IO. Fills ``report.skipped``/``near``."""
    paper_id = paper["id"] if paper else None
    own = [q for q in year_pool if paper_id and q["pyq_paper_id"] == paper_id]
    own_hashes = {q.get("normalized_question_hash") for q in own}
    own_extract = {as_meta(q.get("metadata")).get("extraction_content_hash") for q in own}
    pool = [{"id": q["id"], "text": egm.english_part(q.get("question_text") or "")} for q in year_pool]
    seen: set[str] = set()
    todo = []
    for rec in records:
        if rec.normalized_hash in own_hashes or rec.extraction_hash in own_extract:
            report.skip(SKIP_ALREADY)
            continue
        if rec.normalized_hash in seen:
            report.skip(SKIP_BATCH_DUP)
            continue
        match = egm.best_match(rec.text, pool)
        route = egm.route_for(match["score"])
        if route == egm.ROUTE_PRESENT:
            report.skip(SKIP_PRESENT)
            continue
        if route == egm.ROUTE_NEAR:
            report.skip(SKIP_NEAR)
            report.near.append({"extraction_hash": rec.extraction_hash, "score": match["score"],
                                "db_question_id": match["id"]})
            continue
        seen.add(rec.normalized_hash)
        todo.append(rec)
    return todo


async def load_paper(repo: Repo, paper_code: str, records: list[Record],
                     provenance: dict[str, Any], *, live: bool) -> PaperReport:
    report = PaperReport(paper_code)
    year, paper_name = records[0].year, records[0].paper
    paper = await repo.get_paper(paper_code)
    prov = None
    if paper is None:
        if year != NEW_PAPER_YEAR:
            report.action, report.error = "blocked", (
                f"split paper {paper_code} not found; this loader only creates {NEW_PAPER_YEAR} papers")
            return report
        try:
            prov = paper_provenance(provenance, paper_code)
        except (LoadError, ValueError) as exc:
            report.action, report.error = "blocked", str(exc)
            return report
        report.action = "create"
    else:
        if int(paper.get("year") or 0) != year:
            report.action, report.error = "blocked", f"{paper_code} has year {paper.get('year')}, expected {year}"
            return report
        if as_meta(paper.get("metadata")).get("retired"):
            report.action, report.error = "blocked", f"{paper_code} is retired"
            return report
        report.action = "existing"

    year_pool = await repo.year_questions(year)
    todo = plan_paper(records, paper, year_pool, report)
    report.would_insert = len(todo)
    if not live or not todo:
        return report

    async with repo.transaction():
        paper_id = paper["id"] if paper else await repo.create_paper(
            new_paper_row(year, paper_name, paper_code, prov))
        taken = [q.get("question_number") or 0 for q in year_pool if q["pyq_paper_id"] == paper_id]
        next_no = max(taken, default=0)
        for rec in todo:
            next_no += 1
            qid = await repo.insert_question({
                "pyq_paper_id": paper_id,
                "question_number": next_no,
                "question_text": rec.text,
                "normalized_question_hash": rec.normalized_hash,
                "content_hash": rec.normalized_hash,
                "idempotency_key": idempotency_key(paper_code, rec.extraction_hash),
                "metadata": rec.metadata,
            })
            if qid is None:
                # A unique index fired that the plan did not foresee: roll the
                # whole paper back rather than load part of it.
                raise LoadError(f"{paper_code}: insert conflict on official #"
                                f"{rec.metadata['official_number']}{rec.metadata['sub_part'] or ''}")
            report.inserted.append(qid)
        report.question_count = await repo.recount(paper_id)
    return report


# ── tags ─────────────────────────────────────────────────────────────────


@dataclass
class TagReport:
    applied: int = 0
    skipped: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1


async def apply_tags(repo: Repo, tag_rows: list[dict[str, str]], *, reviewer_id: str | None,
                     live: bool) -> TagReport:
    """Approved tag proposals -> verified primary tags on loader-inserted questions only."""
    report = TagReport()
    if live:
        if not reviewer_id:
            raise LoadError("--reviewer-id (profiles.id of the approving reviewer) is required to write tags")
        uuid.UUID(reviewer_id)
    by_year: dict[int, list[dict[str, Any]]] = {}
    papers: dict[str, dict[str, Any] | None] = {}
    for row in tag_rows:
        if row.get("approved", "").upper() not in APPROVED_VALUES:
            continue
        code = row["paper_code"]
        if code not in papers:
            papers[code] = await repo.get_paper(code)
        paper = papers[code]
        if paper is None:
            report.skip("paper_not_loaded")
            continue
        year = int(paper["year"])
        if year not in by_year:
            by_year[year] = await repo.year_questions(year)
        question = next((
            q for q in by_year[year]
            if q["pyq_paper_id"] == paper["id"]
            and as_meta(q.get("metadata")).get("extraction_content_hash") == row["content_hash"]
            and as_meta(q.get("metadata")).get("loader_version")
        ), None)
        if question is None:
            report.skip("question_not_loaded")
            continue
        existing = await repo.question_tags(question["id"])
        slug = row.get("edited_slug") or row.get("proposed_slug")
        if not slug:
            report.skip("no_proposal")
            continue
        source = "manual" if row.get("edited_slug") else "rule"
        confidence = 1.0 if row.get("edited_slug") else float(row.get("score") or 0)
        meta = {"proposer": row.get("proposer_version"), "approved_via": "tag_review.csv",
                "loader_version": LOADER_VERSION}
        if row.get("kind") == "essay_theme":
            if existing["essay"]:
                report.skip("has_essay_tag")
                continue
            theme = await repo.resolve_theme(slug)
            if not theme or theme.get("status") != "active":
                report.errors.append(f"{code} {row['content_hash'][:12]}: essay theme {slug!r} not active")
                continue
            if live:
                ok = await repo.insert_essay_tag({
                    "question_id": question["id"], "theme_id": theme["id"],
                    "essay_type": row.get("essay_type") or None, "tagging_source": source,
                    "confidence_score": min(max(confidence, 0.0), 1.0), "reviewed_by": reviewer_id,
                    "metadata": meta,
                })
                report.applied += int(ok)
                if not ok:
                    report.skip("tag_exists")
            else:
                report.applied += 1
            continue
        if existing["primary"]:
            report.skip("has_primary")
            continue
        topic = await repo.resolve_topic(row["subject_slug"], slug)
        if not topic or topic.get("level") != "microtopic" or not topic.get("is_active", True):
            report.errors.append(f"{code} {row['content_hash'][:12]}: microtopic {slug!r} not in {row['subject_slug']}")
            continue
        if live:
            ok = await repo.insert_topic_tag({
                "question_id": question["id"], "topic_id": topic["id"], "tagging_source": source,
                "confidence_score": min(max(confidence, 0.0), 1.0), "reviewed_by": reviewer_id,
                "metadata": meta,
            })
            report.applied += int(ok)
            if not ok:
                report.skip("tag_exists")
        else:
            report.applied += 1
    return report


# ── run ──────────────────────────────────────────────────────────────────


async def run_load(repo: Repo | None, grouped: dict[str, list[Record]], provenance: dict[str, Any],
                   *, live: bool) -> list[PaperReport]:
    reports = []
    for code in sorted(grouped):
        if repo is None:
            rep = PaperReport(code, action="offline", would_insert=len(grouped[code]))
            if grouped[code][0].year == NEW_PAPER_YEAR:
                try:
                    paper_provenance(provenance, code)
                except (LoadError, ValueError) as exc:
                    rep.error = f"(if created) {exc}"
            reports.append(rep)
            continue
        try:
            reports.append(await load_paper(repo, code, grouped[code], provenance, live=live))
        except LoadError as exc:
            reports.append(PaperReport(code, action="failed", error=str(exc)))
    return reports


def print_reports(reports: list[PaperReport], *, live: bool) -> None:
    verb = "inserted" if live else "would insert"
    for r in reports:
        n = len(r.inserted) if live else r.would_insert
        skipped = ", ".join(f"{k}={v}" for k, v in sorted(r.skipped.items())) or "-"
        line = f"{r.paper_code:<30} {r.action:<9} {verb} {n:>3}  skipped: {skipped}"
        if r.question_count is not None:
            line += f"  question_count={r.question_count}"
        if r.error:
            line += f"  ERROR: {r.error}"
        print(line)
        for near in r.near:
            print(f"    near-match live {near['score']} vs {near['db_question_id']} ({near['extraction_hash'][:12]})")


async def amain(args: argparse.Namespace) -> int:
    review_rows = read_csv(Path(args.review_csv))
    grouped = build_records(review_rows, load_staging(Path(args.staging_dir)))
    if args.year:
        grouped = {k: v for k, v in grouped.items() if v[0].year in args.year}
    prov_path = Path(args.provenance)
    provenance = json.loads(prov_path.read_text(encoding="utf-8")) if prov_path.is_file() else {}
    print(f"{sum(len(v) for v in grouped.values())} approved question(s) across {len(grouped)} paper(s)"
          f" - {'LIVE' if args.live else 'dry run'}")

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        if args.live:
            print("DATABASE_URL is required for --live", file=sys.stderr)
            return 2
        print_reports(await run_load(None, grouped, provenance, live=False), live=False)
        print("(offline: no DATABASE_URL, so nothing was checked against the DB)")
        return 0

    import asyncpg  # declared in app/backend/requirements.txt

    conn = await asyncpg.connect(dsn)
    try:
        repo = PgRepo(conn)
        reports = await run_load(repo, grouped, provenance, live=args.live)
        print_reports(reports, live=args.live)
        if args.tags_csv:
            tag_report = await apply_tags(repo, read_csv(Path(args.tags_csv)),
                                          reviewer_id=args.reviewer_id, live=args.live)
            print(f"tags {'applied' if args.live else 'would apply'}: {tag_report.applied}  "
                  f"skipped: {tag_report.skipped or '-'}")
            for err in tag_report.errors:
                print(f"    tag ERROR: {err}")
    finally:
        await conn.close()
    failed = [r for r in reports if r.action in ("failed", "blocked")]
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--review-csv", default=str(REVIEW_CSV))
    ap.add_argument("--staging-dir", default=str(STAGING_DIR))
    ap.add_argument("--provenance", default=str(PROVENANCE_JSON))
    ap.add_argument("--tags-csv", help="approved tag proposals (tag_review.csv)")
    ap.add_argument("--reviewer-id", help="profiles.id recorded as reviewed_by on applied tags")
    ap.add_argument("--year", type=int, action="append")
    ap.add_argument("--live", action="store_true", help="write (default: dry run)")
    try:
        return asyncio.run(amain(ap.parse_args(argv)))
    except LoadError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
