# Career Copilot checklist — repo source of record

Last repo verification: 2026-06-20 at `main @ 11d188ef`.

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
| Classification readiness / mastery recovery (D1-D4) | CODE-FIXED, VALIDATION PENDING | PR #719: (D1) `submit_attempt` analytics failure no longer silently skips mastery — `MasteryClassificationNotReady` is raised and the mastery_retry job is rescheduled. (D2) `auto_submit_attempt` now enqueues `mastery_retry` when FF≠off (parity with manual submit). (D3) `process_attempt_sync` gates on `check_classification_readiness` before any writes — missing classifications raise `MasteryClassificationNotReady` and re-enqueue `analytics_retry`; mastery never runs with None error_types from absent classification rows. (D4) `_run_job JOB_ANALYTICS_RETRY` enqueues `mastery_retry` after `compute_and_persist` succeeds when FF≠off, closing the analytics-success→mastery handoff gap. New module: `study_os/attempt_classification_readiness.py`. 20 new tests. |
| Correction idempotency guard (23505) / atomic persistence | CODE-FIXED, MIGRATION VALIDATION PENDING | PR-5B (fix/correction-draft-atomicity): five data-loss/correctness defects fixed. D1: per-draft RPC loop replaced by `ensure_mock_correction_drafts` (plural) bulk RPC — full correction set is now atomic in one DB transaction (Option A chosen). D2: `ensure_mock_correction_draft` and `ensure_mock_correction_drafts` now verify `mock_tests.user_id = p_user_id AND source_type = 'platform_attempt'` before any insert. D3 (manual): delete-before-insert replaced by `replace_manual_mock_correction_drafts` RPC (single transaction; prior drafts preserved on failure). D4 (manual): 23505 catch-and-fetch removed; RPC handles conflict internally. D5 (manual): `_safe`-wrapped review_state update replaced by atomic RPC step (failure propagates). D6: string-search `"23505" in str(exc)` eliminated; no application-level 23505 handling in either path. Migration 182 adds three RPCs (SECURITY DEFINER, service_role only). Applied/dismissed rows preserved. Empty-draft contract: deletes all drafted rows, sets review_state='reviewed'. 21 new tests. VERIFY DB: dry-run migration 182 with BEGIN/ROLLBACK before production apply. VERIFY DB: confirm anon/authenticated cannot EXECUTE any of the three RPCs. |
| Platform-attempt correction gate | CODE-FIXED, VALIDATION PENDING | PR #716: `POST /api/study/mocks/{mock_id}/correction-tasks` now raises HTTP 409 with `PLATFORM_ATTEMPT_MANUAL_CORRECTION_FORBIDDEN` for `source_type=platform_attempt` mocks. MasteryWriter pipeline owns that path; manual drafting is forbidden. |
| Mastery preview / exact replay (`derive_preview`) | CODE PRESENT, OPERATOR VALIDATION PENDING | `refactor/mastery-preview-exact-replay`: `derive_preview()` refactored to delegate to new `attempt_derivation.py` module. New shape: 4-bucket `response_counts` (selected/marked_unanswered/visited_unanswered/untouched), `classification_coverage`, `persisted_shadow_decision` (rows+duplicate_keys), `replay_consistency` with exact Decimal MATCH/MISMATCH/NO_BASELINE (no mutable mastery in replay path), deterministic `attempt_evidence_corrections` (no user state), labeled `current_state_preview`. Admin route fix: DB error → 503 (not silent 404), structured 422 codes for non-platform and missing attempt-link cases. 31 new tests. |
| Shadow analysis tool redesign | CODE-FIXED, VALIDATION PENDING | PR #723: `shadow-replay` calls real `attempt_derivation` API (load_attempt_inputs → load_persisted_shadow_decisions → replay_from_persisted_baseline) with correct signatures; reads canonical mismatch keys (persisted_delta_db/replay_delta_db); classification_not_ready structured records include missing/duplicate question IDs. `correction-parity` queries submitted mock_attempts (not shadow rows) to include unanswered-only attempts. `live-audit-compare` emits FAIL when data is sufficient but conditions fail (sign_agreement < 95, missing_audit > 0, duplicate_audit > 0, outliers > 0, delta_mismatch > 0); adds delta_mismatch_count/delta_mismatches fields. Tests use real attempt_derivation module (patching only DB layer). CLI validates: --attempt-id+--days mutual exclusion, --to-utc without --from-utc, days <= 0, invalid UUID, invalid ISO-8601, from-utc >= to-utc. NULL invariant fields → CORRUPT (not silent zero). Removed invalid 80%/60% thresholds. Operator shadow-run validation still required before live flip. |
| Live canary user allowlist | BLOCKED | Hard prerequisite — the user allowlist implementation PR has NOT yet merged. `FF_MOCK_MASTERY_WRITES` is currently global. The canary plan (`docs/ops/pr8_live_canary_plan.md`) requires a non-empty named-user allowlist before any live traffic is bounded. Do not flip the flag until this is satisfied. |
| Scheduler verification | OPERATOR PENDING | Two env vars govern the scheduler: `ENABLE_SCHEDULER=true` (server.py, primary gate — default disabled) and `DISABLE_SCHEDULER=true` (scheduler.py, override kill switch). Live proof must capture both env var states, scheduler startup/registration, `/api/admin/jobs` payload, manual sweeper run, and pending-job drain. |
| Repeat off/shadow validation | GATE FAILED — BLOCKED ON ALLOWLIST | 2026-06-19 revalidation attempt stopped at Gate 9: no per-user allowlist deployed (see `docs/audits/2026-06-19-final-candidate-revalidation.md`). Code remediations for DEFECT-001/002/003/005A are present. Live operator run cannot start until allowlist gate clears. |
| 14-day shadow gate (PR-7) | NOT STARTED — BLOCKED ON PR-6 | PR-6 did not pass (Gate 9 hard stop: allowlist not deployed); no observation window opened; candidate fingerprint superseded since PR-6 inspection (PRs #723 and #726 modified fingerprinted files); no thresholds evaluated; final fingerprint manifest (`docs/ops/mastery_validation_fingerprint_manifest_v2.txt`) cannot be frozen until allowlist and error-pattern remediation PRs merge; new baseline and exact UTC window_start required after all Lane A prerequisites clear and PR-6 PASS. See `docs/audits/mastery-shadow-14day-gate-2026-06-20.md` and `docs/ops/pr7_shadow_gate_results.md`. |
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
| CL-2 registry row expansion / column cleanup | CODE PRESENT IN THIS CHECKOUT | Registry rows now lead with the exam name and expose keyboard-accessible details. Lane, cadence, exam key, and secondary metrics moved out of the dense primary table. Existing filters, pagination, console/workspace actions, identifier hygiene, and the /exams API contract remain unchanged. |
| CL-3 remove CMS `+ New guided exam` CTA | CODE PRESENT IN THIS CHECKOUT | Advanced Import / Repair no longer renders the redundant guided-exam CTA. Entity selection, Reload, New row, Bulk import, and their existing forms remain unchanged. The guided-exam route remains available outside the CMS. |
| CL-4 collapsible lifecycle banner | CODE PRESENT IN THIS CHECKOUT | The Exam Registry lifecycle contract now renders as a keyboard-accessible, collapsed-by-default disclosure. Its full reviewed/locked/verified guidance remains available on demand, while other AdminSafetyBanner callers retain their existing expanded behavior. |
| CL-5 one-primary-per-screen buttons | CLEANUP PENDING | Exam Registry, Console Work Queue, and Guided Exam Wizard are reviewed: Registry has one primary header action, Open console; Create exam is secondary and Advanced import / repair remains tertiary; Console Work Queue has no screen-level primary CTA because workflow filters are pressed selectors and repeated row actions are contextual; Guided Exam Wizard keeps wizard progression as the sole primary action while Organization mode controls are pressed selectors. Remaining locked scope: B3d-close final cross-surface audit. Rule: a screen may expose at most one screen-level primary CTA; pressed filters/selectors are not primary actions; repeated row actions are contextual; local form submission buttons are scoped to their form/card and are not automatically competing screen-level CTAs. `SetupPanel` redesign remains owned by Lane C and must not be absorbed into B3d. |
| CL-6 remove orphaned root console layout + `ExamTaskRail` | CODE PRESENT IN THIS CHECKOUT | `ExamWorkspace` no longer accepts or branches on `variant="console"` and `ExamTaskRail` is deleted. The standalone eight-tab workspace is unchanged. |
| CL-6b retire dormant console presentation plumbing | CLEANUP PENDING | Locked scope B4 / CL-6b: remove the unused `variant` contract from `ExamWorkspaceContext`; remove dormant console-only branches from `OverviewPanel` and `ReviewActivatePanel`; delete orphaned `ExamPublishImpact` and its isolated test; preserve the active standalone workspace and `ExamActionConsole` routes. `SetupPanel` remains unchanged. |

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
