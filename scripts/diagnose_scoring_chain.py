#!/usr/bin/env python3
"""Read-only diagnostic for the exam-intelligence scoring chain.

Walks the full path a topic must travel before the deterministic planner can
rank it, and reports which gate is actually blocking:

    pyq_papers (verified, in scope)
        -> pyq_questions (verified)
            -> pyq_question_topic_tags (primary + verified)
                -> exam_topic_score_snapshots (locked)      [score_snapshots.py]
                                                            |
    syllabus_topic_mentions (verified, in scope) -----------+
                                                            v
                                        exam_topic_coverage (locked)
                                                            |
                                                            v
                                                  planner / study plan

Scope matters and is easy to get wrong: score_snapshots and coverage_derivation
read phase-scoped inputs with `exam_phase_id = <id>` and exam-wide inputs with
`exam_phase_id IS NULL`. Evidence written at one scope is invisible to a run at
the other. This script reports both scopes side by side so a mismatch is
obvious rather than discovered after the review work is done.

Writes nothing. Safe to run against production.

Usage:

    export CCP_API_BASE=https://... CCP_ADMIN_JWT=...
    python scripts/diagnose_scoring_chain.py \
        --exam-id 5466e62f-7382-4a38-ba96-2fe5fbfeaba2 \
        --exam-phase-id 626ec667-4bbf-4420-8715-48c5b83e0d11
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import requests

CMS = "/api/admin/exam-intelligence-cms"
INTEL = "/api/admin/exam-intelligence"


class Reader:
    def __init__(self, base: str, token: str, timeout: int = 30) -> None:
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        r = self.session.get(f"{self.base}{path}", params=params or {}, timeout=self.timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"GET {path} -> {r.status_code}: {r.text[:200]}")
        return r.json() or {}

    def count(self, path: str, params: dict[str, Any] | None = None) -> int:
        """Total row count for a listing endpoint, without fetching the rows."""
        data = self.get(path, {**(params or {}), "limit": 1})
        total = data.get("total")
        if total is None:  # endpoints that return a bare list
            items = data.get("items") or data.get("snapshots") or []
            return len(items)
        return int(total)

    def all_items(self, path: str, params: dict[str, Any] | None = None,
                  *, key: str = "items", page: int = 200) -> list[dict]:
        out: list[dict] = []
        offset = 0
        while True:
            data = self.get(path, {**(params or {}), "limit": page, "offset": offset})
            items = data.get(key) or []
            out.extend(items)
            if len(items) < page:
                return out
            offset += page


def hr(title: str) -> None:
    print(f"\n{'=' * 68}\n{title}\n{'=' * 68}")


def diagnose(r: Reader, exam_id: str, phase_id: str | None) -> list[str]:
    """Print the chain state. Returns a list of blocking-gate descriptions."""
    blockers: list[str] = []

    # ── 1. PYQ papers ──────────────────────────────────────────────────────
    hr("1. PYQ papers")
    papers = r.all_items(f"{CMS}/pyq-papers", {"exam_id": exam_id})
    if not papers:
        print("  none for this exam")
        blockers.append("No PYQ papers exist for this exam.")
    by_scope: dict[Any, dict[str, int]] = {}
    for p in papers:
        scope = p.get("exam_phase_id")
        by_scope.setdefault(scope, {}).setdefault(p.get("trust_status", "?"), 0)
        by_scope[scope][p.get("trust_status", "?")] += 1
    for scope, statuses in by_scope.items():
        label = "exam-wide (phase NULL)" if scope is None else f"phase {scope}"
        marker = "  <-- target scope" if scope == phase_id else ""
        print(f"  {label}: {statuses}{marker}")

    scoped = [p for p in papers if p.get("exam_phase_id") == phase_id]
    in_scope = [p for p in scoped if p.get("trust_status") == "verified"]
    print(f"\n  papers at target scope: {len(scoped)} "
          f"({len(in_scope)} verified, {len(scoped) - len(in_scope)} not)")
    if not in_scope:
        blockers.append(
            "No verified PYQ papers at the target scope — scoring reads "
            "pyq_papers WHERE trust_status='verified' AND exam_phase_id matches, "
            "so it will produce zero snapshots."
        )

    years = sorted({p.get("year") for p in scoped if p.get("year")})
    if years:
        print(f"  years present at target scope: {years}")

    # ── 2. Questions on those papers ───────────────────────────────────────
    # Count questions on EVERY in-scope paper, not just verified ones. When
    # the papers are still pending, the verified-only view reports 0/0 and
    # hides the actual size of the tagging workload sitting behind the gate.
    hr("2. PYQ questions at target scope")
    verified_q = 0
    total_q = 0
    for p in sorted(scoped, key=lambda x: (x.get("year") or 0)):
        pid = p["id"]
        v = r.count(f"{CMS}/pyq-questions", {"pyq_paper_id": pid, "reviewer_status": "verified"})
        t = r.count(f"{CMS}/pyq-questions", {"pyq_paper_id": pid})
        verified_q += v
        total_q += t
        print(f"  {p.get('year')} {pid[:8]}… [{p.get('trust_status')}]: "
              f"{t} questions, {v} verified")
    print(f"\n  total questions at target scope: {total_q} ({verified_q} verified)")
    if total_q and verified_q == 0:
        blockers.append(
            f"{total_q} questions exist at the target scope but none are "
            "reviewer_status='verified' — scoring counts only verified questions."
        )
    if total_q:
        print(f"\n  tagging workload if this scope is pursued: up to {total_q} "
              "questions\n  need exactly one verified primary topic tag each.")

    # ── 3. Primary verified topic tags ─────────────────────────────────────
    hr("3. Primary + verified topic tags")
    print("  (frequency is primary-only: one verified question contributes at")
    print("   most one count, through its primary tag)")
    tags_verified = r.count(f"{CMS}/pyq-question-topic-tags", {"reviewer_status": "verified"})
    tags_pending = r.count(f"{CMS}/pyq-question-topic-tags", {"reviewer_status": "pending"})
    tags_all = r.count(f"{CMS}/pyq-question-topic-tags", {})
    print(f"\n  tags across all exams: {tags_all} total, "
          f"{tags_verified} verified, {tags_pending} pending")
    print("  NOTE: the tags endpoint has no exam filter, so these are global")
    print("        counts — treat them as an upper bound for this exam.")
    if verified_q and tags_verified == 0:
        blockers.append(
            "No verified primary topic tags anywhere — untagged questions "
            "contribute nothing to any topic's frequency."
        )

    # ── 4. Score snapshots ─────────────────────────────────────────────────
    hr("4. Score snapshots")
    for scope_label, scope_params in (
        ("exam-wide (phase NULL)", {}),
        (f"phase {phase_id}", {"exam_phase_id": phase_id} if phase_id else None),
    ):
        if scope_params is None:
            continue
        try:
            data = r.get(f"{INTEL}/exams/{exam_id}/score-snapshots",
                         {**scope_params, "limit": 200})
        except RuntimeError as exc:
            print(f"  {scope_label}: read failed — {exc}")
            continue
        rows = data.get("snapshots") or []
        statuses: dict[str, int] = {}
        for s in rows:
            statuses[s.get("status", "?")] = statuses.get(s.get("status", "?"), 0) + 1
        marker = "  <-- target scope" if scope_params else ""
        print(f"  {scope_label}: {data.get('total', len(rows))} rows {statuses}{marker}")

    locked_scoped = 0
    if phase_id:
        try:
            d = r.get(f"{INTEL}/exams/{exam_id}/score-snapshots",
                      {"exam_phase_id": phase_id, "status": "locked", "limit": 1})
            locked_scoped = int(d.get("total") or 0)
        except RuntimeError:
            pass
    if phase_id and locked_scoped == 0:
        blockers.append(
            f"No locked score snapshots at phase {phase_id} — coverage derivation "
            "reads snapshots at the SAME scope it reads mentions, so every derived "
            "row would land with exam_priority_score=0 (undifferentiated)."
        )

    # ── 5. Syllabus mentions ───────────────────────────────────────────────
    hr("5. Syllabus topic mentions")
    for label, params in (
        ("verified", {"exam_id": exam_id, "reviewer_status": "verified"}),
        ("pending", {"exam_id": exam_id, "reviewer_status": "pending"}),
    ):
        n = r.count(f"{CMS}/syllabus-topic-mentions", params)
        print(f"  {label}: {n}")

    if phase_id:
        scoped = r.all_items(f"{CMS}/syllabus-topic-mentions",
                             {"exam_id": exam_id, "exam_phase_id": phase_id})
        by_status: dict[str, int] = {}
        for m in scoped:
            by_status[m.get("reviewer_status", "?")] = by_status.get(m.get("reviewer_status", "?"), 0) + 1
        print(f"  at phase {phase_id}: {by_status or 'none'}")
        if by_status.get("verified", 0) == 0 and by_status.get("pending", 0):
            blockers.append(
                f"{by_status['pending']} mentions at the target phase are still "
                "pending — derivation reads verified mentions only."
            )

    # ── 6. Coverage ────────────────────────────────────────────────────────
    hr("6. Exam topic coverage (planner input)")
    cov = r.all_items(f"{CMS}/exam-topic-coverage", {"exam_id": exam_id})
    by_key: dict[tuple, int] = {}
    for c in cov:
        key = (c.get("exam_phase_id"), c.get("reviewer_status"), c.get("source_basis"))
        by_key[key] = by_key.get(key, 0) + 1
    if not by_key:
        print("  none")
    for (ph, status, basis), n in sorted(by_key.items(), key=lambda x: str(x[0])):
        label = "exam-wide" if ph is None else f"phase {ph[:8]}…"
        marker = "  <-- target scope" if ph == phase_id else ""
        print(f"  {label:<22} {status:<14} {basis:<18} {n}{marker}")

    locked_total = sum(n for (ph, st, _), n in by_key.items() if st == "locked")
    print(f"\n  locked rows (any scope): {locked_total}  <- planner readiness")
    if locked_total == 0:
        blockers.append(
            "No locked exam_topic_coverage rows — the planner treats this exam "
            "as not planner-ready."
        )

    return blockers


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exam-id", required=True)
    p.add_argument("--exam-phase-id", default=None,
                   help="Phase to treat as the target scope (e.g. the Mains template phase)")
    p.add_argument("--api-base", default=None)
    args = p.parse_args()

    base = args.api_base or os.environ.get("CCP_API_BASE")
    token = os.environ.get("CCP_ADMIN_JWT", "")
    if not base or not token:
        print("error: set CCP_API_BASE and CCP_ADMIN_JWT", file=sys.stderr)
        return 2

    blockers = diagnose(Reader(base, token), args.exam_id, args.exam_phase_id)

    hr("BLOCKING GATES")
    if not blockers:
        print("  none — the chain is complete at the target scope.")
    for i, b in enumerate(blockers, 1):
        print(f"  {i}. {b}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
