"""Quant heuristic authority — verified-only reads + review wrapper (GQR-Q7).

Content Studio authors and reviews ``quant_heuristics`` (migration 243). This
module is the read/selection authority the learner-feedback path uses, plus a
thin wrapper over the ``cms_review_quant_heuristic`` lifecycle RPC.

Domain rule (CLAUDE.md): user-facing reads filter ``reviewer_status='verified'``
CONJUNCTIVELY. A heuristic reaches a learner only when BOTH the heuristic row and
its question link are verified — and the heuristic is active. The reviewed link
must also connect a question whose topic/microtopic is compatible with the
heuristic's governed scope; this prevents a misassigned Quant link from leaking
onto a different subject's question.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger("career_copilot.study_os.quant_heuristics")

_HEURISTICS = "quant_heuristics"
_LINKS = "quant_question_heuristics"

# Learner-facing display order for a question's heuristics.
_RELEVANCE_RANK = {"primary": 0, "secondary": 1, "related": 2}

# Fetch the content fields used by the learner projection plus the internal scope
# fields needed to validate that the reviewed link targets a compatible question.
# Governance fields such as applicability_rule, reviewer notes/actors, timestamps,
# and audit/CAS metadata never cross this authority boundary.
_CONTENT_KEYS = (
    "id",
    "name",
    "heuristic_type",
    "formula_latex",
    "standard_method",
    "shortcut_method",
    "worked_example",
    "common_traps",
)
_INTERNAL_SCOPE_KEYS = ("topic_id", "microtopic_id")
_HEURISTIC_FIELDS = ",".join((*_CONTENT_KEYS, *_INTERNAL_SCOPE_KEYS))


def _safe(call: Callable[[], Any], default: Any = None) -> Any:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("db_op_failed op=quant_heuristics err=%r", exc)
        return default


def _display_key(h: dict) -> tuple:
    """Stable learner display order: relevance, normalized name, then id."""
    return (
        _RELEVANCE_RANK.get(h.get("relevance"), 99),
        (h.get("name") or "").lower(),
        str(h.get("id") or ""),
    )


def _learner_row(row: dict) -> dict:
    """Defense-in-depth allowlist for the batched learner authority."""
    return {key: row.get(key) for key in _CONTENT_KEYS}


def _scope_matches(heuristic: dict, question: Any) -> bool:
    """Fail closed unless every populated heuristic scope dimension matches.

    When both topic and microtopic are stored, both must match. This avoids
    trusting that historical or operator-authored rows always carry a consistent
    parent/child pair, while still supporting topic-only and microtopic-only
    strategies. Topic IDs are canonical, subject-owned rows, so a mismatch also
    blocks a Quant strategy linked to a Reasoning/English question.
    """
    if not isinstance(question, dict):
        return False
    heuristic_topic = heuristic.get("topic_id")
    heuristic_microtopic = heuristic.get("microtopic_id")
    if not heuristic_topic and not heuristic_microtopic:
        return False
    if heuristic_topic and str(question.get("topic_id") or "") != str(heuristic_topic):
        return False
    if (
        heuristic_microtopic
        and str(question.get("microtopic_id") or "") != str(heuristic_microtopic)
    ):
        return False
    return True


def heuristics_for_questions(
    supabase: Any, question_ids: list[str]
) -> dict[str, list[dict]]:
    """Return verified active heuristics for every requested question id.

    Uses at most ONE link query and ONE heuristic query regardless of how many
    question ids are passed (no N+1). The link query embeds the referenced bank
    question's topic scope, so the gate is conjunctive:

      link verified AND heuristic verified AND heuristic active AND scope match.

    Every requested id is present with at least ``[]``; rows never cross-leak
    between questions or subjects. Only learner content fields plus per-link
    relevance leave this authority, ordered deterministically by relevance, name,
    then id.

    Optional strategy content is fail-soft: a database read failure returns the
    initialized empty mapping so the primary review response remains available.
    """
    ids = [q for q in dict.fromkeys(question_ids or []) if q]
    out: dict[str, list[dict]] = {q: [] for q in ids}
    if not ids:
        return out

    link_rows = _safe(
        lambda: supabase.table(_LINKS)
        .select(
            "question_id,heuristic_id,relevance,"
            "question:mock_question_bank!inner(topic_id,microtopic_id)"
        )
        .in_("question_id", ids)
        .eq("reviewer_status", "verified")
        .execute(),
        default=None,
    )
    links = getattr(link_rows, "data", None) or []
    if not links:
        return out

    heuristic_ids = sorted(
        {
            link.get("heuristic_id")
            for link in links
            if isinstance(link, dict) and link.get("heuristic_id")
        }
    )
    if not heuristic_ids:
        return out

    heur_rows = _safe(
        lambda: supabase.table(_HEURISTICS)
        .select(_HEURISTIC_FIELDS)
        .in_("id", heuristic_ids)
        .eq("reviewer_status", "verified")
        .eq("is_active", True)
        .execute(),
        default=None,
    )
    heur_by_id = {
        row["id"]: row
        for row in (getattr(heur_rows, "data", None) or [])
        if isinstance(row, dict) and row.get("id")
    }

    for link in links:
        if not isinstance(link, dict):
            continue
        question_id = link.get("question_id")
        heuristic = heur_by_id.get(link.get("heuristic_id"))
        if (
            question_id in out
            and heuristic is not None
            and _scope_matches(heuristic, link.get("question"))
        ):
            # Copy per question so the same heuristic may carry different reviewed
            # relevance without shared mutation across output lists.
            out[question_id].append(
                {
                    **_learner_row(heuristic),
                    "relevance": link.get("relevance") or "related",
                }
            )

    for question_id in out:
        out[question_id].sort(key=_display_key)
    return out


def heuristics_for_question(supabase: Any, question_id: str) -> list[dict]:
    """Compatibility wrapper over the batched verified-only authority."""
    if not question_id:
        return []
    return heuristics_for_questions(supabase, [question_id]).get(question_id, [])


def list_verified_heuristics_for_topic(
    supabase: Any, *, topic_id: str | None = None, microtopic_id: str | None = None
) -> list[dict]:
    """Verified + active heuristics scoped to a topic or microtopic.

    At least one of ``topic_id`` / ``microtopic_id`` must be supplied; passing
    neither returns ``[]`` rather than scanning the whole table.
    """
    if not topic_id and not microtopic_id:
        return []
    q = (
        supabase.table(_HEURISTICS)
        .select("*")
        .eq("reviewer_status", "verified")
        .eq("is_active", True)
    )
    if microtopic_id:
        q = q.eq("microtopic_id", microtopic_id)
    elif topic_id:
        q = q.eq("topic_id", topic_id)
    rows = _safe(lambda: q.execute(), default=None)
    heuristics = getattr(rows, "data", None) or []
    return sorted(
        heuristics,
        key=lambda h: ((h.get("name") or "").lower(), str(h.get("id") or "")),
    )


def review_heuristic(
    supabase: Any,
    *,
    heuristic_id: str,
    expected_status: str,
    expected_updated_at: str,
    new_status: str,
    reviewer_notes: str | None,
    reason: str,
    actor_user_id: str,
    actor_email: str | None,
) -> dict:
    """Transition a heuristic's reviewer_status via the audited lifecycle RPC.

    The RPC (migration 246, replacing 243) owns the transition matrix, dual
    optimistic-concurrency (CAS on BOTH ``expected_status`` and
    ``expected_updated_at`` — the content-revision token, so a reviewer can never
    verify a revision they did not read), the mandatory 8–500 char audit
    ``reason``, and the audit row. This wrapper only marshals params and returns
    the RPC's JSON result. Raises on RPC error (invalid transition, stale expected
    status, stale content token, invalid reason, missing actor) — callers surface
    those as 4xx.
    """
    res = supabase.rpc(
        "cms_review_quant_heuristic",
        {
            "p_heuristic_id": heuristic_id,
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
