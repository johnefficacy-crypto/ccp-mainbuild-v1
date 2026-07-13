"""Exam-level baseline eligibility evaluator.

Reads the verified rows from ``exam_eligibility_rules`` and a small slice
of the user's profile and decides one of four outcomes per exam:

  * ``eligible``     — every applicable rule passes on the data we have.
  * ``conditional``  — every rule we *could* check passes, but at least
                       one applicable rule needs a field we don't have yet.
  * ``not_eligible`` — at least one is_knockout rule fails on data we have.
  * ``unknown``      — no rule is checkable yet (no profile data overlaps
                       with any applicable rule).

The four states map to the product decision discussed in the spec: only
``eligible`` and ``conditional`` are shown to users at onboarding; the
others either drop trust (``not_eligible``) or carry no signal yet
(``unknown``).

This module never writes data, never decides verdicts at the recruitment
level, and never raises into a request — its caller wraps any DB error.
"""
from __future__ import annotations

import logging
import re
from datetime import date
from typing import Any, Iterable

from cachetools import TTLCache

logger = logging.getLogger("career_copilot.exam_eligibility.evaluator")


# Verified rules change rarely (admin-mutable, but only on approval). A
# 10-minute in-process cache cuts the dashboard fan-out cost without
# making stale data outlive a reviewer's edit by more than the TTL.
# Admin writers in ``app/api/admin_exam_eligibility.py`` must call
# :func:`invalidate_eligibility_rules_cache` after they mutate the
# table.
_RULES_CACHE: TTLCache = TTLCache(maxsize=128, ttl=600)


def invalidate_eligibility_rules_cache() -> None:
    """Drop the verified-rules cache. Call after admin writes."""
    _RULES_CACHE.clear()


# Ordered enum used by the ``education_min_level`` rule. A user with the
# value at index N satisfies any rule asking for level at index ≤ N.
_EDUCATION_LEVEL_ORDER: tuple[str, ...] = (
    "10th",
    "12th",
    "diploma",
    "graduation",
    "post_graduation",
    "phd",
)


def _education_rank(level: str | None) -> int | None:
    if not level:
        return None
    try:
        return _EDUCATION_LEVEL_ORDER.index(level.lower().strip())
    except ValueError:
        return None


def _age_in_years(dob: str | None, reference: date | None = None) -> int | None:
    if not dob:
        return None
    try:
        born = date.fromisoformat(str(dob)[:10])
    except ValueError:
        return None
    ref = reference or date.today()
    years = ref.year - born.year - ((ref.month, ref.day) < (born.month, born.day))
    return years


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    return text or None


def _user_scopes(profile: dict[str, Any]) -> list[str]:
    """Scopes that potentially apply to this user, most-specific first.

    For category-driven rules, the most specific scope wins. PWD overrides
    category (matches the typical product policy of "PWD relaxation is
    more lenient than category relaxation").
    """
    scopes: list[str] = []
    pwbd = _normalize_text(profile.get("pwbd_status"))
    is_pwd = pwbd not in (None, "", "none", "no", "false")
    if is_pwd:
        scopes.append("pwd")
    cat = _normalize_text(profile.get("category"))
    if cat in {"general", "obc", "sc", "st", "ews"}:
        scopes.append(cat)
    if profile.get("ex_serviceman"):
        scopes.append("ex_serviceman")
    gender = _normalize_text(profile.get("gender"))
    if gender in {"female", "woman", "women"}:
        scopes.append("women")
    # ``all`` is always a fallback.
    scopes.append("all")
    return scopes


def _pick_rule(
    rules: list[dict[str, Any]], rule_type: str, user_scopes: Iterable[str]
) -> dict[str, Any] | None:
    """Return the rule whose scope best matches the user, or None.

    Walks ``user_scopes`` in most-specific-first order; the first rule
    found wins. Falls through to ``all`` as the implicit baseline if
    nothing more specific was set up.
    """
    by_scope = {r.get("scope"): r for r in rules if r.get("rule_type") == rule_type}
    for scope in user_scopes:
        if scope in by_scope:
            return by_scope[scope]
    return None


def _rules_for_stream(
    rules: list[dict[str, Any]], stream_id: str | None
) -> list[dict[str, Any]]:
    """Merge common (stream_id NULL) rules with one stream's rules.

    A stream-specific rule OVERRIDES the common rule for the same
    (rule_type, scope). ``stream_id=None`` returns only the common rules
    (the exam-wide baseline, unchanged behaviour).
    """
    common = [r for r in rules if r.get("stream_id") is None]
    if stream_id is None:
        return common
    stream_rules = [r for r in rules if r.get("stream_id") == stream_id]
    if not stream_rules:
        return common
    override = {(r.get("rule_type"), r.get("scope")) for r in stream_rules}
    merged = [r for r in common if (r.get("rule_type"), r.get("scope")) not in override]
    merged.extend(stream_rules)
    return merged


# ── Atomic requirement evaluation (used by the new rule_types and by the
#    qualification_combination clauses). Each returns a tri-state so the
#    four-state contract (eligible/conditional/not_eligible/unknown) holds:
#      'pass'    — the requirement is satisfied on data we have.
#      'fail'    — the requirement is contradicted on data we have.
#      'missing' — we lack the field needed to decide.

def _tokens(values: Iterable[Any]) -> set[str]:
    out: set[str] = set()
    for v in values:
        t = _normalize_text(v)
        if t:
            out.add(t)
    return out


# Alias sets for short discipline acronyms so boundary matching still resolves
# "IT" ↔ "information technology" without the substring false-positives the
# checkpost flagged (required "it" must NOT match "statistics").
_DISCIPLINE_ALIASES: dict[str, set[str]] = {
    "it": {"it", "information technology"},
    "cs": {"cs", "computer science"},
    "ca": {"ca", "chartered accountant", "chartered accountancy"},
    "cma": {"cma", "cost accountant", "cost and management accountant"},
    "llb": {"llb", "ll.b", "law", "bachelor of law", "bachelor of laws"},
    "law": {"law", "llb", "ll.b", "bachelor of law", "bachelor of laws"},
    "cfa": {"cfa", "chartered financial analyst"},
    "eng": {"engineering", "b.e", "b.tech", "be", "btech"},
}


_CERT_ALIASES: dict[str, set[str]] = {
    "ca": {"ca", "chartered accountant", "chartered accountancy"},
    "cma": {"cma", "cost accountant", "cost and management accountant"},
    "cs": {"cs", "company secretary"},
    "cfa": {"cfa", "chartered financial analyst"},
    "frm": {"frm", "financial risk manager"},
}


def _boundary_match(needle: str, field: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", field) is not None


def _alias_expanded_match(required: str, field: str, amap: dict[str, set[str]]) -> bool:
    """Boundary-aware, alias-expanded match. `required` and `field` are
    already normalized (lowercase, stripped) — no substring false positives."""
    for alias in amap.get(required, {required}):
        if _boundary_match(alias, field):
            return True
    # Symmetric: the field may itself be an acronym whose alias set holds req.
    return required in amap.get(field, set())


def _discipline_matches(required: str, field: str) -> bool:
    return _alias_expanded_match(required, field, _DISCIPLINE_ALIASES)


def _eval_discipline(required: str | None, profile: dict[str, Any]) -> str:
    req = _normalize_text(required)
    if not req:
        return "pass"  # mis-seeded rule — don't punish the user
    disciplines = profile.get("disciplines")
    if disciplines is None:
        return "missing"
    fields = [d for d in (_normalize_text(x) for x in disciplines) if d]
    if not fields:
        return "missing"
    return "pass" if any(_discipline_matches(req, f) for f in fields) else "fail"


def _eval_min_percentage(required: Any, profile: dict[str, Any]) -> str:
    if required is None:
        return "pass"
    pct = profile.get("best_percentage")
    if pct is None:
        return "missing"
    try:
        return "pass" if float(pct) >= float(required) else "fail"
    except (TypeError, ValueError):
        return "missing"


def _eval_certification(required: str | None, profile: dict[str, Any]) -> str:
    req = _normalize_text(required)
    if not req:
        return "pass"
    certs = profile.get("certifications")
    if certs is None:
        return "missing"
    have = [c for c in (_normalize_text(x) for x in certs) if c]
    if not have:
        return "fail"
    # Boundary-aware (checkpost P0): required "CA" must NOT match
    # "First Aid Certification" via substring.
    return "pass" if any(_alias_expanded_match(req, c, _CERT_ALIASES) for c in have) else "fail"


def _eval_atomic(rule_type: str, value_num: Any, value_text: Any, profile: dict[str, Any]) -> str:
    if rule_type == "discipline":
        return _eval_discipline(value_text, profile)
    if rule_type == "min_percentage":
        return _eval_min_percentage(value_num, profile)
    if rule_type == "certification":
        return _eval_certification(value_text, profile)
    if rule_type == "education_min_level":
        req_rank = _education_rank(_normalize_text(value_text))
        user_rank = _education_rank(profile.get("education_level"))
        if req_rank is None:
            return "pass"
        if user_rank is None:
            return "missing"
        return "pass" if user_rank >= req_rank else "fail"
    if rule_type == "nationality":
        req = _normalize_text(value_text)
        have = _normalize_text(profile.get("nationality"))
        if not req:
            return "pass"
        if not have:
            return "missing"
        return "pass" if have == req else "fail"
    # Unknown atomic type inside a combination — treat as unsatisfiable so a
    # mis-authored clause fails closed rather than silently passing.
    return "fail"


def _eval_qc_tree(node: Any, view: dict[str, Any]) -> str:
    """Tri-state evaluation of a {op, clauses} tree against ONE profile view."""
    if not isinstance(node, dict):
        return "fail"
    op = node.get("op")
    if op in ("and", "or"):
        results = [_eval_qc_tree(c, view) for c in node.get("clauses") or []]
        if not results:
            return "fail"
        if op == "and":
            if "fail" in results:
                return "fail"
            if "missing" in results:
                return "missing"
            return "pass"
        # or
        if "pass" in results:
            return "pass"
        if "missing" in results:
            return "missing"
        return "fail"
    return _eval_atomic(node.get("rule_type"), node.get("value_num"), node.get("value_text"), view)


def _eval_qualification_combination(node: Any, profile: dict[str, Any]) -> str:
    """Record-correlated evaluation. Discipline / min_percentage / education
    clauses that appear together in a combination must be satisfied by the SAME
    education record — so "LLB AND 60%" needs one qualification that is BOTH,
    not an LLB at 50% plus an unrelated degree at 75% (checkpost P0).

    Evaluated existentially over the user's education records: a record-scoped
    view (disciplines/percentage/level from that record) is combined with the
    global profile (nationality, certifications). Passes if any record passes;
    missing if none pass but some are undecidable; else fails.
    """
    records = profile.get("education_records")
    if not records:
        # No per-record data — evaluate once with whatever the profile has, so a
        # record-bound clause resolves to 'missing' rather than a false verdict.
        return _eval_qc_tree(node, profile)
    outcomes: list[str] = []
    for rec in records:
        view = {
            **profile,
            "disciplines": rec.get("disciplines"),
            "best_percentage": rec.get("percentage"),
            "education_level": rec.get("level"),
        }
        outcomes.append(_eval_qc_tree(node, view))
    if "pass" in outcomes:
        return "pass"
    if "missing" in outcomes:
        return "missing"
    return "fail"


def evaluate_exam_for_user(
    rules: list[dict[str, Any]],
    profile: dict[str, Any],
    *,
    reference_date: date | None = None,
) -> dict[str, Any]:
    """Decide one exam against one user profile. Pure function.

    ``rules`` is the list of verified rows for one exam. ``profile`` is the
    slimmed-down dict ``summarize_user_eligibility`` builds — we never
    touch the DB here.
    """
    if not rules:
        return {
            "status": "unknown",
            "reasons": [],
            "missing_fields": [],
        }

    scopes = _user_scopes(profile)
    user_age = _age_in_years(profile.get("date_of_birth") or profile.get("dob"), reference_date)
    user_education_rank = _education_rank(profile.get("education_level"))
    user_nationality = _normalize_text(profile.get("nationality"))
    user_gender = _normalize_text(profile.get("gender"))
    user_attempts_used = profile.get("attempts_used")

    reasons: list[str] = []
    missing: list[str] = []
    any_rule_checked = False

    # ── age_min ──
    rule = _pick_rule(rules, "age_min", scopes)
    if rule:
        if user_age is None:
            missing.append("date_of_birth")
        else:
            any_rule_checked = True
            if user_age < int(rule["value_num"]):
                reasons.append(
                    f"Age must be at least {int(rule['value_num'])} (you are {user_age})."
                )
                return _decision("not_eligible", reasons, missing)

    # ── age_max ──
    rule = _pick_rule(rules, "age_max", scopes)
    if rule:
        if user_age is None:
            missing.append("date_of_birth")
        else:
            any_rule_checked = True
            if user_age > int(rule["value_num"]):
                reasons.append(
                    f"Age must be at most {int(rule['value_num'])} for scope "
                    f"{rule.get('scope')} (you are {user_age})."
                )
                return _decision("not_eligible", reasons, missing)

    # ── education_min_level ──
    rule = _pick_rule(rules, "education_min_level", scopes)
    if rule:
        required = (rule.get("value_text") or "").lower().strip()
        required_rank = _education_rank(required)
        if user_education_rank is None:
            missing.append("education_level")
        elif required_rank is None:
            # Mis-seeded rule — ignore rather than punish the user.
            pass
        else:
            any_rule_checked = True
            if user_education_rank < required_rank:
                reasons.append(
                    f"Requires at least {required.replace('_', ' ')} education."
                )
                return _decision("not_eligible", reasons, missing)

    # ── nationality ──
    rule = _pick_rule(rules, "nationality", scopes)
    if rule:
        required = (rule.get("value_text") or "").lower().strip()
        if not user_nationality:
            missing.append("nationality")
        elif required:
            any_rule_checked = True
            if user_nationality != required:
                reasons.append(
                    f"Open to {required.title()} nationals only."
                )
                return _decision("not_eligible", reasons, missing)

    # ── gender ──
    rule = _pick_rule(rules, "gender", scopes)
    if rule:
        required = (rule.get("value_text") or "").lower().strip()
        if not user_gender:
            missing.append("gender")
        elif required:
            any_rule_checked = True
            if user_gender != required:
                reasons.append(f"Restricted to {required} candidates.")
                return _decision("not_eligible", reasons, missing)

    # ── attempts_max ──
    rule = _pick_rule(rules, "attempts_max", scopes)
    if rule and user_attempts_used is not None:
        any_rule_checked = True
        if int(user_attempts_used) >= int(rule["value_num"]):
            reasons.append(
                f"Already used {user_attempts_used} of {int(rule['value_num'])} attempts."
            )
            return _decision("not_eligible", reasons, missing)

    # ── discipline / min_percentage / certification (stream-stable facts) ──
    for rule_type, field, fail_msg in (
        ("discipline", "disciplines", "Requires a matching academic discipline"),
        ("min_percentage", "education_percentage", "Marks below the required minimum"),
        ("certification", "certifications", "Requires a specific certification"),
    ):
        rule = _pick_rule(rules, rule_type, scopes)
        if not rule:
            continue
        res = _eval_atomic(rule_type, rule.get("value_num"), rule.get("value_text"), profile)
        if res == "missing":
            missing.append(field)
        elif res == "fail" and rule.get("is_knockout", True):
            detail = rule.get("value_text") or rule.get("value_num")
            reasons.append(f"{fail_msg} ({detail}).")
            return _decision("not_eligible", reasons, missing)
        elif res == "pass":
            any_rule_checked = True

    # ── stream_availability — fail closed: only offered/expected pass; a
    #    not_offered OR any unknown/typo'd value knocks the stream out. ──
    rule = _pick_rule(rules, "stream_availability", scopes)
    if rule:
        any_rule_checked = True
        avail = _normalize_text(rule.get("value_text"))
        if avail not in ("offered", "expected") and rule.get("is_knockout", True):
            reasons.append("This stream is not offered.")
            return _decision("not_eligible", reasons, missing)

    # ── qualification_combination (structured AND/OR of the atomics) ──
    rule = _pick_rule(rules, "qualification_combination", scopes)
    if rule:
        res = _eval_qualification_combination(rule.get("value_json"), profile)
        if res == "missing":
            missing.append("qualification_details")
        elif res == "fail" and rule.get("is_knockout", True):
            reasons.append("Does not meet the required qualification combination.")
            return _decision("not_eligible", reasons, missing)
        elif res == "pass":
            any_rule_checked = True

    # All known checks passed.
    if missing:
        return _decision("conditional", reasons, missing)
    if not any_rule_checked:
        return _decision("unknown", reasons, missing)
    return _decision("eligible", reasons, missing)


def _decision(status: str, reasons: list[str], missing: list[str]) -> dict[str, Any]:
    return {
        "status": status,
        "reasons": reasons,
        "missing_fields": sorted(set(missing)),
    }


# ── DB-aware wrapper ─────────────────────────────────────────────────────


def _safe(call, default=None):
    try:
        return call()
    except Exception as exc:  # noqa: BLE001
        logger.warning("exam_eligibility supabase call failed: %s", exc)
        return default


def _load_user_profile(supabase: Any, user_id: str) -> dict[str, Any]:
    """Project the minimum profile fields the evaluator needs."""
    prof_rows = _safe(
        lambda: (
            supabase.table("profiles")
            .select(
                "id, date_of_birth, dob, category, pwbd_status, nationality, "
                "gender, ex_serviceman, govt_employee"
            )
            .eq("id", user_id)
            .limit(1)
            .execute()
            .data
        ),
        default=[],
    ) or []
    profile: dict[str, Any] = dict(prof_rows[0]) if prof_rows else {}

    # Education level: pick the highest level on file. A user with both 12th
    # and graduation rows must satisfy a "graduation" rule with the latter.
    edu_rows = _safe(
        lambda: (
            supabase.table("aspirant_education")
            .select("level, degree, stream, percentage, is_completed")
            .eq("user_id", user_id)
            .limit(20)
            .execute()
            .data
        ),
        default=[],
    ) or []
    best_rank = -1
    best_level = None
    disciplines: list[str] = []
    best_percentage: float | None = None
    records: list[dict[str, Any]] = []
    for row in edu_rows:
        if row.get("is_completed") is False:
            continue
        rank = _education_rank(row.get("level"))
        if rank is not None and rank > best_rank:
            best_rank = rank
            best_level = row.get("level")
        rec_disc: list[str] = []
        for key in ("degree", "stream"):
            val = row.get(key)
            if isinstance(val, str) and val.strip():
                disciplines.append(val)
                rec_disc.append(val)
        rec_pct: float | None = None
        pct = row.get("percentage")
        if pct is not None:
            try:
                rec_pct = float(pct)
                best_percentage = max(best_percentage or float("-inf"), rec_pct)
            except (TypeError, ValueError):
                pass
        # One normalized record: discipline + percentage + level stay CORRELATED
        # so a combination like "LLB AND 60%" must be satisfied by ONE qualification.
        records.append({"disciplines": rec_disc, "percentage": rec_pct, "level": row.get("level")})
    if best_level:
        profile["education_level"] = best_level
    # Keyed presence (empty list, not absent) so the evaluator distinguishes
    # "no discipline on file → missing" from "has discipline that doesn't match".
    if edu_rows:
        profile["disciplines"] = disciplines
        profile["education_records"] = records
    if best_percentage is not None:
        profile["best_percentage"] = best_percentage

    cert_rows = _safe(
        lambda: (
            supabase.table("aspirant_certifications")
            .select("certification_name, is_active")
            .eq("user_id", user_id)
            .limit(50)
            .execute()
            .data
        ),
        default=None,
    )
    if cert_rows is not None:
        profile["certifications"] = [
            c.get("certification_name")
            for c in cert_rows
            if c.get("is_active") is not False and c.get("certification_name")
        ]

    return profile


# Exams are queried in bounded batches so a single unordered `.limit(...)` can
# never silently drop verified rules/streams once the fan-out (up to 500 exams ×
# common+stream rules) crosses a global cap (checkpost P0). Batch size keeps each
# query's row count well under the per-batch limit.
_EXAM_BATCH = 50
_PER_BATCH_LIMIT = 10000


def _chunks(items: list[str], size: int) -> list[list[str]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _load_rules_by_exam(
    supabase: Any, exam_ids: list[str]
) -> dict[str, list[dict[str, Any]]]:
    if not exam_ids:
        return {}
    cache_key = tuple(sorted(exam_ids))
    cached = _RULES_CACHE.get(cache_key)
    if cached is not None:
        # Return a shallow copy so callers can't mutate the cache.
        return {k: list(v) for k, v in cached.items()}
    rows: list[dict[str, Any]] = []
    for batch in _chunks(exam_ids, _EXAM_BATCH):
        rows.extend(
            _safe(
                lambda b=batch: (
                    supabase.table("exam_eligibility_rules")
                    .select(
                        "exam_id, stream_id, scope, rule_type, value_num, value_text, value_json, "
                        "is_knockout, source_url, reviewer_status"
                    )
                    .in_("exam_id", b)
                    .eq("reviewer_status", "verified")
                    .limit(_PER_BATCH_LIMIT)
                    .execute()
                    .data
                ),
                default=[],
            )
            or []
        )
    out: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        # Both common (stream_id NULL) and stream-scoped rows are loaded. The
        # exam-WIDE verdict uses only common rules (via _rules_for_stream(.,None));
        # stream-scoped rows drive the per-stream breakdown. A stream rule is
        # never applied exam-wide — see summarize_user_eligibility.
        out.setdefault(r["exam_id"], []).append(r)
    _RULES_CACHE[cache_key] = {k: list(v) for k, v in out.items()}
    return out


def _load_streams_by_exam(
    supabase: Any, exam_ids: list[str]
) -> dict[str, list[dict[str, Any]]]:
    if not exam_ids:
        return {}
    rows: list[dict[str, Any]] = []
    for batch in _chunks(exam_ids, _EXAM_BATCH):
        rows.extend(
            _safe(
                lambda b=batch: (
                    supabase.table("exam_streams")
                    .select("id, exam_id, stream_key, name, is_active")
                    .in_("exam_id", b)
                    .limit(_PER_BATCH_LIMIT)
                    .execute()
                    .data
                ),
                default=[],
            )
            or []
        )
    out: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        if r.get("is_active") is False:
            continue
        out.setdefault(r["exam_id"], []).append(r)
    return out


def summarize_user_eligibility(supabase: Any, user_id: str) -> dict[str, Any]:
    """Return the four-bucket summary for the dashboard / onboarding card.

    Output shape::

        {
            "eligible":      [{exam_id, slug, name, reasons, missing_fields}, ...],
            "conditional":   [...],
            "not_eligible":  [...],
            "unknown":       [...],
            "evaluated_at":  "<iso>",
            "rule_count":    int
        }

    Only ``eligible`` and ``conditional`` are intended for the user-facing
    onboarding/dashboard surfaces (PR-D3). ``not_eligible`` and ``unknown``
    are included so the admin tool / debug surfaces can audit coverage.
    """
    # Route through the cached lookup so the dashboard fan-out shares
    # one read of the exams table per TTL window. The lookup superset
    # includes the columns this caller needs (id, slug, name,
    # exam_family_id, is_active).
    from app.exam_intelligence.lookup import list_active_exams

    exam_rows = list_active_exams(supabase, limit=500)

    exam_ids = [e["id"] for e in exam_rows]
    rules_by_exam = _load_rules_by_exam(supabase, exam_ids)
    streams_by_exam = _load_streams_by_exam(supabase, exam_ids)
    profile = _load_user_profile(supabase, user_id)

    buckets: dict[str, list[dict[str, Any]]] = {
        "eligible": [],
        "conditional": [],
        "not_eligible": [],
        "unknown": [],
    }
    rule_count = 0
    for exam in exam_rows:
        rules = rules_by_exam.get(exam["id"], [])
        rule_count += len(rules)
        # Exams with no verified rules are intentionally omitted from
        # ``unknown`` — they carry no signal to admins yet either.
        if not rules:
            continue
        # Exam-WIDE verdict uses only common (stream_id NULL) rules — unchanged
        # bucket semantics, so existing consumers are backward-compatible.
        common_rules = _rules_for_stream(rules, None)
        result = evaluate_exam_for_user(common_rules, profile)

        # Additive per-stream breakdown: each stream evaluated against common +
        # its own stream-specific rules (stream rules override). Streams with no
        # stream-specific rule simply mirror the common verdict.
        streams_out: list[dict[str, Any]] = []
        for st in streams_by_exam.get(exam["id"], []):
            st_result = evaluate_exam_for_user(_rules_for_stream(rules, st["id"]), profile)
            streams_out.append(
                {
                    "stream_id": st["id"],
                    "stream_key": st.get("stream_key"),
                    "name": st.get("name"),
                    "status": st_result["status"],
                    "reasons": st_result["reasons"],
                    "missing_fields": st_result["missing_fields"],
                }
            )

        buckets[result["status"]].append(
            {
                "exam_id": exam["id"],
                "slug": exam.get("slug"),
                "name": exam.get("name"),
                "reasons": result["reasons"],
                "missing_fields": result["missing_fields"],
                "streams": streams_out,
            }
        )

    from datetime import datetime, timezone
    return {
        **buckets,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "rule_count": rule_count,
    }
