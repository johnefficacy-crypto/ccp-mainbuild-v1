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
     selectable set, answerable types only (mcq/msq/integer),
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
    "MCQ-only (integer/msq excluded — no scoring path yet), is_current/"
    "is_current_based excluded, e2e_fixture excluded / NULL provenance retained, "
    "not-expired; scoped by section subject_id. Equals the pool the readiness "
    "verdict was computed over."
)


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
            "source_type, source_kind"
        )
        .eq("exam_id", exam_id)
        .in_("reviewer_status", statuses)
        .in_("question_type", list(_SELECTABLE_QUESTION_TYPES))
        .or_(f"source_type.is.null,source_type.neq.{_E2E_FIXTURE_SOURCE_TYPE}")
    )
    pool = [
        r
        for r in rows
        if _not_expired(r.get("valid_until"), now_iso)
        # is_current / is_current_based are segmented OUT of the base pool by the
        # diagnostic; the base mock must not draw time-bound items.
        and not (bool(r.get("is_current")) or bool(r.get("is_current_based")))
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


def _select_section(pool: list[dict], target: int, *, source_mix: dict | None, difficulty_mix: dict | None):
    """Run the relaxation ladder over one section's eligible pool.

    Returns ``(question_ids, rungs)``. ``rungs`` lists every ladder rung in fixed
    order with its status + whether it relaxed — so the snapshot reflects exactly
    what happened, including the inert A-PR4/A-PR5 rungs.
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
        chosen_ids, rungs = _select_section(
            eligible,
            target,
            source_mix=sec.get("source_mix"),
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
