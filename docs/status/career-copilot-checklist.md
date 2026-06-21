# Career Copilot checklist — repo source of record

Last repo verification: 2026-06-21 at `main @ 2308b31` (includes PRs #745 mastery error-pattern fix, #746 allowlist/pinned-mode fix).

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
| Live canary user allowlist | CODE-FIXED, VALIDATION PENDING | `resolve_effective_mastery_flag(requested_flag, user_id)` implemented in `mastery_writer.py` (PR #746). Reads `FF_MOCK_MASTERY_LIVE_USER_IDS` (comma-separated UUIDs); downgrades `live` → `shadow` for non-allowlisted users; fails closed on empty/malformed allowlist. Applied at `auto_submit_attempt` enqueue, `JOB_ANALYTICS_RETRY` D4 handoff, and `_recover_corrections_after_mock_tests` (pinned-mode: reads job row `mastery_flag_state`, falls back to env flag only for legacy attempts). 17 new tests in `test_mastery_allowlist.py`. Blocking prerequisites for live canary still open: (a) PR-6 GATE FAILED — re-run required; (b) PR-7 NOT STARTED — blocked on PR-6; (c) migration 182 DRY-RUN/APPLY/PERMISSION VALIDATION PENDING; (d) operator must populate `FF_MOCK_MASTERY_LIVE_USER_IDS` with named consenting user(s) before any canary attempt. |
| `_apply_error_patterns` schema fix | CODE-FIXED, VALIDATION PENDING | PR #745: column renamed `error_count` → `frequency_count`; `microtopic_id` removed from top-level columns and stored inside `evidence` JSONB alongside `signal_strength` and `evidence_question_ids`. 9 new schema-regression tests in `test_mastery_error_pattern_schema.py`. |
| Scheduler verification | OPERATOR PENDING | Two env vars govern the scheduler: `ENABLE_SCHEDULER=true` (server.py, primary gate — default disabled) and `DISABLE_SCHEDULER=true` (scheduler.py, override kill switch). Live proof must capture both env var states, scheduler startup/registration, `/api/admin/jobs` payload, manual sweeper run, and pending-job drain. |
| Repeat off/shadow validation | GATE FAILED — BLOCKED ON ALLOWLIST | 2026-06-19 revalidation attempt stopped at Gate 9: no per-user allowlist deployed (see `docs/audits/2026-06-19-final-candidate-revalidation.md`). Code remediations for DEFECT-001/002/003/005A are present. Live operator run cannot start until allowlist gate clears. |
| 14-day shadow gate (PR-7) | NOT STARTED — BLOCKED ON PR-6 | PR-6 did not pass (Gate 9 hard stop: allowlist not deployed); no observation window opened; candidate fingerprint superseded since PR-6 inspection (PRs #723 and #726 modified fingerprinted files); no thresholds evaluated; final fingerprint manifest (`docs/ops/mastery_validation_fingerprint_manifest_v2.txt`) cannot be frozen until allowlist and error-pattern remediation PRs merge; new baseline and exact UTC window_start required after all Lane A prerequisites clear and PR-6 PASS. See `docs/audits/mastery-shadow-14day-gate-2026-06-20.md` and `docs/ops/pr7_shadow_gate_results.md`. |
| `FF_MOCK_MASTERY_WRITES=live` | BLOCKED | Blocked on scheduler verification, clean repeat validation, AND user allowlist implementation + bounded live canary approval. |
| Mock semantics label fix (§17 frontend) | CODE-FIXED, VALIDATION PENDING | `Mocks.jsx`: (1) "Error patterns" eyebrow → "Self-reported error patterns" for `trust_level=self_reported`/`source_type=manual_log` mocks; (2) `MockAnalysis` `SectionHeader` subtitle is now conditional — self-reported shows "based on the values you entered", platform shows "derived from your platform-scored attempt" (removes the false "extracted from your logged answer sheet" copy); (3) `ErrorPatternPanel` footer → "counts entered by you · user-entered, not system-inferred" for self-logged, unchanged for platform-attempt; (4) Average stat relabeled "Average across N logged mocks". No derived-label logic changed (§17.5 pending product approval). Regression tests in `pages/__tests__/Mocks.labels.test.jsx` (15 tests, all passing). |
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
| CL-1b de-leak `ExamActionConsole` | CODE PRESENT IN THIS CHECKOUT | `operatorChrome.humanizeToken` extended to truncate UUID-shaped strings (first 8 chars + "…") — closes the vector where a UUID-valued token reaching any `humanizeToken` fallback would render verbatim. `formatOperatorActor` now shares the same `UUID_TOKEN_RE` constant. `ExamActionConsole` already imports and uses `humanizeToken` for all reason/area/gate fallbacks; no new raw-UUID render sites found. Targeted CL-1b regression test added: plants a UUID as `verdict.status` and asserts the raw UUID does not appear while the 8-char truncation does. |
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
| BUG-EI-1 `POST .../syllabus/propose` → 404 | CODE-FIXED, VALIDATION PENDING | `syllabus_mapper.py` now queries `syllabus_documents` (has `exam_id` column) on both occurrences. Duplicate `ProposerError` and `propose_syllabus_mentions` definitions removed. Regression tests in `tests/exam_intelligence/test_syllabus_proposer.py` — 30 tests passing. Branch: `fix/h1-syllabus-propose-404`. |
| BUG-EI-2 `GET /console/exams/{id}` → 500 | CODE-FIXED, VALIDATION PENDING | Final fix: `load_doc_extraction_counts(strict=False/True)` in readiness.py — strict path (console) uses full pagination + fail-closed reads (execute_or_raise), workspace readiness uses fail-soft wrapper. Full vocabulary: total/extracted/pending/failed/needs_review/not_started. Deterministic latest-job by (created_at, id). No `.limit(2000)` or `.limit(5000)`. 58 tests passing. See `docs/audits/document-readiness-2026-06-21.md`. |

### D-series — Redundant data display (4 defects)

Full evidence: `docs/reviews/exam-intelligence-design-review-2026-06-20.md` §Category 1.

| ID | Area | Status | Notes |
|---|---|---|---|
| D1 | Exam identity in 3 locations simultaneously | CODE-FIXED, VALIDATION PENDING | SmartHeader (`ExamWorkspace.jsx:110–128`) is canonical. Name/slug/type/family removed from `OverviewPanel` identity section and `SetupPanel` "Exam details" card (909–924). Unique fields (management lane, cadence, active) preserved in OverviewPanel. D1 regression tests in `OverviewPanel.test.jsx` and `SetupPanel.identity.test.jsx`. |
| D2 | Readiness scorecard duplicated in header and OverviewPanel | CODE-FIXED, VALIDATION PENDING | `ExamWorkspace.jsx:152–204` (actionable, has CTA) is canonical. Overall score/status summary removed from `OverviewPanel` readiness section; per-section readiness rows (7 sections) are unique to OverviewPanel and preserved. D2 regression tests in `OverviewPanel.test.jsx`. |
| D3 | "Phases needing dates" is filtered duplicate of main phases list | CODE-FIXED, VALIDATION PENDING | Standalone "Phases needing dates" card removed from `SetupPanel` (C2 / D3). Missing-date phases are now flagged inline in `PhaseTimeline.jsx` (new standalone component under `panels/`) with a "Needs date" badge + cycle label (H3/UX-EI-5 cycle context carried through). Regression tests: `PhaseTimeline.test.jsx` (14 tests) and `PhaseDateWorklist.test.jsx` (updated, 10 tests). All 48 targeted tests green. |
| D4 | Competition "Exam" column always identical in workspace context | CLEANUP PENDING | `CompetitionPanel.jsx:43` pre-filters by `exam.id`. `CompetitionMetricsTable.jsx:78` still renders `c.exam` column — value is always the same exam within the workspace. |

### E-series — Multiple overlapping entry points (5 defects)

Full evidence: `docs/reviews/exam-intelligence-design-review-2026-06-20.md` §Category 2.

| ID | Area | Status | Notes |
|---|---|---|---|
| E1 / I7 | KnowledgeGovernance "Exam truth & planner readiness" lane removed | CODE-FIXED, VALIDATION PENDING | Lane card removed from `KnowledgeGovernance.jsx` (§4.4 landing-card removal). Landing copy updated from "Four lanes" → "Three lanes". Exam-governance links (Console, Registry, Create exam) remain in AdminShell primary nav — not duplicated on the KG landing page. Sidebar exam group untouched (removed atomically in I8-A). 4 landing tests updated. |
| E2 | ExamIntelligence.jsx exposes 5 navigation paths simultaneously | **LOCKED — SUPERSEDED; I8 GATED** | Decision locked 2026-06-21: old "registry-first cleanup" approach is superseded. Locked end state: one visible Exam Management front door combining Registry + Console purposes (search/discovery, blocked/needs-action/ready filters, family/exam/cycle context, first blocker, one row action: `Manage exam`). "Console" and "Workspace" must not be peer product choices. I8-A/B/C gated by IA design lock document. See §Exam Management IA section below. |
| E3 | Exam/cycle/phase entities editable from 3 surfaces, no governance model | DESIGN QUESTION | CMS (`ExamIntelCms.jsx:159–200`): full CRUD. Workspace (`SetupPanel.jsx`): operational edits. Header cycle picker (`ExamWorkspace.jsx:136`). UI does not communicate the tier hierarchy (CMS=repair, workspace=operation, CMS=power-users-only). |
| E4 | PyqPaperWorkspace reachable as standalone route and embedded tab | CLEANUP PENDING | Route: `/admin/exam-intelligence/pyq-papers/:id/workspace`. `PyqWorkbenchPanel.jsx:87` also renders `<PyqPaperWorkspace embedded />`. Standalone route has no exam context in URL; embedded version has it from `ExamWorkspaceContext`. No link explains which path to use. |
| E5 | Three surfaces to create a new exam | CLEANUP PENDING | `ExamIntelligence.jsx:153` → GuidedExamWizard. `KnowledgeGovernance.jsx` → same wizard. `ExamIntelCms.jsx:159` → direct CMS entity form (bypasses wizard multi-step validation). UI does not differentiate them. |

### F-series — Workflow gaps and flow inconsistency (5 defects)

Full evidence: `docs/reviews/exam-intelligence-design-review-2026-06-20.md` §Category 3.

| ID | Area | Status | Notes |
|---|---|---|---|
| F1 | No guided workflow for the most common operator task (cycle setup end-to-end) | **LOCKED ARCHITECTURE; I9 IMPLEMENTATION GATED** | Architecture locked 2026-06-21: hybrid approach. (1) Mini-wizard for atomic cycle creation: cycle identity + dates → phase selection/creation → review + save → return to Manage Exam. (2) Persistent 9-step activation checklist (resumable across sessions): Cycle details → Phases and schedule → Source documents → Extraction → Syllabus mapping → PYQ readiness → Policy updates → Competition context → Review and activate. Implementation blocked on I6 cycle-setup gate document defining completion sources, hard/advisory/N-A gates, deep links, resume behaviour, `AddCycleWizard` decision, progress derivation model, and management-mode/cadence applicability per step. |
| F2 | Bulk import modal detached from paper management workflow | CODE-FIXED, VALIDATION PENDING | `BulkImportModal` now accepts `onSuccess(paperId)` prop. On result-step Close, fires `onSuccess(state.selected_paper_id)` then `onClose`. `PyqWorkbenchPanel` passes `onSuccess={(paperId) => { setSelectedPaperId(paperId); setShowBulkImport(false); }}` — auto-selects imported paper and mounts `<PyqPaperWorkspace>`. `CommitResult` shows inline success banner ("N questions committed. Close to open the paper.") and relabels Close → "Open paper" when committed > 0. Tests: `BulkImport.test.jsx` (F2 onSuccess, success banner, button label); `PyqWorkbench.test.jsx` (F2 auto-select via mocked BulkImportModal). |
| F3 | PYQ tab shows one paper at a time with no overview | CODE-FIXED, VALIDATION PENDING | `PyqWorkbenchPanel.jsx` `<select>` replaced with a table (columns: year, section, questions, readiness). Row click sets selected paper; `<PyqPaperWorkspace>` is driven by the selected row. Tests added in `__tests__/PyqWorkbench.test.jsx` asserting no `<select>`, table rows per paper, and row-click selection. |
| F4 | Topics management not accessible from workspace context | DESIGN QUESTION | `TopicAliasesEditor.jsx` nested inside `TopicEditDrawer` inside `SyllabusMapperPanel` only. Topics cannot be browsed or filtered by exam from the Setup tab. Topic prerequisites have no dedicated management surface anywhere. |
| F5 | Policy `affects_*` flags displayed prominently but immutable | CLEANUP PENDING | `PolicyUpdatesTable.jsx:5–11` comment: "flags set at row creation, gated by DB check constraint — this surface only moves reviewer_status." Six colored-pill booleans per row with no edit action. No UI correction path if a flag is wrong. |

### M-series — Missing CRUD / management capabilities (4 defects)

Full evidence: `docs/reviews/exam-intelligence-design-review-2026-06-20.md` §Category 4.

| ID | Area | Status | Notes |
|---|---|---|---|
| M1 | Topic prerequisites: no editable surface | PLANNED | `TopicEditDrawer.jsx` allows editing topic fields, but strength values between topics have no UI. Confirmed: no prerequisite CRUD exists anywhere in the codebase. Requires schema design decision before implementation. |
| M2 | Topic aliases: exists only in mapper context | CLEANUP PENDING | `TopicAliasesEditor.jsx` nested inside `TopicEditDrawer` inside `SyllabusMapperPanel`. No standalone alias management. Operator cannot add aliases before running a proposal. |
| M3 | PYQ questions: all 200 loaded simultaneously, no pagination | CODE-FIXED, VALIDATION PENDING | `limit=200` removed. `PyqPaperWorkspace` now fetches `PAGE_SIZE=50` per page with `limit`/`offset` server params. `reviewer_status` and `source_kind` filters both moved server-side (backend: `source_kind: str | None = Query(default=None)` added to `list_pyq_questions`; frontend: `loadQuestions` sends `source_kind` param when filter ≠ "all"; client-side `source_kind` filter removed). Client-only sorts (`confidence_asc`, `status`) dropped — server orders by `question_number ASC`. Offset resets on filter/paper/source_kind change; page clamped after mutations; questions refetched after review actions; total from server shown in list header. Pagination controls (prev/next, range label) added to left pane. 14 targeted tests: `PyqPaperWorkspace.pagination.test.jsx` (includes source_kind server filter + offset reset). |
| M4 | Subjects surface: IDs visible, no exam-scoped management | CLEANUP PENDING | `ExamIntelCms.jsx:115` loads all subjects globally. No exam-family filter on subjects endpoint confirmed in earlier audit. `subject_id` visible in rendered table. |

### I-series — Identifier leakage (5 sites)

Full evidence: `docs/reviews/exam-intelligence-design-review-2026-06-20.md` §Category 5.
`operatorChrome.humanizeToken` and `formatOperatorActor` enforce no-UUID-in-UI. All five sites violate that contract.

| ID | Location | File:Line | Status | Notes |
|---|---|---|---|---|
| I1 | ReviewQueueTable "Row id" button | `ReviewQueueTable.jsx:92` | CLEANUP PENDING | `{r.id}` raw UUID rendered. `operatorChrome.humanizeToken` pattern exists but not applied here. Covered by H3. |
| I2 | SetupPanel phase error message | `SetupPanel.jsx:803` | CLEANUP PENDING | `{ptError.phaseId}` raw UUID in error message text. Covered by H3. |
| I3 | ExamIntelCms entity table rows | `ExamIntelCms.jsx` (multiple) | CODE-FIXED, VALIDATION PENDING | `renderCellValue` helper imported from `operatorChrome.humanizeToken`; UUID-shaped id/FK cells now rendered as `${first8}…` instead of the full identifier. All entity table rows (exam-families, exams, cycles, phases, topics, coverage, etc.) use this path. 4-test identifier regression added in `ExamIntelCms.identifiers.test.jsx`. |
| I4 | Competition table "exam" column in workspace | `CompetitionMetricsTable.jsx:78` | CODE-FIXED, VALIDATION PENDING | `humanizeToken(c.exam \|\| c.exam_slug) \|\| "—"` replaces the raw `c.exam_slug` render. `humanizeToken` truncates UUID-shaped exam slugs and transforms snake_case slugs into readable labels. 4-test regression in `CompetitionMetricsTable.identifiers.test.jsx`. |
| I5 | Subjects CMS surface | `ExamIntelCms.jsx` subjects entity | CODE-FIXED, VALIDATION PENDING | `subject_id` column in the topics entity table now goes through `renderCellValue` (same fix as I3) — UUID is truncated to `${first8}…`. Covered by `ExamIntelCms.identifiers.test.jsx` test "I5: subject_id FK column is truncated". |

### Prior setup/workspace UX items

| Area | Status | Notes |
|---|---|---|
| Setup phase UX | CLEANUP PENDING | `SetupPanel` still renders separate cards for phases, template phases, and phases needing dates. A single timeline manager has not landed. (Lane C) |
| Template phases duplication | CLEANUP PENDING | `phases.map(...)` still renders all phases while `templatePhases` are rendered again in a separate section. (Lane C) |
| Slow/heavy date inputs | CLEANUP PENDING | Dense phase date worklist still mounts two `DateField` components per row; `DateField` uses `react-day-picker`. (Lane C) |
| Setup mutations governance | CLEANUP PENDING | Cycle create/edit use `useApiAction`; add phase, phase-date patch, and template promotion still call `api.post`/`api.patch` directly. (Lane C) |
| Cycle Trust column | CLEANUP PENDING | Cycle Trust is still derived from cycle status (`active` → `locked`, otherwise `verified`) rather than a real trust lifecycle. |
| Add-cycle product path | CLEANUP PENDING | Route redirects into workspace setup, but `AddCycleWizard.jsx` and direct tests remain. Decide whether to retire or re-promote it. |
| Document readiness extraction status | CODE-FIXED, VALIDATION PENDING | `load_doc_extraction_counts(strict=False/True)` in `readiness.py`: strict path (console) uses full pagination + fail-closed reads; workspace path is fail-soft. Full vocabulary: extracted/pending/failed/needs_review/not_started. Deterministic by (created_at, id). No .limit(2000)/.limit(5000). 58 tests. See `docs/audits/document-readiness-2026-06-21.md`. |
| Bulk import JSON schema undocumented (UX-EI-4) | PLANNED | `ExamIntelCms.jsx:696` references a bulk-import endpoint; `BulkImportModal.jsx` exists. No in-repo docs describe the JSON/CSV schema, required field values, or whether cycle/phase must be pre-created. |
| Competition metrics phase/category cutoffs unstructured (UX-EI-6) | DESIGN QUESTION | Migration 055 stores `cutoff_trend` and `vacancy_by_category` as opaque JSONB. No schema for the JSONB structure documented. Phase/category breakdown not structured in API or UI. |

## Exam Management IA — locked decisions (2026-06-21)

Full decision record: `docs/status/Exam-Management-IA-Findings-and-Locked-Decisions-2026-06-21.md`

**Locked mental model:** Find the exam → Manage the exam → Advanced Repair only when the normal workflow cannot resolve the problem.

**No-new-surface rule:** No new top-level destination unless it removes at least two existing top-level destinations. A new sidebar item or promoted top-level route IS a surface. A drill-in, backend endpoint, or embedded component is NOT.

**Surface-count exit test:** Before: KG exam lane + Registry + Console + Workspace + CMS = 5 visible peers. After: Exam Management → Manage Exam drill-in → Advanced Repair overflow = 1 visible peer with 2 scoped sub-destinations. If visible peer count stays equal or increases, the arc fails.

### Dispatch tracker

| Item | State | Action |
|---|---|---|
| H2/D2 — real extraction readiness | **P0 / READY** | dispatch now |
| I7 — KG exam lane removal | **READY** | dispatch now |
| Mock semantics trust fix | **READY** | dispatch now |
| I5 — PYQ question pagination | **READY (with constraint)** | dispatch now; must not hardcode routes I8-A will remove |
| H1 — syllabus/propose linked-document E2E | **CODE-FIXED, VALIDATION PENDING** | operator E2E test on redeploy |
| IA design-lock document | **NOT STARTED** | write next — keystone gate for all I8 work |
| I6 cycle-setup gate document | **NOT STARTED** | write after IA lock; gates I9 implementation |
| I8-A/B/C — Exam Management consolidation | **GATED** | blocked on IA lock; serial, one owner |
| Portfolio/readiness read-model (backend) | **GATED** | part of IA lock contract; no UI route |
| J1/J2/J3, competition metrics, mixed-PDF, coverage governance, KG rename | **DEFERRED** | contract-first; do not interleave with I8 |

### Locked item details

| Item | Status | Notes |
|---|---|---|
| IA design-lock document | PLANNED — KEYSTONE GATE | Must define: no-new-surface rule, surface-count baseline and exit test, canonical route map, canonical page names, component ownership, front-door content, selected-exam content, canonical readiness source of truth, blocker/deep-link contract, portfolio/readiness read-model contract, Advanced Repair access model, old-route compatibility strategy, redirect timing, component retirement plan, test migration plan. Gates ALL of I8-A/B/C. |
| I7 — KG exam lane removal | PLANNED — UNBLOCKED | Immediate scope only: remove exam lane/card from `KnowledgeGovernance.jsx`; update count/copy from 4 to 3 lanes; update landing-page tests. Do NOT rename KG. Do NOT touch sidebar exam group (deferred to I8-A). Do NOT change backend metrics or routing. |
| KG sidebar exam group | DEFERRED — I8-A ONLY | Must be removed atomically in I8-A when the new single Exam Management sidebar entry lands. Removing it before a replacement nav entry exists makes exam operations harder to discover. |
| KG rename ("Knowledge Governance" → "Policy & Trust") | DEFERRED — SEPARATE LATER PR | Touches sidebar labels, masthead/page titles, breadcrumbs, tests. Must not fold into I7 or I8-A. |
| I8-A — Exam Management front door | GATED — IA LOCK | One sidebar entry; family/exam/cycle discovery + triage; status filters; one row action: `Manage exam`. Atomically adds the new entry AND removes old KG sidebar exam group AND removes Registry/Console peer navigation. Adds legacy route compatibility during transition. |
| I8-B — Manage Exam consolidation | GATED — I8-A + IA LOCK | Merges per-exam Console information into the exam-management drill-in. Requires authority decision (locked in IA design doc): Console detail/action queue canonical OR workspace readiness sections canonical OR unified read model. Do NOT merge components before authority is locked. |
| I8-C — Advanced Repair isolation | GATED — I8-A + IA LOCK | Remove CMS from normal navigation. Expose `Manage exam → More → Advanced repair` scoped to selected exam. Permission-gate it. Explicit warning. Global super-admin recovery may remain, but must not be presented as normal workflow. |
| I8 delivery model | LOCKED — NO FAN-OUT | I8-A, I8-B, and I8-C must be **serial and owned by one lane/owner**. Must NOT be fanned out to parallel agents. Shared write scope includes: `AdminShell.jsx`, `adminRoutes.jsx`, `ExamIntelligence.jsx`, `ExamGovernanceConsole.jsx`, `ConsoleWorkQueue.jsx`, `ExamActionConsole.jsx`, `ExamWorkspace.jsx`, action CTA generation, route/title tests, navigation active-state tests. |
| I9 architecture | LOCKED | Hybrid: (1) bounded mini-wizard for atomic cycle creation only; (2) persistent 9-step activation checklist resumable across sessions. |
| I9 implementation | GATED — I6 GATE DOC | Blocked on gate document defining for all 9 steps: completion source, hard/advisory/N-A gate, deep-link target, resume behaviour, empty-state behaviour, selected-cycle behaviour, management-mode/cadence applicability, `AddCycleWizard` decision, progress derivation model (backend-derived vs frontend-composed), and manual-mark-complete rules. |
| Blocker deep-link contract | LOCKED DIRECTION | All action CTAs must deep-link to exact task state (e.g. `?tab=syllabus&status=pending`; `?tab=documents&document={id}`; `?tab=pyq&paper={id}&status=pending`). Current `cta_route=/workspace/{exam_id}` for all actions is the confirmed defect. Final route shape depends on IA lock. Backend implementation (`console_detail.py`) lands in I8-B. |
| Backend portfolio read-model | PLANNED — GATED | New headless endpoint (not a UI surface) required by I8 consolidated pages. Must return: family, exam, cycles, phases, dates, phase states, per-cycle content readiness. Status vocabulary: `missing/uploaded/extracting/review_pending/ready/stale/failed/not_applicable`. Contract not yet locked. Parallel-safe backend work after contract approval; frontend integration after I8-A. |
| Portfolio/coverage matrix (I10) | CANCELLED — FOLDED INTO I8 | No separate dashboard, coverage-matrix page, or lane. Portfolio hierarchy and coverage readiness are content inside the Exam Management / Manage Exam hierarchy. Adding another route would repeat the KG mistake. |
| Mock semantics trust fix | PLANNED — DISPATCHABLE | Isolated; does not require IA lock or I8. (1) Relabel "Error patterns" → "Self-reported error patterns". (2) Relabel average score → "Average across N logged mocks". (3) Add copy explaining that time pressure / misread / guesswork / concept gap values are entered by the user for manually logged mocks. Files: `app/frontend/src/pages/study/Mocks.jsx` + tests. |
| I5 — PYQ question pagination | PLANNED — DISPATCHABLE | Backend pagination already exists (paper filter, reviewer-status filter, `limit`, `offset`, exact `total`, deterministic ordering). Frontend still uses `limit=200`. Constraint: must NOT hardcode old routes that I8-A will remove. Filters/sorts must move server-side before implementing; reset offset on filter/paper changes; show total after filters; refetch after review actions. |
| J1 — Advanced Repair scoping | DEFERRED — GATED BY I8-C | Selected exam + cycle scope, search, filters, pagination, explicit warning, permission gate. |
| J2 — missing operational editors in Manage Exam | DEFERRED — GATED BY I8-B | Move normal work into Manage Exam tabs: topic/microtopic management, alias management, prerequisite editing, historical paper creation, question/option correction, policy flag correction, cycle-specific entity management. |
| J3 — schema/domain redesign | DEFERRED — CONTRACT-FIRST | Phase/category competition cutoffs, applied vs appeared counts, mixed-format PDF extraction, evidence-based coverage scoring. Each needs its own contract and potentially schema changes before implementation. |
| Competition metrics structure | DEFERRED — CONTRACT-FIRST | Opaque JSONB `cutoff_trend`/`vacancy_by_category`; no locked schema. Needs domain contract + JSON/schema decision + evidence model + reviewer lifecycle. |
| Mixed-format PDF support | DEFERRED — EXTRACTION ARCHITECTURE | Current pipeline assigns one format per document. Does not support page-level layout classification. Product must either support page-range classification or reject unsupported mixed files clearly and document the temporary workaround. |
| Management mode / cadence / coverage governance | DEFERRED — PRODUCT CONTRACT | Who assigns management mode (core/light/index-only/archive), cadence, coverage depth, priority score, high-yield designation? Deterministic rule vs admin judgement vs model suggestion not yet decided. |
| KG rename | DEFERRED — SEPARATE LATER PR | Separate from I7 and I8; touches sidebar labels, masthead/page titles, breadcrumbs, tests. |

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
