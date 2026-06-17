"""Console work-queue aggregation (Wave 4.6H) — read-only, set-based.

Builds the per-exam console work queue and the catalogue summary from a single
candidate load plus a bounded, constant number of batched child reads. There is
NO per-exam round-trip: it never calls ``compute_exam_workspace_readiness`` or
``assemble_mock_readiness_report`` per exam. One pure classifier
(``classify_exam``) derives the primary status + orthogonal flags; the list and
summary share that classifier and the same candidate scope.

Hard product invariants (see docs/exam-governance/backend-capability-preflight-4.6H0.md):
- Planner-consumable coverage == ``exam_topic_coverage.reviewer_status='locked'``.
  ``reviewed`` does NOT count.
- Mock readiness is advisory: ``thin_mock_bank`` is never, by itself, a blocker.
- Exactly one primary status per exam: ``blocked`` | ``needs_action`` | ``ready``.
- No response field carries score_percent / confidence_score / confidence_percent;
  ``state``/``jurisdiction`` are never inferred from the slug.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable

# ── Constants (grounded in source) ──────────────────────────────────────────
# Review-queue staleness threshold. Mirrors
# admin_exam_intelligence._STALE_REVIEW_DAYS (= 14). NOT the 30-day policy rule
# (readiness._STALE_DAYS), which is a different KPI and out of scope here.
STALE_REVIEW_DAYS = 14
# Selectable mock-bank depth below which the bank is "thin" (advisory). Mirrors
# the diagnostics mock-readiness default ``min_per_section`` (= 30).
MIN_SELECTABLE_MOCK = 30
# Mock reviewer_status values that count as selectable answerable items, mirroring
# the diagnostics endpoint default (selectable_status = ["verified", "published"]).
SELECTABLE_MOCK_STATUSES = ("verified", "published")

# Bounded fetch cap — mirrors the existing list_exams child-read convention
# (.limit(20000)); the admin exam catalogue is far smaller.
_MAX_ROWS = 20000
_CHUNK = 500  # batch size for `.in_(...)` reads

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

# Ranks for deterministic sorting.
STATUS_RANK = {"blocked": 0, "needs_action": 1, "ready": 2}
_LANE_RANK = {"core": 0, "light": 1, "index_only": 2, None: 3, "archive": 4}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _chunked(items: list[Any], size: int = _CHUNK) -> Iterable[list[Any]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception:  # pragma: no cover - defensive; mirrors list_exams._safe
        return default


# ── Candidate load (base filters byte-identical to list_exams) ──────────────

def load_candidates(sb, *, q_sanitized: str, exam_type: str | None, active_state: str,
                    management_mode: str | None, cadence: str | None,
                    exam_family_id: str | None) -> list[dict[str, Any]]:
    """Load the base-filtered candidate exams (the same predicate as
    ``GET /exams``), fetching only the columns the work queue needs."""
    qb = sb.table("exams").select(
        "id, slug, name, exam_type, is_active, exam_family_id, management_mode, "
        "cadence, conducting_organization_id"
    )
    if q_sanitized:
        qb = qb.or_(f"name.ilike.%{q_sanitized}%,slug.ilike.%{q_sanitized}%")
    if exam_type is not None:
        qb = qb.eq("exam_type", exam_type)
    if active_state == "active":
        qb = qb.eq("is_active", True)
    elif active_state == "inactive":
        qb = qb.eq("is_active", False)
    if management_mode == "__null__":
        # Unclassified sentinel — select rows with no lane. Same rows as
        # list_exams' `.is_("management_mode","null")`; expressed via or_ so the
        # NULL match is unambiguous to PostgREST and the in-memory test stub.
        qb = qb.or_("management_mode.is.null")
    elif management_mode is not None:
        qb = qb.eq("management_mode", management_mode)
    else:
        qb = qb.or_("management_mode.is.null,management_mode.neq.archive")
    if cadence is not None:
        qb = qb.eq("cadence", cadence)
    if exam_family_id is not None:
        qb = qb.eq("exam_family_id", exam_family_id)
    return _safe(lambda: qb.order("name").limit(_MAX_ROWS).execute().data, default=[]) or []


def _batch_rows(sb, table: str, key: str, ids: list[str], columns: str) -> list[dict[str, Any]]:
    """Fetch ``columns`` from ``table`` where ``key`` IN ``ids`` (chunked)."""
    out: list[dict[str, Any]] = []
    for chunk in _chunked(ids):
        rows = _safe(
            lambda c=chunk: sb.table(table).select(columns).in_(key, c).limit(_MAX_ROWS).execute().data,
            default=[],
        ) or []
        out.extend(rows)
    return out


# ── Aggregation (constant number of reads, regardless of exam count) ────────

def aggregate(sb, exams: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Aggregate per-exam signals for the candidate ``exams``. Returns
    ``{exam_id: aggregate_dict}``. Bounded reads: one per child table (+ PYQ
    sub-joins), each chunked — never one read per exam."""
    exam_ids = [e["id"] for e in exams if e.get("id")]
    stale_cutoff = (_now() - timedelta(days=STALE_REVIEW_DAYS)).isoformat()

    agg: dict[str, dict[str, Any]] = {
        eid: {
            "phase_count": 0,
            "locked_coverage_count": 0,
            "total_pyq_count": 0,
            "verified_pyq_count": 0,
            "selectable_mock_count": 0,
            "pending_review_count": 0,
            "stale_review_count": 0,
        }
        for eid in exam_ids
    }
    if not exam_ids:
        return agg

    def _bump_pending(exam_id: str, status: str, created_at: str | None, table: str) -> None:
        slot = agg.get(exam_id)
        if slot is None:
            return
        if status in _PENDING_STATES[table]:
            slot["pending_review_count"] += 1
            if (created_at or "") < stale_cutoff:
                slot["stale_review_count"] += 1

    # Setup: phase count.
    for r in _batch_rows(sb, "exam_phases", "exam_id", exam_ids, "id, exam_id"):
        slot = agg.get(r.get("exam_id"))
        if slot is not None:
            slot["phase_count"] += 1

    # Coverage: locked-only planner coverage + pending review.
    for r in _batch_rows(sb, "exam_topic_coverage", "exam_id", exam_ids,
                         "exam_id, reviewer_status, created_at"):
        slot = agg.get(r.get("exam_id"))
        if slot is None:
            continue
        if r.get("reviewer_status") == "locked":
            slot["locked_coverage_count"] += 1
        _bump_pending(r.get("exam_id"), r.get("reviewer_status"), r.get("created_at"),
                      "exam_topic_coverage")

    # Syllabus: pending review.
    for r in _batch_rows(sb, "syllabus_topic_mentions", "exam_id", exam_ids,
                         "exam_id, reviewer_status, created_at"):
        _bump_pending(r.get("exam_id"), r.get("reviewer_status"), r.get("created_at"),
                      "syllabus_topic_mentions")

    # Policy updates: pending review.
    for r in _batch_rows(sb, "exam_policy_updates", "exam_id", exam_ids,
                         "exam_id, reviewer_status, created_at"):
        _bump_pending(r.get("exam_id"), r.get("reviewer_status"), r.get("created_at"),
                      "exam_policy_updates")

    # Mock bank: selectable depth (advisory).
    for r in _batch_rows(sb, "mock_question_bank", "exam_id", exam_ids,
                         "exam_id, reviewer_status"):
        slot = agg.get(r.get("exam_id"))
        if slot is not None and r.get("reviewer_status") in SELECTABLE_MOCK_STATUSES:
            slot["selectable_mock_count"] += 1

    # ── PYQ: papers → questions → (tags, options). Bounded sub-joins. ──
    papers = _batch_rows(sb, "pyq_papers", "exam_id", exam_ids,
                         "id, exam_id, trust_status")
    paper_exam = {p["id"]: p.get("exam_id") for p in papers if p.get("id")}
    verified_paper_ids = {p["id"] for p in papers if p.get("trust_status") == "verified"}
    paper_ids = list(paper_exam.keys())

    question_exam: dict[str, str] = {}
    if paper_ids:
        for r in _batch_rows(sb, "pyq_questions", "pyq_paper_id", paper_ids,
                             "id, pyq_paper_id, reviewer_status, created_at"):
            exam_id = paper_exam.get(r.get("pyq_paper_id"))
            slot = agg.get(exam_id)
            if slot is None:
                continue
            question_exam[r.get("id")] = exam_id
            slot["total_pyq_count"] += 1
            # Verified PYQ requires BOTH a verified parent paper and a verified
            # question — the planner invariant (coverage.verified_pyq_topic_counts).
            if r.get("reviewer_status") == "verified" and r.get("pyq_paper_id") in verified_paper_ids:
                slot["verified_pyq_count"] += 1
            _bump_pending(exam_id, r.get("reviewer_status"), r.get("created_at"), "pyq_questions")

    question_ids = list(question_exam.keys())
    if question_ids:
        for r in _batch_rows(sb, "pyq_question_topic_tags", "question_id", question_ids,
                             "question_id, reviewer_status, created_at"):
            _bump_pending(question_exam.get(r.get("question_id")), r.get("reviewer_status"),
                          r.get("created_at"), "pyq_question_topic_tags")
        for r in _batch_rows(sb, "pyq_options", "question_id", question_ids,
                             "question_id, reviewer_status, created_at"):
            _bump_pending(question_exam.get(r.get("question_id")), r.get("reviewer_status"),
                          r.get("created_at"), "pyq_options")

    return agg


# ── Pure classifier (the single source of status/flag truth) ────────────────

def classify_exam(a: dict[str, Any]) -> dict[str, Any]:
    """Derive {status, flags, blocker_count, first_blocker_text} from one exam's
    aggregate. Pure: no I/O. Exactly one primary status."""
    # Hard gates, in deterministic priority order. blocker_count counts hard
    # gates only — advisory flags are excluded.
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
    # Advisory: only meaningful once the exam is otherwise planner-relevant
    # (has locked coverage). Never a hard blocker.
    if a["locked_coverage_count"] > 0 and a["selectable_mock_count"] < MIN_SELECTABLE_MOCK:
        flags.append("thin_mock_bank")

    if hard_blockers:
        status = "blocked"
    elif flags:  # only non-hard signals remain here (missing_pyq/pending/stale/thin)
        status = "needs_action"
    else:
        status = "ready"

    return {
        "status": status,
        "flags": flags,
        "blocker_count": len(hard_blockers),
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
    for r in _batch_rows(sb, "organizations", "id", org_ids, "id, name"):
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
        "pending_review": 0, "stale_review_queue": 0, "thin_mock_bank": 0,
    }
    for r in rows:
        counts[r["status"]] += 1
        for flag in ("pending_review", "stale_review_queue", "thin_mock_bank"):
            if flag in r["flags"]:
                counts[flag] += 1
    return counts
