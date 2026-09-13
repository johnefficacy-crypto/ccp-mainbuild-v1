"""Locked-only coverage / PYQ aggregates.

Reads ``exam_topic_coverage`` joined with ``topics`` + ``subjects``.
Only ``reviewer_status='locked'`` rows are planner-ready and may surface
to aspirants. PYQ aggregates filter strictly to
``pyq_question_topic_tags.reviewer_status='verified'``.

No claims, no AI inference, no scraping. If a table is missing every
helper returns an empty list.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger("career_copilot.exam_intelligence.coverage")

# Postgres SQLSTATEs we want to surface loudly (schema drift / missing
# table) rather than swallow as a warning.
_LOUD_PG_CODES = {"42703", "42P01"}

_BATCH = 250   # max items per IN() filter
_PAGE = 1000   # rows per pagination page


def _chunks(lst: list[Any], n: int) -> list[list[Any]]:
    return [lst[i : i + n] for i in range(0, len(lst), n)]


def _safe(call: Callable[[], Any], default: Any = None, *, table: str | None = None, operation: str | None = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "code", None) or getattr(exc, "pgcode", None)
        message = str(exc)
        level = logging.ERROR if code in _LOUD_PG_CODES else logging.WARNING
        logger.log(
            level,
            "exam_intelligence coverage read failed",
            extra={
                "operation": operation or "read",
                "table": table,
                "error_code": code,
                "error_message": message,
            },
        )
        return default


def _paginate(
    build_query: Any,
    *,
    table: str | None = None,
    operation: str | None = None,
) -> list[dict[str, Any]] | None:
    """Fetch every row of a read using ordered, verified range pagination.

    ``build_query(from_n, to_n)`` must return the PostgREST *response* for the
    inclusive ``[from_n, to_n]`` window, and the query it builds MUST carry:

    * a total ``.order(...)`` ending on a unique column (``id``), and
    * ``count="exact"`` on ``.select(...)``.

    Range paging without a total order is undefined in Postgres: each window
    is a separate query, so the server may return rows in a different
    physical order per page. Rows then repeat across pages while others never
    appear — the read completes, reports no error, and is short. In this
    module that lands on ``verified_pyq_topic_counts``, whose output is a
    topic's PYQ frequency: an undercount there is not a missing row a caller
    can notice, it is a plausible-looking wrong number.

    ``count="exact"`` is the completeness proof, because a page short of
    ``_PAGE`` is indistinguishable from the end of the set by length alone.

    Returns ``None`` — not a partial list — when a page read raises, when the
    driver reports no exact count, or when the rows collected do not match
    that count. This replaces the previous "return whatever was retrieved"
    behaviour: a partial frequency map is more dangerous than an empty one,
    because every caller can recognise empty and none can recognise partial.
    """
    all_rows: list[dict[str, Any]] = []
    offset = 0
    exact_total: int | None = None
    while True:
        resp = _safe(
            lambda o=offset: build_query(o, o + _PAGE - 1),
            default=None,
            table=table,
            operation=operation,
        )
        if resp is None:
            return None
        rows = list(getattr(resp, "data", None) or [])
        count = getattr(resp, "count", None)
        if count is not None:
            exact_total = int(count)
        all_rows.extend(rows)
        if len(rows) < _PAGE:
            break
        offset += _PAGE

    if exact_total is None or len(all_rows) != exact_total:
        logger.error(
            "exam_intelligence coverage paginated read is incomplete",
            extra={
                "operation": operation or "read",
                "table": table,
                "rows_collected": len(all_rows),
                "rows_expected": exact_total,
            },
        )
        return None
    return all_rows


def _paginate_in(
    supabase: Any,
    table: str,
    columns: str,
    key: str,
    values: list[str],
    *,
    operation: str,
    extra: Any = None,
) -> list[dict[str, Any]] | None:
    """Read every row where ``key`` is in ``values``, chunked and paginated.

    The follow-up joins in this module used a single ``.in_(ids).limit(2000)``.
    Two ways that silently truncated: PostgREST caps the read at
    ``db-max-rows`` (1 000) regardless of the 2 000 asked for, and a single
    ``IN()`` of a few thousand ids is a very long URL. Chunking by ``_BATCH``
    and range-paginating each chunk removes both.
    """
    rows: list[dict[str, Any]] = []
    for chunk in _chunks(values, _BATCH):
        def _page(from_n: int, to_n: int, c: list[str] = chunk) -> Any:
            q = supabase.table(table).select(columns, count="exact").in_(key, c)
            if extra is not None:
                q = extra(q)
            return q.order("id").range(from_n, to_n).execute()

        batch = _paginate(_page, table=table, operation=operation)
        if batch is None:
            return None
        rows.extend(batch)
    return rows


def locked_topic_coverage_summary(supabase: Any, exam_id: str) -> list[dict[str, Any]] | None:
    """Return locked topic-coverage rows for ``exam_id`` joined with topic + subject metadata.

    Only ``reviewer_status='locked'`` rows surface — the same verified-only
    contract the rest of exam intelligence uses. Joined via two follow-up
    reads against ``topics`` and ``subjects`` so behaviour is identical
    against the live client and against unit-test stubs.

    Result row shape::

        {
            "topic_id": "...",
            "topic_slug": "...",
            "topic_name": "...",
            "topic_level": "topic|microtopic|concept",
            "subject_id": "...",
            "subject_name": "...",
            "exam_priority_score": float|None,   # 0..100 numeric
            "is_high_yield": bool,
            "confidence_score": float|None,
            "reviewer_status": "locked",
            "exam_phase_id": str|None,
        }

    Returns ``None`` when a read could not be completed (failed page, or a
    read the server's exact count says came back short). ``None`` is not
    ``[]``: an incomplete read must not read as "this exam has nothing".
    Callers that want to degrade spell it ``or []`` at the call site.
    """
    if not exam_id:
        return []

    # Was a bare `.limit(1000)` — exactly PostgREST's `db-max-rows`, so this
    # read was truncated the moment an exam held 1 000 locked coverage rows
    # (UPSC CSE Mains holds 1 497). Range-paginated and count-verified now.
    def _coverage_page(from_n: int, to_n: int) -> Any:
        return (
            supabase.table("exam_topic_coverage")
            .select(
                "id, topic_id, exam_phase_id, exam_priority_score, "
                # RANK-SCALE-01: the unit system this row's score is in.
                "source_basis, "
                "is_high_yield, confidence_score, reviewer_status",
                count="exact",
            )
            .eq("exam_id", exam_id)
            .eq("reviewer_status", "locked")
            .order("id")
            .range(from_n, to_n)
            .execute()
        )

    flat = _paginate(
        _coverage_page,
        table="exam_topic_coverage",
        operation="select_locked_summary",
    )
    if flat is None:
        return None
    topic_ids = list({r.get("topic_id") for r in flat if r.get("topic_id")})
    if not topic_ids:
        return []

    topic_rows = _paginate_in(
        supabase,
        "topics",
        "id, slug, name, level, is_active, subject_id",
        "id",
        topic_ids,
        operation="select_by_ids",
    )
    if topic_rows is None:
        return None
    topics_by_id = {t["id"]: t for t in topic_rows if t.get("id")}

    subject_ids = list({t.get("subject_id") for t in topics_by_id.values() if t.get("subject_id")})
    subjects_by_id: dict[str, dict[str, Any]] = {}
    if subject_ids:
        subj_rows = _safe(
            lambda: (
                supabase.table("subjects")
                .select("id, slug, name, subject_group, is_active")
                .in_("id", subject_ids)
                .limit(500)
                .execute()
                .data
            ),
            default=[],
            table="subjects",
            operation="select_by_ids",
        ) or []
        subjects_by_id = {s["id"]: s for s in subj_rows if s.get("id")}

    out: list[dict[str, Any]] = []
    for r in flat:
        topic = topics_by_id.get(r.get("topic_id")) or {}
        if not topic or topic.get("is_active") is False:
            continue
        subject = subjects_by_id.get(topic.get("subject_id")) or {}
        if subject and subject.get("is_active") is False:
            continue
        out.append(
            {
                "topic_id": topic.get("id") or r.get("topic_id"),
                "topic_slug": topic.get("slug"),
                "topic_name": topic.get("name"),
                "topic_level": topic.get("level"),
                "subject_id": subject.get("id") or topic.get("subject_id"),
                "subject_name": subject.get("name"),
                "exam_priority_score": r.get("exam_priority_score"),
                "source_basis": r.get("source_basis"),
                "is_high_yield": bool(r.get("is_high_yield")),
                "confidence_score": r.get("confidence_score"),
                "reviewer_status": r.get("reviewer_status"),
                "exam_phase_id": r.get("exam_phase_id"),
            }
        )
    return out


def verified_pyq_topic_counts(supabase: Any, exam_id: str) -> dict[str, int] | None:
    """Return ``{topic_id: verified_primary_pyq_count}`` for ``exam_id``.

    Counts only ``tag_role='primary'`` tags from verified papers/questions.
    Secondary, trap, calculation_layer, and conceptual_layer associations are
    intentionally excluded — one question must not inflate a topic's frequency
    through multiple roles. This is the primary-only frequency contract.

    Questions with multiple primary tags (ambiguous) are excluded entirely —
    one question must contribute to at most one topic's count.

    Joins: ``pyq_papers`` (trust_status='verified') →
           ``pyq_questions`` (reviewer_status='verified') →
           ``pyq_question_topic_tags`` (reviewer_status='verified', tag_role='primary').

    All reads are ordered, range-paginated and verified against the server's
    exact count, so neither the 1 000-row cap nor an undefined page order can
    silently drop questions from a topic's count.

    Returns ``None`` when a read could not be completed (failed page, or a
    read the server's exact count says came back short). ``None`` is not
    ``{}``: an incomplete read must not read as "this exam has no PYQ evidence".
    Callers that want to degrade spell it ``or {}`` at the call site.
    """
    if not exam_id:
        return {}

    # ── 1. Verified papers (paginated) ────────────────────────────────────
    paper_rows = _paginate(
        lambda from_n, to_n: (
            supabase.table("pyq_papers")
            .select("id", count="exact")
            .eq("exam_id", exam_id)
            .eq("trust_status", "verified")
            .order("id")
            .range(from_n, to_n)
            .execute()
        ),
        table="pyq_papers",
        operation="select_verified_by_exam",
    )
    if paper_rows is None:
        return None
    paper_ids = [r["id"] for r in paper_rows if r.get("id")]
    if not paper_ids:
        return {}

    # ── 2. Verified questions (batched + paginated) ───────────────────────
    question_ids: list[str] = []
    for chunk in _chunks(paper_ids, _BATCH):
        batch_rows = _paginate(
            lambda from_n, to_n, c=chunk: (
                supabase.table("pyq_questions")
                .select("id", count="exact")
                .in_("pyq_paper_id", c)
                .eq("reviewer_status", "verified")
                .order("id")
                .range(from_n, to_n)
                .execute()
            ),
            table="pyq_questions",
            operation="select_verified",
        )
        if batch_rows is None:
            return None
        question_ids.extend(r["id"] for r in batch_rows if r.get("id"))

    if not question_ids:
        return {}

    # ── 3. Primary tags (batched + paginated) ─────────────────────────────
    # Build question→topics map so ambiguous questions (multiple primary tags
    # across different topics) can be identified and excluded.
    q_to_topics: dict[str, set[str]] = {}
    for chunk in _chunks(question_ids, _BATCH):
        batch_rows = _paginate(
            lambda from_n, to_n, c=chunk: (
                supabase.table("pyq_question_topic_tags")
                .select("id, question_id, topic_id, reviewer_status, tag_role", count="exact")
                .in_("question_id", c)
                .eq("reviewer_status", "verified")
                .eq("tag_role", "primary")
                .order("id")
                .range(from_n, to_n)
                .execute()
            ),
            table="pyq_question_topic_tags",
            operation="select_verified_primary",
        )
        if batch_rows is None:
            return None
        for tag in batch_rows:
            if tag.get("tag_role") != "primary":  # defense-in-depth
                continue
            qid = tag.get("question_id")
            tid = tag.get("topic_id")
            if qid and tid:
                q_to_topics.setdefault(qid, set()).add(tid)

    ambiguous = [q for q, topics in q_to_topics.items() if len(topics) > 1]
    if ambiguous:
        logger.warning(
            "coverage: %d questions have multiple primary tags — excluded from frequency counts",
            len(ambiguous),
            extra={"exam_id": exam_id, "ambiguous_sample": ambiguous[:5]},
        )

    counts: dict[str, int] = {}
    for qid, topics in q_to_topics.items():
        if len(topics) == 1:
            tid = next(iter(topics))
            counts[tid] = counts.get(tid, 0) + 1
    return counts


def locked_topic_coverage(supabase: Any, exam_id: str) -> list[dict[str, Any]] | None:
    """Return ``exam_topic_coverage`` rows whose ``reviewer_status='locked'``.

    Verified-only contract: ONLY ``locked`` rows are planner-ready and may
    surface to aspirants. ``draft`` / ``pending_review`` / ``reviewed`` /
    ``rejected`` rows are excluded here on purpose.

    Result row shape::

        {
            "topic": "Percentage",
            "topic_id": "...",
            "priority_score": float|None,
            "confidence_score": float|None,
            "high_yield": bool,
            "status": "locked",
        }

    Sorted by ``priority_score`` descending so callers can take the top N.

    Returns ``None`` when a read could not be completed (failed page, or a
    read the server's exact count says came back short). ``None`` is not
    ``[]``: an incomplete read must not read as "this exam has nothing".
    Callers that want to degrade spell it ``or []`` at the call site.
    """
    if not exam_id:
        return []

    # Was a bare `.limit(2000)`, which PostgREST silently served as 1 000.
    def _coverage_page(from_n: int, to_n: int) -> Any:
        return (
            supabase.table("exam_topic_coverage")
            .select(
                "id, topic_id, exam_priority_score, is_high_yield, "
                "confidence_score, reviewer_status",
                count="exact",
            )
            .eq("exam_id", exam_id)
            .eq("reviewer_status", "locked")
            .order("id")
            .range(from_n, to_n)
            .execute()
        )

    flat = _paginate(
        _coverage_page,
        table="exam_topic_coverage",
        operation="select_locked",
    )
    if flat is None:
        return None
    if not flat:
        return []

    topic_ids = list({r.get("topic_id") for r in flat if r.get("topic_id")})
    topic_rows = _paginate_in(
        supabase,
        "topics",
        "id, name, slug, is_active",
        "id",
        topic_ids,
        operation="select_by_ids",
    )
    if topic_rows is None:
        return None
    topics_by_id = {t["id"]: t for t in topic_rows if t.get("id")}

    out: list[dict[str, Any]] = []
    for r in flat:
        topic = topics_by_id.get(r.get("topic_id")) or {}
        if topic.get("is_active") is False:
            continue
        out.append(
            {
                "topic": topic.get("name") or topic.get("slug"),
                "topic_id": r.get("topic_id"),
                "priority_score": r.get("exam_priority_score"),
                "confidence_score": r.get("confidence_score"),
                "high_yield": bool(r.get("is_high_yield")),
                "status": "locked",
            }
        )

    def _score(row: dict[str, Any]) -> float:
        try:
            return float(row.get("priority_score") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    out.sort(key=_score, reverse=True)
    return out
