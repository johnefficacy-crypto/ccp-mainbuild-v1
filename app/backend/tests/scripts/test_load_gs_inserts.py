"""Loader contract for ``scripts/load_gs_inserts.py``.

Runs the real load path against an in-memory repository with the same
semantics the SQL relies on: per-paper unique hash / number / idempotency key,
transactions that roll back on error, and a recount of ``question_count``.
Covered: approved-only, idempotency over two live runs, never touching an
existing row, provenance on created papers, question_count, live re-dedupe,
and tags only on questions the loader itself inserted.
"""
from __future__ import annotations

import asyncio
import contextlib
import copy
import csv
import importlib.util
import json
import pathlib
import sys
import uuid

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[4]
_spec = importlib.util.spec_from_file_location("load_gs_inserts", _ROOT / "scripts" / "load_gs_inserts.py")
lgi = importlib.util.module_from_spec(_spec)
sys.modules["load_gs_inserts"] = lgi
_spec.loader.exec_module(lgi)
egm = lgi.egm

REVIEWER = "11111111-1111-1111-1111-111111111111"
DOC_ID = "22222222-2222-2222-2222-222222222222"

NEW_Q = [
    "Analyze the importance of Ashokan inscriptions for reconstructing Mauryan history.",
    "Discuss the role of aeolian processes in desertification and land degradation.",
    "Is caste disappearing in urban India? Illustrate your answer with examples.",
]
OLD_Q = "Underline the changes in the field of society and economy from the Rig Vedic to the later Vedic period."
MISSING_2024 = "Estimate the contribution of Pallavas of Kanchi for the development of art and literature of South India."


# ── in-memory repository ─────────────────────────────────────────────────


class MemoryRepo:
    def __init__(self):
        self.papers: dict[str, dict] = {}
        self.questions: dict[str, dict] = {}
        self.topic_tags: list[dict] = []
        self.essay_tags: list[dict] = []
        self.topics = {("upsc-cse-mains-gs1", "mauryan-slug"): {"id": str(uuid.uuid4()), "level": "microtopic", "is_active": True}}
        self.themes = {"ethics": {"id": str(uuid.uuid4()), "status": "active"}}
        self.writes = 0

    # seeding
    def add_paper(self, code, year, **extra):
        pid = str(uuid.uuid4())
        self.papers[pid] = {"id": pid, "paper_code": code, "year": year, "trust_status": "pending",
                            "metadata": {"paper_code": code, "question_count": 0}, **extra}
        return pid

    def add_question(self, pid, number, text, **meta):
        qid = str(uuid.uuid4())
        self.questions[qid] = {"id": qid, "pyq_paper_id": pid, "question_number": number,
                               "question_text": text, "normalized_question_hash": egm.content_hash(text),
                               "idempotency_key": None, "reviewer_status": "verified", "metadata": dict(meta)}
        return qid

    # Repo protocol
    async def get_paper(self, code):
        rows = [p for p in self.papers.values() if p["paper_code"] == code]
        return copy.deepcopy(rows[0]) if rows else None

    async def year_questions(self, year):
        ids = {p["id"] for p in self.papers.values() if p["year"] == year}
        return [copy.deepcopy(q) for q in self.questions.values() if q["pyq_paper_id"] in ids]

    async def create_paper(self, row):
        self.writes += 1
        pid = str(uuid.uuid4())
        self.papers[pid] = {"id": pid, **copy.deepcopy(row)}
        return pid

    async def insert_question(self, row):
        for q in self.questions.values():
            same_paper = q["pyq_paper_id"] == row["pyq_paper_id"]
            if (same_paper and (q["normalized_question_hash"] == row["normalized_question_hash"]
                                or q["question_number"] == row["question_number"])) \
                    or (row["idempotency_key"] and q["idempotency_key"] == row["idempotency_key"]):
                return None
        self.writes += 1
        qid = str(uuid.uuid4())
        self.questions[qid] = {"id": qid, "reviewer_status": "pending", "question_type": "descriptive",
                               **copy.deepcopy(row)}
        return qid

    async def recount(self, pid):
        n = sum(1 for q in self.questions.values() if q["pyq_paper_id"] == pid)
        self.papers[pid]["metadata"]["question_count"] = n
        return n

    @contextlib.asynccontextmanager
    async def transaction(self):
        snapshot = copy.deepcopy((self.papers, self.questions, self.topic_tags, self.essay_tags))
        try:
            yield
        except BaseException:
            self.papers, self.questions, self.topic_tags, self.essay_tags = snapshot
            raise

    async def resolve_topic(self, subject_slug, slug):
        return self.topics.get((subject_slug, slug))

    async def resolve_theme(self, code):
        return self.themes.get(code)

    async def question_tags(self, qid):
        return {"primary": sum(1 for t in self.topic_tags if t["question_id"] == qid),
                "essay": sum(1 for t in self.essay_tags if t["question_id"] == qid)}

    async def insert_topic_tag(self, row):
        if any(t["question_id"] == row["question_id"] and t["topic_id"] == row["topic_id"] for t in self.topic_tags):
            return False
        self.topic_tags.append({**row, "reviewer_status": "verified", "tag_role": "primary"})
        return True

    async def insert_essay_tag(self, row):
        self.essay_tags.append({**row, "reviewer_status": "verified"})
        return True


# ── staging fixtures ─────────────────────────────────────────────────────


def staged_question(n: int, text: str, **extra) -> dict:
    return {
        "official_number": n, "sub_part": None, "section": None, "text": text,
        "marks": "10", "marks_source": "printed_column", "word_limit": 150,
        "source_file": "workbench/audit/ocr_cache/2026_GS1.txt", "line_span": [10 * n, 10 * n + 1],
        "page": 2, "low_confidence_lines": [], "flags": [], "content_hash": egm.content_hash(text),
        "route": "insert", "best_db_match": {"score": 0.1}, **extra,
    }


def write_stage(tmp_path, year, paper, questions):
    doc = {"year": year, "paper": paper, "paper_code": egm.paper_code_for(year, paper),
           "paper_kind": "gs", "extractor_version": egm.EXTRACTOR_VERSION, "questions": questions}
    (tmp_path / f"{year}_{paper}.json").write_text(json.dumps(doc), encoding="utf-8")


def review_csv(tmp_path, rows):
    path = tmp_path / "review.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=egm.REVIEW_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in egm.REVIEW_FIELDS})
    return path


def review_row(year, paper, text, approved="Y", **extra):
    return {"paper_code": egm.paper_code_for(year, paper), "content_hash": egm.content_hash(text),
            "year": year, "paper": paper, "text": text, "approved": approved, **extra}


PROVENANCE = {"papers": {"UPSC-CSE-MAINS-GS-2026-GS1": {"source_type": "official", "source_document_id": DOC_ID,
                                                        "source_url": None}}}


@pytest.fixture
def stage(tmp_path):
    write_stage(tmp_path, 2026, "GS1", [staged_question(i + 1, t) for i, t in enumerate(NEW_Q)])
    write_stage(tmp_path, 2024, "GS1", [staged_question(2, MISSING_2024)])
    return tmp_path


def records(tmp_path, rows):
    return lgi.build_records(lgi.read_csv(review_csv(tmp_path, rows)), lgi.load_staging(tmp_path))


def run(repo, grouped, provenance=PROVENANCE, live=True):
    return asyncio.run(lgi.run_load(repo, grouped, provenance, live=live))


# ── approval + record building ───────────────────────────────────────────


def test_only_approved_rows_become_records(stage):
    grouped = records(stage, [
        review_row(2026, "GS1", NEW_Q[0]),
        review_row(2026, "GS1", NEW_Q[1], approved="N"),
        review_row(2026, "GS1", NEW_Q[2], approved=""),
    ])
    assert [r.text for r in grouped["UPSC-CSE-MAINS-GS-2026-GS1"]] == [NEW_Q[0]]


def test_reviewer_edits_win_and_are_recorded(stage):
    grouped = records(stage, [review_row(2026, "GS1", NEW_Q[0], edited_text="Edited text.", edited_marks="15")])
    rec = grouped["UPSC-CSE-MAINS-GS-2026-GS1"][0]
    assert rec.text == "Edited text."
    assert rec.metadata["marks"] == "15" and rec.metadata["marks_source"] == "reviewer"
    assert rec.metadata["text_edited_by_reviewer"] is True
    # Idempotency stays keyed on what was extracted, so a later edit cannot re-insert.
    assert rec.extraction_hash == egm.content_hash(NEW_Q[0])


def test_question_metadata_contract(stage):
    rec = records(stage, [review_row(2026, "GS1", NEW_Q[0])])["UPSC-CSE-MAINS-GS-2026-GS1"][0]
    meta = rec.metadata
    assert meta["marks"] == "10" and meta["marks_source"] == "printed"
    assert meta["word_limit"] == 150 and meta["official_number"] == 1 and meta["sub_part"] is None
    assert meta["assignment_method"] == "official_ocr"
    assert meta["gs_paper"] == "1"
    assert meta["extraction_source"]["file"].endswith("2026_GS1.txt")
    assert meta["extraction_source"]["line_span"] == [10, 11]


def test_approved_row_without_staging_is_refused(stage):
    with pytest.raises(lgi.LoadError):
        records(stage, [review_row(2026, "GS1", "A question nobody staged.")])


# ── 2026: create in split shape, with provenance ─────────────────────────


def test_creates_2026_paper_in_split_shape_with_provenance(stage):
    repo = MemoryRepo()
    grouped = records(stage, [review_row(2026, "GS1", t) for t in NEW_Q])
    [report] = run(repo, {k: v for k, v in grouped.items() if "2026" in k})
    assert report.action == "create" and len(report.inserted) == 3 and report.error is None
    [paper] = repo.papers.values()
    assert paper["paper_code"] == "UPSC-CSE-MAINS-GS-2026-GS1"
    assert paper["trust_status"] == "pending" and paper["year"] == 2026
    assert paper["source_type"] == "official" and paper["source_document_id"] == DOC_ID
    assert paper["metadata"]["paper_kind"] == "gs" and paper["metadata"]["gs_paper"] == "1"
    assert paper["metadata"]["question_count"] == 3 == report.question_count
    qs = sorted(repo.questions.values(), key=lambda q: q["question_number"])
    assert [q["question_number"] for q in qs] == [1, 2, 3]
    assert {q["reviewer_status"] for q in qs} == {"pending"}
    assert {q["question_type"] for q in qs} == {"descriptive"}


def test_missing_provenance_blocks_creation_and_writes_nothing(stage):
    repo = MemoryRepo()
    grouped = records(stage, [review_row(2026, "GS1", NEW_Q[0])])
    [report] = run(repo, {k: v for k, v in grouped.items() if "2026" in k}, provenance={})
    assert report.action == "blocked" and "source_document_id or source_url" in report.error
    assert repo.writes == 0 and not repo.papers


def test_non_official_provenance_is_refused():
    with pytest.raises(lgi.LoadError):
        lgi.paper_provenance({"papers": {"X": {"source_type": "aggregator", "source_url": "https://x"}}}, "X")


# ── idempotency ──────────────────────────────────────────────────────────


def test_two_live_runs_insert_once(stage):
    repo = MemoryRepo()
    grouped = records(stage, [review_row(2026, "GS1", t) for t in NEW_Q])
    only_2026 = {k: v for k, v in grouped.items() if "2026" in k}
    [first] = run(repo, only_2026)
    before = copy.deepcopy(repo.questions)
    [second] = run(repo, only_2026)
    assert len(first.inserted) == 3
    assert second.inserted == [] and second.skipped == {lgi.SKIP_ALREADY: 3}
    assert repo.questions == before
    assert len(repo.papers) == 1


def test_dry_run_writes_nothing(stage):
    repo = MemoryRepo()
    grouped = records(stage, [review_row(2026, "GS1", t) for t in NEW_Q])
    [report] = run(repo, {k: v for k, v in grouped.items() if "2026" in k}, live=False)
    assert report.would_insert == 3 and repo.writes == 0 and not repo.questions


def test_conflict_rolls_the_whole_paper_back(stage):
    repo = MemoryRepo()
    pid = repo.add_paper("UPSC-CSE-MAINS-GS-2024-GS1", 2024)
    repo.add_question(pid, 1, OLD_Q)
    grouped = records(stage, [review_row(2024, "GS1", MISSING_2024)])

    real_insert = repo.insert_question

    async def conflicting(row):
        await real_insert(row)
        return None  # a unique index fired after a partial write

    repo.insert_question = conflicting
    [report] = run(repo, grouped)
    assert report.action == "failed"
    assert len(repo.questions) == 1


# ── other years: existing split paper, never modify ──────────────────────


def test_other_year_inserts_into_existing_split_paper_without_touching_rows(stage):
    repo = MemoryRepo()
    pid = repo.add_paper("UPSC-CSE-MAINS-GS-2024-GS1", 2024)
    old_id = repo.add_question(pid, 41, OLD_Q, gs_paper="1")
    before = copy.deepcopy(repo.questions[old_id])
    grouped = records(stage, [review_row(2024, "GS1", MISSING_2024)])
    [report] = run(repo, grouped)
    assert report.action == "existing" and len(report.inserted) == 1
    assert repo.questions[old_id] == before
    new = repo.questions[report.inserted[0]]
    assert new["question_number"] == 42  # appended after the paper's highest number
    assert new["metadata"]["official_number"] == 2
    assert repo.papers[pid]["metadata"]["question_count"] == 2 == report.question_count


def test_missing_split_paper_is_refused_for_old_years(stage):
    repo = MemoryRepo()
    grouped = records(stage, [review_row(2024, "GS1", MISSING_2024)])
    [report] = run(repo, grouped)
    assert report.action == "blocked" and "not found" in report.error
    assert repo.writes == 0


def test_live_rededupe_skips_present_and_refuses_near(stage):
    repo = MemoryRepo()
    pid = repo.add_paper("UPSC-CSE-MAINS-GS-2024-GS1", 2024)
    other = repo.add_paper("UPSC-CSE-MAINS-GS-2024-GS2", 2024)
    # Present in the year, filed under a different paper: still present.
    repo.add_question(other, 3, MISSING_2024)
    grouped = records(stage, [review_row(2024, "GS1", MISSING_2024)])
    [report] = run(repo, grouped)
    assert report.inserted == [] and report.skipped == {lgi.SKIP_PRESENT: 1}

    repo2 = MemoryRepo()
    pid2 = repo2.add_paper("UPSC-CSE-MAINS-GS-2024-GS1", 2024)
    repo2.add_question(pid2, 1, "Estimate the contribution of the Pallavas to South Indian temple art.")
    [report2] = run(repo2, grouped)
    assert report2.inserted == [] and report2.skipped == {lgi.SKIP_NEAR: 1}
    assert report2.near and report2.near[0]["score"] < egm.PRESENT_CUT
    assert pid not in repo2.papers


# ── tags ─────────────────────────────────────────────────────────────────


def tag_row(text, slug="mauryan-slug", **extra):
    return {"paper_code": "UPSC-CSE-MAINS-GS-2026-GS1", "content_hash": egm.content_hash(text),
            "kind": "topic", "subject_slug": "upsc-cse-mains-gs1", "proposed_slug": slug,
            "score": "0.4", "approved": "Y", **extra}


def loaded_repo(stage):
    repo = MemoryRepo()
    grouped = records(stage, [review_row(2026, "GS1", t) for t in NEW_Q])
    run(repo, {k: v for k, v in grouped.items() if "2026" in k})
    return repo


def test_approved_tag_is_written_verified_on_inserted_question(stage):
    repo = loaded_repo(stage)
    report = asyncio.run(lgi.apply_tags(repo, [tag_row(NEW_Q[0])], reviewer_id=REVIEWER, live=True))
    assert report.applied == 1 and not report.errors
    [tag] = repo.topic_tags
    assert tag["reviewer_status"] == "verified" and tag["tag_role"] == "primary"
    assert tag["reviewed_by"] == REVIEWER and tag["tagging_source"] == "rule"
    again = asyncio.run(lgi.apply_tags(repo, [tag_row(NEW_Q[0])], reviewer_id=REVIEWER, live=True))
    assert again.applied == 0 and again.skipped == {"has_primary": 1}


def test_tags_never_touch_questions_the_loader_did_not_insert(stage):
    repo = MemoryRepo()
    pid = repo.add_paper("UPSC-CSE-MAINS-GS-2026-GS1", 2026)
    # Same text and even the same extraction hash, but not inserted by the loader.
    repo.add_question(pid, 1, NEW_Q[0], extraction_content_hash=egm.content_hash(NEW_Q[0]))
    report = asyncio.run(lgi.apply_tags(repo, [tag_row(NEW_Q[0])], reviewer_id=REVIEWER, live=True))
    assert report.applied == 0 and report.skipped == {"question_not_loaded": 1}
    assert repo.topic_tags == []


def test_unapproved_or_unknown_tags_are_not_written(stage):
    repo = loaded_repo(stage)
    report = asyncio.run(lgi.apply_tags(repo, [
        tag_row(NEW_Q[0], approved=""),
        tag_row(NEW_Q[1], slug="not-a-microtopic"),
    ], reviewer_id=REVIEWER, live=True))
    assert report.applied == 0 and len(report.errors) == 1 and repo.topic_tags == []


def test_live_tags_require_a_reviewer(stage):
    repo = loaded_repo(stage)
    with pytest.raises(lgi.LoadError):
        asyncio.run(lgi.apply_tags(repo, [tag_row(NEW_Q[0])], reviewer_id=None, live=True))
