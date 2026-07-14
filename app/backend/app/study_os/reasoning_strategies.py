"""Reasoning strategy authority — verified-only reads + review wrapper (GQR-S3/S4/S7).

Content Studio authors and reviews ``reasoning_strategies`` (migration 262). This
module is the read/selection authority the learner-feedback path uses, plus a
thin wrapper over the ``cms_review_reasoning_strategy`` lifecycle RPC.

Domain rule (CLAUDE.md): user-facing reads filter ``reviewer_status='verified'``
CONJUNCTIVELY. A strategy reaches a learner only when BOTH the strategy row and
its question/stimulus link are verified — and the strategy is active. Reviewed
links must also connect content whose topic/microtopic is compatible with the
strategy's governed Reasoning scope; this prevents a misassigned Reasoning link
from leaking onto a different subject's question or set. The batched readers
mirror ``study_os.quant_heuristics.heuristics_for_questions``: bounded queries,
explicit projection, deterministic order, and fail-soft review delivery.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from app.study_os.subject_runtime_policy import FAMILY_REASONING, family_for_subject

logger = logging.getLogger("career_copilot.study_os.reasoning_strategies")

_STRATEGIES = "reasoning_strategies"
_LINKS = "reasoning_question_strategies"
_STIMULUS_LINKS = "reasoning_stimulus_strategies"

# Learner-facing display order for a question's strategies.
_RELEVANCE_RANK = {"primary": 0, "secondary": 1, "related": 2}

# Content fields used by the learner projection. Migration 262 named these to
# match the shared solution-strategy DTO, so the projection is a straight copy.
# Governance fields (applicability_rule, reviewer notes/actors, timestamps, audit/
# CAS metadata) never cross this authority boundary.
_CONTENT_KEYS = (
    "id",
    "name",
    "strategy_type",
    "formula_latex",
    "standard_method",
    "faster_method",
    "key_observation",
    "worked_example",
    "common_traps",
)
_INTERNAL_SCOPE_KEYS = ("topic_id", "microtopic_id")
_STRATEGY_FIELDS = ",".join(
    (
        *_CONTENT_KEYS,
        *_INTERNAL_SCOPE_KEYS,
        "topic:topics!reasoning_strategies_topic_id_fkey("
        "subject:subjects(slug,subject_group))",
        "microtopic:topics!reasoning_strategies_microtopic_id_fkey("
        "parent_topic_id,subject:subjects(slug,subject_group))",
    )
)


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("db_op_failed op=reasoning_strategies err=%r", exc)
        return default


def _read(call: Callable[[], Any], strict: bool) -> Any:
    """Fail-soft (default, mock-review consumer) or strict (Improvement Lab feed —
    a read failure PROPAGATES so an outage is not disguised as an empty result)."""
    return call() if strict else _safe(call, default=None)


def _display_key(s: dict) -> tuple:
    """Stable learner display order: relevance, normalized name, then id."""
    return (
        _RELEVANCE_RANK.get(s.get("relevance"), 99),
        (s.get("name") or "").lower(),
        str(s.get("id") or ""),
    )


def _learner_row(row: dict) -> dict:
    """Defense-in-depth allowlist for the batched learner authority."""
    return {key: row.get(key) for key in _CONTENT_KEYS}


def _canonical_scope_is_reasoning(strategy: dict) -> bool:
    """Require every populated scope to resolve to canonical Reasoning taxonomy.

    Migration 262 guarantees only that at least one scope ID is populated; it does
    not constrain that topic to Reasoning or ensure a microtopic belongs to the
    paired topic. The embedded topic rows keep this validation inside the one
    strategy query required by the learner contract.
    """
    scopes: list[dict] = []

    topic_id = strategy.get("topic_id")
    if topic_id:
        topic = strategy.get("topic")
        if not isinstance(topic, dict):
            return False
        scopes.append(topic)

    microtopic_id = strategy.get("microtopic_id")
    if microtopic_id:
        microtopic = strategy.get("microtopic")
        if not isinstance(microtopic, dict):
            return False
        if topic_id and str(microtopic.get("parent_topic_id") or "") != str(topic_id):
            return False
        scopes.append(microtopic)

    for scope in scopes:
        subject = scope.get("subject")
        if not isinstance(subject, dict):
            return False
        if family_for_subject(
            slug=subject.get("slug"),
            subject_group=subject.get("subject_group"),
        ) != FAMILY_REASONING:
            return False
    return bool(scopes)


def _scope_matches(strategy: dict, question: Any) -> bool:
    """Fail closed unless every populated strategy scope dimension matches.

    When both topic and microtopic are stored, both must match. Topic IDs are
    canonical, subject-owned rows, so a mismatch also blocks a Reasoning strategy
    linked to a Quant/English question.
    """
    if not isinstance(question, dict) or not _canonical_scope_is_reasoning(strategy):
        return False
    strategy_topic = strategy.get("topic_id")
    strategy_microtopic = strategy.get("microtopic_id")
    if not strategy_topic and not strategy_microtopic:
        return False
    if strategy_topic and str(question.get("topic_id") or "") != str(strategy_topic):
        return False
    if (
        strategy_microtopic
        and str(question.get("microtopic_id") or "") != str(strategy_microtopic)
    ):
        return False
    return True


def strategies_for_questions(
    supabase: Any, question_ids: list[str], *, strict: bool = False
) -> dict[str, list[dict]]:
    """Return verified active reasoning strategies for every requested question id.

    Uses at most ONE link query and ONE strategy query regardless of how many
    question ids are passed (no N+1). The link query embeds the referenced bank
    question's topic scope, so the gate is conjunctive:

      link verified AND strategy verified AND strategy active AND scope match.

    Every requested id is present with at least ``[]``; rows never cross-leak
    between questions or subjects. Only learner content fields plus per-link
    relevance leave this authority, ordered deterministically by relevance, name,
    then id. Optional strategy content is fail-soft: a read failure returns the
    initialized empty mapping so the primary review response remains available.
    """
    ids = [q for q in dict.fromkeys(question_ids or []) if q]
    out: dict[str, list[dict]] = {q: [] for q in ids}
    if not ids:
        return out

    link_rows = _read(
        lambda: supabase.table(_LINKS)
        .select(
            "question_id,strategy_id,relevance,"
            "question:mock_question_bank!inner(topic_id,microtopic_id)"
        )
        .in_("question_id", ids)
        .eq("reviewer_status", "verified")
        .execute(),
        strict,
    )
    links = getattr(link_rows, "data", None) or []
    if not links:
        return out

    strategy_ids = sorted(
        {
            link.get("strategy_id")
            for link in links
            if isinstance(link, dict) and link.get("strategy_id")
        }
    )
    if not strategy_ids:
        return out

    strat_rows = _read(
        lambda: supabase.table(_STRATEGIES)
        .select(_STRATEGY_FIELDS)
        .in_("id", strategy_ids)
        .eq("reviewer_status", "verified")
        .eq("is_active", True)
        .execute(),
        strict,
    )
    strat_by_id = {
        row["id"]: row
        for row in (getattr(strat_rows, "data", None) or [])
        if isinstance(row, dict) and row.get("id")
    }

    for link in links:
        if not isinstance(link, dict):
            continue
        question_id = link.get("question_id")
        strategy = strat_by_id.get(link.get("strategy_id"))
        if (
            question_id in out
            and strategy is not None
            and _scope_matches(strategy, link.get("question"))
        ):
            out[question_id].append(
                {
                    **_learner_row(strategy),
                    "relevance": link.get("relevance") or "related",
                }
            )

    for question_id in out:
        out[question_id].sort(key=_display_key)
    return out


def _normalise_stimulus_scopes(
    stimulus_scopes: Any,
) -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    """Return ``(all_requested, valid_for_read)`` stimulus scope mappings.

    Set delivery is fail-closed: a missing, empty, or malformed question-scope list
    must never be silently shortened. Every requested stimulus remains in the
    output with ``[]``, but only groups whose COMPLETE scope list is a non-empty
    list/tuple of dictionaries are queried. This preserves the S7 invariant that a
    strategy must match every frozen question in the set.
    """
    requested: dict[str, list[dict]] = {}
    valid: dict[str, list[dict]] = {}
    if not isinstance(stimulus_scopes, dict):
        return requested, valid

    for raw_stimulus_id, raw_scopes in stimulus_scopes.items():
        if not raw_stimulus_id:
            continue
        stimulus_id = str(raw_stimulus_id)
        requested[stimulus_id] = []
        if not isinstance(raw_scopes, (list, tuple)) or not raw_scopes:
            continue
        if any(not isinstance(scope, dict) for scope in raw_scopes):
            continue
        valid[stimulus_id] = list(raw_scopes)

    return requested, valid


def strategies_for_stimuli(
    supabase: Any,
    stimulus_scopes: dict[str, list[dict]],
    *,
    strict: bool = False,
) -> dict[str, list[dict]]:
    """Return verified active strategies for canonical PYQ stimuli.

    ``stimulus_scopes`` maps each ``pyq_stimuli.id`` to the COMPLETE frozen topic
    scopes of every question displayed with that stimulus. A set strategy is
    admitted only when its governed scope matches EVERY question in the set. The
    reader performs one link query and one strategy query for the whole review
    payload. Malformed or incomplete scope groups fail closed to ``[]``.
    """
    out, scopes = _normalise_stimulus_scopes(stimulus_scopes)
    if not scopes:
        return out

    stimulus_ids = sorted(scopes)
    link_rows = _read(
        lambda: supabase.table(_STIMULUS_LINKS)
        .select("stimulus_id,strategy_id,relevance")
        .in_("stimulus_id", stimulus_ids)
        .eq("reviewer_status", "verified")
        .execute(),
        strict,
    )
    links = getattr(link_rows, "data", None) or []
    if not links:
        return out

    strategy_ids = sorted(
        {
            link.get("strategy_id")
            for link in links
            if isinstance(link, dict) and link.get("strategy_id")
        }
    )
    if not strategy_ids:
        return out

    strat_rows = _read(
        lambda: supabase.table(_STRATEGIES)
        .select(_STRATEGY_FIELDS)
        .in_("id", strategy_ids)
        .eq("reviewer_status", "verified")
        .eq("is_active", True)
        .execute(),
        strict,
    )
    strat_by_id = {
        row["id"]: row
        for row in (getattr(strat_rows, "data", None) or [])
        if isinstance(row, dict) and row.get("id")
    }

    for link in links:
        if not isinstance(link, dict):
            continue
        raw_stimulus_id = link.get("stimulus_id")
        if not raw_stimulus_id:
            continue
        stimulus_id = str(raw_stimulus_id)
        strategy = strat_by_id.get(link.get("strategy_id"))
        question_scopes = scopes.get(stimulus_id)
        if (
            question_scopes
            and strategy is not None
            and all(_scope_matches(strategy, scope) for scope in question_scopes)
        ):
            out[stimulus_id].append(
                {
                    **_learner_row(strategy),
                    "relevance": link.get("relevance") or "related",
                }
            )

    for stimulus_id in out:
        out[stimulus_id].sort(key=_display_key)
    return out


def strategies_for_question(supabase: Any, question_id: str) -> list[dict]:
    """Compatibility wrapper over the batched verified-only authority."""
    if not question_id:
        return []
    return strategies_for_questions(supabase, [question_id]).get(question_id, [])


def review_strategy(
    supabase: Any,
    *,
    strategy_id: str,
    expected_status: str,
    expected_updated_at: str,
    new_status: str,
    reviewer_notes: str | None,
    reason: str,
    actor_user_id: str,
    actor_email: str | None,
) -> dict:
    """Transition a strategy's reviewer_status via the audited lifecycle RPC.

    The RPC (migration 262) owns the transition matrix, dual optimistic-
    concurrency (CAS on BOTH ``expected_status`` and ``expected_updated_at`` — the
    content-revision token, so a reviewer can never verify a revision they did not
    read), the mandatory 8–500 char audit ``reason``, and the audit row. This
    wrapper only marshals params and returns the RPC's JSON result. Raises on RPC
    error (invalid transition, stale expected status, stale content token, invalid
    reason, missing actor) — callers surface those as 4xx.
    """
    res = supabase.rpc(
        "cms_review_reasoning_strategy",
        {
            "p_strategy_id": strategy_id,
            "p_expected_status": expected_status,
            "p_expected_updated_at": expected_updated_at,
            "p_new_status": new_status,
            "p_reviewer_notes": reviewer_notes,
            "p_reason": reason,
            "p_actor_user_id": actor_user_id,
            "p_actor_email": actor_email,
        },
    ).execute()
    return getattr(res, "data", None) or {}
