"""Versioned exam-topic score snapshot writer and reader.

Computes draft ``exam_topic_score_snapshots`` from verified PYQ evidence and
locked coverage. Snapshots are draft until an operator reviews/locks them.
Only locked snapshots reach the planner and user surfaces.

Frequency contract: primary-only. One verified question contributes at most
one count to a topic's frequency, through its primary tag. Questions with
multiple primary tags (ambiguous) are excluded from frequency counts.

Scale contract (v2.0): a topic's frequency is measured against its **peer
cohort** — the papers that examine the topic's own subject — not against the
whole exam corpus. See ``_cohort_stats`` for the derivation and
``_cohort_weight`` for the neutrality guarantee that keeps single-cohort exams
(one undivided paper series examining every subject, e.g. an objective
general-studies Prelims paper) bit-for-bit identical to v1.0.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger("career_copilot.exam_intelligence.score_snapshots")

MODEL_VERSION = "v2.0"  # bump when computation logic changes

# ── Scale constants (model-wide, never per-exam) ──────────────────────────────
# A topic's cohort lift is how many times its cohort's mean question count it
# was asked. These two constants map lift onto the score; they are properties
# of the model, not tunables keyed on an exam.
_LIFT_FULL_MARKS = 10.0  # 10x the cohort mean earns the full frequency weight
_HIGH_YIELD_LIFT = 3.0   # 3x the cohort mean is "asked far more than its peers"

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


def _cohort_stats(
    primary_counts: dict[str, int],
    counted_tag_tuples: list[tuple[str, str]],
    q_to_paper: dict[str, str],
    topic_subject: dict[str, str],
) -> dict[str, tuple[int, int]]:
    """Return ``{topic_id: (cohort_total, cohort_topic_count)}``.

    A topic's **peer cohort** is the set of papers that examine the topic's own
    subject — derived from the evidence itself (which papers carry primary tags
    for topics owned by that subject), never from a configured exam id.
    ``cohort_total`` is the primary-counted question total over those papers and
    ``cohort_topic_count`` the number of distinct topics tagged in them.

    Why this is the right denominator for a descriptive paper: "Panchayati Raj
    is 14 of PSIR Paper-I's 392 questions" is a share a human can act on;
    "14 of the exam's 5,133" is not, because a PSIR question was never going to
    be asked in the History Optional paper. For an objective general-studies
    paper — where every paper examines every subject — every subject's cohort is
    the whole scope, so this reduces exactly to the v1.0 exam-wide denominator.

    Topics whose subject is unknown (``topics`` row missing) fall back to the
    whole scope, i.e. to v1.0 behaviour.
    """
    scope_papers = {q_to_paper[q] for q, _ in counted_tag_tuples if q in q_to_paper}
    scope_total = sum(primary_counts.values())
    scope_topic_count = len(primary_counts)

    # Per-paper primary totals and the topic set each paper touches.
    paper_total: dict[str, int] = {}
    paper_topics: dict[str, set[str]] = {}
    subject_papers: dict[str, set[str]] = {}
    for qid, tid in counted_tag_tuples:
        pid = q_to_paper.get(qid)
        if not pid:
            continue
        paper_total[pid] = paper_total.get(pid, 0) + 1
        paper_topics.setdefault(pid, set()).add(tid)
        sid = topic_subject.get(tid)
        if sid:
            subject_papers.setdefault(sid, set()).add(pid)

    by_subject: dict[str, tuple[int, int]] = {}
    for sid, papers in subject_papers.items():
        total = sum(paper_total.get(pid, 0) for pid in papers)
        topics: set[str] = set()
        for pid in papers:
            topics |= paper_topics.get(pid, set())
        by_subject[sid] = (total, len(topics))

    whole_scope = (scope_total, scope_topic_count)
    # A cohort that turns out to span every paper in the scope IS the scope;
    # normalise it to the exact scope totals so the neutrality guarantee holds
    # even when a paper carries no primary-counted question.
    return {
        tid: (
            whole_scope
            if (sid := topic_subject.get(tid)) is None
            or subject_papers.get(sid, set()) >= scope_papers
            else by_subject.get(sid, whole_scope)
        )
        for tid in primary_counts
    }


def _cohort_weight(cohort_total: int, scope_total: int) -> float:
    """How much of the score the cohort-relative axis owns, in ``[0, 1]``.

    ``1 - cohort_total/scope_total`` — the share of the exam that a topic's
    cohort does *not* cover. It is exactly ``0`` when the exam is a single
    cohort, which is what makes v2.0 bit-for-bit identical to v1.0 there: the
    cohort-prominence term drops out and the frequency denominator is unchanged.
    The more specialised an exam's papers are, the more a topic's standing among
    its own peers matters and the less its share of the whole exam means.
    """
    if scope_total <= 0 or cohort_total <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - cohort_total / scope_total))


def _build_fingerprint(
    exam_id: str,
    model_version: str,
    exam_phase_id: str | None,
    paper_ids: list[str],
    question_ids: list[str],
    primary_tag_tuples: list[tuple[str, str]],
    locked_cov_rows: list[dict[str, Any]],
    *,
    q_to_paper: dict[str, str] | None = None,
    topic_subject: dict[str, str] | None = None,
) -> str:
    """SHA-256 fingerprint over all inputs that affect score computation.

    Including primary-tag content and locked-coverage values means that
    changing a topic assignment or a locked priority score invalidates the
    existing draft and triggers a re-compute.

    v2.0 also folds in the question→paper and topic→subject maps, because a
    topic's cohort — and therefore its score — changes when a question moves
    paper or a topic moves subject, even though the tag tuples are unchanged.
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
        f"tags={tags_str}:cov={cov_str}:"
        f"qpapers={','.join(sorted(f'{q}:{p}' for q, p in (q_to_paper or {}).items()))}:"
        f"tsubjects={','.join(sorted(f'{t}:{sid}' for t, sid in (topic_subject or {}).items()))}"
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
    # ``pyq_paper_id`` comes back alongside the id: the cohort derivation needs
    # to know which paper each counted question sat in.
    question_ids: list[str] = []
    q_to_paper: dict[str, str] = {}
    for chunk in _chunks(paper_ids, _BATCH):
        def _questions_page(from_n: int, to_n: int, c: list[str] = chunk) -> list[dict[str, Any]]:
            return (
                sb.table("pyq_questions")
                .select("id, pyq_paper_id")
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
        for r in batch_rows:
            qid = r.get("id")
            if not qid:
                continue
            question_ids.append(qid)
            if r.get("pyq_paper_id"):
                q_to_paper[qid] = r["pyq_paper_id"]

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

    # ── 4b. Topic → subject (batched + paginated) ─────────────────────────
    # Owning subject is what defines a topic's peer cohort (``_cohort_stats``).
    # Fail closed like every other input read: a partial map would silently
    # move topics into the wrong cohort and change their scores.
    topic_subject: dict[str, str] = {}
    tagged_topic_ids = sorted(primary_counts.keys())
    for chunk in _chunks(tagged_topic_ids, _BATCH):
        def _topics_page(from_n: int, to_n: int, c: list[str] = chunk) -> list[dict[str, Any]]:
            return (
                sb.table("topics")
                .select("id, subject_id")
                .in_("id", c)
                .range(from_n, to_n)
                .execute()
                .data
            )

        batch_rows = _paginate(
            _topics_page,
            table="topics",
            operation="select_subject",
        )
        if batch_rows is None:
            return {**zero, "read_error": True}
        for row in batch_rows:
            tid, sid = row.get("id"), row.get("subject_id")
            if tid and sid:
                topic_subject[tid] = sid

    # ── 5. Locked coverage (paginated, phase-isolated) ────────────────────
    # Exam-wide reads use .is_("exam_phase_id", None) to exclude phase-
    # specific rows — mixing scopes would make the score nondeterministic.
    #
    # OD-3 (Option A, "break the input edge", J3 evidence-coverage gate):
    # source_basis='evidence_derived' coverage rows are EXCLUDED here. Those
    # rows are themselves a projection of THIS module's locked snapshots
    # (see coverage_derivation.py); folding them back into coverage_component
    # would create a self-reinforcing feedback loop across recompute cycles.
    # coverage_component must only ever reflect genuinely human-authored
    # coverage (manual/admin_review/official_syllabus/pyq_analysis/hybrid).
    # This is a scoring invariant enforced by tests, not a promotion check.
    def _coverage_page(from_n: int, to_n: int) -> list[dict[str, Any]]:
        q = (
            sb.table("exam_topic_coverage")
            .select("topic_id, exam_priority_score, is_high_yield, source_basis")
            .eq("exam_id", exam_id)
            .eq("reviewer_status", "locked")
            .neq("source_basis", "evidence_derived")
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
        q_to_paper=q_to_paper,
        topic_subject=topic_subject,
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
    cohorts = _cohort_stats(primary_counts, primary_tag_tuples, q_to_paper, topic_subject)

    written = skipped = errors = 0

    for tid in all_topic_ids:
        topic_count = primary_counts.get(tid, 0)
        cohort_total, cohort_topics = cohorts.get(tid, (total_primary, len(primary_counts)))

        # Frequency is a share of the topic's own cohort. When the exam is a
        # single cohort this is identical to the v1.0 exam-wide share.
        freq_component = topic_count / max(cohort_total, 1)
        cov_component = float(locked_cov.get(tid, {}).get("exam_priority_score") or 0) / 100
        evidence_quality = min(topic_count / 10.0, 1.0)

        # Cohort lift: how many times its cohort's mean a topic was asked. This
        # is the axis that discriminates on a descriptive paper, where no topic
        # can own a meaningful fraction of the exam but one can plainly own
        # several times its peers' share.
        cohort_mean = cohort_total / cohort_topics if cohort_topics else 0.0
        cohort_lift = topic_count / cohort_mean if cohort_mean > 0 else 0.0
        prominence = min(cohort_lift / _LIFT_FULL_MARKS, 1.0)
        weight = _cohort_weight(cohort_total, total_primary)

        # The frequency weight is blended between the exam-wide share (v1.0) and
        # cohort prominence, by how specialised the topic's cohort is. weight==0
        # on a single-cohort exam collapses this to ``freq_component * 50``.
        frequency_term = freq_component * 50 * (1 - weight) + prominence * 50 * weight

        exam_priority_score = round(
            frequency_term + cov_component * 40 + evidence_quality * 10, 2
        )
        is_high_yield = (
            bool(locked_cov.get(tid, {}).get("is_high_yield"))
            or freq_component > 0.15
            # Relative high yield, available only where cohorts actually
            # partition the corpus: asked far more than its own peers.
            or (weight > 0 and cohort_lift >= _HIGH_YIELD_LIFT)
        )
        confidence_score = round(min(0.3 + evidence_quality * 0.7, 1.0), 3)

        score_components = {
            "frequency_component": round(freq_component, 4),
            "coverage_component": round(cov_component, 4),
            "evidence_quality": round(evidence_quality, 4),
            "cohort_lift": round(cohort_lift, 4),
            "cohort_prominence": round(prominence, 4),
            "cohort_weight": round(weight, 4),
        }
        input_summary = {
            "fingerprint": fingerprint,
            "paper_count": len(paper_ids),
            "question_count": len(question_ids),
            "topic_primary_count": topic_count,
            "corpus_total_primary": total_primary,
            "cohort_total_primary": cohort_total,
            "cohort_topic_count": cohort_topics,
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
) -> list[dict[str, Any]] | None:
    """Return one locked snapshot per topic for planner consumption.

    Returns the latest-computed locked row per topic for the given scope,
    restricted to ``MODEL_VERSION`` to prevent a stale-model row from
    overriding a current-model result when multiple model versions exist.

    Scope is exam-wide when ``exam_phase_id`` is None; phase-specific
    otherwise. Mixed-scope reads are explicitly prevented — callers must
    pass a resolved phase or accept exam-wide rows.

    Snapshots are cycle-independent by design: the writer does not set
    ``exam_cycle_id`` and the corpus is all-time verified PYQs. No cycle
    filter is applied here; callers must not expect cycle-scoped rows.

    Returns ``None`` on DB read failure; caller must distinguish from empty
    list (no locked snapshots yet computed).

    Result row shape::

        {
            "snapshot_id": str|None,
            "topic_id": str,
            "exam_priority_score": float|None,
            "is_high_yield": bool,
            "confidence_score": float|None,
            "model_version": str,
            "score_components": dict,
            "computed_at": str|None,
            "evidence_count": int|None,
            "fingerprint": str|None,   # snapshot's own input_summary.fingerprint
        }
    """
    if not exam_id:
        return []

    def _locked_page(from_n: int, to_n: int) -> list[dict[str, Any]]:
        q = (
            sb.table("exam_topic_score_snapshots")
            .select(
                "id, topic_id, exam_priority_score, is_high_yield, "
                "confidence_score, model_version, score_components, computed_at, "
                "evidence_count, input_summary"
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
    )
    if rows is None:
        return None  # read failure — caller must distinguish from empty list

    # Deduplicate to latest locked per topic (rows already sorted by computed_at desc).
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for r in rows:
        tid = r.get("topic_id")
        if tid and tid not in seen:
            seen.add(tid)
            deduped.append({
                "snapshot_id": r.get("id"),
                "topic_id": tid,
                "exam_priority_score": r.get("exam_priority_score"),
                "is_high_yield": bool(r.get("is_high_yield")),
                "confidence_score": r.get("confidence_score"),
                "model_version": r.get("model_version"),
                "score_components": r.get("score_components") or {},
                "computed_at": r.get("computed_at"),
                "evidence_count": r.get("evidence_count"),
                # P1-1 fix (J3 PR4 checkpost): expose the snapshot's OWN input
                # fingerprint (input_summary.fingerprint) so downstream
                # projections (coverage_derivation.py) can build their
                # derivation fingerprint over the snapshot's actual inputs,
                # not just its model_version. model_version alone does not
                # change when the underlying verified evidence changes, so
                # using it as a proxy for "did the snapshot's inputs change"
                # silently masked real input changes.
                "fingerprint": (r.get("input_summary") or {}).get("fingerprint"),
            })
    # Re-sort by priority descending for planner consumption.
    deduped.sort(key=lambda r: (r.get("exam_priority_score") or 0), reverse=True)
    return deduped


def list_exam_score_snapshots(
    sb: Any,
    exam_id: str,
    *,
    status: str | None = None,
    exam_phase_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return all snapshots for an admin list view (paginated).

    Optionally filter by *status* and *exam_phase_id*.  When *exam_phase_id*
    is supplied only rows for that phase are returned; when ``None`` only
    exam-wide rows (``exam_phase_id IS NULL``) are returned.  Mixing scopes
    in a single call is intentionally not supported — operators review one
    scope at a time to avoid comparing incomparable evidence sets.

    Returns full rows including review metadata.
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
        if exam_phase_id:
            q = q.eq("exam_phase_id", exam_phase_id)
        else:
            q = q.is_("exam_phase_id", None)
        return q.order("computed_at", desc=True).range(from_n, to_n).execute().data

    return _paginate(
        _page,
        table="exam_topic_score_snapshots",
        operation="select_all",
    ) or []
