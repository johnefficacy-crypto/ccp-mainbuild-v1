"""A cycle phase inherits its template's evidence — for READS only.

THE PROBLEM
-----------
The evidence chain — papers → snapshots → coverage — is phase-scoped at every
step, so a cycle phase can only produce coverage if the corpus is physically
moved onto it. UPSC CSE Mains has two phases:

=========================================  =======  ======  ========
phase                                      cycle    papers  coverage
=========================================  =======  ======  ========
626ec667-4bbf-4420-8715-48c5b83e0d11       null         60  1,497 with predictability
f42ffb84-082e-49db-9154-9fd973e8b6e5       2026          0  1,497 without
=========================================  =======  ======  ========

``exam_target_window.py:56-57`` deliberately excludes null-cycle phases from
targeting — a template is not something a person sits for — so the planner
reads the cycle phase, which holds the older copy, while the corpus sits on the
template where the planner structurally cannot see it. Recomputing against the
cycle phase does not help: ``score_snapshots.py:366-367`` filters
``pyq_papers`` by ``exam_phase_id``, so that compute finds zero papers.

Moving the papers would work and is what an operator reaches for. It is wrong:
8,302 questions spanning 1980-2026 are cycle-independent evidence, and a 1991
PSIR paper is not a 2026 artefact. Attaching the corpus to the 2026 cycle means
repointing it every cycle, forever, with the semantics degrading each time.

THE SHAPE
---------
The template holds the canonical evidence; each cycle's phase gets the
projected result. Reads fall back to the template; **writes never do** — a
compute scoped to a cycle phase reads the template's papers and writes
snapshots carrying the CYCLE phase id.

Two guarantees, both enforced here rather than left to callers:

* **Only cycle-reads-template.** A template resolves to no parent, so it can
  never read a cycle's data, and the resolved parent must itself be a template,
  so one cycle can never read another's. Leaking 2026 evidence into 2025 is the
  failure this direction exists to prevent.
* **Inheritance is all-or-nothing per read, and only when the target has
  nothing.** A cycle phase that carries its own papers uses its own; mixing the
  two sets would double-count. "Empty → inherit" keeps this strictly additive.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("career_copilot.exam_intelligence.phase_inheritance")

#: Written into the cycle phase's metadata by
#: `admin_exam_intel_cms.py:811` (`POST /exam-phases/promote-template`).
#: The explicit link, preferred over resolving by slug.
PROMOTED_FROM_KEY = "promoted_from_template_phase_id"


def _phase_row(sb: Any, phase_id: str, exam_id: str) -> dict[str, Any] | None:
    try:
        rows = (
            sb.table("exam_phases")
            .select("id, exam_id, exam_cycle_id, phase_slug, metadata")
            .eq("id", phase_id)
            .eq("exam_id", exam_id)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("phase_inheritance: phase read failed for %s: %s", phase_id, exc)
        return None
    return rows[0] if rows else None


def resolve_template_phase_id(
    sb: Any, exam_id: str, exam_phase_id: str | None
) -> str | None:
    """The template phase a cycle phase should inherit evidence from, or None.

    Returns None — meaning "no inheritance, behave exactly as before" — when:

    * no phase is scoped (an exam-wide compute),
    * the phase IS the template (``exam_cycle_id is null``),
    * the phase does not exist or does not belong to *exam_id*,
    * the exam has no template phase for that slug.

    Resolution prefers the explicit link recorded at promotion time
    (``metadata.promoted_from_template_phase_id``) and falls back to
    ``(exam_id, phase_slug, exam_cycle_id is null)``.

    That fallback is safe despite 86 exams sharing the slug ``mains``: the
    lookup is always scoped by ``exam_id``, and within one exam the partial
    unique index ``exam_phases_exam_slug_no_cycle_uidx``
    (``030_exam_registry_cycles_phases.sql:73-75``) guarantees AT MOST ONE
    null-cycle phase per slug. The slug collision that bit the PYQ explorer was
    across exams; this never crosses one.
    """
    if not exam_phase_id or not exam_id:
        return None

    phase = _phase_row(sb, exam_phase_id, exam_id)
    if not phase:
        return None
    if phase.get("exam_cycle_id") is None:
        # This phase is itself the template. Inheriting would mean reading a
        # cycle's data into the template — the direction that leaks one year's
        # evidence into another.
        return None

    meta = phase.get("metadata") if isinstance(phase.get("metadata"), dict) else {}
    candidate = meta.get(PROMOTED_FROM_KEY)
    if candidate:
        parent = _phase_row(sb, str(candidate), exam_id)
        if parent and parent.get("exam_cycle_id") is None:
            logger.debug(
                "phase_inheritance: %s inherits from template %s (explicit link)",
                exam_phase_id,
                parent["id"],
            )
            return str(parent["id"])
        logger.debug(
            "phase_inheritance: %s names template %s but it is missing or is "
            "itself cycle-bound; falling back to slug resolution",
            exam_phase_id,
            candidate,
        )

    slug = phase.get("phase_slug")
    if not slug:
        return None
    try:
        rows = (
            sb.table("exam_phases")
            .select("id")
            .eq("exam_id", exam_id)
            .eq("phase_slug", slug)
            .is_("exam_cycle_id", None)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("phase_inheritance: template lookup failed for %s: %s", slug, exc)
        return None
    if not rows:
        logger.debug(
            "phase_inheritance: exam %s has no template phase for slug %r; "
            "no inheritance",
            exam_id,
            slug,
        )
        return None
    logger.debug(
        "phase_inheritance: %s inherits from template %s (resolved by slug %r)",
        exam_phase_id,
        rows[0]["id"],
        slug,
    )
    return str(rows[0]["id"])
