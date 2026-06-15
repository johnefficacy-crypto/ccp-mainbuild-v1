"""Pure-read diagnostic helpers for operational hygiene.

find_orphan_questions  — pyq_questions with zero pyq_options children.
find_stuck_documents   — document_assets stuck in 'processing' > age_minutes.
find_stuck_text_extract_jobs — document_processing_jobs text_extract rows
                               stuck in 'running' > age_minutes.

Mock content-readiness diagnostics (for mock-generation gating). These are a
pure-read family that report the raw shape of the question corpus so an
operator can decide whether an exam is mock-ready. They never decide which
status value or source signal is authoritative — that vocabulary is
discovered by ``status_value_census`` and PASSED IN to the depth/verdict
helpers, never hardcoded here:

    status_value_census        — distinct reviewer/trust status value→count
                                 maps across the mock + pyq + coverage tables.
    section_structure_completeness — per exam_phase_section authored-structure
                                 completeness (question_count/marks/duration).
    selectable_mcq_depth       — selectable mock_question_bank depth grouped by
                                 subject/topic/difficulty, segmenting current
                                 items OUT of the base pool.
    source_distribution        — counts by the three (possibly disagreeing)
                                 provenance signals.
    verified_pyq_tag_depth     — verified pyq topic-tag depth by topic/role.
    locked_coverage_count      — exam_topic_coverage counts by status & section.
    readiness_verdict          — pure verdict over the above; thresholds are
                                 PARAMETERS, never baked in.

All functions accept a Supabase admin client and return plain dicts.
No writes are performed here; action endpoints live in the API layer.
"""
from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("career_copilot.exam_intelligence.diagnostics")

# Mock question types that count as selectable answerable items. Mirrors the
# mock_question_type enum (migration 135: 'mcq','integer','msq').
_SELECTABLE_QUESTION_TYPES = ("mcq", "msq", "integer")

# Coverage-lifecycle status that gates the Study OS planner. This is a fixed
# domain enum from migration 030 (exam_topic_coverage.reviewer_status), NOT a
# discovered/assumed value — see AGENTS.md Patterns and Lessons #11 ("only
# `locked` rows feed competition_context"). It indexes raw census output; it is
# not a threshold.
_COVERAGE_LOCKED_STATUS = "locked"

# JSON-safe bucket key for a NULL grouping value (e.g. a coverage row with no
# section_id — phase/topic-level coverage, which the CMS write path allows).
_NULL_BUCKET = "<null>"

# E2E Playwright fixtures (app/supabase/seeds/e2e_fixtures.sql) tag their
# mock_question_bank rows with this source_type. They are deliberately
# 'published' so the E2E fixed-id selector can load them, but they are NOT real
# catalogue content — so the production readiness depth must exclude them by
# construction, never counting a test fixture toward an exam's mock-readiness.
_E2E_FIXTURE_SOURCE_TYPE = "e2e_fixture"


def find_orphan_questions(
    sb, *, exam_id: str | None = None, limit: int = 200
) -> list[dict]:
    """Return pyq_questions rows that have no corresponding pyq_options rows.

    Performs three cheap point-reads rather than a raw SQL NOT EXISTS so the
    logic works with the PostgREST / SBStub query interface.
    """
    paper_q = sb.table("pyq_papers").select("id, exam_id, year, exam_cycle_id")
    if exam_id:
        paper_q = paper_q.eq("exam_id", exam_id)
    papers = paper_q.execute().data or []
    paper_map: dict[str, dict] = {p["id"]: p for p in papers}
    if not paper_map:
        return []

    q_query = (
        sb.table("pyq_questions")
        .select("id, pyq_paper_id, question_number, created_at")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if exam_id:
        q_query = q_query.in_("pyq_paper_id", list(paper_map.keys()))
    questions = q_query.execute().data or []
    if not questions:
        return []

    q_ids = [q["id"] for q in questions]
    opts = (
        sb.table("pyq_options")
        .select("question_id")
        .in_("question_id", q_ids)
        .execute()
        .data
        or []
    )
    has_options = {o["question_id"] for o in opts}

    result = []
    for q in questions:
        if q["id"] not in has_options:
            paper = paper_map.get(q.get("pyq_paper_id") or "", {})
            result.append(
                {
                    "id": q["id"],
                    "pyq_paper_id": q.get("pyq_paper_id"),
                    "question_number": q.get("question_number"),
                    "created_at": q.get("created_at"),
                    "exam_id": paper.get("exam_id"),
                    "year": paper.get("year"),
                    "exam_cycle_id": paper.get("exam_cycle_id"),
                }
            )
    return result


def find_stuck_documents(
    sb, *, age_minutes: int = 30, limit: int = 200
) -> list[dict]:
    """Return document_assets rows in 'processing' status older than age_minutes."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
    ).isoformat()
    return (
        sb.table("document_assets")
        .select("id, status, updated_at, created_at")
        .eq("status", "processing")
        .lt("updated_at", cutoff)
        .limit(limit)
        .execute()
        .data
        or []
    )


def find_stuck_text_extract_jobs(
    sb, *, age_minutes: int = 30, limit: int = 200
) -> list[dict]:
    """Return document_processing_jobs text_extract rows stuck in 'running'."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=age_minutes)
    ).isoformat()
    return (
        sb.table("document_processing_jobs")
        .select("id, job_type, status, started_at, document_id, error_code, error_message")
        .eq("job_type", "text_extract")
        .eq("status", "running")
        .lt("started_at", cutoff)
        .limit(limit)
        .execute()
        .data
        or []
    )


# ─────────────────────────────────────────────────────────────────────────────
# Mock content-readiness diagnostics
#
# These do grouping / OR-logic / segmentation in Python (like
# find_orphan_questions' NOT-EXISTS) rather than SQL aggregates, so they work
# against the PostgREST / SBStub query interface, which has no GROUP BY or OR.
# ─────────────────────────────────────────────────────────────────────────────


def _fetch_all(make_query, *, page_size: int = 1000) -> list[dict]:
    """Page through a PostgREST select so corpus totals are never silently
    capped at the server's default row limit.

    ``make_query`` is a zero-arg factory returning a fresh query (select +
    filters, no range) for each page, so each page is an independent request.
    Pages until a short page (< ``page_size``) is returned. The SBStub ignores
    ``.range()`` and returns all matching rows on the first call, which is
    < page_size for test fixtures, so the loop terminates after one iteration.
    """
    rows: list[dict] = []
    start = 0
    while True:
        page = (
            make_query()
            .range(start, start + page_size - 1)
            .execute()
            .data
            or []
        )
        rows.extend(page)
        if len(page) < page_size:
            break
        start += page_size
    return rows


def _chunked(items: list, size: int = 500) -> list[list]:
    """Split an id list into chunks so a large ``in_(...)`` filter does not
    exceed PostgREST's URL length limit. Empty input yields no chunks.
    """
    return [items[i : i + size] for i in range(0, len(items), size)]


def _count_by(rows: list[dict], key: str) -> dict:
    """Return a raw {distinct value → count} map for ``key`` over ``rows``.

    NULLs are reported under the string ``"<null>"`` so the map is
    JSON-serialisable and the absence of a value is visible rather than dropped.
    """
    counter: Counter = Counter()
    for r in rows:
        val = r.get(key)
        counter[_NULL_BUCKET if val is None else val] += 1
    return dict(counter)


def _not_expired(valid_until, now_iso: str) -> bool:
    """Mirror ``valid_until IS NULL OR valid_until > now()`` as a Python guard.

    ISO-8601 date/timestamp strings sort lexically, so a string compare matches
    Postgres ordering for both the ``date`` and ``timestamptz`` shapes that
    migrations 136/159 left on this column.
    """
    if valid_until in (None, ""):
        return True
    return str(valid_until) > now_iso


def status_value_census(sb) -> dict:
    """Discover the ACTUAL status vocabulary before anything downstream gates.

    Returns the raw distinct-value→count map for each status column the
    readiness audit depends on. Does NOT assume 'published'/'verified'/'live' —
    it reports whatever exists so the caller can pass the right values into
    ``selectable_mcq_depth`` / ``verified_pyq_tag_depth``.
    """
    columns = [
        ("mock_question_bank", "reviewer_status"),
        ("pyq_questions", "reviewer_status"),
        ("pyq_question_topic_tags", "reviewer_status"),
        ("pyq_papers", "trust_status"),
        ("exam_topic_coverage", "reviewer_status"),
    ]
    census: dict = {}
    for table, column in columns:
        rows = _fetch_all(lambda t=table, c=column: sb.table(t).select(c))
        census[f"{table}.{column}"] = _count_by(rows, column)
    return census


def list_exam_phases(sb, exam_id: str, *, exam_phase_id: str | None = None) -> list[dict]:
    """Return the exam's phases (or just the one named by ``exam_phase_id``).

    Ordered by phase_order so the report surfaces phases in exam sequence.
    """
    phases = _fetch_all(
        lambda: sb.table("exam_phases")
        .select("id, exam_id, phase_name, phase_slug, phase_order")
        .eq("exam_id", exam_id)
    )
    if exam_phase_id:
        phases = [p for p in phases if p.get("id") == exam_phase_id]
    phases.sort(key=lambda p: (p.get("phase_order") if p.get("phase_order") is not None else 0))
    return phases


def section_structure_completeness(
    sb, exam_id: str, *, exam_phase_id: str | None = None
) -> dict:
    """Per-section authored-structure completeness, scoped to one phase if given.

    Joins exam → exam_phases (exam_id) → exam_phase_sections and flags each
    section that is missing question_count / marks / duration_mins. When
    ``exam_phase_id`` is supplied, only that phase's sections are returned
    (mock structure is phase-level, so the caller scopes per phase).

    Duration uses a phase fallback: a common-timer phase sets
    ``exam_phases.duration_mins`` and leaves the per-section ``duration_mins``
    NULL by design, so a section's duration counts as present when EITHER the
    section or its parent phase carries one (``duration_source`` records which).
    """
    phases = _fetch_all(
        lambda: sb.table("exam_phases")
        .select("id, exam_id, phase_name, phase_slug, duration_mins")
        .eq("exam_id", exam_id)
    )
    if exam_phase_id:
        phases = [p for p in phases if p.get("id") == exam_phase_id]
    phase_ids = [p["id"] for p in phases]
    phase_duration = {p["id"]: p.get("duration_mins") for p in phases}
    if not phase_ids:
        return {
            "exam_id": exam_id,
            "exam_phase_id": exam_phase_id,
            "phase_count": 0,
            "section_count": 0,
            "sections": [],
            "sections_missing_structure": 0,
        }

    sections = _fetch_all(
        lambda: sb.table("exam_phase_sections")
        .select(
            "id, exam_phase_id, subject_id, section_label, "
            "question_count, marks, duration_mins, sort_order"
        )
        .in_("exam_phase_id", phase_ids)
    )

    out_sections = []
    missing_total = 0
    for s in sections:
        missing = [
            field
            for field in ("question_count", "marks")
            if s.get(field) is None
        ]
        section_dur = s.get("duration_mins")
        phase_dur = phase_duration.get(s.get("exam_phase_id"))
        if section_dur is not None:
            duration_source = "section"
        elif phase_dur is not None:
            duration_source = "phase"  # common-timer phase covers the section
        else:
            duration_source = None
            missing.append("duration_mins")
        if missing:
            missing_total += 1
        out_sections.append(
            {
                "section_id": s.get("id"),
                "exam_phase_id": s.get("exam_phase_id"),
                "subject_id": s.get("subject_id"),
                "section_label": s.get("section_label"),
                "question_count": s.get("question_count"),
                "marks": s.get("marks"),
                "duration_mins": section_dur,
                "duration_source": duration_source,
                "missing": missing,
                "complete": not missing,
            }
        )
    out_sections.sort(key=lambda r: (r.get("section_label") or ""))
    return {
        "exam_id": exam_id,
        "exam_phase_id": exam_phase_id,
        "phase_count": len(phase_ids),
        "section_count": len(out_sections),
        "sections": out_sections,
        "sections_missing_structure": missing_total,
    }


def selectable_mcq_depth(
    sb, exam_id: str, selectable_statuses, *, now: datetime | None = None
) -> dict:
    """Selectable mock-question depth for one exam, base pool vs current pool.

    ``selectable_statuses`` is supplied by the caller (after reading
    ``status_value_census``) — never hardcoded. A row counts when its
    reviewer_status is in that set, its question_type is an answerable type,
    it is not expired (valid_until NULL or in the future), and it is not an E2E
    test fixture (``source_type = 'e2e_fixture'`` is excluded by construction).

    Current-affairs items (is_current OR is_current_based) are segmented INTO a
    separate ``current_depth`` and kept OUT of ``base_depth`` so the durable
    pool is never inflated by time-bound questions.

    SCOPE: this read is EXAM-level. ``mock_question_bank`` has no phase column
    (only exam_id / subject_id / topic_id), so depth cannot be filtered by
    exam_phase_id directly. Phase/section attribution is INDIRECT: a section's
    pool is the depth of the subject_ids that belong to that phase's
    exam_phase_sections. ``readiness_verdict`` performs that section→subject→
    bank attribution; ``pool_scope`` records that the pool is subject-level.
    """
    statuses = list(selectable_statuses or [])
    now_iso = (now or datetime.now(timezone.utc)).isoformat()
    base: dict = {
        "exam_id": exam_id,
        "selectable_statuses": statuses,
        "scope": "exam",
        "pool_scope": "subject",
        "attribution": "per-section via subject_id; mock_question_bank has no "
        "phase column",
        "base_depth": [],
        "current_depth": [],
        "base_total": 0,
        "current_total": 0,
    }
    if not statuses:
        return base

    rows = _fetch_all(
        lambda: sb.table("mock_question_bank")
        .select(
            "id, exam_id, subject_id, topic_id, difficulty, question_type, "
            "reviewer_status, is_current, is_current_based, valid_until"
        )
        .eq("exam_id", exam_id)
        .in_("reviewer_status", statuses)
        .in_("question_type", list(_SELECTABLE_QUESTION_TYPES))
        .neq("source_type", _E2E_FIXTURE_SOURCE_TYPE)
    )

    base_groups: dict = defaultdict(int)
    current_groups: dict = defaultdict(int)
    base_total = 0
    current_total = 0
    for r in rows:
        if not _not_expired(r.get("valid_until"), now_iso):
            continue
        gkey = (r.get("subject_id"), r.get("topic_id"), r.get("difficulty"))
        is_current = bool(r.get("is_current")) or bool(r.get("is_current_based"))
        if is_current:
            current_groups[gkey] += 1
            current_total += 1
        else:
            base_groups[gkey] += 1
            base_total += 1

    def _emit(groups: dict) -> list[dict]:
        return [
            {
                "subject_id": subject_id,
                "topic_id": topic_id,
                "difficulty": difficulty,
                "count": count,
            }
            for (subject_id, topic_id, difficulty), count in sorted(
                groups.items(), key=lambda kv: (str(kv[0]),)
            )
        ]

    base["base_depth"] = _emit(base_groups)
    base["current_depth"] = _emit(current_groups)
    base["base_total"] = base_total
    base["current_total"] = current_total
    return base


def _segment_source_distribution(sb, rows: list[dict]) -> dict:
    """Compute the three provenance signal maps over one segment of bank rows."""
    seg = {
        "by_bank_source_type": _count_by(rows, "source_type"),
        "by_bank_source_kind": _count_by(rows, "source_kind"),
        "by_sources_table_source_kind": {},
    }
    question_ids = [r["id"] for r in rows if r.get("id")]
    source_counts: Counter = Counter()
    for chunk in _chunked(question_ids):
        source_rows = _fetch_all(
            lambda c=chunk: sb.table("mock_question_sources")
            .select("question_id, source_kind")
            .in_("question_id", c)
        )
        source_counts.update(_count_by(source_rows, "source_kind"))
    seg["by_sources_table_source_kind"] = dict(source_counts)
    return seg


def source_distribution(
    sb, exam_id: str, selectable_statuses, *, now: datetime | None = None
) -> dict:
    """Provenance-signal counts over the SAME eligible pool as
    ``selectable_mcq_depth``, segmented into base and current.

    The eligible-pool filter is identical to ``selectable_mcq_depth``:
    reviewer_status IN ``selectable_statuses`` (passed in, never hardcoded),
    answerable question_type, and not expired (valid_until NULL or future).
    Current-affairs items (is_current OR is_current_based) are reported in
    ``current_source_distribution`` and kept OUT of
    ``base_source_distribution``.

    Each segment reports all THREE signals independently (they may disagree;
    authority is the caller's call):
      - mock_question_bank.source_type
      - mock_question_bank.source_kind  (in-row, added migration 161)
      - mock_question_sources.source_kind (join table, migration 136)
    """
    statuses = list(selectable_statuses or [])
    empty = {
        "by_bank_source_type": {},
        "by_bank_source_kind": {},
        "by_sources_table_source_kind": {},
    }
    out = {
        "exam_id": exam_id,
        "selectable_statuses": statuses,
        "base_source_distribution": dict(empty),
        "current_source_distribution": dict(empty),
    }
    if not statuses:
        return out

    now_iso = (now or datetime.now(timezone.utc)).isoformat()
    rows = _fetch_all(
        lambda: sb.table("mock_question_bank")
        .select(
            "id, source_type, source_kind, question_type, "
            "is_current, is_current_based, valid_until"
        )
        .eq("exam_id", exam_id)
        .in_("reviewer_status", statuses)
        .in_("question_type", list(_SELECTABLE_QUESTION_TYPES))
        .neq("source_type", _E2E_FIXTURE_SOURCE_TYPE)
    )

    base_rows: list[dict] = []
    current_rows: list[dict] = []
    for r in rows:
        if not _not_expired(r.get("valid_until"), now_iso):
            continue
        if bool(r.get("is_current")) or bool(r.get("is_current_based")):
            current_rows.append(r)
        else:
            base_rows.append(r)

    out["base_source_distribution"] = _segment_source_distribution(sb, base_rows)
    out["current_source_distribution"] = _segment_source_distribution(sb, current_rows)
    return out


def verified_pyq_tag_depth(
    sb, exam_id: str, verified_status: str, *, exam_phase_id: str | None = None
) -> dict:
    """Verified pyq topic-tag depth, grouped by topic + tag role.

    All three lifecycle gates (pyq_papers.trust_status,
    pyq_questions.reviewer_status, pyq_question_topic_tags.reviewer_status) are
    filtered to ``verified_status`` — the verified-equivalent value surfaced by
    ``status_value_census``, PASSED IN, never hardcoded. When ``exam_phase_id``
    is supplied, papers are scoped via pyq_papers.exam_phase_id (pyq is
    phase-level).
    """
    out = {
        "exam_id": exam_id,
        "exam_phase_id": exam_phase_id,
        "verified_status": verified_status,
        "depth": [],
        "total": 0,
    }
    if not verified_status:
        return out

    def _papers_query():
        q = (
            sb.table("pyq_papers")
            .select("id, exam_id, exam_phase_id, trust_status")
            .eq("exam_id", exam_id)
            .eq("trust_status", verified_status)
        )
        if exam_phase_id:
            q = q.eq("exam_phase_id", exam_phase_id)
        return q

    papers = _fetch_all(_papers_query)
    paper_ids = [p["id"] for p in papers]
    if not paper_ids:
        return out

    questions: list[dict] = []
    for chunk in _chunked(paper_ids):
        questions += _fetch_all(
            lambda c=chunk: sb.table("pyq_questions")
            .select("id, pyq_paper_id, reviewer_status")
            .in_("pyq_paper_id", c)
            .eq("reviewer_status", verified_status)
        )
    question_ids = [q["id"] for q in questions]
    if not question_ids:
        return out

    groups: dict = defaultdict(int)
    for chunk in _chunked(question_ids):
        tags = _fetch_all(
            lambda c=chunk: sb.table("pyq_question_topic_tags")
            .select("question_id, topic_id, tag_role, reviewer_status")
            .in_("question_id", c)
            .eq("reviewer_status", verified_status)
        )
        for t in tags:
            groups[(t.get("topic_id"), t.get("tag_role"))] += 1

    out["depth"] = [
        {"topic_id": topic_id, "tag_role": tag_role, "count": count}
        for (topic_id, tag_role), count in sorted(
            groups.items(), key=lambda kv: (str(kv[0][0]), str(kv[0][1]))
        )
    ]
    out["total"] = sum(groups.values())
    return out


def locked_coverage_count(
    sb, exam_id: str, *, exam_phase_id: str | None = None
) -> dict:
    """exam_topic_coverage counts, by status and per section.

    Reports the raw breakdown (locked vs reviewed vs pending vs …) so the
    caller decides what "locked enough" means. ``by_section`` is a nested
    {section_id → {status → count}} map so ``readiness_verdict`` can resolve
    locked depth per section. When ``exam_phase_id`` is supplied, coverage is
    scoped via exam_topic_coverage.exam_phase_id (coverage is phase-level).
    """
    def _coverage_query():
        q = (
            sb.table("exam_topic_coverage")
            .select("id, exam_id, exam_phase_id, section_id, reviewer_status")
            .eq("exam_id", exam_id)
        )
        if exam_phase_id:
            q = q.eq("exam_phase_id", exam_phase_id)
        return q

    rows = _fetch_all(_coverage_query)
    by_status = _count_by(rows, "reviewer_status")
    by_section: dict = defaultdict(lambda: defaultdict(int))
    for r in rows:
        section_id = r.get("section_id")
        skey = _NULL_BUCKET if section_id is None else section_id
        status = r.get("reviewer_status")
        by_section[skey][_NULL_BUCKET if status is None else status] += 1
    return {
        "exam_id": exam_id,
        "exam_phase_id": exam_phase_id,
        "by_status": by_status,
        "by_section": {sid: dict(counts) for sid, counts in by_section.items()},
        "total": len(rows),
    }


def readiness_verdict(
    structure: dict,
    mcq_depth: dict,
    coverage: dict,
    *,
    min_per_section: int,
    min_locked_coverage: int,
) -> dict:
    """Pure verdict over the structure/depth/coverage signals.

    Thresholds are PARAMETERS — there is deliberately no default in the body.
    Emits one verdict per (exam, section):
      - blocked: no_sections | missing_structure | no_locked_coverage
      - thin_bank: thin_mcq_pool (structure + coverage OK, pool too shallow)
      - ready: none of the above

    Pool depth is attributed to a section by its subject_id (the only link
    between exam_phase_sections and mock_question_bank), using the BASE pool —
    current-affairs items are excluded from the durable readiness check. The
    emitted ``pool_scope: "subject"`` records that the base pool is subject-
    level, NOT section-selector level (the bank has no phase/section column).

    Locked coverage is counted as section-attributed rows PLUS phase-level
    (section_id NULL) rows: phase/topic-level coverage applies to every section
    in the phase, so a section is not blocked for ``no_locked_coverage`` when
    the phase carries locked coverage without a concrete section_id. ``coverage``
    is expected to be phase-scoped (as the assembler provides), so its NULL
    bucket is this phase's phase-level coverage.
    """
    exam_id = structure.get("exam_id")
    exam_phase_id = structure.get("exam_phase_id")
    sections = structure.get("sections") or []

    if not sections:
        return {
            "exam_id": exam_id,
            "exam_phase_id": exam_phase_id,
            "pool_scope": "subject",
            "thresholds": {
                "min_per_section": min_per_section,
                "min_locked_coverage": min_locked_coverage,
            },
            "sections": [
                {
                    "section_id": None,
                    "subject_id": None,
                    "section_label": None,
                    "verdict": "blocked",
                    "reasons": ["no_sections"],
                    "base_pool": 0,
                    "locked_coverage": 0,
                }
            ],
            "summary": {"ready": 0, "thin_bank": 0, "blocked": 1},
        }

    # Base pool per subject (durable pool only; current items excluded upstream).
    pool_by_subject: dict = defaultdict(int)
    for grp in mcq_depth.get("base_depth") or []:
        pool_by_subject[grp.get("subject_id")] += grp.get("count", 0)

    coverage_by_section = coverage.get("by_section") or {}
    # Phase-level (section_id NULL) locked coverage applies to every section.
    phase_level_locked = (coverage_by_section.get(_NULL_BUCKET) or {}).get(
        _COVERAGE_LOCKED_STATUS, 0
    )

    results = []
    summary = {"ready": 0, "thin_bank": 0, "blocked": 0}
    for s in sections:
        section_id = s.get("section_id")
        subject_id = s.get("subject_id")
        base_pool = pool_by_subject.get(subject_id, 0)
        locked = (coverage_by_section.get(section_id) or {}).get(
            _COVERAGE_LOCKED_STATUS, 0
        ) + phase_level_locked

        reasons = []
        if s.get("missing"):
            reasons.append("missing_structure")
        if locked < min_locked_coverage:
            reasons.append("no_locked_coverage")
        if base_pool < min_per_section:
            reasons.append("thin_mcq_pool")

        blocking = {"missing_structure", "no_locked_coverage"}
        if blocking & set(reasons):
            verdict = "blocked"
        elif "thin_mcq_pool" in reasons:
            verdict = "thin_bank"
        else:
            verdict = "ready"
        summary[verdict] += 1

        results.append(
            {
                "section_id": section_id,
                "subject_id": subject_id,
                "section_label": s.get("section_label"),
                "verdict": verdict,
                "reasons": reasons,
                "base_pool": base_pool,
                "locked_coverage": locked,
            }
        )

    return {
        "exam_id": exam_id,
        "exam_phase_id": exam_phase_id,
        "pool_scope": "subject",
        "thresholds": {
            "min_per_section": min_per_section,
            "min_locked_coverage": min_locked_coverage,
        },
        "sections": results,
        "summary": summary,
    }


def assemble_mock_readiness_report(
    sb,
    *,
    exam_id: str,
    exam_phase_id: str | None = None,
    selectable_statuses=None,
    verified_status: str | None = None,
    min_per_section: int | None = None,
    min_locked_coverage: int | None = None,
) -> dict:
    """Assemble the content-readiness report, GROUPED BY PHASE.

    Mocks are phase-level, so structure / coverage / verified-pyq depth / the
    verdict are computed PER phase and never merged across phases. When
    ``exam_phase_id`` is given only that phase is reported; otherwise every
    phase of the exam gets its own block.

    Census and the bank-level views (selectable_mcq_depth, source_distribution)
    are EXAM-level — the bank has no phase column — and live at the top level;
    per-phase verdicts attribute that depth to sections by subject_id.

    Status-dependent blocks are only computed when the caller supplies the
    discovered vocabulary / thresholds; otherwise they are reported as skipped
    so nothing is silently assumed.
    """
    report: dict = {
        "exam_id": exam_id,
        "exam_phase_id": exam_phase_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status_value_census": status_value_census(sb),
        "phases": [],
        "skipped": [],
    }

    mcq_depth = None
    if selectable_statuses:
        mcq_depth = selectable_mcq_depth(sb, exam_id, selectable_statuses)
        report["selectable_mcq_depth"] = mcq_depth
        report["source_distribution"] = source_distribution(
            sb, exam_id, selectable_statuses
        )
    else:
        report["skipped"].append(
            "selectable_mcq_depth/source_distribution: pass --selectable-status "
            "after reading census"
        )
    if not verified_status:
        report["skipped"].append(
            "verified_pyq_tag_depth: pass --verified-status after reading census"
        )
    can_verdict = (
        mcq_depth is not None
        and min_per_section is not None
        and min_locked_coverage is not None
    )
    if not can_verdict:
        report["skipped"].append(
            "readiness_verdict: pass --selectable-status, --min-per-section, "
            "--min-locked-coverage"
        )

    phases = list_exam_phases(sb, exam_id, exam_phase_id=exam_phase_id)
    if not phases:
        report["skipped"].append(
            "phases: exam has no exam_phases rows (nothing to scope per phase)"
        )

    for ph in phases:
        pid = ph["id"]
        block: dict = {
            "exam_phase_id": pid,
            "phase_slug": ph.get("phase_slug"),
            "phase_name": ph.get("phase_name"),
            "section_structure": section_structure_completeness(
                sb, exam_id, exam_phase_id=pid
            ),
            "locked_coverage": locked_coverage_count(sb, exam_id, exam_phase_id=pid),
        }
        if verified_status:
            block["verified_pyq_tag_depth"] = verified_pyq_tag_depth(
                sb, exam_id, verified_status, exam_phase_id=pid
            )
        if can_verdict:
            block["readiness_verdict"] = readiness_verdict(
                block["section_structure"],
                mcq_depth,
                block["locked_coverage"],
                min_per_section=min_per_section,
                min_locked_coverage=min_locked_coverage,
            )
        report["phases"].append(block)

    return report
