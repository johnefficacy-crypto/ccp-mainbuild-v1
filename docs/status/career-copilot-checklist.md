# Career Copilot checklist — repo source of record

Last repo verification: 2026-06-20 at `main @ a2ded8c`.

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
| Live canary user allowlist | DESIGN PRESENT — EXECUTION BLOCKED | Hard prerequisite — `FF_MOCK_MASTERY_LIVE_USER_IDS` (or equivalent per-user allowlist) is **not implemented** in deployed code. `MasteryWriter.process_attempt_sync` applies live writes to all users globally; no per-user gate exists. Bounded canary plan at `docs/ops/pr8_live_canary_plan.md`: one named canary UUID (allowlisted) + one control UUID (not allowlisted), one attempt each, 15-minute window, resolver-at-enqueue architecture required. Blocking prerequisites: (a) allowlist implementation PR not merged; (b) PR-6 GATE FAILED — re-run required after allowlist and pinned-mode PRs deploy; (c) PR-7 NOT STARTED — blocked on PR-6; (d) migration 182 DRY-RUN/APPLY/PERMISSION VALIDATION PENDING; (e) `_apply_error_patterns` schema mismatch (`microtopic_id`/`error_count` not in migration 033) not resolved; (f) pinned effective mode for delayed correction recovery not implemented: `_recover_corrections_after_mock_tests` must read original pinned per-attempt flag, not recalculate from current global env at recovery time (failure case: attempt processed as live → FF flipped back → delayed recovery incorrectly skips live correction recovery). Do not flip the flag without clearing all six. |
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
| CL-1b de-leak `ExamActionConsole` | CODE-FIXED, VALIDATION PENDING | `operatorChrome.humanizeToken` extended to truncate UUID-shaped strings (first 8 chars + "…") — closes the vector where a UUID-valued token reaching any `humanizeToken` fallback would render verbatim. `formatOperatorActor` now shares the same `UUID_TOKEN_RE` constant. `ExamActionConsole` already imports and uses `humanizeToken` for all reason/area/gate fallbacks; no new raw-UUID render sites found. Targeted CL-1b regression test added: plants a UUID as `verdict.status` and asserts the raw UUID does not appear while the 8-char truncation does. |
| CL-2 registry row expansion / column cleanup | CODE PRESENT IN THIS CHECKOUT | Registry rows now lead with the exam name and expose keyboard-accessible details. Lane, cadence, exam key, and secondary metrics moved out of the dense primary table. Existing filters, pagination, console/workspace actions, identifier hygiene, and the /exams API contract remain unchanged. |
| CL-3 remove CMS `+ New guided exam` CTA | CODE PRESENT IN THIS CHECKOUT | Advanced Import / Repair no longer renders the redundant guided-exam CTA. Entity selection, Reload, New row, Bulk import, and their existing forms remain unchanged. The guided-exam route remains available outside the CMS. |
| CL-4 collapsible lifecycle banner | CODE PRESENT IN THIS CHECKOUT | The Exam Registry lifecycle contract now renders as a keyboard-accessible, collapsed-by-default disclosure. Its full reviewed/locked/verified guidance remains available on demand, while other AdminSafetyBanner callers retain their existing expanded behavior. |
| CL-5 one-primary-per-screen buttons | CODE PRESENT IN THIS CHECKOUT | B3d-close six-surface audit passed in this checkout. Registry, Console Work Queue, Action Console, Guided Wizard, Workspace Smart Header, and Advanced Import / Repair were inspected: Registry has one primary header action, Open console; Work Queue has no screen-level primary CTA because workflow filters are pressed selectors and repeated row actions are contextual; Action Console header navigation is secondary and queue actions are contextual; Guided Wizard keeps one forward/create primary per active step while Organization mode controls are pressed selectors; Workspace Smart Header has Go to next action as its sole screen-level primary; Advanced Import / Repair has no header-level primary CTA and its Reload, New row, and Bulk import controls are local neutral repair controls. Rule: a screen may expose at most one screen-level primary CTA; pressed filters/selectors are not primary actions; repeated row actions are contextual; local form submission buttons are scoped to their form/card and are not automatically competing screen-level CTAs. `SetupPanel` local transaction controls remain owned by Lane C and must not be absorbed into B3d. Audit evidence is in `docs/reviews/exam-governance-primary-action-audit.md`. |
| CL-6 remove orphaned root console layout + `ExamTaskRail` | CODE PRESENT IN THIS CHECKOUT | `ExamWorkspace` no longer accepts or branches on `variant="console"` and `ExamTaskRail` is deleted. The standalone eight-tab workspace is unchanged. |
| CL-6b retire dormant console presentation plumbing | CODE PRESENT IN THIS CHECKOUT | Provider variant was removed from `ExamWorkspaceContext`; `OverviewPanel` and `ReviewActivatePanel` now contain workspace-only behavior with readiness percentages preserved for the standalone workspace; orphaned `ExamPublishImpact` and its isolated test were deleted; active standalone workspace and `ExamActionConsole` routes remain unchanged; `SetupPanel` remains unchanged. |

## Exam intelligence / workspace — design defects & UX cleanup

Findings confirmed against this checkout. Full audit evidence:
- `docs/audits/exam-intelligence-gaps-2026-06-20.md` — P0 runtime bugs and UX gaps
- `docs/reviews/exam-intelligence-design-review-2026-06-20.md` — 23 structural design defects (D/E/F/M/I series)

### P0 runtime bugs

| Area | Status | Notes |
|---|---|---|
| BUG-EI-1 `POST .../syllabus/propose` → 404 | PLANNED | `syllabus_mapper.py` queries `document_assets` (wrong table) instead of `syllabus_documents`. `document_assets` has no `exam_id` column; PostgREST returns empty list → 404 raised. Fix: change table name on both occurrences (~line 99 and ~line 503). `ProposerError` and `propose_syllabus_mentions` are defined twice; deduplicate first. |
| BUG-EI-2 `GET /console/exams/{id}` → 500 | PLANNED — AUDITED 2026-06-21 | `console_detail.py::_documents()` queries `document_assets` with `.eq("exam_id", ...)` and `.select("id, extraction_status")` — neither column exists on that table. Audit verdict: **Option A undercounts** — `syllabus_documents.trust_status` is a human-review gate, NOT an extraction signal. The canonical extraction signal is `document_processing_jobs` where `job_type='text_extract'` and `status='succeeded'`. Same missing-column bug exists in `readiness.py:77`. Fix class: backend-only. Files: `console_detail.py` + `readiness.py`. See `docs/audits/document-readiness-2026-06-21.md`. |

### D-series — Redundant data display (4 defects)

Full evidence: `docs/reviews/exam-intelligence-design-review-2026-06-20.md` §Category 1.

| ID | Area | Status | Notes |
|---|---|---|---|
| D1 | Exam identity in 3 locations simultaneously | CLEANUP PENDING | SmartHeader (`ExamWorkspace.jsx:110–128`) is canonical. `OverviewPanel.jsx:121–128` and `SetupPanel.jsx:909–924` re-render the same 4 fields (name, slug, type, family) with no added information. |
| D2 | Readiness scorecard duplicated in header and OverviewPanel | CLEANUP PENDING | `ExamWorkspace.jsx:152–204` (actionable, has CTA). `OverviewPanel.jsx:149–164` (static, same score/status data). Operator sees readiness count twice with no added insight in the panel version. |
| D3 | "Phases needing dates" is filtered duplicate of main phases list | CLEANUP PENDING | `SetupPanel.jsx:201` filters the phases array; `SetupPanel.jsx:816–901` re-renders them as a separate section with date inputs. No cycle label shown — multi-cycle exams are ambiguous. |
| D4 | Competition "Exam" column always identical in workspace context | CLEANUP PENDING | `CompetitionPanel.jsx:43` pre-filters by `exam.id`. `CompetitionMetricsTable.jsx:78` still renders `c.exam` column — value is always the same exam within the workspace. |

### E-series — Multiple overlapping entry points (5 defects)

Full evidence: `docs/reviews/exam-intelligence-design-review-2026-06-20.md` §Category 2.

| ID | Area | Status | Notes |
|---|---|---|---|
| E1 | KnowledgeGovernance adds 5th path to exam setup, zero metrics | DESIGN QUESTION | `KnowledgeGovernance.jsx` "Exam truth & planner readiness" lane has `metricKey: null` — just 3 links (Console, Registry, Create). Same links exist in AdminShell primary nav. TODO comment: "no kg metrics available from overview endpoint for those two lanes yet." |
| E2 | ExamIntelligence.jsx exposes 5 navigation paths simultaneously | DESIGN QUESTION | Lines 145–166: Open console + Create exam + Advanced import/repair header buttons + Overview tab + Exams tab → workspace. No screen communicates the operator's goal before selection. |
| E3 | Exam/cycle/phase entities editable from 3 surfaces, no governance model | DESIGN QUESTION | CMS (`ExamIntelCms.jsx:159–200`): full CRUD. Workspace (`SetupPanel.jsx`): operational edits. Header cycle picker (`ExamWorkspace.jsx:136`). UI does not communicate the tier hierarchy (CMS=repair, workspace=operation, CMS=power-users-only). |
| E4 | PyqPaperWorkspace reachable as standalone route and embedded tab | CLEANUP PENDING | Route: `/admin/exam-intelligence/pyq-papers/:id/workspace`. `PyqWorkbenchPanel.jsx:87` also renders `<PyqPaperWorkspace embedded />`. Standalone route has no exam context in URL; embedded version has it from `ExamWorkspaceContext`. No link explains which path to use. |
| E5 | Three surfaces to create a new exam | CLEANUP PENDING | `ExamIntelligence.jsx:153` → GuidedExamWizard. `KnowledgeGovernance.jsx` → same wizard. `ExamIntelCms.jsx:159` → direct CMS entity form (bypasses wizard multi-step validation). UI does not differentiate them. |

### F-series — Workflow gaps and flow inconsistency (5 defects)

Full evidence: `docs/reviews/exam-intelligence-design-review-2026-06-20.md` §Category 3.

| ID | Area | Status | Notes |
|---|---|---|---|
| F1 | No guided workflow for the most common operator task (cycle setup end-to-end) | DESIGN QUESTION | 9-step task requires navigating 7 separate tabs with no guided flow connecting them. Console shows blockers but links to the full tab, not to the specific action within the tab. SmartHeader shows next blocker at section level only. |
| F2 | Bulk import modal detached from paper management workflow | CLEANUP PENDING | `PyqWorkbenchPanel.jsx:95–101`: `BulkImportModal` closes after import with no auto-navigate to the imported paper and no confirmation of what was imported. Operator must then separately pick the paper from the dropdown. |
| F3 | PYQ tab shows one paper at a time with no overview | CODE-FIXED, VALIDATION PENDING | `PyqWorkbenchPanel.jsx` `<select>` replaced with a table (columns: year, section, questions, readiness). Row click sets selected paper; `<PyqPaperWorkspace>` is driven by the selected row. Tests added in `__tests__/PyqWorkbench.test.jsx` asserting no `<select>`, table rows per paper, and row-click selection. |
| F4 | Topics management not accessible from workspace context | DESIGN QUESTION | `TopicAliasesEditor.jsx` nested inside `TopicEditDrawer` inside `SyllabusMapperPanel` only. Topics cannot be browsed or filtered by exam from the Setup tab. Topic prerequisites have no dedicated management surface anywhere. |
| F5 | Policy `affects_*` flags displayed prominently but immutable | CLEANUP PENDING | `PolicyUpdatesTable.jsx:5–11` comment: "flags set at row creation, gated by DB check constraint — this surface only moves reviewer_status." Six colored-pill booleans per row with no edit action. No UI correction path if a flag is wrong. |

### M-series — Missing CRUD / management capabilities (4 defects)

Full evidence: `docs/reviews/exam-intelligence-design-review-2026-06-20.md` §Category 4.

| ID | Area | Status | Notes |
|---|---|---|---|
| M1 | Topic prerequisites: no editable surface | PLANNED | `TopicEditDrawer.jsx` allows editing topic fields, but strength values between topics have no UI. Confirmed: no prerequisite CRUD exists anywhere in the codebase. Requires schema design decision before implementation. |
| M2 | Topic aliases: exists only in mapper context | CLEANUP PENDING | `TopicAliasesEditor.jsx` nested inside `TopicEditDrawer` inside `SyllabusMapperPanel`. No standalone alias management. Operator cannot add aliases before running a proposal. |
| M3 | PYQ questions: all 200 loaded simultaneously, no pagination | CLEANUP PENDING | `PyqPaperWorkspace.jsx:1131` uses `limit=200`. All questions render at once — no page or section navigation for 100+ question papers (common for UPSC pre). |
| M4 | Subjects surface: IDs visible, no exam-scoped management | CLEANUP PENDING | `ExamIntelCms.jsx:115` loads all subjects globally. No exam-family filter on subjects endpoint confirmed in earlier audit. `subject_id` visible in rendered table. |

### I-series — Identifier leakage (5 sites)

Full evidence: `docs/reviews/exam-intelligence-design-review-2026-06-20.md` §Category 5.
`operatorChrome.humanizeToken` and `formatOperatorActor` enforce no-UUID-in-UI. All five sites violate that contract.

| ID | Location | File:Line | Status | Notes |
|---|---|---|---|---|
| I1 | ReviewQueueTable "Row id" button | `ReviewQueueTable.jsx:92` | CLEANUP PENDING | `{r.id}` raw UUID rendered. `operatorChrome.humanizeToken` pattern exists but not applied here. Covered by H3. |
| I2 | SetupPanel phase error message | `SetupPanel.jsx:803` | CLEANUP PENDING | `{ptError.phaseId}` raw UUID in error message text. Covered by H3. |
| I3 | ExamIntelCms entity table rows | `ExamIntelCms.jsx` (multiple) | CLEANUP PENDING | Entity `id` fields shown in table cells across CMS entity tables. Not covered by H3 — needs separate pass. |
| I4 | Competition table "exam" column in workspace | `CompetitionMetricsTable.jsx:78` | CLEANUP PENDING | `c.exam_slug` rendered alongside workspace header already displaying slug. Overlaps with D4 fix. |
| I5 | Subjects CMS surface | `ExamIntelCms.jsx` subjects entity | CLEANUP PENDING | `subject_id` column visible in subjects table. Overlaps with M4 fix. |

### Prior setup/workspace UX items

| Area | Status | Notes |
|---|---|---|
| Setup phase UX | CLEANUP PENDING | `SetupPanel` still renders separate cards for phases, template phases, and phases needing dates. A single timeline manager has not landed. (Lane C) |
| Template phases duplication | CLEANUP PENDING | `phases.map(...)` still renders all phases while `templatePhases` are rendered again in a separate section. (Lane C) |
| Slow/heavy date inputs | CLEANUP PENDING | Dense phase date worklist still mounts two `DateField` components per row; `DateField` uses `react-day-picker`. (Lane C) |
| Setup mutations governance | CLEANUP PENDING | Cycle create/edit use `useApiAction`; add phase, phase-date patch, and template promotion still call `api.post`/`api.patch` directly. (Lane C) |
| Cycle Trust column | CLEANUP PENDING | Cycle Trust is still derived from cycle status (`active` → `locked`, otherwise `verified`) rather than a real trust lifecycle. |
| Add-cycle product path | CLEANUP PENDING | Route redirects into workspace setup, but `AddCycleWizard.jsx` and direct tests remain. Decide whether to retire or re-promote it. |
| Document readiness extraction status | AUDITED 2026-06-21 | `extraction_status` does NOT exist on `document_assets`. Real extraction signal: `document_processing_jobs` where `job_type='text_extract'` and `status='succeeded'`. `syllabus_documents.trust_status='verified'` is a human-review gate, orthogonal to extraction. Option A (H2 proposal) undercounts. Outcome: backend-only fix. Named files: `console_detail.py`, `readiness.py`. See `docs/audits/document-readiness-2026-06-21.md`. |
| Bulk import JSON schema undocumented (UX-EI-4) | PLANNED | `ExamIntelCms.jsx:696` references a bulk-import endpoint; `BulkImportModal.jsx` exists. No in-repo docs describe the JSON/CSV schema, required field values, or whether cycle/phase must be pre-created. |
| Competition metrics phase/category cutoffs unstructured (UX-EI-6) | DESIGN QUESTION | Migration 055 stores `cutoff_trend` and `vacancy_by_category` as opaque JSONB. No schema for the JSONB structure documented. Phase/category breakdown not structured in API or UI. |

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
