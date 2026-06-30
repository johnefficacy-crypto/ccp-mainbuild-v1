---
owner: exam-intelligence
status: architecture decision + phased implementation plan
last_targeted_reconciliation: 2026-06-30
reconciliation_scope: frequency-semantics section + delivery-order steps 2-4 (including P2/Track-C gate boundary); full cross-examination of all source paths, gap entries, and delivery dependencies not performed in this pass
source_of_truth: code
related_code:
  - app/backend/app/exam_intelligence/coverage.py
  - app/backend/app/exam_intelligence/pyq_papers.py
  - app/backend/app/exam_intelligence/score_snapshots.py
  - app/backend/app/study_os/planner.py
  - app/backend/app/study_os/mastery.py
  - app/backend/app/study_os/mastery_writer.py
  - app/backend/app/study_os/mastery_engine/
  - app/backend/app/study_os/mock_blueprint_selection.py
  - app/backend/app/admin/pyq_mock_projection.py
  - app/backend/app/api/admin_exam_intelligence.py
  - app/backend/app/api/flashcards.py
related_migrations:
  - app/supabase/migrations/029_exam_intelligence_taxonomy.sql
  - app/supabase/migrations/030_exam_registry_cycles_phases.sql
  - app/supabase/migrations/032_pyq_question_intelligence.sql
  - app/supabase/migrations/033_exam_topic_analytics_snapshots.sql
  - app/supabase/migrations/056_exam_policy_updates.sql
  - app/supabase/migrations/135_mock_engine_core.sql
  - app/supabase/migrations/156_resource_extension.sql
  - app/supabase/migrations/183_pyq_mock_projection_bridge.sql
  - app/supabase/migrations/198_syllabus_documents_source_document_id.sql
  - app/supabase/migrations/201_pyq_source_review_transaction.sql
review_cadence: per-sprint
---

# PYQ Intelligence v2 — code-verified architecture and gap plan

## Decision

The proposed PYQ knowledge-graph direction is valid, but it must not be implemented as a parallel greenfield platform.

The repository already has the canonical taxonomy, PYQ graph relations, review gates, learner mastery, adaptive planner, mock engine, PYQ-to-mock projection, resource classification, and spaced-repetition foundations. The correct design is to extend those authorities through versioned, reviewable analytical outputs.

Do not introduce Neo4j, Pinecone/Weaviate, or a stateful multi-agent runtime as the default architecture. PostgreSQL/Supabase is already the transactional and graph-shaped source of truth. New AI work should be bounded jobs with explicit inputs, idempotency, confidence, model version, evidence, and human review.

## Verified current state

| Proposed capability | Repository state | Actual authority |
|---|---|---|
| Subject → topic → microtopic hierarchy | Present | `subjects`, hierarchical `topics.parent_topic_id`, and `topics.level in ('topic','microtopic','concept')` in `029_exam_intelligence_taxonomy.sql` |
| Syllabus-to-topic mapping | Present | `syllabus_documents`, `syllabus_topic_mentions`, syllabus mapper/review workflow; `syllabus_documents.source_document_id FK → document_assets` added in migration 198 (mirrors PYQ document linkage) |
| PYQ papers, questions, options | Present | `pyq_sources`, `pyq_papers`, `pyq_questions`, `pyq_options` in `032_pyq_question_intelligence.sql` |
| PYQ topic/microtopic tagging | Present | `pyq_question_topic_tags` with role, source, confidence, and review status |
| Distractor/trap intelligence | Schema present | `pyq_option_patterns`, including chronology, concept-confusion, formula-confusion, elimination, and common-trap patterns |
| Near-duplicate and concept relations | Schema present | `question_relation_edges` and `topic_relation_edges` |
| Exam priority/high-yield overlay | Present | locked `exam_topic_coverage.exam_priority_score`, `is_high_yield`, confidence, evidence source |
| Versioned analytical score output | Schema present, draft writer implemented | `exam_topic_score_snapshots` exists; `score_snapshots.py::compute_exam_topic_scores` writes SHA-256-idempotent draft rows; admin `GET/PATCH/POST compute` surface on the existing exam-intelligence router enforces `draft→reviewed→locked` transitions (PR #767, MERGED). `locked_score_snapshots()` wired into `planner.py` as a 0–15 pt confidence-weighted additive signal (PR #773, MERGED). No AI writes into locked rows. |
| Basic exam DNA visualisation | Partial | verified PYQ counts and `difficulty_heatmap()` exist; no governed recency/trend/recurrence score |
| Learner competency | Present at topic level | `user_topic_mastery`, `user_topic_error_patterns`, generated-attempt mastery pipeline |
| Adaptive planner | Present | deterministic `planner.py` consumes locked coverage, verified PYQ counts, mastery, errors, prerequisites, competition, and policy updates |
| PYQ-backed mock generation | Present | migrations 183–191 and `pyq_mock_projection.py` project reviewed PYQs into `mock_question_bank` with lineage and invalidation |
| Mastery-informed mock selection | Planned/blocked | A-PR4/A-PR5 remain blocked by the live mastery validation gate in `career-copilot-checklist.md` |
| Spaced repetition | Split implementation | flashcards use SM-2-lite; mastery uses fixed 2/5/10-day revision bands |
| Resource taxonomy | Partial | `community_resources` has exam/subject/topic/microtopic, difficulty, level, format, review, validity fields |
| Current-affairs-to-microtopic linking | Missing | `exam_policy_updates` is official exam-change intelligence, not a general current-affairs corpus |
| Cognitive/Bloom classification | Missing as a governed field | no first-class reviewed cognitive-demand record was found |
| Recurrence prediction | Missing | no calibrated prediction writer, backtest, snapshot, or publication gate was found |

## Corrections to the proposed model

### 1. Microtopic is already represented

Do not create a separate `microtopics` table. A microtopic is a row in `topics` with `level='microtopic'`, linked through `parent_topic_id`. Existing APIs and the planner already expose hierarchy fields.

### 2. Do not store derived aggregates on every PYQ question

The following proposed fields are analytical outputs, not canonical question attributes:

- `frequency_count`
- `last_appeared`
- `predicted_recurrence_score`
- exam-level heat/priority score

They change when the corpus, trust state, review status, time window, or model changes. Persist them as versioned snapshots with evidence and model version, using the existing `exam_topic_score_snapshots` authority.

Canonical question records should retain observed facts: paper, year, text, options, correct answer, difficulty, language, review status, and reviewed topic relations.

### 3. Separate exam priority from appearance prediction

A topic can be strategically important without being likely to appear in the next paper. Keep separate outputs:

- `exam_priority_score`: governed study importance.
- `appearance_signal`: experimental, calibrated signal with a forecast horizon.
- `confidence_score`: evidence sufficiency and model confidence.
- `learner_priority_score`: user-specific planner output.

Do not present a priority score as a probability.

### 4. “Bloom level” should be cognitive demand, not an exam stereotype

Do not hard-code claims such as “UPSC = analyze” or “NEET = recall.” Store reviewed per-question cognitive demand and aggregate only from verified question evidence.

Recommended vocabulary:

- `recall`
- `understand`
- `apply`
- `analyze`
- `evaluate`
- `multi_step_reasoning`

`create` is generally unsuitable as a label for objective MCQ scoring. Question format, reasoning depth, and cognitive demand should remain separate dimensions.

### 5. Current affairs must not reuse `exam_policy_updates`

`exam_policy_updates` has a strict official-source trust contract for notification, date, pattern, syllabus, vacancy, eligibility, and related exam changes. General news/current affairs has different provenance, expiry, correction, and editorial requirements.

A future current-affairs pipeline needs a separate source and review model. It may link to canonical topics, but must not silently set `affects_*` flags or modify official exam facts.

## Canonical architecture

```text
Official syllabus / reviewed PYQ sources / reviewed resources / reviewed CA sources
                              │
                              ▼
                    Ingestion + provenance
                              │
                              ▼
                   Human-reviewed canonical layer
       subjects → topics → microtopics/concepts
       pyq_papers → pyq_questions → options → reviewed tags
       option patterns + question/topic relation edges
                              │
                              ▼
                 Versioned analytical snapshot layer
       exam-topic frequency, recency, trend, difficulty, confidence
       optional calibrated appearance signal
                              │
               ┌──────────────┴──────────────┐
               ▼                             ▼
        Learner signal layer            Content delivery layer
 mastery, errors, retention, due date    resources, PYQs, mocks, CA links
               │                             │
               └──────────────┬──────────────┘
                              ▼
                  Deterministic adaptive planner
                              │
                              ▼
                study task → attempt → analytics
                              │
                              └──────── feedback to mastery
```

## Scoring contracts

### Verified frequency

**Implemented (PR #767, slice-1 — MERGED):** `verified_pyq_topic_counts()` in `coverage.py` now filters `tag_role='primary'` at the DB query and guards the count loop (defence-in-depth), so one verified question can no longer inflate multiple topics through secondary/trap/calculation_layer tags. Paper `trust_status='verified'` + question `reviewer_status='verified'` + tag `reviewer_status='verified'` gates remain conjunctive. Seven frequency-semantics regression tests pass (`test_pyq_frequency_semantics.py`).

The three candidate contracts were:

1. **Primary-only (selected and implemented):** one verified primary tag per question.
2. Role-weighted: primary = 1.0, secondary/conceptual = configured fractional weight, traps excluded from topic frequency.
3. Multi-label coverage: count all roles but label the metric as associations, not questions.

Role-weighted scoring remains a future option after corpus validation. The current list API is presentation-paginated (Python-side slice after full enrichment); true DB-level pagination and count is a bounded scalability follow-up.

### Exam-topic analytical snapshot

Use `exam_topic_score_snapshots` rather than adding mutable score columns to `topics` or `pyq_questions`.

Each published snapshot should include:

```text
exam_id, exam_cycle_id?, exam_phase_id?, topic_id
model_version, computed_at, evidence_count
input_summary, score_components
exam_priority_score, is_high_yield, confidence_score
status: draft → reviewed → locked | rejected
```

Suggested components, each normalized and visible in `score_components`:

```text
frequency_component     verified primary PYQ share in a defined corpus/window
recency_component       configurable time decay, never a hidden 2–3× constant
trend_component         change across comparable windows with minimum sample size
difficulty_component    observed verified difficulty distribution
coverage_component      locked syllabus/exam-coverage importance
evidence_quality        source trust + review completeness + corpus coverage
```

Do not hard-code a “three-year cycle” boost. Cyclicality must be backtested per exam/phase and disabled where sample size or stability is insufficient.

### Learner priority

The existing planner score is a transparent additive blend and should remain the authority. Extend it rather than replacing it with an unbounded multiplication.

Target inputs:

```text
locked exam-topic priority
+ learner mastery gap
+ verified PYQ evidence
+ error-pattern urgency
+ revision-due signal
+ exam-window urgency
+ explicit user pin/mute preferences
```

Multiplying all factors can collapse a valid topic to zero or amplify a noisy prediction. Keep normalized additive components and persist the complete reason payload.

### Appearance signal

An appearance signal is experimental until it passes backtesting. It must carry:

- exam and phase scope
- forecast horizon
- model version
- training/evidence window
- corpus coverage
- calibration metrics
- confidence/abstention reason
- generated timestamp and expiry

User copy must say “historical signal” or “elevated evidence,” not “will appear.” No prediction dashboard should ship before calibration and operator review exist.

## The proposed “8 agents” as bounded capabilities

Do not run eight autonomous agents. Implement independently testable services/jobs.

| Proposed agent | Correct repository-aligned implementation |
|---|---|
| Syllabus Parser | Extend the existing document extraction + syllabus mapper; proposals remain pending until reviewed |
| PYQ Tagger | Batch classification job writing pending tags/classifications with confidence and model version; no direct verification |
| Learner Profiler | Existing attempt analytics, mastery writer, error patterns, and correction policy; add explicit confidence/error self-report only where UX supports it |
| Adaptive Planner | Extend `planner.py`; preserve deterministic scoring, versioned plans, pin/mute autonomy, and reason payloads |
| Current Affairs Linker | New provenance-controlled CA ingestion/link service; separate from official policy updates |
| Resource Curator | Deterministic ranking over reviewed `community_resources`; AI may suggest candidates but not bypass review/validity gates |
| Mock Generator | Existing blueprint selector + source-mix policies + PYQ projection; personalization only after current live-mastery gates pass |
| Spaced Repetition Scheduler | Reuse the shared SRS service; unify flashcard due state with topic-level revision signals through an adapter, not a second scheduler |

## Gap analysis

### P0 — semantic correctness before new scoring

1. Define whether PYQ topic frequency is primary-only or role-weighted.
2. Prevent secondary/trap relations from being marketed as unique question appearances.
3. Define corpus completeness thresholds per exam/phase/year before publishing percentages.
4. Keep paper, question, option, and tag trust gates conjunctive.
5. Add fixed-input parity tests wherever SQL and Python compute the same score/hash.

### P1 — activate the existing analytical snapshot model

Build a deterministic score computation service that:

- reads only verified papers/questions/tags and locked coverage;
- paginates all corpus reads;
- produces draft `exam_topic_score_snapshots`;
- records component values, evidence IDs/counts, model version, and corpus window;
- is idempotent for the same input fingerprint;
- requires review/lock before planner or user surfaces consume it;
- preserves prior snapshots for audit and rollback.

Do not write directly into locked `exam_topic_coverage` from an AI job.

### P2 — governed cognitive and distractor classification

Add a reviewed classification record rather than hiding labels in generic JSON metadata. It should support:

- question ID
- classification dimension (`cognitive_demand`, `reasoning_form`, `trap_pattern`)
- value
- classifier source/model version
- confidence
- evidence/rationale
- reviewer lifecycle and audit actor/time

Reuse `pyq_option_patterns` for option-level traps. Do not duplicate trap labels in question metadata without a migration-backed authority.

### P3 — learner evidence and revision unification

Current state is split:

- `mastery.py` computes topic mastery and fixed revision intervals.
- `mastery_writer.py` processes generated-attempt evidence behind feature gates.
- flashcards use SM-2-lite in `app.services.srs`.

Unify through a common revision recommendation contract, not one shared mutable table. A topic can need conceptual re-study while related flashcards have individual SM-2 schedules.

Required distinction:

- `relearn`: mastery/error evidence indicates a concept gap.
- `review`: retention is due but underlying mastery is adequate.
- `practice`: application or trap evidence is weak.

### P4 — resource ranking

Use reviewed resource metadata already added in migration 156. Add ranking inputs only after the underlying values are populated reliably:

- exact topic/microtopic match
- cognitive-demand fit
- language and format preference
- validity window
- source/reviewer trust
- completion/engagement outcomes
- price/budget constraints

Community rating alone must not override provenance or validity.

### P5 — current-affairs linking

Required new concepts:

- source registry link and publisher
- canonical URL/content fingerprint
- publication/event dates
- article/event/entity records
- correction/supersession state
- topic-link confidence and review state
- valid-from/valid-until or expiry
- copyright-safe excerpt/summary policy

Static-topic links can then surface reviewed PYQs and resources. Generated integrated questions remain draft mock-bank content requiring normal author/reviewer workflow.

### P6 — personalized mock selection

Do not start this while `FF_MOCK_MASTERY_WRITES=live` remains blocked.

After the checklist gates pass:

- add exposure cooldown;
- add mastery/error-aware weighting;
- keep exam blueprint constraints authoritative;
- cap personalization so weak-topic weighting cannot distort exam realism;
- persist selector snapshots and relaxation reasons;
- run shadow comparisons before serving personalized sets.

### P7 — calibrated appearance dashboard

Only after multiple complete exam corpora exist:

- define historical train/test windows;
- compare against frequency-only and random baselines;
- measure calibration and top-k precision;
- publish abstentions when evidence is insufficient;
- require operator-reviewed copy and visible evidence.

## Technical stack decision

### Keep

- PostgreSQL/Supabase as canonical data and relationship store.
- Existing relation tables for question/topic graph traversal.
- FastAPI services and scheduled jobs for deterministic pipelines.
- Existing review lifecycles, audit logs, RLS, and service-role RPC boundaries.
- Existing mock engine, planner, mastery engine, and shared SRS service.

### Add only when justified

- An active pgvector migration and ETL job for semantic candidate retrieval, after an explicit retrieval benchmark. A legacy embedding migration is not proof that production vector search is available.
- A provider-neutral LLM adapter for classification proposals. The persisted contract must not depend on Claude/OpenAI-specific response shapes.
- Queue-backed batch jobs with retries and idempotency for expensive classification.

### Do not add now

- Neo4j as a second source of truth.
- Pinecone/Weaviate before PostgreSQL retrieval quality is measured.
- LangGraph solely to label ordinary ETL stages as agents.
- unreviewed AI writes into verified/locked exam intelligence.
- hard-coded recurrence claims or unsupported exam-level percentages.

## Delivery order

1. **Close current runtime gates.** Complete scheduler, shadow, allowlist, migration, and canary validation already tracked for Mock Engine v2. *(In progress — see `career-copilot-checklist.md`.)*
2. ~~**Define frequency semantics.**~~ **DONE (PR #767, merged).** Primary-only semantics implemented in `coverage.py`; 7 regression tests; primary-only is the current default.
3. ~~**Activate `exam_topic_score_snapshots`.**~~ **DONE (PRs #767/#773/#810, all merged).** Deterministic idempotent writer, draft→reviewed→locked transition matrix, atomic review RPC (migration 204), operator workbench embedded in PYQ Workbench tab, locked-only reader wired into planner as 0–15 pt confidence-weighted additive signal. Operator/browser validation still pending before full sign-off.
4. **Add cognitive-demand classification.** Pending AI proposals + admin review. *(Metadata-only classification — reviewed per-question cognitive-demand records with no mock-selection or weighting output — is independent of Track C and may proceed once its contract is approved. However, no classification output may feed mock-selection weighting or personalization until Lane A clears the live mastery gate (`FF_MOCK_MASTERY_WRITES=live`). P2 contract must be defined before implementation.)*
5. **Unify revision recommendations.** Topic mastery due/relearn/practice contract using existing SRS where appropriate.
6. **Rank reviewed resources.** No AI-generated resource claims.
7. **Build CA provenance and linking.** Separate from policy updates.
8. **Enable mock personalization in shadow.** Only after live mastery gates pass.
9. **Evaluate appearance forecasting.** Ship only if it beats baselines and is calibrated.

## Historical acceptance criteria — P-slice-1 / P-slice-3 (reference only)

These criteria were written before implementation began. P-slice-1 (PR #767) and P-slice-3 (PR #810) are now MERGED. Annotations show what was met and what was deferred.

- ~~all reads are paper/question/tag trust-gated~~ — **MET** (conjunctive trust gates in `coverage.py` and all admin endpoints); ~~paginated~~ — **DEFERRED**: the admin snapshot list performs a full DB read/enrichment and slices in Python (`all_rows[offset: offset + limit]`); true DB-level pagination is a bounded scalability follow-up (no current open issue);
- ~~a question cannot inflate frequency through multiple non-primary tags~~ — **MET** (primary-only filter at DB query + loop, PR #767);
- ~~computation is deterministic and idempotent~~ — **MET** (SHA-256 input fingerprint; re-run with same corpus skips unchanged topics);
- ~~snapshots include model version, input fingerprint, evidence count, component breakdown, and confidence~~ — **MET**;
- ~~no draft/reviewed snapshot reaches user-facing APIs or the planner~~ — **MET** (`locked_score_snapshots()` returns only `status='locked'` rows);
- ~~operator can review, lock, reject, and inspect evidence~~ — **MET** (workbench UI + atomic RPC, PR #810/migration 204);
- ~~old locked snapshots remain auditable~~ — **MET** (insert-only; no UPDATE/DELETE on locked rows);
- ~~tests cover incomplete corpus, duplicate/multi-role tags, status reversal, zero evidence, pagination, and retry/idempotency~~ — **MET** (54 tests across `ScoreSnapshotPanel.test.jsx` and `test_score_snapshot_admin_api.py`; Python-side pagination tested);
- ~~no new top-level admin route is added~~ — **MET** (controls embedded in existing Exam Workspace / PYQ Workbench `?view=snapshots`);
- ~~the repo checklist is updated in the same PR when implementation status changes~~ — **MET**.

The next implementation milestone is P2 cognitive-demand classification; acceptance criteria will be defined in its own contract.

## Explicit non-goals

- Guaranteeing likely exam questions.
- Replacing official syllabus or source review with LLM output.
- Automatically publishing generated mock questions.
- Making current affairs an unbounded news feed.
- Optimizing for every exam family before one complete pilot corpus works end to end.
