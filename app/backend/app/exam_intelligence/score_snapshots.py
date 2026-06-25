"""Versioned exam-topic score snapshot writer and reader.

Computes draft ``exam_topic_score_snapshots`` from verified PYQ evidence and
locked coverage. Snapshots are draft until an operator reviews/locks them.
Only locked snapshots reach the planner and user surfaces.

Frequency contract: primary-only. One verified question contributes at most
one count to a topic's frequency, through its primary tag. Questions with
multiple primary tags (ambiguous) are excluded from frequency counts.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger("career_copilot.exam_intelligence.score_snapshots")

MODEL_VERSION = "v1.0"  # bump when computation logic changes

_BATCH = 250   # max items per Supabase IN() filter
_PAGE = 1000   # rows per pagination page

# Postgres SQLSTATEs we want to surface loudly (schema drift / missing table)
_LOUD_PG_CODES = {"42703", "42P01"}


def _chunks(lst: list[Any], n: int) -> list[list[Any]]:
    """Split *lst* into chunks of at most *n* items each."""
    return [lst[i : i + n] for i in range(0, len(lst), n)]


def _safe(
    call: Any,
    default: Any = None,
    *,
    table: str | None = None,
    operation: str | None = None,
) -> Any:
    """Call *call()*, return *default* on any exception, logging the error."""
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "code", None) or getattr(exc, "pgcode", None)
        message = str(exc)
        level = logging.ERROR if code in _LOUD_PG_CODES else logging.WARNING
        logger.log(
            level,
            "exam_intelligence score_snapshots operation failed",
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
    """Fetch all rows using range-based pagination.

    *build_query(from_n, to_n)* must return a list of rows for the given
    inclusive ``[from_n, to_n]`` range. Returns ``None`` if any page read
    fails (caller should treat this as a read error).
    """
    all_rows: list[dict[str, Any]] = []
    offset = 0
    while True:
        rows = _safe(
            lambda o=offset: build_query(o, o + _PAGE - 1),
            default=None,
            table=table,
            operation=operation,
        )
        if rows is None:
            return None
        all_rows.extend(rows)
        if len(rows) < _PAGE:
            break
        offset += _PAGE
    return all_rows


def _build_fingerprint(
    exam_id: str,
    model_version: str,
    exam_phase_id: str | None,
    paper_ids: list[str],
    question_ids: list[str],
    primary_tag_tuples: list[tuple[str, str]],
    locked_cov_rows: list[dict[str, Any]],
) -> str:
    """SHA-256 fingerprint over all inputs that affect score computation.

    Including primary-tag content and locked-coverage values means that
    changing a topic assignment or a locked priority score invalidates the
    existing draft and triggers a re-compute.
    """
    phase_str = exam_phase_id or "null"
    tags_str = ",".join(sorted(f"{q}:{t}" for q, t in primary_tag_tuples))
    cov_str = ",".join(
        sorted(
            f"{r['topic_id']}:{r.get('exam_priority_score', 0)}:{int(bool(r.get('is_high_yield')))}"
            for r in locked_cov_rows
            if r.get("topic_id")
        )
    )
    raw = (
        f"{exam_id}:{model_version}:phase={phase_str}:"
        f"papers={','.join(sorted(paper_ids))}:"
        f"questions={','.join(sorted(question_ids))}:"
        f"tags={tags_str}:cov={cov_str}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def compute_exam_topic_scores(
    sb: Any,
    exam_id: str,
    model_version: str = MODEL_VERSION,
    *,
    exam_phase_id: str | None = None,
) -> dict[str, Any]:
    """Compute and write draft score snapshots for every topic in *exam_id*.

    Returns a summary dict::

        {
            "written": int,
            "skipped": int,
            "errors": int,
            "total_topics": int,
            "read_error": bool,     # True when a critical DB read failed
            "invalid_scope": bool,  # True when exam_phase_id is not in exam
        }

    Idempotent: topics whose existing drafts already contain the same
    fingerprint are skipped without re-writing.  Locked rows are never
    touched.

    ``read_error=True`` means one or more input reads failed; the caller
    (admin endpoint) must treat this as a compute failure, not a "no
    evidence" success.

    ``invalid_scope=True`` means *exam_phase_id* does not belong to the
    given exam; the caller should return HTTP 422, not 502.
    """
    zero: dict[str, Any] = {
        "written": 0,
        "skipped": 0,
        "errors": 0,
        "total_topics": 0,
        "read_error": False,
    }
    if not exam_id:
        return zero

    # ── 1. Validate phase belongs to exam ─────────────────────────────────
    if exam_phase_id:
        phase_rows = _safe(
            lambda: (
                sb.table("exam_phases")
                .select("id")
                .eq("id", exam_phase_id)
                .eq("exam_id", exam_id)
                .limit(1)
                .execute()
                .data
            ),
            default=None,
            table="exam_phases",
            operation="validate_phase",
        )
        if phase_rows is None:
            return {**zero, "read_error": True}
        if not phase_rows:
            logger.warning(
                "score_snapshots: exam_phase_id %r does not belong to exam %r",
                exam_phase_id,
                exam_id,
            )
            return {**zero, "invalid_scope": True}

    # ── 2. Verified papers (paginated) ────────────────────────────────────
    def _papers_page(from_n: int, to_n: int) -> list[dict[str, Any]]:
        q = (
            sb.table("pyq_papers")
            .select("id")
            .eq("exam_id", exam_id)
            .eq("trust_status", "verified")
        )
        if exam_phase_id:
            q = q.eq("exam_phase_id", exam_phase_id)
        return q.range(from_n, to_n).execute().data

    paper_rows = _paginate(
        _papers_page,
        table="pyq_papers",
        operation="select_verified_by_exam",
    )
    if paper_rows is None:
        return {**zero, "read_error": True}

    paper_ids: list[str] = [r["id"] for r in paper_rows if r.get("id")]
    if not paper_ids:
        return zero

    # ── 3. Verified questions (batched + paginated) ───────────────────────
    question_ids: list[str] = []
    for chunk in _chunks(paper_ids, _BATCH):
        def _questions_page(from_n: int, to_n: int, c: list[str] = chunk) -> list[dict[str, Any]]:
            return (
                sb.table("pyq_questions")
                .select("id")
                .in_("pyq_paper_id", c)
                .eq("reviewer_status", "verified")
                .range(from_n, to_n)
                .execute()
                .data
            )

        batch_rows = _paginate(
            _questions_page,
            table="pyq_questions",
            operation="select_verified",
        )
        if batch_rows is None:
            return {**zero, "read_error": True}
        question_ids.extend(r["id"] for r in batch_rows if r.get("id"))

    if not question_ids:
        return zero

    # ── 4. Primary tags (batched + paginated) ─────────────────────────────
    # Map each question to the set of topics it has primary tags for.
    q_to_topics: dict[str, set[str]] = {}
    for chunk in _chunks(question_ids, _BATCH):
        def _tags_page(from_n: int, to_n: int, c: list[str] = chunk) -> list[dict[str, Any]]:
            return (
                sb.table("pyq_question_topic_tags")
                .select("question_id, topic_id")
                .in_("question_id", c)
                .eq("reviewer_status", "verified")
                .eq("tag_role", "primary")
                .range(from_n, to_n)
                .execute()
                .data
            )

        batch_rows = _paginate(
            _tags_page,
            table="pyq_question_topic_tags",
            operation="select_primary_verified",
        )
        if batch_rows is None:
            return {**zero, "read_error": True}
        for row in batch_rows:
            qid, tid = row.get("question_id"), row.get("topic_id")
            if qid and tid:
                q_to_topics.setdefault(qid, set()).add(tid)

    # Questions with multiple primary topics are ambiguous: exclude them.
    ambiguous = [q for q, topics in q_to_topics.items() if len(topics) > 1]
    if ambiguous:
        logger.warning(
            "score_snapshots: %d questions have multiple primary tags — excluded from frequency counts",
            len(ambiguous),
            extra={"exam_id": exam_id, "ambiguous_sample": ambiguous[:5]},
        )

    primary_counts: dict[str, int] = {}
    primary_tag_tuples: list[tuple[str, str]] = []
    for qid, topics in q_to_topics.items():
        if len(topics) == 1:
            tid = next(iter(topics))
            primary_counts[tid] = primary_counts.get(tid, 0) + 1
            primary_tag_tuples.append((qid, tid))

    # ── 5. Locked coverage (paginated, phase-isolated) ────────────────────
    # Exam-wide reads use .is_("exam_phase_id", None) to exclude phase-
    # specific rows — mixing scopes would make the score nondeterministic.
    def _coverage_page(from_n: int, to_n: int) -> list[dict[str, Any]]:
        q = (
            sb.table("exam_topic_coverage")
            .select("topic_id, exam_priority_score, is_high_yield")
            .eq("exam_id", exam_id)
            .eq("reviewer_status", "locked")
        )
        if exam_phase_id:
            q = q.eq("exam_phase_id", exam_phase_id)
        else:
            q = q.is_("exam_phase_id", None)
        return q.range(from_n, to_n).execute().data

    locked_cov_rows = _paginate(
        _coverage_page,
        table="exam_topic_coverage",
        operation="select_locked",
    )
    if locked_cov_rows is None:
        return {**zero, "read_error": True}

    locked_cov: dict[str, dict[str, Any]] = {
        r["topic_id"]: r for r in locked_cov_rows if r.get("topic_id")
    }

    # ── 6. Fingerprint ────────────────────────────────────────────────────
    fingerprint = _build_fingerprint(
        exam_id,
        model_version,
        exam_phase_id,
        paper_ids,
        question_ids,
        primary_tag_tuples,
        locked_cov_rows,
    )

    # ── 7. Existing drafts (phase-scoped, paginated, fail closed) ─────────
    def _drafts_page(from_n: int, to_n: int) -> list[dict[str, Any]]:
        q = (
            sb.table("exam_topic_score_snapshots")
            .select("topic_id, input_summary")
            .eq("exam_id", exam_id)
            .eq("model_version", model_version)
            .eq("status", "draft")
        )
        if exam_phase_id:
            q = q.eq("exam_phase_id", exam_phase_id)
        else:
            q = q.is_("exam_phase_id", None)
        return q.range(from_n, to_n).execute().data

    existing_rows = _paginate(
        _drafts_page,
        table="exam_topic_score_snapshots",
        operation="select_drafts",
    )
    if existing_rows is None:
        # Fail closed: a DB error here is indistinguishable from "no drafts"
        # without this guard, causing duplicates on every recompute.
        return {**zero, "read_error": True}

    # Track ALL fingerprints per topic. If PostgREST row order varies between
    # runs, a single-row-per-topic dict could select a stale draft and miss
    # a matching fingerprint inserted by a prior run.
    existing_fps: dict[str, set[str]] = {}
    for r in existing_rows:
        tid = r.get("topic_id")
        fp = (r.get("input_summary") or {}).get("fingerprint")
        if tid and fp:
            existing_fps.setdefault(tid, set()).add(fp)

    # ── 8. Score each topic ───────────────────────────────────────────────
    all_topic_ids = set(primary_counts.keys()) | set(locked_cov.keys())
    total_primary = sum(primary_counts.values())

    written = skipped = errors = 0

    for tid in all_topic_ids:
        freq_component = primary_counts.get(tid, 0) / max(total_primary, 1)
        cov_component = float(locked_cov.get(tid, {}).get("exam_priority_score") or 0) / 100
        evidence_quality = min(primary_counts.get(tid, 0) / 10.0, 1.0)

        exam_priority_score = round(
            freq_component * 50 + cov_component * 40 + evidence_quality * 10, 2
        )
        is_high_yield = bool(locked_cov.get(tid, {}).get("is_high_yield")) or freq_component > 0.15
        confidence_score = round(min(0.3 + evidence_quality * 0.7, 1.0), 3)

        score_components = {
            "frequency_component": round(freq_component, 4),
            "coverage_component": round(cov_component, 4),
            "evidence_quality": round(evidence_quality, 4),
        }
        input_summary = {
            "fingerprint": fingerprint,
            "paper_count": len(paper_ids),
            "question_count": len(question_ids),
            "topic_primary_count": primary_counts.get(tid, 0),
            "corpus_total_primary": total_primary,
        }

        # Idempotency check: skip if current fingerprint is already in
        # any existing draft for this topic.
        if fingerprint in existing_fps.get(tid, set()):
            skipped += 1
            continue

        try:
            sb.table("exam_topic_score_snapshots").insert(
                {
                    "exam_id": exam_id,
                    "exam_phase_id": exam_phase_id,
                    "topic_id": tid,
                    "model_version": model_version,
                    "exam_priority_score": exam_priority_score,
                    "is_high_yield": is_high_yield,
                    "confidence_score": confidence_score,
                    "evidence_count": primary_counts.get(tid, 0),
                    "score_components": score_components,
                    "input_summary": input_summary,
                    "status": "draft",
                }
            ).execute()
            written += 1
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", None) or getattr(exc, "pgcode", None)
            logger.warning(
                "score_snapshots insert failed",
                extra={
                    "operation": "insert_draft",
                    "table": "exam_topic_score_snapshots",
                    "topic_id": tid,
                    "error_code": code,
                    "error_message": str(exc),
                },
            )
            errors += 1

    return {
        "written": written,
        "skipped": skipped,
        "errors": errors,
        "total_topics": len(all_topic_ids),
        "read_error": False,
    }


def locked_score_snapshots(
    sb: Any,
    exam_id: str,
    *,
    exam_phase_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return one locked snapshot per topic for planner consumption.

    Returns the latest-computed locked row per topic for the given scope,
    restricted to ``MODEL_VERSION`` to prevent a stale-model row from
    overriding a current-model result when multiple model versions exist.

    Scope is exam-wide when ``exam_phase_id`` is None; phase-specific
    otherwise. Mixed-scope reads are explicitly prevented — callers must
    pass a resolved phase or accept exam-wide rows.

    Result row shape::

        {
            "topic_id": str,
            "exam_priority_score": float|None,
            "is_high_yield": bool,
            "confidence_score": float|None,
            "model_version": str,
            "score_components": dict,
        }
    """
    if not exam_id:
        return []

    def _locked_page(from_n: int, to_n: int) -> list[dict[str, Any]]:
        q = (
            sb.table("exam_topic_score_snapshots")
            .select(
                "topic_id, exam_priority_score, is_high_yield, "
                "confidence_score, model_version, score_components, computed_at"
            )
            .eq("exam_id", exam_id)
            .eq("status", "locked")
            .eq("model_version", MODEL_VERSION)
        )
        if exam_phase_id:
            q = q.eq("exam_phase_id", exam_phase_id)
        else:
            q = q.is_("exam_phase_id", None)
        return q.order("computed_at", desc=True).range(from_n, to_n).execute().data

    rows = _paginate(
        _locked_page,
        table="exam_topic_score_snapshots",
        operation="select_locked",
    ) or []

    # Deduplicate to latest locked per topic (rows already sorted by computed_at desc).
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for r in rows:
        tid = r.get("topic_id")
        if tid and tid not in seen:
            seen.add(tid)
            deduped.append(
                {
                    "topic_id": tid,
                    "exam_priority_score": r.get("exam_priority_score"),
                    "is_high_yield": bool(r.get("is_high_yield")),
                    "confidence_score": r.get("confidence_score"),
                    "model_version": r.get("model_version"),
                    "score_components": r.get("score_components") or {},
                }
            )
    # Re-sort by priority descending for planner consumption.
    deduped.sort(key=lambda r: (r.get("exam_priority_score") or 0), reverse=True)
    return deduped


def list_exam_score_snapshots(
    sb: Any,
    exam_id: str,
    *,
    status: str | None = None,
) -> list[dict[str, Any]]:
    """Return all snapshots for an admin list view (paginated).

    Optionally filter by *status*. Returns full rows including review
    metadata (``reviewed_by``, ``reviewed_at``, ``reviewer_notes``).
    """
    if not exam_id:
        return []

    def _page(from_n: int, to_n: int) -> list[dict[str, Any]]:
        q = (
            sb.table("exam_topic_score_snapshots")
            .select("*")
            .eq("exam_id", exam_id)
        )
        if status:
            q = q.eq("status", status)
        return q.order("computed_at", desc=True).range(from_n, to_n).execute().data

    return _paginate(
        _page,
        table="exam_topic_score_snapshots",
        operation="select_all",
    ) or []
