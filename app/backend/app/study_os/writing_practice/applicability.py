"""EWP writing-prompt applicability resolver (migration 214 content-scoping).

Canonical writing content is SUBJECT-scoped (`writing_prompts` has no exam
columns since migration 214). APPLICABILITY — which exam / family / phase a prompt
may be launched under — is carried SOLELY by `public.writing_prompt_targets`.

This module is the single, deterministic authority that turns a set of target
rows + an authoritative exam context into an applicability verdict. It is the
mandatory source for BOTH:

  * session-creation enforcement (``POST /study/practice/english/sessions`` must
    reject a prompt that is not applicable for the session's exam context), and
  * planner / aspirant prompt selection (which prompts may be surfaced for an
    exam+phase context).

Semantics (locked by migration 214 header + the checkpost P0s):

  * DEFAULT-DENY. A prompt is applicable IFF it has an ACTIVE matching target.
    NO active target => NOT applicable (UNASSIGNED). Never global-by-absence.
    Deleting/cascading-away a target can only REMOVE applicability, never widen
    it — fail-closed.
  * GLOBAL is EXPLICIT only: an active ``is_global=true`` target (all scope
    columns NULL) applies to every context, including a context with no exam.
  * PRECEDENCE bands, most specific first: phase > exam > family > global. Each
    target row names EXACTLY ONE band (214's CHECK). The verdict is decided by
    the MOST SPECIFIC band that has a non-inert matching target.
  * EXCLUSION. ``applicability_status='excluded'`` subtracts a narrower scope
    from an explicit broader active scope (e.g. exclude one exam/phase from an
    active global/family target). An excluded row confers no applicability of
    its own; when it is the most specific matching band, the verdict is NOT
    applicable.
  * ``pending_review`` / ``rejected`` (any status that is not ``active`` or
    ``excluded``) is INERT — it neither widens nor blocks. It is skipped, and
    resolution falls through to the next broader band.

The resolver reads under the service role (``writing_prompt_targets`` is
service-role-managed with no client RLS policy — migration 214 §4). Aspirant
surfaces never read raw target rows; they receive this already-filtered verdict.
"""
from __future__ import annotations

from typing import Any, Iterable

from app.db.utils import maybe_single

# Most-specific -> least-specific precedence bands.
_BAND_ORDER = ("phase", "exam", "family", "global")

_TARGET_COLUMNS = (
    "prompt_id,is_global,exam_family_id,exam_id,exam_phase_id,applicability_status"
)


def _as_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _match_band(
    target: dict,
    *,
    exam_id: str | None,
    exam_phase_id: str | None,
    exam_family_id: str | None,
) -> str | None:
    """Which precedence band this target row occupies for the given context.

    Returns the band name if the row's single scope MATCHES the context, else
    None (the row does not apply to this context at all). Exactly one scope is
    set per row (214 CHECK), so this is an ordered set of mutually-exclusive
    tests.
    """
    if target.get("is_global"):
        return "global"
    phase = _as_str(target.get("exam_phase_id"))
    if phase is not None:
        return "phase" if exam_phase_id and phase == _as_str(exam_phase_id) else None
    exam = _as_str(target.get("exam_id"))
    if exam is not None:
        return "exam" if exam_id and exam == _as_str(exam_id) else None
    family = _as_str(target.get("exam_family_id"))
    if family is not None:
        return "family" if exam_family_id and family == _as_str(exam_family_id) else None
    return None


def evaluate_targets(
    targets: Iterable[dict],
    *,
    exam_id: str | None,
    exam_phase_id: str | None,
    exam_family_id: str | None,
) -> bool:
    """Deterministic applicability verdict for one prompt's target rows.

    Pure function — no I/O. ``targets`` are the ``writing_prompt_targets`` rows
    for a SINGLE prompt. Returns True IFF the prompt is applicable to the given
    (exam, phase, family) context under the default-deny + precedence +
    exclusion semantics described in the module docstring.
    """
    # Bucket matching rows by band, keeping their statuses.
    by_band: dict[str, list[str]] = {}
    for t in targets:
        band = _match_band(
            t, exam_id=exam_id, exam_phase_id=exam_phase_id, exam_family_id=exam_family_id
        )
        if band is None:
            continue
        by_band.setdefault(band, []).append(t.get("applicability_status") or "")

    # Decide at the most specific band that carries a non-inert (active|excluded)
    # matching row. Inert rows (pending_review/rejected/anything else) fall
    # through to the next broader band.
    for band in _BAND_ORDER:
        statuses = by_band.get(band)
        if not statuses:
            continue
        has_active = "active" in statuses
        has_excluded = "excluded" in statuses
        if has_excluded:
            # A narrower excluded carve-out wins over a same-band active (which
            # the unique index makes impossible anyway) — fail-closed.
            return False
        if has_active:
            return True
        # Only inert rows in this band — keep looking at broader bands.
    return False


# --------------------------------------------------------------------------- #
# DB-facing helpers (service-role Supabase client).                           #
# --------------------------------------------------------------------------- #

def _resolve_exam_family(supabase: Any, exam_id: str | None) -> str | None:
    """The exam's family id, or None when there is no exam / no family."""
    if not exam_id:
        return None
    row = maybe_single(
        supabase.table("exams")
        .select("exam_family_id")
        .eq("id", str(exam_id))
        .maybe_single()
    )
    return (row or {}).get("exam_family_id")


def _fetch_targets(supabase: Any, prompt_ids: list[str]) -> dict[str, list[dict]]:
    """Target rows grouped by prompt_id for the given prompts."""
    grouped: dict[str, list[dict]] = {pid: [] for pid in prompt_ids}
    if not prompt_ids:
        return grouped
    rows = (
        supabase.table("writing_prompt_targets")
        .select(_TARGET_COLUMNS)
        .in_("prompt_id", prompt_ids)
        .execute()
    ).data or []
    for r in rows:
        pid = _as_str(r.get("prompt_id"))
        if pid in grouped:
            grouped[pid].append(r)
    return grouped


def is_prompt_applicable(
    supabase: Any,
    prompt_id: str,
    *,
    exam_id: str | None,
    exam_phase_id: str | None,
) -> bool:
    """Whether ``prompt_id`` is applicable for the authoritative exam context.

    Fail-closed: with no exam context (``exam_id`` None) only an explicit active
    global target can make a prompt applicable — a scoped prompt is denied.
    """
    family_id = _resolve_exam_family(supabase, exam_id)
    targets = _fetch_targets(supabase, [str(prompt_id)]).get(str(prompt_id), [])
    return evaluate_targets(
        targets, exam_id=exam_id, exam_phase_id=exam_phase_id, exam_family_id=family_id
    )


def resolve_applicable_prompt_ids(
    supabase: Any,
    prompt_ids: Iterable[str],
    *,
    exam_id: str | None,
    exam_phase_id: str | None,
) -> set[str]:
    """The subset of ``prompt_ids`` applicable for the exam context.

    The mandatory selection primitive for planner / aspirant surfaces: never
    surface a prompt this set does not contain.
    """
    ids = [str(p) for p in prompt_ids]
    family_id = _resolve_exam_family(supabase, exam_id)
    grouped = _fetch_targets(supabase, ids)
    return {
        pid
        for pid in ids
        if evaluate_targets(
            grouped.get(pid, []),
            exam_id=exam_id,
            exam_phase_id=exam_phase_id,
            exam_family_id=family_id,
        )
    }
