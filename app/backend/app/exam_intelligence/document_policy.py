"""D05 evidence-policy evaluator (D12 v1, PR-2).

Resolves the D05 evidence requirements for a selected cycle's phases (deterministic base-policy
specificity + phase>cycle>exam override precedence, with expiry) and evaluates each *blocking*
requirement against the relational evidence registered in ``exam_document_evidence`` /
``exam_document_evidence_roles`` (migration 211) and the verified PYQ corpus, applying the D05
independent predicates:

  1. correct exam / cycle / phase scope,
  2. evidence role matches the required class,
  3. authoritative source        — ``source_registry`` active + official + not discovery-only,
  4. human trust review verified — ``exam_document_evidence.trust_status = 'verified'``,
  5. not superseded/rejected,
  6. extraction succeeded        — latest ``text_extract`` job ``succeeded`` (when required).

Used by ``cycle_readiness`` Step 9 for ``required_phases_complete``. Until documents are
registered as evidence (PR-4), no document-backed requirement is satisfied, so Step 9 stays
fail-closed (never false-ready).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("career_copilot.exam_intelligence.document_policy")

# D05 §1 canonical classified phase kinds; NULL/'other' are unclassified (block).
CLASSIFIED_PHASE_KINDS = (
    "objective_written", "descriptive_written", "mixed_written",
    "interview", "physical_test", "medical", "document_verification",
)

# D05 §6: operational-cycle policy applies to expected/open/active cycles only.
OPERATIONAL_CYCLE_STATUSES = ("expected", "open", "active")

_PAGE = 500


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _fetch_paged(sb, table: str, select: str, eq: dict[str, Any]) -> list[dict]:
    """Paginated read (avoids silent truncation from a fixed .limit())."""
    rows: list[dict] = []
    offset = 0
    while True:
        q = sb.table(table).select(select)
        for k, v in eq.items():
            q = q.eq(k, v)
        batch = q.range(offset, offset + _PAGE - 1).execute().data or []
        rows.extend(batch)
        if len(batch) < _PAGE:
            break
        offset += _PAGE
    return rows


def _condition_applies(code: str, *, phase_kind: str | None, cycle_status: str | None) -> bool:
    """Whether a requirement's condition_code is active in this context.

    Fail-closed defaults: any condition we cannot canonically evaluate returns True (require the
    evidence — over-block, never false-ready).
      * ``objective_pyq_used_for_scoring``: there is no canonical scoring-use signal in the
        schema yet, so this is a CONSERVATIVE default — objective/mixed written phases are
        assumed to use objective scoring (answer key required). Not a real scoring-use check.
      * ``study_os_enabled`` / ``pattern_details_exposed``: no exposure signal until PR-3 -> True.
    """
    if code == "always":
        return True
    if code == "cycle_is_operational":
        return (cycle_status or "") in OPERATIONAL_CYCLE_STATUSES
    if code == "objective_pyq_used_for_scoring":
        return phase_kind in ("objective_written", "mixed_written")  # conservative default
    # study_os_enabled / pattern_details_exposed / cycle_dates_published / corrigendum_known /
    # application_tracking_enabled -> fail closed (applies).
    return True


# ─── policy resolution ───────────────────────────────────────────────────────
_OVERRIDE_FIELDS = (
    "requirement_level", "gate_effect", "minimum_count", "minimum_distinct_years",
    "requires_verified_source", "requires_human_review", "requires_extraction",
    "condition_code", "condition_params",
)


def _resolve_base(reqs: list[dict], *, exam_type: str | None, phase_kind: str | None,
                  scope: str) -> dict[str, dict]:
    """Most-specific base requirement per evidence_kind for (exam_type, phase_kind, scope).

    D05 specificity: exact(mode+exam_type+phase_kind) > mode+exam_type > mode+phase_kind >
    mode default. Higher rank wins; the unique identity index guarantees no ties.
    """
    best: dict[str, tuple[int, dict]] = {}
    for r in reqs:
        if r.get("scope") != scope or r.get("is_active") is False:
            continue
        rpk, ret = r.get("phase_kind"), r.get("exam_type")
        if rpk not in (None, phase_kind) or ret not in (None, exam_type):
            continue
        rank = (2 if (ret is not None and ret == exam_type) else 0) + \
               (1 if (rpk is not None and rpk == phase_kind) else 0)
        k = r["evidence_kind"]
        cur = best.get(k)
        if cur is None or rank > cur[0]:
            best[k] = (rank, r)
    return {k: v[1] for k, v in best.items()}


def _resolve_overrides(overrides: list[dict], *, cycle_id: str, phase_id: str | None
                       ) -> dict[str, dict]:
    """Most-specific ACTIVE, unexpired override per evidence_kind (phase > cycle > exam)."""
    now = _now()
    best: dict[str, tuple[int, dict]] = {}
    for o in overrides:
        if o.get("is_active") is False:
            continue
        exp = _parse_ts(o.get("expires_at"))
        if exp is not None and exp <= now:
            continue  # expired override is ignored
        oc, op = o.get("exam_cycle_id"), o.get("exam_phase_id")
        if op is not None:
            if phase_id is None or op != phase_id:
                continue
            rank = 3
        elif oc is not None:
            if oc != cycle_id:
                continue
            rank = 2
        else:
            rank = 1  # exam-level
        k = o["evidence_kind"]
        cur = best.get(k)
        if cur is None or rank > cur[0]:
            best[k] = (rank, o)
    return {k: v[1] for k, v in best.items()}


def _effective_requirements(base: dict[str, dict], overrides: dict[str, dict]) -> list[dict]:
    """Merge base + override per evidence_kind; return the ones that remain BLOCKING.

    A TARGETED override (non-null base_requirement_id) applies only to the selected base row with
    that id; an untargeted override (null base_requirement_id) applies to the evidence_kind
    generally and may add a requirement where no base exists. Overrides can promote a warn base to
    blocking or downgrade a blocker to advisory/not-applicable.
    """
    kinds = set(base) | set(overrides)
    out: list[dict] = []
    for k in kinds:
        base_row = base.get(k)
        ov = overrides.get(k)
        if ov is not None and ov.get("base_requirement_id") is not None:
            if base_row is None or base_row.get("id") != ov.get("base_requirement_id"):
                ov = None  # targets a different base variant -> not applicable to this selection
        if base_row is None and ov is None:
            continue
        eff = dict(base_row) if base_row else {
            "evidence_kind": k, "satisfied_by": "document_asset",
            "requirement_level": "required", "gate_effect": "block", "minimum_count": 1,
            "requires_verified_source": True, "requires_human_review": True,
            "requires_extraction": False, "condition_code": "always"}
        if ov is not None:
            for f in _OVERRIDE_FIELDS:
                if ov.get(f) is not None:
                    eff[f] = ov[f]
        if eff.get("requirement_level") == "required" and eff.get("gate_effect") == "block":
            out.append(eff)
    return out


# ─── evidence evaluation ─────────────────────────────────────────────────────
class _EvidenceIndex:
    """One-shot paginated load of the exam's registered evidence + supporting predicates."""

    def __init__(self, sb, exam_id: str):
        self.evidence = _fetch_paged(
            sb, "exam_document_evidence",
            "id, document_asset_id, exam_id, exam_cycle_id, exam_phase_id, "
            "source_registry_id, trust_status, superseded_by_id",
            {"exam_id": exam_id},
        )
        ev_ids = [e["id"] for e in self.evidence if e.get("id")]
        self.roles: list[dict] = []
        for ev_id in ev_ids:
            self.roles.extend(_fetch_paged(
                sb, "exam_document_evidence_roles",
                "document_evidence_id, evidence_kind, exam_cycle_id, exam_phase_id",
                {"document_evidence_id": ev_id},
            ))
        self.extracted_ok = self._latest_extract_ok(
            sb, [e.get("document_asset_id") for e in self.evidence if e.get("document_asset_id")])
        self._by_ev = {e["id"]: e for e in self.evidence if e.get("id")}
        # verified, phase-tagged PYQ papers grouped by phase (D05 per-phase compatibility).
        papers = [p for p in _fetch_paged(
            sb, "pyq_papers", "id, exam_id, exam_phase_id, year, pyq_source_id, trust_status",
            {"exam_id": exam_id})
            if p.get("trust_status") == "verified" and p.get("exam_phase_id")]
        self.pyq_by_phase: dict[str, list[dict]] = {}
        for p in papers:
            self.pyq_by_phase.setdefault(p["exam_phase_id"], []).append(p)
        # Resolve the PYQ source-authority chain: pyq_papers.pyq_source_id -> pyq_sources.source_id
        # -> source_registry, so requires_verified_source is a REAL authority check (not just a
        # non-null link).
        pyq_source_to_reg: dict[str, str | None] = {}
        for psid in {p.get("pyq_source_id") for p in papers if p.get("pyq_source_id")}:
            for ps in _fetch_paged(sb, "pyq_sources", "id, source_id", {"id": psid}):
                pyq_source_to_reg[ps["id"]] = ps.get("source_id")
        # Load every referenced source_registry row once (document evidence + PYQ sources).
        reg_ids = {e.get("source_registry_id") for e in self.evidence if e.get("source_registry_id")}
        reg_ids |= {r for r in pyq_source_to_reg.values() if r}
        self.authoritative_src: set[str] = set()
        for sid in reg_ids:
            for s in _fetch_paged(sb, "source_registry",
                                  "id, is_active, is_official_source, discovery_only", {"id": sid}):
                if s.get("is_active") and s.get("is_official_source") and not s.get("discovery_only"):
                    self.authoritative_src.add(s["id"])
        self.authoritative_pyq_sources: set[str] = {
            psid for psid, reg in pyq_source_to_reg.items() if reg in self.authoritative_src}

    @staticmethod
    def _latest_extract_ok(sb, doc_ids: list[str]) -> set[str]:
        latest: dict[str, dict] = {}
        for d in {d for d in doc_ids if d}:
            for j in _fetch_paged(sb, "document_processing_jobs",
                                  "id, document_id, status, created_at, job_type",
                                  {"document_id": d, "job_type": "text_extract"}):
                cur = latest.get(d)
                key = (j.get("created_at", ""), j.get("id", ""))
                if cur is None or key > (cur.get("created_at", ""), cur.get("id", "")):
                    latest[d] = j
        return {d for d, j in latest.items() if j.get("status") == "succeeded"}

    def satisfies(self, req: dict, *, cycle_id: str, phase_id: str | None) -> bool:
        kind = req["evidence_kind"]
        minimum = int(req.get("minimum_count") or 1)

        if kind == "pyq_paper":
            # D05: one verified COMPATIBLE paper per written phase (phase-tagged, not exam-wide),
            # with the source-authority predicate resolved through pyq_sources -> source_registry.
            if phase_id is None:
                return False
            papers = self.pyq_by_phase.get(phase_id, [])
            if req.get("requires_verified_source"):
                papers = [p for p in papers
                          if p.get("pyq_source_id") in self.authoritative_pyq_sources]
            min_years = req.get("minimum_distinct_years")
            if min_years:
                years = {p.get("year") for p in papers if p.get("year") is not None}
                return len(years) >= int(min_years)
            return len(papers) >= minimum

        need_src = bool(req.get("requires_verified_source"))
        need_extract = bool(req.get("requires_extraction"))
        # requires_human_review: when true, only trust_status='verified' counts; when false, any
        # USABLE lifecycle counts (still reject rejected/superseded).
        rhr = req.get("requires_human_review")
        need_review = True if rhr is None else bool(rhr)
        # Count DISTINCT satisfying evidence registrations (not role rows) toward minimum_count.
        matched_docs: set[str] = set()
        for role in self.roles:
            if role.get("evidence_kind") != kind:
                continue
            ev = self._by_ev.get(role.get("document_evidence_id"))
            if not ev:
                continue
            ts = ev.get("trust_status")
            if ev.get("superseded_by_id") is not None or ts == "rejected":
                continue  # unusable lifecycle regardless of policy
            if need_review and ts != "verified":
                continue
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
            matched_docs.add(ev["id"])
            if len(matched_docs) >= minimum:
                return True
        return False


def evaluate_required_phases_complete(
    sb, exam_id: str, cycle_id: str, management_mode: str, phases: list[dict],
    *, exam_type: str | None = None, cycle_status: str | None = None,
) -> dict[str, Any]:
    """Evaluate D12 required-phase completeness for the selected cycle.

    Completeness holds when: the cycle is operational; every non-cancelled phase is canonically
    classified AND every applicable blocking phase-scoped requirement for its phase_kind is
    satisfied; AND every applicable blocking cycle-scoped requirement is satisfied — each against
    verified, in-scope, authoritative, extracted evidence. Deterministic base-policy specificity
    and phase>cycle>exam override precedence (with expiry) are applied.

    Returns {complete, evaluated_phases, unclassified_phases, unmet_requirements:[...], reason?}.
    """
    active = [p for p in phases if (p.get("status") or "") != "cancelled"]
    if not active:
        return {"complete": False, "evaluated_phases": 0, "unclassified_phases": 0,
                "unmet_requirements": [], "reason": "no_phases"}
    # D05 §6: activation policy applies only to operational cycles.
    if (cycle_status or "") not in OPERATIONAL_CYCLE_STATUSES:
        return {"complete": False, "evaluated_phases": len(active), "unclassified_phases": 0,
                "unmet_requirements": [], "reason": "cycle_not_operational"}

    reqs = _fetch_paged(
        sb, "exam_evidence_requirements",
        "id, exam_type, phase_kind, evidence_kind, satisfied_by, requirement_level, gate_effect, "
        "scope, minimum_count, minimum_distinct_years, requires_verified_source, "
        "requires_human_review, requires_extraction, condition_code, condition_params, is_active",
        {"management_mode": management_mode},
    )
    overrides = _fetch_paged(
        sb, "exam_evidence_requirement_overrides",
        "exam_id, base_requirement_id, exam_cycle_id, exam_phase_id, evidence_kind, "
        "requirement_level, gate_effect, minimum_count, minimum_distinct_years, "
        "requires_verified_source, requires_human_review, requires_extraction, condition_code, "
        "condition_params, expires_at, is_active",
        {"exam_id": exam_id},
    )
    index = _EvidenceIndex(sb, exam_id)

    unclassified = 0
    unmet: list[dict] = []

    # Cycle-scoped "required cycle facts" (evaluated once).
    cyc_base = _resolve_base(reqs, exam_type=exam_type, phase_kind=None, scope="cycle")
    cyc_ov = _resolve_overrides(overrides, cycle_id=cycle_id, phase_id=None)
    for eff in _effective_requirements(cyc_base, cyc_ov):
        if not _condition_applies(eff.get("condition_code") or "always",
                                  phase_kind=None, cycle_status=cycle_status):
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
        base = _resolve_base(reqs, exam_type=exam_type, phase_kind=pk, scope="phase")
        ov = _resolve_overrides(overrides, cycle_id=cycle_id, phase_id=p["id"])
        effs = _effective_requirements(base, ov)
        # Fail-closed by CODE, not by seed: a classified phase with NO seeded policy at all for
        # its (mode, exam_type, phase_kind) AND no effective governing requirement is NOT
        # vacuously complete — an unseeded/regressed policy cannot verify activation-readiness.
        # (Requirements explicitly resolved to not_applicable by an operator OVERRIDE on an
        # existing base are governed intent and remain allowed.)
        if not base and not effs:
            unmet.append({"scope": "phase", "phase_id": p["id"], "phase_kind": pk,
                          "evidence_kind": None, "reason": "no_blocking_policy"})
            continue
        for eff in effs:
            if not _condition_applies(eff.get("condition_code") or "always",
                                      phase_kind=pk, cycle_status=cycle_status):
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
