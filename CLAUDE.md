# CLAUDE.md — Career Copilot

## Read order before touching any code

1. `graphify-out/GRAPH_REPORT.md` — primary codebase map (29 651 nodes, 53 998 edges)
2. `docs/00-ai-context.md` — product context and governance rules
3. `AGENTS.md` — locked decisions, CI quirks, pattern library
4. `docs/architecture/domain-model.md` — entity canonicity rules
5. `docs/status/career-copilot-checklist.md` — live gate status
6. Module-specific doc under `docs/architecture/` for the area being changed

Never grep or glob the codebase before reading the graphify report. The graph is faster and more accurate than file search.

---

## Token efficiency

- **No planning narration.** Do not announce what you are about to do. Do it.
- **No step-by-step commentary.** No "Now I'll...", "Let me...", "Now I have enough context".
- **No redundant context-setting.** Do not restate what you just read.
- **Parallel tool calls silently.** Run them; do not announce them.
- **One-sentence updates only** when a mid-task status is genuinely needed.
- **End-of-turn summary:** one or two sentences — what changed, what's next.

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
- Do not mark live-deployment or Supabase operator steps as complete from code inspection alone — use `OPERATOR PENDING` or `VERIFY DB` until live proof is captured.
- If code lands but shadow/live/operator validation is pending, mark `CODE-FIXED, VALIDATION PENDING` in the checklist.

---

## Before touching shared files

Read `docs/status/Exam-Management-IA-Design-Lock-2026-06-21.md` before editing any of:
`KnowledgeGovernance.jsx`, `ExamIntelligence.jsx`, `ExamGovernanceConsole.jsx`, `AdminShell.jsx`, `adminRoutes.jsx`, `ExamWorkspace.jsx`, `ExamActionConsole.jsx`, `ConsoleWorkQueue.jsx`, `console_detail.py`, `readiness.py`.

**Serial delivery rule**: work that touches routing, navigation, or AdminShell must be one owner's sequential work — never fan out in parallel across agents.

---

## CI behaviour

- **backend (push-trigger run)**: fires before PR exists, frequently fails. The PR-triggered run is authoritative. Two `backend` entries = normal; ignore the first (push) failure.
- **validate-pr-body**: requires sections `Summary`, `Problem / Gap Addressed`, `Implemented in This PR` (≥1 checked item), `Remaining Work / Intentionally Deferred`, `Files Changed`, `API Contracts Touched`, `UI States Covered`, `Accessibility Checklist`, `E2E Impact`, `Manual Test Checklist`, `Commands Run`. Set the PR body in the same call that opens the PR.
- **e2e**: treat failures as actionable unless they match a documented environment/secrets outage.

---

## Checklist hygiene

- Every PR that changes implementation status, validation status, operator gates, or product decisions must update `docs/status/career-copilot-checklist.md` in the same branch.
- Status vocabulary: `MERGED` / `CODE-FIXED, VALIDATION PENDING` / `OPERATOR PENDING` / `VERIFY DB` / `BLOCKED` / `PLANNED` / `CLEANUP PENDING`.
- After modifying code, run `graphify update .` to keep the knowledge graph current (AST-only, no API cost).
