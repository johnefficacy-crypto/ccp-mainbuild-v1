from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid as _uuid_mod
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

# All logs go to stderr; JSON results go to stdout only.
logging.basicConfig(
    stream=sys.stderr,
    level=logging.WARNING,
    format="%(levelname)s %(name)s: %(message)s",
)
_log = logging.getLogger("shadow_analysis")

try:
    from supabase import create_client
except ImportError:  # pragma: no cover
    create_client = None  # type: ignore[assignment]

# Trust weights verified from mastery_writer.TRUST_WEIGHT.
_TRUST_WEIGHTS: dict[str, Decimal] = {
    "platform_verified": Decimal("1.0"),
    "admin_verified": Decimal("1.0"),
    "self_reported": Decimal("0.3"),
}
_RECOGNIZED_TRUST_LEVELS: frozenset[str] = frozenset(_TRUST_WEIGHTS)
_CAP_DB = Decimal("15")  # ±0.15 unit × 100 = ±15 db

# Formalized exit codes.
_EXIT_OK = 0           # PASS or FAIL — run completed, data was sufficient
_EXIT_ERROR = 2        # config / credential / query error  (ERROR status)
_EXIT_INSUFFICIENT = 3 # insufficient data                  (INSUFFICIENT_DATA status)
_EXIT_CORRUPT = 4      # corrupt / invariant-invalid data


# ─── helpers ─────────────────────────────────────────────────────────────────


def _get_supabase() -> Any:
    """Create Supabase admin client from env or exit 2 with a clear error."""
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        _emit_result(
            {
                "schema_version": 1,
                "command": "",
                "status": "ERROR",
                "error": "MISSING_CREDENTIALS",
                "detail": (
                    "NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set. "
                    "Refusing to print zero metrics on missing credentials."
                ),
            },
            output_json=True,
        )
        sys.exit(_EXIT_ERROR)
    if create_client is None:  # pragma: no cover
        _emit_result(
            {
                "schema_version": 1,
                "command": "",
                "status": "ERROR",
                "error": "MISSING_DEPENDENCY",
                "detail": "supabase-py not installed. Run: pip install supabase",
            },
            output_json=True,
        )
        sys.exit(_EXIT_ERROR)
    return create_client(url, key)


def _since_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2 or len(ys) != n:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    denom_x = sum((a - mx) ** 2 for a in xs) ** 0.5
    denom_y = sum((b - my) ** 2 for b in ys) ** 0.5
    if denom_x == 0 or denom_y == 0:
        return None
    return round(num / (denom_x * denom_y), 4)


def _fetch_paginated(
    sb: Any,
    table: str,
    query_fn: Any,
    batch_size: int = 1000,
    order_by: str = "id",
) -> list[dict]:
    """Stable offset-based pagination; page size ≤ 1000, duplicate detection."""
    all_rows: list[dict] = []
    seen_ids: set[Any] = set()
    offset = 0
    while True:
        result = (
            query_fn(sb.table(table))
            .order(order_by)
            .range(offset, offset + batch_size - 1)
            .execute()
            .data
            or []
        )
        for r in result:
            row_id = r.get("id") or r.get(order_by)
            if row_id not in seen_ids:
                seen_ids.add(row_id)
                all_rows.append(r)
        if len(result) < batch_size:
            break
        offset += batch_size
    return all_rows


def _emit_result(result: dict[str, Any], output_json: bool) -> None:
    """Write result to stdout. JSON mode: pretty JSON. Human mode: key=value."""
    if output_json:
        print(json.dumps(result, indent=2))
        return
    cmd = result.get("command", "")
    status = result.get("status", "")
    print(f"{cmd} status={status}")
    skip = {"schema_version", "command", "status", "thresholds"}
    for k, v in result.items():
        if k in skip:
            continue
        if isinstance(v, list) and len(v) == 0:
            continue
        if isinstance(v, (dict, list)):
            print(f"  {k}={json.dumps(v)}")
        else:
            print(f"  {k}={v}")
    if "thresholds" in result:
        print(f"  thresholds={json.dumps(result['thresholds'])}")


def _check_attempt_derivation(command: str) -> Any:
    """Import attempt_derivation or exit 2 with PREREQUISITE_MISSING."""
    # Try project-root import path.
    try:
        from app.study_os import attempt_derivation as ad  # type: ignore[import-not-found]
        return ad
    except ImportError:
        pass
    # Try inserting the backend root into sys.path.
    backend_root = os.path.join(os.path.dirname(__file__), "..", "..", "app", "backend")
    sys.path.insert(0, os.path.abspath(backend_root))
    try:
        from app.study_os import attempt_derivation as ad  # type: ignore[import-not-found]
        return ad
    except ImportError:
        pass
    _emit_result(
        {
            "schema_version": 1,
            "command": command,
            "status": "ERROR",
            "error": "PREREQUISITE_MISSING",
            "detail": (
                "attempt_derivation module not found. "
                "This command requires PR-4 "
                "(app/backend/app/study_os/attempt_derivation.py) to be present."
            ),
        },
        output_json=True,
    )
    sys.exit(_EXIT_ERROR)


# ─── per-row invariant checker ────────────────────────────────────────────────


def _check_invariants(row: dict) -> list[str]:
    """Return list of invariant violation descriptions for one shadow row."""
    violations: list[str] = []
    attempt_id = row.get("attempt_id", "?")
    topic_id = row.get("topic_id", "?")
    key = f"attempt={attempt_id} topic={topic_id}"

    trust = row.get("trust_level")
    if trust not in _RECOGNIZED_TRUST_LEVELS:
        violations.append(f"{key}: unknown trust_level={trust!r}")
        return violations  # cannot compute trust-adjusted cap without known trust

    if row.get("flag_state") != "shadow":
        violations.append(f"{key}: flag_state={row.get('flag_state')!r} (expected 'shadow')")

    # B7: explicit NULL checks — or "0" silently passes null as zero, masking missing data
    null_fields = [
        f for f in (
            "proposed_delta_db_unweighted",
            "proposed_delta_db",
            "current_mastery_db",
            "would_be_mastery_db",
        )
        if row.get(f) is None
    ]
    if null_fields:
        violations.append(f"{key}: NULL value in fields: {', '.join(null_fields)}")
        return violations

    try:
        unweighted_db = Decimal(str(row["proposed_delta_db_unweighted"]))
        weighted_db = Decimal(str(row["proposed_delta_db"]))
        current_db = Decimal(str(row["current_mastery_db"]))
        would_be_db = Decimal(str(row["would_be_mastery_db"]))
    except Exception:
        violations.append(f"{key}: non-numeric value in delta/mastery fields")
        return violations

    if abs(unweighted_db) > _CAP_DB:
        violations.append(
            f"{key}: proposed_delta_db_unweighted={unweighted_db} exceeds cap ±{_CAP_DB}"
        )

    trust_cap = _CAP_DB * _TRUST_WEIGHTS[trust]
    if abs(weighted_db) > trust_cap + Decimal("0.01"):
        violations.append(
            f"{key}: proposed_delta_db={weighted_db} exceeds trust-adjusted cap ±{trust_cap}"
        )

    if not (Decimal("0") <= current_db <= Decimal("100")):
        violations.append(f"{key}: current_mastery_db={current_db} out of [0,100]")
    if not (Decimal("0") <= would_be_db <= Decimal("100")):
        violations.append(f"{key}: would_be_mastery_db={would_be_db} out of [0,100]")

    expected = min(Decimal("100"), max(Decimal("0"), current_db + weighted_db))
    if abs(expected - would_be_db) > Decimal("0.01"):
        violations.append(
            f"{key}: would_be_mastery_db={would_be_db} "
            f"!= clamp(current+weighted_delta)={expected}"
        )

    return violations


# ─── shadow_replay ────────────────────────────────────────────────────────────

_SR_THRESHOLDS: dict[str, Any] = {
    "min_distinct_attempts": 20,
    "min_topic_decisions": 50,
    "required_exact_match_pct": 100.0,
    "required_coverage_pct": 100.0,
}

# Shadow self-consistency gate (shadow mode only).
#
# Population: mock_mastery_shadow WHERE flag_state='shadow'.
# For each attempt, calls attempt_derivation.load_attempt_inputs to get
# analytics + trust_level + classification_coverage, then
# load_persisted_shadow_decisions for the stored baseline state, then
# replay_from_persisted_baseline(persisted, analytics, trust_level) to
# re-derive decisions and compare exactly (Decimal) to persisted shadow.
#
# Gate: distinct_attempt_count ≥ 20, topic_decision_count ≥ 50,
#       exact_match_pct = 100.0, coverage_pct = 100.0,
#       zero missing/extra/mismatch/duplicate/invariant violations,
#       zero classification_not_ready attempts.
#
# REQUIRES PR-4 (attempt_derivation.py). Exits 2 if the module is absent.


def shadow_replay(
    days: int = 14,
    attempt_id: str | None = None,
    from_utc: str | None = None,
    to_utc: str | None = None,
    output_json: bool = False,
) -> None:
    # B10: validate flag combinations
    if to_utc and not from_utc:
        _emit_result(
            {
                "schema_version": 1,
                "command": "shadow_replay",
                "status": "ERROR",
                "error": "INVALID_FLAGS",
                "detail": "--to-utc requires --from-utc",
            },
            output_json,
        )
        sys.exit(_EXIT_ERROR)

    ad = _check_attempt_derivation("shadow_replay")
    sb = _get_supabase()

    now_iso = datetime.now(timezone.utc).isoformat()
    window_start: str | None
    window_end: str | None

    # Population filter: --attempt-id takes precedence;
    # --from-utc/--to-utc overrides --days.
    if attempt_id:
        window_start = None
        window_end = None

        def query_fn(q: Any) -> Any:
            return (
                q.select(
                    "id,attempt_id,user_id,topic_id,proposed_delta_db,"
                    "proposed_delta_db_unweighted,current_mastery_db,"
                    "would_be_mastery_db,trust_level,flag_state,decided_at"
                )
                .eq("flag_state", "shadow")
                .eq("attempt_id", attempt_id)
            )

    elif from_utc or to_utc:
        window_start = from_utc
        window_end = to_utc

        def query_fn(q: Any) -> Any:  # type: ignore[misc]
            q = q.select(
                "id,attempt_id,user_id,topic_id,proposed_delta_db,"
                "proposed_delta_db_unweighted,current_mastery_db,"
                "would_be_mastery_db,trust_level,flag_state,decided_at"
            ).eq("flag_state", "shadow")
            if from_utc:
                q = q.gte("decided_at", from_utc)
            if to_utc:
                q = q.lte("decided_at", to_utc)
            return q

    else:
        since = _since_iso(days)
        window_start = since
        window_end = now_iso

        def query_fn(q: Any) -> Any:  # type: ignore[misc]
            return (
                q.select(
                    "id,attempt_id,user_id,topic_id,proposed_delta_db,"
                    "proposed_delta_db_unweighted,current_mastery_db,"
                    "would_be_mastery_db,trust_level,flag_state,decided_at"
                )
                .eq("flag_state", "shadow")
                .gte("decided_at", since)
            )

    try:
        shadow_rows = _fetch_paginated(
            sb, "mock_mastery_shadow", query_fn, batch_size=1000, order_by="id"
        )
    except Exception as exc:
        _log.error("Query failed: %s", exc)
        _emit_result(
            {
                "schema_version": 1,
                "command": "shadow_replay",
                "status": "ERROR",
                "error": "QUERY_FAILED",
                "detail": str(exc),
            },
            output_json,
        )
        sys.exit(_EXIT_ERROR)

    if not shadow_rows:
        _emit_result(
            {
                "schema_version": 1,
                "command": "shadow_replay",
                "window_start": window_start,
                "window_end": window_end,
                "status": "INSUFFICIENT_DATA",
                "thresholds": _SR_THRESHOLDS,
                "distinct_attempt_count": 0,
                "topic_decision_count": 0,
                "exact_match_count": 0,
                "exact_match_pct": None,
                "coverage_pct": None,
                "answered_topic_count": 0,
                "shadow_topic_count": 0,
                "missing_count": 0,
                "missing": [],
                "extra_count": 0,
                "extra": [],
                "mismatch_count": 0,
                "mismatches": [],
                "duplicate_key_count": 0,
                "duplicate_keys": [],
                "classification_not_ready_count": 0,
                "classification_not_ready": [],
                "invariant_violations": [],
            },
            output_json,
        )
        sys.exit(_EXIT_INSUFFICIENT)

    # Group by attempt_id.
    by_attempt: dict[str, list[dict]] = {}
    for r in shadow_rows:
        aid = r.get("attempt_id") or ""
        by_attempt.setdefault(aid, []).append(r)

    distinct_attempt_count = len(by_attempt)
    topic_decision_count = len(shadow_rows)

    # Duplicate key detection across all rows.
    seen_keys: dict[tuple, str] = {}
    duplicate_key_set: list[str] = []
    for r in shadow_rows:
        key = (r.get("attempt_id"), r.get("topic_id"), r.get("flag_state"))
        key_str = f"attempt={r.get('attempt_id')} topic={r.get('topic_id')}"
        if key in seen_keys:
            if key_str not in duplicate_key_set:
                duplicate_key_set.append(key_str)
        else:
            seen_keys[key] = r.get("id") or ""

    # Per-row invariant checks.
    invariant_violations: list[str] = []
    for r in shadow_rows:
        invariant_violations.extend(_check_invariants(r))

    # Per-attempt replay — B1/B4: call load_attempt_inputs, load_persisted_shadow_decisions,
    # replay_from_persisted_baseline(persisted, analytics, trust_level) with correct signatures.
    mismatches: list[dict] = []
    missing_list: list[dict] = []
    extra_list: list[dict] = []
    classification_not_ready: list[dict] = []
    exact_match_count = 0
    answered_topic_count = 0

    for aid in by_attempt:
        # Load attempt inputs (analytics + trust_level + classification readiness).
        try:
            inputs = ad.load_attempt_inputs(sb, aid)
        except Exception as exc:
            _log.warning("load_attempt_inputs(%s) raised: %s", aid, exc)
            classification_not_ready.append({"attempt_id": aid})
            continue

        if inputs is None:
            classification_not_ready.append({"attempt_id": aid})
            continue

        if not inputs.classification_coverage.ready:
            classification_not_ready.append({
                "attempt_id": aid,
                "missing": inputs.classification_coverage.missing_question_ids,
                "duplicate": inputs.classification_coverage.duplicate_question_ids,
            })
            continue

        # Load persisted shadow decisions (baseline state at write time).
        try:
            persisted = ad.load_persisted_shadow_decisions(sb, aid)
        except Exception as exc:
            _log.warning("load_persisted_shadow_decisions(%s) raised: %s", aid, exc)
            classification_not_ready.append({"attempt_id": aid})
            continue

        # Replay: re-derive mastery decisions using persisted baseline state.
        try:
            replay_result = ad.replay_from_persisted_baseline(
                persisted, inputs.analytics, inputs.trust_level
            )
        except Exception as exc:
            _log.warning("replay_from_persisted_baseline(%s) raised: %s", aid, exc)
            classification_not_ready.append({"attempt_id": aid})
            continue

        if replay_result is None:
            classification_not_ready.append({"attempt_id": aid})
            continue

        exact_match_count += replay_result.exact_match_count
        answered_topic_count += (
            replay_result.exact_match_count
            + len(replay_result.mismatches)
            + len(replay_result.extra)
        )
        missing_list.extend(replay_result.missing)
        extra_list.extend(replay_result.extra)
        # Convert Decimal delta values to str for JSON serialization.
        for m in replay_result.mismatches:
            mismatches.append({
                "attempt_id": m.get("attempt_id", ""),
                "topic_id": m.get("topic_id", ""),
                "persisted_delta_db": str(m.get("persisted_delta_db", "")),
                "replay_delta_db": str(m.get("replay_delta_db", "")),
                "diff_db": str(m.get("diff_db", "")),
                "reason": m.get("reason", ""),
            })

    shadow_topic_count = len(shadow_rows)
    total_comparable = exact_match_count + len(mismatches)
    exact_match_pct: float | None = (
        round(exact_match_count / total_comparable * 100, 4) if total_comparable else None
    )
    coverage_pct: float | None = (
        round(total_comparable / shadow_topic_count * 100, 4) if shadow_topic_count else None
    )

    t = _SR_THRESHOLDS
    if (
        distinct_attempt_count < t["min_distinct_attempts"]
        or topic_decision_count < t["min_topic_decisions"]
    ):
        status = "INSUFFICIENT_DATA"
    elif (
        exact_match_pct == 100.0
        and coverage_pct == 100.0
        and not missing_list
        and not extra_list
        and not mismatches
        and not duplicate_key_set
        and not invariant_violations
        and not classification_not_ready
    ):
        status = "PASS"
    else:
        status = "FAIL"

    result: dict[str, Any] = {
        "schema_version": 1,
        "command": "shadow_replay",
        "window_start": window_start,
        "window_end": window_end,
        "status": status,
        "thresholds": t,
        "distinct_attempt_count": distinct_attempt_count,
        "topic_decision_count": topic_decision_count,
        "exact_match_count": exact_match_count,
        "exact_match_pct": exact_match_pct,
        "coverage_pct": coverage_pct,
        "answered_topic_count": answered_topic_count,
        "shadow_topic_count": shadow_topic_count,
        "missing_count": len(missing_list),
        "missing": missing_list,
        "extra_count": len(extra_list),
        "extra": extra_list,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "duplicate_key_count": len(duplicate_key_set),
        "duplicate_keys": duplicate_key_set,
        "classification_not_ready_count": len(classification_not_ready),
        "classification_not_ready": classification_not_ready,
        "invariant_violations": invariant_violations,
    }
    _emit_result(result, output_json)

    if status == "INSUFFICIENT_DATA":
        sys.exit(_EXIT_INSUFFICIENT)
    if invariant_violations:
        sys.exit(_EXIT_CORRUPT)
    sys.exit(_EXIT_OK)


# ─── correction_parity ────────────────────────────────────────────────────────

_CP_THRESHOLDS: dict[str, Any] = {
    "min_correction_decisions": 10,
    "required_parity_pct": 100.0,
}

# Proves attempt_derivation.derive_attempt_evidence_corrections is equivalent to
# calling correction_policy.select_categories directly over the same normalized
# per-topic evidence.  Key: (attempt_id, canonical_topic_id, category) — UUID
# only, no display labels, no human string comparison.
#
# Gate: correction_decisions ≥ 10 AND exact_parity_pct = 100.0
# REQUIRES PR-4 (attempt_derivation.py). Exits 2 if absent.


def correction_parity(
    days: int = 14,
    attempt_id: str | None = None,
    from_utc: str | None = None,
    to_utc: str | None = None,
    output_json: bool = False,
) -> None:
    # B10: validate flag combinations
    if to_utc and not from_utc:
        _emit_result(
            {
                "schema_version": 1,
                "command": "correction_parity",
                "status": "ERROR",
                "error": "INVALID_FLAGS",
                "detail": "--to-utc requires --from-utc",
            },
            output_json,
        )
        sys.exit(_EXIT_ERROR)

    ad = _check_attempt_derivation("correction_parity")
    sb = _get_supabase()

    # Query submitted mock_attempts in window — includes unanswered-only attempts
    # that may have correction evidence but no shadow rows.
    if attempt_id:
        def query_fn(q: Any) -> Any:
            return q.select("id,submitted_at").eq("id", attempt_id).not_.is_("submitted_at", "null")
    elif from_utc or to_utc:
        def query_fn(q: Any) -> Any:  # type: ignore[misc]
            q = q.select("id,submitted_at").not_.is_("submitted_at", "null")
            if from_utc:
                q = q.gte("submitted_at", from_utc)
            if to_utc:
                q = q.lte("submitted_at", to_utc)
            return q
    else:
        since = _since_iso(days)

        def query_fn(q: Any) -> Any:  # type: ignore[misc]
            return (
                q.select("id,submitted_at")
                .not_.is_("submitted_at", "null")
                .gte("submitted_at", since)
            )

    try:
        attempt_rows = _fetch_paginated(
            sb, "mock_attempts", query_fn, batch_size=1000, order_by="id"
        )
    except Exception as exc:
        _log.error("Query failed: %s", exc)
        _emit_result(
            {
                "schema_version": 1,
                "command": "correction_parity",
                "status": "ERROR",
                "error": "QUERY_FAILED",
                "detail": str(exc),
            },
            output_json,
        )
        sys.exit(_EXIT_ERROR)

    attempt_ids = list({r.get("id") for r in attempt_rows if r.get("id")})

    if not attempt_ids:
        _emit_result(
            {
                "schema_version": 1,
                "command": "correction_parity",
                "status": "INSUFFICIENT_DATA",
                "thresholds": _CP_THRESHOLDS,
                "attempt_count": 0,
                "decision_count": 0,
                "generated_count": 0,
                "reference_count": 0,
                "intersection_count": 0,
                "generated_only": [],
                "reference_only": [],
                "exact_parity_pct": None,
            },
            output_json,
        )
        sys.exit(_EXIT_INSUFFICIENT)

    generated_set: set[tuple[str, str, str]] = set()
    reference_set: set[tuple[str, str, str]] = set()

    for aid in attempt_ids:
        # B3: load_attempt_inputs first, then call with (analytics, trust_level)
        try:
            inputs = ad.load_attempt_inputs(sb, aid)
        except Exception as exc:
            _log.warning("load_attempt_inputs(%s) raised: %s", aid, exc)
            continue

        if inputs is None:
            continue

        # Generated set: derive_attempt_evidence_corrections(analytics, trust_level).
        try:
            gen_corrections = ad.derive_attempt_evidence_corrections(
                inputs.analytics, inputs.trust_level
            )
        except Exception as exc:
            _log.warning("derive_attempt_evidence_corrections(%s) failed: %s", aid, exc)
            gen_corrections = []

        for item in gen_corrections or []:
            if isinstance(item, dict):
                tid = item.get("topic_id") or item.get("canonical_topic_id")
                cat = item.get("category")
            else:
                try:
                    tid, cat = item
                except (TypeError, ValueError):
                    continue
            if tid and cat:
                generated_set.add((aid, str(tid), str(cat)))

        # Reference set: call correction_policy.select_categories directly over analytics.
        try:
            ref_items = _build_reference_corrections(inputs.analytics)
        except Exception as exc:
            _log.warning("reference corrections(%s) failed: %s", aid, exc)
            ref_items = []

        for tid, cat in ref_items:
            reference_set.add((aid, str(tid), str(cat)))

    decision_count = len(generated_set | reference_set)
    intersection = generated_set & reference_set
    generated_only = sorted(f"{a}/{t}/{c}" for a, t, c in (generated_set - reference_set))
    reference_only = sorted(f"{a}/{t}/{c}" for a, t, c in (reference_set - generated_set))

    exact_parity_pct: float | None = (
        round(len(intersection) / decision_count * 100, 4) if decision_count else None
    )

    t = _CP_THRESHOLDS
    if decision_count < t["min_correction_decisions"]:
        status = "INSUFFICIENT_DATA"
    elif exact_parity_pct == 100.0:
        status = "PASS"
    else:
        status = "FAIL"

    _emit_result(
        {
            "schema_version": 1,
            "command": "correction_parity",
            "status": status,
            "thresholds": t,
            "attempt_count": len(attempt_ids),
            "decision_count": decision_count,
            "generated_count": len(generated_set),
            "reference_count": len(reference_set),
            "intersection_count": len(intersection),
            "generated_only": generated_only,
            "reference_only": reference_only,
            "exact_parity_pct": exact_parity_pct,
        },
        output_json,
    )

    exit_code = _EXIT_INSUFFICIENT if status == "INSUFFICIENT_DATA" else _EXIT_OK
    sys.exit(exit_code)


def _build_reference_corrections(analytics: Any) -> list[tuple[str, str]]:
    """Call correction_policy.select_categories directly over analytics, mirroring
    what derive_correction_tasks does — used to prove correction_parity."""
    try:
        from app.study_os.correction_policy import (
            CorrectionPolicyInput,
            normalize_error_type,
            select_categories,
        )
    except ImportError:
        backend_root = os.path.join(
            os.path.dirname(__file__), "..", "..", "app", "backend"
        )
        sys.path.insert(0, os.path.abspath(backend_root))
        from app.study_os.correction_policy import (  # type: ignore[import-not-found]
            CorrectionPolicyInput,
            normalize_error_type,
            select_categories,
        )

    # B2: build per-topic evidence directly from analytics, not from ad.load_attempt_topic_evidence
    by_topic = {t.topic_id: t for t in (analytics.topics or [])}
    q_by_topic: dict[str, list] = defaultdict(list)
    for q in analytics.questions or []:
        q_by_topic[q.topic_id].append(q)

    results: list[tuple[str, str]] = []
    for topic_id in sorted(set(by_topic.keys())):
        topic = by_topic.get(topic_id)
        attempted = topic.attempted if topic else 0
        accuracy = topic.accuracy_pct if topic else Decimal("100")
        questions = q_by_topic.get(topic_id, [])

        raw_counts: Counter = Counter()
        for q in questions:
            if q.error_type and normalize_error_type(q.error_type) is not None:
                raw_counts[q.error_type] += 1

        wrong_pyq = any((not q.is_correct and q.source_type == "pyq") for q in questions)
        related_ids = sorted({q.question_id for q in questions if (not q.is_correct) or q.error_type})

        inp = CorrectionPolicyInput(
            topic=topic_id,
            error_counts=dict(raw_counts),
            attempted=attempted,
            accuracy_pct=accuracy,
            prior_error=False,  # no existing_error_topics in replay context
            wrong_pyq=wrong_pyq,
            source_question_ids=tuple(related_ids),
            evidence_mode="question_level",
        )
        for cat in select_categories(inp):
            results.append((str(topic_id), str(cat)))

    return results


# ─── tasks_overlap ────────────────────────────────────────────────────────────

# Cross-origin topic identity is unavailable: generated corrections use canonical
# topic UUIDs; manual study tasks use display-name topic references.  This
# subcommand is EXPLICITLY INVALID and always exits 2.  Use correction-parity
# instead to verify correctness of the generated correction pipeline.


def tasks_overlap(output_json: bool = False) -> None:  # noqa: ARG001
    _emit_result(
        {
            "schema_version": 1,
            "command": "tasks_overlap",
            "status": "ERROR",
            "error": "CROSS_ORIGIN_TOPIC_IDENTITY_UNAVAILABLE",
            "detail": (
                "Generated corrections use canonical topic UUIDs. "
                "Manual study tasks use display-name topic references. "
                "Cross-origin overlap is not computable without a topic identity resolver. "
                "Use correction-parity instead."
            ),
        },
        output_json=True,  # always emit JSON for this error
    )
    sys.exit(_EXIT_ERROR)


# ─── live_audit_compare ───────────────────────────────────────────────────────

_LAC_THRESHOLDS: dict[str, Any] = {
    "min_matched_pairs": 10,
    "required_delta_tolerance_db": 0.01,
}

# Live audit comparison — CANARY-ONLY.
# Population: mock_mastery_shadow WHERE flag_state='live' (NOT shadow).
# Audit rows: user_topic_mastery_audit WHERE reason='mock_submit'.
# Join key: (attempt_id, topic_id).
# Requires delta_applied_db within 0.01 db.
#
# Running against a shadow-only deployment correctly returns
# INSUFFICIENT_DATA (no live rows exist until FF=live is active).


def live_audit_compare(
    days: int = 14,
    output_json: bool = False,
) -> None:
    sb = _get_supabase()
    since = _since_iso(days)

    try:
        shadow_rows = _fetch_paginated(
            sb,
            "mock_mastery_shadow",
            lambda q: (
                q.select(
                    "attempt_id,user_id,topic_id,proposed_delta_db,"
                    "proposed_delta_db_unweighted,current_mastery_db,"
                    "would_be_mastery_db,trust_level,flag_state"
                )
                .eq("flag_state", "live")
                .gte("decided_at", since)
            ),
            batch_size=1000,
            order_by="id",
        )
    except Exception as exc:
        _log.error("Query failed: %s", exc)
        _emit_result(
            {
                "schema_version": 1,
                "command": "live_audit_compare",
                "status": "ERROR",
                "error": "QUERY_FAILED",
                "detail": str(exc),
            },
            output_json,
        )
        sys.exit(_EXIT_ERROR)

    if not shadow_rows:
        _emit_result(
            {
                "schema_version": 1,
                "command": "live_audit_compare",
                "window_days": days,
                "status": "INSUFFICIENT_DATA",
                "thresholds": _LAC_THRESHOLDS,
                "shadow_rows": 0,
                "matched_with_audit": 0,
                "sign_agreement_pct": None,
                "magnitude_corr": None,
                "outliers": 0,
                "duplicate_audit_count": 0,
                "missing_audit_count": 0,
                "delta_mismatch_count": 0,
                "delta_mismatches": [],
                "trust_breakdown": {},
            },
            output_json,
        )
        sys.exit(_EXIT_INSUFFICIENT)

    attempt_ids = list(
        {r["attempt_id"] for r in shadow_rows if r.get("attempt_id")}
    )

    # B8: use _fetch_paginated for audit rows (batched by 500 attempt_ids, each batch
    # paginated so rows beyond Supabase's 1000-row default limit are not silently dropped).
    audit_rows: list[dict] = []
    duplicate_audit_count = 0
    seen_audit_keys: set[tuple] = set()
    for i in range(0, len(attempt_ids), 500):
        batch = attempt_ids[i : i + 500]
        batch_rows = _fetch_paginated(
            sb,
            "user_topic_mastery_audit",
            lambda q, b=batch: (
                q.select("id,user_id,topic_id,attempt_id,delta_applied_db")
                .in_("attempt_id", b)
                .eq("reason", "mock_submit")
            ),
            batch_size=1000,
            order_by="id",
        )
        for r in batch_rows:
            akey = (r.get("attempt_id"), r.get("topic_id"))
            if akey in seen_audit_keys:
                duplicate_audit_count += 1
            else:
                seen_audit_keys.add(akey)
                audit_rows.append(r)

    # B9: use Decimal for all delta comparisons (not float)
    audit_map: dict[tuple, Decimal] = {}
    for r in audit_rows:
        if (
            r.get("attempt_id")
            and r.get("topic_id")
            and r.get("delta_applied_db") is not None
        ):
            audit_map[(r["attempt_id"], r["topic_id"])] = Decimal(str(r["delta_applied_db"]))

    # Count shadow keys not found in audit.
    shadow_keys = {
        (r["attempt_id"], r["topic_id"])
        for r in shadow_rows
        if r.get("attempt_id") and r.get("topic_id")
    }
    missing_audit_count = len(shadow_keys - set(audit_map))

    matched_shadow: list[Decimal] = []
    matched_audit: list[Decimal] = []
    for r in shadow_rows:
        key = (r.get("attempt_id"), r.get("topic_id"))
        if key in audit_map and r.get("proposed_delta_db") is not None:
            matched_shadow.append(Decimal(str(r["proposed_delta_db"])))
            matched_audit.append(audit_map[key])

    MIN_SAMPLE = _LAC_THRESHOLDS["min_matched_pairs"]
    sufficient = len(matched_shadow) >= MIN_SAMPLE

    sign_agreement_pct: float | None = None
    magnitude_corr: float | None = None
    if sufficient:
        agreements = sum(
            1
            for s, a in zip(matched_shadow, matched_audit)
            if _sign(float(s)) == _sign(float(a))
        )
        sign_agreement_pct = round(agreements / len(matched_shadow) * 100, 2)
        magnitude_corr = _pearson(
            [float(x) for x in matched_shadow],
            [float(x) for x in matched_audit],
        )

    # Outliers: |proposed_delta_db| > 15 db
    outliers = sum(
        1
        for r in shadow_rows
        if r.get("proposed_delta_db") is not None
        and abs(Decimal(str(r["proposed_delta_db"]))) > _CAP_DB
    )

    trust_breakdown: dict[str, Any] = {}
    for trust in _RECOGNIZED_TRUST_LEVELS:
        trust_rows = [r for r in shadow_rows if r.get("trust_level") == trust]
        if not trust_rows:
            continue
        t_shadow: list[Decimal] = []
        t_audit: list[Decimal] = []
        for r in trust_rows:
            key = (r.get("attempt_id"), r.get("topic_id"))
            if key in audit_map and r.get("proposed_delta_db") is not None:
                t_shadow.append(Decimal(str(r["proposed_delta_db"])))
                t_audit.append(audit_map[key])
        t_sufficient = len(t_shadow) >= MIN_SAMPLE
        t_sign: float | None = None
        t_corr: float | None = None
        if t_sufficient:
            t_agr = sum(
                1 for s, a in zip(t_shadow, t_audit)
                if _sign(float(s)) == _sign(float(a))
            )
            t_sign = round(t_agr / len(t_shadow) * 100, 2)
            t_corr = _pearson(
                [float(x) for x in t_shadow],
                [float(x) for x in t_audit],
            )
        trust_breakdown[trust] = {
            "count": len(trust_rows),
            "matched": len(t_shadow),
            "sign_agreement_pct": t_sign,
            "magnitude_corr": t_corr,
            "insufficient_sample": not t_sufficient,
        }

    # Delta mismatches: |shadow_delta - audit_delta| > tolerance
    tolerance = Decimal(str(_LAC_THRESHOLDS["required_delta_tolerance_db"]))
    delta_mismatches: list[dict] = []
    for r in shadow_rows:
        key = (r.get("attempt_id"), r.get("topic_id"))
        if key in audit_map and r.get("proposed_delta_db") is not None:
            shadow_d = Decimal(str(r["proposed_delta_db"]))
            audit_d = audit_map[key]
            diff = abs(shadow_d - audit_d)
            if diff > tolerance:
                delta_mismatches.append({
                    "attempt_id": r.get("attempt_id"),
                    "topic_id": r.get("topic_id"),
                    "shadow_delta_db": str(shadow_d),
                    "audit_delta_db": str(audit_d),
                    "diff_db": str(diff),
                })
    delta_mismatch_count = len(delta_mismatches)

    if not sufficient:
        status = "INSUFFICIENT_DATA"
    elif (
        sign_agreement_pct is not None
        and sign_agreement_pct >= 95
        and missing_audit_count == 0
        and duplicate_audit_count == 0
        and outliers == 0
        and delta_mismatch_count == 0
    ):
        status = "PASS"
    else:
        status = "FAIL"

    _emit_result(
        {
            "schema_version": 1,
            "command": "live_audit_compare",
            "window_days": days,
            "status": status,
            "thresholds": _LAC_THRESHOLDS,
            "shadow_rows": len(shadow_rows),
            "matched_with_audit": len(matched_shadow),
            "sign_agreement_pct": sign_agreement_pct,
            "magnitude_corr": magnitude_corr,
            "outliers": outliers,
            "duplicate_audit_count": duplicate_audit_count,
            "missing_audit_count": missing_audit_count,
            "delta_mismatch_count": delta_mismatch_count,
            "delta_mismatches": delta_mismatches,
            "trust_breakdown": trust_breakdown,
        },
        output_json,
    )
    sys.exit(_EXIT_INSUFFICIENT if status == "INSUFFICIENT_DATA" else _EXIT_OK)


# ─── multi-exam-coverage ─────────────────────────────────────────────────────


def multi_exam_coverage(
    *,
    required_exam_ids: list[str],
    required_exam_slugs: list[str],
    min_questions: int = 1,
    from_utc: str | None = None,
    to_utc: str | None = None,
    days: int | None = None,
    output_json: bool = False,
) -> None:
    """Validate FF_MOCK_MASTERY_WRITES shadow coverage across multiple exams.

    Uses ``mock_mastery_shadow`` (flag_state='shadow') as the source of truth
    and joins to ``mock_attempts`` for exam_id + ``mock_attempt_responses``
    for per-question source_kind breakdown.

    At least one --required-exam-id or --required-exam-slug must be supplied;
    the command exits ERROR without them (no-track runs are meaningless).

    Time window: supply --from-utc/--to-utc or --days to restrict
    ``decided_at``; omitting all three reads the full history.

    Exits:
      0 — PASS: all required exam tracks meet the min_questions threshold
      3 — INSUFFICIENT_DATA: a required track is below threshold, or no shadow data
      4 — CORRUPT: invariant violations detected
      2 — ERROR: credential / query failure, or no tracks supplied
    """
    cmd = "multi_exam_coverage"
    sb = _get_supabase()

    # ── 0. Require at least one track ─────────────────────────────────────────
    if not required_exam_ids and not required_exam_slugs:
        _emit_result(
            {
                "schema_version": 1,
                "command": cmd,
                "status": "ERROR",
                "error": "NO_TRACKS_SUPPLIED",
                "detail": (
                    "At least one --required-exam-id or --required-exam-slug must be "
                    "specified. Running without tracks would always PASS vacuously."
                ),
            },
            output_json,
        )
        sys.exit(_EXIT_ERROR)

    # ── 0b. Resolve time window ────────────────────────────────────────────────
    now_utc = datetime.now(timezone.utc)
    if from_utc:
        window_start: str | None = from_utc
        window_end: str | None = to_utc or now_utc.isoformat()
    elif days is not None:
        window_start = (now_utc - timedelta(days=days)).isoformat()
        window_end = now_utc.isoformat()
    else:
        window_start = None
        window_end = None

    # ── 1. Fetch mock_mastery_shadow rows (flag_state='shadow') ───────────────
    def _shadow_query(t: Any) -> Any:
        q = t.select(
            "id, attempt_id, user_id, topic_id, "
            "proposed_delta_db, current_mastery_db, would_be_mastery_db, decided_at"
        ).eq("flag_state", "shadow")
        if window_start:
            q = q.gte("decided_at", window_start)
        if window_end:
            q = q.lte("decided_at", window_end)
        return q

    try:
        shadow_rows = _fetch_paginated(sb, "mock_mastery_shadow", _shadow_query, order_by="id")
    except Exception as exc:
        _emit_result(
            {
                "schema_version": 1,
                "command": cmd,
                "status": "ERROR",
                "error": "QUERY_FAILED",
                "detail": f"mock_mastery_shadow fetch failed: {exc}",
            },
            output_json,
        )
        sys.exit(_EXIT_ERROR)

    if not shadow_rows:
        _emit_result(
            {
                "schema_version": 1,
                "command": cmd,
                "status": "INSUFFICIENT_DATA",
                "error": "NO_SHADOW_DATA",
                "detail": (
                    "No shadow rows found (flag_state='shadow'). "
                    "FF_MOCK_MASTERY_WRITES may not be active, or no attempts "
                    "in the specified time window."
                ),
                "required_exam_ids": required_exam_ids,
                "required_exam_slugs": required_exam_slugs,
                "window": {"from_utc": window_start, "to_utc": window_end},
            },
            output_json,
        )
        sys.exit(_EXIT_INSUFFICIENT)

    # ── 2. Resolve attempt_id → exam_id ──────────────────────────────────────
    # Fixed-template attempts: mock_attempts.template_id → mock_templates.exam_id
    # Generated attempts:      mock_attempts.generated_blueprint_id → mock_generated_blueprints.exam_id
    attempt_ids = list({r["attempt_id"] for r in shadow_rows if r.get("attempt_id")})
    attempt_template_map: dict[str, str] = {}   # attempt_id → template_id
    attempt_blueprint_map: dict[str, str] = {}  # attempt_id → generated_blueprint_id

    for batch_start in range(0, len(attempt_ids), 100):
        batch = attempt_ids[batch_start: batch_start + 100]
        try:
            attempt_rows = (
                sb.table("mock_attempts")
                .select("id, template_id, generated_blueprint_id")
                .in_("id", batch)
                .execute()
                .data
                or []
            )
            for r in attempt_rows:
                if r.get("template_id"):
                    attempt_template_map[r["id"]] = r["template_id"]
                elif r.get("generated_blueprint_id"):
                    attempt_blueprint_map[r["id"]] = r["generated_blueprint_id"]
        except Exception as exc:
            _emit_result(
                {
                    "schema_version": 1,
                    "command": cmd,
                    "status": "ERROR",
                    "error": "QUERY_FAILED",
                    "detail": f"mock_attempts fetch failed: {exc}",
                },
                output_json,
            )
            sys.exit(_EXIT_ERROR)

    # Resolve template_id → exam_id via mock_templates.
    template_ids = list(set(attempt_template_map.values()))
    template_exam_map: dict[str, str] = {}
    for batch_start in range(0, len(template_ids), 100):
        batch = template_ids[batch_start: batch_start + 100]
        try:
            tmpl_rows = (
                sb.table("mock_templates")
                .select("id, exam_id")
                .in_("id", batch)
                .execute()
                .data
                or []
            )
            for r in tmpl_rows:
                if r.get("exam_id"):
                    template_exam_map[r["id"]] = r["exam_id"]
        except Exception as exc:
            _emit_result(
                {
                    "schema_version": 1,
                    "command": cmd,
                    "status": "ERROR",
                    "error": "QUERY_FAILED",
                    "detail": f"mock_templates fetch failed: {exc}",
                },
                output_json,
            )
            sys.exit(_EXIT_ERROR)

    # Resolve generated_blueprint_id → exam_id via mock_generated_blueprints.
    blueprint_ids = list(set(attempt_blueprint_map.values()))
    blueprint_exam_map: dict[str, str] = {}
    for batch_start in range(0, len(blueprint_ids), 100):
        batch = blueprint_ids[batch_start: batch_start + 100]
        try:
            bp_rows = (
                sb.table("mock_generated_blueprints")
                .select("id, exam_id")
                .in_("id", batch)
                .execute()
                .data
                or []
            )
            for r in bp_rows:
                if r.get("exam_id"):
                    blueprint_exam_map[r["id"]] = r["exam_id"]
        except Exception as exc:
            _emit_result(
                {
                    "schema_version": 1,
                    "command": cmd,
                    "status": "ERROR",
                    "error": "QUERY_FAILED",
                    "detail": f"mock_generated_blueprints fetch failed: {exc}",
                },
                output_json,
            )
            sys.exit(_EXIT_ERROR)

    # Build the final attempt → exam map (template path takes precedence).
    attempt_exam_map: dict[str, str] = {}
    for attempt_id, tmpl_id in attempt_template_map.items():
        if tmpl_id in template_exam_map:
            attempt_exam_map[attempt_id] = template_exam_map[tmpl_id]
    for attempt_id, bp_id in attempt_blueprint_map.items():
        if attempt_id not in attempt_exam_map and bp_id in blueprint_exam_map:
            attempt_exam_map[attempt_id] = blueprint_exam_map[bp_id]

    # ── 3. Fetch question snapshots for source_kind + subject breakdown ────────
    responses_by_attempt: dict[str, list[dict]] = defaultdict(list)

    for batch_start in range(0, len(attempt_ids), 100):
        batch = attempt_ids[batch_start: batch_start + 100]
        try:
            # Paginate within each attempt batch: 100 attempts × up to 100 questions
            # each = 10 000 rows, exceeding PostgREST's default 1 000-row page size.
            page_size = 1000
            offset = 0
            while True:
                page = (
                    sb.table("mock_attempt_responses")
                    .select("attempt_id, question_snapshot")
                    .in_("attempt_id", batch)
                    .order("id")
                    .range(offset, offset + page_size - 1)
                    .execute()
                    .data
                    or []
                )
                for r in page:
                    responses_by_attempt[r["attempt_id"]].append(r)
                if len(page) < page_size:
                    break
                offset += page_size
        except Exception as exc:
            _emit_result(
                {
                    "schema_version": 1,
                    "command": cmd,
                    "status": "ERROR",
                    "error": "QUERY_FAILED",
                    "detail": f"mock_attempt_responses fetch failed: {exc}",
                },
                output_json,
            )
            sys.exit(_EXIT_ERROR)

    # ── 4. Fetch exam metadata for slug resolution ────────────────────────────
    exam_meta: dict[str, dict] = {}
    try:
        exam_rows = (
            sb.table("exams")
            .select("id, slug, name")
            .execute()
            .data
            or []
        )
        for e in exam_rows:
            exam_meta[e["id"]] = e
    except Exception:
        pass  # slug resolution is best-effort; exam_id coverage still works

    slug_to_id: dict[str, str] = {
        e["slug"]: e["id"] for e in exam_meta.values() if e.get("slug")
    }

    # Resolve required_exam_slugs to IDs.
    required_ids_from_slugs: set[str] = set()
    missing_slugs: list[str] = []
    for slug in required_exam_slugs:
        eid = slug_to_id.get(slug)
        if eid:
            required_ids_from_slugs.add(eid)
        else:
            missing_slugs.append(slug)

    all_required_ids = set(required_exam_ids) | required_ids_from_slugs

    # ── 5. Build per-exam coverage stats ──────────────────────────────────────
    # Pre-compute per-attempt response stats so they are added to the exam
    # bucket exactly once per attempt, not once per shadow_row per attempt.
    attempt_response_stats: dict[str, dict] = {}
    for attempt_id, responses in responses_by_attempt.items():
        source_split: dict[str, int] = defaultdict(int)
        subject_breakdown: dict[str, int] = defaultdict(int)
        pyq_year_breakdown: dict[str, int] = defaultdict(int)
        for resp in responses:
            snap = resp.get("question_snapshot") or {}
            source_kind = snap.get("source_kind") or snap.get("source_type") or "unknown"
            source_split[source_kind] += 1
            subject_id = snap.get("subject_id")
            if subject_id:
                subject_breakdown[subject_id] += 1
            pyq_year = snap.get("pyq_year")
            if pyq_year:
                pyq_year_breakdown[str(pyq_year)] += 1
        attempt_response_stats[attempt_id] = {
            "source_split": source_split,
            "subject_breakdown": subject_breakdown,
            "pyq_year_breakdown": pyq_year_breakdown,
        }

    per_exam: dict[str, dict] = defaultdict(lambda: {
        "shadow_row_count": 0,
        "unique_attempts": set(),
        "source_split": defaultdict(int),
        "subject_breakdown": defaultdict(int),
        "pyq_year_breakdown": defaultdict(int),
    })

    seen_attempt_in_exam: set[tuple[str, str]] = set()

    for shadow_row in shadow_rows:
        attempt_id = shadow_row.get("attempt_id")
        if not attempt_id:
            continue
        exam_id = attempt_exam_map.get(attempt_id)
        if not exam_id:
            continue

        bucket = per_exam[exam_id]
        bucket["shadow_row_count"] += 1
        bucket["unique_attempts"].add(attempt_id)

        # Merge response breakdown only once per (attempt, exam) pair.
        pair = (attempt_id, exam_id)
        if pair not in seen_attempt_in_exam:
            seen_attempt_in_exam.add(pair)
            stats = attempt_response_stats.get(attempt_id, {})
            for k, v in stats.get("source_split", {}).items():
                bucket["source_split"][k] += v
            for k, v in stats.get("subject_breakdown", {}).items():
                bucket["subject_breakdown"][k] += v
            for k, v in stats.get("pyq_year_breakdown", {}).items():
                bucket["pyq_year_breakdown"][k] += v

    # Serialize (sets → counts, defaultdicts → plain dicts).
    exam_coverage: list[dict] = []
    for exam_id, bucket in per_exam.items():
        meta = exam_meta.get(exam_id, {})
        exam_coverage.append({
            "exam_id": exam_id,
            "exam_slug": meta.get("slug"),
            "exam_name": meta.get("name"),
            "shadow_row_count": bucket["shadow_row_count"],
            "unique_attempt_count": len(bucket["unique_attempts"]),
            "source_split": dict(bucket["source_split"]),
            "subject_breakdown": dict(bucket["subject_breakdown"]),
            "pyq_year_breakdown": dict(bucket["pyq_year_breakdown"]),
        })

    exam_coverage.sort(key=lambda r: r["exam_id"])

    # ── 6. Check required exam coverage ───────────────────────────────────────
    insufficient_exams: list[dict] = []
    for eid in all_required_ids:
        entry = next((r for r in exam_coverage if r["exam_id"] == eid), None)
        count = entry["shadow_row_count"] if entry else 0
        if count < min_questions:
            meta = exam_meta.get(eid, {})
            insufficient_exams.append({
                "exam_id": eid,
                "exam_slug": meta.get("slug"),
                "shadow_row_count": count,
                "required_minimum": min_questions,
            })

    for slug in missing_slugs:
        insufficient_exams.append({
            "exam_slug": slug,
            "exam_id": None,
            "shadow_row_count": 0,
            "required_minimum": min_questions,
            "error": "slug_not_found_in_db",
        })

    status: str
    if insufficient_exams:
        status = "INSUFFICIENT_DATA"
    else:
        status = "PASS"

    _emit_result(
        {
            "schema_version": 1,
            "command": cmd,
            "status": status,
            "source_table": "mock_mastery_shadow",
            "flag_state_filter": "shadow",
            "window": {"from_utc": window_start, "to_utc": window_end},
            "total_shadow_rows": len(shadow_rows),
            "total_exams_in_shadow": len(exam_coverage),
            "required_exam_ids": list(all_required_ids),
            "min_questions_threshold": min_questions,
            "insufficient_exams": insufficient_exams,
            "exam_coverage": exam_coverage,
            "thresholds": {
                "min_questions_per_exam": min_questions,
            },
        },
        output_json,
    )
    if status == "INSUFFICIENT_DATA":
        sys.exit(_EXIT_INSUFFICIENT)
    sys.exit(_EXIT_OK)


# ─── CLI ──────────────────────────────────────────────────────────────────────


# ─── telemetry-quality gate ───────────────────────────────────────────────────

_VISIT_EVENT_TYPES: frozenset[str] = frozenset({"question.visited", "question_visited"})

# Fail-closed telemetry-quality thresholds for the 14-day shadow gate. Any
# touched question without a visit event, any client-sequence gap, or any
# evaluated attempt with zero usable events fails the gate — proving the frozen
# classifications/dwell were derived from the documented primary event source
# rather than silently falling back to mock_attempt_responses.time_spent_sec.
_TQ_THRESHOLDS: dict[str, Any] = {
    "visit_coverage_pct": 100.0,    # every EXPECTED-VISIT question has a visit event
    "fallback_question_count": 0,   # no touched question fell back to time_spent_sec
    "delivery_gap_count": 0,        # no missing client sequence numbers (ingest/delivery loss)
    "attempts_without_events": 0,   # every evaluated attempt produced usable events
}


def _is_touched(resp: dict) -> bool:
    """Expected-visit population membership.

    Generated attempts legitimately contain UNTOUCHED questions (the user never
    navigated to them); those are NOT expected to carry a visit event and must
    not count against coverage. `mock_attempt_responses.is_visited` is set by
    answer-save (not by a mere visit), so we treat a question as *touched* — and
    therefore expected to have a client `question.visited` anchor — if it was
    answered, marked for review, or flagged visited.
    """
    return bool(
        resp.get("selected_option_id") is not None
        or resp.get("is_marked_for_review")
        or resp.get("is_visited")
    )


def compute_telemetry_quality(
    attempt_ids: list[str],
    responses_by_attempt: dict[str, list[dict]],
    events_by_attempt: dict[str, list[dict]],
) -> dict[str, Any]:
    """Pure metric computation (no DB, no thresholds) so it is unit-testable.

    Per attempt:
      - expected_visit population = touched questions (see _is_touched)
      - covered = touched questions that have a client `question.visited` event
      - missing/fallback = touched questions with no visit event (dwell falls back)
      - events_used = usable client visit events (valid occurred_at + question_id)
      - delivery_gap = max(client sequence_no) − distinct client sequence count.
        The client assigns monotonic per-attempt sequence numbers, so a gap means
        events that were enqueued but never accepted — a delivery / ingest-
        rejection proxy observable purely from persisted rows.
    """
    per_attempt: list[dict] = []
    agg_expected = agg_covered = agg_fallback = 0
    agg_events_used = agg_delivery_gap = 0
    attempts_without_events = 0

    for aid in attempt_ids:
        responses = responses_by_attempt.get(aid, [])
        events = events_by_attempt.get(aid, [])

        expected_qids = {
            r["question_id"]
            for r in responses
            if r.get("question_id") and _is_touched(r)
        }

        visit_qids: set[str] = set()
        events_used = 0
        seqs: set[int] = set()
        max_seq = 0
        for e in events:
            seq = e.get("sequence_no")
            if isinstance(seq, int):
                seqs.add(seq)
                if seq > max_seq:
                    max_seq = seq
            if e.get("event_type") not in _VISIT_EVENT_TYPES:
                continue
            if not e.get("occurred_at"):
                continue
            qid = (e.get("payload") or {}).get("question_id") or e.get("question_id")
            if not qid:
                continue
            visit_qids.add(qid)
            events_used += 1

        covered = expected_qids & visit_qids
        missing = sorted(expected_qids - visit_qids)
        delivery_gap = max(0, max_seq - len(seqs))
        if events_used == 0:
            attempts_without_events += 1

        per_attempt.append({
            "attempt_id": aid,
            "expected_visit_questions": len(expected_qids),
            "covered_questions": len(covered),
            "missing_visit_questions": len(missing),
            "missing_visit_qids": missing,
            "events_used": events_used,
            "delivery_gap_count": delivery_gap,
            "max_client_sequence_no": max_seq,
            "distinct_client_sequences": len(seqs),
        })

        agg_expected += len(expected_qids)
        agg_covered += len(covered)
        agg_fallback += len(missing)
        agg_events_used += events_used
        agg_delivery_gap += delivery_gap

    visit_coverage_pct = (
        round(100.0 * agg_covered / agg_expected, 4) if agg_expected else None
    )

    return {
        "attempts_evaluated": len(attempt_ids),
        "attempts_without_events": attempts_without_events,
        "expected_visit_questions": agg_expected,
        "covered_questions": agg_covered,
        "fallback_question_count": agg_fallback,
        "visit_coverage_pct": visit_coverage_pct,
        "events_used": agg_events_used,
        "delivery_gap_count": agg_delivery_gap,
        "per_attempt": per_attempt,
    }


def _fetch_by_attempt_ids(
    sb: Any,
    table: str,
    select: str,
    attempt_ids: list[str],
    source: str | None = None,
    chunk: int = 100,
) -> list[dict]:
    """Fetch rows for a set of attempt IDs in chunked `.in_()` queries."""
    rows: list[dict] = []
    for i in range(0, len(attempt_ids), chunk):
        batch = attempt_ids[i : i + chunk]

        def query_fn(q: Any, _batch: list[str] = batch) -> Any:
            q = q.select(select).in_("attempt_id", _batch)
            if source is not None:
                q = q.eq("source", source)
            return q

        rows.extend(_fetch_paginated(sb, table, query_fn, batch_size=1000, order_by="id"))
    return rows


_TQ_POPULATION_DEFINITION = (
    "expected-visit population = questions the user engaged with "
    "(selected_option_id set OR is_marked_for_review OR is_visited); "
    "legitimately untouched questions are excluded. visit_coverage_pct = "
    "covered / expected. delivery_gap_count = max(client sequence_no) - distinct "
    "client sequence count (events enqueued but never accepted)."
)


def telemetry_quality(
    days: int = 14,
    attempt_id: str | None = None,
    from_utc: str | None = None,
    to_utc: str | None = None,
    min_attempts: int = 1,
    output_json: bool = False,
) -> None:
    cmd = "telemetry_quality"
    sb = _get_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()

    if attempt_id:
        window_start = window_end = None

        def attempts_q(q: Any) -> Any:
            return (
                q.select("id,user_id,submitted_at,status")
                .eq("status", "submitted")
                .eq("id", attempt_id)
            )
    elif from_utc or to_utc:
        window_start, window_end = from_utc, to_utc

        def attempts_q(q: Any) -> Any:  # type: ignore[misc]
            q = q.select("id,user_id,submitted_at,status").eq("status", "submitted")
            if from_utc:
                q = q.gte("submitted_at", from_utc)
            if to_utc:
                q = q.lte("submitted_at", to_utc)
            return q
    else:
        since = _since_iso(days)
        window_start, window_end = since, now_iso

        def attempts_q(q: Any) -> Any:  # type: ignore[misc]
            return (
                q.select("id,user_id,submitted_at,status")
                .eq("status", "submitted")
                .gte("submitted_at", since)
            )

    thresholds = {**_TQ_THRESHOLDS, "min_attempts": min_attempts}

    try:
        attempts = _fetch_paginated(sb, "mock_attempts", attempts_q, batch_size=1000, order_by="id")
    except Exception as exc:  # noqa: BLE001
        _emit_result(
            {"schema_version": 1, "command": cmd, "status": "ERROR",
             "error": "QUERY_FAILED", "detail": str(exc)},
            output_json,
        )
        sys.exit(_EXIT_ERROR)

    attempt_ids = [a["id"] for a in attempts if a.get("id")]
    if len(attempt_ids) < min_attempts:
        _emit_result(
            {"schema_version": 1, "command": cmd, "window_start": window_start,
             "window_end": window_end, "status": "INSUFFICIENT_DATA",
             "thresholds": thresholds, "population_definition": _TQ_POPULATION_DEFINITION,
             "attempts_evaluated": len(attempt_ids)},
            output_json,
        )
        sys.exit(_EXIT_INSUFFICIENT)

    try:
        resp_rows = _fetch_by_attempt_ids(
            sb, "mock_attempt_responses",
            "id,attempt_id,question_id,selected_option_id,is_visited,is_marked_for_review,time_spent_sec",
            attempt_ids,
        )
        event_rows = _fetch_by_attempt_ids(
            sb, "mock_attempt_events",
            "id,attempt_id,event_type,payload,sequence_no,occurred_at,source",
            attempt_ids, source="client",
        )
    except Exception as exc:  # noqa: BLE001
        _emit_result(
            {"schema_version": 1, "command": cmd, "status": "ERROR",
             "error": "QUERY_FAILED", "detail": str(exc)},
            output_json,
        )
        sys.exit(_EXIT_ERROR)

    responses_by_attempt: dict[str, list[dict]] = defaultdict(list)
    for r in resp_rows:
        responses_by_attempt[r["attempt_id"]].append(r)
    events_by_attempt: dict[str, list[dict]] = defaultdict(list)
    for e in event_rows:
        events_by_attempt[e["attempt_id"]].append(e)

    metrics = compute_telemetry_quality(attempt_ids, responses_by_attempt, events_by_attempt)

    if metrics["expected_visit_questions"] == 0:
        _emit_result(
            {"schema_version": 1, "command": cmd, "window_start": window_start,
             "window_end": window_end, "status": "INSUFFICIENT_DATA",
             "thresholds": thresholds, "population_definition": _TQ_POPULATION_DEFINITION,
             "detail": "no expected-visit (touched) questions across evaluated attempts",
             **metrics},
            output_json,
        )
        sys.exit(_EXIT_INSUFFICIENT)

    failures: list[str] = []
    if metrics["visit_coverage_pct"] != 100.0:
        failures.append("visit_coverage_pct")
    if metrics["fallback_question_count"] != 0:
        failures.append("fallback_question_count")
    if metrics["delivery_gap_count"] != 0:
        failures.append("delivery_gap_count")
    if metrics["attempts_without_events"] != 0:
        failures.append("attempts_without_events")
    status = "PASS" if not failures else "FAIL"

    _emit_result(
        {"schema_version": 1, "command": cmd, "window_start": window_start,
         "window_end": window_end, "status": status, "thresholds": thresholds,
         "population_definition": _TQ_POPULATION_DEFINITION, "failures": failures,
         **metrics},
        output_json,
    )
    sys.exit(_EXIT_OK)


def main() -> None:
    p = argparse.ArgumentParser(prog="shadow-analysis")
    p.add_argument(
        "--json",
        dest="output_json",
        action="store_true",
        help="Machine-readable JSON output (also accepted after subcommand)",
    )
    sp = p.add_subparsers(dest="cmd", required=True)

    def _add_json(sub: argparse.ArgumentParser) -> None:
        """Add --json to a subparser so it works both before and after subcommand."""
        sub.add_argument(
            "--json",
            dest="sub_output_json",
            action="store_true",
            default=False,
            help="Machine-readable JSON output",
        )

    def _add_window_flags(sub: argparse.ArgumentParser) -> None:
        grp = sub.add_mutually_exclusive_group()
        grp.add_argument("--attempt-id", metavar="UUID", help="Exact single attempt")
        grp.add_argument("--from-utc", metavar="ISO8601", help="Window start (UTC)")
        sub.add_argument(
            "--to-utc",
            metavar="ISO8601",
            help="Window end (UTC); used with --from-utc",
        )
        # B10: default=None so we can detect if --days was explicitly provided alongside --attempt-id
        sub.add_argument("--days", type=int, default=None, help="Rolling window in days (default 14)")

    sr = sp.add_parser(
        "shadow-replay",
        help="Shadow self-consistency gate (main shadow gate command; requires PR-4)",
    )
    _add_json(sr)
    _add_window_flags(sr)

    cp = sp.add_parser(
        "correction-parity",
        help="Prove generated corrections == correction_policy.select_categories (requires PR-4)",
    )
    _add_json(cp)
    _add_window_flags(cp)

    to = sp.add_parser(
        "tasks-overlap",
        help="(INVALID) Cross-origin topic overlap — exits 2; use correction-parity instead",
    )
    _add_json(to)

    mec = sp.add_parser(
        "multi-exam-coverage",
        help="Validate FF_MOCK_MASTERY_WRITES shadow coverage across multiple exams",
    )
    _add_json(mec)
    mec.add_argument(
        "--required-exam-id",
        dest="required_exam_id",
        metavar="UUID",
        action="append",
        help="Exam UUID that must appear in shadow data (repeatable)",
    )
    mec.add_argument(
        "--required-exam-slug",
        dest="required_exam_slug",
        metavar="SLUG",
        action="append",
        help="Exam slug that must appear in shadow data (repeatable)",
    )
    mec.add_argument(
        "--min-questions",
        dest="min_questions",
        type=int,
        default=1,
        help="Minimum shadow question count required per exam (default 1)",
    )
    mec.add_argument(
        "--from-utc",
        dest="from_utc",
        metavar="ISO8601",
        default=None,
        help="Window start (UTC); filter mock_mastery_shadow on decided_at",
    )
    mec.add_argument(
        "--to-utc",
        dest="to_utc",
        metavar="ISO8601",
        default=None,
        help="Window end (UTC); used with --from-utc",
    )
    mec.add_argument(
        "--days",
        dest="days",
        type=int,
        default=None,
        help="Rolling window in days back from now (default: no window filter)",
    )

    lac = sp.add_parser(
        "live-audit-compare",
        help="Compare live shadow writes against audit trail (CANARY-ONLY)",
    )
    _add_json(lac)
    lac.add_argument("--days", type=int, default=14)

    tq = sp.add_parser(
        "telemetry-quality",
        help="Fail-closed telemetry-quality gate: visit coverage / fallback / "
             "delivery-gap over submitted attempts (PR-7 freeze prerequisite)",
    )
    _add_json(tq)
    _add_window_flags(tq)
    tq.add_argument(
        "--min-attempts",
        dest="min_attempts",
        type=int,
        default=1,
        help="Data-sufficiency floor; below this -> INSUFFICIENT_DATA (real gate uses >= 20)",
    )

    a = p.parse_args()
    output_json = a.output_json or getattr(a, "sub_output_json", False)

    if a.cmd in ("shadow-replay", "correction-parity", "telemetry-quality"):
        attempt_id_val = getattr(a, "attempt_id", None)
        from_utc_val = getattr(a, "from_utc", None)
        to_utc_val = getattr(a, "to_utc", None)
        days_raw = getattr(a, "days", None)

        cmd_name = a.cmd.replace("-", "_")

        # --attempt-id and --days are mutually exclusive
        if attempt_id_val and days_raw is not None:
            _emit_result(
                {
                    "schema_version": 1,
                    "command": cmd_name,
                    "status": "ERROR",
                    "error": "INVALID_FLAGS",
                    "detail": "--attempt-id cannot be combined with --days",
                },
                output_json,
            )
            sys.exit(_EXIT_ERROR)

        # --to-utc requires --from-utc (also checked inside each function, but
        # validate here so errors are reported before any DB access)
        if to_utc_val and not from_utc_val:
            _emit_result(
                {
                    "schema_version": 1,
                    "command": cmd_name,
                    "status": "ERROR",
                    "error": "INVALID_FLAGS",
                    "detail": "--to-utc requires --from-utc",
                },
                output_json,
            )
            sys.exit(_EXIT_ERROR)

        # Validate --attempt-id is a valid UUID
        if attempt_id_val:
            try:
                _uuid_mod.UUID(attempt_id_val)
            except ValueError:
                _emit_result(
                    {
                        "schema_version": 1,
                        "command": cmd_name,
                        "status": "ERROR",
                        "error": "INVALID_FLAGS",
                        "detail": f"--attempt-id is not a valid UUID: {attempt_id_val!r}",
                    },
                    output_json,
                )
                sys.exit(_EXIT_ERROR)

        # Validate ISO-8601 timestamps and from-utc < to-utc ordering
        def _parse_iso(val: str, flag: str) -> datetime:
            try:
                return datetime.fromisoformat(val)
            except ValueError:
                _emit_result(
                    {
                        "schema_version": 1,
                        "command": cmd_name,
                        "status": "ERROR",
                        "error": "INVALID_FLAGS",
                        "detail": f"{flag} is not a valid ISO-8601 timestamp: {val!r}",
                    },
                    output_json,
                )
                sys.exit(_EXIT_ERROR)

        if from_utc_val:
            dt_from = _parse_iso(from_utc_val, "--from-utc")
            if to_utc_val:
                dt_to = _parse_iso(to_utc_val, "--to-utc")
                if dt_from >= dt_to:
                    _emit_result(
                        {
                            "schema_version": 1,
                            "command": cmd_name,
                            "status": "ERROR",
                            "error": "INVALID_FLAGS",
                            "detail": "--from-utc must be before --to-utc",
                        },
                        output_json,
                    )
                    sys.exit(_EXIT_ERROR)
        elif to_utc_val:
            _parse_iso(to_utc_val, "--to-utc")

        # Validate --days > 0
        days_val = days_raw if days_raw is not None else 14
        if days_raw is not None and days_raw <= 0:
            _emit_result(
                {
                    "schema_version": 1,
                    "command": cmd_name,
                    "status": "ERROR",
                    "error": "INVALID_FLAGS",
                    "detail": "--days must be a positive integer",
                },
                output_json,
            )
            sys.exit(_EXIT_ERROR)

        if a.cmd == "shadow-replay":
            shadow_replay(
                days=days_val,
                attempt_id=attempt_id_val,
                from_utc=from_utc_val,
                to_utc=to_utc_val,
                output_json=output_json,
            )
        elif a.cmd == "telemetry-quality":
            telemetry_quality(
                days=days_val,
                attempt_id=attempt_id_val,
                from_utc=from_utc_val,
                to_utc=to_utc_val,
                min_attempts=getattr(a, "min_attempts", 1),
                output_json=output_json,
            )
        else:
            correction_parity(
                days=days_val,
                attempt_id=attempt_id_val,
                from_utc=from_utc_val,
                to_utc=to_utc_val,
                output_json=output_json,
            )
    elif a.cmd == "tasks-overlap":
        tasks_overlap(output_json=output_json)
    elif a.cmd == "live-audit-compare":
        if a.days <= 0:
            _emit_result(
                {
                    "schema_version": 1,
                    "command": "live_audit_compare",
                    "status": "ERROR",
                    "error": "INVALID_FLAGS",
                    "detail": "--days must be a positive integer",
                },
                output_json,
            )
            sys.exit(_EXIT_ERROR)
        live_audit_compare(days=a.days, output_json=output_json)
    elif a.cmd == "multi-exam-coverage":
        multi_exam_coverage(
            required_exam_ids=getattr(a, "required_exam_id", None) or [],
            required_exam_slugs=getattr(a, "required_exam_slug", None) or [],
            min_questions=a.min_questions,
            from_utc=getattr(a, "from_utc", None),
            to_utc=getattr(a, "to_utc", None),
            days=getattr(a, "days", None),
            output_json=output_json,
        )


if __name__ == "__main__":
    main()
