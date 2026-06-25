"""Console work-queue aggregation (Wave 4.6H) — read-only, set-based.

Builds the per-exam console work queue and the catalogue summary from a paged
candidate load plus a bounded number of paged, chunked child reads. There is NO
per-exam round-trip: it never calls ``compute_exam_workspace_readiness`` or
``assemble_mock_readiness_report`` per exam. One pure classifier
(``classify_exam``) derives the primary status + orthogonal flags; the list and
summary share that classifier and the same candidate scope.

Truthfulness guarantees (see docs/exam-governance/backend-capability-preflight-4.6H0.md):
- Planner-consumable coverage == ``exam_topic_coverage.reviewer_status='locked'``.
  ``reviewed`` does NOT count.
- ``verified_pyq_count`` counts DISTINCT questions clearing all three gates:
  parent ``pyq_papers.trust_status='verified'`` AND
  ``pyq_questions.reviewer_status='verified'`` AND at least one
  ``pyq_question_topic_tags`` row with ``reviewer_status='verified'``.
- Exactly one primary status per exam: ``blocked`` | ``needs_action`` | ``ready``.
- Every correctness-critical read pages fully (no silent row cap) and raises
  ``DatabaseError`` on failure — a failed read never degrades to fabricated
  empty/blocked truth.
- No response field carries score_percent / confidence_score / confidence_percent;
  ``state``/``jurisdiction`` are never inferred from the slug.

NOTE: ``thin_mock_bank`` is intentionally NOT produced here. A truthful
list-level thin-mock signal requires the section-attributed, valid_until- and
question_type-aware diagnostic (``diagnostics.assemble_mock_readiness_report``)
which is per-exam; an exam-total approximation is not equivalent and would be a
misleading governance flag. Exact per-exam mock readiness is deferred to
4.6I-BE; a set-based catalogue aggregation remains future work.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable

from app.db.utils import execute_or_raise
from app.exam_intelligence.pyq_readiness import aggregate_pyq_evidence_batch

# ── Constants (grounded in source) ──────────────────────────────────────────
# Review-queue staleness threshold. Mirrors
# admin_exam_intelligence._STALE_REVIEW_DAYS (= 14). NOT the 30-day policy rule
# (readiness._STALE_DAYS), which is a different KPI and out of scope here.
STALE_REVIEW_DAYS = 14

# Page size for required reads. Large enough that normal admin catalogues fetch
# in one page; small datasets in tests fetch in one page too. Monkeypatched to a
# small value in the paging tests.
_PAGE_SIZE = 1000
_CHUNK = 500  # batch size for `.in_(...)` reads (URL-length safety)

# Per-table "awaiting reviewer action" lifecycle states. Each table has its own
# vocabulary — do NOT blanket one set across tables.
_PENDING_STATES: dict[str, frozenset[str]] = {
    "syllabus_topic_mentions": frozenset({"pending", "needs_correction"}),
    # coverage lifecycle: draft → pending_review → reviewed → locked → rejected
    "exam_topic_coverage": frozenset({"pending_review", "needs_correction"}),
    "pyq_questions": frozenset({"pending", "needs_correction"}),
    "pyq_question_topic_tags": frozenset({"pending", "needs_correction"}),
    "pyq_options": frozenset({"pending", "needs_correction"}),
    "exam_policy_updates": frozenset({"pending", "needs_correction"}),
}

# Reviewable table → (console area, exact evidence kind). Used only by the
# include_details path so each pending row carries a typed evidence ref.
_TABLE_AREA_KIND = {
    "exam_topic_coverage": ("topic_coverage", "exam_topic_coverage"),
    "syllabus_topic_mentions": ("syllabus", "syllabus_topic_mention"),
    "exam_policy_updates": ("updates", "exam_policy_updates"),
    "pyq_questions": ("pyq", "pyq_question"),
    "pyq_question_topic_tags": ("pyq", "pyq_question_topic_tag"),
    "pyq_options": ("pyq", "pyq_option"),
}

# Ranks for deterministic sorting.
STATUS_RANK = {"blocked": 0, "needs_action": 1, "ready": 2}
_LANE_RANK = {"core": 0, "light": 1, "index_only": 2, None: 3, "archive": 4}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _chunked(items: list[Any], size: int = _CHUNK) -> Iterable[list[Any]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _fetch_all_pages(make_query: Callable[[], Any], *, operation: str,
                     page_size: int | None = None) -> list[dict[str, Any]]:
    """Page a required read to completion. ``make_query`` returns a FRESH query
    (already filtered + deterministically ordered) each call; we apply
    ``.range`` per page and stop only on a short page. Raises ``DatabaseError``
    on any failure (never silently truncates or degrades to [])."""
    size = page_size or _PAGE_SIZE
    out: list[dict[str, Any]] = []
    start = 0
    while True:
        end = start + size - 1
        page = execute_or_raise(
            operation, lambda s=start, e=end: make_query().range(s, e).execute().data
        ) or []
        out.extend(page)
        if len(page) < size:
            break
        start += size
    return out


# ── Candidate load (base filters byte-identical to list_exams) ──────────────

def load_candidates(sb, *, q_sanitized: str, exam_type: str | None, active_state: str,
                    management_mode: str | None, cadence: str | None,
                    exam_family_id: str | None) -> list[dict[str, Any]]:
    """Load the COMPLETE base-filtered candidate set (same predicate as
    ``GET /exams``), paged. Ordered by id for stable paging; the API's console
    sort happens later, after classification."""
    cols = ("id, slug, name, exam_type, is_active, exam_family_id, "
            "management_mode, cadence, conducting_organization_id")

    def _mk():
        qb = sb.table("exams").select(cols)
        if q_sanitized:
            qb = qb.or_(f"name.ilike.%{q_sanitized}%,slug.ilike.%{q_sanitized}%")
        if exam_type is not None:
            qb = qb.eq("exam_type", exam_type)
        if active_state == "active":
            qb = qb.eq("is_active", True)
        elif active_state == "inactive":
            qb = qb.eq("is_active", False)
        if management_mode == "__null__":
            qb = qb.or_("management_mode.is.null")
        elif management_mode is not None:
            qb = qb.eq("management_mode", management_mode)
        else:
            qb = qb.or_("management_mode.is.null,management_mode.neq.archive")
        if cadence is not None:
            qb = qb.eq("cadence", cadence)
        if exam_family_id is not None:
            qb = qb.eq("exam_family_id", exam_family_id)
        return qb.order("id")

    return _fetch_all_pages(_mk, operation="console.candidates")


def _batch_paged(sb, table: str, key: str, ids: list[str], columns: str) -> list[dict[str, Any]]:
    """Fetch ``columns`` from ``table`` where ``key`` IN ``ids`` — chunked over
    ids (URL safety) and paged within each chunk (no row cap). Required read:
    raises ``DatabaseError`` on failure."""
    out: list[dict[str, Any]] = []
    for chunk in _chunked(ids):
        out.extend(_fetch_all_pages(
            lambda c=chunk: sb.table(table).select(columns).in_(key, c).order("id"),
            operation=f"console.{table}",
        ))
    return out


# ── Aggregation (reads scale with tables × id-chunks × pages, never per-exam) ─

def aggregate(sb, exams: list[dict[str, Any]], *, include_details: bool = False) -> dict[str, dict[str, Any]]:
    """Aggregate per-exam signals for the candidate ``exams``. Returns
    ``{exam_id: aggregate_dict}``.

    ``include_details=False`` (default) is the list/summary path — output
    unchanged. ``include_details=True`` additionally records, per exam, a
    ``pending_by_area`` map with each pending area's ``pending_count``,
    ``stale_count``, and TYPED ``evidence_refs`` ({kind,row_id}) — so a
    ``needs_action`` verdict can always be explained by a matching area."""
    exam_ids = [e["id"] for e in exams if e.get("id")]
    stale_cutoff = (_now() - timedelta(days=STALE_REVIEW_DAYS)).isoformat()

    def _new_slot() -> dict[str, Any]:
        slot = {
            "phase_count": 0,
            "locked_coverage_count": 0,
            "total_pyq_count": 0,
            "verified_pyq_count": 0,
            "pending_review_count": 0,
            "stale_review_count": 0,
        }
        if include_details:
            slot["pending_by_area"] = {
                area: {"pending_count": 0, "stale_count": 0, "evidence_refs": []}
                for area in ("topic_coverage", "syllabus", "updates", "pyq")
            }
        return slot

    agg: dict[str, dict[str, Any]] = {eid: _new_slot() for eid in exam_ids}
    if not exam_ids:
        return agg

    def _bump_pending(exam_id: str, status: str, created_at: str | None, table: str,
                      row_id: str | None = None) -> None:
        slot = agg.get(exam_id)
        if slot is None:
            return
        if status in _PENDING_STATES[table]:
            stale = (created_at or "") < stale_cutoff
            slot["pending_review_count"] += 1
            if stale:
                slot["stale_review_count"] += 1
            if include_details and row_id:
                area, kind = _TABLE_AREA_KIND[table]
                d = slot["pending_by_area"][area]
                d["pending_count"] += 1
                if stale:
                    d["stale_count"] += 1
                d["evidence_refs"].append({"kind": kind, "row_id": row_id})

    # Setup: phase count.
    for r in _batch_paged(sb, "exam_phases", "exam_id", exam_ids, "id, exam_id"):
        slot = agg.get(r.get("exam_id"))
        if slot is not None:
            slot["phase_count"] += 1

    # Coverage: locked-only planner coverage + pending review.
    for r in _batch_paged(sb, "exam_topic_coverage", "exam_id", exam_ids,
                          "id, exam_id, reviewer_status, created_at"):
        slot = agg.get(r.get("exam_id"))
        if slot is None:
            continue
        if r.get("reviewer_status") == "locked":
            slot["locked_coverage_count"] += 1
        _bump_pending(r.get("exam_id"), r.get("reviewer_status"), r.get("created_at"),
                      "exam_topic_coverage", r.get("id"))

    # Syllabus: pending review.
    for r in _batch_paged(sb, "syllabus_topic_mentions", "exam_id", exam_ids,
                          "id, exam_id, reviewer_status, created_at"):
        _bump_pending(r.get("exam_id"), r.get("reviewer_status"), r.get("created_at"),
                      "syllabus_topic_mentions", r.get("id"))

    # Policy updates: pending review.
    for r in _batch_paged(sb, "exam_policy_updates", "exam_id", exam_ids,
                          "id, exam_id, reviewer_status, created_at"):
        _bump_pending(r.get("exam_id"), r.get("reviewer_status"), r.get("created_at"),
                      "exam_policy_updates", r.get("id"))

    # ── PYQ: papers → questions → tags/options. Three-gate verified count. ──
    papers = _batch_paged(sb, "pyq_papers", "exam_id", exam_ids, "id, exam_id, trust_status, exam_cycle_id")
    paper_exam = {p["id"]: p.get("exam_id") for p in papers if p.get("id")}
    verified_paper_ids = {p["id"] for p in papers if p.get("trust_status") == "verified"}
    paper_ids = list(paper_exam.keys())

    question_exam: dict[str, str] = {}
    # Questions that clear gates 1+2 (verified paper + verified question), pending
    # only the verified-tag gate; resolved after the tag read.
    verified_eligible: dict[str, str] = {}
    all_questions: list[dict] = []
    if paper_ids:
        for r in _batch_paged(sb, "pyq_questions", "pyq_paper_id", paper_ids,
                              "id, pyq_paper_id, reviewer_status, created_at"):
            exam_id = paper_exam.get(r.get("pyq_paper_id"))
            slot = agg.get(exam_id)
            if slot is None:
                continue
            qid = r.get("id")
            question_exam[qid] = exam_id
            all_questions.append(r)
            if r.get("reviewer_status") == "verified" and r.get("pyq_paper_id") in verified_paper_ids:
                verified_eligible[qid] = exam_id
            _bump_pending(exam_id, r.get("reviewer_status"), r.get("created_at"), "pyq_questions", qid)

    question_ids = list(question_exam.keys())
    all_tags: list[dict] = []
    if question_ids:
        for r in _batch_paged(sb, "pyq_question_topic_tags", "question_id", question_ids,
                              "id, question_id, reviewer_status, created_at"):
            all_tags.append(r)
            _bump_pending(question_exam.get(r.get("question_id")), r.get("reviewer_status"),
                          r.get("created_at"), "pyq_question_topic_tags", r.get("id"))
        for r in _batch_paged(sb, "pyq_options", "question_id", question_ids,
                              "id, question_id, reviewer_status, created_at"):
            _bump_pending(question_exam.get(r.get("question_id")), r.get("reviewer_status"),
                          r.get("created_at"), "pyq_options", r.get("id"))

    # Delegate three-gate verified count and total to the shared batch aggregator.
    pyq_batch = aggregate_pyq_evidence_batch(papers=papers, questions=all_questions, topic_tags=all_tags)
    for eid in exam_ids:
        agg[eid]["verified_pyq_count"] = pyq_batch.get(eid, {}).get("verified_question_count", 0)
        agg[eid]["total_pyq_count"] = pyq_batch.get(eid, {}).get("questions_total", 0)

    return agg


# ── Pure classifier (the single source of status/flag truth) ────────────────

def classify_exam(a: dict[str, Any]) -> dict[str, Any]:
    """Derive {status, flags, blocker_count, first_blocker_text} from one exam's
    aggregate. Pure: no I/O. Exactly one primary status."""
    hard_blockers: list[str] = []
    if a["phase_count"] == 0:
        hard_blockers.append("Setup incomplete — no exam phases defined")
    if a["locked_coverage_count"] == 0:
        hard_blockers.append("No locked topic coverage — planner cannot use this exam")

    flags: list[str] = []
    if a["locked_coverage_count"] == 0:
        flags.append("missing_coverage")
    if a["verified_pyq_count"] == 0:
        flags.append("missing_pyq")
    if a["pending_review_count"] > 0:
        flags.append("pending_review")
    if a["stale_review_count"] > 0:
        flags.append("stale_review_queue")

    if hard_blockers:
        status = "blocked"
    elif flags:
        status = "needs_action"
    else:
        status = "ready"

    return {
        "status": status,
        "flags": flags,
        "blocker_count": len(hard_blockers),  # hard gates only; advisory flags excluded
        "first_blocker_text": hard_blockers[0] if hard_blockers else None,
    }


# ── Row assembly + sort/filter/paginate ─────────────────────────────────────

_PRIMARY = {"blocked", "needs_action", "ready"}


def build_rows(exams: list[dict[str, Any]], agg: dict[str, dict[str, Any]],
               org_names: dict[str, str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for e in exams:
        a = agg.get(e["id"])
        if a is None:
            continue
        c = classify_exam(a)
        org_id = e.get("conducting_organization_id")
        rows.append({
            "id": e["id"],
            "slug": e.get("slug"),
            "name": e.get("name"),
            "exam_type": e.get("exam_type"),
            "management_mode": e.get("management_mode"),
            "cadence": e.get("cadence"),
            "exam_family_id": e.get("exam_family_id"),
            "organization_name": org_names.get(org_id) if org_id else None,
            "status": c["status"],
            "flags": c["flags"],
            "blocker_count": c["blocker_count"],
            "first_blocker_text": c["first_blocker_text"],
            "locked_coverage_count": a["locked_coverage_count"],
            "verified_pyq_count": a["verified_pyq_count"],
            "total_pyq_count": a["total_pyq_count"],
        })
    return rows


def apply_workflow(rows: list[dict[str, Any]], workflow: str | None) -> list[dict[str, Any]]:
    if not workflow:
        return rows
    if workflow in _PRIMARY:
        return [r for r in rows if r["status"] == workflow]
    return [r for r in rows if workflow in r["flags"]]


def sort_rows(rows: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    def key(r: dict[str, Any]):
        name, rid = r["name"] or "", r["id"]
        if sort == "name":
            return (0, 0, name, rid)
        if sort == "management_lane":
            return (_LANE_RANK.get(r["management_mode"], _LANE_RANK[None]),
                    STATUS_RANK[r["status"]], name, rid)
        # blockers_first (default): worst status first, then most blockers.
        return (STATUS_RANK[r["status"]], -r["blocker_count"], name, rid)

    return sorted(rows, key=key)


def load_org_names(sb, exams: list[dict[str, Any]]) -> dict[str, str]:
    org_ids = sorted({e.get("conducting_organization_id") for e in exams
                      if e.get("conducting_organization_id")})
    if not org_ids:
        return {}
    names: dict[str, str] = {}
    for r in _batch_paged(sb, "organizations", "id", org_ids, "id, name"):
        if r.get("id"):
            names[r["id"]] = r.get("name")
    return names


def build_classified_rows(sb, base_filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Shared entry point: candidate load → aggregate → classify → rows.
    Both the list and the summary consume this (same scope, same classifier)."""
    exams = load_candidates(sb, **base_filters)
    agg = aggregate(sb, exams)
    org_names = load_org_names(sb, exams)
    return build_rows(exams, agg, org_names)


def summary_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "blocked": 0, "needs_action": 0, "ready": 0,
        "pending_review": 0, "stale_review_queue": 0,
    }
    for r in rows:
        counts[r["status"]] += 1
        for flag in ("pending_review", "stale_review_queue"):
            if flag in r["flags"]:
                counts[flag] += 1
    return counts


# ── Deterministic current-cycle selection (design-lock Section 8.3) ─────────

_CYCLE_STATUS_PRIORITY = {"active": 0, "open": 1, "expected": 2}


def select_current_cycle(cycles: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the 'current' cycle deterministically per design-lock Section 8.3.

    Priority: active > open > expected > highest year > lowest UUID.
    The backend applies this rule; the frontend receives ``current_cycle``
    pre-selected and must NOT recompute or override it on initial load.
    """
    if not cycles:
        return None

    def _key(c: dict[str, Any]) -> tuple:
        return (
            _CYCLE_STATUS_PRIORITY.get(c.get("status") or "", 3),
            -(c.get("year") or 0),
            c.get("id") or "",
        )

    return min(cycles, key=_key)
