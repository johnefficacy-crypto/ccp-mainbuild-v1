"""Evidence-derived exam-topic coverage projection (J3 PR 4).

Deterministically projects the **latest locked** ``exam_topic_score_snapshots``
row (plus verified ``syllabus_topic_mentions``) into a **draft**
``exam_topic_coverage`` row. This module does not compute evidence scores —
that is the merged, locked responsibility of
``app.exam_intelligence.score_snapshots`` (see also
``docs/architecture/pyq-intelligence-v2.md`` §Scoring contracts, P1: "do not
write directly into locked exam_topic_coverage from an AI job"). This module
is the governed, deterministic **projection** step that closes that gap
without violating it — it is a P1 elaboration of pyq-intelligence-v2.md, not
a re-specification of its scoring logic.

Contract (see ``docs/status/J3-Evidence-Coverage-Scoring-Gate-2026-07-02.md``
Sections B/C/E and ``docs/status/J3-OD-Resolutions-Locked-2026-07-02.md`` §5,
OD-1...OD-6, OD-5a — implement exactly, do not deviate):

- PD-1 evidence-only inputs: locked snapshots + verified syllabus mentions.
- PD-2 determinism + idempotency: fingerprint-guarded, mirrors
  ``score_snapshots.py``'s fingerprint pattern.
- PD-3 draft-only writes: never mutates a reviewed/locked coverage row.
- PD-4 / PD-4a row-ownership: the derivation may write/update a row ONLY
  when it is derivation-owned (``source_basis='evidence_derived'`` and
  ``model_version`` set by this module). Any other ``source_basis`` in ANY
  status is never overwritten.
- PD-4b comparison storage: proposed-vs-current delta lives in the returned
  summary (for audit-log / derivation-metadata storage by the caller) —
  never as a shadow ``exam_topic_coverage`` row.
- PD-5 provenance: ``source_basis='evidence_derived'``, ``model_version``
  set to :data:`DERIVATION_VERSION`; pyq-vs-hybrid detail lives in
  ``metadata.evidence.derivation_basis``, never in ``source_basis``.
- PD-6 single source of evidence numbers: priority/confidence/high-yield are
  copied verbatim from the locked snapshot — never recomputed here.
- OD-2 / §5.1 total ``coverage_depth`` bucket function — see
  :func:`bucket_coverage_depth`.
- OD-3 (Option A, break-the-edge) is implemented in ``score_snapshots.py``,
  not here.
- OD-6 scope: exam-wide (``exam_phase_id is None``) and phase-scoped only.
  Cycle-only derivation is not supported — this module has no
  ``exam_cycle_id`` parameter, so a cycle-only scope cannot even be
  expressed; exactly one explicit scope (exam-wide XOR one phase) is derived
  per invocation.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any

from app.exam_intelligence.score_snapshots import locked_score_snapshots

logger = logging.getLogger("career_copilot.exam_intelligence.coverage_derivation")

DERIVATION_VERSION = "v1.0"  # bump when the projection/bucketing logic changes

_PAGE = 1000  # rows per pagination page
_BATCH = 250  # max items per Supabase IN() filter

# Postgres SQLSTATEs we want to surface loudly (schema drift / missing table)
_LOUD_PG_CODES = {"42703", "42P01"}

# §5.2 conflict-rule vocabulary (post OD-1). Any source_basis NOT in
# _EVIDENCE_DERIVED is either human-authored (skip+delta) or
# model_generated (skip+triage) — this set is exhaustive and MUST be kept in
# sync with the exam_topic_coverage.source_basis CHECK constraint.
_HUMAN_AUTHORED_BASES = {
    "manual",
    "admin_review",
    "official_syllabus",
    "pyq_analysis",
    "hybrid",
}
_MODEL_GENERATED_BASIS = "model_generated"
_EVIDENCE_DERIVED_BASIS = "evidence_derived"

_KNOWN_SOURCE_BASES = _HUMAN_AUTHORED_BASES | {_MODEL_GENERATED_BASIS, _EVIDENCE_DERIVED_BASIS}

# PD-4a ownership: a row is derivation-owned ONLY when source_basis is
# 'evidence_derived' AND model_version is a value THIS derivation code
# recognizes as its own (i.e. a row it previously wrote). Today that is
# exactly DERIVATION_VERSION. A null/missing/future/unrecognized
# model_version on an 'evidence_derived' row must NOT be treated as owned,
# even though source_basis claims 'evidence_derived' — skip+triage instead
# of silently overwriting.
_OWNED_MODEL_VERSIONS = {DERIVATION_VERSION}

# Reviewer statuses the derivation is allowed to recompute/update in place
# (PD-3: draft/rejected only — never pending_review/reviewed/locked).
_MUTABLE_STATUSES = ("draft", "rejected")


class CoverageDerivationError(Exception):
    """Raised only for programmer-error / invariant violations, never for
    ordinary read failures (those are reported via ``read_error`` in the
    result dict, mirroring ``score_snapshots.py``'s fail-closed contract)."""


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
            "coverage_derivation operation failed",
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

    Returns ``None`` if any page read fails (caller must treat this as a
    read error — fail-closed, mirrors ``score_snapshots.py``).
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


def bucket_coverage_depth(
    evidence_count: int,
    syllabus_mentions: int,
    is_high_yield: bool,
) -> str | None:
    """Total ``coverage_depth`` bucket function (resolutions §5.1 / OD-2).

    Every valid ``(evidence_count, syllabus_mentions, is_high_yield)`` input
    maps to exactly one bucket. Returns ``None`` only for the "no row"
    case (``evidence_count == 0 and syllabus_mentions == 0``) — the caller
    must not write a coverage row in that case.

    ::

        (no row)  : evidence_count = 0 AND syllabus_mentions = 0
        mentioned : evidence_count = 0 AND syllabus_mentions >= 1
        light     : evidence_count 1-2
        normal    : evidence_count 3-5
        deep      : evidence_count 6-9
        core      : evidence_count >= 10 AND syllabus_mentions >= 1 AND is_high_yield
        deep      : evidence_count >= 10 AND NOT (syllabus_mentions >= 1 AND is_high_yield)
                    -- fallback: high evidence volume failing any `core`
                    -- predicate is `deep`, never unmatched.
    """
    evidence_count = max(int(evidence_count or 0), 0)
    syllabus_mentions = max(int(syllabus_mentions or 0), 0)

    if evidence_count == 0 and syllabus_mentions == 0:
        return None
    if evidence_count == 0:
        return "mentioned"
    if evidence_count <= 2:
        return "light"
    if evidence_count <= 5:
        return "normal"
    if evidence_count <= 9:
        return "deep"
    # evidence_count >= 10
    if syllabus_mentions >= 1 and is_high_yield:
        return "core"
    return "deep"  # fallback — every evidence_count>=10 input reaches here or `core`


def _build_fingerprint(
    snapshot_id: str | None,
    snapshot_fingerprint: str | None,
    syllabus_mentions: int,
    derivation_version: str,
) -> str:
    """SHA-256 fingerprint over the exact inputs that affect the projection.

    Per the gate contract (docs/status/J3-Evidence-Coverage-Scoring-Gate-
    2026-07-02.md §C), the derivation fingerprint is a function of
    (snapshot_id, the snapshot's OWN input fingerprint, syllabus_mentions,
    DERIVATION_VERSION).

    P1-1 fix (checkpost): this used to substitute the snapshot's
    ``model_version`` for its input fingerprint. ``model_version`` does not
    change when the underlying verified evidence corpus changes (it only
    bumps on a code/formula change), so a re-score of the same model version
    over a *different* verified-evidence corpus was silently treated as
    "unchanged" and the derivation would idempotent-skip a stale draft
    instead of recomputing it. ``snapshot_fingerprint`` (the snapshot's own
    ``input_summary.fingerprint`` from ``score_snapshots.py``) DOES change
    whenever its inputs change, so it is the correct input here.

    ``snapshot_id`` uniquely identifies an immutable locked snapshot row —
    once locked its scoring values never change in place (a re-score creates
    a new draft/locked row with a new id) — but is included defensively
    alongside the fingerprint, not as a substitute for it.
    """
    raw = (
        f"snapshot={snapshot_id or 'none'}:"
        f"snapshot_fp={snapshot_fingerprint or 'none'}:"
        f"mentions={syllabus_mentions}:"
        f"derivation={derivation_version}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _verified_syllabus_mention_counts(
    sb: Any,
    exam_id: str,
    *,
    exam_phase_id: str | None,
) -> dict[str, int] | None:
    """Return ``{topic_id: verified_mention_count}`` for the given scope.

    Scope isolation mirrors ``score_snapshots.py``: exam-wide reads use
    ``exam_phase_id IS NULL``; phase reads use equality. Mentions are
    aggregated across ``exam_cycle_id`` (mentions are not cycle-scoped for
    this derivation — snapshots and coverage themselves are cycle-
    independent per OD-6).

    Returns ``None`` on any read failure (fail-closed).
    """

    def _page(from_n: int, to_n: int) -> list[dict[str, Any]]:
        q = (
            sb.table("syllabus_topic_mentions")
            .select("topic_id")
            .eq("exam_id", exam_id)
            .eq("reviewer_status", "verified")
        )
        if exam_phase_id:
            q = q.eq("exam_phase_id", exam_phase_id)
        else:
            q = q.is_("exam_phase_id", None)
        return q.range(from_n, to_n).execute().data

    rows = _paginate(_page, table="syllabus_topic_mentions", operation="select_verified")
    if rows is None:
        return None

    counts: dict[str, int] = {}
    for r in rows:
        tid = r.get("topic_id")
        if tid:
            counts[tid] = counts.get(tid, 0) + 1
    return counts


def _existing_coverage_rows(
    sb: Any,
    exam_id: str,
    topic_ids: list[str],
    *,
    exam_phase_id: str | None,
) -> list[dict[str, Any]] | None:
    """Return existing ``exam_topic_coverage`` rows at the given exam-wide-or-
    phase scope (``exam_cycle_id IS NULL`` always — this derivation never
    touches cycle-scoped coverage rows). Returns ``None`` on read failure.
    """
    if not topic_ids:
        return []

    rows: list[dict[str, Any]] = []
    for chunk in [topic_ids[i : i + _BATCH] for i in range(0, len(topic_ids), _BATCH)]:

        def _page(from_n: int, to_n: int, c: list[str] = chunk) -> list[dict[str, Any]]:
            q = (
                sb.table("exam_topic_coverage")
                .select(
                    "id, topic_id, exam_id, exam_cycle_id, exam_phase_id, "
                    "source_basis, model_version, reviewer_status, "
                    "exam_priority_score, is_high_yield, confidence_score, "
                    "coverage_depth, metadata"
                )
                .eq("exam_id", exam_id)
                .in_("topic_id", c)
                .is_("exam_cycle_id", None)
            )
            if exam_phase_id:
                q = q.eq("exam_phase_id", exam_phase_id)
            else:
                q = q.is_("exam_phase_id", None)
            return q.range(from_n, to_n).execute().data

        batch = _paginate(_page, table="exam_topic_coverage", operation="select_existing")
        if batch is None:
            return None
        rows.extend(batch)
    return rows


def _proposed_row(
    exam_id: str,
    exam_phase_id: str | None,
    topic_id: str,
    snapshot: dict[str, Any] | None,
    syllabus_mentions: int,
    fingerprint: str,
) -> dict[str, Any] | None:
    """Build the proposed derived-coverage payload for one topic.

    Returns ``None`` when :func:`bucket_coverage_depth` says "no row"
    (evidence_count == 0 and syllabus_mentions == 0).
    """
    evidence_count = int((snapshot or {}).get("evidence_count") or 0)
    is_high_yield = bool((snapshot or {}).get("is_high_yield"))
    depth = bucket_coverage_depth(evidence_count, syllabus_mentions, is_high_yield)
    if depth is None:
        return None

    # P2 fix (checkpost): the gate doc (Section C) defines the two-value
    # enum as `derivation_basis: 'pyq' | 'hybrid'` with the parenthetical
    # "pyq-vs-hybrid detail (evidence-only vs evidence + verified syllabus
    # mention)" — i.e. 'hybrid' is explicitly scoped to BOTH evidence AND a
    # syllabus mention being present together, not "evidence OR syllabus".
    # That definition does not cover the zero-PYQ-evidence,
    # syllabus-mentions-only case (the 'mentioned' bucket), which the §5.1
    # bucket table structurally allows. Rather than silently overload
    # 'hybrid' to also mean "syllabus only", this emits the more honest
    # 'syllabus_only' value and the gate doc is amended (see
    # docs/status/J3-Evidence-Coverage-Scoring-Gate-2026-07-02.md, Section C
    # addendum) to extend the enum to `pyq | hybrid | syllabus_only`.
    derivation_basis = "hybrid" if syllabus_mentions >= 1 and evidence_count > 0 else "pyq"
    if evidence_count == 0 and syllabus_mentions >= 1:
        derivation_basis = "syllabus_only"

    return {
        "exam_id": exam_id,
        "exam_cycle_id": None,
        "exam_phase_id": exam_phase_id,
        "topic_id": topic_id,
        "exam_priority_score": (snapshot or {}).get("exam_priority_score") or 0,
        "is_high_yield": is_high_yield,
        "confidence_score": (snapshot or {}).get("confidence_score") or 0,
        "coverage_depth": depth,
        "source_basis": _EVIDENCE_DERIVED_BASIS,
        "model_version": DERIVATION_VERSION,
        "reviewer_status": "draft",
        "metadata": {
            "evidence": {
                "snapshot_id": (snapshot or {}).get("snapshot_id"),
                "evidence_count": evidence_count,
                "syllabus_mentions": syllabus_mentions,
                "fingerprint": fingerprint,
                "derivation_basis": derivation_basis,
            }
        },
    }


def _existing_fingerprint(row: dict[str, Any]) -> str | None:
    return ((row.get("metadata") or {}).get("evidence") or {}).get("fingerprint")


def _cas_update_owned_row(
    sb: Any,
    row_id: str,
    model_version: str,
    expected_fingerprint: str | None,
    patch: dict[str, Any],
) -> int:
    """Attempt one CAS-guarded UPDATE of a derivation-owned coverage row.

    P1-2 fix (checkpost): the predicate now ALSO requires the row's current
    ``metadata.evidence.fingerprint`` to still equal *expected_fingerprint*
    (the fingerprint this call read the row with), in addition to id +
    source_basis + model_version + reviewer_status IN (draft, rejected).
    Without the fingerprint check, two concurrent derivations of the SAME
    topic from DIFFERENT (competing) locked snapshots both satisfy the
    coarser predicate — whichever UPDATE commits last would win even if it
    were computed from a now-stale snapshot. Requiring the exact fingerprint
    read at select-time means only a caller that observed the CURRENT row
    state may write it; a competing writer that already committed changes
    the fingerprint out from under a stale caller, forcing a 0-row (CAS
    conflict) response instead of a silent overwrite.

    Returns the number of rows the UPDATE actually affected (0 or 1).
    """
    q = (
        sb.table("exam_topic_coverage")
        .update(patch)
        .eq("id", row_id)
        .eq("source_basis", _EVIDENCE_DERIVED_BASIS)
        .eq("model_version", model_version)
        .in_("reviewer_status", list(_MUTABLE_STATUSES))
    )
    if expected_fingerprint is None:
        q = q.is_("metadata->evidence->>fingerprint", None)
    else:
        q = q.eq("metadata->evidence->>fingerprint", expected_fingerprint)
    resp = q.execute()
    return len(resp.data or [])


def _delta(existing: dict[str, Any], proposed: dict[str, Any]) -> dict[str, Any]:
    """Proposed-vs-current comparison, for audit/derivation metadata ONLY
    (PD-4b / OD-5) — never written as a shadow coverage row."""
    fields = ("exam_priority_score", "is_high_yield", "confidence_score", "coverage_depth")
    return {
        "topic_id": existing.get("topic_id"),
        "existing_row_id": existing.get("id"),
        "existing_source_basis": existing.get("source_basis"),
        "existing_reviewer_status": existing.get("reviewer_status"),
        "changed_fields": {
            f: {"current": existing.get(f), "proposed": proposed.get(f)}
            for f in fields
            if existing.get(f) != proposed.get(f)
        },
    }


def _reconcile_stale_owned_rows(
    sb: Any,
    exam_id: str,
    exam_phase_id: str | None,
    current_topic_ids: set[str],
) -> tuple[int, list[dict[str, Any]]] | None:
    """P1-3 fix (checkpost): flag derivation-owned draft/rejected rows whose
    topic has fallen OUT of the current evidence+syllabus input set.

    ``derive_topic_coverage`` builds its topic universe from CURRENT locked
    snapshots + CURRENT verified syllabus mentions only (PD-1). If a topic
    previously had an ``evidence_derived`` draft/rejected row and its last
    verified mention is revoked, or its last locked snapshot is unlocked/
    removed, that topic silently drops out of ``topic_ids`` — the stale row
    is never revisited by the main loop and would otherwise sit forever as a
    draft an operator could mistakenly promote, even though the §5.1
    zero-evidence+zero-mentions bucket contract says "no row" for that
    topic.

    Per PD-4b / "no shadow rows" and the "never touch human-authored or
    reviewed/locked rows" invariant, this function is scoped as narrowly as
    the main loop's ownership check: ONLY rows with
    ``source_basis='evidence_derived'`` AND a recognized (owned)
    ``model_version`` AND ``reviewer_status`` in (draft, rejected) are
    candidates. Chosen behavior (documented per the task's option (b)):
    flag via ``metadata.stale=true`` for operator triage rather than delete
    — deletion is irreversible and this derivation module otherwise never
    deletes rows (mirrors the existing model_generated "skip + flag for
    triage" pattern already used elsewhere in this module), so triage-flag
    is the consistent, less-destructive choice. Reviewed/locked
    `evidence_derived` rows and rows of any other `source_basis` are never
    touched here, matching the main loop's ownership rules.

    Returns ``(reconciled_count, topic_ids)`` or ``None`` on a read failure
    (fail-closed — caller should treat this the same as any other read
    error).
    """

    def _page(from_n: int, to_n: int) -> list[dict[str, Any]]:
        q = (
            sb.table("exam_topic_coverage")
            .select(
                "id, topic_id, exam_id, exam_cycle_id, exam_phase_id, "
                "source_basis, model_version, reviewer_status, metadata"
            )
            .eq("exam_id", exam_id)
            .eq("source_basis", _EVIDENCE_DERIVED_BASIS)
            .in_("reviewer_status", list(_MUTABLE_STATUSES))
            .is_("exam_cycle_id", None)
        )
        if exam_phase_id:
            q = q.eq("exam_phase_id", exam_phase_id)
        else:
            q = q.is_("exam_phase_id", None)
        return q.range(from_n, to_n).execute().data

    rows = _paginate(_page, table="exam_topic_coverage", operation="select_owned_for_reconcile")
    if rows is None:
        return None

    reconciled = 0
    flagged: list[dict[str, Any]] = []
    for r in rows:
        if r.get("model_version") not in _OWNED_MODEL_VERSIONS:
            continue
        tid = r.get("topic_id")
        if not tid or tid in current_topic_ids:
            continue
        meta = r.get("metadata") if isinstance(r.get("metadata"), dict) else {}
        if meta.get("stale") is True:
            continue  # already flagged — idempotent, avoid redundant writes
        patch = {"metadata": {**meta, "stale": True}}
        try:
            sb.table("exam_topic_coverage").update(patch).eq("id", r["id"]).execute()
            reconciled += 1
            flagged.append({"topic_id": tid, "row_id": r.get("id")})
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "coverage_derivation stale-reconcile update failed",
                extra={"topic_id": tid, "row_id": r.get("id"), "error": str(exc)},
            )
    return reconciled, flagged


def derive_topic_coverage(
    sb: Any,
    exam_id: str,
    *,
    exam_phase_id: str | None = None,
) -> dict[str, Any]:
    """Derive/update ``draft`` ``exam_topic_coverage`` rows for *exam_id*.

    Reads the **latest locked** ``exam_topic_score_snapshots`` row per topic
    (via ``score_snapshots.locked_score_snapshots``) plus verified
    ``syllabus_topic_mentions`` counts, and projects them into
    ``exam_topic_coverage`` rows with ``source_basis='evidence_derived'``
    per the deterministic bucket function (§5.1) and conflict rules (§5.2).

    Exactly one explicit scope per invocation: *exam_phase_id* is ``None``
    for exam-wide derivation, or a specific phase id for phase-scoped
    derivation. Cycle-only derivation cannot be expressed by this signature
    (OD-6) — there is no ``exam_cycle_id`` parameter.

    Returns a summary dict::

        {
            "written": int,           # new evidence_derived draft rows inserted
            "updated": int,           # existing derivation-owned rows recomputed
            "skipped": int,           # rows left untouched (delta recorded)
            "triaged": int,           # model_generated rows flagged for operator triage
            "no_row": int,            # topics with zero evidence + zero mentions
            "errors": int,
            "total_topics": int,
            "read_error": bool,
            "invalid_scope": bool,
            "deltas": list[dict],     # proposed-vs-current comparisons (PD-4b)
            "triage": list[dict],     # model_generated rows flagged (topic_id, row_id)
            "stale_reconciled": int,  # P1-3: derivation-owned rows flagged stale=true
            "stale_rows": list[dict],  # (topic_id, row_id) flagged this run
        }

    ``read_error=True`` means a critical DB read failed; the caller (admin
    endpoint) must treat this as a compute failure — never a partial write.
    """
    zero: dict[str, Any] = {
        "written": 0,
        "updated": 0,
        "skipped": 0,
        "triaged": 0,
        "no_row": 0,
        "errors": 0,
        "total_topics": 0,
        "read_error": False,
        "invalid_scope": False,
        "deltas": [],
        "triage": [],
        "stale_reconciled": 0,
        "stale_rows": [],
    }
    if not exam_id:
        return zero

    # ── 1. Validate phase belongs to exam (mirrors score_snapshots.py) ────
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
                "coverage_derivation: exam_phase_id %r does not belong to exam %r",
                exam_phase_id,
                exam_id,
            )
            return {**zero, "invalid_scope": True}

    # ── 2. Latest locked snapshots (PD-1, PD-6 — the ONLY evidence-number
    #      authority; fail-closed on read error) ───────────────────────────
    snapshots = locked_score_snapshots(sb, exam_id, exam_phase_id=exam_phase_id)
    if snapshots is None:
        return {**zero, "read_error": True}
    snapshot_by_topic: dict[str, dict[str, Any]] = {
        s["topic_id"]: s for s in snapshots if s.get("topic_id")
    }

    # ── 3. Verified syllabus mentions (PD-1) ───────────────────────────────
    mention_counts = _verified_syllabus_mention_counts(sb, exam_id, exam_phase_id=exam_phase_id)
    if mention_counts is None:
        return {**zero, "read_error": True}

    topic_ids = sorted(set(snapshot_by_topic.keys()) | set(mention_counts.keys()))
    # NOTE (P1-3 fix): do NOT early-return here when topic_ids is empty. A
    # scope can legitimately go from "has current evidence/mentions" to
    # "none at all" (every snapshot unlocked, every mention un-verified) —
    # that is exactly the case stale reconciliation below must still catch,
    # so an empty current-input set must still fall through to the
    # reconciliation pass rather than short-circuiting before it.

    # ── 4. Existing coverage rows at this exact scope (PD-4a) ──────────────
    existing_rows = _existing_coverage_rows(sb, exam_id, topic_ids, exam_phase_id=exam_phase_id)
    if existing_rows is None:
        return {**zero, "read_error": True}
    existing_by_topic: dict[str, dict[str, Any]] = {
        r["topic_id"]: r for r in existing_rows if r.get("topic_id")
    }

    written = updated = skipped = triaged = no_row = errors = 0
    deltas: list[dict[str, Any]] = []
    triage: list[dict[str, Any]] = []

    for tid in topic_ids:
        snapshot = snapshot_by_topic.get(tid)
        syllabus_mentions = mention_counts.get(tid, 0)
        snapshot_id = (snapshot or {}).get("snapshot_id")
        # P1-1 fix: use the snapshot's OWN input fingerprint, not its
        # model_version — see _build_fingerprint docstring.
        snapshot_fingerprint = (snapshot or {}).get("fingerprint")
        fingerprint = _build_fingerprint(
            snapshot_id, snapshot_fingerprint, syllabus_mentions, DERIVATION_VERSION
        )

        proposed = _proposed_row(exam_id, exam_phase_id, tid, snapshot, syllabus_mentions, fingerprint)
        if proposed is None:
            no_row += 1
            continue

        existing = existing_by_topic.get(tid)

        if existing is None:
            # No row at this scope/topic yet — safe to insert a fresh
            # derivation-owned draft.
            #
            # P1-2 fix (checkpost): two concurrent "no existing row" reads
            # (e.g. two overlapping derivation runs) can both reach this
            # branch and both attempt an INSERT; the exam-wide/scope unique
            # index (OD-5a) means only one commits and the other raises a
            # unique-violation. Previously that loser was just counted as a
            # generic error with no attempt to determine whether the winner
            # was actually a newer/consistent computation. Now: on a unique-
            # violation, re-read the row the winner created. If it is
            # derivation-owned (evidence_derived + a recognized
            # model_version), this run is cleanly superseded by a concurrent
            # winner computing the same projection — treat as an idempotent
            # skip, not an error. Any other outcome (e.g. the winner is not
            # derivation-owned, which should be impossible given the
            # ownership-scoped insert path but is treated fail-closed
            # anyway) is still counted as an error.
            try:
                sb.table("exam_topic_coverage").insert(proposed).execute()
                written += 1
            except Exception as exc:  # noqa: BLE001
                code = getattr(exc, "code", None) or getattr(exc, "pgcode", None)
                is_unique_violation = code == "23505" or "23505" in str(exc) or "duplicate key" in str(exc).lower()
                if is_unique_violation:
                    winner_rows = _existing_coverage_rows(
                        sb, exam_id, [tid], exam_phase_id=exam_phase_id
                    )
                    winner = (winner_rows or [{}])[0] if winner_rows else None
                    if (
                        winner
                        and winner.get("source_basis") == _EVIDENCE_DERIVED_BASIS
                        and winner.get("model_version") in _OWNED_MODEL_VERSIONS
                    ):
                        logger.info(
                            "coverage_derivation insert superseded by a "
                            "concurrent derivation-owned insert — skipping cleanly",
                            extra={"topic_id": tid},
                        )
                        skipped += 1
                        deltas.append(_delta(winner, proposed))
                        continue
                logger.warning(
                    "coverage_derivation insert failed",
                    extra={"topic_id": tid, "error": str(exc), "error_code": code},
                )
                errors += 1
            continue

        basis = existing.get("source_basis")
        status = existing.get("reviewer_status")

        # §5.2 conflict matrix — complete over the full source_basis
        # vocabulary. Any row not derivation-owned is NEVER overwritten.
        if basis in _HUMAN_AUTHORED_BASES:
            skipped += 1
            deltas.append(_delta(existing, proposed))
            continue

        if basis == _MODEL_GENERATED_BASIS:
            triaged += 1
            deltas.append(_delta(existing, proposed))
            triage.append({"topic_id": tid, "row_id": existing.get("id")})
            continue

        if basis == _EVIDENCE_DERIVED_BASIS:
            existing_model_version = existing.get("model_version")
            if existing_model_version not in _OWNED_MODEL_VERSIONS:
                # PD-4a: source_basis alone does not establish ownership.
                # A null/missing/unrecognized model_version on an
                # 'evidence_derived' row means this row was not written by
                # (a version of) this derivation — never overwrite it.
                # Treat like model_generated: skip + flag for operator
                # triage rather than silently clobbering it.
                triaged += 1
                deltas.append(_delta(existing, proposed))
                triage.append({"topic_id": tid, "row_id": existing.get("id")})
                continue
            if status in _MUTABLE_STATUSES:
                # Idempotency (PD-2): if the existing derivation-owned row
                # already carries this exact fingerprint AND is already in
                # `draft`, re-running writes nothing new.
                existing_fp = ((existing.get("metadata") or {}).get("evidence") or {}).get(
                    "fingerprint"
                )
                if status == "draft" and existing_fp == fingerprint:
                    skipped += 1
                    continue
                # Derivation-owned + re-derivable: recompute/update in
                # place. `rejected` returns to `draft` with fresh inputs.
                #
                # CAS guard: the read-then-write gap between fetching
                # `existing` above and this UPDATE is a real race. Two
                # DIFFERENT hazards close here (P1-2 / checkpost):
                #  (a) a reviewer moves the row to pending_review/reviewed/
                #      locked in between — the reviewer_status IN
                #      (draft, rejected) predicate catches this;
                #  (b) a CONCURRENT derivation run for the SAME topic,
                #      computed from a DIFFERENT (newer or older) locked
                #      snapshot, commits its own UPDATE in between — the
                #      coarser predicate alone (id + source_basis +
                #      model_version + status) does NOT catch this, because
                #      both runs' updates satisfy it identically. The
                #      fingerprint predicate in `_cas_update_owned_row`
                #      closes that gap: only a caller whose in-memory
                #      `existing` still matches the row's CURRENT fingerprint
                #      may write it.
                #
                # On a 0-row CAS conflict, retry exactly once (re-issuing the
                # same CAS predicate) to absorb a transient conflict; if the
                # row still doesn't match after the retry, this run's inputs
                # are stale relative to what's now in the database — report
                # a delta/conflict and skip rather than silently applying a
                # stale write.
                patch = {**proposed}
                try:
                    affected = _cas_update_owned_row(
                        sb, existing["id"], existing_model_version, existing_fp, patch
                    )
                    if affected == 0:
                        affected = _cas_update_owned_row(
                            sb, existing["id"], existing_model_version, existing_fp, patch
                        )
                    if affected == 1:
                        updated += 1
                    else:
                        # Conflict survived the retry: row moved out of
                        # draft/rejected, or a competing derivation already
                        # wrote a different fingerprint, between read and
                        # write. Do NOT proceed as if the update succeeded.
                        logger.warning(
                            "coverage_derivation update CAS conflict (after retry) — "
                            "row no longer matches the fingerprint/status this run read",
                            extra={"topic_id": tid, "row_id": existing.get("id")},
                        )
                        skipped += 1
                        deltas.append(_delta(existing, proposed))
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "coverage_derivation update failed",
                        extra={"topic_id": tid, "row_id": existing.get("id"), "error": str(exc)},
                    )
                    errors += 1
                continue
            if status == "pending_review":
                skipped += 1
                deltas.append(_delta(existing, proposed))
                continue
            if status in ("reviewed", "locked"):
                # Leave unchanged — explicit operator replacement workflow
                # required (PD-3 / PD-4).
                skipped += 1
                deltas.append(_delta(existing, proposed))
                continue
            # Unknown status on an evidence_derived row: fail closed by
            # treating as skip+delta rather than guessing a mutation.
            skipped += 1
            deltas.append(_delta(existing, proposed))
            continue

        # Unknown/legacy source_basis value not in the documented
        # vocabulary: treat conservatively as human-authored (skip+delta)
        # rather than risk overwriting unknown provenance.
        skipped += 1
        deltas.append(_delta(existing, proposed))

    # ── 5. Stale derivation-owned row reconciliation (P1-3 / PD-4b) ────────
    # Runs over the FULL current topic_ids set (which may be empty — see the
    # note at step 3 above) so a topic whose evidence/mentions disappeared
    # entirely this run is still caught.
    reconcile_result = _reconcile_stale_owned_rows(sb, exam_id, exam_phase_id, set(topic_ids))
    if reconcile_result is None:
        # The main derivation pass above already committed real writes —
        # reporting `read_error=True` here would misrepresent a successful
        # (partial) run as if nothing happened. Log loudly and report zero
        # reconciliation for this run instead; the next invocation will
        # retry reconciliation from scratch (it is independently idempotent
        # per-row via the `metadata.stale` check).
        logger.warning(
            "coverage_derivation: stale-row reconciliation read failed; "
            "primary derivation results below are still valid",
            extra={"exam_id": exam_id, "exam_phase_id": exam_phase_id},
        )
        stale_reconciled, stale_rows = 0, []
    else:
        stale_reconciled, stale_rows = reconcile_result

    return {
        "written": written,
        "updated": updated,
        "skipped": skipped,
        "triaged": triaged,
        "no_row": no_row,
        "errors": errors,
        "total_topics": len(topic_ids),
        "read_error": False,
        "invalid_scope": False,
        "deltas": deltas,
        "triage": triage,
        "stale_reconciled": stale_reconciled,
        "stale_rows": stale_rows,
    }
