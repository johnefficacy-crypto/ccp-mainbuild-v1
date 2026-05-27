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
