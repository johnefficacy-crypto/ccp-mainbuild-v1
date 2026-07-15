# Unified PYQ Practice and Intelligence — Implementation Checklist

Status: **IN DELIVERY — PR-1 → PR-10 CODE-LANDED; PR-5 FULL-PAPER PRODUCTION PATH OPERATOR VALIDATED FOR UPSC CSE 2025 CSAT SET-B, WITH LEARNER IDENTIFICATION/DISCOVERABILITY DEFECTS OPEN; PR-5/6 REVISION MODE DEFERRED; PR-11 PARTIAL**  
Verified against repository `main`: **2026-07-14**  
Owners: Exam Intelligence + Study OS + Mock Engine  
Primary architecture: `docs/architecture/pyq-intelligence-v2.md`  
Mock/Study OS integration: `docs/study_os/mock-engine-v2-study-os-integration.md`  
Source-of-record delivery detail per PR: `docs/status/career-copilot-checklist.md` (this file is the contract map; the checklist carries the merged-PR evidence).

> **Delivery snapshot (2026-07-14).** PR-1 through PR-10 are code-landed, except PR-5/6's revision entry mode remains deferred (PR-8/SRS) and the mastery live-write gate remains closed. The production full-paper path is no longer merely validation-pending: the exact UPSC CSE 2025 Prelims GS Paper-II CSAT Set-B corpus was validated with real learner/admin identities, 80 verified questions, 80 active projections, an exact 80-question learner-owned frozen attempt, refresh persistence, submission/scoring/result/review, and real-JWT projection-table RLS. Overall PR-5 remains **PARTIAL**, because exact Set-B identity is absent from the learner card, `UPSC` catalogue search misses the exam, the large-paper palette is not sufficiently discoverable, MCQ responses cannot be cleared back to unattempted, provenance metadata is stale, and revision entry mode is still deferred. PR-11 has landed media storage/CMS slices while advanced-answer-type runtimes and asset-upload/importer lanes remain deferred. Every unchecked `[ ]` box that merged code satisfies is tracked in the source-of-record checklist; this contract map is not re-ticked wholesale.

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
| Mock attempt shell, answer persistence, result and review | MERGED / PRODUCTION OPERATOR VALIDATED FOR EXACT 80-Q CSAT SET-B FULL PAPER | `/app/study/mocks/attempts/*`; dated evidence in `docs/audits/2026-07-14-upsc-cse-2025-csat-set-b-learner-access-validation.md` |
| Topic mastery and error-pattern derivation | MERGED / CODE PRESENT | `mastery.py`, `mastery_writer.py` |
| Planner consumption of coverage, PYQ frequency, mastery, errors and persona policy | MERGED / CODE PRESENT | `planner.py` |
| Persona snapshots and study-policy derivation | MERGED / CODE PRESENT | `docs/architecture/persona-layer.md` and persona runtime |
| Revision calendar for topic/note/deck/mistake/custom sources | MERGED / CODE PRESENT | `Revision.jsx` + revision service |
| Dedicated aspirant PYQ catalogue and attempt flow | PARTIAL — FULL-PAPER PRODUCTION PATH VALIDATED; IDENTIFICATION/DISCOVERABILITY UX DEFECTS OPEN; REVISION ENTRY DEFERRED | Embedded practice via `pyq_practice.py` + `POST /study/mocks/practice/start`, launched from `PyqExplorerSection`; exact Set-B audit above |
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

Current repository evidence: the prior P8 window was ended by owner direction; `FF_MOCK_MASTERY_WRITES=live` remains blocked until a fresh shadow window and canary pass.

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

Status: **PARTIAL — EXACT UPSC CSE 2025 CSAT SET-B FULL-PAPER PRODUCTION FLOW + ACCESS CONTROL OPERATOR VALIDATED (2026-07-14); IDENTIFICATION/DISCOVERABILITY/CLEAR-RESPONSE UX DEFECTS OPEN; REVISION MODE DEFERRED (PR-8/SRS)** — slice A (render fidelity) + slice B (practice attempt assembly, migration 231) + slice C (learner launcher `PyqExplorerSection`) + slice D (learner practice UX hardening, PR #940); reuses the mock attempt shell. Full-paper data integrity and runtime are proven, but the learner-practice exit gate is not complete while the exact paper cannot be identified from the card, catalogue search misses expected aliases, large-paper palette discoverability and clear-response remain open, and revision entry is absent.

> **Exact Set-B production validation (2026-07-14) — PARTIAL PASS.** Full record: `docs/audits/2026-07-14-upsc-cse-2025-csat-set-b-learner-access-validation.md`. Environment: frontend SHA `33f52f3b2d1e3558821a5c08c62eca56a9c24e82`, backend SHA `9d3d1c78be728088d5387147ad06a4d81176f872`, Supabase `ylfnbxyqiyiqvxtthhum`. Real `/api/auth/me` sessions proved learner role `user` and admin role `super_admin`. Canonical paper `505b29a0-0d4d-5230-88aa-3bbc525a6db5` is `GS-PAPER-II-CSAT`, metadata Set-B, official UPSC PDF attached, `trust_status=verified`, 80 verified questions, 80 active projections. `/pyq-summary` exposed the exact paper with `question_count=80`, `practice_ready_count=80`, `practice_enabled=true`. `POST /api/study/mocks/practice/start` returned a learner-owned `pyq_practice_paper` attempt with 80 template ids, 80 response rows, 80 unique bank/canonical question ids and exact frozen paper lineage. Selected answers survived refresh. Submit/result/review returned 200; `2 correct + 11 wrong + 67 unattempted = 80`; time dwell persisted (`2167s`); printed source option labels were preserved. Direct PostgREST RLS proof: anonymous `200 []`, learner `200 []`, super-admin `200` with one projection row. **Untimed clarification:** `time_remaining_sec=null` is expected because this paper practice launch carried no duration; the 24-hour abandonment TTL is intentionally not a learner countdown. No further operator testing is required for this attempt.

> **Earlier aggregate validation (2026-07-13).** Full record: `docs/audits/2026-07-13-upsc-cse-pyq-learner-flow-operator-validation.md`. PR #980 fixed the canonical `exam_phases.phase_name` query; the aggregate learner API returned 4 papers / 177 questions / 177 practice-ready, and a 97-question GS paper completed through result/review. The exact Set-B run above supersedes the earlier blanket timer interpretation: distinguish timed attempts (must show a countdown) from untimed paper practice (must show explicit `Untimed`, not an ambiguous placeholder).

> **Slice I — consolidated post-validation learner-UX follow-ups (OPEN, bounded frontend/API + e2e).** (1) **Exact paper identity** [High / release blocker for exact-paper claim] — extend the safe learner paper summary with `paper_code` and a reviewed display label/set identity; render `CSAT · Set-B`; test two same-year/same-phase papers. (2) **Catalogue acronym/alias search** [High] — search normalized name, slug, aliases/acronyms and family so `UPSC` finds `upsc-cse`. (3) **Large-paper palette discoverability** [High] — dedicated vertical scroll container with footer-height reserve; active item `scrollIntoView({block:'nearest'})`; canonical active-state sync; test 80+ and 97-question keyboard/mouse/direct-palette navigation. (4) **Clear MCQ response** [High] — explicit `Clear response` action that sends `selected_option_id:null` through `useAnswerSync`, updates answered counts/palette, survives refresh and reconciles at submit/review. (5) **Timed/untimed label** [Medium] — timed attempts show countdown; untimed PYQ practice renders `Untimed`, never ambiguous `--`. (6) **Review option separation** [Medium] — keep each printed option in a separate semantic element; retain the earlier ≥97-question review regression. (7) **Stale provenance metadata** [cleanup] — verified source/paper promotion must clear or replace `provenance_pending=true` atomically.

> **Slice D — learner practice UX hardening (PR #940, frontend-only + one backend review-contract fix).** Makes the attempt/review flow aspirant-ready: right-side sticky question navigator (mobile bottom sheet) in `MockAttemptShell`; structured stems/passages via shared `QuestionStem`/`QuestionStimuli`; `MockReview` maps classifier codes through `errorTypeLabels.js` and `MockResult` does the same; `MCQSingle` review shows the correct option as a printed label + text, never the option UUID; source-aware return links via `attemptReturnContext.js`. `mock_engine.get_review` orders by frozen `template_snapshot.question_ids` and returns immutable 1-based `attempt_order`.

> **Slice D.2 — practice attempt/review/result UX + timing (PR #942).** `MockAttemptShell` + `MockReview` have fixed/sticky footer action bars; keyboard navigation; shared option-label formatting; exam-canvas layout; persisted per-question dwell; result `time_used_sec`/`time_remaining_sec`/`avg_time_per_q_sec`; submit flushes all touched answers before finalization. The production Set-B run confirms persistence/timing/result behavior. The remaining timer requirement is presentation only: show countdown for timed attempts and explicit `Untimed` for no-duration practice.

> **P1 phase A — learner PYQ intelligence API.** `/pyqs` carries phase/subject/topic metadata. `/pyq-summary` returns verified-only totals/distributions and per-paper `question_count`, `practice_ready_count`, `practice_enabled`, with readiness mirroring the launch freeze gate. The exact Set-B audit proves the contract live; follow-up must add a safe exact paper display identity without exposing internal-only fields.

> **P2 — Accountability Partner.** Existing frontend-only waitlist/preferences shell; real matching backend remains deferred. Unchanged by this validation.

> **P1 phase B + C — Intelligence + Practice Hub and top-level Exam Intelligence nav.** The hub, paper cards, opt-in browse and canonical routes are code-landed. Production showed the direct detail route works, but catalogue search currently matches only `exam.name` and failed the expected `UPSC` lookup; Slice I owns the bounded search correction.

> **Slice H — projected-PYQ practice→submit→review e2e.** The seeded Playwright fixture remains the repeatable regression. The live-production equivalent is now operator validated for the exact 80-question Set-B corpus, including projection RLS. Extend automation with exact paper identity/search/clear-response and >80-question palette visibility; revision-mode entry stays deferred.

- [ ] Add embedded PYQ catalogue under existing Study IA.
- [ ] Browse by exam, phase/tier, year and paper/shift.
- [ ] Start/resume a full-paper attempt through the existing attempt shell.
- [ ] Render shared stimuli once per linked question group.
- [ ] Add loading, empty, error and success states through repository frontend contracts.

Exit gate: aspirant can complete and review a verified previous-year paper. **Runtime/data/RLS portion PASS for exact CSAT Set-B; exact-paper learner identification/discoverability and clear-response follow-ups remain open.**

### PR-6 — Section and topic practice

Status: **CODE-LANDED / VALIDATION PENDING** — `pyq_practice.py` supports `paper`/`section`/`topic` modes (topic requires `exam_id`; source printed-order sort; exam-scoped pool); same `POST /study/mocks/practice/start` endpoint. Merged with PR-5. The 2026-07-14 production proof covers paper mode only; it does not close section/topic operator validation.

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
- [ ] Live DB facts remain `OPERATOR PENDING` / `VERIFY DB` until captured. Exact Set-B paper/attempt/RLS facts are captured in the dated 2026-07-14 audit; do not generalize them to section/topic/revision or mastery gates.

## 8. Definition of done

This workstream is complete only when:

- [ ] At least one five-option banking/SSC-style paper imports and renders correctly.
- [ ] At least one shared-passage UPSC/IBPS-style set imports and renders without duplicating the stimulus.
- [ ] Full-paper, section, topic and revision practice all query the same canonical questions.
- [ ] Verified PYQs project into the mock bank with complete lineage and snapshot fidelity.
- [ ] Mock and PYQ attempts emit the same normalized evidence contract.
- [ ] Shadow mastery/revision output passes replay and correction-parity gates.
- [ ] Planner can launch PYQ sessions with deterministic reasons and safe fallback.
