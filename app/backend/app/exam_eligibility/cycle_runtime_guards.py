"""Fail-closed runtime guards for cycle-scoped exam eligibility.

The cycle layer is additive to the stable baseline evaluator. These guards keep
that shared evaluator API intact while enforcing two cycle-only invariants:

* an unresolved authoritative age cut-off cannot be hidden by another passing
  rule; and
* the summary profile includes the recorded experience used by
  ``experience_min_years``.

Installed from :mod:`app.exam_eligibility` before callers import the evaluator
surface. Remove this adapter when the same guards are folded into the evaluator
implementation directly.
"""
from __future__ import annotations

from functools import wraps
from math import isfinite
from typing import Any


_UNRESOLVED_CUTOFF_REASON = (
    "This cycle's cut-off date isn't published yet, so age can't be verified."
)


def _unknown(
    evaluator: Any, result: dict[str, Any], *, cutoff_unresolved: bool = False
) -> dict[str, Any]:
    # Surface a concrete cause for an unresolved-cut-off unknown so the UI never
    # mislabels it "verified rules missing" (verified rules ARE present here).
    reasons = list(result.get("reasons") or [])
    if cutoff_unresolved and not reasons:
        reasons.append(_UNRESOLVED_CUTOFF_REASON)
    return evaluator._decision(  # noqa: SLF001 - package-internal adapter
        "unknown",
        reasons,
        list(result.get("missing_fields") or []),
    )


def install_cycle_runtime_guards(evaluator: Any) -> None:
    """Install the cycle-only fail-closed guards exactly once."""
    if getattr(evaluator, "_CYCLE_RUNTIME_GUARDS_INSTALLED", False):
        return

    original_evaluate = evaluator.evaluate_exam_for_user
    original_load_profile = evaluator._load_user_profile  # noqa: SLF001

    @wraps(original_evaluate)
    def guarded_evaluate(
        rules: list[dict[str, Any]],
        profile: dict[str, Any],
        *,
        reference_date=None,
        cutoff_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if cutoff_context is None:
            return original_evaluate(rules, profile, reference_date=reference_date)

        scopes = evaluator._user_scopes(profile)  # noqa: SLF001
        cycle = cutoff_context.get("cycle") if isinstance(cutoff_context, dict) else None
        unresolved_types: set[str] = set()
        # Distinguish an unresolved authoritative cut-off (a real, explainable
        # cause) from a malformed threshold, so the unknown can carry a reason.
        cutoff_unresolved = False

        for rule_type in ("age_min", "age_max"):
            rule = evaluator._pick_rule(rules, rule_type, scopes)  # noqa: SLF001
            if not rule:
                continue
            try:
                int(rule["value_num"])
            except (KeyError, TypeError, ValueError):
                unresolved_types.add(rule_type)
                continue
            if evaluator._resolve_cutoff_date(rule, cycle) is None:  # noqa: SLF001
                unresolved_types.add(rule_type)
                cutoff_unresolved = True

        experience_rule = evaluator._pick_rule(  # noqa: SLF001
            rules, "experience_min_years", scopes
        )
        if experience_rule:
            try:
                required_experience = float(experience_rule.get("value_num"))
            except (TypeError, ValueError):
                unresolved_types.add("experience_min_years")
            else:
                if not isfinite(required_experience) or required_experience < 0:
                    unresolved_types.add("experience_min_years")

        # Remove the unresolved dimension before delegating. This prevents a
        # malformed threshold from raising and prevents a less-specific fallback
        # rule of the same type from replacing the selected unresolved rule.
        evaluable_rules = [
            rule for rule in rules if rule.get("rule_type") not in unresolved_types
        ]
        result = original_evaluate(
            evaluable_rules,
            profile,
            reference_date=reference_date,
            cutoff_context=cutoff_context,
        )

        # A concrete knockout remains authoritative. Otherwise any unresolved
        # system-side prerequisite keeps the cycle claim unknown, even when a
        # different rule passed or only user fields are missing.
        if unresolved_types and result.get("status") != "not_eligible":
            return _unknown(evaluator, result, cutoff_unresolved=cutoff_unresolved)
        return result

    @wraps(original_load_profile)
    def guarded_load_profile(supabase: Any, user_id: str) -> dict[str, Any]:
        profile = original_load_profile(supabase, user_id)
        rows = evaluator._safe(  # noqa: SLF001
            lambda: (
                supabase.table("aspirant_experience")
                .select("years_experience")
                .eq("user_id", user_id)
                .limit(50)
                .execute()
                .data
            ),
            default=None,
        )
        if rows is None:
            return profile

        total = 0.0
        found = False
        for row in rows:
            try:
                years = float(row.get("years_experience"))
            except (AttributeError, TypeError, ValueError):
                continue
            if not isfinite(years) or years < 0:
                continue
            total += years
            found = True
        if found:
            profile["experience_years"] = total
        return profile

    evaluator.evaluate_exam_for_user = guarded_evaluate
    evaluator._load_user_profile = guarded_load_profile  # noqa: SLF001
    evaluator._CYCLE_RUNTIME_GUARDS_INSTALLED = True
