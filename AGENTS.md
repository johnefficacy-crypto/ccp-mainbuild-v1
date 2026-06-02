<!-- Table of contents -->
- [graphify](#graphify)
- [Known-flaky CI checks](#known-flaky-ci-checks)
- [Study OS frontend contract](#study-os-frontend-contract)
- [Frontend governance](#frontend-governance)
- [Migration discipline](#migration-discipline)
- [Before adding new modules, verify they don't already exist](#before-adding-new-modules-verify-they-dont-already-exist)
- [Patterns and Lessons](#patterns-and-lessons)

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- ALWAYS read graphify-out/GRAPH_REPORT.md before reading any source files, running grep/glob searches, or answering codebase questions. The graph is your primary map of the codebase.
- IF graphify-out/wiki/index.md EXISTS, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Known-flaky CI checks

These checks fail in predictable, non-code-related ways. Do not spend time
diagnosing them unless the failure pattern changes.

**backend (push-trigger run)**
- The `ci.yml` workflow runs on both `push` and `pull_request` events.
- The push-trigger run fires immediately on branch push, before a PR exists.
- This run frequently fails against the pre-existing test suite (the same
  tests pass on the PR-triggered run minutes later).
- Pattern: two `backend` check entries appear — the first (push run) fails,
  the second (PR run) passes. The PR run result is authoritative.
- Observed on PR #480 and PR #481.

**e2e**
- The `e2e` check is not defined in `.github/workflows/ci.yml` or
  `pr-body-check.yml` (the only two local workflow files).
- It fails on every PR observed so far and PRs merge despite it.
- Likely requires live Supabase / app-server infra not available in CI.
- Treat as non-blocking until the check definition and required secrets
  are traced down.

**validate-pr-body (first run only)**
- `pr-body-check.yml` triggers on `pull_request` events including
  `synchronize`. The very first run fires before the PR description is
  fully set if the branch was pushed before the PR was opened.
- Fix: ensure the PR body is set in the same API call that opens the PR.
  If it still fails on the first run, a PR body edit triggers a re-run
  that will pass.

## Study OS frontend contract

Each surface has one source of truth. Do not cross-wire them:

- `/app/study/home` (StudyHome.jsx) → `/api/study/mission-control` for the
  active plan, today's tasks, and focus rollup. The weekly report card is a
  separate fetch (`/api/study/report-card*`) because mission-control does
  not include it.
- `/app/study/plan` (StudyPlan.jsx) → `/api/study/plan/draft`,
  `/api/study/plan/apply`, `/api/study/plan/timeline`. Different contract;
  no overlap with mission-control.
- `/app/today` (Today.jsx) → the dashboard hook only. It is intentionally a
  general action/application overview after the PR3 reorg. **Never call
  `/api/study/mission-control` from `/app/today`.**
- `competition_context` reads `reviewer_status in ('locked','reviewed')`
  (locked preferred). UI copy must say "reviewed or locked rows feed the
  planner; locked preferred" — not "locked only".
  
RLS verification protocol for Supabase Studio:
- set_config(name, value, is_local := true) only persists for the
  current transaction
- ALWAYS wrap role + JWT-claims + SELECT in a single BEGIN/ROLLBACK
- A read that returns rows OUTSIDE a wrapped transaction proves nothing
  about RLS — it just proves Studio's connection has bypass privileges


## Frontend governance

Three mandatory patterns for all new frontend code. PRs that skip them will be
rejected in review.

### Routes
Every new route goes inside `<RouteErrorBoundary>` in `routes/appRoutes.jsx` or
`routes/adminRoutes.jsx`. No inline error handling or custom try/catch at the
route level.

### Mutations
Every user-triggered mutation (`api.post`, `api.patch`, `api.delete`) must use
`useApiAction` from `lib/hooks/useApiAction.js`. Pattern:

```js
const { run, busy } = useApiAction();
run({
  action: () => api.post("/api/...", body),
  optimistic: () => setLocal(optimisticState),
  rollback: () => setLocal(previousState),
  successMessage: "Done.",       // omit for silent-success (e.g. votes)
  errorMessage: "Action failed.",
});
```

Background read/check calls (dedup probes, preview fetches) are exempt, but
must carry a comment explaining why they are non-blocking.

### Collections
Every data collection fetched from the API must use `useApiCollection` from
`lib/hooks/useApiCollection.js`, or manually implement the same four-state
contract (`idle → loading → data | empty | error`).

- Error state must NOT render seed fixtures; seeds are only visible when
  `REACT_APP_ENABLE_DEMO_DATA=true`.
- Pass `<ErrorState />` (from `shared/ui`) when `status === "error"` if the
  screen doesn't handle it inline.

  ## Migration discipline

1. Applied migrations are immutable. Never rename, delete, or rewrite a
   migration that exists on main. Reverse via a NEW forward migration.

2. Migration numbers are checked by CI (migration-numbers workflow).
   Numbering must be MAX(main) + 1, contiguous. The next slot is
   determined by `select max(version)::int + 1 from schema_migrations`,
   not by inspecting the file system.

3. RLS verification: Supabase Studio's SQL editor bypasses RLS for the
   dashboard role. `set role authenticated` alone does NOT simulate a
   real user. Use wrapped transactions:
     begin;
       select set_config('role', 'authenticated', true);
       select set_config('request.jwt.claims', '{...}'::text, true);
       -- query here, in the same transaction
     rollback;
   Or test via PostgREST with a real JWT. Studio output that isn't
   transaction-wrapped proves nothing.

4. RLS access model: admin operations are FastAPI-mediated on
   service_role for most tables. Direct PostgREST admin reads are
   only supported on Pattern A tables (profiles, notification_*,
   eligibility_results, scrape_queue, tracked_recruitments, audit
   logs, settings — those using is_admin(auth.uid())). All other
   tables use defense-in-depth Pattern B (inline profiles.is_admin
   check, fails closed). When adding a new admin-touching table,
   default to Pattern B unless the frontend has a clear need for
   direct PostgREST reads.

5. profiles.is_admin and profiles.admin_role are DEPRECATED. Source
   of truth is auth.users.raw_app_meta_data.role ∈ {user, admin,
   super_admin}. public.is_admin(uid) reads from raw_app_meta_data.
   Do not consult profiles.is_admin in new code.

   ## Before adding new modules, verify they don't already exist

When a prompt says "add `app/<path>/<module>.py`", do not assume 
the path is empty. Run:

  git show origin/main:app/<path>/<module>.py 2>/dev/null && \
    echo "EXISTS — read before writing" || \
    echo "OK to create"

Also check the parent directory:

  git ls-tree origin/main app/<path>/

If any file in that directory exists, read it and the test file 
that exercises it before writing new code. Stubs that replace 
real implementations break test suites silently — CI catches it, 
but the rework cost is high.

This applies to all "new file" instructions in prompts, not just 
this one. The prompt is a description of intent, not a guarantee 
of filesystem state.

## Patterns and Lessons

Patterns observed across PRs #526–#535. Each item has a one-sentence
summary and a pointer to where it was learned.

### 1. Graphify-first discovery
Before authoring any PR prompt or starting work in an unfamiliar area,
read graphify-out/GRAPH_REPORT.md and the relevant wiki file. Treat
file paths in prompts as hints, not facts. Source: every operator
audit in the workspace track caught at least one bad assumption this way.

### 2. Audit before assume
When a prompt mentions an existing module/route/table, grep first.
PR4's prompt assumed PyqPaperWorkspace could render directly; operator
audit caught the useParams coupling before dispatch. See PR #534.

### 3. Hash-parity tests for cross-side identity
Any time frontend and backend compute the same hash (e.g. proposal_key
in syllabus mapper, future bulk-import tokens), commit a unit test on
BOTH sides with a fixed input and the known SHA output. Without this,
every commit silently fails as "stale" and operators think the system
is broken. Source: PR #533 — the single highest-risk thing about
that feature, caught by the pin test.

### 4. api.post() JSON-stringifies bodies
Anywhere binary or CSV bodies cross the API wrapper, use apiFetch
directly with explicit Content-Type, or add an api.postRaw() helper.
Caught mid-build during PR5 frontend. See PR #535.

### 5. Override semantics labeling
Operator-facing flags must describe what they actually do. "Override
errors" misleads operators into thinking malformed rows can be
force-imported. Use precise copy: "Override duplicate/error warnings
where importable" + helper text explaining what override cannot fix.
Source: PR #527 operator review.

### 6. Descriptive branch names
Use claude/pr-name-shape (e.g. claude/pr3b-syllabus-mapper), not
generated names like claude/festive-sagan-xAIiF. The latter pattern
showed up on PRs #526 and #530 and made the merge log unreadable.

### 7. PR7-style atomic cascade
Single-parent + multi-child inserts must rollback parent on any child
failure and return { ok: false, child_errors: [...] }. Application-level
rollback is acceptable; true Postgres transaction is better. Pattern
lives in app/backend/app/api/admin_exam_intel_cms.py:create_pyq_question.
See PR #526.

### 8. Trust gate on bulk inserts
reviewer_status forced 'pending' on every CMS write, even when caller
sends 'verified'. Pattern lives across PR3b accept (#533) and PR5
commit (#527). Bulk flows must not bypass review.

### 9. Snapshot pin when refactoring shared compute
When extracting a service module from a multi-consumer function (e.g.
compute_exam_workspace_readiness out of overview() in PR #530), pin
the pre-refactor output byte-identical with a test. The shared
consumer (review kanban for that case) breaks silently otherwise.

### 10. Guarded geometry gates over blunt thresholds
Spatial gates that work on one corpus can silently miss on another
when coordinates drift (e.g. PR #528's _ANCHOR_X_GAP=0.04 failed on
2026 GS-I where option labels sit at x+0.05–0.08). Fix is rarely
"widen the threshold" or "remove the gate". Instead, guard the gate
with a look-ahead that distinguishes the two cases it conflates
(body enumerator vs real option). See PR #553 find_stem_end rule.
