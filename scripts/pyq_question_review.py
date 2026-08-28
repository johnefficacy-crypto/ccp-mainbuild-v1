#!/usr/bin/env python3
"""Review and promote UPSC CSE PYQ questions + topic tags — safely.

A PYQ backlog sits at ``reviewer_status='pending'``. CLAUDE.md locks
verified-only reads, so a bulk ``UPDATE ... SET reviewer_status='verified'`` is
prohibited: it would put unreviewed questions in front of aspirants. This tool
splits the job into three offline-first steps and never promotes a row on its
own judgement.

Scope is chosen at ``export`` time and is not baked into the tool: pass
``--exam-phase-id`` (repeatable) for any phase, or ``--paper-id`` (repeatable)
to name papers directly. ``--mains-phase-id`` remains as the default phase so
existing Mains invocations keep working unchanged. ``sweep`` and ``apply``
operate purely on the exported files and have never had phase-specific
behaviour — the worksheet shape and the decision semantics are identical for
every phase.

    PRELIMS CAVEAT — READ BEFORE PROMOTING MCQs. The deterministic sweep was
    built for Mains, whose questions are descriptive: it checks the stem only.
    For an MCQ phase (Prelims/CSAT) the substance is in the OPTIONS and the
    answer key, and this tool sees neither — ``export`` fetches
    ``pyq_questions`` rows, not ``pyq_options``. The one option-level signal it
    can give is ``mcq_no_correct_option`` (below), derived from the question
    row's own ``correct_option_id``. It CANNOT check option count, option text,
    or that exactly one option carries ``is_correct``. Those are enforced
    downstream by the PYQ->Mock projection's eligibility gate
    (``app/backend/app/admin/pyq_mock_projection.py``,
    ``_check_question_eligibility``; see
    ``docs/runbooks/EI-DATA-01_upsc_2026_primary_topic_tags.md``). A clean sweep
    on an MCQ row therefore means "the stem looks sane", NOT "this question is
    answerable" — the spot-check sample must be read against the paper.

    export  ->  pull the pending in-scope questions + tags from the live API into
                two flat JSON files (read-only).

    sweep   ->  pure offline. Run deterministic checks that only ever FLAG a
                row — they never decide it. Clean rows are sorted from flagged
                rows and a spread spot-check sample is picked per paper. Writes
                one worksheet.csv with a blank ``decision`` column.

    apply   ->  read the worksheet back and PATCH one review call per decided
                row. Blank decisions are skipped. Requires ``--apply --confirm``.

Every row that ends up ``verified`` must trace back to EITHER a passed
deterministic check AND a clean batch a human signed off after eyeballing its
spot-check sample, OR an explicit human decision typed into the worksheet. No
step in this tool sets a row to verified by itself.

    THE WORKSHEET CSV IS THE AUDIT TRAIL. The review endpoint does NOT persist
    reviewer_notes for either kind (see below), so the DB row carries no record
    of WHY it was verified. Keep the filled-in CSV — do not discard it after
    ``apply``.

Route contracts this tool depends on (verified against the repo backend):

  export reads:
    GET  /api/admin/exam-intelligence/exams/{exam_id}/items
         ?kind=pyq_question|pyq_question_topic_tag&status=pending&limit&offset
         -> {items:[...], count}. pyq_question items carry NO question_text.
    GET  /api/admin/exam-intelligence-cms/pyq-questions?pyq_paper_id=...
         -> {items:[...], total, limit, offset}; items include question_text.
    GET  /api/admin/exam-intelligence-cms/pyq-papers?exam_id=...
         -> paper rows (year, exam_phase_id) used to resolve the scope.
    GET  /api/admin/exam-intelligence-cms/exam-phase-sections?exam_phase_id=...
         -> section_id -> section_label map.

  apply writes:
    PATCH /api/admin/exam-intelligence/items/{kind}/{row_id}/review
         body {"reviewer_status": "...", "reviewer_notes": "..."}  (flat body —
         this is NOT the {reason, payload} CMS envelope).
         * kind=pyq_question routes through the update_pyq_question_review_atomic
           RPC, which cascades reviewer_status to the question's pyq_options and
           accepts NO notes parameter -> reviewer_notes is DROPPED server-side.
         * kind=pyq_question_topic_tag is a plain table update with
           supports_notes=False -> reviewer_notes is DROPPED server-side.
         The tool sends reviewer_notes anyway (harmless, forward-compatible) but
         does NOT claim it was persisted.

Usage:

    export CCP_API_BASE=...      # e.g. https://<host>
    export CCP_ADMIN_JWT=...     # admin/super_admin JWT

    # 1. Export (read-only; --apply just means "write the files").
    #    Mains (unchanged — --mains-phase-id still defaults):
    python scripts/pyq_question_review.py export \
        --exam-id <uuid> --out review_out --apply
    #    Any other phase, e.g. Prelims:
    python scripts/pyq_question_review.py export \
        --exam-id <uuid> --exam-phase-id <prelims-phase-uuid> \
        --out review_out --apply
    #    Or name the papers directly (phase filter not applied):
    python scripts/pyq_question_review.py export \
        --exam-id <uuid> --paper-id <uuid> --paper-id <uuid> \
        --out review_out --apply

    # 2. Sweep (offline; --apply means "write the worksheet").
    python scripts/pyq_question_review.py sweep \
        --questions review_out/questions_export.json \
        --tags review_out/tags_export.json \
        --topic-catalog <path/to/topic_catalog.json> \
        --out worksheet.csv --apply

    # ... a human opens worksheet.csv and fills the decision (+ notes) column ...

    # 3. Apply (dry-run by default; needs BOTH flags to write).
    python scripts/pyq_question_review.py apply --worksheet worksheet.csv \
        --exam-id <uuid>
    python scripts/pyq_question_review.py apply --worksheet worksheet.csv \
        --exam-id <uuid> --apply --confirm

export needs ``exam_intelligence.review`` (items route) + ``exam_intelligence.cms``
(pyq-questions / pyq-papers / sections). apply needs ``exam_intelligence.review``.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable

try:  # requests is only needed for the live export/apply paths, not for sweep
    import requests  # or the offline unit tests, which never build a Client.
except ImportError:  # pragma: no cover - exercised only where requests is absent
    requests = None

CMS = "/api/admin/exam-intelligence-cms"
INTEL = "/api/admin/exam-intelligence"

# Reusable identity (docs/pyqfrontloadnotes.md, docs/runbooks/EI-DATA-02...).
DEFAULT_EXAM_ID = "5466e62f-7382-4a38-ba96-2fe5fbfeaba2"       # UPSC CSE
DEFAULT_MAINS_PHASE_ID = "626ec667-4bbf-4420-8715-48c5b83e0d11"  # Mains phase

DECISIONS = {"verified", "rejected", "needs_correction"}
NOTE_MAX = 500  # ReviewBody.reviewer_notes max_length; over this the API 422s.

QUESTION_KIND = "pyq_question"
TAG_KIND = "pyq_question_topic_tag"

WORKSHEET_FIELDS = [
    "row_type", "row_id", "paper_year", "question_number_or_topic_id",
    "text_preview", "flags", "sample_reason", "decision", "notes",
]

# Printable ASCII the sweep treats as clean; \t \n \r are allowed whitespace.
_PRINTABLE = set(chr(c) for c in range(0x20, 0x7F)) | {"\t", "\n", "\r"}
_REPEAT_CHAR = re.compile(r"(\S)\1{3,}")


# ─── HTTP client (mirrors scripts/syllabus_mention_review.py) ─────────────────
class Client:
    def __init__(self, base: str, token: str, timeout: int = 60) -> None:
        if requests is None:  # pragma: no cover - environment guard
            raise RuntimeError("the 'requests' package is required for live "
                               "export/apply calls but is not installed")
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"Authorization": f"Bearer {token}",
             "Content-Type": "application/json; charset=utf-8"}
        )

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        r = self.session.get(f"{self.base}{path}", params=params or {}, timeout=self.timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"GET {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() or {}

    def patch(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        r = self.session.patch(f"{self.base}{path}", data=data, timeout=self.timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"PATCH {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() or {}

    def all_items(self, path: str, params: dict[str, Any] | None = None,
                  page: int = 200) -> list[dict]:
        """Loop offset until a short page. Works for both the items route
        ({items, count}) and the CMS list routes ({items, total, ...})."""
        out: list[dict] = []
        offset = 0
        while True:
            d = self.get(path, {**(params or {}), "limit": page, "offset": offset})
            items = d.get("items") or []
            out.extend(items)
            if len(items) < page:
                return out
            offset += page


# ─── export ───────────────────────────────────────────────────────────────
def select_papers(papers: Iterable[dict], phase_ids: set[str] | None,
                  paper_ids: set[str] | None) -> list[dict]:
    """Narrow the exam's papers to the operator-chosen scope.

    Exactly one scope applies, and one of the two must be given — this never
    falls through to "every paper in the exam":

    * ``paper_ids`` — explicit ids ARE the scope, so the phase filter is not
      also applied. Naming a paper is a deliberate act; requiring it to sit on
      an expected phase as well only turns a correct request into a confusing
      "no papers found".
    * ``phase_ids`` — every paper whose ``exam_phase_id`` is in the set.

    Papers with no ``exam_phase_id`` can only be reached by explicit id.
    """
    if paper_ids:
        return [p for p in papers if p.get("id") in paper_ids]
    if not phase_ids:
        return []
    return [p for p in papers if p.get("exam_phase_id") in phase_ids]


def merge_questions(pending_items: list[dict], cms_by_id: dict[str, dict],
                    paper_year: dict[str, Any], section_label: dict[str, str]) -> list[dict]:
    """Merge route (a) pending pyq_question rows with route (b) CMS rows by id.

    Route (a) has no question_text; route (b) supplies it. Only rows present in
    BOTH the pending set and the in-scope CMS set survive (scope-limited
    pending).

    ``question_type`` and ``correct_option_id`` are carried through so the
    offline sweep can raise ``mcq_no_correct_option`` without a second fetch;
    see the Prelims caveat in the module docstring for what that does and does
    not cover.
    """
    rows = []
    for it in pending_items:
        qid = it.get("id")
        cms = cms_by_id.get(qid)
        if cms is None:
            continue  # not an in-scope paper's question, or not fetched
        paper_id = it.get("pyq_paper_id") or cms.get("pyq_paper_id")
        section_id = it.get("section_id") or cms.get("section_id")
        rows.append({
            "id": qid,
            "paper_id": paper_id,
            "year": paper_year.get(paper_id),
            "section": section_label.get(section_id, section_id or ""),
            "question_number": it.get("question_number", cms.get("question_number")),
            "source_question_ref": it.get("source_question_ref", cms.get("source_question_ref")),
            "question_type": cms.get("question_type", it.get("question_type")),
            "question_text": cms.get("question_text", ""),
            "language": it.get("language", cms.get("language")),
            "correct_option_id": cms.get("correct_option_id", it.get("correct_option_id")),
            "reviewer_status": it.get("reviewer_status", cms.get("reviewer_status")),
        })
    return rows


def do_export(c: Client, args: argparse.Namespace) -> int:
    exam_id = args.exam_id
    override_ids = {p.strip() for p in (args.paper_id or []) if p.strip()} or None

    # Explicit --exam-phase-id wins outright; otherwise fall back to
    # --mains-phase-id, which keeps its historical default so existing Mains
    # invocations are unchanged. --paper-id, when given, supersedes both.
    phase_ids = {p.strip() for p in (args.exam_phase_id or []) if p.strip()}
    if not phase_ids and args.mains_phase_id:
        phase_ids = {args.mains_phase_id}

    all_papers = c.all_items(f"{CMS}/pyq-papers", {"exam_id": exam_id})
    scoped_papers = select_papers(all_papers, phase_ids, override_ids)
    skipped = len(all_papers) - len(scoped_papers)
    if not scoped_papers:
        scope_desc = (f"paper id(s) {sorted(override_ids)}" if override_ids
                      else f"phase(s) {sorted(phase_ids)}" if phase_ids
                      else "no scope (pass --exam-phase-id or --paper-id)")
        print(f"error: no papers found for exam {exam_id} matching {scope_desc}. "
              f"Checked {len(all_papers)} paper(s).", file=sys.stderr)
        return 1
    scoped_paper_ids = {p["id"] for p in scoped_papers}
    paper_year = {p["id"]: p.get("year") for p in scoped_papers}
    scoped_phase_ids = {p.get("exam_phase_id") for p in scoped_papers if p.get("exam_phase_id")}

    # section_id -> label, across the in-scope phase(s).
    section_label: dict[str, str] = {}
    for phase_id in scoped_phase_ids:
        for s in c.all_items(f"{CMS}/exam-phase-sections", {"exam_phase_id": phase_id}):
            if s.get("id"):
                section_label[s["id"]] = s.get("section_label") or s["id"]

    # Route (b): full question rows per in-scope paper (for question_text + to
    # build the question-id membership used to scope tags). Fetch every scoped
    # paper so a paper with pending tags but no pending questions is still
    # covered.
    cms_by_id: dict[str, dict] = {}
    for pid in sorted(scoped_paper_ids):
        for row in c.all_items(f"{CMS}/pyq-questions", {"pyq_paper_id": pid}):
            if row.get("id"):
                cms_by_id[row["id"]] = row
    scoped_question_ids = set(cms_by_id)

    # Route (a) intentionally NOT used for questions: the exam-wide
    # /items?kind=pyq_question route paginates via a re-executed
    # .limit(limit+offset) query ordered only by created_at with no secondary
    # tiebreaker, which silently drops/duplicates rows when many share an
    # identical created_at (bulk-imported years) — confirmed live 2026-08-26
    # (2025: 0/87 returned, 2024: 44/87 returned, both papers verified 87/87
    # present via the CMS per-paper route). Derive "pending" status directly
    # from the reliable per-paper CMS fetch instead.
    pending_q = [
        row for row in cms_by_id.values()
        if args.status == "all" or row.get("reviewer_status") == args.status
    ]

    questions = merge_questions(pending_q, cms_by_id, paper_year, section_label)

    # Route (a) skipped for tags too — same backend pagination instability
    # (confirmed live 2026-08-26: growing-limit re-query with no tiebreak on
    # created_at silently drops bulk-inserted rows). The CMS list route uses
    # true fixed-page .range() pagination — reliable.
    tag_params = {} if args.status == "all" else {"reviewer_status": args.status}
    pending_tags = [
        t for t in c.all_items(f"{CMS}/pyq-question-topic-tags", tag_params)
        if t.get("question_id") in scoped_question_ids
    ]
    tags = [{
        "id": t.get("id"),
        "question_id": t.get("question_id"),
        "topic_id": t.get("topic_id"),
        "tag_role": t.get("tag_role"),
        "tagging_source": t.get("tagging_source"),
        "confidence_score": t.get("confidence_score"),
        "reviewer_status": t.get("reviewer_status"),
    } for t in pending_tags]

    scope_label = ("explicit paper id(s)" if override_ids
                   else f"phase(s) {sorted(phase_ids)}")
    print(f"In-scope papers: {len(scoped_papers)} via {scope_label} "
          f"(skipped {skipped} out-of-scope). "
          f"Pending questions: {len(questions)}. Pending tags: {len(tags)}.")
    mcq_count = sum(1 for q in questions if (q.get("question_type") or "") == "mcq")
    if mcq_count:
        print(f"  NOTE: {mcq_count} MCQ question(s) in scope. The sweep checks the "
              f"stem and the question row's correct_option_id only — it does NOT "
              f"see pyq_options, so option count/text and the exactly-one-correct "
              f"invariant are NOT validated here. See the module docstring.")
    by_year: dict[Any, int] = {}
    for q in questions:
        by_year[q["year"]] = by_year.get(q["year"], 0) + 1
    print(f"  questions by year: {dict(sorted(by_year.items(), key=lambda kv: str(kv[0])))}")

    if not args.apply:
        print("\nDRY RUN — no files written. Re-run with --apply to write "
              "questions_export.json and tags_export.json.")
        return 0

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    q_path = out_dir / "questions_export.json"
    t_path = out_dir / "tags_export.json"
    q_path.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
    t_path.write_text(json.dumps(tags, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {len(questions)} rows -> {q_path}")
    print(f"wrote {len(tags)} rows -> {t_path}")
    return 0   

# ─── sweep (pure offline) ───────────────────────────────────────────────────
def normalize_text(s: str | None) -> str:
    """Lowercase + collapse whitespace, for per-paper duplicate detection."""
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def has_non_ascii(text: str) -> bool:
    return any(ch not in _PRINTABLE for ch in text)


def question_flags(q: dict, per_paper_norm_counts: dict[str, int],
                   hindi_years: set) -> list[str]:
    """Deterministic checks — each produces a NAMED FLAG, never a verdict.

    A question hitting zero flags is 'clean'. Nothing here promotes a row.
    """
    text = q.get("question_text") or ""
    stripped = text.strip()
    flags: list[str] = []

    if len(stripped) < 15:
        flags.append("empty_or_short")

    if stripped and has_non_ascii(text) and _year_key(q.get("year")) not in hindi_years:
        flags.append("non_ascii_suspect")

    if per_paper_norm_counts.get(normalize_text(text), 0) > 1 and stripped:
        flags.append("duplicate_text")

    if _REPEAT_CHAR.search(text):
        flags.append("suspicious_repeat_char")

    # MCQ-only, and only what the question row itself can tell us: an MCQ with
    # no correct_option_id can never satisfy the projection's
    # exactly-one-correct-option gate, so promoting it to verified produces a
    # question that is verified and still unusable. This does NOT check the
    # options themselves — see the Prelims caveat in the module docstring.
    if (q.get("question_type") or "") == "mcq" and not q.get("correct_option_id"):
        flags.append("mcq_no_correct_option")

    return flags


def tag_flags(t: dict, valid_ids: set[str], orphan_ids: set[str]) -> list[str]:
    """Deterministic tag checks — named flags only, never a verdict."""
    topic_id = t.get("topic_id")
    flags: list[str] = []
    if topic_id not in valid_ids:
        flags.append("unknown_topic")
    elif topic_id in orphan_ids:
        flags.append("orphaned_topic")
    if t.get("tag_role") != "primary":
        flags.append("non_primary")
    return flags


def load_topic_catalog(path: str) -> tuple[set[str], set[str], dict[str, str]]:
    """Load the operator-supplied topic catalog.

    Returns (valid_ids, orphan_ids, id->name). Per Preflight #2, this list is
    NEVER derived — the operator supplies it. ``orphan_ids`` is only populated
    when the catalog explicitly distinguishes pre-split-orphan rows (an entry
    with a truthy ``orphaned``, ``status in {orphan, orphaned, pre_split_orphan}``,
    or ``reviewed`` false); otherwise no row is treated as orphaned and only
    ``unknown_topic`` can fire.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("topic catalog must be a JSON list of {id, ...} objects")
    valid: set[str] = set()
    orphan: set[str] = set()
    names: dict[str, str] = {}
    for e in data:
        tid = e.get("id")
        if not tid:
            continue
        valid.add(tid)
        names[tid] = e.get("text") or e.get("macro_topic") or tid
        status = str(e.get("status") or "").lower()
        if (e.get("orphaned") is True or e.get("reviewed") is False
                or status in {"orphan", "orphaned", "pre_split_orphan"}):
            orphan.add(tid)
    return valid, orphan, names


def _year_key(year: Any) -> str:
    return str(year) if year is not None else ""


def _qnum_sort_key(q: dict) -> tuple:
    n = q.get("question_number")
    try:
        return (0, int(n))
    except (TypeError, ValueError):
        return (1, str(n))


def spread_sample(rows: list[dict], cap: int = 8, frac: float = 0.20) -> list[dict]:
    """Pick a spot-check sample spread across ``rows`` (not just the first N).

    Sample size = min(cap, ceil(frac * count)); ceil guarantees >=1 for any
    non-empty group, capped at ``cap``. Indices are evenly strided so the
    sample is spread across the paper rather than clustered at the start.
    """
    count = len(rows)
    if count == 0:
        return []
    n = min(cap, math.ceil(frac * count))
    if n >= count:
        return list(rows)
    stride = count / n
    picked = []
    seen = set()
    for i in range(n):
        idx = min(count - 1, int(round(i * stride)))
        while idx in seen and idx < count - 1:
            idx += 1
        seen.add(idx)
        picked.append(rows[idx])
    return picked


def _preview(text: str, width: int = 140) -> str:
    one_line = re.sub(r"\s+", " ", (text or "")).strip()
    return one_line[:width]


def build_worksheet(questions: list[dict], tags: list[dict],
                    valid_ids: set[str], orphan_ids: set[str],
                    topic_names: dict[str, str], hindi_years: set) -> list[dict]:
    """Sort every row into clean vs flagged, pick spot-checks, emit worksheet
    rows. Flagged rows are ALWAYS emitted and are NEVER eligible for the
    spot-check (clean-batch) path.
    """
    # Per-paper normalized-text counts, scoped so identical text in DIFFERENT
    # papers does not flag as duplicate.
    per_paper: dict[str, dict[str, int]] = {}
    for q in questions:
        counts = per_paper.setdefault(q.get("paper_id"), {})
        norm = normalize_text(q.get("question_text"))
        if norm:
            counts[norm] = counts.get(norm, 0) + 1

    id_to_year = {q.get("id"): q.get("year") for q in questions}

    q_flags = {q["id"]: question_flags(q, per_paper.get(q.get("paper_id"), {}), hindi_years)
               for q in questions}
    t_flags = {t["id"]: tag_flags(t, valid_ids, orphan_ids) for t in tags}

    # Spot-check sample from CLEAN rows only, per paper, per row type.
    clean_q_by_paper: dict[Any, list[dict]] = {}
    for q in questions:
        if not q_flags[q["id"]]:
            clean_q_by_paper.setdefault(q.get("paper_id"), []).append(q)
    clean_t_by_bucket: dict[Any, list[dict]] = {}
    for t in tags:
        if not t_flags[t["id"]]:
            bucket = id_to_year.get(t.get("question_id"), "unassigned")
            clean_t_by_bucket.setdefault(bucket, []).append(t)

    sampled: set = set()
    for paper_id, rows in clean_q_by_paper.items():
        rows_sorted = sorted(rows, key=_qnum_sort_key)
        for r in spread_sample(rows_sorted):
            sampled.add(r["id"])
    for bucket, rows in clean_t_by_bucket.items():
        rows_sorted = sorted(rows, key=lambda t: str(t.get("topic_id")))
        for r in spread_sample(rows_sorted):
            sampled.add(r["id"])

    def sample_reason(row_id: Any, flags: list[str]) -> str:
        if flags:
            return "flagged"
        return "spot_check" if row_id in sampled else ""

    out: list[dict] = []
    years = sorted({_year_key(q.get("year")) for q in questions}
                   | {_year_key(id_to_year.get(t.get("question_id"))) for t in tags})
    q_by_year: dict[str, list[dict]] = {}
    for q in questions:
        q_by_year.setdefault(_year_key(q.get("year")), []).append(q)
    t_by_year: dict[str, list[dict]] = {}
    for t in tags:
        t_by_year.setdefault(_year_key(id_to_year.get(t.get("question_id"))), []).append(t)

    for yr in years:
        for q in sorted(q_by_year.get(yr, []), key=_qnum_sort_key):
            flags = q_flags[q["id"]]
            out.append({
                "row_type": "question",
                "row_id": q["id"],
                "paper_year": _year_key(q.get("year")),
                "question_number_or_topic_id": q.get("question_number", ""),
                "text_preview": _preview(q.get("question_text", "")),
                "flags": ";".join(flags),
                "sample_reason": sample_reason(q["id"], flags),
                "decision": "",
                "notes": "",
            })
        for t in sorted(t_by_year.get(yr, []), key=lambda t: str(t.get("topic_id"))):
            flags = t_flags[t["id"]]
            tid = t.get("topic_id")
            out.append({
                "row_type": "tag",
                "row_id": t["id"],
                "paper_year": yr,
                "question_number_or_topic_id": tid,
                "text_preview": _preview(topic_names.get(tid, "") or (tid or "")),
                "flags": ";".join(flags),
                "sample_reason": sample_reason(t["id"], flags),
                "decision": "",
                "notes": "",
            })
    return out


def do_sweep(args: argparse.Namespace) -> int:
    if not args.topic_catalog:
        print("error: --topic-catalog is required; the valid-topic-id list is "
              "never derived (Preflight #2).", file=sys.stderr)
        return 2
    try:
        questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
        tags = json.loads(Path(args.tags).read_text(encoding="utf-8"))
        valid_ids, orphan_ids, topic_names = load_topic_catalog(args.topic_catalog)
    except (OSError, ValueError) as exc:
        print(f"error: cannot read inputs — {exc}", file=sys.stderr)
        return 2
    hindi_years = {y.strip() for y in (args.hindi_year or []) if str(y).strip()}

    rows = build_worksheet(questions, tags, valid_ids, orphan_ids, topic_names, hindi_years)

    flagged = sum(1 for r in rows if r["flags"])
    spot = sum(1 for r in rows if r["sample_reason"] == "spot_check")
    clean = len(rows) - flagged
    print(f"{len(rows)} rows: {clean} clean, {flagged} flagged, "
          f"{spot} clean rows sampled for mandatory spot-check.")
    flag_counts: dict[str, int] = {}
    for r in rows:
        for f in (r["flags"].split(";") if r["flags"] else []):
            flag_counts[f] = flag_counts.get(f, 0) + 1
    if flag_counts:
        print(f"  flags: {dict(sorted(flag_counts.items()))}")
    if orphan_ids:
        print(f"  catalog carries {len(orphan_ids)} orphan-marked topic(s).")
    else:
        print("  catalog has no orphan distinction — only unknown_topic can fire.")

    if not args.apply:
        print(f"\nDRY RUN — worksheet not written. Re-run with --apply to write {args.out}.")
        return 0

    out = Path(args.out)
    with out.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=WORKSHEET_FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {len(rows)} rows -> {out}")
    print("Fill 'decision' (verified|rejected|needs_correction) for every row you "
          "promote; blanks stay pending. This CSV is the audit trail — keep it.")
    return 0


# ─── apply ──────────────────────────────────────────────────────────────────
def _kind_for(row_type: str) -> str:
    return QUESTION_KIND if row_type == "question" else TAG_KIND


def do_apply(c: Client, args: argparse.Namespace) -> int:
    with Path(args.worksheet).open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    decided = [r for r in rows if (r.get("decision") or "").strip()]
    bad = [r for r in decided if r["decision"].strip().lower() not in DECISIONS]
    if bad:
        print(f"error: {len(bad)} row(s) have an unrecognized decision. "
              f"Allowed: {sorted(DECISIONS)}", file=sys.stderr)
        for r in bad[:5]:
            print(f"  {r.get('row_id')}: {r.get('decision')!r}", file=sys.stderr)
        return 2

    # Group by paper_year so a bad batch is visible mid-run, not only at the end.
    def batch_key(r: dict) -> str:
        return (r.get("paper_year") or "").strip() or "(unknown)"

    ordered = sorted(rows, key=batch_key)
    skipped_blank = len(rows) - len(decided)
    print(f"{len(decided)} decided of {len(rows)} rows "
          f"({skipped_blank} blank -> skipped, stay pending).")

    if not (args.apply and args.confirm):
        # Dry-run default: report exactly what WOULD happen, write nothing.
        plan: dict[str, dict[str, int]] = {}
        for r in decided:
            plan.setdefault(batch_key(r), {}).setdefault(r["decision"].strip().lower(), 0)
            plan[batch_key(r)][r["decision"].strip().lower()] += 1
        for yr in sorted(plan):
            print(f"  year {yr}: {dict(sorted(plan[yr].items()))}")
        print("\nDRY RUN — nothing written. Re-run with --apply --confirm to PATCH.")
        return 0

    ok = failed = 0
    cur_year = None
    counts = {"verified": 0, "rejected": 0, "needs_correction": 0, "skipped": 0}

    def flush(year: Any) -> None:
        print(f"  year {year}: verified={counts['verified']} "
              f"rejected={counts['rejected']} "
              f"needs_correction={counts['needs_correction']} "
              f"skipped={counts['skipped']}")

    for r in ordered:
        yr = batch_key(r)
        if cur_year is not None and yr != cur_year:
            flush(cur_year)
            for k in counts:
                counts[k] = 0
        cur_year = yr

        decision = (r.get("decision") or "").strip().lower()
        if not decision:
            counts["skipped"] += 1
            continue

        kind = _kind_for((r.get("row_type") or "").strip().lower())
        row_id = (r.get("row_id") or "").strip()
        body: dict[str, Any] = {"reviewer_status": decision}
        note = (r.get("notes") or "").strip()
        if note:
            if len(note) > NOTE_MAX:
                print(f"  warning: note on {row_id} exceeds {NOTE_MAX} chars — "
                      f"truncated client-side.", file=sys.stderr)
                note = note[:NOTE_MAX]
            # Sent for forward-compatibility; the API drops it for both kinds.
            body["reviewer_notes"] = note

        try:
            c.patch(f"{INTEL}/items/{kind}/{row_id}/review", body)
            counts[decision] += 1
            ok += 1
        except RuntimeError as exc:
            print(f"  {row_id}: {exc}", file=sys.stderr)
            failed += 1
        if args.sleep:
            time.sleep(args.sleep)

    if cur_year is not None:
        flush(cur_year)

    print(f"\napplied={ok} failed={failed} "
          f"(reviewer_notes NOT persisted server-side — the worksheet is the "
          f"audit trail).")
    return 1 if failed else 0


# ─── CLI ────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api-base", default=None,
                   help="API base URL (default: $CCP_API_BASE)")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("export", help="pull pending questions + tags for a scope (read-only)")
    e.add_argument("--exam-id", default=DEFAULT_EXAM_ID)
    e.add_argument("--out", default="pyq_review_out",
                   help="directory for questions_export.json / tags_export.json")
    e.add_argument("--exam-phase-id", action="append", default=None,
                   help="scope to papers on this exam phase; repeatable. Any "
                        "phase (Prelims, CSAT, Mains). Overrides "
                        "--mains-phase-id when given.")
    e.add_argument("--mains-phase-id", default=DEFAULT_MAINS_PHASE_ID,
                   help="default phase scope, kept so existing Mains "
                        "invocations are unchanged; ignored when "
                        "--exam-phase-id or --paper-id is supplied")
    e.add_argument("--paper-id", action="append", default=None,
                   help="restrict to these paper id(s); repeatable. These ids "
                        "ARE the scope — no phase filter is also applied.")
    e.add_argument("--status", default="pending")
    e.add_argument("--apply", action="store_true", help="write the export files")

    s = sub.add_parser("sweep", help="offline deterministic checks -> worksheet")
    s.add_argument("--questions", required=True)
    s.add_argument("--tags", required=True)
    s.add_argument("--topic-catalog", required=True,
                   help="operator-supplied valid-topic-id list (never derived)")
    s.add_argument("--out", default="worksheet.csv")
    s.add_argument("--hindi-year", action="append", default=None,
                   help="year(s) whose questions legitimately carry non-ASCII "
                        "(bilingual/Hindi) text; repeatable. Non-ASCII outside "
                        "these years flags as non_ascii_suspect. Confirm from the "
                        "export before trusting a year (e.g. 2023) — never hardcoded.")
    s.add_argument("--apply", action="store_true", help="write the worksheet CSV")

    a = sub.add_parser("apply", help="apply worksheet decisions via the review API")
    a.add_argument("--worksheet", required=True)
    a.add_argument("--exam-id", default=DEFAULT_EXAM_ID)
    a.add_argument("--sleep", type=float, default=0.1,
                   help="delay in seconds between review calls (rate-limit friendly)")
    a.add_argument("--apply", action="store_true")
    a.add_argument("--confirm", action="store_true",
                   help="required WITH --apply to actually PATCH")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cmd == "sweep":
        return do_sweep(args)

    base = args.api_base or os.environ.get("CCP_API_BASE")
    token = os.environ.get("CCP_ADMIN_JWT", "")
    if not base or not token:
        print("error: set CCP_API_BASE and CCP_ADMIN_JWT", file=sys.stderr)
        return 2
    c = Client(base, token)
    handler: Callable[[Client, argparse.Namespace], int] = {
        "export": do_export, "apply": do_apply}[args.cmd]
    return handler(c, args)


if __name__ == "__main__":
    raise SystemExit(main())
