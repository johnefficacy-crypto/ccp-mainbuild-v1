# Career Copilot remaining-work PR plan

Last planned from repo state: 2026-06-20 at `main @ 11d188ef`.

This plan decomposes the remaining Career Copilot work into small PRs that can
be assigned to simultaneous agents without overlapping write scopes. Status
terms come from `docs/status/career-copilot-checklist.md`.

## Parallelization rules

1. Each PR owns only the files listed in its **write scope**. If an agent needs a
   file outside that scope, it must stop and split or re-plan the PR.
2. Checklist updates are allowed in every PR, but keep them to the rows touched
   by that PR.
3. Do not combine backend validation gates, frontend cleanup, and UX redesign in
   the same PR.
4. Operator-only tasks produce dated evidence docs; they do not edit runtime
   code unless a separate implementation PR is opened.
5. `FF_MOCK_MASTERY_WRITES=live`, A-PR4/A-PR5, and Track C remain blocked until
   the validation gate in Lane A passes.

## Lane map

| Lane | Can run now? | Blocking relationship | Primary owner |
|---|---:|---|---|
| A. Mock Engine validation gate | Yes, operator-led | Blocks `FF=live`, A-PR4/A-PR5, Track C | Operator / backend validator |
| B. Exam Governance cleanup | Yes | Independent of Lane A | Frontend cleanup agent |
| C. Exam workspace setup/timeline UX | Yes, after design lock | Independent of Lane A/B if scoped to SetupPanel | Frontend UX agent |
| D. Document readiness identity/status audit | Yes | May feed Lane C or a backend fix later | Backend+frontend auditor |
| E. Backend CI audit sequencing | Yes | Independent infrastructure PR | CI/backend infra agent |
| F. Live-DB tails | Yes, operator-led | Does not block code cleanup unless evidence changes status | Operator |
| G. Track C / personalization expansion | No | Waits on Lane A clean gate | Backend+frontend feature agents later |

## Lane A — Mock Engine validation gate

Goal: prove the already-landed code remediations against live/operator evidence
without flipping `FF_MOCK_MASTERY_WRITES=live`.

### PR #716 — Shadow gate prerequisite hardening — **MERGED**

### PR #718 — Platform-review authority hardening (code-only, prerequisite for A1/A2/A3 clean-state signoff)

Fixes 5 confirmed bugs in `canonical.py::review_mock`:

1. **BUG-A — `review_status` silent mutation:** removed Pydantic default from `review_status`; patch built from `model_fields_set` only so omitted fields are never overwritten.
2. **BUG-B — TOCTOU race:** scoped UPDATE (`id + user_id + source_type`) replaces the single-predicate update; zero-row result triggers 4-case diagnostic.
3. **BUG-C — platform path pollution:** `aggregated_error_types` derivation and breakdown/mastery/regen writes are fully isolated to the manual/imported path.
4. **Denylist → allowlist:** `_PLATFORM_REVIEW_ALLOWED` replaces `_PLATFORM_FORBIDDEN`; future body fields are rejected by default for platform mocks.
5. **FK ordering (seedAttempt.ts):** `resetAttempts` now deletes `mock_tests` compat rows (`mock_attempt_id IN attemptIds`) before deleting `mock_attempts` to avoid FK violations.

PR #718 adds regression coverage for the existing PR #716 correction-task authority guard; it does not modify that guard (`study_os.py`, `mocks.py`, and `mastery_writer.py` are empty diff vs main).

**Write scope (changed files only):**
- `app/backend/app/api/canonical.py`
- `app/backend/tests/study_os/test_mock_review.py`
- `app/frontend/e2e/fixtures/seedAttempt.ts`
- `docs/status/career-copilot-checklist.md`
- `docs/status/career-copilot-pr-plan.md`

### PR #716 — Shadow gate prerequisite hardening (original)

Fixes 6 blocking review findings against the mastery shadow gate:

1. **Correction idempotency (23505):** `_draft_correction_tasks` in `mastery_writer.py`
   and `draft_correction_tasks` in `mocks.py` now handle PostgreSQL 23505 uniqueness
   conflicts idempotently. Migration 181 dedup CTE fixed for `NULL created_at`.
2. **Platform-attempt correction guard:** `POST /api/study/mocks/{id}/correction-tasks`
   returns HTTP 409 (`PLATFORM_ATTEMPT_MANUAL_CORRECTION_FORBIDDEN`) for
   `source_type=platform_attempt` mocks.
3. **`derive_preview` three sections:** redesigned to return `persisted_shadow_decision`,
   `current_read_only_preview`, and `replay_consistency` with zero writes.
4. **Shadow analysis tool redesign:** `shadow-replay` (self-consistency), `live-audit-compare`
   (canary-only), `tasks-overlap` (with semantic note); correct env vars; real pagination.
5. **Canary plan hardened:** user allowlist made a hard prerequisite; rollback scoped to
   exact canary attempt_ids covering all 5 affected tables.
6. **Status docs:** this file and `docs/status/career-copilot-checklist.md` updated.

### A1 — Scheduler/job visibility evidence

- **Type:** operator evidence doc only.
- **Write scope:** `docs/audits/*scheduler*2026-*.md`, checklist row updates.
- **Do not touch:** `app/backend/app/study_os/*`, migrations, frontend.
- **Work:** capture both scheduler env vars (`ENABLE_SCHEDULER=true` primary gate,
  `DISABLE_SCHEDULER=true` override kill switch), scheduler startup/registration,
  `/api/admin/jobs` payload, manual sweeper run, and pending-job drain.
- **Exit:** checklist scheduler row moves from `OPERATOR PENDING` to either
  verified or code-defect-found. If code defect is found, open a separate A1-fix
  PR with a narrow backend scope.

### A2 — Repeat off/shadow validation evidence

- **Type:** operator evidence doc only.
- **Write scope:** new dated shadow-validation report under `docs/audits/`,
  checklist row updates.
- **Do not touch:** the 2026-06-18 failed report.
- **Work:** prove only answered topics get deltas, classification-enriched
  corrections match, resubmit creates no new shadow rows, compat row exists with
  integral marks, and retry jobs drain.
- **Exit:** if clean, `FF=live` can move from `BLOCKED` to next controlled live
  canary plan. If not clean, file one defect-specific backend PR per root cause.

### A3 — Live canary plan, not implementation

- **Type:** plan/evidence doc only (canary plan exists at `docs/ops/pr8_live_canary_plan.md`).
- **Write scope:** `docs/runbooks/` or `docs/audits/`, checklist row updates.
- **Depends on:** A1 and A2 clean, **AND** the user-allowlist implementation PR merged.
- **Hard prerequisite — not optional:** `FF_MOCK_MASTERY_WRITES` is currently global.
  A live canary MUST be bounded to a named user allowlist before this plan can be
  approved. The allowlist implementation PR (check `user_id` against an explicit
  allow-list before calling `MasteryWriter.process_attempt_sync`) must be merged and
  the allowlist must be non-empty with named consenting users. Rollback is scoped to
  exact canary attempt_ids recorded in pre-canary queries — not a time window.
- **Work:** confirm allowlist implementation merged, populate allowlist, run
  pre-canary queries, flip flag for bounded users, verify post-canary queries against
  success thresholds, attach evidence to PR9.
- **Exit:** only after all success thresholds pass should any expansion of the
  allowlist or full promotion occur. Never flip without allowlist in place.

## Lane B — Exam Governance cleanup

Goal: remove console-era leftovers now that `/console/:exam_id` renders
`ExamActionConsole`.

### B1 — De-leak `ExamActionConsole` labels

- **Type:** frontend cleanup.
- **Write scope:**
  - `app/frontend/src/features/admin/exam-intelligence/ExamActionConsole.jsx`
  - `app/frontend/src/features/admin/exam-intelligence/operatorChrome.js`
  - targeted tests under `app/frontend/src/features/admin/exam-intelligence/`
  - checklist row for CL-1b
- **Do not touch:** `ExamWorkspace.jsx`, `ExamTaskRail.jsx`, backend routes.
- **Work:** replace local token humanization with shared operator chrome helpers
  where compatible; add regression coverage for UUID/API-token leakage.
- **Tests:** targeted frontend tests for `ExamActionConsole` / identifier hygiene.

### B2 — Remove orphaned console variant and task rail

- **Type:** frontend cleanup.
- **Write scope:**
  - `app/frontend/src/pages/admin/exam-workspace/ExamWorkspace.jsx`
  - `app/frontend/src/pages/admin/exam-workspace/ExamTaskRail.jsx`
  - `app/frontend/src/pages/admin/exam-workspace/__tests__/ExamWorkspace.test.jsx`
  - `app/frontend/src/pages/admin/__tests__/ExamGovernanceConsole.test.jsx`
  - checklist row for CL-6
- **Depends on:** B1 only if tests share helper expectations; otherwise can run
  in parallel if the agents coordinate test ownership.
- **Work:** remove `variant="console"` branches and `ExamTaskRail` if no longer
  imported; keep standalone workspace behavior unchanged.
- **Tests:** workspace and governance-console frontend tests.

### B3 — Remaining console polish PRs

Run these as separate PRs because they touch different user-facing surfaces:

| PR | Write scope | Notes |
|---|---|---|
| B3a registry row expansion / dead columns | registry/list components and tests only | CL-2. |
| B3b remove CMS `+ New guided exam` CTA | `ExamIntelCms.jsx` and its tests only | CL-3. |
| B3c collapsible lifecycle banner | banner component/tests only | CL-4. |
| B3d-2 Console Work Queue action hierarchy | `ConsoleWorkQueue.jsx`, targeted console tests, and existing admin-console button styling only | CL-5; the queue has no screen-level primary CTA. Pressed workflow filters use selected-state styling rather than primary-action styling. Repeated `Open console` and `Advanced workspace` links are contextual row actions, not screen primaries. |
| B3d-3 Guided Exam Wizard primary-action hierarchy | `GuidedExamWizard.jsx` and its targeted tests only | CL-5; Organization mode selectors must use pressed-state styling rather than primary-action styling. The forward or create action remains the sole primary action on each wizard step. |
| B3d-close cross-surface CL-5 closure audit | audit and status documentation only | CL-5 closure gate; inspect current `main` after B3d-2 and B3d-3 merge. No runtime or test changes are allowed. If any violation remains, keep CL-5 `CLEANUP PENDING` and open a separate implementation PR for the affected screen. Mark CL-5 complete only when the audited repository state already satisfies the rule. |
| B4 / CL-6b remove dormant console presentation plumbing | `ExamWorkspaceContext.jsx`, `OverviewPanel.jsx`, `ReviewActivatePanel.jsx`, orphaned `ExamPublishImpact.jsx`, its isolated test, targeted workspace/console regression tests, and the checklist row only | CL-6b; remove the unused provider `variant`, remove dormant console-only presentation branches, delete orphaned `ExamPublishImpact` and its isolated test, and preserve the active standalone workspace and `ExamActionConsole` routes. |

#### CL-5 one-primary-per-screen rule

- A screen may expose at most one screen-level primary CTA.
- Pressed filter states must not use primary-action styling.
- Repeated table-row actions are contextual, not screen primaries.
- Local form submission buttons are scoped to their form/card and are not automatically competing screen-level CTAs.
- `SetupPanel` redesign remains owned by Lane C and must not be absorbed into B3d.
- B3d-close must not modify runtime code.
- B3d-close must not modify tests.
- B3d-close must not fix violations discovered during the audit.
- Discovered violations require a separate implementation PR.
- CL-5 remains pending until the audit passes against current `main` after B3d-2 and B3d-3 land.

## Lane C — Exam workspace setup/timeline UX

Goal: clean the chaotic setup workflow without cross-wiring console or CMS.

### C0 — Design lock / component ownership preflight

- **Type:** read-only design doc.
- **Write scope:** `docs/reviews/` or `docs/status/`, checklist row updates.
- **Work:** decide whether to refactor `SetupPanel` in place or introduce a new
  child component such as `PhaseTimelineManager`.
- **Exit:** explicit write scopes for C1-C4.

### C1 — Phase timeline table extraction

- **Type:** frontend refactor.
- **Write scope:** `SetupPanel.jsx`, new component under
  `app/frontend/src/pages/admin/exam-workspace/panels/`, and targeted tests.
- **Do not touch:** documents, syllabus, PYQ, competition, backend.
- **Work:** replace phase boxes with a grouped table that distinguishes
  template vs cycle-bound phases and keeps current create/edit behavior intact.

### C2 — Merge Template Phases and Phases Needing Dates into timeline

- **Type:** frontend UX cleanup.
- **Write scope:** same new timeline component and tests only.
- **Depends on:** C1.
- **Work:** render missing-date rows inline with badges; remove duplicate template
  rendering outside the timeline.

### C3 — Fast date-entry mode

- **Type:** frontend performance/UX.
- **Write scope:** timeline date-entry component and tests only.
- **Depends on:** C1 or C2.
- **Work:** use native `input type="date"` or a focused drawer for dense rows;
  avoid mounting two `DateField`/DayPicker controls per row.

### C4 — Setup mutation governance

- **Type:** frontend governance fix.
- **Write scope:** `SetupPanel.jsx` / extracted setup hooks and tests only.
- **Can run parallel with:** C1 only if C1 owns rendering components and C4 owns
  mutation handlers; otherwise run after C1.
- **Work:** migrate add-phase, phase-date patch, and template promotion to
  `useApiAction`; preserve audit reason requirements and refetch behavior.

## Lane D — Document readiness identity/status audit

Goal: resolve the suspected mismatch between upload/list/document identity,
`extraction_status`, and readiness/console checks.

### D1 — Read-only contract audit

- **Type:** audit doc only.
- **Write scope:** `docs/reviews/` or `docs/audits/`, checklist row updates.
- **Work:** trace `document_assets`, `syllabus_documents`, `document_pages`,
  extraction jobs/status fields, workspace readiness, and console detail.
- **Exit:** one of: no bug; backend-only fix; frontend-only selector fix; or
  coordinated backend+frontend fix.

### D2 — Narrow implementation fix, if D1 finds a bug

- **Type:** implementation, scope chosen by D1.
- **Write scope:** only the files named by D1.
- **Rule:** do not combine with Setup timeline work.

## Lane E — Backend CI audit sequencing

Goal: make backend tests run even when dependency audit findings need attention.

### E1 — CI sequencing PR

- **Type:** infrastructure.
- **Write scope:** `.github/workflows/ci.yml`, backend requirements only if needed,
  checklist row updates.
- **Do not touch:** application code.
- **Work:** preserve `pip-audit` visibility while ensuring `pytest` still runs or
  is reported independently; avoid silent CVE suppression.
- **Tests:** workflow syntax check where available; no app test changes.

## Lane F — Live-DB-only tails

Goal: keep live state separate from code-verifiable status.

Run each as an operator evidence task with no runtime code changes unless a real
code defect is found:

1. Verify/delete `e2e-workspace-exam` prod row.
2. Verify state PSC official/calendar URL backfill.
3. Reconfirm SEBI Grade A only if a future workflow depends on it.

## Lane G — Later expansion after clean gate

Do not dispatch until Lane A exits clean:

1. A-PR4 exposure cooldown.
2. A-PR5 mastery-informed mock selection.
3. Track C question model v2: stimulus/shared passages, media, non-MCQ scoring.
4. Wave 5 PYQ weighting into generated mock mix.

Each of these needs its own preflight to define schema, scoring, and frontend
contract before implementation.

## Suggested simultaneous dispatch batch

Safe first batch:

1. **Agent A:** A1 scheduler evidence (operator/live, docs only).
2. **Agent B:** B1 `ExamActionConsole` de-leak (frontend scoped).
3. **Agent C:** C0 setup timeline design lock (docs only).
4. **Agent D:** D1 document readiness identity/status audit (docs only).
5. **Agent E:** E1 CI sequencing (workflow scoped).

Do **not** dispatch B2 and C1 to the same agent unless B1 is complete and the
agent explicitly owns the relevant tests. Do **not** dispatch G-lane work until
A1/A2 are clean.
