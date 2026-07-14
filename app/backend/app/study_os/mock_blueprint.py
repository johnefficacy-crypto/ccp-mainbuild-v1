"""Exam-realistic generated-mock BLUEPRINT PAYLOAD service (A-PR1).

NON-MUTATING. This service assembles a generated-mock blueprint payload for a
single exam phase and returns it together with the diagnostic readiness verdict.
It writes NOTHING:

  * it does NOT insert a ``mock_generated_blueprints`` row (persistence is A-PR3),
  * it does NOT start an attempt (mock_engine.start_attempt is untouched),
  * it does NOT select or fill questions (selection is A-PR2),
  * it does NOT personalize (A-PR5) or handle descriptive items (Track B).

What it DOES:
  1. Builds the exam-realism STRUCTURAL ENVELOPE from authored
     ``exam_phase_sections`` (per-section structure, question_count,
     marks/negative-marking, timing, weightage, order, subject_id), reusing
     ``section_structure_completeness`` for the completeness signal.
  2. Calls ``assemble_mock_readiness_report`` with the caller-supplied statuses
     + thresholds so the per-phase verdict is COMPUTED (never 'skipped'), and
     attaches that verdict + summary to the payload verbatim — the verdict
     vocabulary is the diagnostic's (per-section blocked / thin_bank / ready;
     phase summary {ready, thin_bank, blocked}), not reinvented here.
  3. Returns a structured payload for every outcome (ready / thin_bank /
     blocked), shaped to mirror the A-PR0 ``mock_generated_blueprints`` CONTENT
     columns (template_snapshot / section_snapshot / selector_snapshot /
     question_ids / readiness_snapshot). A-PR3 supplies the persistence metadata
     migration 174 requires — ``expires_at`` (NOT NULL, no default) and
     ``status`` (DB default 'draft') — which this service does not set.

AUTHORED-STRUCTURE SCOPE (important): readiness is computed over AUTHORED
``exam_phase_sections`` rows ONLY. There is no source of truth here for whether
an exam's authored structure is officially complete: OP-0 audits authored rows
and cannot tell whether a section is missing, so this service deliberately does
NOT judge "official N-section completeness". That stays a HUMAN canary-prep
gate. (The SSC CGL Tier 1 demo seed now authors all FOUR real sections,
including General Awareness; earlier it carried only three, and this service
reported the authored count either way without flagging the gap — the point is
the service never self-reports official completeness.) The payload marks this
scope explicitly (``authored_structure_scope`` / ``scope_note``).

DESIGN INTENT: the verdict is data-driven off the diagnostic. When the missing
section is authored and content is populated, the SAME code flips a phase from
thin_bank to ready with NO code change.

Thresholds (selectable_statuses, verified_status, min_per_section,
min_locked_coverage) are PARAMETERS with NO baked-in defaults — mirroring the
diagnostic's no-default discipline. They are caller-supplied, never assumed.
"""
from __future__ import annotations

import logging

from app.exam_intelligence.diagnostics import (
    _fetch_all,
    assemble_mock_readiness_report,
    section_structure_completeness,
)

logger = logging.getLogger("career_copilot.study_os.mock_blueprint")

# A-PR1 only builds the exam-realistic blueprint. 'personalized' (the other
# value allowed by the migration-174 source CHECK) is A-PR5 and out of scope.
_EXAM_REALISTIC = "exam_realistic"

# Section verdict the diagnostic emits for a too-shallow base MCQ pool. Indexed
# (not redefined) here so the per-section shortfall list mirrors exactly what
# readiness_verdict flagged — the vocabulary stays owned by diagnostics.
_THIN_REASON = "thin_mcq_pool"


def _structural_envelope(sb, *, exam_id: str, exam_phase_id: str) -> dict:
    """Authored structural envelope for one phase's exam_phase_sections.

    Reuses ``section_structure_completeness`` for the completeness signal
    (question_count / marks / duration present + ``missing`` / ``complete``),
    then enriches each section with the envelope-only columns that helper does
    not surface — negative_marking, weightage_percent, difficulty_level,
    sort_order — read straight from ``exam_phase_sections`` using its REAL
    column names (migration 030). NO questions are selected or filled here;
    question selection is A-PR2.

    Returns an envelope whose ``sections`` is empty when the phase has no
    authored sections (the caller treats that as envelope-absent / blocked).
    """
    structure = section_structure_completeness(
        sb, exam_id, exam_phase_id=exam_phase_id
    )

    # Envelope-only columns (not surfaced by the completeness helper).
    extra_rows = _fetch_all(
        lambda: sb.table("exam_phase_sections")
        .select(
            "id, negative_marking, weightage_percent, difficulty_level, sort_order"
        )
        .eq("exam_phase_id", exam_phase_id)
    )
    extra_by_id = {r.get("id"): r for r in extra_rows}

    sections = []
    for s in structure.get("sections") or []:
        extra = extra_by_id.get(s.get("section_id"), {})
        sections.append(
            {
                "section_id": s.get("section_id"),
                "exam_phase_id": s.get("exam_phase_id"),
                "subject_id": s.get("subject_id"),
                "section_label": s.get("section_label"),
                "question_count": s.get("question_count"),
                "marks": s.get("marks"),
                "negative_marking": extra.get("negative_marking"),
                "duration_mins": s.get("duration_mins"),
                "duration_source": s.get("duration_source"),
                "weightage_percent": extra.get("weightage_percent"),
                "difficulty_level": extra.get("difficulty_level"),
                "sort_order": extra.get("sort_order"),
                "structure_complete": s.get("complete"),
                "missing": s.get("missing"),
            }
        )
    sections.sort(key=lambda r: (r.get("sort_order") if r.get("sort_order") is not None else 0))

    return {
        "exam_id": exam_id,
        "exam_phase_id": exam_phase_id,
        # Marks the scope of this envelope/verdict: AUTHORED rows only. There is
        # no source of truth here for official section completeness — see module
        # docstring. A human canary-prep gate owns that judgement.
        "authored_structure_scope": True,
        "authored_section_count": structure.get("section_count", 0),
        "sections_missing_structure": structure.get("sections_missing_structure", 0),
        "sections": sections,
    }


def _phase_verdict(report: dict, exam_phase_id: str) -> dict | None:
    """Pull the COMPUTED per-phase readiness_verdict out of the assembler report.

    The assembler groups verdicts per phase; with an exam_phase_id supplied it
    reports exactly the one phase (or none if the phase id does not exist). The
    verdict is reused verbatim — never recomputed here.
    """
    for block in report.get("phases") or []:
        if block.get("exam_phase_id") == exam_phase_id:
            return block.get("readiness_verdict")
    return None


def _overall_outcome(summary: dict) -> str:
    """Collapse the per-section summary into a single phase outcome.

    Vocabulary mirrors the diagnostic's: any blocked section blocks the phase;
    else any thin_bank section makes it thin_bank; else ready.
    """
    if summary.get("blocked", 0) > 0:
        return "blocked"
    if summary.get("thin_bank", 0) > 0:
        return "thin_bank"
    return "ready"


def _section_shortfall(verdict_sections: list, envelope_sections: list, *, min_per_section: int) -> list:
    """Per-section shortfall for thin_bank sections (base pool below threshold).

    Shortfall is derived from the diagnostic's own per-section base_pool, so the
    list cannot drift from the verdict that produced it. subject_id/label are
    enriched from the structural envelope when present.
    """
    label_by_section = {
        s.get("section_id"): s for s in (envelope_sections or [])
    }
    out = []
    for vs in verdict_sections or []:
        if _THIN_REASON not in (vs.get("reasons") or []):
            continue
        base_pool = vs.get("base_pool", 0)
        env = label_by_section.get(vs.get("section_id"), {})
        out.append(
            {
                "section_id": vs.get("section_id"),
                "subject_id": vs.get("subject_id"),
                "section_label": vs.get("section_label") or env.get("section_label"),
                "base_pool": base_pool,
                "min_per_section": min_per_section,
                "shortfall": max(0, min_per_section - base_pool),
                "reasons": vs.get("reasons"),
            }
        )
    return out


def build_blueprint_payload(
    sb,
    *,
    exam_id: str,
    exam_phase_id: str,
    user_id: str,
    source: str = _EXAM_REALISTIC,
    selectable_statuses,
    verified_status,
    min_per_section,
    min_locked_coverage,
) -> dict:
    """Assemble (non-mutating) the exam-realistic blueprint payload for a phase.

    Inputs:
      * exam_id / exam_phase_id — the phase to blueprint.
      * user_id — carried for A-PR3's later persist; A-PR1 writes it NOWHERE.
      * source — must be 'exam_realistic' (personalized is A-PR5).
      * selectable_statuses / verified_status / min_per_section /
        min_locked_coverage — threshold/vocabulary PARAMETERS, no defaults.

    Returns a payload mirroring the A-PR0 mock_generated_blueprints CONTENT
    columns (template_snapshot / section_snapshot / selector_snapshot /
    question_ids / readiness_snapshot) plus the outcome, envelope and (for
    thin_bank) the per-section shortfall. A-PR3 supplies the persistence metadata
    (expires_at NOT NULL/no default, status DB default 'draft'); this service
    sets neither. ``persisted`` is always False — nothing is written.

    Outcomes:
      * ready    → envelope + verdict.
      * thin_bank → envelope + verdict + per-section shortfall.
      * blocked / no_sections → verdict + reason; envelope absent (no sections)
        or partial (structure present but incomplete).
    """
    if source != _EXAM_REALISTIC:
        # A-PR1 is the exam-realistic service only. 'personalized' is A-PR5.
        raise ValueError(
            f"mock_blueprint.build_blueprint_payload only supports "
            f"source='{_EXAM_REALISTIC}' (got {source!r}); personalized is A-PR5"
        )

    # Hard-validate the readiness inputs up front so a SKIPPED verdict can never
    # masquerade as a real 'blocked/no_sections' outcome. assemble_mock_readiness_
    # report skips the verdict (rather than computing it) when selectable_statuses
    # is falsy or either threshold is None — without this guard that skip would
    # leave verdict is None and be misread below as "no exam_phases row". Fail
    # loud instead. verified_status only feeds the informational verified-pyq
    # depth (not the verdict), but it is validated here for caller consistency.
    if not selectable_statuses:
        raise ValueError("selectable_statuses is required and must be non-empty")
    if min_per_section is None:
        raise ValueError("min_per_section is required")
    if min_locked_coverage is None:
        raise ValueError("min_locked_coverage is required")
    if not verified_status:
        raise ValueError("verified_status is required")

    # 1. Structural envelope from AUTHORED exam_phase_sections (no selection).
    envelope = _structural_envelope(sb, exam_id=exam_id, exam_phase_id=exam_phase_id)
    has_sections = bool(envelope.get("sections"))

    # 2. COMPUTE the per-phase verdict via the diagnostic orchestrator — pass the
    #    supplied vocabulary + thresholds so the verdict is real, not 'skipped'.
    report = assemble_mock_readiness_report(
        sb,
        exam_id=exam_id,
        exam_phase_id=exam_phase_id,
        selectable_statuses=selectable_statuses,
        verified_status=verified_status,
        min_per_section=min_per_section,
        min_locked_coverage=min_locked_coverage,
    )
    verdict = _phase_verdict(report, exam_phase_id)

    if verdict is None:
        # Phase id resolves to no exam_phases row → there is nothing to scope a
        # verdict over. Surface a blocked/no_sections outcome without inventing a
        # verdict shape beyond what the diagnostic emits for an empty phase.
        verdict = {
            "exam_id": exam_id,
            "exam_phase_id": exam_phase_id,
            "pool_scope": "subject",
            "thresholds": {
                "min_per_section": min_per_section,
                "min_locked_coverage": min_locked_coverage,
            },
            "sections": [
                {
                    "section_id": None,
                    "subject_id": None,
                    "section_label": None,
                    "verdict": "blocked",
                    "reasons": ["no_sections"],
                    "base_pool": 0,
                    "locked_coverage": 0,
                }
            ],
            "summary": {"ready": 0, "thin_bank": 0, "blocked": 1},
        }

    summary = verdict.get("summary") or {"ready": 0, "thin_bank": 0, "blocked": 0}
    outcome = _overall_outcome(summary)

    thresholds = {
        "selectable_statuses": list(selectable_statuses or []),
        "verified_status": verified_status,
        "min_per_section": min_per_section,
        "min_locked_coverage": min_locked_coverage,
    }

    # template_snapshot: phase-level realism metadata. envelope_present records
    # whether any authored section backs this blueprint (blocked/no_sections has
    # none). authored_structure_scope flags that completeness is NOT judged here.
    template_snapshot = {
        "source": source,
        "exam_id": exam_id,
        "exam_phase_id": exam_phase_id,
        "authored_structure_scope": True,
        "authored_section_count": envelope.get("authored_section_count", 0),
        "envelope_present": has_sections,
        "thresholds": thresholds,
    }

    # section_snapshot: the structural envelope sections. Empty for
    # blocked/no_sections (envelope absent), partial when structure incomplete.
    section_snapshot = envelope.get("sections") if has_sections else []

    payload = {
        "service": "exam_realistic_blueprint",
        "source": source,
        "exam_id": exam_id,
        "exam_phase_id": exam_phase_id,
        # user_id is carried for A-PR3's persist; A-PR1 writes it nowhere.
        "user_id": user_id,
        # A-PR1 is NON-MUTATING: no row in mock_generated_blueprints, no attempt.
        "persisted": False,
        "authored_structure_scope": True,
        "scope_note": (
            "readiness computed over AUTHORED exam_phase_sections only; whether "
            "that structure is officially complete (e.g. all real sections "
            "authored) is a human canary-prep gate, NOT enforced in code"
        ),
        "thresholds": thresholds,
        "outcome": outcome,
        # Snapshot columns mirroring migration 174's CONTENT columns; A-PR3
        # supplies persistence metadata — expires_at (NOT NULL, no default) and
        # status (DB default 'draft') — which A-PR1 deliberately does not set.
        "template_snapshot": template_snapshot,
        "section_snapshot": section_snapshot,
        # Question selection + relaxation ladder are A-PR2: left empty here.
        "selector_snapshot": {},
        "question_ids": [],
        # The diagnostic verdict + summary, surfaced verbatim (data-driven).
        "readiness_snapshot": {
            "verdict": verdict,
            "summary": summary,
        },
        # Convenience view for the envelope (absent/partial for blocked).
        "structural_envelope": envelope if has_sections else None,
        # Per-section shortfall is meaningful for thin_bank.
        "section_shortfall": _section_shortfall(
            verdict.get("sections"),
            section_snapshot,
            min_per_section=min_per_section,
        )
        if outcome == "thin_bank"
        else [],
    }
    return payload
