"""Solution Strategies — learner-safe per-question strategy projection (GQR-S1).

Contract: docs/architecture/solution-strategies-improvement-lab.md.

Learner-facing **Solution Strategy** content is a NORMALIZED, governance-stripped
projection over the governed subject authorities (Quant heuristics today;
Reasoning strategies later). The mock / generated-mock review path calls
:func:`strategies_for_questions` ONCE per attempt; registering a new subject
source here must never force another rewrite of ``mock_engine.get_review``.

Guarantees (inherited from the per-subject batched readers):
  * conjunctive verified gate (strategy verified AND active AND link verified),
  * LIVE read at review time — never frozen into the attempt snapshot,
  * only the fields in :data:`ALLOWED_FIELDS` reach the learner payload
    (governance fields are dropped by CONSTRUCTION in the per-subject projector,
    not merely omitted by the caller),
  * fail-soft: a source read failure yields ``[]`` for that subject, never a 500.
"""
from __future__ import annotations

import logging
from typing import Any

from app.study_os import quant_heuristics

logger = logging.getLogger("career_copilot.study_os.solution_strategies")

# The learner-safe DTO. NO governance field (reviewer_status / reviewer_notes /
# reviewed_by / reviewed_at / created_by, applicability_rule, audit or CAS
# internals) may ever appear here. This tuple is the contract the frontend and
# tests assert against.
ALLOWED_FIELDS = (
    "id",
    "subject_family",
    "name",
    "strategy_type",
    "formula_latex",
    "standard_method",
    "faster_method",
    "worked_example",
    "key_observation",
    "common_traps",
    "relevance",
)

_RELEVANCE_RANK = {"primary": 0, "secondary": 1, "related": 2}


def _project_quant(h: dict) -> dict:
    """Map a governed ``quant_heuristics`` row → the normalized learner DTO.

    Renames ``heuristic_type`` → ``strategy_type`` and ``shortcut_method`` →
    ``faster_method`` and tags ``subject_family='quant'``. Built from an explicit
    allowlist, so governance columns present on the source row (reviewer_status,
    applicability_rule, reviewed_by, …) can never leak into the projection.
    """
    return {
        "id": h.get("id"),
        "subject_family": "quant",
        "name": h.get("name"),
        "strategy_type": h.get("heuristic_type"),
        "formula_latex": h.get("formula_latex"),
        "standard_method": h.get("standard_method"),
        "faster_method": h.get("shortcut_method"),
        "worked_example": h.get("worked_example"),
        # Quant heuristics carry no discrete "key observation" column in v1.
        "key_observation": None,
        "common_traps": h.get("common_traps"),
        "relevance": h.get("relevance") or "related",
    }


def _sort_key(s: dict) -> tuple:
    return (
        _RELEVANCE_RANK.get(s.get("relevance"), 99),
        (s.get("name") or "").lower(),
        str(s.get("id") or ""),
    )


def strategies_for_questions(
    supabase: Any, question_ids: list[str]
) -> dict[str, list[dict]]:
    """Return ``{question_id: [normalized strategy DTO, …]}`` for every requested
    question, aggregated across all subject sources.

    Every requested id is present with at least ``[]``. Deterministic ordering
    (relevance → name → id). Each subject source is read fail-soft: an error in
    one source contributes nothing rather than breaking the review response.
    """
    ids = [q for q in dict.fromkeys(question_ids or []) if q]
    out: dict[str, list[dict]] = {q: [] for q in ids}
    if not ids:
        return out

    # ── Quant source (batched, verified-only) ───────────────────────────────
    try:
        quant = quant_heuristics.heuristics_for_questions(supabase, ids)
    except Exception as exc:  # noqa: BLE001
        logger.warning("solution_strategies quant source failed err=%r", exc)
        quant = {}
    for qid, rows in (quant or {}).items():
        if qid in out:
            out[qid].extend(_project_quant(h) for h in rows)

    # Reasoning source registers here in a later slice (GQR-S4) — same shape.

    for qid in out:
        out[qid].sort(key=_sort_key)
    return out
