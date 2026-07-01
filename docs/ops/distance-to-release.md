# Distance to Release — v1 tracker (READ-ONLY derived view)

> **This file is a derived, read-only summary. Do NOT mutate status here.**
> The shared source of record is **`docs/status/career-copilot-checklist.md`** (per `AGENTS.md`);
> live evidence lives in the gate docs / `docs/audits/`. When a gate changes, update the
> checklist + its audit, then regenerate this view. Each row links its authoritative source.

**as_of:** `main @ ad81e8d4` · 2026-07-01
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
| P7 | **PR-6** final-candidate revalidation rerun (clear Gate A) | OPS+ENG | ⛔ CODE-FIX REQUIRED, REVALIDATION PENDING | 2026-07-02 partial run at SHA `9b0c96ed`: 12 start gates PASS; Gate A BLOCKED (`canonical.py::review_mock` schema mismatch `review_status`/`reviewed_at` vs `review_state`); code fix on branch (PR #840); re-deploy + Gate A re-run required; staging fixtures preserved | `pr6_final_candidate_revalidation.md` + `audits/2026-07-02-p7-candidate-revalidation-partial.md` |
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

**ETA:** the only hard duration is **P8 = 14 days**. Remaining pre-T0 work (F3 + P1→P4 + P5 +
P7; **P6 done**) is operator-/eng-paced — realistically a **handful of days** but not reproducibly
fixed here, so it is expressed as a range, not a promise. Post-window (P9→R3) is a **few days**.
**Floor ≈ 3 weeks from T0**, *longer* if the shadow window restarts or PR-6 needs multiple reruns.
Do not quote a calendar date until T0 is set.

## Shortest path right now

**P6 is CLOSED** (PR #827 merged; all scheduler-drain evidence on `main`). **F3 is CODE-FIXED**
(PR #834 merged: `_update_job` guard + `finalize_failed` regression test; needs live/staging
validation only). The active ENG blocker is **P7 Gate A** (schema contract fix, PR #840 in
review). **P5** is an independent operator track running in parallel.

### F3 — CODE-FIXED, VALIDATION PENDING (PR #834, merged)
`finalize_document_extraction` → `document_archived` now calls `_fail()` before raising (no job
can strand `running`); mid-flight regression test added. No code work remains — ENG dependency is
MET. Live/staging confirmation still required before T0.

### P7 — Gate A code fix + re-run required
2026-07-02 partial run at SHA `9b0c96ed` confirmed 12 start gates PASS. Gate A BLOCKED:
`canonical.py::review_mock` writes `review_status`/`reviewed_at` but schema has `review_state`
(no `reviewed_at` column). Code fix on PR #840 (branch `claude/brave-maxwell-kywecs`):
maps `review_status` → `review_state`, removes `reviewed_at`, accepts
`scheduled|unreviewed|reviewed|correction_drafted`, null-guards explicit `null` write.

After PR #840 merges:
1. Deploy the fixed SHA to **staging** (SHA A from Render; confirm deployed SHA B == A).
2. With `FF_MOCK_MASTERY_WRITES=shadow` and `FF_MOCK_MASTERY_LIVE_USER_IDS` populated, re-run
   **Gate A** using preserved attempt `60b14100-02eb-40fa-a1f0-88a43a48b315`.
3. Confirm `review_status: "reviewed"` → HTTP 200, `review_state = "reviewed"` in DB.
4. Record full gate results in a new dated audit under `docs/audits/`.

### P5 — parallel operator track (independent of P7)
PR #800 staging delivery validation (3 manual checks) + explicit 36-file boundary sign-off.

### After P7 PASS **and** P5 approval → T0
Re-pin the fingerprint at the deployed SHA (from the `f2ee2c40…` reference) and record
`window_start`. That sets **T0** and starts the 14-day **P8** shadow window.

> **Now:** merge PR #840 → deploy to staging → re-run Gate A. P5 runs alongside. Nothing else
> shortens the distance — the 14-day P8 window is the floor, and it can't open until
> F3 (validation) + P7 (Gate A PASS) + P5 all clear.
