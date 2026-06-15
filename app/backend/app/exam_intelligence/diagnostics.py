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


def _count_by(rows: list[dict], key: str) -> dict:
    """Return a raw {distinct value → count} map for ``key`` over ``rows``.

    NULLs are reported under the string ``"<null>"`` so the map is
    JSON-serialisable and the absence of a value is visible rather than dropped.
    """
    counter: Counter = Counter()
    for r in rows:
        val = r.get(key)
        counter["<null>" if val is None else val] += 1
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
        rows = sb.table(table).select(column).execute().data or []
        census[f"{table}.{column}"] = _count_by(rows, column)
    return census


def section_structure_completeness(sb, exam_id: str) -> dict:
    """Per-section authored-structure completeness for one exam.

    Joins exam → exam_phases (exam_id) → exam_phase_sections and flags each
    section that is missing question_count / marks / duration_mins.
    """
    phases = (
        sb.table("exam_phases")
        .select("id, exam_id, phase_name, phase_slug")
        .eq("exam_id", exam_id)
        .execute()
        .data
        or []
    )
    phase_ids = [p["id"] for p in phases]
    if not phase_ids:
        return {
            "exam_id": exam_id,
            "phase_count": 0,
            "section_count": 0,
            "sections": [],
            "sections_missing_structure": 0,
        }

    sections = (
        sb.table("exam_phase_sections")
        .select(
            "id, exam_phase_id, subject_id, section_label, "
            "question_count, marks, duration_mins, sort_order"
        )
        .in_("exam_phase_id", phase_ids)
        .execute()
        .data
        or []
    )

    out_sections = []
    missing_total = 0
    for s in sections:
        missing = [
            field
            for field in ("question_count", "marks", "duration_mins")
            if s.get(field) is None
        ]
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
                "duration_mins": s.get("duration_mins"),
                "missing": missing,
                "complete": not missing,
            }
        )
    out_sections.sort(key=lambda r: (r.get("section_label") or ""))
    return {
        "exam_id": exam_id,
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
    and it is not expired (valid_until NULL or in the future).

    Current-affairs items (is_current OR is_current_based) are segmented INTO a
    separate ``current_depth`` and kept OUT of ``base_depth`` so the durable
    pool is never inflated by time-bound questions.
    """
    statuses = list(selectable_statuses or [])
    now_iso = (now or datetime.now(timezone.utc)).isoformat()
    base: dict = {
        "exam_id": exam_id,
        "selectable_statuses": statuses,
        "base_depth": [],
        "current_depth": [],
        "base_total": 0,
        "current_total": 0,
    }
    if not statuses:
        return base

    rows = (
        sb.table("mock_question_bank")
        .select(
            "id, exam_id, subject_id, topic_id, difficulty, question_type, "
            "reviewer_status, is_current, is_current_based, valid_until"
        )
        .eq("exam_id", exam_id)
        .in_("reviewer_status", statuses)
        .in_("question_type", list(_SELECTABLE_QUESTION_TYPES))
        .execute()
        .data
        or []
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


def source_distribution(sb, exam_id: str, selectable_statuses) -> dict:
    """Report counts across all THREE provenance signals for one exam.

    They may disagree; this reports each independently and leaves the
    authority decision to the caller:
      - mock_question_bank.source_type
      - mock_question_bank.source_kind  (in-row, added migration 161)
      - mock_question_sources.source_kind (join table, migration 136)
    """
    statuses = list(selectable_statuses or [])
    out = {
        "exam_id": exam_id,
        "selectable_statuses": statuses,
        "by_bank_source_type": {},
        "by_bank_source_kind": {},
        "by_sources_table_source_kind": {},
    }
    if not statuses:
        return out

    bank_rows = (
        sb.table("mock_question_bank")
        .select("id, source_type, source_kind")
        .eq("exam_id", exam_id)
        .in_("reviewer_status", statuses)
        .execute()
        .data
        or []
    )
    out["by_bank_source_type"] = _count_by(bank_rows, "source_type")
    out["by_bank_source_kind"] = _count_by(bank_rows, "source_kind")

    question_ids = [r["id"] for r in bank_rows if r.get("id")]
    if question_ids:
        source_rows = (
            sb.table("mock_question_sources")
            .select("question_id, source_kind")
            .in_("question_id", question_ids)
            .execute()
            .data
            or []
        )
        out["by_sources_table_source_kind"] = _count_by(source_rows, "source_kind")
    return out


def verified_pyq_tag_depth(sb, exam_id: str, verified_status: str) -> dict:
    """Verified pyq topic-tag depth for one exam, grouped by topic + tag role.

    All three lifecycle gates (pyq_papers.trust_status,
    pyq_questions.reviewer_status, pyq_question_topic_tags.reviewer_status) are
    filtered to ``verified_status`` — the verified-equivalent value surfaced by
    ``status_value_census``, PASSED IN, never hardcoded.
    """
    out = {
        "exam_id": exam_id,
        "verified_status": verified_status,
        "depth": [],
        "total": 0,
    }
    if not verified_status:
        return out

    papers = (
        sb.table("pyq_papers")
        .select("id, exam_id, trust_status")
        .eq("exam_id", exam_id)
        .eq("trust_status", verified_status)
        .execute()
        .data
        or []
    )
    paper_ids = [p["id"] for p in papers]
    if not paper_ids:
        return out

    questions = (
        sb.table("pyq_questions")
        .select("id, pyq_paper_id, reviewer_status")
        .in_("pyq_paper_id", paper_ids)
        .eq("reviewer_status", verified_status)
        .execute()
        .data
        or []
    )
    question_ids = [q["id"] for q in questions]
    if not question_ids:
        return out

    tags = (
        sb.table("pyq_question_topic_tags")
        .select("question_id, topic_id, tag_role, reviewer_status")
        .in_("question_id", question_ids)
        .eq("reviewer_status", verified_status)
        .execute()
        .data
        or []
    )

    groups: dict = defaultdict(int)
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


def locked_coverage_count(sb, exam_id: str) -> dict:
    """exam_topic_coverage counts for one exam, by status and per section.

    Reports the raw breakdown (locked vs reviewed vs pending vs …) so the
    caller decides what "locked enough" means. ``by_section`` is a nested
    {section_id → {status → count}} map so ``readiness_verdict`` can resolve
    locked depth per section.
    """
    rows = (
        sb.table("exam_topic_coverage")
        .select("id, exam_id, section_id, reviewer_status")
        .eq("exam_id", exam_id)
        .execute()
        .data
        or []
    )
    by_status = _count_by(rows, "reviewer_status")
    by_section: dict = defaultdict(lambda: defaultdict(int))
    for r in rows:
        section_id = r.get("section_id")
        skey = "<null>" if section_id is None else section_id
        status = r.get("reviewer_status")
        by_section[skey]["<null>" if status is None else status] += 1
    return {
        "exam_id": exam_id,
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
    current-affairs items are excluded from the durable readiness check.
    """
    exam_id = structure.get("exam_id")
    sections = structure.get("sections") or []

    if not sections:
        return {
            "exam_id": exam_id,
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

    results = []
    summary = {"ready": 0, "thin_bank": 0, "blocked": 0}
    for s in sections:
        section_id = s.get("section_id")
        subject_id = s.get("subject_id")
        base_pool = pool_by_subject.get(subject_id, 0)
        locked = (coverage_by_section.get(section_id) or {}).get(
            _COVERAGE_LOCKED_STATUS, 0
        )

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
    selectable_statuses=None,
    verified_status: str | None = None,
    min_per_section: int | None = None,
    min_locked_coverage: int | None = None,
) -> dict:
    """Assemble the full content-readiness report for one exam.

    Census is always run (it needs no assumptions). Status-dependent depth and
    the verdict are only computed when the caller supplies the discovered
    vocabulary / thresholds — otherwise those blocks are reported as skipped so
    nothing is silently assumed.
    """
    report: dict = {
        "exam_id": exam_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status_value_census": status_value_census(sb),
        "section_structure": section_structure_completeness(sb, exam_id),
        "locked_coverage": locked_coverage_count(sb, exam_id),
        "skipped": [],
    }

    if selectable_statuses:
        report["selectable_mcq_depth"] = selectable_mcq_depth(
            sb, exam_id, selectable_statuses
        )
        report["source_distribution"] = source_distribution(
            sb, exam_id, selectable_statuses
        )
    else:
        report["skipped"].append("selectable_mcq_depth/source_distribution: "
                                 "pass --selectable-status after reading census")

    if verified_status:
        report["verified_pyq_tag_depth"] = verified_pyq_tag_depth(
            sb, exam_id, verified_status
        )
    else:
        report["skipped"].append("verified_pyq_tag_depth: "
                                 "pass --verified-status after reading census")

    if (
        selectable_statuses
        and min_per_section is not None
        and min_locked_coverage is not None
    ):
        report["readiness_verdict"] = readiness_verdict(
            report["section_structure"],
            report["selectable_mcq_depth"],
            report["locked_coverage"],
            min_per_section=min_per_section,
            min_locked_coverage=min_locked_coverage,
        )
    else:
        report["skipped"].append("readiness_verdict: "
                                 "pass --selectable-status, --min-per-section, "
                                 "--min-locked-coverage")

    return report
