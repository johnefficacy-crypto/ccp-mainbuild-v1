# Unified PYQ Practice and Intelligence — Implementation Checklist

Status: **IN DELIVERY — PR-1 → PR-10 CODE-LANDED (VALIDATION PENDING), except PR-5/6 revision mode DEFERRED; PR-11 PARTIAL**  
Verified against repository `main`: **2026-07-08**  
Owners: Exam Intelligence + Study OS + Mock Engine  
Primary architecture: `docs/architecture/pyq-intelligence-v2.md`  
Mock/Study OS integration: `docs/study_os/mock-engine-v2-study-os-integration.md`  
Source-of-record delivery detail per PR: `docs/status/career-copilot-checklist.md` (this file is the contract map; the checklist carries the merged-PR evidence).

> **Delivery snapshot (2026-07-08).** The ordered plan below (§6) has shipped PR-1 through PR-10 to `main`, all at `CODE-FIXED, VALIDATION PENDING` (code merged + tested; operator/DB validation and the mastery live-write gate still pending) — **except PR-5/6's revision entry mode, which is deferred** (PR-8/SRS), so the learner-practice exit gate is not yet fully code-complete. PR-11 has landed slice 1 (media storage, migration 233) and slice 2 (CMS media authoring); its advanced-answer-type runtimes and asset-upload/importer lanes remain deferred. Every unchecked `[ ]` box in this document that a merged PR satisfies is tracked as done in the source-of-record checklist — this contract file is retained as the original scope map and is **not** re-ticked box-by-box. See each PR's status line in §6 for the merged pointer.

## 1. Locked product decision

Store every previous-year question once in the canonical PYQ layer and let learner practice, the mock bank, analytics, mastery, revision, planner and persona consume references or derived evidence.

```text
Exam → Cycle/Year → Phase/Tier → Paper/Shift → Section
                                              ↓
                                      Stimulus/Passage
                                              ↓
                                Question → Options
                                              ↓
                        Reviewed topic/microtopic tags
                                              ↓
        PYQ practice / mock projection / topic analytics
                                              ↓
                           attempt evidence and behaviour
                                              ↓
                   mastery → revision → planner → persona
```

Required learner hierarchy:

```text
Exam → Phase/Tier → Year → Paper/Shift → Section → Question
```

Default learner experience:

- Full papers: phase/tier → year → paper/shift.
- Section practice: section with optional year range.
- Topic practice: subject → topic → microtopic.
- Revision practice: weak or due topics.
- Do not duplicate questions across these views.

UI rule: embed this under the existing Study/Mocks/Learning hierarchy. Do not introduce another top-level destination unless the repository no-new-surface rule is satisfied.

## 2. Current application capability

| Capability | Status | Current authority / evidence |
|---|---|---|
| Exam families, exams, cycles, phases and sections | MERGED / CODE PRESENT | `030_exam_registry_cycles_phases.sql` |
| Section structure: question count, marks, duration, negative marking, difficulty, ordering | MERGED / CODE PRESENT | `exam_phase_sections` |
| Canonical PYQ sources, papers, questions and options | MERGED / CODE PRESENT | `032_pyq_question_intelligence.sql` |
| Paper scope by exam, cycle, phase, year, date, shift and code | MERGED / CODE PRESENT | `pyq_papers` |
| Variable option rows at database level | MERGED / CODE PRESENT | `pyq_options`; no four-option database constraint |
| Reviewed primary/secondary/prerequisite/trap topic tags | MERGED / CODE PRESENT | `pyq_question_topic_tags` |
| Option-pattern and question/topic relation schemas | MERGED / CODE PRESENT | `pyq_option_patterns`, `question_relation_edges`, `topic_relation_edges` |
| Bulk import preflight, dedup and commit | CODE PRESENT — LIMITED CONTRACT | `pyq_bulk_import.py`; fixed A–D importer |
| Verified PYQ → mock bank projection with lineage and invalidation | MERGED / CODE PRESENT | migration 183 + `pyq_mock_projection.py` |
| Exam-realistic phase/section mock blueprint | MERGED / CODE PRESENT | `mock_blueprint.py`, `mock_blueprint_selection.py` |
| Mock attempt shell, answer persistence, result and review | MERGED / CODE PRESENT | `/app/study/mocks/attempts/*` |
| Topic mastery and error-pattern derivation | MERGED / CODE PRESENT | `mastery.py`, `mastery_writer.py` |
| Planner consumption of coverage, PYQ frequency, mastery, errors and persona policy | MERGED / CODE PRESENT | `planner.py` |
| Persona snapshots and study-policy derivation | MERGED / CODE PRESENT | `docs/architecture/persona-layer.md` and persona runtime |
| Revision calendar for topic/note/deck/mistake/custom sources | MERGED / CODE PRESENT | `Revision.jsx` + revision service |
| Dedicated aspirant PYQ catalogue and attempt flow | CODE-LANDED / VALIDATION PENDING (PR-5/6) | Embedded practice via `pyq_practice.py` + `POST /study/mocks/practice/start`, launched from `PyqExplorerSection`; reuses the mock attempt shell (no new surface) |
| Passage/chart/image fidelity | PARTIAL — text/passage CODE-LANDED (PR-5/6 slice A); media storage CODE-LANDED (PR-11 slice 1, migration 233); advanced-type runtimes deferred | `QuestionStimuli` renders passage/caselet/table + `image`/`chart`/`diagram`; MSQ/integer/descriptive runtimes still deferred |
| Unified direct-PYQ attempt evidence into mastery/planner/revision/persona | CODE-LANDED / VALIDATION PENDING (PR-7 → PR-10) | `attempt_evidence.py` normalizes mock + PYQ + trap-drill to `DerivedAttemptAnalytics`; PR-8 shadow mastery, PR-9 planner launch, PR-10 persona aggregates all consume it |

## 3. Confirmed gaps

### G1 — Importer is fixed to four A–D options

- [ ] Replace fixed `option_a`–`option_d` validation with variable-length options.
- [ ] Accept labels such as `A–E`, `1–5`, `I–V`, `(a)–(e)` and other unique source labels.
- [ ] Retain the existing four-column CSV format as backward-compatible legacy input.
- [ ] Make structured JSON the canonical import contract.
- [ ] Add `options_json` for CSV compatibility.

Current blocker: `_CORRECT_OPTIONS = {"A", "B", "C", "D"}` and commit writes exactly four options.

### G2 — Source numbering and display order are conflated

- [ ] Add `source_question_ref text` for values such as `Q1A`, `17(b)` or section-local numbers.
- [ ] Add `display_order integer` for deterministic paper rendering.
- [ ] Keep `question_number integer` nullable/backward-compatible where useful.
- [ ] Stop using `question_number` alone as the paper-order and import identity contract.

### G3 — Questions lack first-class section ownership

- [ ] Add `pyq_questions.section_id → exam_phase_sections.id`.
- [ ] Validate that the question section belongs to the paper’s exam phase.
- [ ] Index paper + section + display order.
- [ ] Use section scope for IBPS/SSC/banking/defence/regulatory practice and analytics.

### G4 — No reusable stimulus/passage/media entity

- [ ] Add `pyq_stimuli` for passage, caselet, table, chart, image and diagram content.
- [ ] Add `pyq_question_stimuli` for shared stimulus-to-question links.
- [ ] Support one stimulus linked to several questions without text duplication.
- [ ] Add asset references for question and option media.
- [ ] Snapshot stimuli/media into runtime attempts for historical integrity.

### G5 — Mock projection supports only standalone single-answer text MCQs

- [ ] Extend projection snapshots with section, display order, source labels and stimuli.
- [ ] Keep eligibility fail-closed for unsupported question types.
- [ ] Preserve `pyq_question_id`, `pyq_paper_id` and year lineage.
- [ ] Continue requiring verified paper, question, options and exactly one verified primary topic.

### G6 — No learner-facing PYQ practice flow

- [ ] Add an embedded PYQ catalogue/drill-in under existing Study/Mocks/Learning IA.
- [ ] Add full-paper, section, topic and revision entry modes.
- [ ] Reuse the existing attempt shell instead of building a parallel runner.
- [ ] Support resume, timer, submission, result and solution review.
- [ ] Add year/phase/shift/section filters with server pagination.

### G7 — Direct PYQ practice does not produce normalized learner evidence

- [ ] Define one source-neutral attempt evidence contract.
- [ ] Emit evidence for mock and PYQ attempt kinds through one adapter.
- [ ] Include correctness, time, skip state, selected answer, error classification and canonical topic scope.
- [ ] Keep immutable question snapshots plus canonical source lineage.
- [ ] Make evidence writes idempotent and replayable.

Suggested attempt kinds:

```text
mock
pyq_full_paper
pyq_section
pyq_topic
pyq_revision
```

### G8 — Mastery and revision scheduling remain split

- [ ] Add a common revision recommendation contract.
- [ ] Distinguish `relearn`, `practice` and `review`.
- [ ] Keep topic mastery scheduling and per-item SM-2-style scheduling separate behind an adapter.
- [ ] Add PYQ-backed revision selection for due/weak topics.
- [ ] Do not add mutable learner aggregates to canonical PYQ records.

### G9 — Planner cannot yet resolve a topic task into a PYQ session

- [ ] Map `retrieval_practice` to a PYQ topic/section session when eligible content exists.
- [ ] Map `revision` to due verified questions from the relevant topic.
- [ ] Map `concept_learning` to content/resource followed by a bounded PYQ check.
- [ ] Persist complete reason payloads and fallback reasons.
- [ ] Keep deterministic planner scoring as authority.

### G10 — Persona receives only coarse practice signals

- [ ] Emit aggregated section accuracy, median response time, skip rate and review completion.
- [ ] Add passage/set avoidance and time-management signals where evidence is sufficient.
- [ ] Feed aggregates into deterministic persona recomputation.
- [ ] Never derive identity/aptitude claims from one question or expose internal persona labels.

### G11 — Advanced objective types are not safely scored

- [ ] Implement MSQ set-based scoring before enabling MSQ selection.
- [ ] Implement integer/numerical answer scoring before enabling integer questions.
- [ ] Add matching-question scoring contract.
- [ ] Add descriptive-answer evaluation only through its governed runtime.
- [ ] Add image-option accessibility and snapshot rules.

### G12 — Mastery live-write gate remains closed

- [ ] Keep new PYQ mastery integration in shadow mode initially.
- [ ] Do not enable live writes before the active P8 shadow gate and subsequent canary approval pass.
- [ ] Reuse current replay, idempotency, classification-readiness and correction-parity controls.

Current repository evidence: P8 window started 2026-07-06 with `FF_MOCK_MASTERY_WRITES=shadow`; live remains blocked.

## 4. Target schema additions

### `pyq_questions`

- [ ] `section_id uuid references exam_phase_sections(id)`
- [ ] `source_question_ref text`
- [ ] `display_order integer`
- [ ] Preserve existing type, language, explanation, difficulty and expected-time fields.

### `pyq_options`

- [ ] `display_order integer`
- [ ] `source_label text`
- [ ] Preserve normalized `option_label` for answer matching.
- [ ] Enforce unique normalized labels per question and deterministic display order.

### `pyq_stimuli`

- [ ] `id`
- [ ] `pyq_paper_id`
- [ ] `section_id`
- [ ] `stimulus_type`
- [ ] `content_text`
- [ ] `language`
- [ ] `display_order`
- [ ] `metadata`

### `pyq_question_stimuli`

- [ ] `question_id`
- [ ] `stimulus_id`
- [ ] `display_order`
- [ ] Unique question/stimulus link.

## 5. Canonical import v2 contract

- [ ] JSON list/envelope supports variable options.
- [ ] Option labels are arbitrary non-empty unique strings.
- [ ] `correct_option_label` must resolve to one supplied option for single-answer MCQ.
- [ ] `source_question_ref` is preserved exactly.
- [ ] `display_order` is explicit and unique within a paper.
- [ ] `section_ref` resolves to an authored section in the paper phase.
- [ ] `stimulus_ref` resolves within the same paper.
- [ ] Preflight returns row-level and stimulus-level errors without writes.
- [ ] Commit remains tokenized, audited and idempotent.
- [ ] Existing A–D CSV remains accepted through an adapter.

Example:

```json
{
  "source_question_ref": "Q17",
  "display_order": 17,
  "section_ref": "reasoning",
  "stimulus_ref": "passage-04",
  "question_text": "Which conclusion follows?",
  "question_type": "mcq",
  "options": [
    {"label": "1", "source_label": "(1)", "text": "...", "display_order": 1},
    {"label": "2", "source_label": "(2)", "text": "...", "display_order": 2},
    {"label": "3", "source_label": "(3)", "text": "...", "display_order": 3},
    {"label": "4", "source_label": "(4)", "text": "...", "display_order": 4},
    {"label": "5", "source_label": "(5)", "text": "...", "display_order": 5}
  ],
  "correct_option_label": "3"
}
```

## 6. Ordered implementation plan

### PR-1 — Schema fidelity

Status: **CODE-LANDED / VALIDATION PENDING** — see checklist (migrations 223 stimulus/section schema + 224 uniqueness).

- [ ] Add section, source-reference and display-order fields.
- [ ] Add stimuli and question-stimulus links.
- [ ] Add option display/source-label fields.
- [ ] Add integrity triggers/checks and indexes.
- [ ] Use a new forward migration; do not alter migration 032.
- [ ] Add PostgreSQL behaviour tests for ownership, ordering and cascade rules.

Exit gate: canonical schema can represent SSC/IBPS/banking/defence/regulatory five-option and shared-passage questions without duplicated passage text.

### PR-2 — Importer v2

Status: **CODE-LANDED / VALIDATION PENDING** — bulk-import v2 (migration 224 uniqueness); variable-option/label + stimulus-ref handling per checklist. Media-type import deferred to PR-11.

- [ ] Implement canonical variable-option JSON parser.
- [ ] Add legacy CSV adapter and `options_json` CSV support.
- [ ] Add section/stimulus reference validation.
- [ ] Add non-integer source-reference handling.
- [ ] Preserve preflight token, dedup and idempotent commit semantics.
- [ ] Add regression tests for 2, 4, 5 and more options plus alternate labels.

Exit gate: official paper JSON can be imported without manual SQL and without the developed extractor.

### PR-3 — Operator review and correction

Status: **CODE-LANDED / VALIDATION PENDING** — CMS stimulus review + cascade (migration 227) and `/pyq-stimuli` authoring in the existing exam-intelligence workspace (no new admin surface).

- [ ] Extend the existing PYQ workspace; no new admin top-level surface.
- [ ] Review paper structure, sections, stimuli, question ordering and options.
- [ ] Add passage/set grouping controls.
- [ ] Show projection eligibility and blockers.
- [ ] Preserve pending → verified/rejected/needs-correction lifecycle and audit reasons.

Exit gate: operators can fully verify a paper without direct database editing.

### PR-4 — Projection and snapshot fidelity

Status: **CODE-LANDED / VALIDATION PENDING** — projection stores section_id + per-option `source_label`/`display_order` + `mock_question_stimuli` passage snapshot (migration 229); SQL/Python content-hash parity. Media (`asset_url`/`alt_text`) projection wiring deferred to PR-11.

- [ ] Extend PYQ → mock projection with section and stimulus snapshots.
- [ ] Preserve source labels and display ordering.
- [ ] Include new fields in source-content hash and stale invalidation.
- [ ] Keep unsupported types blocked.
- [ ] Add projection parity tests between SQL and Python hash implementations.

Exit gate: projected text MCQs, including shared passage sets, render correctly and become stale when canonical content changes.

### PR-5 — Learner PYQ catalogue and full-paper practice

Status: **PARTIAL — full-paper/section/topic CODE-LANDED / VALIDATION PENDING; revision mode DEFERRED (PR-8/SRS)** — slice A (render fidelity) + slice B (practice attempt assembly, migration 231) + slice C (learner launcher `PyqExplorerSection`) + slice D (learner practice UX hardening, PR #940); reuses the mock attempt shell. The source-of-record checklist tracks the combined PR-5/6 row as `IN PROGRESS` for the same reason — the revision entry mode is not yet built, so the full learner-practice exit gate is not code-complete.

> **Live operator validation (2026-07-13) - CODE-FIXED, REDEPLOY/SMOKE-TEST PENDING.** UPSC CSE validation confirmed 177 verified questions with exactly one verified primary tag each and 177 active projections after refreshing 2 stale projections. The deployed learner smoke test exposed PostgreSQL error `42703`: `/pyq-summary` and `/pyqs` selected the nonexistent `exam_phases.name` column instead of canonical `phase_name`, causing HTTP 200 empty payloads. This branch corrects both endpoint queries and their regression fixture. Focused backend verification: `7 passed`. Learner validation remains pending until Render redeploys the fix and a full-paper attempt opens successfully.

> **Slice D — learner practice UX hardening (PR #940, frontend-only + one backend review-contract fix).** Makes the attempt/review flow aspirant-ready: right-side sticky question navigator (mobile bottom sheet) in `MockAttemptShell`; structured stems/passages via shared `QuestionStem`/`QuestionStimuli`; `MockReview` maps classifier codes through `errorTypeLabels.js` (no raw `silly_mistake`/etc. shown) and `MockResult`'s error donut does the same; `MCQSingle` review shows the correct option as a printed label + text, never the option UUID; source-aware "Back to <exam> PYQs" links via `attemptReturnContext.js`; `ExamIntelligenceTab` swaps the operator "PYQ availability trend" chart for a verified-coverage summary (labelled "Verified tagged questions", **not** a practice-launch readiness count); `ExamDetail` no-cycle mode collapses to one banner and hides recruitment-only sections. **Review-order contract fix:** `mock_engine.get_review` now orders questions by the frozen `template_snapshot.question_ids` and returns an immutable 1-based `attempt_order` per question (PostgREST row order is not guaranteed); the review UI numbers by `attempt_order` so filtered palettes keep the real attempt number. Deferred: routing non-MCQ answer types (`match_following`/`numerical_answer`) through `QuestionRenderer` awaits attempt answer/scoring runtime support; full practice→submit→review e2e awaits a seeded projected-PYQ pool fixture.

> **Slice D.2 — practice attempt/review/result UX + timing (PR #942, phase P0 of the Step-3B blocker set).** P0 items 1–7 of the PR-#942 spec, delivered as the first phase (P1 PYQ-Explorer redesign/API + nav IA + P2 community are follow-ups): (1) `MockAttemptShell` + `MockReview` get **fixed/sticky footer action bars** (attempt canvas scrolls independently so Prev/Next/Save & Next never move with stem length); (2) **keyboard navigation** — attempt: `→`/`j` next, `←`/`k` prev, `1`–`6` select option by position, `m` mark, `Ctrl/Cmd+Enter` submit-confirm, `Esc` close transient UI; review: `→`/`j`, `←`/`k`, `1`–`9` jump, `Esc`; (3) shared `optionLabels.js::resolveOptionLabel(option, index)` used across attempt/`OptionList`/`MCQSingle` — never renders a raw `0/1/2/3` (source_label → A/B/C-style option_index → non-numeric option_label → positional letter); (4) exam-canvas layout (stem top-left, not over-centered); (5) **real per-question dwell** tracked in `MockAttemptShell` (accrued on question change/select/mark/submit, flushed into the answer payload's `time_spent_sec`, no double-count on revisit); (6) backend `_build_result` now returns `time_used_sec` (Σ per-response dwell), `time_remaining_sec` (duration − used), `avg_time_per_q_sec`; (7) `MockResult` styled segmented tabs (title-case), real time metrics, and an explicit "time tracking unavailable" state instead of an empty chart. Tests: backend `test_result_payload_includes_time_used_sec`; frontend `optionLabels.test.js`, `MockAttemptShell.keyboard.test.jsx` (kbd nav + numeric select + no-numeric-label + footer), `MockReview.test.jsx` (+footer +kbd), `MockResult.errorLabels.test.jsx` (+time metrics/unavailable). Verified: backend 21 pass; frontend 126 pass; `CI=true react-scripts build` clean; e2e `tsc` clean; existing `attempt-happy-path`/`submit-review` e2e selectors preserved. Deferred to later PR-#942 phases: P1 (PYQ-Explorer intelligence/practice-hub redesign, `/pyqs` enrichment + `GET …/pyq-summary`, learner filters), P1 nav (top-level Exam Intelligence — **owner-approved override of the no-new-surface lock**, to be recorded when it lands), P2 (Accountability Partner card/wizard), and the full projected-PYQ-seeded practice e2e. **Checkpost round 1 (PR #942) — 2 fixes:** (P1) **keyboard-submit pending-save race** — the new `Ctrl/Cmd+Enter` shortcut and the confirm dialog could finalize before non-current answer saves persisted (submit scores from `mock_attempt_responses`). Fixed: the shortcut now mirrors the disabled-button guard (no confirm while `pendingCount>0`/`submitting`); the confirm "Yes, submit" button is disabled while pending; `doSubmit` now calls a new `useAnswerSync.flushAll()` that flushes **every** touched question, waits for terminal states, and returns `{failedIds, answeredCount}` from the synchronous mirror — submit aborts to the failed-save modal if any `failedIds`, and `claimed_answered_count` comes from the flushed mirror (not stale render state). Regressions in `MockAttemptShell.keyboard.test.jsx`: pending→Ctrl+Enter opens no confirm; not-pending→opens; flushAll-failed→no `/submit` + failed modal; happy→`/submit` with the flushed count. (P2) **double punctuation on printed labels** — attempt + correct-answer rendering appended "." unconditionally after `resolveOptionLabel`, so a printed `(a)` showed `(a).`; centralized into `optionLabels.js::formatOptionLabel` (dot only for bare alphanumeric) reused by attempt/`OptionList`/`MCQSingle`. Verified: frontend 88 (mocks) + 43 (exams) pass; build clean.

> **P1 phase A — learner PYQ intelligence API (PR #942 spec items 8–9, backend-only).** `GET /api/exam-intelligence/exams/{slug}/pyqs` items now carry `phase_id`/`phase_slug`/`phase_name`, `subject_id`/`subject_name` (from the question's primary topic tag → `topics.subject_id` → `subjects`), and `topic_names[]` — enrichment the learner filters/cards will consume; `source_type` stays in the payload for diagnostics but the learner UI won't surface it. New `GET /api/exam-intelligence/exams/{slug}/pyq-summary` returns verified-only `totals` (papers / questions / `projected_practice_ready`), `by_year`/`by_phase`/`by_subject`/`by_difficulty` distributions, and per-paper cards with `question_count`, **`practice_ready_count`**, and `practice_enabled` — where `practice_ready_count` mirrors the launch predicate via new `pyq_practice.practice_ready_counts_by_paper` (verified/published/live bank rows + `pyq_question_id` present + unexpired + `sync_status='active'` projection), so it never over-promises a paper the launcher would 409 on. Fails closed to empty arrays. Tests: `tests/exam_intelligence/test_pyq_summary.py` (verified-only exclusion; year/phase/subject/difficulty counts; active-projection practice-ready; /pyqs phase+subject metadata). Verified: backend `pytest tests/exam_intelligence/test_pyq_summary.py tests/study_os/test_pyq_practice.py tests/exam_intelligence/test_trap_drill.py tests/test_pyq_counts_trust.py` → 37 passed; `import server` clean. **Checkpost round 1 (PR #944) — 3 fixes:** (1) `projected_practice_ready` could include active projections on pending/unverified papers — `practice_ready_counts_by_paper` now takes `paper_ids` and the endpoint constrains it to the verified paper set, so totals count only verified papers. (2) `practice_ready_count` now applies the SAME `_snapshot_ready` freeze gate the launch aborts on (loads candidate rows via `_load_questions`, requires options + `correct_option_id`), so a bad snapshot on an active projection is not advertised ready. (3) `by_subject` gains an explicit `Untagged` bucket for verified questions with no primary-subject mapping, so it always sums to `totals.questions`. Regressions added for all three.

> **P2 — Accountability Partner (PR #942 spec items 14–15, frontend-only; stacked onto PR #944 by owner direction).** `ExamDetail`'s Groups section gains a third card, **Accountability Partner** (`accountability-cta`), linking to `/app/accountability?exam=<slug>` (the route already maps to `PartnersScreen`). New `features/community/AccountabilityWizard.jsx` — a lightweight onboarding wizard (target exam prefilled from `?exam=`, preparation stage, daily check-in preference, accountability style, availability window, language) whose "Join accountability pool" CTA lands on a **waitlist confirmation** (`accountability-wizard-done`) since partner-matching has no backend yet — a UI shell so the exam-page CTA never dead-ends; mounted at the top of `PartnersScreen`. Tests: `AccountabilityWizard.test.jsx` (prefill + submit→pool confirmation + no-dead-end + no-exam-param), `ExamDetail.test.jsx` (+accountability CTA href). Verified: frontend community + ExamDetail suites pass; build clean; e2e `tsc` clean. Deferred: real matching backend (pool/request/suggested-match endpoints) when the community matching service lands. **Checkpost round 1 (PR #944, P2):** the wizard's confirmation claimed durable "on the accountability pool / preferences saved" state with no persistence. Fixed: preferences now persist to `localStorage` (`cc.accountability.prefs`, restored on remount, session-only fallback if storage throws) and the copy is honest — "Preferences saved · Saved on this device · matching isn't live yet". CTA renamed "Save my preferences". Test asserts the persisted value and that the copy does not claim server-side pool membership. Next P1 phases (serial, one owner): the PYQ-Explorer "Intelligence + Practice Hub" frontend redesign (items 10–12) consuming these endpoints, then the top-level Exam Intelligence nav (item 13, no-new-surface-lock override), then P2 community (14–15).

> **P1 phase B + C — PYQ-Explorer "Intelligence + Practice Hub" redesign + top-level Exam Intelligence nav (PR #942 spec items 10–13, frontend-only).** Rebuilt `PyqExplorerSection.jsx` from a raw 20-question feed into three purpose-built sections consuming the phase-A endpoints. **(B) Intelligence overview** — new `PyqSummaryCharts.jsx` renders CSS-bar distributions from `/pyq-summary` (`by_year`/`by_phase`/`by_subject`/`by_difficulty`, `summary-by-*` blocks) plus stat tiles including `summary-practice-ready` from `totals.projected_practice_ready`; root `pyq-summary-charts`. **Practice by paper** — new `PyqPaperPracticeCards.jsx` renders one card per `summary.papers[]` entry (`pyq-paper-card`), a `pyq-paper-practice-btn` only when `practice_enabled`, else a `pyq-paper-not-ready` notice — so a 10-paper exam shows 10 cards, not 1,000 question cards, and only launch-accurate papers offer practice. **(C) Browse questions** — the raw feed becomes a collapsible section (`pyq-browse-toggle`/`pyq-browse`, default collapsed; `/pyqs` fetched only when opened). Learner filters are now **Year / Phase / Subject / Topic / Difficulty** (removed **Source / Trust** — internal-only signals never shown to aspirants); topic options derived from a broad `/pyqs` fetch. Question-card chips → Year/Phase/Subject/Difficulty/Q# (dropped Shift/Source). **Nav (item 13, owner-approved no-new-surface-lock override):** promoted exam intelligence out of Eligibility to its own top-level sidebar destination — new `sidebar-exam-intelligence` (`BarChart3`) between Eligibility and Study in `DashShell.jsx`; new routes `/app/exam-intelligence` (catalogue) + `/app/exam-intelligence/exams/:slug` (`ExamDetail`) in `appRoutes.jsx`; old `/app/eligibility/exams/:slug` now redirects via new `ExamDetailRedirect.jsx` (preserves `:slug` + hash) so nothing breaks. Eligibility stays the recruitment/application funnel. Return-to context on practice launch now targets `/app/exam-intelligence/exams/<slug>#pyq-explorer`. Tests: `PyqExplorerSection.hub.test.jsx` (defaults to overview+paper-cards not raw feed; one card per paper + practice only when ready; filters are Year/Phase/Subject/Topic/Difficulty, no Source/Trust), `PyqExplorerSection.practice.test.jsx` (browse-toggle expand before paper/question assertions), `navContract.test.js` (+`/app/exam-intelligence` nav + both routes). Verified: frontend 116 pass (exams/ExamDetail/navContract/appRoutes); `CI=true react-scripts build` clean, entry 194.54 kB gz (< 220 KB budget); e2e `tsc` clean; `exam-detail-no-cycle.spec.ts` retargeted to the canonical `/app/exam-intelligence/exams/:slug` route. Deferred: full projected-PYQ-seeded practice e2e; heavy DashShell render test (nav coverage asserted via `navContract` instead). **Checkpost round 1 (PR #946) — 2 blocking fixes:** (1) **Browse was not truly opt-in** — the topic-filter aux fetch hit `/pyqs` on mount (and only sampled page 1, silently dropping topics after it). Moved behind `browseOpen` (fires once, only after Browse opens) and paginated to completeness (walks pages until `total` reached, `MAX_PAGES` safety cap, fails closed to an empty set + retry rather than a misleading partial list). Regression: initial render calls `/pyq-summary` but never `/pyqs` until `pyq-browse-toggle` is clicked. (2) **`/app/exam-intelligence` landing reused `EligibleExamsPage`** — so the top-level nav still opened the eligibility/recruitment funnel (eligibility copy, `/api/exams/eligibility-summary`, recruitment CTA, `/app/eligibility/exams/:slug` links), violating the item-13 IA split. Added a dedicated `pages/exam-intelligence/ExamIntelligenceCatalogue.jsx` backed by the verified-only `/api/exam-intelligence/exams` catalogue with intelligence-oriented copy + search and cards linking straight to `/app/exam-intelligence/exams/:slug`; route now points at it. Regression `ExamIntelligenceCatalogue.test.jsx`: reads the intelligence catalogue not eligibility-summary; no `eligibility-exams-page`/"Exam eligibility"/recruitment copy; exam links target the top-level detail route (never `/app/eligibility/`). Verified: frontend affected suites 71 pass; build clean (194.56 kB gz); e2e `tsc` clean.

> **Slice H — projected-PYQ practice→submit→review e2e (tests/fixtures only, CODE-LANDED, VALIDATION PENDING).** Closes the deferred half of this exit gate — the workspace seed had no projected verified-PYQ pool, so the full "complete and review a verified previous-year paper" path was never exercised end-to-end. New `app/frontend/e2e/fixtures/seedProjectedPyq.ts` seeds the **canonical** side on the E2E workspace exam — a **verified** `pyq_papers` row + verified `pyq_questions` (printed order via `question_number`/`display_order`) + verified `pyq_options` (printed `source_label`/`display_order`, exactly one correct) + one primary verified `pyq_question_topic_tags` per question — then projects each through the **real** `project_pyq_question_to_mock_bank` bridge RPC. The projection table is RPC-only (migration 183 revokes direct DML on `pyq_mock_question_projections`), so the fixture drives the genuine projection path (183/229) and its trust gates rather than a hand-forged bank/projection. Fixed UUIDs + service-role upserts (idempotent; RPC returns `unchanged` on re-run, projection stays `active`); `resetPyqPracticeAttempts` clears the learner's prior `pyq_practice_*` blueprint attempts. New `app/frontend/e2e/flows/pyq-practice-review.spec.ts` drives the learner path: Exam Intelligence detail → PYQ Explorer overview (`/pyq-summary`) → launch-accurate `pyq-paper-practice-btn` → `POST /practice/start` → shared attempt shell → answer all → submit → result → review with the projected correct answer (printed label, never a UUID). Also validates the live-schema path (migration 231 blueprint source, 183/229 projection bridge) that mock-Supabase unit tests cannot. **Real bug caught → migration `251`:** the E2E surfaced `42501 permission denied for table pyq_mock_question_projections` on the backend's service-role read — 183 granted service_role EXECUTE on the projection RPCs but no table privilege, so practice readiness/launch fails wherever projected PYQ data exists. `251_pyq_projection_service_role_read_grant.sql` (renumbered from 241/249 as main advanced) grants `select` only (writes stay RPC-only). Verified: e2e `tsc --noEmit` → exit 0; migration-contract assertions pass. **VALIDATION PENDING:** the CI e2e run is the live proof (251 unblocks it). **Revision-mode entry stays deferred** (SRS/mastery due-signals, PR-8; mastery live-write gate closed), so the exit gate is not yet fully code-complete.

- [ ] Add embedded PYQ catalogue under existing Study IA.
- [ ] Browse by exam, phase/tier, year and paper/shift.
- [ ] Start/resume a full-paper attempt through the existing attempt shell.
- [ ] Render shared stimuli once per linked question group.
- [ ] Add loading, empty, error and success states through repository frontend contracts.

Exit gate: aspirant can complete and review a verified previous-year paper.

### PR-6 — Section and topic practice

Status: **CODE-LANDED / VALIDATION PENDING** — `pyq_practice.py` supports `paper`/`section`/`topic` modes (topic requires `exam_id`; source printed-order sort; exam-scoped pool); same `POST /study/mocks/practice/start` endpoint. Merged with PR-5.

- [ ] Add section practice with optional year range.
- [ ] Add subject/topic/microtopic practice from verified primary tags.
- [ ] Add question-count and timed/untimed controls.
- [ ] Prevent question duplication within generated sessions.
- [ ] Persist session selection reasons and filters.

Exit gate: SSC/IBPS/banking-style sectional practice and UPSC topic practice both use the same canonical corpus.

### PR-7 — Unified attempt evidence adapter

Status: **CODE-LANDED / VALIDATION PENDING** — `attempt_evidence.py` normalizes mock/generated/PYQ-practice + trap-drill into `mastery_engine.schemas.DerivedAttemptAnalytics`; `MasteryWriter._load_analytics` delegates to it. Read-only (no schema).

- [ ] Define versioned source-neutral attempt evidence.
- [ ] Adapt mock and all PYQ attempt kinds to the same evidence contract.
- [ ] Preserve question snapshot and canonical lineage.
- [ ] Add idempotency keys, replay and failure recovery.
- [ ] Add section/topic/time/error aggregation tests.

Exit gate: downstream systems do not need separate mock-vs-PYQ interpretation code.

### PR-8 — Mastery and revision integration

Status: **CODE-LANDED / VALIDATION PENDING (shadow only)** — isolated `trap_drill_mastery_shadow` table (migration 232) + `trap_drill_shadow.py`, gated behind its own `FF_TRAP_DRILL_MASTERY_SHADOW` (no live value). No live mastery writes; the mastery live-write gate (§G12) stays closed.

- [ ] Feed normalized evidence into topic mastery and error patterns.
- [ ] Implement revision recommendation adapter: relearn/practice/review.
- [ ] Select verified PYQs for due and weak topics.
- [ ] Run in shadow mode first.
- [ ] Add replay, correction-parity and no-double-write tests.

Exit gate: PYQ practice produces validated shadow mastery and revision recommendations without live-state divergence.

### PR-9 — Planner task resolver

Status: **CODE-LANDED / VALIDATION PENDING** — `pyq_practice_launch.py` resolver + `POST /api/study/tasks/{id}/launch-pyq-practice` (task is sole exam-context authority; idempotent via deterministic `uuid5` blueprint id); `planner.py` stamps `launch_type='pyq_practice'` on `retrieval_practice`/`revision` topic tasks. No new migration/surface.

- [ ] Resolve retrieval/revision tasks into bounded PYQ sessions.
- [ ] Respect exam, cycle, phase, section and topic scope.
- [ ] Fail gracefully when verified content is insufficient.
- [ ] Preserve deterministic scoring and explainability.
- [ ] Prevent duplicate active practice tasks.

Exit gate: Study OS can launch the correct PYQ practice from planner tasks.

### PR-10 — Persona behavioural aggregates

Status: **CODE-LANDED / VALIDATION PENDING (PR #914 merged)** — `collect_user_signals` adds `pyq_practice_sessions_30d` (recent-attempt-window-first derivation) + `trap_drill_sessions_30d`; classifier `mock_avoider` and no-activity guards both account for PYQ engagement. Read-derived (no schema).

- [ ] Emit aggregate practice signals after submission/review.
- [ ] Add deterministic persona collector inputs.
- [ ] Adjust study policy using sufficient evidence only.
- [ ] Add safe defaults for missing/failed reads.
- [ ] Verify no internal persona identity label is exposed to aspirants.

Exit gate: persona can adapt task size, mix and cadence based on practice behaviour without reading raw question content.

### PR-11 — Advanced question types and media

Status: **PARTIAL — slice 1 (media storage, migration 233) + slice 2 (CMS media authoring) CODE-LANDED / VALIDATION PENDING; advanced-answer-type runtimes DEFERRED** — `pyq_stimuli` gains `document_asset_id`/`asset_locator`/`alt_text` with fail-closed accessibility governance; `QuestionStimuli` renders `image`/`chart`/`diagram`; `/pyq-stimuli` CMS authors media. Deferred lanes: MSQ/integer/matching/descriptive scoring + UI, image-option accessibility, asset-upload surface, bulk-importer media, PR-4-owned projection/snapshot media wiring.

- [ ] MSQ scoring and multi-select UI.
- [ ] Integer/numerical scoring and input UI.
- [ ] Matching/scenario-specific scoring.
- [ ] Image stems and image options with accessibility metadata.
- [ ] Descriptive linkage through the governed writing/evaluation runtime.

Exit gate: each enabled question type has explicit render, answer, scoring, snapshot, review and replay contracts.

## 7. Cross-cutting gates

- [ ] All canonical content changes require audit reason and reviewer lifecycle.
- [ ] Paper/question/option/tag trust gates remain conjunctive.
- [ ] Exactly one verified primary topic tag remains required for mock/mastery eligibility unless a later approved contract replaces it.
- [ ] Derived frequency, priority, recurrence and learner scores remain outside canonical question rows.
- [ ] Attempt snapshots remain immutable after attempt start.
- [ ] Projection content hashes cover every learner-visible/scoring-relevant field.
- [ ] Unsupported types fail closed rather than being silently mis-scored.
- [ ] New learner collections use `useApiCollection` or the equivalent four-state contract.
- [ ] New mutations use `useApiAction`.
- [ ] Routes remain inside `RouteErrorBoundary`.
- [ ] No live mastery writes until the active shadow/canary gates pass.
- [ ] Live DB facts remain `OPERATOR PENDING` / `VERIFY DB` until captured.

## 8. Definition of done

This workstream is complete only when:

- [ ] At least one five-option banking/SSC-style paper imports and renders correctly.
- [ ] At least one shared-passage UPSC/IBPS-style set imports and renders without duplicating the stimulus.
- [ ] Full-paper, section, topic and revision practice all query the same canonical questions.
- [ ] Verified PYQs project into the mock bank with complete lineage and snapshot fidelity.
- [ ] Mock and PYQ attempts emit the same normalized evidence contract.
- [ ] Shadow mastery/revision output passes replay and correction-parity gates.
- [ ] Planner can launch PYQ sessions with deterministic reasons and safe fallback.
- [ ] Persona consumes only aggregated behaviour signals.
- [ ] Unsupported advanced types remain unselectable until their scoring contracts pass.
- [ ] Operator documentation records staging/live validation and feature-flag disposition.

## 9. Repository files inspected for this checklist

- `AGENTS.md`
- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/wiki/index.md`
- `docs/architecture/pyq-intelligence-v2.md`
- `docs/study_os/mock-engine-v2-study-os-integration.md`
- `docs/architecture/persona-layer.md`
- `app/supabase/migrations/030_exam_registry_cycles_phases.sql`
- `app/supabase/migrations/032_pyq_question_intelligence.sql`
- `app/supabase/migrations/183_pyq_mock_projection_bridge.sql`
- `app/backend/app/exam_intelligence/pyq_bulk_import.py`
- `app/backend/app/study_os/mock_blueprint.py`
- `app/backend/app/study_os/planner.py`
- `app/backend/app/study_os/mastery.py`
- `app/frontend/src/routes/appRoutes.jsx`
- `app/frontend/src/pages/study/Revision.jsx`
- `docs/audits/2026-07-06-p8-t0-start.md`
