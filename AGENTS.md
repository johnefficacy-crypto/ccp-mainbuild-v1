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
