"""Solution Strategies — learner-safe question and stimulus strategy projection.

Contract: docs/architecture/solution-strategies-improvement-lab.md.

Learner-facing **Solution Strategy** content is a NORMALIZED, governance-stripped
projection over the governed subject authorities. The mock / generated-mock
review path calls the batched aggregators once per attempt; registering a new
subject source must never force subject-specific response-loop rewrites.

Guarantees (inherited from the per-subject batched readers):
  * conjunctive verified gate (strategy verified AND active AND link verified),
  * LIVE read at review time — never frozen into the attempt snapshot,
  * only the fields in :data:`ALLOWED_FIELDS` reach the learner payload
    (governance fields are dropped by CONSTRUCTION in the per-subject projector,
    not merely omitted by the caller),
  * fail-soft review delivery: a source read failure yields empty strategy lists.
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
    allowlist, so governance columns present on the source row can never leak.
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
    this is a near-straight copy tagged ``subject_family='reasoning'``. It remains
    an explicit allowlist, so governance columns can never leak.
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
    """Return normalized strategy DTOs for every requested question.

    ``strict=False`` is the fail-soft mock-review contract. ``strict=True`` is
    used by standalone feeds so an authority outage is visible. ``subjects`` can
    restrict reads to one source, preserving independent feed failure domains.
    """
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


def strategies_for_stimuli(
    supabase: Any,
    stimulus_scopes: dict[str, list[dict]],
    *,
    strict: bool = False,
) -> dict[str, list[dict]]:
    """Project verified Reasoning set strategies into the shared learner DTO.

    Canonical IDs are normalized to strings before crossing the authority
    boundary, matching PostgREST's UUID JSON representation. Malformed top-level
    input returns an empty mapping; per-stimulus malformed scope lists remain in
    the result as ``[]`` through the underlying fail-closed authority.
    """
    if not isinstance(stimulus_scopes, dict):
        return {}

    scopes: dict[str, Any] = {}
    for raw_stimulus_id, question_scopes in stimulus_scopes.items():
        if raw_stimulus_id:
            scopes[str(raw_stimulus_id)] = question_scopes

    ids = list(dict.fromkeys(scopes))
    out: dict[str, list[dict]] = {stimulus_id: [] for stimulus_id in ids}
    if not ids:
        return out

    try:
        data = reasoning_strategies.strategies_for_stimuli(
            supabase,
            {stimulus_id: scopes[stimulus_id] for stimulus_id in ids},
            strict=strict,
        )
    except Exception as exc:  # noqa: BLE001
        if strict:
            raise
        logger.warning("solution_strategies reasoning stimulus source failed err=%r", exc)
        return out

    for raw_stimulus_id, rows in (data or {}).items():
        stimulus_id = str(raw_stimulus_id)
        if stimulus_id in out:
            out[stimulus_id] = sorted(
                (_project_reasoning(row) for row in rows),
                key=_sort_key,
            )
    return out
