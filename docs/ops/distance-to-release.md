# Distance to Release — v1 tracker (READ-ONLY derived view)

> **This file is a derived, read-only summary. Do NOT mutate status here.**
> The shared source of record is **`docs/status/career-copilot-checklist.md`** (per `AGENTS.md`);
> live evidence lives in the gate docs / `docs/audits/`. When a gate changes, update the
> checklist + its audit, then regenerate this view. Each row links its authoritative source.

**as_of:** `main @ 0ffad093` · 2026-07-02
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
| F3 | Extraction archive-race terminalization | ENG | 🟡 CODE-FIXED, VALIDATION PENDING | Caller now calls `_fail()` before raising on `document_archived` (and `finalize_failed`); mid-flight regression test added. Needs live/staging validation no jobs strand `running` after archive race. | `text_extract.py:476-492` + regression test |
| **Production-ready (Condition 2)** |
| P1 | Apply full migration chain to staging→prod (head `204`) via the approved runner | OPS | ⏳ NOT STARTED | **precedes P2/P4** | runbook Phase 1 |
| P2 | RPC/RLS live verification (`scripts/v1_release_verification.sql`) + RLS real-JWT proof | OPS | 🟡 CODE-READY | needs P1, then a live run | verification script |
| P3 | Migration 182 operator validation | OPS | ✅ CLEAR | OPERATOR VALIDATED | `audits/2026-06-30-migration-182-operator-validation.md` |
| P4 | Migration 204 snapshot-review RPC validated on staging | OPS | 🟡 CODE-READY | needs P1; grant matrix + review→lock cycle | checklist (mig 204) |
| P5 | PR-7 36-file fingerprint boundary approved + re-pinned at deployed SHA | OPS | 🟡 OPERATOR-APPROVAL ONLY | verifier code/tooling closed (#803/#814, ref digest `f2ee2c40…`); needs **PR #800 staging delivery validation + boundary sign-off**; fingerprint is reference-only until re-pinned at `window_start` | `pr7_shadow_gate_results.md` |
| P6 | Scheduler verification (jobs/manual-run/drain) | OPS | ✅ CLEAR | OPERATOR PASS (2026-07-01, candidate SHA `b9bd9d7b`): job `cf2a8f44` drained in 19.67 s; `manual: absent`, `derivations: 1` on capturing tick; all `pr1_scheduler_drain_verification.md` steps met. | `audits/2026-07-01-scheduler-drain-validation.md` |
| P7 | **PR-6** final-candidate revalidation rerun (clear Gate A) | OPS+ENG | ✅ CLEAR | OPERATOR PASS 2026-07-02 at deployed SHA `6ecfbed956cc467c70ad50c4f7dce3b1a2443d25`: all 12 start gates PASS; Gate 4 fresh fingerprint `b3cec4ac…` (36 files); Gate A PASS (`review_state` updated, notes-only preserved, null-guard held, 409 on breakdowns); Gates B–E, H–J PASS; F/G INSUFFICIENT_DATA exit 3 (permitted). PR #840 (code fix) + PR #850 (PASS audit) merged. | `audits/2026-07-02-p7-final-candidate-revalidation-6ecfbed9.md` |
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
2. **P6** scheduler evidence complete (jobs/manual-run/**drain**) — ✅ OPERATOR PASS (2026-07-01).
3. **P7** PR-6 PASS (Gate A cleared) on the deployed candidate SHA — ✅ OPERATOR PASS (2026-07-02, SHA `6ecfbed9`).
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
  P6(drain) ─► P7(PR-6) ✅  (both CLOSED 2026-07-01 / 2026-07-02)
  P5(boundary+#800) ──────┐
  [P7 PASS — done] ───────┴─► [re-pin fingerprint + set window_start] = T0
        │
        ▼
  P8  PR-7 14-day shadow   = 14 days HARD (restart on any miss)   ← only fixed number
        │
        ▼
  P9 canary ─► P10 flip ─► R1 E2E ─► R3 prod canary
Parallelizable: F2 decision, R2 pilot (overlaps P8), R4 readiness.
```

**ETA:** the only hard duration is **P8 = 14 days**. Remaining pre-T0 work (F3 + P1→P4 + P5;
**P6 done, P7 OPERATOR PASS 2026-07-02**) is operator-/eng-paced — realistically a **handful of
days** but not reproducibly fixed here, so it is expressed as a range, not a promise.
Post-window (P9→R3) is a **few days**. **Floor ≈ 3 weeks from T0**, *longer* if the shadow window
restarts. Do not quote a calendar date until T0 is set.

## Shortest path right now

**P6 is CLOSED** (PR #827 merged). **P7 is CLOSED** (OPERATOR PASS 2026-07-02 at SHA `6ecfbed9`;
PR #840 code fix + PR #850 PASS audit merged). **F3 is CODE-FIXED**
(PR #834 merged: `_update_job` guard + `finalize_failed` regression test; needs live/staging
validation only). **P5** is the active operator blocker running in parallel with F3 validation.

### F3 — CODE-FIXED, VALIDATION PENDING (PR #834, merged)
`finalize_document_extraction` → `document_archived` now calls `_fail()` before raising (no job
can strand `running`); mid-flight regression test added. No code work remains — ENG dependency is
MET. Live/staging confirmation still required before T0.

### P7 — OPERATOR PASS (2026-07-02, SHA `6ecfbed9`)
CLOSED. Full evidence in `docs/audits/2026-07-02-p7-final-candidate-revalidation-6ecfbed9.md`.
Gate 4 fresh fingerprint: `b3cec4accf3bdf729d3f68d9694dcbb5fc69e96bfbc165f5739973de7738da8b`
(36 files; one file differs from reference `f2ee2c40…`: `canonical.py`, the Gate A fix).
Gate A PASS: `review_state` changed `unreviewed→reviewed`; notes-only preserved; null-guard held.
Gates B–E, H–J PASS. F/G INSUFFICIENT_DATA exit 3 (permitted). No ENG action remains.

### P5 — active operator track (independent; parallel with F3)
PR #800 staging delivery validation (3 manual checks) + explicit 36-file boundary sign-off.
The fingerprint re-attestation at the final deployed SHA must happen at T0 time, not before.

### After F3 validation + P5 approval → T0
With F3 confirmed live and P5 sign-off obtained, record `window_start` (UTC) at the deployed SHA.
That sets **T0** and starts the 14-day **P8** shadow window.

> **Now:** F3 live/staging validation + P5 operator sign-off. Nothing else shortens the distance —
> the 14-day P8 window is the floor, and it can't open until F3 (validation) + P5 both clear.
