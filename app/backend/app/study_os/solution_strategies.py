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

from app.study_os import quant_heuristics, reasoning_strategies

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


def _project_reasoning(s: dict) -> dict:
    """Map a governed ``reasoning_strategies`` row → the normalized learner DTO.

    Migration 262 named the Reasoning content columns to match the shared DTO, so
    this is a near-straight copy tagged ``subject_family='reasoning'``. Still an
    explicit allowlist, so a governance column can never leak into the projection.
    """
    return {
        "id": s.get("id"),
        "subject_family": "reasoning",
        "name": s.get("name"),
        "strategy_type": s.get("strategy_type"),
        "formula_latex": s.get("formula_latex"),
        "standard_method": s.get("standard_method"),
        "faster_method": s.get("faster_method"),
        "worked_example": s.get("worked_example"),
        "key_observation": s.get("key_observation"),
        "common_traps": s.get("common_traps"),
        "relevance": s.get("relevance") or "related",
    }


def _sort_key(s: dict) -> tuple:
    return (
        _RELEVANCE_RANK.get(s.get("relevance"), 99),
        (s.get("name") or "").lower(),
        str(s.get("id") or ""),
    )


_SUBJECT_SOURCES = ("quant", "reasoning")


def strategies_for_questions(
    supabase: Any,
    question_ids: list[str],
    *,
    strict: bool = False,
    subjects: tuple[str, ...] | None = None,
) -> dict[str, list[dict]]:
    """Return ``{question_id: [normalized strategy DTO, …]}`` for every requested
    question, aggregated across the selected subject sources.

    Every requested id is present with at least ``[]``. Deterministic ordering
    (relevance → name → id).

    ``strict=False`` (default, the mock-review consumer, contract §11.7): each
    subject source is fail-soft — an error in one source contributes nothing
    rather than breaking the review response. ``strict=True`` (the standalone
    Improvement Lab feed): a subject-source read failure PROPAGATES so a
    strategy-table outage surfaces as an error, not a silently-empty feed.

    ``subjects`` restricts which sources are read (default: all). A subject-scoped
    feed passes e.g. ``subjects=("quant",)`` so an UNRELATED source's outage can
    never fail (or, in strict mode, 502) the requested feed — preserving the
    Improvement Lab's independent-section contract (Codex #999)."""
    ids = [q for q in dict.fromkeys(question_ids or []) if q]
    out: dict[str, list[dict]] = {q: [] for q in ids}
    if not ids:
        return out
    want = subjects or _SUBJECT_SOURCES

    def _source(reader, projector, label):
        if strict:
            data = reader(supabase, ids, strict=True)
        else:
            try:
                data = reader(supabase, ids)
            except Exception as exc:  # noqa: BLE001
                logger.warning("solution_strategies %s source failed err=%r", label, exc)
                data = {}
        for qid, rows in (data or {}).items():
            if qid in out:
                out[qid].extend(projector(r) for r in rows)

    if "quant" in want:
        _source(quant_heuristics.heuristics_for_questions, _project_quant, "quant")
    if "reasoning" in want:
        _source(reasoning_strategies.strategies_for_questions, _project_reasoning, "reasoning")

    for qid in out:
        out[qid].sort(key=_sort_key)
    return out
