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

    MCQ COVERAGE — READ BEFORE PROMOTING MCQs. ``export`` now fetches
    ``pyq_options`` and ``pyq_stimuli`` alongside the question rows, so the
    sweep sees more than the stem. What it checks, and what it still cannot:

      CHECKED, when ``sweep --options`` is given the exported options file:
        * option count outside 4-5              -> option_count_unexpected
        * no option carries is_correct          -> no_option_marked_correct
        * more than one does                    -> multiple_options_marked_correct
        * two options share normalised text     -> duplicate_option_text
      plus ``mcq_no_correct_option`` from the question row's own
      ``correct_option_id`` — a DIFFERENT source, which can disagree with the
      option rows; that disagreement is itself worth a look.

      NOT CHECKED, and no amount of fetching fixes it: whether the option
      marked correct IS correct. The key is a claim about the world, not a
      structural property, and on a memory-based corpus it is a claim about
      what an aspirant recalled. Only a human with the source paper settles it.

    ABSENCE IS NOT A PASS. ``--options`` is optional; run without it and the
    four checks above do not run at all. The sweep says so on stdout rather
    than letting a clean sheet imply they were evaluated.

    STIMULI. Set questions (DI tables, caselets, comprehension passages,
    arrangement puzzles) share a setup held in ``pyq_stimuli`` and linked
    through ``pyq_question_stimuli``. Without it a member's stem reads as a
    bare question — "Who sits immediate right of R?" — which can be neither
    reviewed nor graded for difficulty. ``export`` resolves the links and
    ``sweep --stimuli`` renders the shared setup into the worksheet's
    ``stimulus_preview`` column, beside each member.

    A clean sweep on an MCQ row therefore means "the stem and the option
    STRUCTURE look sane", NOT "this question is answerable". Answerability is
    enforced downstream by the PYQ->Mock projection's eligibility gate
    (``app/backend/app/admin/pyq_mock_projection.py``,
    ``_check_question_eligibility``; see
    ``docs/runbooks/EI-DATA-01_upsc_2026_primary_topic_tags.md``), and
    correctness is settled only by the spot-check read against the paper.

    catalog ->  build the ``--topic-catalog`` file from the taxonomy: MICROTOPIC
                rows whose ``topics.metadata.exams`` lists any of the
                ``--body`` keys given. ``--body`` is repeatable and UNIONED, so
                one file spans the bodies that share subjects (RBI Grade B /
                SEBI / PFRDA / IFSCA sit on the same Finance, Management,
                Economics, Commerce & Accountancy, Costing and QRE microtopics)
                and a row listing several of them is emitted once. Read-only;
                ``--apply`` writes the file.

    export  ->  pull the pending in-scope questions + tags, plus the options and
                shared stimuli they depend on, from the live API into four flat
                JSON files (read-only).

    sweep   ->  pure offline. Run deterministic checks that only ever FLAG a
                row — they never decide it. Clean rows are sorted from flagged
                rows and a spread spot-check sample is picked per paper. Writes
                one worksheet.csv with blank ``decision``, ``assign_topic_id``
                and ``difficulty`` columns.

    apply   ->  read the worksheet back and issue one call per non-blank field
                per row. Blank fields are skipped. Requires ``--apply --confirm``.

WORKSHEET COLUMNS the operator fills (all blank on write, all independent — a
row may carry any combination, and a blank one is skipped exactly as a blank
decision always has been):

    decision         verified|rejected|needs_correction — the review verdict,
                     PATCHed to the review queue. Unchanged.
    assign_topic_id  a topic id from --topic-catalog. QUESTION ROWS ONLY.
                     Creates a NEW primary topic tag for that question
                     (tag_role='primary', tagging_source='manual'). The new tag
                     is born ``pending`` server-side — assigning it does not
                     verify it; it comes back in the next export for review.
    difficulty       easy|medium|hard, or ``none`` to CLEAR. QUESTION ROWS
                     ONLY. Writes ``pyq_questions.observed_difficulty``.
                     Independent of ``assign_topic_id``: a row may carry a
                     difficulty and no topic id, which is the shape the three
                     already-tagged regulatory exams need. ``none`` PATCHes
                     ``observed_difficulty: null`` — the CMS route validates the
                     field with a falsy check, so NULL passes the vocabulary
                     gate and lands as SQL NULL. A BLANK cell still means
                     "leave this row alone"; clearing must be typed.

    ``very_hard`` IS NOT ACCEPTED and cannot be written through this tool. The
    column is bare ``text`` (migration 032, no CHECK), and migration 239's
    projection to ``mock_question_bank`` recognises only easy|medium|hard —
    anything else is silently rewritten to ``medium`` there, so a ``very_hard``
    would read as ``hard`` in the PYQ heatmap and ``medium`` in the projected
    bank. The CMS route rejects it with a 422; this tool rejects it offline,
    naming the row, before any network call.

    NEW FLAG — ``no_primary_tag``. The sweep's other checks are presence checks
    on the question row; this one is an ABSENCE check across the exported tag
    set: a question with no tag carrying ``tag_role='primary'`` is flagged, so
    it is emitted for a human and is never eligible for the clean/spot-check
    path. It is a named flag like every other — NOT a verdict. Without it a
    paper whose questions have zero tags produced zero tag rows and swept
    entirely clean, which is precisely the state of the 597 verified UPSC
    Prelims GS questions.

    SCOPE CAVEAT for ``no_primary_tag``: it is computed from the tags file the
    export produced, and ``export`` filters tags by ``--status`` (default
    ``pending``). A question whose primary tag is already ``verified`` will
    therefore flag against a pending-only export. Run ``export --status all``
    when you want this flag to describe the corpus rather than the backlog.

Every row that ends up ``verified`` must trace back to EITHER a passed
deterministic check AND a clean batch a human signed off after eyeballing its
spot-check sample, OR an explicit human decision typed into the worksheet. No
step in this tool sets a row to verified by itself.

    THE WORKSHEET CSV IS THE AUDIT TRAIL. The review endpoint does NOT persist
    reviewer_notes for either kind (see below), so the DB row carries no record
    of WHY it was verified. Keep the filled-in CSV — do not discard it after
    ``apply``.

Route contracts this tool depends on (verified against the repo backend):

  catalog reads:
    GET  /api/admin/exam-intelligence-cms/topics?level=microtopic&subject_id&limit&offset
         -> {items:[...], total, limit, offset}; items carry ``metadata``. This
         is the only route that returns it. There is NO server-side predicate on
         ``metadata.exams``, so the body filter is applied client-side; ``level``
         IS a server-side filter, so only leaves cross the wire.

  export reads:
    GET  /api/admin/exam-intelligence-cms/pyq-stimuli?pyq_paper_id=...
         -> {items, total, limit, offset}. Filters by PAPER only — there is no
         question-id filter — so the fetch is per in-scope paper.
    GET  /api/admin/exam-intelligence-cms/pyq-question-stimuli?stimulus_id=...
         -> the question<->stimulus join rows (migration 223). The route
         requires question_id OR stimulus_id (422 without either) and takes no
         paper filter, so it is walked per STIMULUS: one call per passage
         rather than one per question. Each link carries its OWN
         reviewer_status — a link is 'pending' until an operator confirms this
         passage belongs to this question — which the export preserves.
    GET  /api/admin/exam-intelligence-cms/pyq-options?question_id=...
         -> {items, total}. Filters by question only, and caps `limit` at 50
         (le=50), unlike every other CMS list route's 200. Paged at 50.

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

    POST  /api/admin/exam-intelligence-cms/pyq-question-topic-tags
         body {"reason": "...", "payload": {"question_id", "topic_id",
               "tag_role": "primary", "tagging_source": "manual"}}
         (the CMS {reason, payload} envelope — reason is required, 8-500 chars).
         Both FKs are resolved server-side; reviewer_status is FORCED to
         'pending' by the route, so this can never mint a verified tag.
         Unique key is (question_id, topic_id, tag_role) — re-assigning the same
         topic to the same question returns a 409, reported per row, not fatal.
    PATCH /api/admin/exam-intelligence-cms/pyq-questions/{question_id}
         body {"reason": "...", "payload": {"observed_difficulty": "easy"}}
         Same envelope. The route is the ONLY enforcement point for the
         easy|medium|hard vocabulary (no DB CHECK on the column).

Usage:

    export CCP_API_BASE=...      # e.g. https://<host>
    export CCP_ADMIN_JWT=...     # admin/super_admin JWT

    # 0. Catalog (read-only; --apply writes the file). One file for every body
    #    that shares the subject set:
    python scripts/pyq_question_review.py catalog \
        --body rbi --body sebi --body pfrda --body ifsca \
        --out topic_catalog_regulatory.json --apply

    # --timeout is global and defaults to 180s (free-tier Render cold starts):
    python scripts/pyq_question_review.py --timeout 300 catalog --body rbi

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
        --stimuli review_out/stimuli_export.json \
        --options review_out/options_export.json \
        --topic-catalog <path/to/topic_catalog.json> \
        --out worksheet.csv --apply

    # ... a human opens worksheet.csv and fills decision / assign_topic_id /
    #     difficulty (+ notes) ...

    # 3. Apply (dry-run by default; needs BOTH flags to write).
    #    --topic-catalog is REQUIRED: every non-blank assign_topic_id is
    #    validated against it, and an unknown id aborts the whole run before
    #    the first network call.
    python scripts/pyq_question_review.py apply --worksheet worksheet.csv \
        --exam-id <uuid> --topic-catalog <path/to/topic_catalog.json>
    python scripts/pyq_question_review.py apply --worksheet worksheet.csv \
        --exam-id <uuid> --topic-catalog <path/to/topic_catalog.json> \
        --apply --confirm

export needs ``exam_intelligence.review`` (items route) + ``exam_intelligence.cms``
(pyq-questions / pyq-papers / sections). apply needs ``exam_intelligence.review``
for decisions, plus ``exam_intelligence.cms`` when any row carries an
assign_topic_id or a difficulty.
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
REASON_MAX = 500  # WriteEnvelope.reason max_length (min 8); over this the CMS 422s.

# The ONLY values accepted in the ``difficulty`` column. This mirrors
# ``_OBSERVED_DIFFICULTIES`` in app/backend/app/api/admin_exam_intel_cms.py,
# which is the sole enforcement point for the column (migration 032 declares
# ``pyq_questions.observed_difficulty`` bare ``text``, with no CHECK).
# ``very_hard`` is deliberately absent and must stay absent: migration 239's
# projection to mock_question_bank recognises only these three and silently
# rewrites anything else to 'medium', so a ``very_hard`` would mean "hard" in
# the PYQ heatmap and "medium" in the practice bank. It cannot be written
# through this tool — the offline check below rejects the run.
DIFFICULTIES = {"easy", "medium", "hard"}

# Typed in the ``difficulty`` column to CLEAR a previously written value back to
# SQL NULL. A BLANK cell has always meant "leave this row alone" and must keep
# meaning that — an operator who never touches the column must not wipe the
# corpus — so clearing needs its own explicit token. The CMS route validates
# ``observed_difficulty`` with a FALSY check
# (``admin_exam_intel_cms.py:2148``: ``if patch.get("observed_difficulty") and
# ... not in _OBSERVED_DIFFICULTIES``), so ``None`` passes the vocabulary gate
# and is written straight through as NULL; the key survives the
# ``_QUESTION_FIELDS`` filter because that filter tests key names, not values.
DIFFICULTY_CLEAR = "none"

# Catalogue rows are microtopic-level ONLY (see ``load_topic_catalog``). A
# top-level topic id tagged onto a question routes ``mock_question_bank`` to the
# parent rather than the leaf, which migration 270 exists to undo.
MICROTOPIC_LEVEL = "microtopic"

QUESTION_KIND = "pyq_question"
TAG_KIND = "pyq_question_topic_tag"
QUESTION_ROW = "question"

# tag_role/tagging_source for a tag this tool creates. The point of the
# ``no_primary_tag`` flag is a MISSING primary tag, and the worksheet is typed
# by a human, so both are fixed rather than operator-settable.
ASSIGN_TAG_ROLE = "primary"
ASSIGN_TAGGING_SOURCE = "manual"

_TAG_CREATE_REASON = "pyq_question_review worksheet: assign primary topic tag"
_DIFFICULTY_REASON = "pyq_question_review worksheet: set observed_difficulty"
_DIFFICULTY_CLEAR_REASON = "pyq_question_review worksheet: clear observed_difficulty"

# ``decision`` stays first among the operator-filled columns and the columns
# that existed before keep their order — the two new ones are APPENDED, so a
# worksheet written by an older run still reads back cleanly.
WORKSHEET_FIELDS = [
    "row_type", "row_id", "paper_year", "question_number_or_topic_id",
    "text_preview", "flags", "sample_reason", "decision", "notes",
    "assign_topic_id", "difficulty",
    # APPENDED (stimulus/option pass): the shared passage, caselet or DI table a
    # set member depends on. Blank when the question has no stimulus, and blank
    # for every row when `sweep` is run without --stimuli, so a worksheet from
    # an older export still reads back cleanly.
    "stimulus_preview",
]

# Expected option count for an MCQ in these papers. Four is the norm; five
# appears in RBI/SEBI sets that carry an "all of the above"/"none" choice.
# Outside this range is FLAGGED for a human, never corrected here.
_MCQ_OPTION_RANGE = (4, 5)

# `/pyq-options` caps `limit` at 50 (le=50 in admin_exam_intel_cms.py:2188),
# unlike every other CMS list route, which allows 200. Paging it at the usual
# 200 returns a 422, so the option fetch pages at this value instead.
_OPTIONS_PAGE = 50

# Printable ASCII the sweep treats as clean; \t \n \r are allowed whitespace.
_PRINTABLE = set(chr(c) for c in range(0x20, 0x7F)) | {"\t", "\n", "\r"}
_REPEAT_CHAR = re.compile(r"(\S)\1{3,}")


# ─── HTTP client (mirrors scripts/syllabus_mention_review.py) ─────────────────
# Default HTTP timeout. The API is deployed on a free Render instance that
# spins down when idle: the first request of a session pays a cold start that
# routinely runs past a 60s budget, and the export/apply loops issue hundreds of
# requests, so a spurious first-call timeout costs the whole run.
DEFAULT_TIMEOUT = 180


class Client:
    def __init__(self, base: str, token: str, timeout: int = DEFAULT_TIMEOUT) -> None:
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

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """Used only by ``apply`` for the CMS tag-create route."""
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        r = self.session.post(f"{self.base}{path}", data=data, timeout=self.timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"POST {path} -> {r.status_code}: {r.text[:300]}")
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

    # ── stimuli + their question links ──────────────────────────────────────
    # `/pyq-stimuli` filters by pyq_paper_id ONLY (no question filter), so the
    # fetch is per in-scope paper. The question<->stimulus link is a join table,
    # `pyq_question_stimuli`, whose route requires question_id OR stimulus_id
    # and takes no paper filter — so it is walked per STIMULUS, which is one
    # call per passage rather than one per question.
    stimuli: list[dict] = []
    link_rows: list[dict] = []
    for pid in sorted(scoped_paper_ids):
        for st in c.all_items(f"{CMS}/pyq-stimuli", {"pyq_paper_id": pid}):
            if not st.get("id"):
                continue
            links = [
                lk for lk in c.all_items(f"{CMS}/pyq-question-stimuli",
                                         {"stimulus_id": st["id"]})
                if lk.get("question_id") in scoped_question_ids
            ]
            link_rows.extend(links)
            stimuli.append({
                "id": st.get("id"),
                "paper_id": st.get("pyq_paper_id"),
                "section_id": st.get("section_id"),
                "stimulus_type": st.get("stimulus_type"),
                "content_text": st.get("content_text"),
                "language": st.get("language"),
                "display_order": st.get("display_order"),
                "reviewer_status": st.get("reviewer_status"),
                # Resolved here so the file is self-describing and the sweep
                # needs no second join. Scoped to the exported questions.
                "question_ids": sorted({lk["question_id"] for lk in links}),
                # The LINK carries its own reviewer_status (migration 223): a
                # link is 'pending' until an operator confirms this passage is
                # the right one for this question. Kept per question so a
                # reviewer can see an unverified association.
                "link_status_by_question": {
                    lk["question_id"]: lk.get("reviewer_status") for lk in links
                },
            })

    # ── options ─────────────────────────────────────────────────────────────
    # `/pyq-options` filters by question_id only — no paper or bulk filter — so
    # this is one call per in-scope question, paged at _OPTIONS_PAGE (the route
    # caps limit at 50, not the usual 200).
    options: list[dict] = []
    for qid in sorted(scoped_question_ids):
        for o in c.all_items(f"{CMS}/pyq-options", {"question_id": qid},
                             page=_OPTIONS_PAGE):
            options.append({
                "id": o.get("id"),
                "question_id": qid,
                "option_label": o.get("option_label"),
                "option_text": o.get("option_text"),
                "is_correct": o.get("is_correct"),
                "display_order": o.get("display_order"),
                "source_label": o.get("source_label"),
                "reviewer_status": o.get("reviewer_status"),
            })

    scope_label = ("explicit paper id(s)" if override_ids
                   else f"phase(s) {sorted(phase_ids)}")
    print(f"In-scope papers: {len(scoped_papers)} via {scope_label} "
          f"(skipped {skipped} out-of-scope). "
          f"Pending questions: {len(questions)}. Pending tags: {len(tags)}.")
    mcq_count = sum(1 for q in questions if (q.get("question_type") or "") == "mcq")
    if mcq_count:
        with_opts = len({o["question_id"] for o in options})
        print(f"  {mcq_count} MCQ question(s) in scope; {len(options)} option row(s) "
              f"across {with_opts} question(s). Pass options_export.json to `sweep "
              f"--options` to run the option checks.")
    if stimuli:
        covered = len({q for st in stimuli for q in st["question_ids"]})
        unverified = sum(
            1 for st in stimuli
            for stt in st["link_status_by_question"].values() if stt != "verified"
        )
        print(f"  {len(stimuli)} stimulus/stimuli covering {covered} question(s); "
              f"{len(link_rows)} link(s), {unverified} not yet verified.")
    else:
        print("  no stimuli on the in-scope paper(s).")
    by_year: dict[Any, int] = {}
    for q in questions:
        by_year[q["year"]] = by_year.get(q["year"], 0) + 1
    print(f"  questions by year: {dict(sorted(by_year.items(), key=lambda kv: str(kv[0])))}")

    if not args.apply:
        print("\nDRY RUN — no files written. Re-run with --apply to write "
              "questions_export.json, tags_export.json, stimuli_export.json "
              "and options_export.json.")
        return 0

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    q_path = out_dir / "questions_export.json"
    t_path = out_dir / "tags_export.json"
    s_path = out_dir / "stimuli_export.json"
    o_path = out_dir / "options_export.json"
    q_path.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
    t_path.write_text(json.dumps(tags, ensure_ascii=False, indent=2), encoding="utf-8")
    # Written unconditionally, empty list included: an absent file and an empty
    # one mean different things to `sweep`, and only the empty file says "we
    # looked and there were none".
    s_path.write_text(json.dumps(stimuli, ensure_ascii=False, indent=2), encoding="utf-8")
    o_path.write_text(json.dumps(options, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {len(stimuli)} rows -> {s_path}")
    print(f"wrote {len(options)} rows -> {o_path}")
    print(f"wrote {len(questions)} rows -> {q_path}")
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


def option_flags(q: dict, options: list[dict]) -> list[str]:
    """Option-level checks for one question. NAMED FLAGS, never verdicts.

    MCQ-only. A descriptive question legitimately carries no options, so
    running these against one would flag the whole descriptive corpus.

    Callers pass the options for THIS question only. An empty list is
    meaningful (an MCQ with no option rows) and is reported as
    ``option_count_unexpected`` — the count is zero, which is outside the
    expected range like any other wrong count.

    None of these can fire when ``sweep`` runs without ``--options``: the
    caller passes ``None`` and this returns ``[]``, so a worksheet built from
    an older export is unchanged rather than silently under-flagged.
    """
    if (q.get("question_type") or "") != "mcq" or options is None:
        return []
    flags: list[str] = []

    lo, hi = _MCQ_OPTION_RANGE
    if not (lo <= len(options) <= hi):
        flags.append("option_count_unexpected")

    correct = [o for o in options if o.get("is_correct") is True]
    if not correct:
        flags.append("no_option_marked_correct")
    elif len(correct) > 1:
        flags.append("multiple_options_marked_correct")

    seen: set[str] = set()
    for o in options:
        norm = normalize_text(o.get("option_text"))
        if not norm:
            continue
        if norm in seen:
            flags.append("duplicate_option_text")
            break
        seen.add(norm)

    return flags


def index_options_by_question(options: list[dict] | None) -> dict[str, list[dict]] | None:
    """``question_id -> [option rows]``. ``None`` in, ``None`` out, so the
    "no --options supplied" case stays distinguishable from "no options"."""
    if options is None:
        return None
    by_q: dict[str, list[dict]] = {}
    for o in options:
        qid = o.get("question_id")
        if qid:
            by_q.setdefault(qid, []).append(o)
    return by_q


def index_stimuli_by_question(stimuli: list[dict] | None) -> dict[str, list[dict]]:
    """``question_id -> [stimulus rows]``, read from each stimulus's
    ``question_ids`` list (which ``export`` resolves through
    ``pyq_question_stimuli``). Empty dict when no stimuli were supplied."""
    by_q: dict[str, list[dict]] = {}
    for st in (stimuli or []):
        for qid in (st.get("question_ids") or []):
            by_q.setdefault(qid, []).append(st)
    return by_q


def stimulus_preview(stimuli_for_q: list[dict], width: int = 220) -> str:
    """One cell a human can read next to the member question.

    A set member's stem is often meaningless alone ("Who sits immediate right
    of R?"); the shared setup is what makes it gradeable. Several stimuli are
    joined in display order, each tagged with its type so a passage and a chart
    are distinguishable.
    """
    if not stimuli_for_q:
        return ""
    parts = []
    for st in sorted(stimuli_for_q, key=lambda s: (
            s.get("display_order") is None, s.get("display_order") or 0, str(s.get("id")))):
        kind = str(st.get("stimulus_type") or "stimulus")
        parts.append(f"[{kind}] {_preview(st.get('content_text') or '', width)}")
    return " || ".join(parts)


def index_tags_by_question(tags: list[dict]) -> dict[Any, list[dict]]:
    """question_id -> its tag rows, for the absence check below.

    ``tag_flags`` can only ever speak about a tag that EXISTS. A question with
    no tags at all produces no tag row, so before this index the sweep was
    structurally blind to it: an entirely untagged paper swept clean.
    """
    index: dict[Any, list[dict]] = {}
    for t in tags:
        index.setdefault(t.get("question_id"), []).append(t)
    return index


def has_primary_tag(question_id: Any, tags_by_question: dict[Any, list[dict]]) -> bool:
    return any((t.get("tag_role") or "") == "primary"
               for t in tags_by_question.get(question_id, ()))


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
    NEVER derived from the corpus — either the operator writes it by hand or the
    ``catalog`` subcommand builds it from the taxonomy (which is not the same
    thing as deriving it from the questions being reviewed).
    ``orphan_ids`` is only populated when the catalog explicitly distinguishes
    pre-split-orphan rows (an entry with a truthy ``orphaned``, ``status in
    {orphan, orphaned, pre_split_orphan}``, or ``reviewed`` false); otherwise no
    row is treated as orphaned and only ``unknown_topic`` can fire.

    MICROTOPIC-ONLY, strict when known. A row carrying an explicit ``level``
    that is not ``microtopic`` aborts the load by name: assigning a top-level
    topic id routes the projected ``mock_question_bank`` row to the parent
    instead of the leaf, which is exactly the drift migration 270 had to repair.
    A row with NO ``level`` key is accepted unchanged — the hand-written UPSC
    catalogues are flat ``[{id, text}]`` and predate the field, so this can only
    reject a catalogue that states a level and states a wrong one.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("topic catalog must be a JSON list of {id, ...} objects")
    valid: set[str] = set()
    orphan: set[str] = set()
    names: dict[str, str] = {}
    non_leaf: list[str] = []
    for e in data:
        tid = e.get("id")
        if not tid:
            continue
        level = e.get("level")
        if level is not None and str(level).strip().lower() != MICROTOPIC_LEVEL:
            non_leaf.append(f"{tid} (level={level!r})")
            continue
        valid.add(tid)
        names[tid] = e.get("text") or e.get("name") or e.get("macro_topic") or tid
        status = str(e.get("status") or "").lower()
        if (e.get("orphaned") is True or e.get("reviewed") is False
                or status in {"orphan", "orphaned", "pre_split_orphan"}):
            orphan.add(tid)
    if non_leaf:
        shown = ", ".join(non_leaf[:10])
        more = f" (and {len(non_leaf) - 10} more)" if len(non_leaf) > 10 else ""
        raise ValueError(
            f"topic catalog carries {len(non_leaf)} non-microtopic row(s): {shown}{more}. "
            f"Only level={MICROTOPIC_LEVEL!r} ids may be assigned; rebuild with "
            f"`catalog` (which emits leaves only) or drop the parent rows."
        )
    return valid, orphan, names


# ─── catalog (build the --topic-catalog file) ─────────────────────────────
def catalog_rows(topics: Iterable[dict], bodies: Iterable[str]) -> list[dict]:
    """Narrow taxonomy rows to the catalogue this tool will accept.

    Conjunctive, and both halves matter:

    * ``level == 'microtopic'`` — leaves only, the same rule the UPSC
      catalogues follow and ``load_topic_catalog`` now enforces on read.
    * ``metadata.exams`` INTERSECTS ``bodies`` — a UNION across the requested
      body keys, not one exam. ``topics.metadata.exams`` is a LIST of body keys
      (``269_gap_microtopics.sql:60`` seeds ``{"tier":"official","exams":["upsc"]}``;
      ``propose_pyq_topic_tags.py`` documents ``{"exams": ["sebi", "pfrda"]}``),
      precisely because the regulatory bodies SHARE subjects — RBI Grade B sits
      on the same Finance / Management / Economics / Commerce & Accountancy /
      Costing / QRE rows as SEBI, PFRDA and IFSCA. Matching one body at a time
      and concatenating would emit a row once per body it lists; intersecting
      once emits each row exactly once.

    Inactive rows are dropped (``is_active`` false), a missing ``is_active`` is
    treated as active. Matching is case-folded on both sides. Sorted by
    (subject_id, name, id) so the file is byte-stable across runs.
    """
    wanted = {str(b).strip().casefold() for b in bodies if str(b).strip()}
    if not wanted:
        raise ValueError("catalog_rows: at least one body key is required")
    out: list[dict] = []
    for t in topics:
        if str(t.get("level") or "").strip().lower() != MICROTOPIC_LEVEL:
            continue
        if t.get("is_active") is False:
            continue
        meta = t.get("metadata")
        exams = (meta or {}).get("exams") if isinstance(meta, dict) else None
        if not isinstance(exams, (list, tuple, set)):
            continue
        listed = {str(x).strip().casefold() for x in exams if str(x).strip()}
        matched = sorted(listed & wanted)
        if not matched:
            continue
        out.append({
            "id": t.get("id"),
            "text": t.get("name") or t.get("slug") or t.get("id"),
            "slug": t.get("slug"),
            "subject_id": t.get("subject_id"),
            "level": MICROTOPIC_LEVEL,
            "exams": matched,
        })
    out.sort(key=lambda r: (str(r.get("subject_id") or ""), str(r.get("text") or ""),
                            str(r.get("id") or "")))
    return out


def do_catalog(c: Client, args: argparse.Namespace) -> int:
    """Build a microtopic-only ``--topic-catalog`` file for one or more bodies.

    Read-only against ``GET {CMS}/topics``, which is the only route that returns
    ``metadata`` (``admin_exam_intel_cms.py:3358``). It has no server-side
    predicate on ``metadata.exams``, so the body filter is applied client-side;
    ``level`` IS a server-side filter, so the leaf narrowing happens in the query
    and only leaves cross the wire.
    """
    bodies = [b for b in (args.body or []) if str(b).strip()]
    if not bodies:
        print("error: at least one --body is required (the key to match against "
              "topics.metadata.exams, e.g. --body rbi).", file=sys.stderr)
        return 2

    params: dict[str, Any] = {"level": MICROTOPIC_LEVEL}
    if args.is_active:
        params["is_active"] = "true"
    subject_ids = [s for s in (args.subject_id or []) if str(s).strip()]
    topics: list[dict] = []
    if subject_ids:
        for sid in subject_ids:
            topics.extend(c.all_items(f"{CMS}/topics", {**params, "subject_id": sid}))
    else:
        topics.extend(c.all_items(f"{CMS}/topics", params))

    rows = catalog_rows(topics, bodies)
    by_body: dict[str, int] = {}
    for r in rows:
        for b in r["exams"]:
            by_body[b] = by_body.get(b, 0) + 1
    subjects = {r["subject_id"] for r in rows if r.get("subject_id")}

    print(f"topics fetched: {len(topics)} (level={MICROTOPIC_LEVEL})")
    print(f"catalog rows:   {len(rows)} across {len(subjects)} subject(s)")
    print(f"bodies:         {dict(sorted(by_body.items()))}")
    shared = sum(1 for r in rows if len(r["exams"]) > 1)
    print(f"shared rows:    {shared} carry more than one of the requested bodies "
          f"(emitted ONCE each)")
    if not rows:
        print("error: no microtopic carries any of the requested bodies in "
              "metadata.exams — nothing to write.", file=sys.stderr)
        return 1

    if not args.apply:
        for r in rows[:10]:
            print(f"  {r['id']}  {r['text'][:70]}  exams={r['exams']}")
        if len(rows) > 10:
            print(f"  ... and {len(rows) - 10} more")
        print("\nDRY RUN — nothing written. Re-run with --apply to write the file.")
        return 0

    out = Path(args.out)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    print(f"\nwrote {len(rows)} microtopic rows -> {out}")
    return 0


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
                    topic_names: dict[str, str], hindi_years: set,
                    stimuli: list[dict] | None = None,
                    options: list[dict] | None = None) -> list[dict]:
    """Sort every row into clean vs flagged, pick spot-checks, emit worksheet
    rows. Flagged rows are ALWAYS emitted and are NEVER eligible for the
    spot-check (clean-batch) path.

    Question rows additionally carry ``no_primary_tag`` — an ABSENCE check
    against the question_id -> tags index, deliberately parallel to the
    presence checks in ``question_flags``. It is a named flag, not a verdict:
    a flagged question is emitted for a human exactly like any other flagged
    row, and is excluded from the clean/spot-check path. See the module
    docstring for the ``export --status`` caveat.
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

    tags_by_question = index_tags_by_question(tags)
    opts_by_question = index_options_by_question(options)
    stim_by_question = index_stimuli_by_question(stimuli)

    q_flags: dict[Any, list[str]] = {}
    for q in questions:
        flags = question_flags(q, per_paper.get(q.get("paper_id"), {}), hindi_years)
        if not has_primary_tag(q["id"], tags_by_question):
            flags.append("no_primary_tag")
        # Option-level flags join the same list, so an option defect excludes
        # the row from the clean/spot-check path exactly like a stem defect.
        flags.extend(option_flags(
            q, None if opts_by_question is None else opts_by_question.get(q["id"], [])))
        q_flags[q["id"]] = flags
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
                "assign_topic_id": "",
                "difficulty": "",
                "stimulus_preview": stimulus_preview(stim_by_question.get(q["id"], [])),
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
                # Blank on tag rows too, so the CSV stays rectangular; both are
                # rejected on apply if a tag row carries one.
                "assign_topic_id": "",
                "difficulty": "",
                # A stimulus belongs to a question, never to a tag.
                "stimulus_preview": "",
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
        # Both optional: a worksheet built from an older export (no stimuli or
        # options files) is byte-identical to what it was, minus an empty new
        # column. Absent options means the option checks do not run — NOT that
        # they ran and passed.
        stimuli = (json.loads(Path(args.stimuli).read_text(encoding="utf-8"))
                   if args.stimuli else None)
        options = (json.loads(Path(args.options).read_text(encoding="utf-8"))
                   if args.options else None)
    except (OSError, ValueError) as exc:
        print(f"error: cannot read inputs — {exc}", file=sys.stderr)
        return 2
    hindi_years = {y.strip() for y in (args.hindi_year or []) if str(y).strip()}

    rows = build_worksheet(questions, tags, valid_ids, orphan_ids, topic_names,
                           hindi_years, stimuli=stimuli, options=options)

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

    mcqs = sum(1 for q in questions if (q.get("question_type") or "") == "mcq")
    if options is None:
        print(f"  NO --options supplied: the option checks did NOT run for "
              f"{mcqs} MCQ(s). Absent is not the same as passed.")
    else:
        print(f"  option checks ran over {len(options)} option row(s) for {mcqs} MCQ(s).")
    if stimuli is None:
        print("  NO --stimuli supplied: stimulus_preview is blank on every row, "
              "so a set member's shared setup is not visible to the grader.")
    else:
        linked = len({qid for st in stimuli for qid in (st.get("question_ids") or [])})
        print(f"  {len(stimuli)} stimulus/stimuli covering {linked} question(s).")

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
          "promote; blanks stay pending. On QUESTION rows you may also fill "
          "'assign_topic_id' (a topic id from the catalog -> creates a pending "
          "primary tag) and 'difficulty' (easy|medium|hard, or 'none' to clear "
          "an existing value). This CSV is the audit trail — keep it.")
    return 0


# ─── apply ──────────────────────────────────────────────────────────────────
def _kind_for(row_type: str) -> str:
    return QUESTION_KIND if row_type == QUESTION_ROW else TAG_KIND


def _cell(row: dict, key: str) -> str:
    """Read one worksheet cell. Missing key == blank, which is what makes a
    worksheet written before ``assign_topic_id``/``difficulty`` existed apply
    exactly as it did then."""
    return (row.get(key) or "").strip()


def _write_reason(base: str, note: str) -> str:
    """Build a CMS WriteEnvelope.reason (required, 8-500 chars).

    ``base`` alone always clears the 8-char floor; the operator's note is
    appended when present so the audit row carries their words, and the whole
    thing is capped at the API's limit.
    """
    reason = f"{base} — {note}" if note else base
    return reason[:REASON_MAX]


def _validate_worksheet(rows: list[dict], valid_topic_ids: set[str]) -> list[str]:
    """Every offline check apply makes, run BEFORE the first network call.

    Returns a list of human-readable errors. A non-empty list aborts the whole
    run — a half-applied worksheet with an unknown topic id partway through is
    worse than one that never started.
    """
    errors: list[str] = []

    bad_decision = [r for r in rows
                    if _cell(r, "decision") and _cell(r, "decision").lower() not in DECISIONS]
    for r in bad_decision:
        errors.append(f"row {_cell(r, 'row_id') or '(no row_id)'}: decision "
                      f"{_cell(r, 'decision')!r} is not one of {sorted(DECISIONS)}")

    for r in rows:
        row_id = _cell(r, "row_id") or "(no row_id)"
        row_type = _cell(r, "row_type").lower()
        topic_id = _cell(r, "assign_topic_id")
        difficulty = _cell(r, "difficulty").lower()

        # Both new columns are question-only. A value typed on a tag row is an
        # operator mistake that would otherwise vanish silently, so it aborts.
        if row_type != QUESTION_ROW:
            if topic_id:
                errors.append(f"row {row_id}: assign_topic_id is only meaningful on "
                              f"question rows (row_type={row_type or '(blank)'!s})")
            if difficulty:
                errors.append(f"row {row_id}: difficulty is only meaningful on "
                              f"question rows (row_type={row_type or '(blank)'!s})")
            continue

        if difficulty and difficulty not in DIFFICULTIES | {DIFFICULTY_CLEAR}:
            hint = ""
            if difficulty == "very_hard":
                hint = (" — 'very_hard' is NOT a valid observed_difficulty: the "
                        "PYQ->mock projection rewrites it to 'medium' while the "
                        "heatmap reads it as 'hard'. Use 'hard'.")
            errors.append(f"row {row_id}: difficulty {_cell(r, 'difficulty')!r} is not "
                          f"one of {sorted(DIFFICULTIES)} "
                          f"(or {DIFFICULTY_CLEAR!r} to clear it){hint}")

        if topic_id and topic_id not in valid_topic_ids:
            errors.append(f"row {row_id}: assign_topic_id {topic_id!r} is not in the "
                          f"topic catalog")

    return errors


def do_apply(c: Client, args: argparse.Namespace) -> int:
    # The valid-topic-id list is never derived, on apply exactly as on sweep
    # (Preflight #2). Required even when no row carries an assign_topic_id —
    # the operator should not discover the requirement mid-run.
    catalog_path = getattr(args, "topic_catalog", None)
    if not catalog_path:
        print("error: --topic-catalog is required on apply; every assign_topic_id "
              "is validated against it before any network call.", file=sys.stderr)
        return 2
    try:
        valid_topic_ids, _orphan_ids, _names = load_topic_catalog(catalog_path)
    except (OSError, ValueError) as exc:
        print(f"error: cannot read topic catalog — {exc}", file=sys.stderr)
        return 2

    with Path(args.worksheet).open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    errors = _validate_worksheet(rows, valid_topic_ids)
    if errors:
        print(f"error: {len(errors)} invalid worksheet cell(s) — nothing was sent.",
              file=sys.stderr)
        for e in errors[:20]:
            print(f"  {e}", file=sys.stderr)
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more", file=sys.stderr)
        return 2

    def actions(r: dict) -> tuple[str, str, str]:
        """(decision, assign_topic_id, difficulty), each canonical or blank."""
        return (_cell(r, "decision").lower(),
                _cell(r, "assign_topic_id"),
                _cell(r, "difficulty").lower())

    acting = [r for r in rows if any(actions(r))]

    # Group by paper_year so a bad batch is visible mid-run, not only at the end.
    def batch_key(r: dict) -> str:
        return (r.get("paper_year") or "").strip() or "(unknown)"

    ordered = sorted(rows, key=batch_key)
    skipped_blank = len(rows) - len(acting)
    print(f"{len(acting)} actionable of {len(rows)} rows "
          f"({skipped_blank} blank -> skipped, stay pending).")

    if not (args.apply and args.confirm):
        # Dry-run default: report exactly what WOULD happen, write nothing.
        plan: dict[str, dict[str, int]] = {}
        for r in acting:
            decision, topic_id, difficulty = actions(r)
            bucket = plan.setdefault(batch_key(r), {})
            for key in ([decision] if decision else []):
                bucket[key] = bucket.get(key, 0) + 1
            if topic_id:
                bucket["assign_topic_id"] = bucket.get("assign_topic_id", 0) + 1
            if difficulty:
                bucket[f"difficulty:{difficulty}"] = bucket.get(f"difficulty:{difficulty}", 0) + 1
        for yr in sorted(plan):
            print(f"  year {yr}: {dict(sorted(plan[yr].items()))}")
        print("\nDRY RUN — nothing written. Re-run with --apply --confirm to PATCH.")
        return 0

    ok = failed = 0
    cur_year = None
    counts = {"verified": 0, "rejected": 0, "needs_correction": 0,
              "tagged": 0, "difficulty": 0, "difficulty_cleared": 0, "skipped": 0}

    def flush(year: Any) -> None:
        print(f"  year {year}: verified={counts['verified']} "
              f"rejected={counts['rejected']} "
              f"needs_correction={counts['needs_correction']} "
              f"tagged={counts['tagged']} "
              f"difficulty={counts['difficulty']} "
              f"difficulty_cleared={counts['difficulty_cleared']} "
              f"skipped={counts['skipped']}")

    def pause() -> None:
        if args.sleep:
            time.sleep(args.sleep)

    for r in ordered:
        yr = batch_key(r)
        if cur_year is not None and yr != cur_year:
            flush(cur_year)
            for k in counts:
                counts[k] = 0
        cur_year = yr

        decision, topic_id, difficulty = actions(r)
        if not (decision or topic_id or difficulty):
            counts["skipped"] += 1
            continue

        kind = _kind_for(_cell(r, "row_type").lower())
        row_id = _cell(r, "row_id")
        note = _cell(r, "notes")
        row_failed = False

        # Content edits run BEFORE the verdict: a decision is the promotion, so
        # a question whose difficulty or tag write failed must not be verified
        # on the strength of a worksheet row that only half landed.
        if difficulty:
            clearing = difficulty == DIFFICULTY_CLEAR
            try:
                c.patch(f"{CMS}/pyq-questions/{row_id}",
                        {"reason": _write_reason(
                            _DIFFICULTY_CLEAR_REASON if clearing else _DIFFICULTY_REASON, note),
                         "payload": {"observed_difficulty": None if clearing else difficulty}})
                counts["difficulty_cleared" if clearing else "difficulty"] += 1
                ok += 1
            except RuntimeError as exc:
                print(f"  {row_id}: difficulty — {exc}", file=sys.stderr)
                failed += 1
                row_failed = True
            pause()

        if topic_id and not row_failed:
            try:
                c.post(f"{CMS}/pyq-question-topic-tags",
                       {"reason": _write_reason(_TAG_CREATE_REASON, note),
                        "payload": {"question_id": row_id, "topic_id": topic_id,
                                    "tag_role": ASSIGN_TAG_ROLE,
                                    "tagging_source": ASSIGN_TAGGING_SOURCE}})
                counts["tagged"] += 1
                ok += 1
            except RuntimeError as exc:
                print(f"  {row_id}: assign_topic_id — {exc}", file=sys.stderr)
                failed += 1
                row_failed = True
            pause()

        if decision and not row_failed:
            body: dict[str, Any] = {"reviewer_status": decision}
            if note:
                sent = note
                if len(sent) > NOTE_MAX:
                    print(f"  warning: note on {row_id} exceeds {NOTE_MAX} chars — "
                          f"truncated client-side.", file=sys.stderr)
                    sent = sent[:NOTE_MAX]
                # Sent for forward-compatibility; the API drops it for both kinds.
                body["reviewer_notes"] = sent
            try:
                c.patch(f"{INTEL}/items/{kind}/{row_id}/review", body)
                counts[decision] += 1
                ok += 1
            except RuntimeError as exc:
                print(f"  {row_id}: {exc}", file=sys.stderr)
                failed += 1
            pause()
        elif decision:
            print(f"  {row_id}: decision {decision!r} SKIPPED — an earlier write on "
                  f"this row failed; the row stays pending.", file=sys.stderr)
            counts["skipped"] += 1

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
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                   help=f"per-request HTTP timeout in seconds (default "
                        f"{DEFAULT_TIMEOUT}). The API is on a free Render "
                        f"instance that spins down when idle, so the first "
                        f"request of a run pays a cold start well past the 60s "
                        f"the client used to allow. Applies to every GET, PATCH "
                        f"and POST; ignored by the offline `sweep`.")
    sub = p.add_subparsers(dest="cmd", required=True)

    cat = sub.add_parser("catalog", help="build a microtopic-only --topic-catalog "
                                         "file for one or more exam bodies")
    cat.add_argument("--body", action="append", default=None, required=True,
                     help="body key to match against topics.metadata.exams; "
                          "REPEATABLE and UNIONED, so one file can span the "
                          "bodies that share subjects (e.g. --body rbi --body "
                          "sebi --body pfrda --body ifsca). A microtopic listing "
                          "several of them is emitted once.")
    cat.add_argument("--subject-id", action="append", default=None,
                     help="restrict to these subject id(s); repeatable. Omit to "
                          "read every microtopic in the taxonomy and let the "
                          "body filter do the narrowing.")
    cat.add_argument("--is-active", action="store_true", default=False,
                     help="ask the API for is_active=true rows only; inactive "
                          "rows are dropped client-side regardless.")
    cat.add_argument("--out", default="topic_catalog.json")
    cat.add_argument("--apply", action="store_true", help="write the catalog file")

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
    s.add_argument("--stimuli", default=None,
                   help="stimuli_export.json from `export`. Supplies the shared "
                        "passage/caselet/DI table a set member depends on, shown "
                        "in the worksheet's stimulus_preview column. Optional: "
                        "without it that column is blank on every row.")
    s.add_argument("--options", default=None,
                   help="options_export.json from `export`. Enables the "
                        "option-level checks (count, exactly-one-correct, "
                        "duplicate text). Optional, and its ABSENCE means those "
                        "checks did not run — not that they passed.")
    s.add_argument("--out", default="worksheet.csv")
    s.add_argument("--hindi-year", action="append", default=None,
                   help="year(s) whose questions legitimately carry non-ASCII "
                        "(bilingual/Hindi) text; repeatable. Non-ASCII outside "
                        "these years flags as non_ascii_suspect. Confirm from the "
                        "export before trusting a year (e.g. 2023) — never hardcoded.")
    s.add_argument("--apply", action="store_true", help="write the worksheet CSV")

    a = sub.add_parser("apply", help="apply worksheet decisions, tag assignments "
                                     "and difficulty via the review + CMS APIs")
    a.add_argument("--worksheet", required=True)
    a.add_argument("--exam-id", default=DEFAULT_EXAM_ID)
    a.add_argument("--topic-catalog", required=True,
                   help="operator-supplied valid-topic-id list (never derived); "
                        "every assign_topic_id is checked against it before any "
                        "network call and an unknown id aborts the whole run")
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
    c = Client(base, token, timeout=args.timeout)
    handler: Callable[[Client, argparse.Namespace], int] = {
        "export": do_export, "apply": do_apply, "catalog": do_catalog}[args.cmd]
    return handler(c, args)


if __name__ == "__main__":
    raise SystemExit(main())
