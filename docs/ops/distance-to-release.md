# Distance to Release — v1 tracker

**One-page status of the remaining v1 gates.** Companion to `docs/ops/v1-go-live-runbook.md`
(the *how*) and `scripts/v1_release_verification.sql` (the *evidence*). Update the Status /
ETA cells as gates clear; this file is the at-a-glance "are we there yet?".

**Position:** late-stage beta — feature-complete-approaching, **not** production-ready.
**Floor to GA:** **~3 weeks of operator calendar time**, dominated by the 14-day shadow window
— and that clock **has not started**. Code/tooling merges do not shorten it; only the operator
sequence does.

**Legend:** ✅ CLEAR · 🟡 CODE-READY (operator validation pending) · ⛔ BLOCKED · ⏳ NOT STARTED
**Owner:** OPS = operator (staging/prod/Render/Supabase) · ENG = code change still needed

---

## Gate table

| # | Gate | Owner | Status | Blocking on / clears when | ETA contribution |
|---|------|-------|--------|----------------------------|------------------|
| **Feature-complete (Condition 1)** |
| F1 | Core features merged (RPC/RLS hardening, snapshot RPC, I9 containment, placeholder isolation) | ENG | ✅ CLEAR | merged to `main` | — |
| F2 | I9 deferred defects (D11/D12/D06/D15) frozen as v1 or v2 | ENG | ⛔ OPEN | product decision + (if v1) code | 1–3 d |
| F3 | Extraction archive-race (#780) terminalizes the job | ENG | ⛔ OPEN | fix RPC/caller + regression; branch unmerged | 1–2 d |
| **Production-ready (Condition 2)** |
| P1 | Apply full migration chain to staging→prod (head `204`) | OPS | ⏳ NOT STARTED | run via approved migration runner | 0.5 d |
| P2 | RPC/RLS live verification (run `scripts/v1_release_verification.sql`) | OPS | 🟡 CODE-READY | script merged; needs a live run + RLS real-JWT proof | 0.5 d |
| P3 | Mig 182 durable operator-validation record filled | OPS | 🟡 CODE-READY | template merged (#809); fill with live output | 0.5 d |
| P4 | Mig 204 snapshot-review RPC validated on staging | OPS | 🟡 CODE-READY | apply + grant matrix + review→lock cycle | 0.5 d |
| P5 | PR-7 fingerprint boundary (36-file) approved + re-pinned | OPS | 🟡 CODE-READY | verifier hardened (#803/#814, digest `f2ee2c40…`); operator boundary sign-off | 1 d |
| P6 | Scheduler verification (startup, sweeper, drain) | OPS | ⏳ NOT STARTED | `ENABLE_SCHEDULER=true`; capture evidence | 0.5 d |
| P7 | **PR-6** final-candidate revalidation rerun (clear Gate 9) | OPS | ⛔ `gate_failed` | deploy allowlist build; rerun 12 gates | 1 d |
| P8 | **PR-7 14-day shadow window** | OPS | ⏳ NOT STARTED — **THE FLOOR** | starts only after P5+P7; **a single failure restarts the 14 days** | **14 d** |
| P9 | PR-8 bounded live canary | OPS | ⏳ NOT STARTED | after P8 passes | 1 d |
| P10 | PR-9 approval → flip `FF_MOCK_MASTERY_WRITES=live` | OPS | ⛔ BLOCKED | after P9 + sign-offs | 0.5 d |
| **Release-validated (Condition 3)** |
| R1 | Deployed-env E2E green (main user + admin journeys) | OPS | ⏳ NOT STARTED | run Playwright against deployed env | 0.5 d |
| R2 | Staging pilot (primary journey, no manual DB intervention) | OPS | ⏳ NOT STARTED | representative exam content + real users | parallel w/ P8 |
| R3 | Production canary + no open P0/P1 + perf/error targets | OPS | ⏳ NOT STARTED | after R1/R2 + P10 | 1–2 d |
| R4 | Support / privacy / terms / operational ownership ready | OPS | ⏳ NOT STARTED | non-eng readiness | parallel |

---

## Critical path (what actually sets the date)

```
 [P5 boundary approve + P7 PR-6 rerun + P1/P2/P3/P4 + F3 fix]   ~3–4 days, parallelizable
        │
        ▼
 [P8  PR-7 14-day shadow window]                                14 days   ← THE FLOOR
        │   (any threshold miss → restart 14 days)
        ▼
 [P9 canary → P10 live flip → R1 E2E → R3 prod canary]          ~3 days
        ▼
                         GA
```

**Earliest defensible GA ≈ T0 + ~3 weeks**, where **T0 = the day the operator starts the
deploy → PR-6 → window_start sequence**. T0 has not happened. Everything left of P8 is a few
days of operator work that can run in parallel; P8 is the immovable 14-day pole; R2 (pilot) can
overlap P8.

## What clears the most distance next (do these to reach T0)
1. **Fix F3** (extraction archive-race) and **freeze F2** (I9 v1/v2 decision) — the last ENG items.
2. Operator: **P1 apply migrations** → **P2 run the verification script** → **P3/P4** validate.
3. Operator: **P5 approve the fingerprint boundary** + **P6 scheduler proof** + **P7 PR-6 rerun**.
4. The moment P5+P7 are green → **start P8** (record `window_start`). That is T0; the 14-day clock begins.

> Nothing in the repo shortens P8. Track this file against the 14-day window once it opens.
