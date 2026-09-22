"""Answer structures on the learner side: read after submit, tick covered points.

Every query runs on the service-role client, which bypasses RLS, so the two
rules migration 303's policies state are re-stated here in code:

* only a VERIFIED structure of a VERIFIED question is ever returned;
* a structure is returned only for an attempt the caller owns and has
  SUBMITTED. Before submit the answer is still being written, and seeing the
  checklist then would turn the practice into copying it.

Coverage ticks are the aspirant's own judgement — which points they believe
their answer made. Nothing here reads the answer to check.
"""
from __future__ import annotations

from typing import Any

from app.study_os import descriptive as d
from app.study_os.answer_structure_schema import (
    coverage_pct,
    learner_payload,
    point_ids,
)

_STRUCTURE_COLUMNS = (
    "id, pyq_question_id, version, status, directive, demand, intro_angles, "
    "body_points, dimensions, examples, conclusion_angles, pitfalls, "
    "word_budget, sources_note"
)


def verified_structure(supabase: Any, question_id: str) -> dict[str, Any] | None:
    """The one verified structure of a verified question, or None."""
    if not question_id:
        return None
    question = d._safe(
        lambda: (
            supabase.table("pyq_questions")
            .select("id")
            .eq("id", question_id)
            .eq("reviewer_status", d.QUESTION_REVIEWER_STATUS)
            .limit(1)
            .execute()
            .data
        ),
        default=[],
    ) or []
    if not question:
        return None
    rows = d._safe(
        lambda: (
            supabase.table("answer_structures")
            .select(_STRUCTURE_COLUMNS)
            .eq("pyq_question_id", question_id)
            .eq("status", "verified")
            .limit(1)
            .execute()
            .data
        ),
        default=[],
    ) or []
    # Defence in depth: the filter above is the rule, this is the proof.
    rows = [r for r in rows if r.get("status") == "verified"]
    return rows[0] if rows else None


def _require_submitted(attempt: dict[str, Any]) -> None:
    if (attempt.get("status") or "draft") != "submitted":
        raise d.DescriptiveError(
            "not_submitted",
            "Submit your answer first — the answer structure opens after you do.",
            409,
        )


def structure_for_attempt(supabase: Any, user_id: str, attempt_id: str) -> dict[str, Any]:
    """The comparison panel's payload for one submitted attempt of this user.

    ``structure`` is None when the question has no verified structure yet; the
    surface says so plainly rather than hiding the panel.
    """
    attempt = d._load_owned_attempt(supabase, user_id, attempt_id)
    _require_submitted(attempt)
    row = verified_structure(supabase, str(attempt.get("pyq_question_id") or ""))
    if row is None:
        return {"attempt_id": attempt_id, "structure": None, "covered_point_ids": [],
                "points_covered_pct": None, "ticks_from_older_version": False}

    ids = point_ids(row)
    stored_version = d._as_int(attempt.get("structure_version"))
    same_version = stored_version == d._as_int(row.get("version"))
    covered = [
        c for c in (attempt.get("covered_point_ids") or []) if str(c) in set(ids)
    ] if same_version else []
    return {
        "attempt_id": attempt_id,
        "structure": learner_payload(row),
        "covered_point_ids": covered,
        "points_covered_pct": coverage_pct(covered, ids) if same_version else None,
        # Ticks made against a structure that has since been replaced are not
        # carried onto the new one — its points are different points.
        "ticks_from_older_version": bool(stored_version) and not same_version,
    }


def save_coverage(
    supabase: Any,
    user_id: str,
    attempt_id: str,
    *,
    structure_version: Any,
    covered_point_ids: Any,
) -> dict[str, Any]:
    """Store which body points the aspirant ticked, against one version.

    409 when the structure the client ticked against is no longer the verified
    one — ticks against a withdrawn checklist would measure nothing.
    """
    attempt = d._load_owned_attempt(supabase, user_id, attempt_id)
    _require_submitted(attempt)
    row = verified_structure(supabase, str(attempt.get("pyq_question_id") or ""))
    if row is None:
        raise d.DescriptiveError(
            "no_structure", "This question has no answer structure yet.", 404
        )
    version = d._as_int(structure_version)
    if version is None or version != d._as_int(row.get("version")):
        raise d.DescriptiveError(
            "structure_changed",
            "The answer structure was updated. Reload to tick against the new one.",
            409,
        )
    if not isinstance(covered_point_ids, list):
        raise d.DescriptiveError(
            "covered_invalid", "covered_point_ids must be a list.", 422
        )
    ids = point_ids(row)
    wanted = [str(c) for c in covered_point_ids]
    unknown = sorted(set(wanted) - set(ids))
    if unknown:
        raise d.DescriptiveError(
            "covered_unknown",
            f"Not points of this structure: {', '.join(unknown)}.",
            422,
        )
    # Stored in the structure's own order, de-duplicated, so two clients that
    # tick the same set store the same array.
    ordered = [i for i in ids if i in set(wanted)]
    updated = d._safe(
        lambda: (
            supabase.table("descriptive_attempts")
            .update({"structure_version": version, "covered_point_ids": ordered})
            .eq("id", attempt_id)
            .eq("user_id", user_id)
            .eq("status", "submitted")
            .execute()
            .data
        ),
        default=None,
    )
    if not updated:
        raise d.DescriptiveError(
            "coverage_save_failed", "Couldn't save your ticks.", 503
        )
    return {
        "attempt_id": attempt_id,
        "structure_version": version,
        "covered_point_ids": ordered,
        "points_covered_pct": coverage_pct(ordered, ids),
    }


def point_ids_by_version(
    supabase: Any, pairs: set[tuple[str, int]]
) -> dict[tuple[str, int], list[str]]:
    """(question_id, version) → that version's body-point ids, in one batched
    read per chunk of questions. Any status: an attempt ticked against version 2
    stays measurable against version 2 after version 3 is verified. Only ids
    are read — nothing unverified is returned to a learner."""
    if not pairs:
        return {}
    question_ids = sorted({q for q, _ in pairs})
    out: dict[tuple[str, int], list[str]] = {}
    for chunk in d._chunks(question_ids):
        rows = d._safe(
            lambda ids=chunk: (
                supabase.table("answer_structures")
                .select("pyq_question_id, version, body_points")
                .in_("pyq_question_id", ids)
                .execute()
                .data
            ),
            default=[],
        ) or []
        for r in rows:
            key = (str(r.get("pyq_question_id")), d._as_int(r.get("version")) or 0)
            if key in pairs:
                out[key] = point_ids(r)
    return out


def attempt_coverage(
    supabase: Any, attempts: list[dict[str, Any]]
) -> dict[str, float | None]:
    """attempt_id → points covered %, for attempts that carry ticks."""
    pairs = {
        (str(a.get("pyq_question_id")), d._as_int(a.get("structure_version")))
        for a in attempts
        if a.get("covered_point_ids") is not None and d._as_int(a.get("structure_version"))
    }
    totals = point_ids_by_version(supabase, pairs)  # type: ignore[arg-type]
    out: dict[str, float | None] = {}
    for a in attempts:
        key = (str(a.get("pyq_question_id")), d._as_int(a.get("structure_version")))
        if a.get("covered_point_ids") is None or key not in totals:
            continue
        out[str(a.get("id"))] = coverage_pct(a.get("covered_point_ids"), totals[key])
    return out
