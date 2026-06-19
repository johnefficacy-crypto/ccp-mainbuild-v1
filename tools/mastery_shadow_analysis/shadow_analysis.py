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

    Deliberately fails rather than printing apparently valid zero metrics
    when credentials are absent, because silent zero output is misleading
    during shadow gate validation.
    """
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_SERVICE_KEY", "").strip()
    if not url or not key:
        sys.exit(
            "ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.\n"
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


def _fetch_all(sb, table: str, query_fn, batch_size: int = 100_000) -> list[dict]:
    """Fetch rows with a single large-limit query (no cursor pagination needed
    for internal analysis jobs running against a known-bounded dataset)."""
    return query_fn(sb.table(table)).limit(batch_size).execute().data or []


# ─── compare ─────────────────────────────────────────────────────────────────

# Comparison population and denominators
# ───────────────────────────────────────
# Shadow rows: mock_mastery_shadow WHERE flag_state='shadow' AND decided_at >= since.
#   These represent what MasteryWriter (PR5) *would* write to user_topic_mastery.
#   Denominator for shadow statistics: len(shadow_rows).
#
# Live audit rows: user_topic_mastery_audit WHERE reason='mock_submit' AND at >= since.
#   These represent what MasteryWriter actually applied when flag=live.
#   Join key: (attempt_id, topic_id).
#
# Matched population: rows where both a shadow write AND a live audit entry
# exist for the same (attempt_id, topic_id). This is the population used for
# sign_agreement_pct and magnitude_corr. If the flag has always been 'shadow'
# no audit rows will exist and matched=0 triggers insufficient_sample=true.
#
# Outliers: shadow rows where |proposed_delta_db| > 15 (the ±0.15-unit cap).


def compare(days: int, output_json: bool = False) -> None:
    sb = _get_supabase()
    since = _since_iso(days)

    shadow_rows: list[dict] = _fetch_all(
        sb, "mock_mastery_shadow",
        lambda q: q
        .select("attempt_id,user_id,topic_id,proposed_delta_db,proposed_delta_db_unweighted,current_mastery_db,would_be_mastery_db,trust_level,flag_state")
        .eq("flag_state", "shadow")
        .gte("decided_at", since),
    )

    if not shadow_rows:
        _emit(
            {
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
            label=f"compare window_days={days}",
        )
        return

    # Fetch live audit rows for the same attempts to enable comparison.
    attempt_ids = list({r["attempt_id"] for r in shadow_rows if r.get("attempt_id")})
    audit_rows: list[dict] = []
    for i in range(0, len(attempt_ids), 500):
        batch = attempt_ids[i : i + 500]
        rows = (
            sb.table("user_topic_mastery_audit")
            .select("user_id,topic_id,attempt_id,delta_applied_db")
            .in_("attempt_id", batch)
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
        "window_days": days,
        "shadow_rows": len(shadow_rows),
        "matched_with_audit": len(matched_shadow),
        "sign_agreement_pct": sign_agreement_pct,
        "magnitude_corr": magnitude_corr,
        "outliers": outliers,
        "trust_breakdown": trust_breakdown,
        "insufficient_sample": not sufficient,
    }
    _emit(result, output_json, label=f"compare window_days={days}")


# ─── tasks-overlap ────────────────────────────────────────────────────────────

# Comparison population and denominators
# ───────────────────────────────────────
# PR5 tasks: mock_correction_tasks WHERE state='drafted' AND created_at >= since
#   AND the linked mock_tests.source_type = 'platform_attempt'.
#   These are corrections drafted by MasteryWriter via the platform submit flow.
#
# Rule-based tasks: same table, same window, but source_type != 'platform_attempt'
#   (manual_log or imported_result — corrections drafted through the review route).
#
# Overlap key: (user_id, topic, category) — identifies semantically equivalent
#   corrections regardless of origin.
#
# Denominators:
#   overlap_pct   = |PR5 ∩ rule| / |PR5 ∪ rule| × 100  (Jaccard)
#   pr5_only_pct  = |PR5 \ rule| / |PR5 ∪ rule| × 100
#   rule_only_pct = |rule \ PR5| / |PR5 ∪ rule| × 100


def tasks_overlap(days: int, output_json: bool = False) -> None:
    sb = _get_supabase()
    since = _since_iso(days)

    tasks_rows: list[dict] = _fetch_all(
        sb, "mock_correction_tasks",
        lambda q: q
        .select("id,mock_test_id,user_id,category,topic,state,created_at")
        .eq("state", "drafted")
        .gte("created_at", since),
    )

    if not tasks_rows:
        _emit(
            {
                "window_days": days,
                "total_tasks": 0,
                "pr5_tasks": 0,
                "rule_tasks": 0,
                "overlap": 0,
                "overlap_pct": None,
                "pr5_only_pct": None,
                "rule_only_pct": None,
                "insufficient_sample": True,
                "reason": "no drafted correction tasks in window",
            },
            output_json,
            label=f"tasks-overlap window_days={days}",
        )
        return

    mock_test_ids = list({r["mock_test_id"] for r in tasks_rows if r.get("mock_test_id")})
    mock_source_map: dict[str, str] = {}
    for i in range(0, len(mock_test_ids), 500):
        batch = mock_test_ids[i : i + 500]
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
    for r in tasks_rows:
        source = mock_source_map.get(r.get("mock_test_id") or "", "unknown")
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
        "window_days": days,
        "total_tasks": len(tasks_rows),
        "pr5_tasks": len(pr5_keys),
        "rule_tasks": len(rule_keys),
        "overlap": len(overlap),
        "overlap_pct": overlap_pct,
        "pr5_only_pct": pr5_only_pct,
        "rule_only_pct": rule_only_pct,
        "insufficient_sample": not sufficient,
    }
    _emit(result, output_json, label=f"tasks-overlap window_days={days}")


# ─── output ───────────────────────────────────────────────────────────────────


def _emit(result: dict[str, Any], output_json: bool, label: str) -> None:
    if output_json:
        print(json.dumps(result, indent=2))
        return

    print(label)
    if result.get("insufficient_sample"):
        reason = result.get("reason", f"matched={result.get('matched_with_audit', result.get('overlap', 0))}")
        print(f"  INSUFFICIENT_SAMPLE: {reason}")
    else:
        for key in ("sign_agreement_pct", "magnitude_corr", "outliers",
                    "overlap_pct", "pr5_only_pct", "rule_only_pct"):
            if key in result:
                print(f"  {key}={result[key]}")
    for key in ("shadow_rows", "matched_with_audit", "total_tasks", "pr5_tasks", "rule_tasks"):
        if key in result:
            print(f"  {key}={result[key]}")
    if result.get("trust_breakdown"):
        print("  trust_breakdown:")
        for trust, bd in result["trust_breakdown"].items():
            if bd.get("insufficient_sample"):
                print(f"    {trust}: INSUFFICIENT_SAMPLE count={bd['count']}")
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
    c = sp.add_parser("compare", help="Compare MasteryWriter shadow writes vs live audit trail")
    c.add_argument("--days", type=int, default=14)
    t = sp.add_parser("tasks-overlap", help="Compute PR5 vs rule-based correction task overlap")
    t.add_argument("--days", type=int, default=14)
    a = p.parse_args()
    if a.cmd == "compare":
        compare(a.days, output_json=a.output_json)
    else:
        tasks_overlap(a.days, output_json=a.output_json)


if __name__ == "__main__":
    main()
