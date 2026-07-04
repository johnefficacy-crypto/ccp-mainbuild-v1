# Distance to Release — v1 tracker (READ-ONLY derived view)

> **This file is a derived, read-only summary. Do NOT mutate status here.**
> The shared source of record is **`docs/status/career-copilot-checklist.md`** (per `AGENTS.md`);
> live evidence lives in the gate docs / `docs/audits/`. When a gate changes, update the
> checklist + its audit, then regenerate this view. Each row links its authoritative source.

**as_of:** `main @ 443a74e` · 2026-07-03
**Companion:** `docs/ops/v1-go-live-runbook.md` (the *how*) · `scripts/v1_release_verification.sql` (the *evidence*)
**Position:** late-stage beta — feature-complete-approaching, **not** production-ready.

**Legend:** ✅ CLEAR · 🟡 PARTIAL / validation-pending · ⛔ BLOCKED/open · ⏳ NOT STARTED
**Owner:** OPS = operator (staging/prod/Render/Supabase) · ENG = code change still needed

---

## Canonical gate status (operator-confirmed 2026-07-03)

```text
F1  Core features:                  COMPLETE
F3  Extraction archive race:        OPERATOR PASS
P3  Migration 182 validation:       OPERATOR PASS
P5  Telemetry + boundary sign-off:  OPERATOR PASS (freeze record MERGED, PR #864)
P6  Scheduler drain:                OPERATOR PASS
P7  Final candidate revalidation:   OPERATOR PASS
P8  14-day shadow window:           NOT STARTED — OPERATOR HOLD
P9  Bounded live canary:            NOT STARTED
P10 Live mastery flip:              BLOCKED
T0: NOT SET (deliberate operator hold)
```

---

## Gate table

| # | Gate | Owner | Status | Blocking on / clears when | Source |
|---|------|-------|--------|----------------------------|--------|
| **Feature-complete (Condition 1)** |
| F1 | Core features merged (RPC/RLS hardening, snapshot RPC, I9 containment, placeholder isolation) | ENG | ✅ CLEAR | on `main` | checklist |
| F2 | I9 deferred noncompliance frozen as v1/v2 — **D11, D12, D14, D06, D15** | ENG | 🟡 PARTIAL — D12 v1 IN PROGRESS; D06/D11/D14/D15 v2 deferred | **D12 v1:** full D05 evidence-policy engine (multi-PR program). **PR-1=#843 (schema) ✅ merged**, **PR-2=#849 (evaluator + Step 9 wiring) ✅ merged**; **PR-3 (planner enforcement) + PR-4 (evidence upload/review UI) OPEN**. Step 9 evidence-driven but fail-closed until PR-4 registers evidence (never false-ready). D06/D11/D14/D15 = operator-approved v2 deferral (2026-07-02). | checklist "I9 implementation" |
| F3 | Extraction archive-race terminalization | ENG+OPS | ✅ CLEAR | **OPERATOR PASS (2026-07-02, deployed SHA `920024c4`):** archive-race test ended with job `failed` (`error_code=document_archived`), document still `archived`, zero pages committed. | `audits/2026-07-02-f3-extraction-archive-race-validation.md` |
| **Production-ready (Condition 2)** |
| P1 | Apply full migration chain to staging→prod via the approved runner | OPS | ⏳ NOT STARTED — **recalc needed** | Ledger head is now **220** (not 212). Instructions must be recalculated against the live `schema_migrations` state. **parallel with P8 — does NOT gate T0** | runbook Phase 1 |
| P2 | RPC/RLS live verification (`scripts/v1_release_verification.sql`) + RLS real-JWT proof | OPS | 🟡 CODE-READY | needs P1, then a live run; no newer operator evidence in repo | verification script |
| P3 | Migration 182 operator validation | OPS | ✅ CLEAR | OPERATOR VALIDATED | `audits/2026-06-30-migration-182-operator-validation.md` |
| P4 | Migration 204 snapshot-review RPC validated on staging | OPS | 🟡 CODE-READY | needs P1; grant matrix + review→lock cycle; no newer operator evidence in repo | checklist (mig 204) |
| P5 | Telemetry (PR #800) staging validation + 36-file fingerprint boundary approval + freeze record | OPS | ✅ CLEAR | **OPERATOR PASS (2026-07-03), freeze record MERGED (PR #864):** checks 3A/3B/3C passed at source SHA `6171027a…`; 36-file boundary approved; freeze-candidate digest `51cd6928…`. | checklist rows P5 / PR #800; PR #864 |
| P6 | Scheduler verification (jobs/manual-run/drain) | OPS | ✅ CLEAR | OPERATOR PASS (2026-07-01) | `audits/2026-07-01-scheduler-drain-validation.md` |
| P7 | **PR-6** final-candidate revalidation rerun | OPS+ENG | ✅ CLEAR | OPERATOR PASS 2026-07-02 at deployed SHA `6ecfbed9`: all 12 start gates PASS; Gate A PASS; B–E,H–J PASS; F/G INSUFFICIENT_DATA exit 3 (permitted). | `audits/2026-07-02-p7-final-candidate-revalidation-6ecfbed9.md` |
| P8 | **PR-7 14-day shadow window** | OPS | ⏳ NOT STARTED — **OPERATOR HOLD (the floor)** | T0 deliberately held until in-flight development + E2E onboarding readiness complete; then re-pin at the final SHA + record `window_start`. **Any threshold miss restarts the 14 days.** | `pr7_shadow_gate_results.md` |
| P9 | PR-8 bounded live canary | OPS | ⏳ NOT STARTED | after P8 passes | `pr8_live_canary_plan.md` |
| P10 | PR-9 approval → flip `FF_MOCK_MASTERY_WRITES=live` | OPS | ⛔ BLOCKED | after P9 + P1/P2/P4 + sign-offs | `pr9_live_approval.md` |
| **Release-validated (Condition 3)** |
| R1 | Deployed-env E2E green (main user + admin journeys) | OPS | ⏳ NOT STARTED | Playwright vs deployed env; part of the pre-T0 E2E-onboarding readiness the operator is holding T0 for | runbook Phase 5 |
| R2 | Staging pilot (primary journey, no manual DB intervention) | OPS | ⏳ NOT STARTED | content + real users; **can overlap P8** | runbook Phase 5 |
| R3 | Prod canary + no open P0/P1 + perf/error targets | OPS | ⏳ NOT STARTED | after R1/R2 + P10 | runbook Phase 5 |
| R4 | Support / privacy / terms / operational ownership | OPS | ⏳ NOT STARTED | non-eng readiness; **parallel** | runbook Phase 5 |

---

## Recently-merged feature tracks (merged ≠ operator-complete)

These landed on `main` since the July-2 snapshot but are **not** release-validated — each still
needs some combination of live migration application, RLS/grant verification, click-through, or
live E2E before it counts toward production readiness:

- **D12 v1 (D05 evidence engine):** PR-1 #843 + PR-2 #849 merged; PR-4 (document-evidence registration + trust-review UI/API) code-landed on `claude/evidence-ui-97o0qf` (staging RLS/grant + click-through pending); PR-3 (planner shared authority) open.
- **J3 — Applied-vs-Appeared (PR #870):** typed candidate-count tables + atomic ratio switch merged; **live DB validation pending**.
- **J3 — Evidence-Coverage derivation (PR #867):** migration + endpoint code-landed; **staging validation pending**.
- **Content Studio (PR #868):** consolidated UI + route + writing-prompt operator surface merged.
- **Exam-intel cleanup:** phase-kind editor + PYQ phase selector (PR #871); EI-CLEAN-03/04 (#875); EI-CLEAN-05/06 (#876, current head). Remaining: **EI-CLEAN-07** (Setup phase-timeline regression + mutation governance).
- **Migration collision resolved:** J3 migration 219 vs PYQ-onboarding 219 → latter renumbered **220** with operator attestation of the deployed ledger mapping.

---

## Pre-T0 status

```text
F3:               complete (OPERATOR PASS)
P5:               complete (OPERATOR PASS; freeze record MERGED, PR #864)
Final T0 re-pin:  pending after development freeze (fresh verify at the final SHA)
window_start:     not recorded
```

F3 and P5 are **no longer** on the remaining-pre-T0 blocker list. T0 is a **deliberate operator
hold** — not a single pending fingerprint step — until in-flight development and E2E onboarding
readiness complete.

## Dependency edges (for an honest ETA, not a single number)

```
Serial spine to T0:
  F3 ✅ ─┐
  P5 ✅ ─┤ (freeze record MERGED #864)
  P6 ✅ ─┤
  P7 ✅ ─┴─► [finish pre-T0 dev + E2E-onboarding readiness]
                    │
                    ▼
        [choose final release SHA → deploy exact SHA (FE+BE)
         → confirm FF_MOCK_MASTERY_WRITES=shadow
         → re-run 36-file fingerprint verifier at that SHA (fresh, not 51cd6928 blindly)
         → record window_start] = T0
                    │
                    ▼
  P8  PR-7 14-day shadow   = 14 days HARD (restart on any threshold miss)   ← only fixed number
                    │
                    ▼
  P9 canary ─► P10 flip ─► R1 E2E ─► R3 prod canary
Parallelizable (do NOT gate T0): P1/P2/P4 live-migration (head 220) + RLS proof; R2 pilot; R4 readiness.
```

**ETA:** the only hard duration is **P8 = 14 days**. **A calendar estimate is not supportable now:**
T0 is intentionally held pending development + E2E-onboarding readiness, whose completion is
operator-paced and not fixed here. The prior "≈ 4 weeks from T0" framing is withdrawn until T0 is
actually set. P1/P2/P4 (migration chain to prod at ledger head 220 + RLS/RPC verification) are
parallel release gates that must complete before the P10 live flip but do not gate T0.
Do not quote a calendar date until `window_start` is recorded.

## Shortest path to T0

```text
Finish selected pre-T0 development
→ complete required live/E2E operator validation (incl. onboarding readiness)
→ choose final release SHA
→ deploy the exact SHA to frontend and backend
→ confirm FF_MOCK_MASTERY_WRITES=shadow
→ rerun the 36-file fingerprint verifier at that SHA (fresh attestation)
→ record exact UTC window_start
→ start P8 (14-day shadow window)
```

> **Now:** the pre-T0 floor is operator-held. F3 + P5 + P6 + P7 are all CLOSED. The remaining
> pre-T0 work is finishing in-flight development and the live/E2E-onboarding validation the
> operator is holding T0 for; then re-pin at the final SHA and record `window_start`. In parallel
> (not gating T0): P1/P2/P4 live-migration application at ledger head **220** + RLS/RPC verification.
