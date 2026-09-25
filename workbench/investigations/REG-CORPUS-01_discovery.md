# REG-CORPUS-01 — authored regulatory question corpus: discovery (read-only)

Question: can the platform house an **authored** (non-PYQ) hard MCQ/numerical
corpus for the SEBI/PFRDA/IFSCA core subjects (commerce-accountancy, costing,
economics, finance, management, companies-act), with tax/GST as adjacent
microtopics?

Evidence is repository code at `origin/main` (`d7b4bd48`). No app code, migration
or DB was touched or queried; anything only answerable from the live database is
marked as such. All paths are repo-relative.

---

## HARD STOP — an authored-question pipeline already exists

Per the brief, this is reported and **no design follows**. The findings below
are recorded as evidence for whoever decides next; they are not a proposal.

`mock_question_bank` already accepts hand-authored MCQs through two live admin
paths and one reviewed-AI path:

| Path | What it does | Evidence |
|---|---|---|
| Admin CRUD + review state machine | `draft → in_review → verified → published` (+ `needs_changes`, `archived`, publisher force); inserts straight into `mock_question_bank` with `reviewer_status='draft'`, `created_by`; writes `source_kind`/`source_url` only if the caller sends them | `app/backend/app/admin/mock_questions.py:3-8`, `:184-309` (insert `:247`, provenance `:242-245`) |
| Router (live) | `POST /api/admin/mocks/questions`, submit/review/verify/approve/publish/archive/force, topic tags, sources | `app/backend/app/api/admin_mocks.py:31`, `:166-175`, `:238-362`, `:412`, `:428`; mounted `app/backend/server.py:106`, `:380` |
| Admin UI | `/admin/mocks/questions/new` → `QuestionEditor` (POSTs above); Content Studio library tab → `QuestionList` "New Question" | `app/frontend/src/routes/adminRoutes.jsx:133-134`; `app/frontend/src/pages/admin/mocks/QuestionEditor.jsx:210`; `app/frontend/src/pages/admin/content-studio/ContentStudio.jsx:27` |
| Bulk CSV/JSON import | `source_kind` defaults to `'authored'`; bank row inserted as `draft`; provenance written to `mock_question_sources` only (**not** onto the bank row's `source_kind`) | `app/backend/app/admin/mock_import.py:120-129`, `:448-468`, `:502-509`; endpoints `admin_mocks.py:534-556`; UI `ImportWizard.jsx:100,128`, Content Studio "bulk-import" tab `ContentStudio.jsx:29,42,119` |
| Current-affairs promotion (AI-drafted, human-reviewed) | `ca_promote_candidate` inserts `source_kind='current_event'`, `reviewer_status='verified'`, no `exam_id`, no `pyq_question_id` | `app/supabase/migrations/251_current_affairs_promotion_hardening.sql:214-225`; caller `app/backend/app/api/content_studio.py:1497` |
| Seeded non-PYQ rows | 20 hand-written IBPS questions (backfilled to `published`); e2e fixtures; SSC demo | `135_mock_engine_core.sql:216-402`, `136:282-300`; `app/supabase/seeds/e2e_fixtures.sql:65-74`; `seeds/reasoning_strategy_demo_ssc_cgl.sql:82` |

Not a question bank: `calc_gym_session_items` (`245:68-85`, per-session
generated arithmetic); `current_affairs_question_candidates` (`247:56`, staging
only). No `practice_questions` / `generated_questions` / `ai_questions` table.

---

## Prior work

`content-artefacts-spec.md` **does not exist** on any ref (`git log --all` for
`*content-artefact*` is empty). The nearest doc, `docs/status/HANDOFF-artefact-session.md`,
is about UPSC-optional study artefacts and has no "Part 6". Q4 is therefore
answered against the Part-6 field names given in the brief.

Both named branches are **already merged to main**:

- `claude/reg-subject-inventory-2026-09-22` → `workbench/reports/REG-SUBJECT-INVENTORY-2026-09-22.md` (`69daddea`).
- `claude/regulatory-corpus-decisions-dpq965` → five merges (#1073, #1076, #1077, #1081, #1083): `docs/status/Regulatory-corpus-decision-provenance-2026-09-06.md`, `workbench/rbi-ga-classification.csv`, migration `273_general_knowledge_microtopics.sql` + `workbench/rbi-gk-microtopic-map.csv`, and EWP grammar-topic repair (`274`). Only the first three touch this topic.

What they already settle (not re-derived here):

| Settled fact | Source |
|---|---|
| Regulatory catalogue: 598 microtopics / 12 domain subjects, exam-tagged sebi/pfrda/ifsca, in `workbench/catalogs/topic_catalog_regulatory.json` | inventory §2.2 |
| **No numbered migration creates any of the six domain subjects or their microtopics** — live-only, seeded via untracked root scratch SQL | inventory §5 row 4 (re-confirmed in Q7) |
| **Taxation has no subject**; GST appears only as microtopic leaves inside economics/finance | inventory §3, §4 #3 |
| Regulatory domain subjects resolve to `_GENERIC_POLICY` (topic-PYQ practice only) | inventory §2.5, `subject_runtime_policy.py:74-98, 401-417` |
| No formula sheets, Ind AS cards, tax-rate tables, act/section cards, numerical generators, concept notes | inventory §4 #1-#7 |
| Live DB: 2,484 regulatory `mock_question_bank` rows, all `published`, **0 with explanation, 0 with common_trap** | inventory §7 / 6.3 |
| Live DB: `content_cards`=2, `pyq_question_explanations`=0 | inventory §7 / 6.2 |
| No difficulty rubric for regulatory papers | inventory §6 |
| Review decisions for SEBI/IFSCA/PFRDA live in the needs-correction backlog doc; worksheet CSV is the audit trail; the PYQ review PATCH writes no audit row | decision-provenance §1-§2, §5 |

---

## 1. Can `mock_question_bank` hold a non-PYQ authored question?

**Yes — schema and write paths already allow it** (see Hard stop).

- PYQ link columns `pyq_question_id`, `pyq_paper_id`, `pyq_year` are **nullable**; the uniqueness index is partial `WHERE pyq_question_id IS NOT NULL` — `app/supabase/migrations/183_pyq_mock_projection_bridge.sql:40-55` (re-asserted `184:90-92`).
- Source marker: `source_kind` — nullable, check `pyq | official_syllabus | standard_source | current_event | authored | archive | sme` — `161_*.sql:40-45`. Also free-text `source_type` (`135:73`); PYQ projection stamps both `'pyq'` (`183:629-630`, latest body `307:623`).
- Side provenance: `mock_question_sources.source_kind` incl. `'authored'`, `source_trust`, `evidence_text` (`136:201-211`); `source_document_id` → `document_assets` (`186:42-44`).
- Other relevant NOT NULLs: `question_text`, `question_type` (default `mcq`), `language` (default `en`), `reviewer_status` (default `draft`), `question_fingerprint` table-wide UNIQUE, trigger-filled (`136:154-184`).

**Code paths that assume PYQ origin** (authored rows silently excluded):

| Path | Assumption | Evidence |
|---|---|---|
| Topic/paper practice pool | `pyq_question_id IS NOT NULL` + active projection | `app/backend/app/study_os/pyq_practice.py:265`, `:353`, `:431`, `:104-124` |
| …its callers | planner PYQ launch, mock engine, subject practice, paper practice-ready counts | `app/backend/app/api/pyq_practice_launch.py:74`, `api/mock_engine.py:97`, `api/subject_practice.py:243`, `api/exam_intelligence.py:790` |
| Structured review explanation | looked up by snapshot `pyq_question_id` in `pyq_question_explanations`; authored rows get only the flat `explanation` column | `app/backend/app/study_os/mock_engine.py:1561-1574`, `pyq_explanations.py:25-29` |
| Option lineage | `pyq_option_id` backfill joins on `pyq_question_id is not null` | `migrations/307:119-122`, `:150-151` |
| Projection / invalidation helpers | operate only `WHERE pyq_question_id = …` | `183:859-862`, `:895-898` |

Source-agnostic (let authored rows through): fixed-template load, blueprint pool, readiness depth, generated attempts — projection guard applied only when `pyq_question_id` is set (`mock_engine.py:115-137, 429, 591`; `mock_blueprint_selection.py:236-266`; `exam_intelligence/diagnostics.py:431-460`; `generated_mock_attempt.py:178`). Snapshot `source_type` defaults to `"authored"` (`mock_engine.py:294`). Mastery weights pyq 1.2 / authored 1.0 / current_event 0.8 (`mastery_engine/mastery_delta.py:26-27`).

Silent exclusions even on the source-agnostic paths:
- Blueprint/diagnostics filter `.eq("exam_id", …)` (`mock_blueprint_selection.py:230`, `diagnostics.py:425`); `create_question` treats `exam_id` as optional (`mock_questions.py:232`).
- Base pool drops `is_current` / `is_current_based` (`mock_blueprint_selection.py:264`).
- Source-mix groups by `source_kind`/`source_type` (`:368`), policy default `pyq` (`183:111`); bulk-imported rows have `source_kind` NULL on the bank row.

## 2. Stimuli (shared passage/table stems) and table rendering

- Shared stimuli are PYQ-side: `pyq_stimuli` (types passage/caselet/table/chart/image/diagram/other) + M:N `pyq_question_stimuli` — `223_pyq_section_stimulus_schema.sql:126-144`, `:213-226`; media fields `233:27-85`.
- Mock side has **no stimulus FK** on `mock_question_bank` (`135:58-78`). Stimuli are snapshotted into `mock_question_stimuli` (`229_pyq_projection_stimulus_fidelity.sql:47-59`) keyed by `mock_question_id` (cascading FK) with `pyq_stimulus_id` as **lineage only**. Structurally an authored row could own `mock_question_stimuli` rows, but the only writer is the PYQ projection (`229:586-596`, `307:701-711`); the admin CRUD/import paths do not write it. No sharing: each question gets its own copies.
- `mock_question_stimuli` has no `asset_url`/`alt_text`, but `QuestionStimuli.jsx:45` needs `asset_url` for media → media stimuli not reachable on the mock side (not traced further).
- NABARD repairs inlined passages/DI data into `question_text` rather than using stimulus tables (`278:9-10`, `280:43,100`, `282:45`).
- **Renderer does not render tables.** Stem → `QuestionStem` → `MathRenderer` → (`$…$`) lazy `_katexRuntime.jsx`, which only returns `MarkdownSafe` (KaTeX is a stub) → `MarkdownSafe` HTML-escapes `& < >` and turns `\n` into `<br />` — `app/frontend/src/pages/study/mocks/components/questions/shared/MarkdownSafe.jsx:3-13`. `app/frontend/package.json` has no markdown/remark/katex/dompurify dependency. Markdown or HTML tables and LaTeX show as literal text. Same for text stimuli (`QuestionStimuli.jsx:64-67`). Attempt UI: `pages/study/mocks/MockAttemptShell.jsx:653-655`.

## 3. Difficulty enum end-to-end — `very_hard` is **not** live

| Layer | Allowed | Evidence |
|---|---|---|
| DB `mock_question_bank.difficulty` | `easy, medium, hard` | `135:67`, `136:112-120` |
| DB `pyq_questions.observed_difficulty` | bare text, no CHECK | `032:54` |
| Projection | anything else → `'medium'` | `183:623`, `239:465`, `307:488, 631-649`; Python mirror `app/backend/app/admin/pyq_mock_projection.py:277-278` |
| API writes | easy/medium/hard (`admin_exam_intel_cms.py:2001, 2067, 2148`; `pyq_bulk_import.py:197`; `mock_import.py:122`); **`admin_mocks.py:80,107` untyped `str`** — only the DB CHECK stops bad values |
| API reads | filter `easy|medium|hard|unknown` (`api/exam_intelligence.py:310`); alias `very_hard → hard` (`exam_intelligence/pyq_papers.py:79-84`) — contradicts projection's `→ medium`, admitted at `:66-69` |
| Frontend | easy/medium/hard in `QuestionEditor.jsx:397-400`, `MockResult.jsx:14`, `AccuracyHeatmap.jsx:4`; `+unknown` in `PyqExplorerSection.jsx:10-16`; `very_hard` shown as "legacy — not accepted on save" `PyqPaperWorkspace.jsx:830-838` |

## 4. Provenance / review fields vs the brief's Part-6 names

No table for artefacts exists (no `content_artefacts`, `artefacts`, `study_artefacts`, `content_items`, `content_sources`, `source_refs`). No column named `provenance`, `review_status`, `source_refs`, `authored_by`, `ai_generated` or `generation_method` exists in any migration.

| Part-6 concept | Closest existing on the authored path | Evidence |
|---|---|---|
| provenance | `mock_question_bank.source_kind` (incl. `authored`, `sme`, `standard_source`), `source_type`, `source_url`, `created_by` | `161:40-45`, `135:73`, `159:44`, `136:136-139` |
| review_status | `mock_question_bank.reviewer_status` ∈ draft, reviewed, in_review, needs_changes, verified, published, live, archived; learner RLS reads verified/live/published; transitions logged in `mock_question_review_log` | `161:20-36`, `161:52-54`, `136:218+` |
| source_refs | 1:N `mock_question_sources` (`source_kind`, `source_trust` verified/provisional/unverified, `source_url`, `evidence_text`, `source_document_id` → `document_assets`) | `136:201-211`, `186:42-44` |
| explanation provenance/licence | `pyq_question_explanations.explanation_source_type` (incl. `platform_original`), `license_status`, `source_document_id` — **PYQ-keyed only** | `230:31-64` |

`document_assets.source_kind` already has `sme_authored` (`153:16-29`, `154:13-14`). The `257` trust gate covers syllabus/eligibility review only (`257:145`, `:362`, checks `:215-256`), not questions. `content_cards` has review columns but no source columns (`291:108-114`).

## 5. Practice pools filtering on `topics.metadata.exams`

**None at runtime.** No backend, frontend or SQL-function read of `topics.metadata.exams`. Tooling only:
- `scripts/propose_pyq_topic_tags.py:390-395`, `:574-580` (tag-candidate filter, SEBI/PFRDA/IFSCA).
- `scripts/pyq_question_review.py:1055-1080` (catalogue filter, `--any-body` bypass).
- `scripts/corpus_readiness_report.py:234-238` deliberately does not use it.

Migrations assert the key is *absent* on newer taxonomies (`273:27`, `275:36`, `305:30`, `306:18`, `308:105`; regression tests `app/supabase/tests/regression_305:198`, `_306:239`, `_308:263`). Whether live regulatory topics carry `metadata.exams` is **DB-only**.

## 6. Numeric-answer type; explanation fields

- `pyq_questions.question_type` ∈ mcq, numerical, descriptive, caselet, matching, other (`032:51`).
- Mock enum `mock_question_type` ∈ mcq, integer, msq (`135:29`) + descriptive, essay, precis, letter (`176:19-22`).
- `mock_question_bank.numeric_answer` jsonb `{value, tolerance}` + response column (`250_integer_numeric_answer.sql:13-20`); scored by tolerance (`mock_engine.py:942-969`); numeric input in the attempt UI (`MockAttemptShell.jsx:273-287, 657`; `QuestionRenderer.jsx:15`).
- **But only fixed-template mocks reach `integer`:** projection rejects non-MCQ (`307:297-302`) and generated selection is MCQ-only (`diagnostics.py:49` used by `mock_blueprint_selection.py:232`). **`msq` is not scored** — it falls to "unattempted" (`mock_engine.py:979-994`).
- Explanations: flat `mock_question_bank.explanation` (`135:72`), shown in review only (`MCQSingle.jsx:58`, `MCQMulti.jsx:9`). `common_trap` column exists (`159:45`) with **no learner renderer**. Structured `pyq_question_explanations` (steps, option rationales, `formula_used`, traps) render in review via `PyqExplanationPanel.jsx` (`:52`, `:84-158`), and only for PYQ-linked rows.

## 7. Tax / GST / Ind AS / Schedule topics under the six subjects

**No migration or seed creates these subjects or microtopics**, which confirms the inventory (§5 row 4). The only migration hit is `244:120`, where `finance` is an IRDAI stream key. They exist only in `workbench/catalogs/topic_catalog_regulatory.json` (598 rows, has `exams`) / `topic_catalog_reg_full.json` (776 rows). All are `level=microtopic`; neither file has a parent field. Index = `reg_full[i] / regulatory[j]`.

| Subject | Microtopic | idx | exams |
|---|---|---|---|
| commerce-accountancy | Ind AS 7 – statement of cash flows | 142 / 176 | ifsca, pfrda, sebi |
| commerce-accountancy | Ind AS 16 – PPE | 143 / 173 | ifsca, pfrda, sebi |
| commerce-accountancy | Ind AS 21 – non-monetary items | 144 / 174 | ifsca, pfrda, sebi |
| commerce-accountancy | Ind AS 36 – impairment | 145 / 175 | ifsca, pfrda, sebi |
| commerce-accountancy | Ind AS 105 – held for sale | 146 / 171 | ifsca, pfrda, sebi |
| commerce-accountancy | Ind AS 113 – fair value | 147 / 172 | ifsca, pfrda, sebi |
| commerce-accountancy | AS vs Ind AS convergence | 148 / 146 | ifsca, pfrda, sebi |
| commerce-accountancy | Schedule III – Balance Sheet heads | 177 / 194 | ifsca, pfrda, sebi |
| commerce-accountancy | AS 22 – deferred tax | 183 / 143 | ifsca, pfrda, sebi |
| economics | Tax incidence and elasticity | 269 / 504 | ifsca, pfrda, sebi |
| economics | Non-tax sources of revenue | 316 / 487 | ifsca, pfrda, sebi |
| finance | Direct vs indirect taxes | 390 / 370 | ifsca, pfrda, sebi |
| finance | Non-tax sources of revenue | 391 / 406 | ifsca, pfrda, sebi |
| finance | GST – supply, ITC, zero-rated, exports | 392 / 385 | ifsca, pfrda, sebi |
| finance | GST returns and TCS by e-commerce operators | 393 / 384 | ifsca, pfrda, sebi |
| finance | Income-tax – assessment and rectification | 394 / 389 | ifsca, pfrda, sebi |
| finance | Income-tax – penalties and PAN | 395 / 390 | ifsca, pfrda, sebi |
| finance | DTAA and tax administration bodies | 399 / 363 | ifsca, pfrda, sebi |
| companies-act | Schedules of the Companies Act 2013 | 519 / 294 | pfrda, sebi |
| companies-act | Format of financial statements governed by Schedule III | 523 / 259 | pfrda, sebi |
| *(false positive)* finance | Banking Regulation Act 1949 … scheduled banks | 409 / 345 | — |
| *(false positive)* companies-act | Deposit in a scheduled bank within five days | 487 / 253 | — |

There are no costing or management hits, no `TDS` hits and no literal "accounting standard" hits.

---

## Gaps

1. The authored write paths set provenance inconsistently. CRUD writes `source_kind` only when the caller sends it (`mock_questions.py:242-245`). Bulk import never sets it on the bank row (`mock_import.py:448-468`). So an authored row can't be reliably told apart from a PYQ row on the row itself.
2. Topic/paper practice and the planner's PYQ launch are PYQ-only by filter (`pyq_practice.py:265`). An authored row can reach learners only through mock templates or blueprints.
3. Blueprint and diagnostic pools require `exam_id` (`mock_blueprint_selection.py:230`), but the authoring paths leave it optional. A row without it is unreachable, and no error is raised.
4. The stem and stimulus renderer is escape-plus-`<br>` only. It has no table, markdown or LaTeX rendering, and the KaTeX path is a stub (`MarkdownSafe.jsx:3-13`). Hard numericals and costing or accounts tables would show as raw text.
5. Only the PYQ projection writes shared stimuli. There is no authoring path for a passage or table stem shared across authored questions, and no stimulus sharing on the mock side.
6. The difficulty ceiling is `hard`. `very_hard` is rejected on write, and the two read paths map it differently: `→hard` in `pyq_papers.py:79-84`, `→medium` in the projection.
7. `integer` numeric answers are scored but unreachable from generated or practice pools (MCQ-only selection, `diagnostics.py:49`). `msq` is never scored (`mock_engine.py:979-994`).
8. Structured explanations (steps, option rationales, `formula_used`) are keyed to PYQs (`pyq_question_explanations`). Authored rows get one flat `explanation` field, and `common_trap` has no learner renderer.
9. `metadata.exams` is not used by any runtime pool, so no learner-facing path scopes content by sebi/pfrda/ifsca.
10. The six subjects and their tax/GST/Ind AS microtopics are unmigrated. They are catalogue-JSON only (confirmed; already raised by the inventory).
11. Taxation has no subject. The 7 finance tax/GST microtopics, the 2 economics tax microtopics and AS 22 are spread across three subjects.
12. `admin_mocks.py:80,107` accepts `difficulty` as an untyped `str`, so invalid values are caught only by the DB CHECK.

## Open questions for operator

1. **Hard stop.** Should REG-CORPUS reuse the existing admin CRUD, bulk import and review pipeline (`admin/mock_questions.py`, `admin/mock_import.py`), or is a separate authored lane intended? Nothing is designed until this is decided.
2. DB: how many live `mock_question_bank` rows have `source_kind='authored'` or NULL, or `pyq_question_id IS NULL`? And do any of them carry regulatory `exam_id`s?
3. DB: do the live regulatory topics carry `metadata.exams`, and do the topic ids match `topic_catalog_regulatory.json`?
4. DB: do any rows hold `observed_difficulty='very_hard'`, and how many per exam?
5. Should authored hard questions reach learners through topic practice (which today requires lifting the PYQ-only filter) or only through mocks?
6. Where should the tax, GST and Ind AS content sit: stay as microtopics under finance, economics and commerce-accountancy, or get their own taxation subject? The inventory flags the missing subject but doesn't decide it.
7. Is `content-artefacts-spec.md` in some other location? It is not in this repository, so the Part-6 comparison in §4 uses the field names from the brief only.
