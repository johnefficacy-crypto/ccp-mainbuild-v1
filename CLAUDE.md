# CLAUDE.md — Career Copilot

## Read order before touching any code

1. `graphify-out/GRAPH_REPORT.md` — primary codebase map (29 651 nodes, 53 998 edges)
2. `docs/00-ai-context.md` — product context and governance rules
3. `AGENTS.md` — locked decisions, CI quirks, pattern library
4. `docs/architecture/domain-model.md` — entity canonicity rules
5. `docs/operator-validation/INDEX.md` (generated from `docs/operator-validation/registry.json`) — live operator-validation gate status; read this before the large checklist when you need live operator status
6. `docs/status/career-copilot-checklist.md` — implementation status, product decisions, architecture gates, and historical context (not a live operator-status mirror)
7. Module-specific doc under `docs/architecture/` for the area being changed

Never grep or glob the codebase before reading the graphify report. The graph is faster and more accurate than file search.

---

## Execution style

Act first. Do not announce routine actions before performing them. Tool calls, file searches, command execution, and internal reasoning require no narration unless they reveal a blocker or significant finding.

Never say: "Starting the implementation." / "Now let me inspect the files." / "Verifying branch state." / "Confirmed — the diff contains…" / "Next, I will run tests." / "Say the word and I'll start." / "Used 3 tools." / "Ran 12 commands, read 7 files."

When the user says `start`, begin immediately. Do not restate the task or describe preliminary steps.

## Progress updates

Speak only when one of these occurs:
- A material finding changes the implementation approach.
- A blocker requires user input.
- A risky or irreversible action is about to be taken.
- A meaningful implementation milestone is complete.
- Verification fails in a way that affects delivery.

Keep updates to one or two sentences. Do not report the same fact more than once — a single final statement beats separate confirmations for each sub-step.

## Decision handling

When the repo owner, contract, issue, review, or user provides an explicit disposition: verify only the facts needed to safely execute it, perform the action, and report the result once. No extended justification when the decision has already been made.

Bad:
> Verifying branch state, then closing. Checked branch head and net diff. Confirmed the duplicate row. Closing the PR now. Done. The PR was closed.

Good:
> Closed PR #856 as superseded — its only remaining diff was the rejected duplicate checklist row.

## Token conservation

Do not:
- Repeat the user's instructions.
- Quote large issue or review descriptions.
- Paste unchanged source files.
- Explain each shell command.
- Provide play-by-play updates.
- Repeat conclusions in both progress updates and the final response.
- List tool counts or numbers of files inspected.
- Include generic praise or acknowledgements.
- Propose unrelated future work.
- Ask whether to continue when the current task is actionable.

Use concise references (file paths, symbols, commit hashes, PR numbers, test names) instead of reproducing full contents.

## Blockers

Ask for clarification only when implementation cannot safely proceed. Before asking: inspect the repository, read relevant docs, check existing patterns, and make reasonable repo-grounded decisions. Do not ask questions merely to avoid choosing between equivalent implementation details.

## Final response format

**Implemented**
- Concise description of the completed change.

**Files changed**
- `path/to/file`

**Verification**
- Exact commands run and their result.

**Remaining**
- Unresolved blockers, failures, or material risks only. Omit when none remain.

For non-code actions (closing a PR, updating a doc, posting a comment), report only: the action performed, the relevant identifier, and the verified outcome. No chronological account of how the work was performed.

---

## Project identity

Career Copilot is an eligibility-first recruitment-discovery and exam-preparation OS for Indian government-job aspirants.

Stack:
- Backend: FastAPI + Supabase (PostgreSQL + RLS) + APScheduler + Pydantic. Python 3.12.
- Frontend: React (plain JavaScript, no TypeScript), Tailwind CSS, PropTypes.
- Auth: Supabase Auth — roles stored in `raw_app_meta_data` (`user` / `admin` / `super_admin`).
- Migrations: 200+ SQL files in `app/supabase/migrations/`, numbered sequentially, immutable once merged.

---

## Non-negotiable domain rules

- `public.recruitments` = recruitment notifications (posts, eligibility, dates, application state). Never use as exam identity.
- `public.exams` = exam-master identity (Study OS, exam intelligence, cycles, phases). Never use as a recruitment notification.
- Do NOT merge both FK columns (`exam_id` + `recruitment_id`) without a documented bridge use case.
- **Retire ≠ Archive**: `is_active=false` hides exam from aspirants; `management_mode='archive'` is low-priority but live. Do not swap them.
- Eligibility verdicts must come from the deterministic eligibility engine — never from AI or heuristics.
- User-facing exam intelligence reads filter on `reviewer_status='verified'` conjunctively across papers, questions, and tags. No pending/rejected data leakage ever.
- PYQ frequency uses primary-only verified tags, filtered at query AND loop level (defense in depth).

---

## Architecture invariants

- **Governance before automation** — RBAC, audit, and queue monitoring are P0.
- **Trust > Speed**, **Control > Automation**, **Determinism > Heuristics**.
- **Verified-only reads** — all user-facing content must pass through the review lifecycle.
- **No new AI writes** — do not add Neo4j, Pinecone, LangGraph, or unreviewed AI-authored database writes.
- **Keep the stack**: PostgreSQL/Supabase + FastAPI + existing review lifecycles + mock engine/planner/mastery/SRS. Add pgvector or LLM adapter only when explicitly justified in an architecture doc.

---

## Frontend governance

- No new top-level sidebar destination unless it removes ≥ 2 existing top-level destinations (**no-new-surface rule**, locked 2026-06-21).
- Each surface has one API source of truth — do not cross-wire:
  - `/app/study/home` → `/api/study/mission-control`
  - `/app/study/mock` → `/api/mock/*`
  - `/app/study/review` → `/api/review/*`
  - `/app/study/progress` → `/api/mastery/*` + `/api/progress/*`
- Mutations go through the data-layer hook, not raw `fetch` in components.
- Collections use `useCollection` pattern — no ad-hoc array state.
- Initial bundle chunk ≤ 220 KB gzipped. Admin/prototype/study code must not leak into public entry surfaces via static imports.
- Frontend uses `exam` for display labels; backend FK columns use explicit `exam_id` / `recruitment_id`.

---

## Migration discipline

- Migrations are **immutable once merged**. Never edit a landed migration.
- Decide the entity type (`exam_id` vs `recruitment_id`) before adding an FK column.
- Every new table needs an RLS policy. Verify with `SELECT * FROM pg_policies WHERE tablename = '<name>'` before marking complete.
- Do not mark live-deployment or Supabase operator steps as complete from code inspection alone — use `operator_pending` or `validation_pending` in the operator-validation registry until live proof is captured.
- If code lands but shadow/live/operator validation is pending, keep the implementation status in its contract/checklist and set the operator gate to `validation_pending`; do not mark the gate passed.

---

## Before touching shared files

Read `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` before editing any of:
`KnowledgeGovernance.jsx`, `ExamIntelligence.jsx`, `ExamGovernanceConsole.jsx`, `AdminShell.jsx`, `adminRoutes.jsx`, `ExamWorkspace.jsx`, `ExamActionConsole.jsx`, `ConsoleWorkQueue.jsx`, `console_detail.py`, `readiness.py`.

**Serial delivery rule**: work that touches routing, navigation, or AdminShell must be one owner's sequential work — never fan out in parallel across agents.

---

## CI behaviour

- **CI triggers**: `ci.yml` and `safe-write-lint.yml` run on `pull_request` for PR branches and on `push` only for `main`. A PR gets a single run per check — no duplicate push-triggered run — and `main` gets one authoritative post-merge run. Superseded PR runs are auto-cancelled via `concurrency`.
- **validate-pr-body**: requires sections `Summary`, `Problem / Gap Addressed`, `Implemented in This PR` (≥1 checked item), `Remaining Work / Intentionally Deferred`, `Files Changed`, `API Contracts Touched`, `UI States Covered`, `Accessibility Checklist`, `E2E Impact`, `Manual Test Checklist`, `Commands Run`. Set the PR body in the same call that opens the PR.
- **e2e**: treat failures as actionable unless they match a documented environment/secrets outage.

---

## Operator-validation registry hygiene

- `docs/operator-validation/registry.json` is the only mutable source for operator-validation status, review timing, blockers, defects, next actions, and evidence links. `docs/operator-validation/INDEX.md` is generated and must never be edited manually.
- `docs/status/career-copilot-checklist.md` remains the source for implementation status, product decisions, architecture gates, and historical context. Migrated operator status must not be mirrored into it or into track-specific checklists.
- Runbooks contain reusable procedures; evidence records contain immutable execution results.
- Code completion is not operator validation. A code-fixed defect remains validation-pending until the deployed path is revalidated.
- Every non-terminal gate requires `review_by` as an RFC3339 UTC timestamp (`YYYY-MM-DDTHH:mm:ssZ`), not a date-only value.
- Record `defects_found` and `defects_fixed` on the gate. A fixed defect ID must also exist in `defects_found`.
- Evidence records are immutable. Revalidation appends evidence to the same gate unless the acceptance contract or independent validation boundary changes.
- After changing a registered source, runbook, evidence record, or gate status, update `registry.json`, regenerate `INDEX.md`, and run:
  - `node --test scripts/__tests__/operator-validation.test.js`
  - `node scripts/operator-validation.js --check`
- Do not mark live-deployment, token, Render, Supabase, browser, or other operator-only proof complete from code inspection alone.
- After modifying code, run `graphify update .` to keep the knowledge graph current (AST-only, no API cost).
