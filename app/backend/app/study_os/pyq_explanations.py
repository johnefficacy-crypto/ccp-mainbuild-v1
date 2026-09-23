"""PYQ explanations — learner-safe structured explanation projection (EXPL-READ-01).

Contract: docs/architecture/pyq-explanations.md.

``pyq_question_explanations`` carries its OWN review lifecycle, independent of the
question's. This module is the single place that gate is applied on the read side:
only ``reviewer_status='verified'`` rows leave here, so ``pending``, ``rejected``
and ``needs_correction`` can never reach an aspirant.

Guarantees, deliberately mirroring the GQR-S1 solution-strategy reader
(``app/study_os/solution_strategies.py``) that ``get_review`` already uses:

  * verified-only gate, applied in ONE place (:func:`_verified_rows`),
  * LIVE read at review time — never frozen into ``question_snapshot``, so an
    explanation later unverified disappears from subsequent review reads, and a
    newly verified one reaches attempts that were taken before it existed,
  * only the fields in :data:`ALLOWED_FIELDS` reach the learner payload;
    governance and provenance columns (``reviewer_status``, ``reviewed_by``,
    ``reviewed_at``, ``license_status``, ``source_url``, ``source_document_id``,
    ``source_hash``, ``ambiguity_status``, ``metadata``) are dropped by
    CONSTRUCTION in :func:`_project`, not merely omitted by the caller,
  * fail-soft review delivery: a source read failure yields no explanations and
    never breaks the review response.

Keying note. ``pyq_question_explanations.question_id`` references
``pyq_questions(id)``, NOT ``mock_question_bank(id)``. Callers hold bank ids, so
they map through ``question_snapshot.pyq_question_id`` (frozen at attempt start by
``mock_engine._question_snapshot``). Authored, non-PYQ questions carry no
``pyq_question_id`` and are simply absent from the result.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("career_copilot.study_os.pyq_explanations")

# The learner-safe DTO. NO governance or provenance field may ever appear here.
# This tuple is the contract the frontend and tests assert against.
ALLOWED_FIELDS = (
    "id",
    "short_explanation",
    "explanation_text",
    "solution_steps",
    "option_rationales",
    "formula_used",
    "common_traps",
)

# Columns read from the source table. `explanation_source_type` is read for the
# deterministic tie-break below and is NOT projected into the DTO.
_SELECT = (
    "id,question_id,explanation_source_type,short_explanation,explanation_text,"
    "solution_steps,option_rationales,formula_used,common_traps"
)


def _safe(call, default=None):
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("pyq_explanations supabase call failed: %s", exc)
        return default


def _as_list(value: Any) -> list:
    """jsonb array column → list. Anything else (null, dict, scalar) → []."""
    return value if isinstance(value, list) else []


def _pick(rows: list[dict]) -> dict:
    """Pick ONE explanation row for a question, deterministically.

    ``unique (question_id, explanation_source_type)`` allows several rows per
    question, but today exactly one source type is populated, so there is no
    precedence mechanism here on purpose — building one would mean inventing a
    product decision that has not been made.

    OPEN DECISION: the ranking among source types when more than one is verified
    for the same question. `docs/architecture/pyq-explanations.md:130-134` requires
    "an explicit precedence over explanation_source_type… not by taking the first
    row" but specifies no order, and no code in the repo implements one (see
    `workbench/reports/EXPL-SURFACE-01-FINDINGS.md`, "Precedent for choosing among
    multiple candidate rows"). Until that order is decided, this sorts by
    (explanation_source_type, id) purely so the choice is STABLE across requests
    rather than dependent on PostgREST row order. That is a tie-break, not a
    precedence: do not read the alphabetical order as a product ranking.
    """
    return sorted(
        rows,
        key=lambda r: (str(r.get("explanation_source_type") or ""), str(r.get("id") or "")),
    )[0]


def _option_index_by_pyq_option_id(supabase: Any, pyq_question_ids: list[str]) -> dict[str, int]:
    """Map ``pyq_options.id`` → the ``option_index`` its projected twin carries.

    ``option_rationales`` is keyed by ``pyq_options.id``, but the projection
    (`272_pyq_projection_bytea_cast_fix.sql:547-562`) inserts each
    ``mock_question_options`` row with a FRESH uuid and never retains the source
    option id, so that key resolves to nothing in the frozen snapshot. The only
    field both sides carry is ``option_index``, which the projection derives as
    ``row_number() over (order by option_label, id) - 1`` across the question's
    VERIFIED options. This reproduces that derivation so the rationale can be
    lined up with the option it belongs to.

    Caveat, accepted: the index is recomputed from options verified NOW, while the
    snapshot froze the ordering that held at projection time. If an option's
    verification changed in between, the indices can drift and a rationale would
    line up with the wrong option. Guarded at the call site by dropping any
    rationale whose index is out of range for the frozen option list; a stronger
    fix is migration 307 (EXPL-OPTID-01), which carries ``pyq_option_id`` onto
    every projected option row. This derivation is now the FALLBACK, used only
    for rows projected before 307 and for rows the 307 backfill left NULL because
    the mapping could not be established unambiguously. It stays until the
    backfill is complete enough to drop it; removing it is not part of 307.
    """
    rows = getattr(
        _safe(
            lambda: supabase.table("pyq_options")
            .select("id,question_id,option_label")
            .in_("question_id", pyq_question_ids)
            .eq("reviewer_status", "verified")
            .execute(),
            default=None,
        ),
        "data",
        None,
    ) or []

    by_question: dict[str, list[dict]] = {}
    for row in rows:
        qid = row.get("question_id")
        if qid:
            by_question.setdefault(qid, []).append(row)

    out: dict[str, int] = {}
    for options in by_question.values():
        ordered = sorted(
            options,
            key=lambda o: (str(o.get("option_label") or ""), str(o.get("id") or "")),
        )
        for index, option in enumerate(ordered):
            if option.get("id"):
                out[str(option["id"])] = index
    return out


def _project_option_rationales(raw: Any, index_by_option_id: dict[str, int]) -> list[dict]:
    """``{pyq_option_id: text}`` → an ordered list the frontend can join on.

    Returns ``[{"pyq_option_id": str, "option_index": int | None, "rationale": str}, …]``
    sorted by ``option_index``, with unresolvable positions carried through at
    ``option_index=None`` and sorted last rather than discarded here — a consumer
    that can resolve the option by ``pyq_option_id`` does not need the position at
    all, and one with no frozen option list may still have somewhere to put them.

    ``pyq_option_id`` is INTERNAL to this join. It is the identity key migration
    307 put on ``mock_question_options``, and the consumer joins on it in
    preference to ``option_index``; it is stripped before the payload reaches a
    learner (``mock_engine._explanation_for_snapshot``), which also drops any
    rationale left with no option on the review screen to sit against.
    """
    if not isinstance(raw, dict):
        return []
    out: list[dict] = []
    for option_id, rationale in raw.items():
        if not isinstance(rationale, str) or not rationale.strip():
            continue
        out.append(
            {
                "pyq_option_id": str(option_id),
                "option_index": index_by_option_id.get(str(option_id)),
                "rationale": rationale,
            }
        )
    out.sort(key=lambda r: (r["option_index"] is None, r["option_index"] or 0))
    return out


def _project(row: dict, index_by_option_id: dict[str, int]) -> dict:
    """Governed row → the learner DTO, built from an explicit allowlist so a
    governance or provenance column present on the source row can never leak."""
    return {
        "id": row.get("id"),
        "short_explanation": row.get("short_explanation"),
        "explanation_text": row.get("explanation_text"),
        "solution_steps": _as_list(row.get("solution_steps")),
        "option_rationales": _project_option_rationales(
            row.get("option_rationales"), index_by_option_id
        ),
        "formula_used": _as_list(row.get("formula_used")),
        "common_traps": _as_list(row.get("common_traps")),
    }


def _verified_rows(supabase: Any, pyq_question_ids: list[str], *, strict: bool) -> list[dict]:
    """THE gate. Every explanation that leaves this module passes through here."""
    call = (
        lambda: supabase.table("pyq_question_explanations")
        .select(_SELECT)
        .in_("question_id", pyq_question_ids)
        .eq("reviewer_status", "verified")
        .execute()
    )
    res = call() if strict else _safe(call, default=None)
    return getattr(res, "data", None) or []


def explanations_for_pyq_questions(
    supabase: Any, pyq_question_ids: list[str], *, strict: bool = False
) -> dict[str, dict]:
    """Return one verified explanation DTO per PYQ question that has one.

    At most TWO queries regardless of how many ids are passed (no N+1): the
    explanation read, and the option-index read used to line up
    ``option_rationales``. The second is skipped when no verified explanation
    carries any rationale.

    Questions with no verified explanation are ABSENT from the mapping rather
    than present with an empty value, so a caller's ``.get(qid)`` is falsy and
    existing behaviour is unchanged for them.

    ``strict=False`` (the mock-review consumer) is fail-soft: a read failure
    returns ``{}`` so the review response stays available. ``strict=True`` lets
    the failure propagate for any future standalone feed that must tell a real
    outage apart from "nothing verified".
    """
    ids = [q for q in dict.fromkeys(pyq_question_ids or []) if q]
    if not ids:
        return {}

    rows = _verified_rows(supabase, ids, strict=strict)
    if not rows:
        return {}

    by_question: dict[str, list[dict]] = {}
    for row in rows:
        qid = row.get("question_id")
        if qid:
            by_question.setdefault(str(qid), []).append(row)
    if not by_question:
        return {}

    # Only pay for the option read when something actually needs the join.
    needs_options = any(
        isinstance(row.get("option_rationales"), dict) and row["option_rationales"]
        for row in rows
    )
    index_by_option_id = (
        _option_index_by_pyq_option_id(supabase, sorted(by_question)) if needs_options else {}
    )

    return {
        qid: _project(_pick(question_rows), index_by_option_id)
        for qid, question_rows in by_question.items()
    }
