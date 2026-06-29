# Career Copilot v1 — Go-Live Runbook (operator)

**Purpose.** One ordered, operator-driven checklist that stitches the remaining v1 release
gates into a single sequence. It does **not** restate the detailed gate docs — it links them
and defines the *order*, *who acts*, *the pass condition*, and *the rollback*.

**Audience.** On-call operator + engineering lead + product owner. Most steps need
staging/prod, Render, and Supabase access that the codebase cannot exercise.

**Completion rule.** **Every item in this runbook is required for GA** unless it sits in an
explicit *Deferred / non-blocking* note. The ⛔ marker additionally means *sequencing*: do not
proceed past that point until its pass condition holds. A plain ☐ is still mandatory for the
final GA declaration — it is simply not a stop-the-line ordering gate.

> Authoritative gate docs (do not duplicate — follow them step-for-step; if this runbook and a
> gate doc disagree, the gate doc wins):
> `docs/ops/pr6_final_candidate_revalidation.md`, `pr7_shadow_gate_results.md`,
> `pr8_live_canary_plan.md`, `pr9_live_approval.md`,
> `docs/schema/rpc-grant-audit-v1.md`, `docs/schema/rls-coverage-reconciliation-v1.md`,
> `docs/status/career-copilot-checklist.md` (the repo source-of-record — update it as gates clear).

---

## Phase 0 — Pre-flight (no prod writes)

- ☐ **Branch hygiene.** v1 scope merged to `main`; the open wave PRs (extraction race, I9,
  cleanup-UI, J1/J2, PR-7 freeze) are either merged or explicitly deferred to v2.
- ☐ **Staging parity.** Staging Supabase project is on the same migration head as the `main`
  you intend to ship. Record both `schema_migrations` maxes and confirm **no history holes or
  divergence** between staging, prod, and the repo migration set.
- ☐ **Backups + rollback rehearsed.** Fresh logical backup of prod Supabase; PITR available.
  Record the recovery point and RTO. (PITR/full restore is a last-resort incident action — see
  the rollback note in Phase 1, not an automatic response to any write.)
- ☐ **Feature-flag inventory captured** (current prod values, so rollback is exact):
  `FF_MOCK_MASTERY_WRITES`, `FF_MOCK_MASTERY_LIVE_USER_IDS`, `ENABLE_SCHEDULER`,
  `DISABLE_SCHEDULER`, `FF_ENABLE_PLACEHOLDER_ENDPOINTS`.

---

## Phase 1 — Schema & permission migrations (staging → prod)

**Apply the complete contiguous pending migration chain through the approved migration
runner**, driven by the remote `schema_migrations` state — **do not cherry-pick or replay
individual historical SQL files**. Fail closed on any history hole or divergence. The version
numbers below are **verification checkpoints** to confirm *after* the chain applies, not files
to run independently. "Idempotent" is not assumed on a drifted target (e.g. `203` assumes exact
function signatures already exist).

- ⛔ **`011_verified_domain_gap_p1.sql`** (P0 runtime unblock) — checkpoint: applied; column
  `courses.instructor_id` + FK present.
- ⛔ **`033` / `035`** (PYQ score snapshots + RLS) — checkpoint: `exam_topic_score_snapshots`
  present. **Security caveat:** `035` creates admin predicates using the deprecated
  `profiles.is_admin`; migrations `195`/`196` later drop/recreate those with canonical
  `public.is_admin(auth.uid())`. **Never manually replay `035` on a database where `195` is
  already recorded** — it would recreate the obsolete predicate without `195` rerunning.
  Explicitly verify the `195`/`196` hardening is present (canonical `is_admin` policies in
  force). Validate the snapshot RLS using the proper-JWT protocol in Phase 2 (a Studio query or
  bare `SET ROLE` proves nothing).
- ⛔ **`182`** (mock correction RPCs) — **dry-run with `BEGIN; … ROLLBACK;` first**, then it
  applies via the chain. Checkpoint: the three RPCs exist and `anon`/`authenticated` cannot
  EXECUTE them.
- ⛔ **`202_atomic_extraction_finalize.sql`** (#780 extraction transaction-safety) — **GATE
  BLOCKED.** This migration does **not** by itself prove "no stranded `running` jobs": the RPC
  returns `{ok:false, reason:'document_archived'}` and the Python caller currently maps that to
  an error without driving the job to a terminal state, so an **archive-during-finalize race can
  still leave the claimed job `running`**. Do not mark this gate green until the RPC/caller fix +
  regression test land and this operator query returns zero rows:
  ```sql
  select id, document_id, status, updated_at
  from document_processing_jobs
  where job_type = 'text_extract' and status = 'running'
    and updated_at < now() - interval '15 minutes';
  ```
- ⛔ **`203_rpc_grant_hardening_v1.sql`** (RPC least-privilege, 16 RPCs; renumbered from 202 on
  merge). Checkpoint: run the **grantee verification query** in `docs/schema/rpc-grant-audit-v1.md`
  — every one of the 16 functions lists `service_role` (and owner) only, **no
  PUBLIC/anon/authenticated**, NULL-acl treated as a finding. Smoke-test the service-role flows
  (recruitment promotion, verification report create/supersede, scrape claim, mastery writeback
  + retry). Note: this migration assumes the exact function signatures exist — if the target is
  drifted, reconcile before applying.
- ☐ **Schema-contract test** (required for GA) — run `app/backend/tests/test_schema_contract.py`
  with the service-role key against staging. Pass: green.

**Migration-failure handling (not "restore on any write").** On a failed migration: **stop
further rollout**, assess transaction state, preserve evidence (logs, partial state), and prefer
a **forward remediation** migration. A PITR/full restore is a last-resort *incident* decision
with traffic control, an explicit recovery point, a quantified data-loss window, and
engineering + product + on-call approval — never the automatic response to any write.

---

## Phase 2 — RLS coverage sign-off

- ⛔ Run the **live introspection query** in `docs/schema/rls-coverage-reconciliation-v1.md` on
  staging **and** prod. Diff the returned table set vs the doc's snapshot; **classify every
  addition/removal** (expect at least `support_content_access`). Pass: no returned table is one
  the frontend reads directly with the anon/authenticated key. Then mark the RLS gate GREEN in
  `career-copilot-checklist.md`.
- ⛔ **Per-row RLS proof (mandatory protocol).** "Authenticated users see only `reviewed`/`locked`
  rows" must be proven as a real role, not from a privileged dashboard connection (Studio and a
  bare `SET ROLE authenticated` without JWT claims **bypass/!misrepresent** RLS). Use one of:
  - **PostgREST with a real user JWT** — anon-key client + a signed `authenticated` JWT; `GET`
    the snapshot resource and confirm only `reviewed`/`locked` rows return; repeat with an admin
    JWT and confirm `draft` rows are visible to admins only; or
  - **single transaction** that sets `role` **and** `request.jwt.claims` (sub + role), runs the
    `SELECT`, then `ROLLBACK`.
  Record the exact rows returned for a normal user vs an admin.

---

## Phase 3 — Mock Engine shadow → live (the long pole, ~14+ days)

Sequential and time-dominated. Each PR gate has its own doc; this is the order.

- ⛔ **Deploy the mastery allowlist build** and **populate `FF_MOCK_MASTERY_LIVE_USER_IDS`** with
  named, consenting canary UUID(s). Confirm `FF_MOCK_MASTERY_WRITES=shadow`.
- ⛔ **Scheduler verification.** `ENABLE_SCHEDULER=true`, `DISABLE_SCHEDULER` unset. Capture
  scheduler startup/registration, `/api/admin/jobs` payload, a manual `mock:sweeper` run, and a
  pending-job drain. Pass per the checklist's "Scheduler verification" row.
- ⛔ **PR-6 final-candidate revalidation rerun** on the deployed SHA
  (`docs/ops/pr6_final_candidate_revalidation.md`). Pass: all 12 gates — esp. **Gate 9**
  (allowlist enforced at sync-submit / analytics_retry / recovery) and **Gate 12**
  (`FF_MOCK_MASTERY_WRITES=shadow` active). Current status is `gate_failed`; this rerun clears it.
- ⛔ **PR-7 14-day shadow window** (`docs/ops/pr7_shadow_gate_results.md`). **Do not use any
  pre-recorded fingerprint hash as a baseline** — the prior value is currently a *reference* only
  and the manifest boundary is `FREEZE PENDING` with open telemetry/analytics fixes (and a
  separate open PR changes fingerprinted files). The hard gate is: **(a)** all telemetry fixes
  merged; **(b)** the manifest dependency boundary closed and **operator-approved**; **(c)**
  docs/checklist reconciled; **then (d)** compute and attest a **fresh** fingerprint at the exact
  deployed `window_start` SHA, record the UTC `window_start`, and observe 14 days. Pass:
  exact_match 100% · coverage 100% · correction-parity 100% with zero invariant violations.
  Nothing flips to live before this completes.
- ⛔ **PR-8 bounded live canary** (`docs/ops/pr8_live_canary_plan.md`). Preflight P1–P12 pass.
  Then: deploy `shadow` → set `FF_MOCK_MASTERY_WRITES=live` (start 15-min timer) → one control
  attempt (non-allowlisted, verify **no** live write) → one canary attempt (allowlisted, verify
  S1–S12). Post-canary: set `FF_MOCK_MASTERY_WRITES=shadow` again.
- ⛔ **PR-9 approval + live flip** (`docs/ops/pr9_live_approval.md`). Attach canary evidence;
  Engineering-lead + Product-owner + On-call sign-off. Operator sets `FF_MOCK_MASTERY_WRITES=live`,
  redeploys, verifies the first live attempt writes a `user_topic_mastery_audit` row with
  `reason='mock_submit'`. Monitor `mock:sweeper` error rate for 1 hour.

**Rollback (authoritative — flag flip alone is NOT sufficient).** `mastery_retry` jobs persist
`mastery_flag_state`, and `get_or_resolve_pinned_mastery_flag()` deliberately returns the
*pinned* mode even after the global flag changes — so a pending/running **live-pinned** job (and
delayed correction recovery, which also honors the pinned mode) can keep writing live after you
switch the env back to shadow. To roll back, follow the PR-8 rollback procedure:
1. Flip `FF_MOCK_MASTERY_WRITES=shadow` so **new** resolutions are shadow.
2. Query all jobs with `mastery_flag_state='live'`; **fence/cancel and drain** them; wait for any
   running job to finish.
3. Reconcile/restore the affected data surfaces (`user_topic_mastery`, `user_topic_mastery_audit`,
   correction tasks) for the canary user(s).
4. Audit the rollback (what was written live, what was reverted) and record it.

---

## Phase 4 — Production surface & config

- ☐ Confirm prod leaves **`FF_ENABLE_PLACEHOLDER_ENDPOINTS` unset** (placeholder/demo admin
  endpoints stay off — v2 scope).
- ☐ Background jobs, extraction, uploads, payments, notifications verified working in the
  deployed environment (not just locally).
- ☐ Monitoring, logs, alerts, backups, and the rollback procedures above are live and tested.

---

## Phase 5 — Release validation (pilot)

- ☐ Representative exams have complete, reviewed content.
- ☐ A real user completes the primary journey (onboarding → exam → Study OS plan → tasks → mock
  → analysis → revision) **without manual DB intervention**.
- ☐ An admin can diagnose and recover a failed job through the UI.
- ☐ Critical browser E2E (`app/frontend/e2e/`) green in the deployed env for the main user +
  admin journeys.
- ☐ No open P0/P1 defects; performance and error-rate targets met; planner/mock results manually
  sampled and approved.
- ☐ Support, privacy, terms, and operational ownership ready.

---

## Exit criteria — declare "v1 production-validated / GA"

**Every ☐ and ⛔ item above** is complete (none skipped except those in an explicit Deferred
note), the RLS and RPC gates are GREEN in `career-copilot-checklist.md`, the migration-202
extraction-race gate is fixed and verified (zero stale `running` jobs), `FF_MOCK_MASTERY_WRITES=live`
is safely enabled with a working drain-based rollback, and the pilot passed with no open P0/P1.
Only then state: **Career Copilot v1 is feature-complete, production-validated, and ready for
general availability.**

> Ownership note: every Phase-1→3 ⛔ gate is operator-executed and cannot be proven from repo code
> alone. Do not mark any operator gate complete from code inspection.
