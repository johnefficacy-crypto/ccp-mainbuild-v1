# Distance to Release — v1 tracker (READ-ONLY derived view)

> **This file is a derived, read-only summary. Do NOT mutate status here.**
> The shared source of record is **`docs/status/career-copilot-checklist.md`** (per `AGENTS.md`);
> live evidence lives in the gate docs / `docs/audits/`. When a gate changes, update the
> checklist + its audit, then regenerate this view. Each row links its authoritative source.

**as_of:** `main @ 3484a92` · 2026-06-30
**Companion:** `docs/ops/v1-go-live-runbook.md` (the *how*) · `scripts/v1_release_verification.sql` (the *evidence*)
**Position:** late-stage beta — feature-complete-approaching, **not** production-ready.

**Legend:** ✅ CLEAR · 🟡 PARTIAL / validation-pending · ⛔ BLOCKED/open · ⏳ NOT STARTED
**Owner:** OPS = operator (staging/prod/Render/Supabase) · ENG = code change still needed

---

## Gate table

| # | Gate | Owner | Status | Blocking on / clears when | Source |
|---|------|-------|--------|----------------------------|--------|
| **Feature-complete (Condition 1)** |
| F1 | Core features merged (RPC/RLS hardening, snapshot RPC, I9 containment, placeholder isolation) | ENG | ✅ CLEAR | on `main` | checklist |
| F2 | I9 deferred noncompliance frozen as v1/v2 — **D11, D12, D14, D06, D15** | ENG | ⛔ OPEN | product decision + (if v1) code; **D14** = applicability-from-`gate_class` approximation | checklist "I9 implementation" |
| F3 | Extraction archive-race terminalization | ENG | ⛔ OPEN (partial merged) | #788/#780 + mig `202` merged; **residual:** `finalize_document_extraction` → `document_archived` makes the caller raise **without terminalizing**, so the claimed job can stay `running`. Fix caller + add mid-flight regression | runbook CHECK 3 / extraction caller |
| **Production-ready (Condition 2)** |
| P1 | Apply full migration chain to staging→prod (head `204`) via the approved runner | OPS | ⏳ NOT STARTED | **precedes P2/P4** | runbook Phase 1 |
| P2 | RPC/RLS live verification (`scripts/v1_release_verification.sql`) + RLS real-JWT proof | OPS | 🟡 CODE-READY | needs P1, then a live run | verification script |
| P3 | Migration 182 operator validation | OPS | ✅ CLEAR | OPERATOR VALIDATED | `audits/2026-06-30-migration-182-operator-validation.md` |
| P4 | Migration 204 snapshot-review RPC validated on staging | OPS | 🟡 CODE-READY | needs P1; grant matrix + review→lock cycle | checklist (mig 204) |
| P5 | PR-7 36-file fingerprint boundary approved + re-pinned at deployed SHA | OPS | 🟡 OPERATOR-APPROVAL ONLY | verifier code/tooling closed (#803/#814, ref digest `f2ee2c40…`); needs **PR #800 staging delivery validation + boundary sign-off**; fingerprint is reference-only until re-pinned at `window_start` | `pr7_shadow_gate_results.md` |
| P6 | Scheduler verification (jobs/manual-run/drain) | OPS | 🟡 PARTIAL PASS | startup + sweeper registration + repeat sweeps ✅ at staging `daaddaae`; **remaining:** `/api/admin/jobs` payload, manual sweeper invocation, named pending-job drain | `audits/2026-06-30-mastery-staging-preflight.md` |
| P7 | **PR-6** final-candidate revalidation rerun (clear Gate 9) | OPS | ⛔ `gate_failed` | needs P6 scheduler evidence first; deploy current main (`3484a923`, post-PR-814) to staging; rerun 12 gates with `FF=shadow` on the pinned deployed SHA | `pr6_final_candidate_revalidation.md` |
| P8 | **PR-7 14-day shadow window** | OPS | ⏳ NOT STARTED — **THE FLOOR** | full prerequisite chain below; **any threshold miss restarts the 14 days** | `pr7_shadow_gate_results.md` |
| P9 | PR-8 bounded live canary | OPS | ⏳ NOT STARTED | after P8 passes | `pr8_live_canary_plan.md` |
| P10 | PR-9 approval → flip `FF_MOCK_MASTERY_WRITES=live` | OPS | ⛔ BLOCKED | after P9 + sign-offs | `pr9_live_approval.md` |
| **Release-validated (Condition 3)** |
| R1 | Deployed-env E2E green (main user + admin journeys) | OPS | ⏳ NOT STARTED | Playwright vs deployed env | runbook Phase 5 |
| R2 | Staging pilot (primary journey, no manual DB intervention) | OPS | ⏳ NOT STARTED | content + real users; **can overlap P8** | runbook Phase 5 |
| R3 | Prod canary + no open P0/P1 + perf/error targets | OPS | ⏳ NOT STARTED | after R1/R2 + P10 | runbook Phase 5 |
| R4 | Support / privacy / terms / operational ownership | OPS | ⏳ NOT STARTED | non-eng readiness; **parallel** | runbook Phase 5 |

---

## P8 (PR-7) start prerequisites — the exact chain

The 14-day clock may start **only** when ALL hold (do not start on P5+P7 alone):
1. **F3** extraction terminalization fixed (no jobs can strand `running`).
2. **P6** scheduler evidence complete (jobs/manual-run/**drain**) — required *before* the PR-6 rerun.
3. **P7** PR-6 PASS (Gate 9 cleared) on the deployed candidate SHA.
4. **P5** PR #800 staging delivery validation + explicit 36-file boundary approval.
5. Deployed SHA **matches the approved candidate**, with **continuous `FF_MOCK_MASTERY_WRITES=shadow`**.
6. A **freshly computed + attested fingerprint at that deployed SHA** (re-pin from the `f2ee2c40…` reference).
7. An exact UTC **`window_start`** recorded.

Call the moment all 7 hold **T0**. T0 has not occurred.

## Dependency edges (for an honest ETA, not a single number)

```
Serial spine to T0:
  F3 ─┐
  P1 ─┴─► P2, P4          (P1 must precede the live P2/P4 verification)
  P6(drain) ─► P7(PR-6)   (scheduler evidence before the rerun)
  P5(boundary+#800) ──────┐
  P7(PR-6 PASS) ──────────┴─► [re-pin fingerprint + set window_start] = T0
        │
        ▼
  P8  PR-7 14-day shadow   = 14 days HARD (restart on any miss)   ← only fixed number
        │
        ▼
  P9 canary ─► P10 flip ─► R1 E2E ─► R3 prod canary
Parallelizable: F2 decision, R2 pilot (overlaps P8), R4 readiness.
```

**ETA:** the only hard duration is **P8 = 14 days**. Pre-T0 work (F3 + P1→P4 + P5 + P6 drain +
P7) is operator-paced — realistically a **handful of days** but not reproducibly fixed here, so
it is expressed as a range, not a promise. Post-window (P9→R3) is a **few days**. **Floor ≈ 3
weeks from T0**, *longer* if the shadow window restarts or PR-6 needs multiple reruns. Do not
quote a calendar date until T0 is set.

## What reaches T0 fastest (next actions)
1. **ENG:** fix **F3** terminalization; record the **F2** (D11/D12/**D14**/D06/D15) v1-vs-v2 decision.
2. **OPS:** **P1** apply migrations → **P2** run the verification script (+RLS JWT proof) → **P4** validate mig 204.
3. **OPS:** finish **P6** scheduler drain (`/api/admin/jobs` payload + manual sweeper invocation + named pending-job drain proof) → deploy current main (`3484a923`) to staging → **P5** PR #800 validation + boundary approval → **P7** PR-6 rerun on the pinned deployed SHA.
4. When the 7 prerequisites hold → re-pin the fingerprint, set **`window_start`** (T0), start **P8**.
