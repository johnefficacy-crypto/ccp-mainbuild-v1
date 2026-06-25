<!-- Table of contents -->
- [graphify](#graphify)
- [Shared checklist status](#shared-checklist-status)
- [Known-flaky CI checks](#known-flaky-ci-checks)
- [Study OS frontend contract](#study-os-frontend-contract)
- [Frontend governance](#frontend-governance)
- [Migration discipline](#migration-discipline)
- [Before adding new modules, verify they don't already exist](#before-adding-new-modules-verify-they-dont-already-exist)
- [Patterns and Lessons](#patterns-and-lessons)
- [PYQ Intelligence v2 module contracts](#pyq-intelligence-v2-module-contracts)

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- ALWAYS read graphify-out/GRAPH_REPORT.md before reading any source files, running grep/glob searches, or answering codebase questions. The graph is your primary map of the codebase.
- IF graphify-out/wiki/index.md EXISTS, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## Shared checklist status

The repo-level checklist lives at `docs/status/career-copilot-checklist.md`.
It is the shared source of record for agent-visible status on the Mock Engine
v2 ↔ Study OS arc, Exam Governance Console cleanup tier, exam-intelligence UX
cleanup, Exam Management IA locked decisions, CI gate status, and live-DB-only tails.

The Exam Management IA findings record is at `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md`.

The Exam Management IA **implementation gate** (design-lock) is at `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md`. This is the authoritative gate for I8-A, I8-B, and I8-C. Read this document before touching any of: `KnowledgeGovernance.jsx`, `ExamIntelligence.jsx`, `ExamGovernanceConsole.jsx`, `AdminShell.jsx`, `adminRoutes.jsx`, `ExamWorkspace.jsx`, `ExamActionConsole.jsx`, `ConsoleWorkQueue.jsx`, `console_detail.py`, or `readiness.py`.

No-new-surface rule (locked): **No new top-level destination unless it removes at least two existing top-level destinations.** A new sidebar item or promoted top-level route IS a surface. A backend endpoint, embedded component, or drill-in page is NOT. Violating this rule restarts the IA problem the work is trying to solve.

Rules:
- Before changing code or docs in those areas, read the checklist after the
  Graphify map.
- Every PR that changes implementation status, validation status, operator
  gates, or product decisions in those areas must update the checklist in the
  same branch.
- Do not mark live-deployment, token, Render, Supabase, or other operator-only
  evidence as complete from code inspection alone; use `OPERATOR PENDING` or
  `VERIFY DB` until the live proof is captured.
- If a code remediation lands but shadow/live/operator validation remains, use
  `CODE-FIXED, VALIDATION PENDING` rather than `complete`.

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
- The `e2e` check is defined in `.github/workflows/e2e.yml` and exercises the
  live frontend/backend/Supabase stack.
- Treat failures as actionable unless the failure matches a documented
  environment/secrets outage pattern.

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

### 11. Coverage Lifecycle (CL) statuses — competition & topic-coverage
The competition-metrics and topic-coverage review endpoints use
`CoverageReviewBody`, which accepts ONLY
`draft | pending_review | reviewed | locked | rejected`
(admin_exam_intelligence.py ~L522). `verified` is NOT a valid status for
these resources and returns 422 — it belongs to the items/policy review
flow, not the coverage lifecycle. Only `locked` rows feed
`competition_context` in Study OS (`reviewed`/`locked` for topic-coverage,
locked preferred). Frontend promote actions on these surfaces must send
`locked` (or `reviewed`), never `verified`. The exam-workspace
CompetitionPanel "Verify" button hit this: it PATCHed `verified` and
silently 422'd once the create flow started landing real rows. Fix renamed
it to "Lock" and sends `locked`. See PR #565 (Codex P2 on #563).

### 12. A red `npm ci` masks the entire frontend test suite
`ci.yml`'s `frontend` job runs `npm ci` BEFORE `npm test`/`build`. When the
lockfile is out of sync, `npm ci` fails fast (~11s) and the tests never run —
so PRs can merge with failing/never-executed frontend tests while the check
is red "for the lockfile". Two consequences: (a) a frontend failure at ~11s
is almost always the lockfile, not your code; a failure at ≥40s means
`npm ci` passed and a later step (tests/build) is the real cause; (b) fixing
the lockfile can UNMASK pre-existing test failures that were hidden behind
the install error. Root cause of the recurring drift: local npm 11 treats
`tailwindcss`'s `yaml@^2.4.2` as an optional peer and reports no drift, but
CI's Node 20 / npm 10 expects `node_modules/tailwindcss/node_modules/yaml@2.9.0`
pinned in the lock. Regenerate the lock with the CI npm major to reproduce:
`npx -y npm@10 install --package-lock-only`. See PR #566.

### 13. public.exams is a real table — not just UI vocabulary
`public.exams` exists and is canonical for exam-master identity (cycles,
phases, study plans, exam intelligence all FK into it). The earlier guidance
"do not introduce public.exams" was correct at project start; it was
superseded when the exam-master table was introduced. The invariant that
remains: `public.recruitments` = canonical recruitment/notification entity;
`public.exams` = exam-master identity. They are separate entities. Do not
conflate or merge them. Domain invariant: DB entity = recruitment; frontend
label = exam; exam registry is separate from recruitments. See
`docs/architecture/domain-model.md` (updated 2026-06-12).

### 14. Retire ≠ archive — two distinct lifecycle states
`is_active = false` on `public.exams` means the exam is retired (hidden from
aspirants via `/api/exams` filter `is_active=true`). `management_mode =
'archive'` is a SEPARATE operator lane for low-priority exams that are still
LIVE (`is_active = true`). The "Retire" action (button renamed from
"Deactivate", PR #630) writes ONLY `is_active = false` and NEVER sets
`management_mode`. Do not cross these semantics in future code or migrations.

### 15. Exam importer is retired — wizard is the only identity-change path
`import_exam_registry.py`, `import_subordinate_boards.py`,
`seed_exam_phases.py`, `dedupe_state_psc_orgs.py` and their tests were
deleted (PR #631). Identity changes (new exams, cycles, phases) go through
the operator wizard ONLY (`GuidedExamWizard.jsx` / `AddCycleWizard.jsx`).
`validate_exam_intelligence_seed.py` is KEPT — it is a live readiness gate,
not an importer.

### 16. Slug = upsert key — never editable
`exams.slug` is fenced in `EDIT_EXCLUDED_FIELDS` in the CMS backend.
Editing a slug after creation breaks bulk-import idempotency (slug is the
upsert key for seeded rows). The wizard generates slugs from the name at
create time; they are immutable thereafter. Same invariant applies to
cycle-bound slugs (recomputed at clone time from exam slug + year +
cycle_name; never user-editable post-creation).

### 18. No-new-surface rule for navigation

Before adding any new admin navigation entry, count: (a) how many top-level destinations exist now; (b) how many will exist after the PR. If the number stays equal or increases, the PR fails the IA objective. The test is "did the visible surface count go down?" A new route that folds two existing surfaces into one passes; a new route added alongside existing surfaces fails. Do not treat a "portfolio/matrix" dashboard, a "coverage lane", or a second "workspace variant" as neutral — each is a new surface. See `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md` §9.

### 19. Serial delivery for shared-write-scope redesigns

When multiple implementation PRs must edit the same navigation/routing files — `AdminShell.jsx`, `adminRoutes.jsx`, page shells, context providers, route/title tests — they MUST be dispatched serially to one owner, not fanned out to parallel agents. Parallel agents on shared routing files produce conflicts, duplicate dead code, and broken active-nav state. I8-A → I8-B → I8-C is the canonical example: all three touch routing and navigation; all three must be one agent's sequential work. If a prompt says "implement I8-A and I8-B in parallel", refuse and re-sequence.

### 17. Uniqueness constraints for exam identity graph
- Cycle uniqueness: `(exam_id, year, cycle_name)` — enforced by unique index.
- Phase uniqueness: `(exam_id, exam_cycle_id, phase_slug)` — enforced by
  unique index.
- Generic (cycle-agnostic) template unique index:
  `(exam_id, phase_slug) WHERE exam_cycle_id IS NULL`.
- Template-slug collision in `AddCycleWizard` is guarded before insert;
  clones recompute slugs from the target cycle's bound identifiers.
  Source: PR #635.

## PYQ Intelligence v2 module contracts

Architecture doc: `docs/architecture/pyq-intelligence-v2.md`.
Delivery tracked in `docs/status/career-copilot-checklist.md` (Lane P rows).
PR plan: Lane P in `docs/status/career-copilot-pr-plan.md`.

### verified_pyq_topic_counts — primary-only contract

`app/backend/app/exam_intelligence/coverage.py::verified_pyq_topic_counts(sb, exam_id)`

**Contract (locked as of PR #767):** counts only `tag_role='primary'` tags.
Secondary, trap, and `calculation_layer` tags are excluded at both the DB query
and the loop guard (defense-in-depth).

Trust gates are conjunctive (ALL three required):
- `pyq_papers.trust_status = 'verified'`
- `pyq_questions.reviewer_status = 'verified'`
- `pyq_question_topic_tags.reviewer_status = 'verified'`

Tests: `tests/exam_intelligence/test_pyq_frequency_semantics.py` and `tests/test_pyq_counts_trust.py`.

**Do not remove the loop guard** — it protects against query refactors that
accidentally drop `.eq("tag_role", "primary")`.

### exam_topic_score_snapshots writer

`app/backend/app/exam_intelligence/score_snapshots.py` (added PR #767)

| Function | Purpose |
|---|---|
| `compute_exam_topic_scores(sb, exam_id, model_version, *, exam_phase_id)` | Writes draft snapshots; idempotent via SHA-256 fingerprint on inputs. Returns `{written, skipped, errors, total_topics, read_error, invalid_scope}`. |
| `locked_score_snapshots(sb, exam_id, *, exam_phase_id)` | Locked-only reader for planner/user surfaces. Deduplicated to latest per `(exam_id, topic_id)`, filtered to `MODEL_VERSION`. |
| `list_exam_score_snapshots(sb, exam_id, *, status)` | Admin list helper; fully paginated via `_paginate()`. |

**Status lifecycle:** `draft → reviewed → locked`. Only `locked` rows feed planner/user surfaces.

**Contracts locked in PR #767 second-pass fixes:**
- **Primary-only + ambiguity exclusion:** questions with ≥2 primary tags to different topics are excluded from all frequency counts in both `compute_exam_topic_scores` and `verified_pyq_topic_counts`. `existing_fps` collects ALL fingerprints per topic — not just the last one — so a stale orphaned draft row cannot cause a duplicate insert.
- **Exam-wide coverage isolation:** `_coverage_page` adds `.is_("exam_phase_id", None)` when `exam_phase_id` is not supplied, preventing phase-specific coverage rows from entering exam-wide score computation.
- **Draft fail-closed:** `_paginate()` on `exam_topic_score_snapshots` returns `None` on any page failure → `read_error: True`. A DB error on the draft SELECT must never be treated as "no drafts exist" (which would create unbounded duplicates).
- **Pagination:** all corpus reads (papers, questions, tags, coverage, drafts, locked) use `_paginate()` with PostgREST `.range(from, to)` to satisfy the architecture acceptance criterion.
- **`invalid_scope` vs `read_error`:** phase-not-in-exam is a caller validation error → `invalid_scope: True` → HTTP 422. DB read failures → `read_error: True` → HTTP 502. These are mutually exclusive and the endpoint checks `invalid_scope` first.
- **Model-version authority:** `locked_score_snapshots` filters `.eq("model_version", MODEL_VERSION)` so stale-model rows can never override current-model results.
- **Audit log:** `review_score_snapshot` performs a best-effort INSERT into `admin_audit_logs` before the conditional UPDATE. Not fully atomic (no dedicated RPC migration) but ensures every successful transition has an audit trail.

**Remaining known gap (slice-1b):** audit log INSERT is not atomic with the UPDATE — a concurrent-modification failure (409) leaves an orphan audit row. A dedicated RPC migration is needed for full atomicity.

Admin endpoints added to `app/backend/app/api/admin_exam_intelligence.py`:
`GET /exams/{exam_id}/score-snapshots`, `PATCH /score-snapshots/{id}/review`, `POST /exams/{exam_id}/score-snapshots/compute`.
Tests: `tests/exam_intelligence/test_score_snapshot_admin_api.py`.

### 19. Primary-only frequency is the permanent PYQ contract

`verified_pyq_topic_counts` counts a question once per topic if it has a
verified primary tag. Multiple secondary/trap/calculation_layer tags on the
same question do NOT inflate frequency. This is intentional. Do not revert
to all-role counting without an explicit architectural decision and downstream
consumer audit.
