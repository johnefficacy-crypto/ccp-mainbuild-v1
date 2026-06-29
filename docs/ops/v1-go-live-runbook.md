# Career Copilot v1 — Go-Live Runbook (operator)

**Purpose.** One ordered, operator-driven checklist that stitches the remaining v1
release gates into a single sequence. It does **not** restate the detailed gate docs — it
links them and defines the *order*, *who acts*, *the pass condition*, and *the rollback*.

**Audience.** On-call operator + engineering lead + product owner. Most steps need
staging/prod, Render, and Supabase access that the codebase cannot exercise.

**Status legend.** ☐ todo · ☑ done · ⛔ hard gate (do not proceed until the pass condition holds).

> Authoritative gate docs (do not duplicate — follow them step-for-step):
> `docs/ops/pr6_final_candidate_revalidation.md`, `pr7_shadow_gate_results.md`,
> `pr8_live_canary_plan.md`, `pr9_live_approval.md`,
> `docs/schema/rpc-grant-audit-v1.md`, `docs/schema/rls-coverage-reconciliation-v1.md`,
> `docs/status/career-copilot-checklist.md` (the repo source-of-record — update it as gates clear).

---

## Phase 0 — Pre-flight (no prod writes)

- ☐ **Branch hygiene.** Confirm the v1 scope is merged to `main`; the open wave PRs
  (extraction race, I9, cleanup-UI, J1/J2) are either merged or explicitly deferred to v2.
- ☐ **Staging parity.** Staging Supabase project is on the same migration head as the
  `main` you intend to ship. Record both `schema_migrations` maxes.
- ☐ **Backups + rollback rehearsed.** Confirm a fresh logical backup of the prod Supabase
  DB and that point-in-time restore is available. Note the restore command and RTO.
- ☐ **Feature-flag inventory captured** (current prod values, so rollback is exact):
  `FF_MOCK_MASTERY_WRITES`, `FF_MOCK_MASTERY_LIVE_USER_IDS`, `ENABLE_SCHEDULER`,
  `DISABLE_SCHEDULER`, `FF_ENABLE_PLACEHOLDER_ENDPOINTS`.

---

## Phase 1 — Schema & permission migrations (staging → prod)

Apply on **staging first**, validate, then prod. Each migration is idempotent; apply in
ascending number order against the deployed `schema_migrations` state.

- ⛔ **Migration `011_verified_domain_gap_p1.sql`** (P0 runtime unblock) — applies cleanly
  (column-before-FK is already guarded). Pass: no error; `courses.instructor_id` + FK present.
- ☐ **Migrations `033` / `035`** (PYQ score snapshots + RLS) — required before the planner
  consumes locked snapshots. Pass: `exam_topic_score_snapshots` present; authenticated users
  see only `reviewed`/`locked` rows.
- ⛔ **Migration `182`** (mock correction RPCs) — **dry-run with `BEGIN; … ROLLBACK;` first**,
  then apply. Pass: the three RPCs exist and `anon`/`authenticated` cannot EXECUTE them.
- ☐ **Migration `202_atomic_extraction_finalize.sql`** (#780 extraction transaction-safety) —
  apply. Pass: text-extract page-write + job-terminal update are atomic; no job stranded in
  `running` after a crash/archive race.
- ⛔ **Migration `203_rpc_grant_hardening_v1.sql`** (RPC least-privilege, 16 RPCs; renumbered
  from 202 on merge). Apply, then
  run the **grantee verification query** in `docs/schema/rpc-grant-audit-v1.md`. Pass:
  every one of the 16 functions lists `service_role` (and owner) only — **no PUBLIC/anon/
  authenticated**, and NULL-acl (default-PUBLIC) treated as a finding. Then smoke-test the
  service-role flows (recruitment promotion, verification report create/supersede, scrape
  claim, mastery writeback + retry).
- ☐ **Schema-contract test** — run `app/backend/tests/test_schema_contract.py` with the
  service-role key against staging. Pass: green (no missing required columns).
- Rollback: migrations are forward-only; if a gate fails, **stop**, restore from the Phase-0
  backup if any write occurred, and fix the migration before retrying. Do not hand-patch prod.

---

## Phase 2 — RLS coverage sign-off

- ⛔ Run the **live introspection query** in `docs/schema/rls-coverage-reconciliation-v1.md`
  on staging **and** prod. Diff the returned table-name set against the doc's snapshot;
  **classify every addition/removal** (expect at least `support_content_access`). Pass: no
  returned table is one the frontend reads directly with the anon/authenticated key. Only
  then mark the RLS gate GREEN in `career-copilot-checklist.md`.

---

## Phase 3 — Mock Engine shadow → live (the long pole, ~14+ days)

This is sequential and time-dominated. Each PR gate has its own doc; this is the order.

- ⛔ **Deploy the mastery allowlist build** and **populate `FF_MOCK_MASTERY_LIVE_USER_IDS`**
  with the named, consenting canary user UUID(s). Confirm `FF_MOCK_MASTERY_WRITES=shadow`.
- ⛔ **Scheduler verification.** Confirm `ENABLE_SCHEDULER=true` and `DISABLE_SCHEDULER` unset.
  Capture: scheduler startup/registration, `/api/admin/jobs` payload, a manual `mock:sweeper`
  run, and a pending-job drain. Pass per `career-copilot-checklist.md` "Scheduler verification".
- ⛔ **PR-6 final-candidate revalidation rerun** on the deployed SHA
  (`docs/ops/pr6_final_candidate_revalidation.md`). Pass: **all 12 gates**, specifically
  **Gate 9** (allowlist deployed & enforced at sync-submit / analytics_retry / recovery) and
  **Gate 12** (`FF_MOCK_MASTERY_WRITES=shadow` active during the run). Current status is
  `gate_failed`; this rerun is what clears it.
- ⛔ **PR-7 14-day shadow window** (`docs/ops/pr7_shadow_gate_results.md`). Freeze the v2
  fingerprint manifest hash at the **confirmed window_start SHA** (the recorded baseline is
  `b7394b79…0c3bc2b` at `main @ 1679adb8` — **re-verify at window_start**), record the exact
  UTC `window_start`, then observe for 14 days. Pass: exact_match 100% · coverage 100% ·
  correction-parity 100% with zero invariant violations. **Nothing flips to live before this
  completes.**
- ⛔ **PR-8 bounded live canary** (`docs/ops/pr8_live_canary_plan.md`). Preflight P1–P12 must
  pass. Then: deploy `shadow` → set `FF_MOCK_MASTERY_WRITES=live` (start 15-min timer) →
  one control attempt (non-allowlisted, verify **no** live write) → one canary attempt
  (allowlisted, verify S1–S12). Pass: all stop-conditions clear. Post-canary: set
  `FF_MOCK_MASTERY_WRITES=shadow` again.
- ⛔ **PR-9 approval + live flip** (`docs/ops/pr9_live_approval.md`). Attach canary evidence;
  obtain Engineering-lead + Product-owner + On-call sign-off. Then operator sets
  `FF_MOCK_MASTERY_WRITES=live`, redeploys, and verifies the first live attempt writes a
  `user_topic_mastery_audit` row with `reason='mock_submit'`. Monitor `mock:sweeper` error
  rate for 1 hour.
- Rollback (any step): set `FF_MOCK_MASTERY_WRITES=shadow` (or `off`) and redeploy — writes
  stop immediately. The allowlist fails closed, so a flag/allowlist mistake degrades to shadow,
  not to uncontrolled live writes.

---

## Phase 4 — Production surface & config

- ☐ Confirm prod leaves **`FF_ENABLE_PLACEHOLDER_ENDPOINTS` unset** (placeholder/demo admin
  endpoints stay off — they are v2 scope).
- ☐ Background jobs, extraction, uploads, payments, notifications verified working in the
  deployed environment (not just locally).
- ☐ Monitoring, logs, alerts, backups, and the rollback procedure above are live and tested.

---

## Phase 5 — Release validation (pilot)

- ☐ Representative exams have complete, reviewed content.
- ☐ A real user completes the primary journey (onboarding → exam → Study OS plan → tasks →
  mock → analysis → revision) **without manual DB intervention**.
- ☐ An admin can diagnose and recover a failed job through the UI.
- ☐ Critical browser E2E (`app/frontend/e2e/`) green in the deployed env for the main user +
  admin journeys.
- ☐ No open P0/P1 defects; performance and error-rate targets met; planner/mock results
  manually sampled and approved.
- ☐ Support, privacy, terms, and operational ownership ready.

---

## Exit criteria — declare "v1 production-validated / GA"

All ⛔ gates above are ☑, the RLS and RPC gates are GREEN in `career-copilot-checklist.md`,
`FF_MOCK_MASTERY_WRITES=live` is safely enabled, the pilot passed with no open P0/P1, and
rollback is rehearsed. Only then state: **Career Copilot v1 is feature-complete,
production-validated, and ready for general availability.**

> Ownership note: every Phase-1→3 ⛔ gate is operator-executed and cannot be proven from repo
> code alone. Do not mark any operator gate complete from code inspection.
