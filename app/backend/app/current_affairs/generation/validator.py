"""Stage D — deterministic MCQ validation (code, NOT AI).

The single gate that decides whether a generated candidate is ``review_ready`` (an
operator may see it) or ``validation_failed`` (never surfaced for review). Per
current-affairs-pipeline.md §5 Stage D, this is pure code — the LLM verifier (Stage C)
is advisory only and can never approve a candidate.

Pure and side-effect free: the worker gathers the DB context (claims, evidence,
source authority, existing fingerprints) and passes it in, so this module is fully
unit-testable without a database.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ADR 0007: an aggregator / discovery_only source may never be the SOLE evidence for
# a promotable question.
DISCOVERY_ONLY = "discovery_only"

_VALID_OPTION_IDS = ("a", "b", "c", "d")
_VALID_DIFFICULTY = frozenset({"easy", "medium", "hard"})

# Unqualified time-relative wording bans a question from review — a current-affairs
# question must be self-dating ("in June 2026", not "recently"), or its answer decays
# silently after promotion. Matched case-insensitively as whole words.
_UNQUALIFIED_TIME_WORDS = (
    "currently", "recently", "latest", "nowadays", "at present", "these days",
    "just announced", "newly",
)
_UNQUALIFIED_TIME_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _UNQUALIFIED_TIME_WORDS) + r")\b",
    re.IGNORECASE,
)


@dataclass
class ValidationResult:
    """Verdict for one candidate. ``ok`` gates ``review_ready`` vs ``validation_failed``."""

    ok: bool
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "failures": list(self.failures)}


def _norm(text: str | None) -> str:
    return (text or "").strip().lower()


def _option_texts(payload: dict[str, Any]) -> list[str]:
    return [str((o or {}).get("text") or "").strip() for o in payload.get("options") or []]


def validate_candidate(
    payload: dict[str, Any],
    *,
    claims_by_id: dict[str, dict[str, Any]],
    evidence_by_claim: dict[str, list[dict[str, Any]]],
    source_authority_by_document: dict[str, str],
    event: dict[str, Any] | None = None,
    existing_fingerprints: frozenset[str] = frozenset(),
) -> ValidationResult:
    """Enforce every §5 Stage-D rule. Accumulates ALL failures (not fail-fast) so the
    operator/audit sees the full reason set.

    - ``claims_by_id``: claim_id -> claim row (needs ``factual_status``).
    - ``evidence_by_claim``: claim_id -> list of evidence rows (needs ``document_id``,
      ``evidence_text``).
    - ``source_authority_by_document``: document_id -> ``authority_level``.
    - ``event``: the parent event row (needs ``event_date`` / ``relevance_*``).
    - ``existing_fingerprints``: fingerprints already present in candidates/bank.
    """
    failures: list[str] = []

    # --- structural MCQ shape -------------------------------------------------
    options = payload.get("options") or []
    if len(options) != 4:
        failures.append("must_have_exactly_four_options")
    option_ids = [str((o or {}).get("id") or "").strip().lower() for o in options]
    if sorted(option_ids) != list(_VALID_OPTION_IDS) and len(options) == 4:
        failures.append("option_ids_must_be_a_b_c_d")

    texts = _option_texts(payload)
    if any(not t for t in texts):
        failures.append("empty_option_text")
    norm_texts = [_norm(t) for t in texts]
    if len(set(norm_texts)) != len(norm_texts):
        failures.append("duplicate_options")
    # "all/none of the above" style options are not single-correct safe.
    if any(re.search(r"\b(all|none|both)\s+of\s+the\s+(above|these)\b", t) for t in norm_texts):
        failures.append("meta_option_not_allowed")

    correct = _norm(payload.get("correct_option_id"))
    if correct not in _VALID_OPTION_IDS:
        failures.append("correct_option_id_invalid")
    elif len(options) == 4 and correct not in option_ids:
        failures.append("correct_option_not_among_options")

    if not str(payload.get("stem") or "").strip():
        failures.append("empty_stem")
    explanation = str(payload.get("explanation") or "").strip()
    if not explanation:
        failures.append("empty_explanation")

    difficulty = _norm(payload.get("difficulty"))
    if difficulty and difficulty not in _VALID_DIFFICULTY:
        failures.append("invalid_difficulty")

    # --- answer leakage: the correct option must not be given away by the stem ---
    if len(texts) == 4 and all(texts) and correct in _VALID_OPTION_IDS and correct in option_ids:
        correct_norm = _norm(texts[option_ids.index(correct)])
        stem_norm = _norm(payload.get("stem"))
        if correct_norm and len(correct_norm) >= 4 and correct_norm in stem_norm:
            failures.append("answer_leaked_in_stem")

    # --- time-dependent / self-dating wording ---------------------------------
    scan_text = " ".join([str(payload.get("stem") or ""), *texts, explanation])
    if _UNQUALIFIED_TIME_RE.search(scan_text):
        failures.append("unqualified_time_reference")

    # --- evidence linkage (answer must be grounded) ---------------------------
    linked = [str(c) for c in (payload.get("linked_claim_ids") or []) if c]
    if not linked:
        failures.append("no_linked_claim")
    unknown_claims = [c for c in linked if c not in claims_by_id]
    if unknown_claims:
        failures.append("linked_claim_not_found")
    # No superseded/corrected/disputed claim may back a candidate.
    if any(
        _norm(claims_by_id.get(c, {}).get("factual_status")) not in ("", "current")
        for c in linked
        if c in claims_by_id
    ):
        failures.append("superseded_or_noncurrent_claim")

    # --- ADR 0007: not solely backed by a discovery_only/inactive source ------
    if linked and not unknown_claims:
        authorities: set[str] = set()
        for c in linked:
            for ev in evidence_by_claim.get(c, []):
                lvl = _norm(source_authority_by_document.get(str(ev.get("document_id"))))
                if lvl:
                    authorities.add(lvl)
        if not authorities:
            failures.append("no_resolvable_evidence_source")
        elif authorities == {DISCOVERY_ONLY}:
            failures.append("sole_evidence_discovery_only")

    # --- event / relevance dates ---------------------------------------------
    if event is not None:
        if not event.get("event_date"):
            failures.append("event_missing_date")
        rf, ru = event.get("relevance_from"), event.get("relevance_until")
        if rf and ru and str(ru) < str(rf):
            failures.append("relevance_window_inverted")

    # --- duplicate fingerprint -----------------------------------------------
    fp = str(payload.get("question_fingerprint") or "").strip()
    if fp and fp in existing_fingerprints:
        failures.append("duplicate_question_fingerprint")

    # Deduplicate while preserving order.
    seen: set[str] = set()
    ordered = [f for f in failures if not (f in seen or seen.add(f))]
    return ValidationResult(ok=not ordered, failures=ordered)
