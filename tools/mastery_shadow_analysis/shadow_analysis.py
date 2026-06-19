from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

try:
    from supabase import create_client
except ImportError:  # pragma: no cover
    create_client = None  # type: ignore[assignment]


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _get_supabase():
    """Create Supabase admin client from env or exit with a clear error.

    Uses the repo-standard env var names. Deliberately fails rather than
    printing apparently valid zero metrics when credentials are absent.
    """
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    if not url or not key:
        sys.exit(
            "ERROR: NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.\n"
            "Refusing to print zero metrics on missing credentials."
        )
    if create_client is None:  # pragma: no cover
        sys.exit("ERROR: supabase-py not installed. Run: pip install supabase")
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
    """Pearson r for two equal-length lists of ≥2 values, or None."""
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
    batch_size: int = 5_000,
    order_by: str = "id",
) -> list[dict]:
    """Stable offset-based pagination with deterministic ordering.

    Uses range() + order() to paginate in consistent batches. The order_by
    column must be unique (e.g. 'id') to avoid row skips at page boundaries.
    """
    all_rows: list[dict] = []
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
        all_rows.extend(result)
        if len(result) < batch_size:
            break
        offset += batch_size
    return all_rows


# ─── shadow_replay ────────────────────────────────────────────────────────────

# Shadow self-consistency check
# ──────────────────────────────
# Population: mock_mastery_shadow WHERE flag_state='shadow' AND decided_at >= since.
#
# Checks:
#   arithmetic_violations  — rows where would_be ≠ clamp(current + delta, 0, 100),
#                            tolerance 0.01 db. Indicates a computation bug.
#   outliers               — rows where |proposed_delta_db| > 15 (the ±0.15-unit
#                            per-attempt cap; values outside this range should
#                            never reach the shadow table).
#   duplicate_keys         — rows sharing (attempt_id, topic_id, flag_state);
#                            migration 180 adds a unique index for this. Any
#                            duplicates here mean the migration hasn't applied
#                            or was bypassed.
#
# reference_sign_agreement is always DECISION_REQUIRED: no approved reference
# model exists in this codebase. Do not compare shadow rows to live audit rows
# here — audit rows only exist when FF_MOCK_MASTERY_WRITES=live (use
# live-audit-compare for canary validation instead).


def shadow_replay(days: int, output_json: bool = False) -> None:
    """Shadow write self-consistency check (main shadow gate command).

    Does NOT compare against live audit rows — audit rows only exist in live
    mode. Use `live-audit-compare` during a canary for live vs shadow
    sign-agreement metrics.
    """
    sb = _get_supabase()
    since = _since_iso(days)

    shadow_rows = _fetch_paginated(
        sb,
        "mock_mastery_shadow",
        lambda q: (
            q.select(
                "id,attempt_id,user_id,topic_id,proposed_delta_db,"
                "current_mastery_db,would_be_mastery_db,trust_level,flag_state,decided_at"
            )
            .eq("flag_state", "shadow")
            .gte("decided_at", since)
        ),
        order_by="id",
    )

    if not shadow_rows:
        _emit(
            {
                "command": "shadow_replay",
                "window_days": days,
                "shadow_rows": 0,
                "arithmetic_violations": 0,
                "outliers": 0,
                "duplicate_keys": 0,
                "trust_breakdown": {},
                "reference_sign_agreement": "DECISION_REQUIRED",
                "insufficient_sample": True,
                "reason": "no shadow rows in window",
            },
            output_json,
            label=f"shadow_replay window_days={days}",
        )
        return

    arithmetic_violations = 0
    outliers = 0
    seen_keys: dict[tuple, str] = {}
    duplicate_keys = 0

    for r in shadow_rows:
        # Arithmetic consistency: would_be = clamp(current + delta, 0, 100)
        try:
            delta = float(r.get("proposed_delta_db") or 0)
            current = float(r.get("current_mastery_db") or 0)
            would_be = float(r.get("would_be_mastery_db") or 0)
            expected = min(100.0, max(0.0, current + delta))
            if abs(expected - would_be) > 0.01:
                arithmetic_violations += 1
        except (TypeError, ValueError):
            arithmetic_violations += 1

        # Outlier: |delta| > 15 db violates the ±0.15-unit cap
        try:
            if abs(float(r.get("proposed_delta_db") or 0)) > 15:
                outliers += 1
        except (TypeError, ValueError):
            pass

        # Duplicate shadow key
        key = (r.get("attempt_id"), r.get("topic_id"), r.get("flag_state"))
        if key in seen_keys:
            duplicate_keys += 1
        else:
            seen_keys[key] = r.get("id") or ""

    # Per-trust-level breakdown
    trust_breakdown: dict[str, Any] = {}
    for trust in ("platform_verified", "self_reported", "admin_verified"):
        trust_rows = [r for r in shadow_rows if r.get("trust_level") == trust]
        if not trust_rows:
            continue
        t_violations = 0
        t_outliers = 0
        for r in trust_rows:
            try:
                delta = float(r.get("proposed_delta_db") or 0)
                current = float(r.get("current_mastery_db") or 0)
                would_be = float(r.get("would_be_mastery_db") or 0)
                expected = min(100.0, max(0.0, current + delta))
                if abs(expected - would_be) > 0.01:
                    t_violations += 1
            except (TypeError, ValueError):
                t_violations += 1
            try:
                if abs(float(r.get("proposed_delta_db") or 0)) > 15:
                    t_outliers += 1
            except (TypeError, ValueError):
                pass
        trust_breakdown[trust] = {
            "count": len(trust_rows),
            "arithmetic_violations": t_violations,
            "outliers": t_outliers,
        }

    result: dict[str, Any] = {
        "command": "shadow_replay",
        "window_days": days,
        "shadow_rows": len(shadow_rows),
        "arithmetic_violations": arithmetic_violations,
        "outliers": outliers,
        "duplicate_keys": duplicate_keys,
        "trust_breakdown": trust_breakdown,
        "reference_sign_agreement": "DECISION_REQUIRED",
        "insufficient_sample": False,
    }
    _emit(result, output_json, label=f"shadow_replay window_days={days}")


# ─── live_audit_compare ───────────────────────────────────────────────────────

# Live audit comparison (canary-only)
# ────────────────────────────────────
# Shadow rows: mock_mastery_shadow WHERE flag_state='shadow' AND decided_at >= since.
# Live audit rows: user_topic_mastery_audit WHERE reason='mock_submit'
#   AND attempt_id in (shadow attempt_ids).
# Join key: (attempt_id, topic_id).
#
# CANARY-ONLY: audit rows only exist when FF_MOCK_MASTERY_WRITES=live has been
# active. Running against a shadow-only deployment will produce matched=0 and
# insufficient_sample=True, which is the correct result.


def live_audit_compare(days: int, output_json: bool = False) -> None:
    """Compare shadow writes against live audit trail.

    CANARY-ONLY — requires FF_MOCK_MASTERY_WRITES=live to have been active.
    Running against a shadow-only deployment correctly returns
    insufficient_sample=True (matched=0 is not an error; it means no live
    writes have happened).
    """
    sb = _get_supabase()
    since = _since_iso(days)

    shadow_rows = _fetch_paginated(
        sb,
        "mock_mastery_shadow",
        lambda q: (
            q.select(
                "attempt_id,user_id,topic_id,proposed_delta_db,"
                "proposed_delta_db_unweighted,current_mastery_db,"
                "would_be_mastery_db,trust_level,flag_state"
            )
            .eq("flag_state", "shadow")
            .gte("decided_at", since)
        ),
        order_by="id",
    )

    if not shadow_rows:
        _emit(
            {
                "command": "live_audit_compare",
                "window_days": days,
                "shadow_rows": 0,
                "matched_with_audit": 0,
                "sign_agreement_pct": None,
                "magnitude_corr": None,
                "outliers": 0,
                "trust_breakdown": {},
                "insufficient_sample": True,
                "reason": "no shadow rows in window",
            },
            output_json,
            label=f"live_audit_compare window_days={days}",
        )
        return

    # Fetch live audit rows for the shadow attempts; filter by reason='mock_submit'
    # to exclude rollback rows that would corrupt the sign-agreement metric.
    attempt_ids = list({r["attempt_id"] for r in shadow_rows if r.get("attempt_id")})
    audit_rows: list[dict] = []
    for i in range(0, len(attempt_ids), 500):
        batch = attempt_ids[i: i + 500]
        rows = (
            sb.table("user_topic_mastery_audit")
            .select("user_id,topic_id,attempt_id,delta_applied_db")
            .in_("attempt_id", batch)
            .eq("reason", "mock_submit")
            .execute()
            .data
            or []
        )
        audit_rows.extend(rows)

    audit_map: dict[tuple, float] = {}
    for r in audit_rows:
        if r.get("attempt_id") and r.get("topic_id") and r.get("delta_applied_db") is not None:
            audit_map[(r["attempt_id"], r["topic_id"])] = float(r["delta_applied_db"])

    # Build matched vectors.
    matched_shadow: list[float] = []
    matched_audit: list[float] = []
    for r in shadow_rows:
        key = (r.get("attempt_id"), r.get("topic_id"))
        if key in audit_map and r.get("proposed_delta_db") is not None:
            matched_shadow.append(float(r["proposed_delta_db"]))
            matched_audit.append(audit_map[key])

    MIN_SAMPLE = 10
    sufficient = len(matched_shadow) >= MIN_SAMPLE

    sign_agreement_pct: float | None = None
    magnitude_corr: float | None = None
    if sufficient:
        agreements = sum(
            1 for s, a in zip(matched_shadow, matched_audit) if _sign(s) == _sign(a)
        )
        sign_agreement_pct = round(agreements / len(matched_shadow) * 100, 2)
        magnitude_corr = _pearson(matched_shadow, matched_audit)

    outliers = sum(
        1
        for r in shadow_rows
        if abs(float(r.get("proposed_delta_db") or 0)) > 15
    )

    # Per-trust-level breakdown.
    trust_breakdown: dict[str, Any] = {}
    for trust in ("platform_verified", "self_reported", "admin_verified"):
        trust_rows = [r for r in shadow_rows if r.get("trust_level") == trust]
        if not trust_rows:
            continue
        t_shadow: list[float] = []
        t_audit: list[float] = []
        for r in trust_rows:
            key = (r.get("attempt_id"), r.get("topic_id"))
            if key in audit_map and r.get("proposed_delta_db") is not None:
                t_shadow.append(float(r["proposed_delta_db"]))
                t_audit.append(audit_map[key])

        t_sufficient = len(t_shadow) >= MIN_SAMPLE
        t_sign: float | None = None
        t_corr: float | None = None
        if t_sufficient:
            t_agr = sum(1 for s, a in zip(t_shadow, t_audit) if _sign(s) == _sign(a))
            t_sign = round(t_agr / len(t_shadow) * 100, 2)
            t_corr = _pearson(t_shadow, t_audit)

        trust_breakdown[trust] = {
            "count": len(trust_rows),
            "matched": len(t_shadow),
            "sign_agreement_pct": t_sign,
            "magnitude_corr": t_corr,
            "insufficient_sample": not t_sufficient,
        }

    result: dict[str, Any] = {
        "command": "live_audit_compare",
        "window_days": days,
        "shadow_rows": len(shadow_rows),
        "matched_with_audit": len(matched_shadow),
        "sign_agreement_pct": sign_agreement_pct,
        "magnitude_corr": magnitude_corr,
        "outliers": outliers,
        "trust_breakdown": trust_breakdown,
        "insufficient_sample": not sufficient,
    }
    _emit(result, output_json, label=f"live_audit_compare window_days={days}")


# ─── tasks_overlap ────────────────────────────────────────────────────────────

# Correction task overlap
# ───────────────────────
# PR5 tasks: mock_correction_tasks WHERE state='drafted' AND created_at >= since
#   AND mock_tests.source_type = 'platform_attempt'.
#   The `topic` column for these rows contains a canonical topic_id (UUID),
#   set by MasteryWriter.
#
# Rule-based tasks: same table, same window, source_type != 'platform_attempt'.
#   The `topic` column for these rows contains a display label (e.g. "Polity"),
#   NOT a canonical topic_id.
#
# LIMITATION: The `topic` column has different semantics in the two populations.
# Cross-population overlap via (user_id, topic, category) is NOT MEANINGFUL
# because the same string value refers to a canonical UUID in PR5 rows and a
# display label in rule-based rows. This metric reports each population's size
# separately and notes the semantic mismatch. A canonical `topic_id` column
# is required for a valid overlap comparison.


def tasks_overlap(days: int, output_json: bool = False) -> None:
    """Compute PR5 vs rule-based correction task overlap.

    NOTE: Cross-population overlap is NOT MEANINGFUL because the `topic`
    column uses canonical topic_ids for PR5 corrections and display labels
    for rule-based corrections. Counts are reported per-population.
    """
    sb = _get_supabase()
    since = _since_iso(days)

    tasks_rows = _fetch_paginated(
        sb,
        "mock_correction_tasks",
        lambda q: (
            q.select("id,mock_test_id,user_id,category,topic,state,created_at")
            .eq("state", "drafted")
            .gte("created_at", since)
        ),
        order_by="id",
    )

    if not tasks_rows:
        _emit(
            {
                "command": "tasks_overlap",
                "window_days": days,
                "total_tasks": 0,
                "pr5_tasks": 0,
                "rule_tasks": 0,
                "overlap": 0,
                "overlap_pct": None,
                "pr5_only_pct": None,
                "rule_only_pct": None,
                "unknown_source": 0,
                "insufficient_sample": True,
                "reason": "no drafted correction tasks in window",
                "topic_semantics_note": (
                    "topic column: canonical topic_id for PR5 rows, "
                    "display label for rule-based rows — cross-population "
                    "overlap is NOT MEANINGFUL"
                ),
            },
            output_json,
            label=f"tasks-overlap window_days={days}",
        )
        return

    mock_test_ids = list({r["mock_test_id"] for r in tasks_rows if r.get("mock_test_id")})
    mock_source_map: dict[str, str] = {}
    for i in range(0, len(mock_test_ids), 500):
        batch = mock_test_ids[i: i + 500]
        rows = (
            sb.table("mock_tests")
            .select("id,source_type")
            .in_("id", batch)
            .execute()
            .data
            or []
        )
        for r in rows:
            mock_source_map[r["id"]] = r.get("source_type") or "manual_log"

    pr5_keys: set[tuple] = set()
    rule_keys: set[tuple] = set()
    unknown_source: int = 0

    for r in tasks_rows:
        mock_id = r.get("mock_test_id") or ""
        source = mock_source_map.get(mock_id)
        if source is None:
            unknown_source += 1
            continue
        # For PR5 (platform_attempt): topic is canonical topic_id.
        # For rule-based: topic is a display label. Keys are reported
        # separately; overlap across populations is noted as NOT MEANINGFUL.
        key = (r.get("user_id"), r.get("topic"), r.get("category"))
        if source == "platform_attempt":
            pr5_keys.add(key)
        else:
            rule_keys.add(key)

    overlap = pr5_keys & rule_keys
    union = pr5_keys | rule_keys
    total_union = len(union)

    MIN_SAMPLE = 10
    sufficient = total_union >= MIN_SAMPLE

    overlap_pct = round(len(overlap) / total_union * 100, 2) if total_union else None
    pr5_only = pr5_keys - rule_keys
    rule_only = rule_keys - pr5_keys
    pr5_only_pct = round(len(pr5_only) / total_union * 100, 2) if total_union else None
    rule_only_pct = round(len(rule_only) / total_union * 100, 2) if total_union else None

    result: dict[str, Any] = {
        "command": "tasks_overlap",
        "window_days": days,
        "total_tasks": len(tasks_rows),
        "pr5_tasks": len(pr5_keys),
        "rule_tasks": len(rule_keys),
        "overlap": len(overlap),
        "overlap_pct": overlap_pct,
        "pr5_only_pct": pr5_only_pct,
        "rule_only_pct": rule_only_pct,
        "unknown_source": unknown_source,
        "insufficient_sample": not sufficient,
        "topic_semantics_note": (
            "topic column: canonical topic_id for PR5 rows, "
            "display label for rule-based rows — cross-population "
            "overlap is NOT MEANINGFUL"
        ),
    }
    _emit(result, output_json, label=f"tasks-overlap window_days={days}")


# ─── output ───────────────────────────────────────────────────────────────────


def _emit(result: dict[str, Any], output_json: bool, label: str) -> None:
    if output_json:
        print(json.dumps(result, indent=2))
        return

    cmd = result.get("command", label)
    print(f"{cmd} window_days={result.get('window_days')}")
    if result.get("insufficient_sample"):
        reason = result.get("reason", f"matched={result.get('matched_with_audit', result.get('overlap', 0))}")
        print(f"  INSUFFICIENT_SAMPLE: {reason}")
    else:
        for key in (
            "arithmetic_violations", "outliers", "duplicate_keys",
            "reference_sign_agreement",
            "sign_agreement_pct", "magnitude_corr",
            "overlap_pct", "pr5_only_pct", "rule_only_pct",
        ):
            if key in result:
                print(f"  {key}={result[key]}")
    for key in ("shadow_rows", "matched_with_audit", "total_tasks", "pr5_tasks", "rule_tasks", "unknown_source"):
        if key in result:
            print(f"  {key}={result[key]}")
    if result.get("topic_semantics_note"):
        print(f"  note: {result['topic_semantics_note']}")
    if result.get("trust_breakdown"):
        print("  trust_breakdown:")
        for trust, bd in result["trust_breakdown"].items():
            if bd.get("insufficient_sample"):
                print(f"    {trust}: INSUFFICIENT_SAMPLE count={bd['count']}")
            elif "arithmetic_violations" in bd:
                print(
                    f"    {trust}: arithmetic_violations={bd['arithmetic_violations']}"
                    f" outliers={bd['outliers']}"
                    f" count={bd['count']}"
                )
            else:
                print(
                    f"    {trust}: sign_agreement_pct={bd['sign_agreement_pct']}"
                    f" magnitude_corr={bd['magnitude_corr']}"
                    f" count={bd['count']}"
                )


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main() -> None:
    p = argparse.ArgumentParser(prog="shadow-analysis")
    p.add_argument("--json", dest="output_json", action="store_true", help="Machine-readable JSON output")
    sp = p.add_subparsers(dest="cmd", required=True)

    sr = sp.add_parser("shadow-replay", help="Shadow self-consistency check (main shadow gate command)")
    sr.add_argument("--days", type=int, default=14)

    lac = sp.add_parser("live-audit-compare", help="Compare shadow vs live audit (CANARY-ONLY)")
    lac.add_argument("--days", type=int, default=14)

    to = sp.add_parser("tasks-overlap", help="PR5 vs rule-based correction task overlap")
    to.add_argument("--days", type=int, default=14)

    a = p.parse_args()
    if a.cmd == "shadow-replay":
        shadow_replay(a.days, output_json=a.output_json)
    elif a.cmd == "live-audit-compare":
        live_audit_compare(a.days, output_json=a.output_json)
    else:
        tasks_overlap(a.days, output_json=a.output_json)


if __name__ == "__main__":
    main()
