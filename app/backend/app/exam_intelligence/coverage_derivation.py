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
    model_version: str | None,
    syllabus_mentions: int,
    derivation_version: str,
) -> str:
    """SHA-256 fingerprint over the exact inputs that affect the projection.

    ``snapshot_id`` uniquely identifies an immutable locked snapshot row —
    once locked its scoring values never change in place (a re-score creates
    a new draft/locked row with a new id). So re-deriving from the same
    locked snapshot id + the same syllabus-mention count + the same
    derivation version is guaranteed to reproduce byte-identical output.
    """
    raw = (
        f"snapshot={snapshot_id or 'none'}:"
        f"model={model_version or 'none'}:"
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
    if not topic_ids:
        return zero

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
        model_version = (snapshot or {}).get("model_version")
        fingerprint = _build_fingerprint(
            snapshot_id, model_version, syllabus_mentions, DERIVATION_VERSION
        )

        proposed = _proposed_row(exam_id, exam_phase_id, tid, snapshot, syllabus_mentions, fingerprint)
        if proposed is None:
            no_row += 1
            continue

        existing = existing_by_topic.get(tid)

        if existing is None:
            # No row at this scope/topic yet — safe to insert a fresh
            # derivation-owned draft.
            try:
                sb.table("exam_topic_coverage").insert(proposed).execute()
                written += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "coverage_derivation insert failed",
                    extra={"topic_id": tid, "error": str(exc)},
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
                # `existing` above and this UPDATE is a real race — another
                # actor (a reviewer) could move the row to pending_review/
                # reviewed/locked in between. Constrain the UPDATE itself
                # by id + source_basis + model_version + reviewer_status IN
                # (draft, rejected) so the database, not stale in-memory
                # state, decides whether the write applies. Treat "0 rows
                # affected" as a conflict — the row is no longer
                # derivation-owned/mutable — and fall back to the
                # skip+delta path rather than assuming success.
                patch = {**proposed}
                try:
                    resp = (
                        sb.table("exam_topic_coverage")
                        .update(patch)
                        .eq("id", existing["id"])
                        .eq("source_basis", _EVIDENCE_DERIVED_BASIS)
                        .eq("model_version", existing_model_version)
                        .in_("reviewer_status", list(_MUTABLE_STATUSES))
                        .execute()
                    )
                    affected = resp.data or []
                    if len(affected) == 1:
                        updated += 1
                    else:
                        # Conflict: row moved out of draft/rejected (or was
                        # otherwise mutated) between read and write. Do NOT
                        # proceed as if the update succeeded.
                        logger.warning(
                            "coverage_derivation update CAS conflict — "
                            "row no longer derivation-owned/mutable",
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
    }
