# Career Copilot checklist — repo source of record

Last repo verification: 2026-06-19 at `HEAD` (PR #718 platform-review-authority-hardening branch `fix/platform-review-authority-hardening`).

This checklist replaces chat-only / UI-only status snippets. Keep it current in the same PR as any code change or decision that changes one of these statuses.

Execution plan for parallel PRs: `docs/status/career-copilot-pr-plan.md`.

## Status vocabulary

- **MERGED / CODE PRESENT** — verified from files in this repository checkout.
- **CODE-FIXED, VALIDATION PENDING** — remediation is present in code, but live/operator proof is still required.
- **OPERATOR PENDING** — cannot be proven from repo code alone; requires deployment, token, Render, Supabase, or other live evidence.
- **BLOCKED** — do not start downstream work until the stated gate passes.
- **PLANNED** — not yet implemented in this checkout.
- **CLEANUP PENDING** — no longer on the critical runtime path, but old code or UX debt remains.

## Mock Engine v2 ↔ Study OS — active gate

Current verdict: **DO NOT PROCEED TO LIVE**. `FF_MOCK_MASTERY_WRITES=live` remains blocked until (a) the operator scheduler/job-drain gate, (b) a clean repeat off/shadow validation pass, and (c) the user allowlist implementation PR merges and a bounded live canary is approved.

| Item | Current status | Repo evidence / notes |
|---|---|---|
| #695 decision / plan doc | MERGED / CODE PRESENT | `docs/study_os/mock-engine-v2-study-os-integration.md` remains the source of truth for sequencing and decisions. |
| #697 MCQ-only safety pool | MERGED / CODE PRESENT | Already treated as merged in the planning doc; no Track C expansion yet. |
| #698 A-PR3 generated mock signal producer | MERGED / CODE PRESENT | Generated attempt path remains a signal producer, not personalization. |
| #702 §4b correction schema compatibility | MERGED / CODE PRESENT | Historical schema incompatibility is recorded as code-remediated pending validation. |
| #704 shared correction categorizer | MERGED / CODE PRESENT | Shared policy design remains closed; runtime propagation was historically defective but code-fixed by later remediation. |
| review_mock writer authority | CODE-FIXED, VALIDATION PENDING | `canonical.py::review_mock` hardened (PR #718): (1) allowlist `_PLATFORM_REVIEW_ALLOWED` replaces denylist — new fields are rejected by default for platform mocks; (2) empty body → 422; patch built only from `model_fields_set` so omitted fields (including `review_status`) are never silently overwritten; (3) ownership lookup logs via `logger.exception` on failure; (4) scoped UPDATE (`id + user_id + source_type`) closes the TOCTOU race; zero-row result triggers 4-case diagnostic (deleted→404, owner-changed→404, source-changed→409, unexplained→503); (5) platform code path fully isolated — `aggregated_error_types` and breakdown/mastery/regen never execute for `platform_attempt`. Correction-task drafting for platform attempts remains blocked at service layer (PR #716, already on main). 18/18 test_mock_review.py passing (9 new tests + 2 updated assertions). |
| DEFECT-001 attempted semantics | CODE-FIXED, VALIDATION PENDING | `MasteryWriter._load_analytics` now treats `selected_option_id is not None` as the attempted source of truth; `derive_mastery_deltas` skips unattempted questions. |
| DEFECT-003 classification propagation | CODE-FIXED, VALIDATION PENDING | `MasteryWriter._load_analytics` now reads `mock_attempt_response_classification` and feeds `error_type` into analytics. |
| DEFECT-002 shadow idempotency | CODE-FIXED, VALIDATION PENDING | Migration `180_mock_mastery_shadow_idempotency.sql` dedupes/adds unique shadow keys; `_write_shadow` uses conflict-ignore upsert. |
| DEFECT-005A `total_marks` coercion | CODE-FIXED, VALIDATION PENDING | `_to_integral_marks` is used in both initial mock compat-row insert and retry emission. |
| DEFECT-006 manual weak-topic fallback | CODE-FIXED, VALIDATION PENDING | Manual mock correction drafting delegates weak-topic fallback to `correction_policy`. |
| Correction idempotency guard (23505) | CODE-FIXED, VALIDATION PENDING | PR #716: `_draft_correction_tasks()` in `mastery_writer.py` and `draft_correction_tasks()` in `mocks.py` now catch 23505 unique-constraint violations as idempotent duplicates; non-23505 errors propagate. Migration 181 dedup CTE fixed for `NULL created_at`. Stale "NOT concurrency-safe" and "OUT OF SCOPE" comments removed. |
| Platform-attempt correction gate | CODE-FIXED, VALIDATION PENDING | PR #716: `POST /api/study/mocks/{mock_id}/correction-tasks` now raises HTTP 409 with `PLATFORM_ATTEMPT_MANUAL_CORRECTION_FORBIDDEN` for `source_type=platform_attempt` mocks. MasteryWriter pipeline owns that path; manual drafting is forbidden. |
| Mastery preview (`derive_preview` three sections) | CODE PRESENT, OPERATOR VALIDATION PENDING | PR #716: `derive_preview()` redesigned to return three sections: `persisted_shadow_decision` (from `mock_mastery_shadow`), `current_read_only_preview` (labeled as mutable current state), and `replay_consistency` (per-topic sign+magnitude comparison). Admin endpoint now rejects non-platform_attempt mocks with 422. Zero writes guaranteed. |
| Shadow analysis tool redesign | CODE PRESENT, VALIDATION PENDING | PR #716: `tools/mastery_shadow_analysis/shadow_analysis.py` rewritten with three commands: `shadow-replay` (self-consistency, works in shadow mode), `live-audit-compare` (canary-only, filters `reason=mock_submit`), `tasks-overlap` (with `topic_semantics_note` about cross-population non-comparability). Fixed env vars to `NEXT_PUBLIC_SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY`. Real offset pagination. |
| Live canary user allowlist | BLOCKED | Hard prerequisite — the user allowlist implementation PR has NOT yet merged. `FF_MOCK_MASTERY_WRITES` is currently global. The canary plan (`docs/ops/pr8_live_canary_plan.md`) requires a non-empty named-user allowlist before any live traffic is bounded. Do not flip the flag until this is satisfied. |
| Scheduler verification | OPERATOR PENDING | Two env vars govern the scheduler: `ENABLE_SCHEDULER=true` (server.py, primary gate — default disabled) and `DISABLE_SCHEDULER=true` (scheduler.py, override kill switch). Live proof must capture both env var states, scheduler startup/registration, `/api/admin/jobs` payload, manual sweeper run, and pending-job drain. |
| Repeat off/shadow validation | OPERATOR PENDING | Required after code remediations before any live flip. Create a new dated report; do not edit the 2026-06-18 failed report. |
| `FF_MOCK_MASTERY_WRITES=live` | BLOCKED | Blocked on scheduler verification, clean repeat validation, AND user allowlist implementation + bounded live canary approval. |
| A-PR4 exposure cooldown + A-PR5 mastery-informed mock selection | BLOCKED / PLANNED | Start only after clean shadow/live-readiness gate. |
| Track C question-model v2 / PYQ weighting | BLOCKED / PLANNED | Track C remains downstream of the clean text-MCQ feedback-loop gate. |

### Operator validation still required

The repository can prove code remediation only. It cannot prove live scheduler behavior, token reachability in another agent harness, Render state, or Supabase row-drain evidence. Do not mark the operator gates complete from code inspection alone.

## Exam Governance Console — wave 4.6

Current verdict: **core arc complete; cleanup tier remains**.

| Item | Current status | Repo evidence / notes |
|---|---|---|
| #694 UX audit / decisions | MERGED / CODE PRESENT | Audit docs remain in `docs/exam-governance/`. |
| #699 console primary door | MERGED / CODE PRESENT | AdminShell exposes Exam Governance Console and Registry as primary entries; Create exam and Advanced Import / Repair are advanced entries. |
| #700 console list shell | MERGED / CODE PRESENT | `ExamListShell` still exists as generic list shell. |
| #701 backend capability preflight | MERGED / CODE PRESENT | Backend docs remain available. |
| #703 backend work-queue reads | MERGED / CODE PRESENT | `/console/exams` and `/console/summary` routes exist and use work-queue classification. |
| #705 frontend work-queue wiring | MERGED / CODE PRESENT | `/console` renders `ConsoleWorkQueue`. |
| #707 per-exam backend read | MERGED / CODE PRESENT | `/console/exams/{exam_id}` delegates to `console_detail.build_console_detail`. |
| #709 per-exam action console | MERGED / CODE PRESENT | Selected-exam console renders `ExamActionConsole`, not embedded `ExamWorkspace variant="console"`. |
| CL-1 identifier hygiene | CODE PRESENT IN THIS CHECKOUT | `operatorChrome` helpers and tests are present. Confirm remote PR state separately if needed. |
| CL-1b de-leak `ExamActionConsole` | CODE PRESENT IN THIS CHECKOUT | Shared `operatorChrome.humanizeToken` now backs reason/area/gate fallbacks (with explicit neutral words); UUID title fallback removed (now "Unnamed exam"); verdict-status raw-token label fallback removed; targeted `ExamActionConsole` identifier-hygiene regression added. |
| CL-2 registry row expansion / column cleanup | PLANNED | Not verified as implemented in this checkout. |
| CL-3 remove CMS `+ New guided exam` CTA | PLANNED | Not verified as implemented in this checkout. |
| CL-4 collapsible lifecycle banner | PLANNED | Not verified as implemented in this checkout. |
| CL-5 one-primary-per-screen buttons | PLANNED | Not verified as implemented in this checkout. |
| CL-6 remove orphaned console variant + `ExamTaskRail` | CLEANUP PENDING | `ExamWorkspace` still contains `variant === "console"` branches and still renders `ExamTaskRail`; the runtime console route no longer mounts it. |

## Exam intelligence / workspace UX cleanup findings

These findings are confirmed against the current checkout and should remain visible until remediated.

| Area | Status | Notes |
|---|---|---|
| Setup phase UX | CLEANUP PENDING | `SetupPanel` still renders separate cards for phases, template phases, and phases needing dates. A single timeline manager has not landed. |
| Template phases duplication | CLEANUP PENDING | `phases.map(...)` still renders all phases while `templatePhases` are rendered again in a separate section. |
| Slow/heavy date inputs | CLEANUP PENDING | Dense phase date worklist still mounts two `DateField` components per row; `DateField` uses `react-day-picker`. |
| Setup mutations governance | CLEANUP PENDING | Cycle create/edit use `useApiAction`; add phase, phase-date patch, and template promotion still call `api.post`/`api.patch` directly. |
| Cycle Trust column | CLEANUP PENDING | Cycle Trust is still derived from cycle status (`active` → `locked`, otherwise `verified`) rather than a real trust lifecycle. |
| Add-cycle product path | CLEANUP PENDING | Route redirects into workspace setup, but `AddCycleWizard.jsx` and direct tests remain. Decide whether to retire or re-promote it. |
| Document readiness extraction status | NEEDS TARGETED RECHECK | `console_detail` still counts extracted docs by `extraction_status == "succeeded"`; earlier audit found upload/list flows may use different status fields. |

## Backend CI / dependency gate

| Item | Current status | Notes |
|---|---|---|
| pip-audit dependency versions | PARTIALLY UPDATED | `litellm==1.84.0` and `pypdf==6.13.3` are pinned in `app/backend/requirements.txt`. |
| pip-audit before pytest sequencing | STILL OPEN | `.github/workflows/ci.yml` still runs `pip-audit` before `pytest`; if audit exits nonzero, backend tests will not execute. |

## Prior arcs / live-DB-only tails

Keep these separated from code-verifiable status.

| Item | Current status | Notes |
|---|---|---|
| SEBI Grade A orphan | CLOSED BY PRIOR OPERATOR CLAIM | Treat as live-DB state; reverify before using it as fresh evidence. |
| `e2e-workspace-exam` prod-row cleanup | VERIFY DB | Code guard exists, but row existence/deletion is live DB state. |
| state PSC URL backfill | VERIFY DB | Importer behavior is code-verifiable; actual 29-org/10-calendar backfill status is live DB state. |
| J&K doubled-prefix slug | LEAVE | Do not clean slug unless a real operator/user-facing break appears. |

## Maintenance rule for agents

Every PR that changes any of the following must update this checklist in the same branch:

1. Mock Engine v2 / Study OS feedback-loop code, feature flags, scheduler behavior, retry jobs, or validation docs.
2. Exam Governance Console routes, work queue, action console, cleanup tier, or workspace-console orphan code.
3. Exam intelligence setup/workspace UX, Advanced Import / Repair, Guided/Add Cycle flows, document readiness, PYQ, topic coverage, competition, or publish gates.
4. Backend CI ordering, dependency audit policy, or known flaky checks.
5. Any operator decision that changes a `BLOCKED`, `OPERATOR PENDING`, `PLANNED`, or `CLEANUP PENDING` status.

When a task is live-DB or deployment-only, write **OPERATOR PENDING** or **VERIFY DB**; never mark it complete from code inspection alone.
