"""D05 evidence-policy evaluator (D12 v1, PR-2).

Given a selected cycle's phases, resolves the D05 phase-scoped evidence
requirements from ``exam_evidence_requirements`` (+ active overrides) and evaluates
each *blocking* requirement against the relational evidence registered in
``exam_document_evidence`` / ``exam_document_evidence_roles`` (migration 211) and the
existing verified corpora, applying the D05 independent predicates:

  1. correct exam / cycle / phase scope,
  2. evidence role matches the required class,
  3. authoritative source        — ``source_registry`` active + official + not discovery-only,
  4. human trust review verified — ``exam_document_evidence.trust_status = 'verified'``,
  5. not superseded/rejected,
  6. extraction succeeded        — latest ``text_extract`` job ``succeeded`` (when text use required).

Used by ``cycle_readiness`` Step 9 for ``required_phases_complete``. Until documents are
registered as evidence (PR-4 upload/review), no document-backed requirement is satisfied, so
Step 9 stays fail-closed (never false-ready) — the correct posture.

Scope note: this evaluator gates the **phase-scoped** subset of the D05 matrix (the phases'
"required cycle/phase facts"). Exam/cycle-scoped evidence (verified source, primary cycle
document, corrigendum, …) is seeded in migration 212 and consumed by the document/source steps;
`light` planner-exposure applicability + planner enforcement land in PR-3. Conditions that need
the exposure signal (`study_os_enabled`, `pattern_details_exposed`) evaluate conservatively
(applies) here — fail-closed / over-require — until PR-3 wires the canonical signal.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("career_copilot.exam_intelligence.document_policy")

# D05 §1 canonical classified phase kinds; NULL/'other' are unclassified (block).
CLASSIFIED_PHASE_KINDS = (
    "objective_written", "descriptive_written", "mixed_written",
    "interview", "physical_test", "medical", "document_verification",
)

_PAGE = 500


# D05 §6: operational-cycle policy applies to expected/open/active cycles.
_OPERATIONAL_CYCLE_STATUSES = ("expected", "open", "active")


def _condition_applies(code: str, *, phase_kind: str | None = None, cycle_status: str | None = None) -> bool:
    """Whether a requirement's condition_code is active in this context.

    Fail-closed defaults: exposure-dependent conditions evaluate to True (require the
    evidence) until PR-3 wires the canonical Study-OS/planner exposure signal.
    """
    if code == "always":
        return True
    if code == "objective_pyq_used_for_scoring":
        return phase_kind in ("objective_written", "mixed_written")
    if code == "cycle_is_operational":
        return (cycle_status or "") in _OPERATIONAL_CYCLE_STATUSES
    if code in ("study_os_enabled", "pattern_details_exposed"):
        return True  # conservative / over-require until PR-3
    # cycle_dates_published / corrigendum_known / application_tracking_enabled are advisory
    # (gate_effect=warn) in the seed, so they never enter the blocking set; if a blocking rule
    # ever carries one, fail closed (treat as applicable).
    return True


def _fetch_all(sb, table: str, select: str, eq: dict[str, Any]) -> list[dict]:
    q = sb.table(table).select(select)
    for k, v in eq.items():
        q = q.eq(k, v)
    return q.limit(2000).execute().data or []


def _latest_text_extract_succeeded(sb, doc_asset_ids: list[str]) -> set[str]:
    """Return the set of document_asset ids whose LATEST text_extract job succeeded (D06)."""
    if not doc_asset_ids:
        return set()
    jobs = (
        sb.table("document_processing_jobs")
        .select("id, document_id, status, created_at")
        .eq("job_type", "text_extract")
        .in_("document_id", doc_asset_ids)
        .limit(5000)
        .execute()
        .data
        or []
    )
    latest: dict[str, dict] = {}
    for j in jobs:
        d = j.get("document_id")
        if not d:
            continue
        cur = latest.get(d)
        key = (j.get("created_at", ""), j.get("id", ""))
        if cur is None or key > (cur.get("created_at", ""), cur.get("id", "")):
            latest[d] = j
    return {d for d, j in latest.items() if j.get("status") == "succeeded"}


class _EvidenceIndex:
    """One-shot load of the exam's registered evidence + supporting predicates."""

    def __init__(self, sb, exam_id: str):
        self.evidence = _fetch_all(
            sb, "exam_document_evidence",
            "id, document_asset_id, exam_id, exam_cycle_id, exam_phase_id, "
            "source_registry_id, trust_status, superseded_by_id",
            {"exam_id": exam_id},
        )
        ev_ids = [e["id"] for e in self.evidence if e.get("id")]
        self.roles = []
        if ev_ids:
            self.roles = (
                sb.table("exam_document_evidence_roles")
                .select("document_evidence_id, evidence_kind, exam_cycle_id, exam_phase_id")
                .in_("document_evidence_id", ev_ids)
                .limit(5000)
                .execute()
                .data
                or []
            )
        # source authority: active + official + not discovery-only
        src_ids = [e.get("source_registry_id") for e in self.evidence if e.get("source_registry_id")]
        self.authoritative_src: set[str] = set()
        if src_ids:
            for s in (
                sb.table("source_registry")
                .select("id, is_active, is_official_source, discovery_only")
                .in_("id", list(set(src_ids)))
                .limit(2000)
                .execute()
                .data
                or []
            ):
                if s.get("is_active") and s.get("is_official_source") and not s.get("discovery_only"):
                    self.authoritative_src.add(s["id"])
        self.extracted_ok = _latest_text_extract_succeeded(
            sb, [e.get("document_asset_id") for e in self.evidence if e.get("document_asset_id")]
        )
        self._by_ev = {e["id"]: e for e in self.evidence if e.get("id")}
        # verified pyq papers for the exam (D10 exam-wide); count for pyq_paper requirements.
        self.verified_pyq_papers = sum(
            1 for p in (
                sb.table("pyq_papers").select("id, trust_status").eq("exam_id", exam_id)
                .limit(5000).execute().data or []
            ) if p.get("trust_status") == "verified"
        )

    def satisfies(self, req: dict, *, cycle_id: str, phase_id: str) -> bool:
        kind = req["evidence_kind"]
        minimum = int(req.get("minimum_count") or 1)

        if kind == "pyq_paper":
            # PYQ evidence is verified in pyq_papers (exam-wide corpus).
            return self.verified_pyq_papers >= minimum

        # document-backed: count registered, verified, in-scope, authoritative, extracted roles.
        need_src = bool(req.get("requires_verified_source"))
        need_extract = bool(req.get("requires_extraction"))
        matched = 0
        for role in self.roles:
            if role.get("evidence_kind") != kind:
                continue
            ev = self._by_ev.get(role.get("document_evidence_id"))
            if not ev:
                continue
            if ev.get("trust_status") != "verified" or ev.get("superseded_by_id") is not None:
                continue
            # Scope: evidence must apply to this phase. A role/evidence may be phase-scoped
            # (exact phase), cycle-scoped (this cycle, phase null), or exam-wide (both null).
            ev_phase = role.get("exam_phase_id") or ev.get("exam_phase_id")
            ev_cycle = role.get("exam_cycle_id") or ev.get("exam_cycle_id")
            if ev_phase is not None and ev_phase != phase_id:
                continue
            if ev_cycle is not None and ev_cycle != cycle_id:
                continue
            if need_src and ev.get("source_registry_id") not in self.authoritative_src:
                continue
            if need_extract and ev.get("document_asset_id") not in self.extracted_ok:
                continue
            matched += 1
            if matched >= minimum:
                return True
        return False


def _resolve_requirements(sb, management_mode: str) -> tuple[dict[str, list[dict]], list[dict]]:
    """Return (phase-scoped blocking requirements by phase_kind, cycle-scoped blocking list).

    Only hard/blocking requirements (required + gate_effect=block) gate completeness.
    """
    rows = _fetch_all(
        sb, "exam_evidence_requirements",
        "id, phase_kind, evidence_kind, requirement_level, gate_effect, scope, "
        "minimum_count, requires_verified_source, requires_extraction, condition_code, is_active",
        {"management_mode": management_mode},
    )
    by_kind: dict[str, list[dict]] = {}
    cycle_reqs: list[dict] = []
    for r in rows:
        if r.get("is_active") is False:
            continue
        if r.get("requirement_level") != "required" or r.get("gate_effect") != "block":
            continue
        if r.get("scope") == "phase" and r.get("phase_kind"):
            by_kind.setdefault(r["phase_kind"], []).append(r)
        elif r.get("scope") == "cycle":
            cycle_reqs.append(r)
    return by_kind, cycle_reqs


def _exam_level_overrides(sb, exam_id: str) -> dict[str, dict]:
    """Active exam-level (cycle & phase null) overrides by evidence_kind (one active per key)."""
    out: dict[str, dict] = {}
    for o in _fetch_all(
        sb, "exam_evidence_requirement_overrides",
        "exam_id, exam_cycle_id, exam_phase_id, evidence_kind, requirement_level, "
        "gate_effect, minimum_count, requires_verified_source, requires_extraction, is_active",
        {"exam_id": exam_id},
    ):
        if o.get("is_active") is False:
            continue
        if o.get("exam_cycle_id") is None and o.get("exam_phase_id") is None:
            out[o["evidence_kind"]] = o
    return out


def _effective_req(req: dict, overrides: dict[str, dict]) -> dict | None:
    """Merge a base requirement with its exam-level override; return None if no longer a blocker.

    An override may downgrade requirement_level/gate_effect (dropping the blocker) or tighten
    predicates (minimum_count, requires_*).
    """
    ov = overrides.get(req["evidence_kind"])
    eff = dict(req)
    if ov is not None:
        for f in ("requirement_level", "gate_effect", "minimum_count",
                  "requires_verified_source", "requires_extraction"):
            if ov.get(f) is not None:
                eff[f] = ov[f]
    if eff.get("requirement_level") == "required" and eff.get("gate_effect") == "block":
        return eff
    return None


def evaluate_required_phases_complete(
    sb, exam_id: str, cycle_id: str, management_mode: str, phases: list[dict],
    *, cycle_status: str | None = None,
) -> dict[str, Any]:
    """Evaluate D12 required-phase completeness for the selected cycle.

    ``phases`` is the list of exam_phases rows for the cycle (each with id, phase_kind, status).
    Completeness holds when: every non-cancelled phase is canonically classified AND every
    applicable blocking phase-scoped requirement for its phase_kind is satisfied, AND every
    applicable blocking cycle-scoped requirement (the cycle's "required cycle facts", e.g. the
    primary cycle document) is satisfied — each against verified, in-scope, authoritative,
    extracted evidence registered in exam_document_evidence.

    Returns {complete, evaluated_phases, unclassified_phases, unmet_requirements:[...]}.
    """
    active = [p for p in phases if (p.get("status") or "") != "cancelled"]
    if not active:
        return {"complete": False, "evaluated_phases": 0, "unclassified_phases": 0,
                "unmet_requirements": [], "reason": "no_phases"}

    by_kind, cycle_reqs = _resolve_requirements(sb, management_mode)
    overrides = _exam_level_overrides(sb, exam_id)
    index = _EvidenceIndex(sb, exam_id)

    unclassified = 0
    unmet: list[dict] = []

    # Cycle-scoped "required cycle facts" (evaluated once; evidence scoped to the cycle).
    for req in cycle_reqs:
        eff = _effective_req(req, overrides)
        if eff is None:
            continue
        if not _condition_applies(eff.get("condition_code") or "always", cycle_status=cycle_status):
            continue
        if not index.satisfies(eff, cycle_id=cycle_id, phase_id=None):
            unmet.append({"scope": "cycle", "evidence_kind": eff["evidence_kind"],
                          "minimum_count": int(eff.get("minimum_count") or 1)})

    # Phase-scoped requirements per classified phase.
    for p in active:
        pk = p.get("phase_kind") or ""
        if pk not in CLASSIFIED_PHASE_KINDS:
            unclassified += 1
            continue
        for req in by_kind.get(pk, []):
            eff = _effective_req(req, overrides)
            if eff is None:
                continue
            if not _condition_applies(eff.get("condition_code") or "always", phase_kind=pk):
                continue
            if not index.satisfies(eff, cycle_id=cycle_id, phase_id=p["id"]):
                unmet.append({"scope": "phase", "phase_id": p["id"], "phase_kind": pk,
                              "evidence_kind": eff["evidence_kind"],
                              "minimum_count": int(eff.get("minimum_count") or 1)})

    complete = unclassified == 0 and not unmet
    return {
        "complete": complete,
        "evaluated_phases": len(active),
        "unclassified_phases": unclassified,
        "unmet_requirements": unmet,
    }
