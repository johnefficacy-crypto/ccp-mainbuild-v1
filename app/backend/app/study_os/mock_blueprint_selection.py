"""Section-wise question SELECTION + relaxation ladder for generated mocks (A-PR2).

NON-MUTATING. This service CONSUMES the A-PR1 blueprint envelope/payload
(``mock_blueprint.build_blueprint_payload``) and fills the two slots A-PR1 left
empty: ``selector_snapshot`` and ``question_ids``. It writes NOTHING — no DB
write, no ``mock_generated_blueprints`` insert (A-PR3), no attempt start, no
personalization (A-PR5), no exposure tracking (A-PR4), no content seeding.

WHAT IT DOES
  1. For each AUTHORED section in the A-PR1 envelope, builds the eligible pool
     using the EXACT readiness base-pool predicate from
     ``diagnostics.selectable_mcq_depth`` — reviewer_status in the caller's
     selectable set, MCQ only (``_SELECTABLE_QUESTION_TYPES``; 'msq'/'integer'
     are NOT generated-selectable while scoring is single-option — §4a / D1),
     is_current/is_current_based EXCLUDED, e2e_fixture excluded (#683) / NULL
     provenance retained, not-expired — scoped to the section's subject_id. The
     selection pool is therefore EQUAL to the pool the A-PR1 verdict was computed
     over (pinned by the pool-match guard test).
  2. Fills up to the section's AUTHORED ``question_count`` (the structural target,
     NOT ``min_per_section`` which is the readiness threshold), reusing the
     difficulty-apportionment (largest-remainder) + thin-bucket backfill BEHAVIOR
     from ``mock_engine._criteria_difficulty_targets``.
  3. Applies the relaxation ladder ONLY within the structural envelope, in this
     fixed order: exposure-cooldown → personalization → source-mix →
     difficulty-mix. Exposure (A-PR4) and personalization (A-PR5) do not exist
     yet, so they are explicit INERT no-op rungs that slot in later without
     reordering — they are not faked. Source-mix is enforced ONLY when the
     envelope section carries mix targets (Wave 5); absent targets → no source-mix
     enforcement. Section count, timing, marking, section lock and interface mode
     are NEVER relaxed.
  4. Deterministic ordering (stable id sort, reused from the selector), so the
     same envelope yields the same ``question_ids`` across calls — no unseeded
     randomness.
  5. Populates ``selector_snapshot`` honestly (per-section eligible-pool count,
     selected count, shortfall, which rungs relaxed, source_basis) and
     ``question_ids``. When a section's eligible pool < ``question_count`` it
     returns a structured shortfall and PROPAGATES thin_bank — it never silently
     under-fills and reports ready.

PARKED — TEMPLATE-PATH POOL DIVERGENCE (do NOT change here): the template attempt
path ``mock_engine._select_criteria_question_ids`` / ``select_questions_for_template``
build a LOOSER pool than readiness — statuses ['verified','published','live'],
NO question_type filter and NO is_current exclusion. A-PR2 deliberately does NOT
reuse that pool (it would diverge from the verdict). Aligning the template path is
parked for a later PR; this module leaves it byte-identical to main and only
reuses its difficulty-apportionment LOGIC.
"""
from __future__ import annotations

import logging

from app.exam_intelligence.diagnostics import (
    _E2E_FIXTURE_SOURCE_TYPE,
    _SELECTABLE_QUESTION_TYPES,
    _fetch_all,
    _not_expired,
    selectable_mcq_depth,  # re-exported for callers/tests that pin pool ≡ readiness
)
from app.study_os.mock_blueprint import build_blueprint_payload
# Reuse the apportionment LOGIC only — NOT the looser criteria pool (see PARKED).
from app.study_os.mock_engine import _criteria_difficulty_targets

logger = logging.getLogger("career_copilot.study_os.mock_blueprint_selection")

# Relaxation ladder, fixed order. Each rung may RELAX a soft constraint to reach
# the structural question_count; the hard envelope (count/timing/marking/lock/
# interface) is never relaxed. Exposure + personalization are inert until A-PR4/5.
_LADDER = ("exposure_cooldown", "personalization", "source_mix", "difficulty_mix")

# Constraints the ladder must NEVER relax (recorded in selector_snapshot so the
# guarantee is auditable, not just implied).
_NON_RELAXABLE = (
    "section_count",
    "timing",
    "negative_marking",
    "section_lock",
    "interface_mode",
)

_POOL_PREDICATE_NOTE = (
    "diagnostics.selectable_mcq_depth base pool: reviewer_status in selectable, "
    "MCQ only (msq/integer not generated-selectable while scoring is "
    "single-option), is_current/is_current_based excluded, e2e_fixture excluded "
    "/ NULL provenance retained, not-expired; scoped by section subject_id. "
    "Equals the pool the readiness verdict was computed over."
)

# Scope hierarchy for policy resolution: topic > subject > phase > exam.
# The most specific active policy that matches wins; ties broken by creation order.
_POLICY_SCOPE_PRIORITY = ("topic_id", "subject_id", "exam_phase_id", "exam_id")


def _resolve_source_mix_policy(
    sb,
    *,
    exam_id: str,
    exam_phase_id: str | None = None,
    subject_id: str | None = None,
    topic_id: str | None = None,
) -> tuple[dict | None, dict | None]:
    """Return the most-specific active source-mix policy or (None, None).

    Queries ``mock_source_mix_policies`` with the scope hierarchy:
    topic > subject > phase > exam.  Returns a 2-tuple:
    - ``mix``: ``{source_kind: target_ratio}`` suitable for ``_apportion_order``
    - ``constraints``: ``{source_kind: {"min": float, "max": float, "fallback": str}}``
      for enforcement in ``_select_section`` after selection

    Both are None when no policy applies. ``topic_id`` must be provided by the
    caller for topic-scoped policies to apply; section-level callers pass None
    and only subject/phase/exam-scoped policies match.
    """
    try:
        rows = (
            sb.table("mock_source_mix_policies")
            .select(
                "id, exam_id, exam_phase_id, subject_id, topic_id, "
                "source_kind, target_ratio, minimum_ratio, maximum_ratio, "
                "fallback_policy, is_active"
            )
            .eq("exam_id", exam_id)
            .eq("is_active", True)
            .execute()
            .data
        ) or []
    except Exception:
        # Table may not exist in older environments — fail open (no policy).
        logger.warning("mock_source_mix_policies query failed; skipping policy resolution")
        return None, None

    if not rows:
        return None, None

    # Filter to rows that match the current scope at each level.
    def _scope_matches(row: dict) -> bool:
        if row.get("topic_id") and row["topic_id"] != topic_id:
            return False
        if row.get("subject_id") and row["subject_id"] != subject_id:
            return False
        if row.get("exam_phase_id") and row["exam_phase_id"] != exam_phase_id:
            return False
        return True

    candidates = [r for r in rows if _scope_matches(r)]
    if not candidates:
        return None, None

    # Pick the most-specific scope by priority: topic → subject → phase → exam.
    def _specificity(row: dict) -> int:
        for priority, col in enumerate(_POLICY_SCOPE_PRIORITY):
            if row.get(col):
                return -priority  # negative so most-specific (index 0) sorts first
        return -len(_POLICY_SCOPE_PRIORITY)

    candidates.sort(key=_specificity)
    best_specificity = _specificity(candidates[0])
    winning_rows = [r for r in candidates if _specificity(r) == best_specificity]

    # Collapse winning rows into target-ratio and constraints dicts.
    # Duplicate source_kind entries at the same scope level are a configuration
    # error — log a warning and use the first-encountered row only.
    mix: dict[str, float] = {}
    constraints: dict[str, dict] = {}
    for r in winning_rows:
        sk = r.get("source_kind")
        if not sk:
            continue
        if sk in mix:
            logger.warning(
                "duplicate source_kind=%r at same policy scope "
                "(exam=%s phase=%s subject=%s topic=%s); "
                "using first-encountered row, ignoring id=%s",
                sk, exam_id, exam_phase_id, subject_id, topic_id, r.get("id"),
            )
            continue
        mix[sk] = float(r.get("target_ratio") or 0)
        constraints[sk] = {
            "min": float(r.get("minimum_ratio") or 0),
            "max": float(r.get("maximum_ratio") or 1),
            "fallback": r.get("fallback_policy") or "relax_to_available",
        }

    if not mix:
        return None, None
    return mix, constraints


def _exam_base_pool(sb, *, exam_id: str, selectable_statuses, now_iso: str) -> list[dict]:
    """Eligible BASE pool for the exam, matching selectable_mcq_depth EXACTLY.

    Fetched once for the exam (the bank has no phase column) and partitioned by
    subject_id per section downstream. Mirrors the diagnostic predicate term for
    term so selection ≡ readiness; deterministically ordered by id.
    """
    statuses = list(selectable_statuses or [])
    if not statuses:
        return []
    rows = _fetch_all(
        lambda: sb.table("mock_question_bank")
        .select(
            "id, exam_id, subject_id, topic_id, difficulty, question_type, "
            "reviewer_status, is_current, is_current_based, valid_until, "
            "source_type, source_kind, pyq_question_id"
        )
        .eq("exam_id", exam_id)
        .in_("reviewer_status", statuses)
        .in_("question_type", list(_SELECTABLE_QUESTION_TYPES))
        .or_(f"source_type.is.null,source_type.neq.{_E2E_FIXTURE_SOURCE_TYPE}")
    )

    # Active-lineage guard: pyq-derived questions are only selectable when a
    # corresponding active projection exists. The invalidation trigger already
    # downgrades reviewer_status to 'draft', but this Python-layer check is
    # belt-and-suspenders against trigger failures or manual status overrides.
    pyq_rows = [r for r in rows if r.get("pyq_question_id")]
    active_mock_ids: set[str] = set()
    if pyq_rows:
        try:
            proj_rows = (
                sb.table("pyq_mock_question_projections")
                .select("mock_question_id")
                .eq("sync_status", "active")
                .execute()
                .data
            ) or []
            active_mock_ids = {p["mock_question_id"] for p in proj_rows}
        except Exception:
            logger.warning(
                "pyq_mock_question_projections query failed; "
                "excluding all pyq-derived questions from pool (fail-closed)"
            )

    pool = [
        r
        for r in rows
        if _not_expired(r.get("valid_until"), now_iso)
        # is_current / is_current_based are segmented OUT of the base pool by the
        # diagnostic; the base mock must not draw time-bound items.
        and not (bool(r.get("is_current")) or bool(r.get("is_current_based")))
        # Active-lineage guard: skip pyq questions with no active projection.
        and (not r.get("pyq_question_id") or r.get("id") in active_mock_ids)
    ]
    pool.sort(key=lambda r: str(r.get("id")))  # stable, unseeded ordering
    return pool


def _apportion_order(rows: list[dict], target: int, mix: dict, key: str, *, default=None):
    """Order ``rows`` so a ``mix`` over ``key`` is front-loaded, then backfilled.

    Reuses ``_criteria_difficulty_targets`` (largest-remainder rounding) for the
    per-bucket targets and the thin-bucket backfill pattern from
    ``_select_criteria_question_ids`` — same LOGIC, applied to the readiness pool.
    Returns ``(ordered_rows, relaxed)`` where ``relaxed`` is True when a bucket
    was too thin and the deficit had to be drawn from other buckets.
    """
    buckets: dict = {}
    for r in rows:
        bk = r.get(key)
        if bk is None and default is not None:
            bk = default
        buckets.setdefault(bk, []).append(r)
    chosen: list[dict] = []
    used: set = set()
    for bucket, t in _criteria_difficulty_targets(mix, target).items():
        for r in buckets.get(bucket, [])[:t]:
            chosen.append(r)
            used.add(r["id"])
    relaxed = False
    if len(chosen) < target:
        for r in rows:  # backfill from the rest of the eligible pool (in id order)
            if r["id"] in used:
                continue
            chosen.append(r)
            used.add(r["id"])
            relaxed = True
            if len(chosen) >= target:
                break
    # Append any still-unused rows so ordering is total + deterministic.
    for r in rows:
        if r["id"] not in used:
            chosen.append(r)
            used.add(r["id"])
    return chosen, relaxed


def _select_section(
    pool: list[dict],
    target: int,
    *,
    source_mix: dict | None,
    source_mix_constraints: dict | None = None,
    difficulty_mix: dict | None,
):
    """Run the relaxation ladder over one section's eligible pool.

    Returns ``(question_ids, rungs)``. ``rungs`` lists every ladder rung in fixed
    order with its status + whether it relaxed — so the snapshot reflects exactly
    what happened, including the inert A-PR4/A-PR5 rungs.

    ``source_mix_constraints`` is ``{source_kind: {"min": float, "max": float,
    "fallback": str}}`` from ``_resolve_source_mix_policy``. When provided,
    minimum_ratio is enforced after apportionment: if the selected proportion of
    a source_kind is below its minimum and fallback_policy is 'block', the
    section returns no questions and a blocking rung status.
    """
    rungs: list[dict] = [
        {"rung": "exposure_cooldown", "status": "inert_a_pr4_not_implemented", "relaxed": False},
        {"rung": "personalization", "status": "inert_a_pr5_not_implemented", "relaxed": False},
    ]

    if target <= 0:
        rungs.append({"rung": "source_mix", "status": "skipped_zero_target", "relaxed": False})
        rungs.append({"rung": "difficulty_mix", "status": "skipped_zero_target", "relaxed": False})
        return [], rungs

    candidates = list(pool)  # already deterministically ordered by id

    # ── source-mix rung — only when the envelope carries mix targets (Wave 5) ──
    if source_mix:
        candidates, src_relaxed = _apportion_order(candidates, target, source_mix, "source_kind")
        rungs.append({"rung": "source_mix", "status": "applied", "relaxed": src_relaxed})
    else:
        rungs.append({"rung": "source_mix", "status": "not_applicable_no_targets", "relaxed": False})

    # ── difficulty-mix rung — apportion when configured, else straight fill ──
    if difficulty_mix:
        ordered, diff_relaxed = _apportion_order(
            candidates, target, difficulty_mix, "difficulty", default="medium"
        )
        chosen_ids = [r["id"] for r in ordered[:target]]
        rungs.append({"rung": "difficulty_mix", "status": "applied", "relaxed": diff_relaxed})
    else:
        chosen_ids = [r["id"] for r in candidates[:target]]
        rungs.append({"rung": "difficulty_mix", "status": "applied_no_mix", "relaxed": False})

    # ── min/max constraint enforcement ────────────────────────────────────────
    if source_mix_constraints and chosen_ids and target > 0:
        chosen_set = set(chosen_ids)
        chosen_rows = [r for r in pool if r["id"] in chosen_set]
        n = len(chosen_rows)
        for sk, c in source_mix_constraints.items():
            sk_count = sum(1 for r in chosen_rows if (r.get("source_kind") or r.get("source_type")) == sk)
            actual_ratio = sk_count / n if n > 0 else 0.0
            min_ratio = c.get("min", 0.0)
            max_ratio = c.get("max", 1.0)
            fallback = c.get("fallback", "relax_to_available")
            if actual_ratio < min_ratio:
                if fallback == "block":
                    logger.warning(
                        "source_mix minimum_ratio constraint blocked selection: "
                        "source_kind=%r actual=%.3f min=%.3f target=%d",
                        sk, actual_ratio, min_ratio, target,
                    )
                    rungs.append({
                        "rung": "source_mix_min_constraint",
                        "status": "blocked_min_ratio_unmet",
                        "source_kind": sk,
                        "actual_ratio": round(actual_ratio, 4),
                        "minimum_ratio": min_ratio,
                        "relaxed": False,
                    })
                    return [], rungs
                else:
                    logger.warning(
                        "source_mix minimum_ratio not met but fallback=relax_to_available: "
                        "source_kind=%r actual=%.3f min=%.3f; proceeding with available",
                        sk, actual_ratio, min_ratio,
                    )
            if actual_ratio > max_ratio:
                logger.warning(
                    "source_mix maximum_ratio exceeded: "
                    "source_kind=%r actual=%.3f max=%.3f",
                    sk, actual_ratio, max_ratio,
                )

    return chosen_ids, rungs


def build_blueprint_with_selection(
    sb,
    *,
    exam_id: str,
    exam_phase_id: str,
    user_id: str,
    source: str = "exam_realistic",
    selectable_statuses,
    verified_status,
    min_per_section,
    min_locked_coverage,
) -> dict:
    """A-PR1 envelope + A-PR2 section-wise selection, non-mutating.

    Builds the A-PR1 payload (envelope + computed readiness verdict), then for
    every authored section selects question ids from the readiness base pool and
    fills ``selector_snapshot`` + ``question_ids``. Threshold/vocabulary inputs
    are forwarded to A-PR1 unchanged (no defaults baked here — A-PR1 hard-validates
    them). Returns the enriched payload; nothing is written.

    Outcome handling: a section whose eligible pool < its authored question_count
    yields a structured selection shortfall and downgrades a ready phase to
    thin_bank — selection never under-fills and still reports ready. thin_bank /
    blocked outcomes from A-PR1 are preserved.
    """
    from datetime import datetime, timezone

    # A-PR1 builds the envelope + verdict and hard-validates the readiness inputs.
    payload = build_blueprint_payload(
        sb,
        exam_id=exam_id,
        exam_phase_id=exam_phase_id,
        user_id=user_id,
        source=source,
        selectable_statuses=selectable_statuses,
        verified_status=verified_status,
        min_per_section=min_per_section,
        min_locked_coverage=min_locked_coverage,
    )

    sections = payload.get("section_snapshot") or []
    now_iso = datetime.now(timezone.utc).isoformat()

    selector_sections: list[dict] = []
    all_question_ids: list[str] = []
    any_selection_shortfall = False

    # No authored sections (blocked / no_sections): leave selector empty, keep
    # A-PR1's blocked semantics intact.
    base_pool = (
        _exam_base_pool(sb, exam_id=exam_id, selectable_statuses=selectable_statuses, now_iso=now_iso)
        if sections
        else []
    )

    for sec in sections:
        subject_id = sec.get("subject_id")
        target_raw = sec.get("question_count")
        target = int(target_raw) if target_raw not in (None, "") else 0

        eligible = [r for r in base_pool if r.get("subject_id") == subject_id]

        # Resolve source-mix: envelope wins if explicitly set, else DB policy.
        # topic_id is None here because sections are subject-scoped and may span
        # multiple topics; topic-level policies must be resolved at topic granularity
        # by callers that have a single topic_id in scope.
        envelope_mix = sec.get("source_mix")
        if envelope_mix:
            resolved_mix = envelope_mix
            resolved_constraints = None  # envelope carries target ratios only
            mix_source = "envelope"
        else:
            resolved_mix, resolved_constraints = _resolve_source_mix_policy(
                sb,
                exam_id=exam_id,
                exam_phase_id=exam_phase_id,
                subject_id=subject_id,
                topic_id=None,
            )
            mix_source = "db_policy" if resolved_mix else "none"

        chosen_ids, rungs = _select_section(
            eligible,
            target,
            source_mix=resolved_mix,
            source_mix_constraints=resolved_constraints,
            difficulty_mix=sec.get("difficulty_mix"),
        )
        selected_count = len(chosen_ids)
        shortfall = max(0, target - selected_count)
        if shortfall > 0:
            any_selection_shortfall = True

        relaxed_rungs = [r["rung"] for r in rungs if r.get("relaxed")]
        selector_sections.append(
            {
                "section_id": sec.get("section_id"),
                "subject_id": subject_id,
                "section_label": sec.get("section_label"),
                "question_count": target,           # authored structural target
                "eligible_pool_count": len(eligible),  # == readiness base_depth(subject)
                "selected_count": selected_count,
                "shortfall": shortfall,
                "relaxed_rungs": relaxed_rungs,
                "rungs": rungs,
                "source_basis": "readiness_base_pool",
                # Source-mix provenance for audit trail.
                "source_mix_resolved": resolved_mix,
                "source_mix_source": mix_source,
            }
        )
        all_question_ids.extend(chosen_ids)

    # Fill the two A-PR1 slots.
    payload["selector_snapshot"] = {
        "ladder": list(_LADDER),
        "non_relaxable": list(_NON_RELAXABLE),
        "pool_predicate": _POOL_PREDICATE_NOTE,
        "sections": selector_sections,
        "any_shortfall": any_selection_shortfall,
    }
    payload["question_ids"] = all_question_ids

    # Propagate thin_bank when selection cannot fill an otherwise-ready section's
    # structural count — never silently under-fill and keep reporting ready.
    if payload.get("outcome") == "ready" and any_selection_shortfall:
        payload["outcome"] = "thin_bank"
        payload["selection_downgraded_ready_to_thin_bank"] = True
        payload["section_shortfall"] = [
            {
                "section_id": s["section_id"],
                "subject_id": s["subject_id"],
                "section_label": s["section_label"],
                "question_count": s["question_count"],
                "selected_count": s["selected_count"],
                "shortfall": s["shortfall"],
                "reasons": ["selection_below_question_count"],
            }
            for s in selector_sections
            if s["shortfall"] > 0
        ]

    return payload
