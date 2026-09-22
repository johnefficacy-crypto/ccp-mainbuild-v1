# Regulatory Exam Subject Preparation — Read-Only Inventory

**Generated:** 2026-09-22 · read-only, nothing committed, no writes to the repo other than this file.

---

## 1. SHA + search scope

| Item | Value |
|---|---|
| Working branch HEAD | `ad23740693e4eff4201c0f695a99cc85796b306a` |
| `main` HEAD | `3be01841a205b5f66ac72e8f4c5fadc2e5026e6c` |
| `git status` | clean (no modified/untracked files at preflight) |
| Graphify graph built from | `8dca18e4` — **STALE** relative to both heads (`graphify-out/GRAPH_REPORT.md:13`) |
| Writes performed | none (this report only; not committed) |

**Priming order honoured:** `AGENTS.md` → `graphify-out/GRAPH_REPORT.md` → `graphify-out/wiki/index.md` before any source file.

**Search terms used:** `sebi`, `rbi`, `rbi grade`, `rbigradeb`, `nabard`, `pfrda`, `ifsca`, `irdai`, `regulatory`, `financial-regulatory`, `accounting`, `commerce-accountancy`, `costing`, `taxation`, `income tax`, `gst`, `financial management`, `finance`, `management`, `economics`, `ESI`, `economic-social-issues`, `companies act`, `companies-act`, `sebi act`, `rbi act`, `fema`, `pmla`, `ibc`, `insolvency`, `banking regulation act`, `insurance`, `pension`, `pension-sector`, `statute`, `circular`, `case law`, `ICAI`, `Ind AS`, `accounting standard`, `formula`, `flashcard`, `SRS`, `spaced`, `concept note`, `content_cards`, `_GROUP_FAMILY`, `_SLUG_FAMILY`, `subject_group`, `exam_streams`, `descriptive`.

**Layers searched, depth-first:** A docs (`docs/status/`, `docs/architecture/`, `docs/audits/`, `docs/reference/`, `docs/runbooks/`, `memory/`, `workbench/catalogs/`) · B catalogues + syllabus + backend subject-family maps · C backend `app/backend/app/` · D `app/supabase/migrations/` (300 files) · E `app/frontend/src/` routes/pages/features · F `scripts/`, `tools/`, `workbench/`.

**Note on `workbench/reports/`:** the directory did not exist. It was created to hold this file (the task named it as the output path). No other write occurred.

---

## 2. Feature inventory

Status key — **LIVE** = code merged *and* reachable from a route/job · **DATA-ONLY** = corpus/catalogue/endpoint exists with no aspirant surface · **DOC-ONLY** = specced, no code · **ABSENT** = searched, nothing found.

### 2.1 Identity, streams, eligibility

| Feature | Exams | Subjects | Status | Evidence |
|---|---|---|---|---|
| Umbrella exam family `financial-regulatory` + org dimension + portfolio lane (core/light/index_only) | RBI, SEBI, NABARD A+B, IRDAI, PFRDA, IFSCA, SIDBI, NHB, EXIM, NaBFID, NPS Trust, EPFO, ECGC, IBBI | n/a (identity) | LIVE (schema) / draft rows `is_active=false` | `app/supabase/migrations/244_financial_regulatory_family_identity_seed.sql:33-98` |
| Canonical stream vocabulary (27 stream rows, all `provenance:draft, verified:false`) | RBI 3, SEBI 7, IRDAI 6, PFRDA 7, IFSCA 1 (blocked on PDF), NABARD A+B 1 each, SIDBI 1 | n/a | DATA-ONLY (draft, unverified) | `244_...sql:105-138` |
| `exam_streams` / `exam_cycle_streams` / stream-scoped phases + sections + coverage, with fail-closed parent-consistency triggers | family-wide | n/a | LIVE (schema) | `app/supabase/migrations/242_exam_streams_schema.sql:1-45+` |
| Baseline-vs-cycle eligibility split; `exam_cycle_stream_eligibility`; rule types `discipline` / `min_percentage` / `certification` / `qualification_combination` / `stream_availability` / `experience_min_years` | family-wide | n/a | LIVE (schema) | `app/supabase/migrations/248_exam_stream_eligibility.sql:1-40` |
| Stream-aware eligibility activation | family-wide | n/a | LIVE | `app/supabase/migrations/254_exam_eligibility_stream_aware_activation.sql` |
| Evaluator drops stream-scoped rows before exam-wide evaluation (leak guard) | family-wide | n/a | LIVE | `app/backend/app/exam_eligibility/evaluator.py` (contract stated at `248_...sql:26-30`) |
| Compass — stream breakdown + baseline/current-cycle provenance bands | SEBI, PFRDA (and any family exam) | n/a | LIVE (route `/app/eligibility/exams`) | `app/frontend/src/features/exam-eligibility/ExamStreamBreakdown.jsx`, `EligibleExamsCard.jsx`; route `app/frontend/src/routes/appRoutes.jsx:77-79` |
| Recruitment classifier Tier-A regulator/dev-finance aliases (boundary-aware acronyms) | SEBI, IRDAI, PFRDA, IFSCA, TRAI, NABARD, SIDBI, NHB, EXIM, NaBFID, RBI | n/a | LIVE | `app/backend/app/scraping/recruitment_classifier.py:58-90` |
| Admin eligibility authoring warns that PFRDA/IRDAI identities land inactive | PFRDA, IRDAI | n/a | LIVE | `app/backend/app/api/admin_exam_eligibility.py:302` |

### 2.2 Subject catalogue / taxonomy

| Feature | Exams | Subjects | Status | Evidence |
|---|---|---|---|---|
| Regulatory microtopic catalogue — 598 microtopics across 12 domain subjects, exam-tagged | SEBI, PFRDA, IFSCA | finance, companies-act, management, economics, commerce-accountancy, costing, pension-sector, banking, insurance, capital-market, financial-awareness, ifsca-gift-city | DATA-ONLY | `workbench/catalogs/topic_catalog_regulatory.json` (598 rows) |
| Full regulatory catalogue incl. shared QRE | SEBI, PFRDA, IFSCA, RBI | above + english-language 66, general-intelligence-reasoning 57, quantitative-aptitude 55 | DATA-ONLY | `workbench/catalogs/topic_catalog_reg_full.json` (776 rows) |
| RBI catalogue | RBI Grade B | finance 100, management 78, economics 73 + QRE (rbi_full, 429 rows); banking 30, insurance 26, capital-market 18, financial-awareness 17 + QRE (rbi, 338 rows) | DATA-ONLY | `workbench/catalogs/topic_catalog_rbi_full.json`, `topic_catalog_rbi.json` |
| NABARD catalogue | NABARD Grade A | economic-social-issues 134, agriculture-rural-development 109, computer-knowledge 32, decision-making 16 + QRE | DATA-ONLY | `workbench/catalogs/topic_catalog_nabard_277.json` (473 rows) |
| NABARD microtopic **migration** (the only regulatory-family taxonomy in the numbered migration set) | NABARD | computer-knowledge 32, decision-making 16, economic-social-issues 134, agriculture-rural-development 109 | LIVE (migration) | `app/supabase/migrations/275_nabard_microtopics.sql:1-25` |
| Shared QRE microtopic gap fills (catalogue serves RBI/SEBI/PFRDA/IFSCA/NABARD) | all five | english-language, reasoning, quant | LIVE (migration) | `app/supabase/migrations/277_qre_microtopic_gaps.sql:1-20` |
| `general-knowledge` subject — body-agnostic, 7 sections / 55 microtopics, built from the RBI GA corpus | RBI Grade B | general-knowledge | LIVE (migration, 6 sections) + **provenance gap** for the 7th section | `app/supabase/migrations/273_general_knowledge_microtopics.sql`; gap documented at `docs/architecture/subject-practice-framework.md` §1.1.1 ("Open provenance gap", `app/add_gk_ir.sql` deleted in `4a62535`) |
| RBI GA durable/perishable classification (112 durable-finance / 90 durable-non-finance / 118 perishable) | RBI Grade B | banking 71, economics 24, capital-market 15, financial-awareness 1, pension-sector 1, general-knowledge 90 | DATA-ONLY (classified, not tagged) | `workbench/rbi-ga-classification.csv`; carve-out at `docs/architecture/subject-practice-framework.md` §1.1.1 |

### 2.3 PYQ corpus and intelligence

| Feature | Exams | Subjects | Status | Evidence |
|---|---|---|---|---|
| Regulatory PYQ corpus — keyed, verified, tagged, projected | SEBI 440q/48 papers, IFSCA 444/43, PFRDA 201/47 | all 12 domain subjects + QRE | DATA-ONLY → surfaced via generic PYQ Explorer (LIVE) | `docs/status/HANDOFF-regulatory-corpus-2026-09-05.md` § State; exports `review_out_{sebi,ifsca,pfrda}/questions_export.json` |
| RBI Grade B corpus — largest on the platform, **0 verified / 0 tagged / 0 projected** | RBI Grade B, 999q / 11 papers / 2022-2026 | — | DATA-ONLY (unreviewed) | `docs/status/HANDOFF-regulatory-corpus-2026-09-05.md` § State |
| NABARD corpus — 1055 MCQ loaded (GA 100 + 18 Phase-3 descriptive excluded) | NABARD Grade A, 41 papers | ESI, ARD, CK, DM, QRE | DATA-ONLY | `workbench/nabard_load.py:1-14`; `review_out_nabard/questions_export.json` (1055 rows) |
| Descriptive PYQ rows in the regulatory corpus | IFSCA 9, PFRDA 9 | — | DATA-ONLY (typed `pending`, out of MCQ scope) | `review_out_ifsca/questions_export.json`, `review_out_pfrda/questions_export.json`; count reconciled at `docs/status/Regulatory-PYQ-needs-correction-backlog-2026-08-31.md` (18 pending) |
| PYQ bulk-import v2 tolerates NULL difficulty because the regulatory corpus carries none | SEBI, IFSCA, PFRDA | all | LIVE | `app/backend/app/exam_intelligence/pyq_bulk_import.py:190-197`, `:283-292` |
| PYQ Explorer (year/phase/subject/topic/difficulty filters, "Practice this paper") | exam-agnostic; consumed by all four | all | LIVE | `app/frontend/src/features/exams/PyqExplorerSection.jsx:149-346`; route `appRoutes.jsx:93-94` |
| Reachability trend — explicitly **not** subject-pinned for NABARD/SEBI/IFSCA/PFRDA (pinning is UPSC-only) | all four | all | LIVE (exam-agnostic), regulatory explicitly excluded from pinning | `app/backend/app/api/exam_intelligence.py:918-934`; FE note `app/frontend/src/features/exams/ReachabilityTrendCard.jsx:304` |
| Subject/microtopic composition across a paper series | exam-agnostic | all | LIVE | `app/backend/app/exam_intelligence/subject_composition.py:1-20` |
| PYQ → `mock_question_bank` projection bridge (verified-only, hash-gated, `microtopic_id` carried) | exam-agnostic | all | LIVE | `app/supabase/migrations/183_pyq_mock_projection_bridge.sql`, `270_pyq_projection_microtopic_fidelity.sql` |
| Needs-correction backlog with cause taxonomy | SEBI/PFRDA/IFSCA, 1085 q / 103 papers | all | DOC-ONLY (tracked, deferred) | `docs/status/Regulatory-PYQ-needs-correction-backlog-2026-08-31.md` |
| Decision-provenance rule (worksheet is the audit trail; metadata `review_cause` recording rule for RBI) | SEBI/IFSCA/PFRDA/RBI | all | DOC-ONLY (procedure) | `docs/status/Regulatory-corpus-decision-provenance-2026-09-06.md` §5 |

### 2.4 Corpus repair / QA migrations (regulatory-specific)

| Migration | Exam | What | Status |
|---|---|---|---|
| `276_nabard_answer_keys.sql` | NABARD | answer-key repair | LIVE |
| `278_nabard_qa_di_stem_repair.sql` | NABARD | QA/DI stem repair | LIVE |
| `279_nabard_dm_2023_q7_reflow_repair.sql` | NABARD | single-question reflow | LIVE |
| `280_nabard_english_passages_and_footer_bleed.sql` | NABARD | passage + footer-bleed repair | LIVE |
| `282_nabard_reasoning_setups.sql` | NABARD | reasoning setup text | LIVE |
| `286_nabard_option_continuations.sql` | NABARD | option continuation repair | LIVE |
| `281_rbi_orphaned_context_pull.sql` | RBI | orphaned context recovery | LIVE |
| `283_rbi_2022_context_recovery.sql` | RBI | 2022 context recovery | LIVE |
| `284_rbi_over_flag_reversal.sql` | RBI | over-flag reversal | LIVE |
| `285_rbi_2026_truncated_directions.sql` | RBI | truncated directions repair | LIVE |

### 2.5 Study OS runtime

| Feature | Exams | Subjects | Status | Evidence |
|---|---|---|---|---|
| Shared-core overlap substrate — partition shared vs per-exam delta, fail-closed global-only mastery reuse, 70/20/10 allocation | any ≥2 family exams | all common locked topics | **DATA-ONLY** — endpoint exists, **no frontend consumer** | `app/backend/app/study_os/shared_core.py:1-28, 230-292`; `app/backend/app/api/study_os.py:600-613`; grep for `regulatory-overlap` in `app/frontend/src` returns **zero** hits |
| Subject Runtime Policy registry | — | regulatory domain subjects resolve to **no family** → `_GENERIC_POLICY` | LIVE but **generic only** (`english_writing` + `topic_pyq`) | `app/backend/app/study_os/subject_runtime_policy.py:74-98` (`_GROUP_FAMILY` / `_SLUG_FAMILY` contain **no** regulatory slug), `:401-417` (`_GENERIC_POLICY`) |
| Shared-QRE runtimes reachable for regulatory exams (Calculation Gym, timed practice, English writing) | all four | quantitative-aptitude, general-intelligence-reasoning, english-language | LIVE | `subject_runtime_policy.py:358-390`; routes `appRoutes.jsx:104,115-117` |
| Planner PYQ launch stamp for regulatory domain topics (via generic policy) | all four | all projected domain subjects | LIVE (exam-agnostic) | `subject_runtime_policy.py:288-303`, `app/backend/app/study_os/pyq_practice_launch.py:26-34` |
| Mastery on regulatory domain topics (`mastery_enabled=True` under generic policy) | all four | all | LIVE (exam-agnostic; no regulatory-specific tier) | `subject_runtime_policy.py:401-408` |
| Descriptive answer-writing practice — **self-scored**, rubric 0..2 per criterion, no AI evaluation | exam-agnostic; corpus is ~12k UPSC Mains optionals | any `question_type='descriptive'` PYQ | LIVE (route `/app/study/answer-writing`) — usable for the 18 regulatory descriptive rows only once they are verified | `app/supabase/migrations/293_descriptive_attempts.sql:1-40`; `app/backend/app/api/descriptive_practice.py`; route `appRoutes.jsx:134` |
| English Writing Practice (EWP) evaluator — default-deny applicability by phase > exam > family > global | exam-agnostic | english-language | LIVE, **no regulatory target seeded** | `app/backend/app/study_os/writing_practice/applicability.py:1-40`; no `insert into ... writing_prompt_targets` or `exam_descriptive_requirements` in any migration |
| Notes / Flashcards / Revision (SRS) — **learner-authored**, exam- and subject-agnostic | all | all | LIVE, but no platform-authored regulatory content | `app/frontend/src/pages/Notes.jsx`, `pages/study/Flashcards.jsx`, `pages/study/Revision.jsx`; APIs `app/backend/app/api/{notes,flashcards,revision}.py` |
| Content Cards (merged quant-heuristic + reasoning-strategy authority, `formula_latex` column) | all | **quant + reasoning only** — no regulatory content type | LIVE for quant/reasoning; ABSENT for regulatory subjects | `app/supabase/migrations/291_content_cards_generalisation.sql:92-110`; allowed subtypes `app/backend/app/api/content_studio.py:1022-1024` |
| Calculation Gym — deterministic seeded drills | exam-agnostic | quantitative-aptitude only | LIVE; arithmetic-fluency skills only | `app/backend/app/study_os/calc_gym.py:29-101` (`tables, squares, cubes, square_roots, cube_roots, fraction_percent, ratio_simplify, approximation, multiplication_patterns`) |
| Predictability axis (recurrence-based difficulty for descriptive papers) | exam-agnostic; motivated by and evidenced on UPSC Mains | all | LIVE (schema), no regulatory evidence in repo | `app/supabase/migrations/288_predictability_axis.sql:1-16` |
| Elective vs compulsory section marking (stops non-target subjects polluting the planner) | exam-agnostic | all | LIVE | `app/supabase/migrations/287_exam_electives.sql:1-14` |

### 2.6 Current affairs (regulator sources)

| Feature | Exams | Subjects | Status | Evidence |
|---|---|---|---|---|
| RBI + SEBI RSS adapters with per-publisher document typing | GA, exam-agnostic | general-awareness | LIVE | `app/backend/app/current_affairs/sources.py:52-57` |
| SEBI title deny-list (10 patterns, incl. the `("appeal no.","filed by")` pair) + URL-path allow-list (5 editorial/regulatory sections) | GA | general-awareness | LIVE | `app/backend/app/current_affairs/sources.py:72-108` |
| SEBI chrome-only body detection (290–600 chars) | GA | general-awareness | LIVE | `app/backend/app/current_affairs/ingestion.py:66` |
| SEBI path-allowlist backfill (retire 14 enforcement-order + 1 chrome-only doc) | GA | general-awareness | LIVE | `app/supabase/migrations/296_ca_sebi_path_allowlist_backfill.sql:1-22` |
| Item-level RSS ingestion, language-follow, wave-1 sources, PIB Hindi backfill | GA | general-awareness | LIVE | `294_ca_rss_item_level_ingestion.sql`, `299_ca_rss03_language_follow_and_wave1_sources.sql`, `300_ca_pib_hindi_backfill.sql` |
| **Regulatory-domain** current-affairs feed (circulars/regulations/consultation papers tagged regulator/cycle/stream/plan-impact) | family-wide | domain | **DOC-ONLY** | `docs/architecture/financial-regulatory-development-family.md` §8 item 4; checklist row "Aspirant surfaces … feed/tracker/interview PLANNED (R2/R4)" `docs/status/career-copilot-checklist.md:561` |

### 2.7 Scripts and tooling

| Script | Exams | Purpose | Status | Evidence |
|---|---|---|---|---|
| `scripts/propose_pyq_topic_tags.py` | SEBI, PFRDA, IFSCA | model-proposed microtopic tags with a conjunctive candidate filter (`level='microtopic'` ∧ resolved subject ∧ `metadata.exams` contains the body) + alias map ("Economy"→`economics`, "Company Act"→`companies-act`) | LIVE | `scripts/propose_pyq_topic_tags.py:1-16` |
| `scripts/pyq_question_review.py` | any phase/paper (used for the regulatory pass) | export → sweep → apply; worksheet CSV is the audit trail | LIVE | `scripts/pyq_question_review.py:1-16`; audit-trail contract `docs/status/Regulatory-corpus-decision-provenance-2026-09-06.md` §1 |
| `scripts/repair_pyq_mojibake.py` | regulatory corpora (scan artefacts for RBI/SEBI/IFSCA/PFRDA at repo root) | reverse cp1252-as-UTF-8 mojibake | LIVE | `scripts/repair_pyq_mojibake.py:1-15`; artefacts `mojibake_scan_{sebi,ifsca,pfrda,rbi,rbigradeb}.json`, `repair_audit_rbigradeb.jsonl` |
| `workbench/nabard_extract.py` | NABARD | heading-driven closed segmentation of the NABARD compendium PDF → `nabard_blocks.json` | LIVE | `workbench/nabard_extract.py:1-14` |
| `workbench/nabard_load.py` | NABARD | build/POST the CMS bulk import; excludes GA (100) and Phase-3 descriptive (18) | LIVE | `workbench/nabard_load.py:1-14` |
| `workbench/nabard_fix_answer_keys.py` | NABARD | repair `pyq_options.is_correct` / `pyq_questions.correct_option_id` | LIVE | `workbench/nabard_fix_answer_keys.py:1-14` |
| `workbench/audit_options.py` | NABARD | audit option-label repairs through the same parser path | LIVE | `workbench/audit_options.py:1-13` |
| `scripts/docx_to_pyq_json.py` | UPSC Prelims **only** (docstring) | deterministic .docx → bulk-import v2 envelope | LIVE, not regulatory | `scripts/docx_to_pyq_json.py:2` |
| Worksheets / tag / difficulty drafts | RBI 2022-2026, SEBI, PFRDA, IFSCA, NABARD | difficulty + tag sweeps | DATA-ONLY | `workbench/rbi-{2022..2026}-worksheet*.csv`, `sebi-worksheet.csv`, `pfrda-worksheet.csv`, `ifsca-worksheet.csv`, `nabard-worksheet*.csv` |
| Difficulty rubric for regulatory papers | all four | adapt the UPSC traceability rubric (Acts / ICAI / regulator circulars as the standard-reference tier) | **DOC-ONLY** (explicitly "decide before judging anything") | `docs/status/HANDOFF-regulatory-corpus-2026-09-05.md` § Suggested order, item 2 |

### 2.8 Architecture / planning docs (no code)

| Doc | Scope | Status |
|---|---|---|
| `docs/architecture/financial-regulatory-development-family.md` | whole Lane R: portfolio matrix, stream contract, eligibility split, Compass, domain planner, domain feed, domain rubrics, interview prep, tracker, R1–R4 rollout | header says **PLANNING — no code landed**; §3/§4 have since landed (242/244/248/254) — see §5 mismatches |
| `docs/architecture/regulatory-eligibility-authoring-spec.md` | rule-authoring procedure, four prerequisites | DOC-ONLY (prereqs CODE-FIXED per checklist:558) |
| `docs/architecture/subject-practice-framework.md` | GA/Quant/Reasoning runtime policy; §1.1.1 RBI GA carve-out | partly LIVE (registry, Calc Gym, GA weekly), §1.1.1 carve-out DATA-ONLY |
| `docs/status/HANDOFF-regulatory-corpus-2026-09-05.md` | corpus state, shared-subject finding, suggested order, operator gotchas | DOC-ONLY |
| `docs/status/Regulatory-corpus-decision-provenance-2026-09-06.md` | where review decisions live; RBI recording rule | DOC-ONLY |
| `docs/status/Regulatory-PYQ-needs-correction-backlog-2026-08-31.md` | 121/60/18 cause breakdown | DOC-ONLY |
| `docs/status/career-copilot-checklist.md` § "Financial Regulatory & Development Institutions — Lane R" (lines 525-569) | lane status of record | mixed CODE-FIXED / VALIDATION PENDING / PLANNED / BLOCKED |

### 2.9 Reference corpora on disk (PDF, not ingested as `document_assets`)

`docs/reference/pyq/` carries the source books: SEBI Phase-1 and Phase-2 subject-wise PYQ books for **Commerce & Accountancy, Companies Act, Costing, Economics, Finance, Management**, plus SEBI GA/Quant/Reasoning/English and the Phase-2 Descriptive English book; NABARD Grade A compendium; RBI Grade B 2025/2026 Phase-1 books; IFSCA 2023/2024/2025; PFRDA 2022/2025. `docs/reference/corrections/rbi_gb_2025_phase2_esi.json` holds RBI Phase-2 ESI corrections. **Status: DATA-ONLY** — the evidence matrix in the family doc §6 records every regulator source as `reviewer_status = draft (unverified)`, `document_id = pending`.

---

## 3. Per-subject matrix

Columns: **Catalogue** = microtopics exist · **PYQ corpus** = questions loaded · **Mock projection** = verified→`mock_question_bank` path reached · **Notes/cards** = platform-authored concept content · **Practice tool** = subject-specific runtime beyond generic topic-PYQ · **Evaluator** = answer/response evaluation for that subject · **Planner** = task sequencing support.

Legend: ✅ LIVE · ◐ DATA-ONLY · ○ DOC-ONLY · ✗ ABSENT · *generic* = served only by an exam-agnostic path, nothing subject-specific.

| Subject | Catalogue | PYQ corpus | Mock projection | Notes/cards | Practice tool | Evaluator | Planner |
|---|---|---|---|---|---|---|---|
| **Accounting** (`commerce-accountancy`, 62 micro) | ◐ 62 — SEBI/PFRDA/IFSCA<br>`topic_catalog_regulatory.json` | ◐ within SEBI 440 / IFSCA 444 / PFRDA 201 | ✅ *generic* `183_pyq_mock_projection_bridge.sql` | ✗ | ✗ subject-specific — *generic* `topic_pyq` via `_GENERIC_POLICY` (`subject_runtime_policy.py:401`) | ✗ (MCQ key only) | ✅ *generic* `pyq_practice_launch.py:26-34` |
| **Costing** (`costing`, 58 micro) | ◐ 58 — SEBI/PFRDA/IFSCA | ◐ same corpus | ✅ *generic* | ✗ | ✗ — no costing calculator/variance generator; `calc_gym.py:29` is arithmetic-only | ✗ | ✅ *generic* |
| **Management** (`management`, 78 micro) | ◐ 78 — IFSCA 78 / SEBI 73 / PFRDA 73 | ◐ same corpus | ✅ *generic* | ✗ | ✗ | ✗ — IRDAI Phase-II "Insurance & Management" descriptive is ○ (`family doc §6`) | ✅ *generic* |
| **Finance / Financial Management** (`finance`, 100 micro) | ◐ 100 — IFSCA 100 / SEBI 97 / PFRDA 97; RBI via `topic_catalog_rbi_full.json` | ◐ SEBI/IFSCA/PFRDA loaded; RBI 999 loaded but 0 verified | ✅ *generic* (RBI not projected) | ✗ | ✗ — no TVM/NPV/IRR/bond-pricing generator | ✗ | ✅ *generic* |
| **Taxation** | ✗ **no subject, no microtopics** — `taxation` absent from every catalogue; only `GST` appears as a leaf name inside economics/finance | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Economics / ESI** (`economics` 73; `economic-social-issues` 134) | ◐ economics 73 (IFSCA 73 / SEBI 71 / PFRDA 71, + RBI); ✅ ESI 134 via migration `275_nabard_microtopics.sql` | ◐ economics within the three corpora; ESI within NABARD 1055 | ✅ *generic* | ✗ | ✗ | ✗ — RBI/IRDAI Phase-II ESI descriptive is ○ (`family doc §6`) | ✅ *generic* |
| **Laws & Acts** (`companies-act`, 91 micro) | ◐ 91 — SEBI + PFRDA. Other statutes (SEBI Act, RBI Act, FEMA, Banking Regulation Act) exist only as **leaf names** inside economics/finance; **PMLA and IBC return zero hits** in every catalogue | ◐ within SEBI/PFRDA corpora | ✅ *generic* | ✗ — no section/act/circular reference card, no case-law card | ✗ | ✗ — SEBI Legal / IRDAI Law domain rubric is ○ (`family doc §2, §8.3`) | ✅ *generic* |
| **Insurance** (`insurance`, 26 micro) | ◐ 26 — **IFSCA only**; no IRDAI corpus exists | ✗ no IRDAI PYQ corpus; IFSCA questions only | ✅ *generic* (IFSCA) | ✗ | ✗ | ✗ | ✅ *generic* |
| **Pension** (`pension-sector`, 31 micro) | ◐ 31 — PFRDA + IFSCA | ◐ within PFRDA 201 / IFSCA 444 | ✅ *generic* | ✗ | ✗ | ✗ | ✅ *generic* |
| **Commerce** (`commerce-accountancy`) | — same row as Accounting; the catalogue does not separate them | — | — | — | — | — | — |
| **GA** (`general-knowledge` 55 micro + perishable CA) | ✅ 55 micro / 6 sections via `273_general_knowledge_microtopics.sql`; 7th section (International Relations) live-only, **no migration** | ◐ RBI 320 GA classified 112/90/118 (`workbench/rbi-ga-classification.csv`); NABARD GA 100 excluded at load | ◐ durable carve-out **eligible but not tagged/projected**; perishable permanently excluded | ✗ | ✅ `weekly_current_affairs` (GA family policy) — RBI/SEBI RSS adapters live | ✗ (MCQ key only) | ✅ calendar-driven; `_no_launch_planner_resolver` blocks PYQ stamping (`subject_runtime_policy.py:306-311`) |
| *Shared QRE* (`quantitative-aptitude` 55, `general-intelligence-reasoning` 57, `english-language` 66) | ✅ migrations `277` + live | ◐ within all four corpora | ✅ | ✅ quant heuristics + reasoning strategies (`content_cards`, `291`) | ✅ Calculation Gym, timed practice, English writing | ✅ EWP evaluator — **but no regulatory `writing_prompt_targets` seeded**, and EWP is default-deny | ✅ family policies |
| *NABARD-only* (`agriculture-rural-development` 109, `computer-knowledge` 32, `decision-making` 16) | ✅ migration `275` | ◐ within NABARD 1055 | ✅ *generic* | ✗ | ✗ | ✗ | ✅ *generic* |

**Reading the matrix.** Every regulatory domain subject is at the same maturity: a catalogue exists, a corpus exists, the generic PYQ→mock→practice→mastery→planner chain carries it, and **nothing above that chain is subject-specific**. The Notes/cards, Practice tool and Evaluator columns are empty for all ten domain subjects; they are populated only for the shared QRE subjects, which were built by Lane GQR, not Lane R.

---

## 4. ABSENT list (each explicitly searched)

| # | Item | Verdict | What was searched and found |
|---|---|---|---|
| 1 | **Formula sheets** (FM/costing formula reference) | **ABSENT** | `formula_latex` exists as a single column on `content_cards` (`291_content_cards_generalisation.sql:102`) and in the shared DTO (`app/backend/app/study_os/solution_strategies.py:36,64,88`). It is populated only for `quant_heuristic` and `reasoning_strategy` rows — the only two subtypes the API allows (`app/backend/app/api/content_studio.py:1022-1024`). No formula-sheet entity, no regulatory formula content, no learner formula surface. |
| 2 | **Accounting-standard / Ind AS cards** | **ABSENT** | `ind as` / `accounting standard` / `ifrs` match one unrelated file (`153_extraction_source_kind_gate.sql`). No table, no content type, no catalogue subject. |
| 3 | **Tax-rate tables** | **ABSENT** | No `taxation` subject in any catalogue; no tax-rate table, slab structure, or rate-versioning schema anywhere in `app/supabase/migrations/`. `GST` appears twice as a microtopic leaf name only. |
| 4 | **Section / Act / circular reference cards** | **ABSENT** | `companies-act` microtopics carry section labels in their *names* (e.g. "s.141 eligibility and disqualification", "s.144 prohibited non-audit services") but there is no reference-card entity, no statute table, no circular registry. Regulator circulars exist only as current-affairs *documents* on the SEBI RSS path (`current_affairs/sources.py:101-108`), never as study cards. |
| 5 | **Case-law cards** | **ABSENT** | `case law` / `precedent` / `judgment` match only `app/backend/app/api/essay_builder.py` and `study_os/syllabus_index.json` (UPSC essay/GS context). No case-law entity. |
| 6 | **Numerical practice generators (costing / FM calculators)** | **ABSENT** | The only deterministic generator is Calculation Gym, whose skill set is `tables, squares, cubes, square_roots, cube_roots, fraction_percent, ratio_simplify, approximation, multiplication_patterns` (`app/backend/app/study_os/calc_gym.py:29-101`). No break-even, variance, EOQ, NPV, IRR, TVM, bond-pricing or ratio-analysis generator. |
| 7 | **Concept notes per microtopic** | **ABSENT** | `topics.metadata.study_sources` carries *book references* for UPSC microtopics only (`269_gap_microtopics.sql:66-74`). `exam_subject_resources` (`160_exam_subject_resources.sql`) is a curated booklist mapping, not note content. `/app/notes` is learner-authored (`app/frontend/src/pages/Notes.jsx`). No platform-authored microtopic note exists for any regulatory subject. |
| 8 | **Flashcards / spaced revision for regulatory content** | **ABSENT as content; LIVE as an empty learner tool** | `/app/flashcards`, `/app/flashcards/:deckId`, `/app/study/revision` are live routes over `flashcardsService` / `revisionService` (`appRoutes.jsx:149-153`; `app/backend/app/api/{flashcards,revision}.py`). Decks and revision items are created by the learner; `Revision.jsx:6-12` shows its source kinds are `note / flashcard_deck / mistake / topic / custom`. No seeded regulatory deck, no platform SRS content. |
| 9 | **Descriptive answer evaluation for Phase II (ESI / FM / Management)** | **ABSENT** | Two adjacent systems exist and neither covers it. (a) `descriptive_attempts` is explicitly **self-scored** — "Nothing in this table is machine-scored, and v1 adds no AI evaluation of any kind" (`293_descriptive_attempts.sql:12-16`). (b) The EWP evaluator is English-grammar-scoped and default-deny; **no migration inserts a `writing_prompt_targets` or `exam_descriptive_requirements` row for any regulatory exam**. The domain (non-English) rubric path is named as unbuilt Lane R work: "New Lane R work = the **domain (non-English) rubric path** only; the grammar issue-type taxonomy (`205:308-312`) does not fit IRDAI ESI / Insurance & Management or SEBI Legal domain answers" (`family doc §5`). Status **DOC-ONLY**. |
| 10 | **Mastery tracking per regulatory subject** | **ABSENT as a regulatory-specific feature; LIVE generically** | Regulatory domain subjects resolve to no family in `_GROUP_FAMILY` / `_SLUG_FAMILY` (`subject_runtime_policy.py:74-98`) and therefore to `_GENERIC_POLICY`, which sets `mastery_enabled=True` (`:401-408`) — so `user_topic_mastery` accrues on regulatory topics through the ordinary objective path. There is no regulatory subject family, no per-subject mastery tier, and no regulatory mastery surface. Cross-exam reuse exists but is unsurfaced (see #11). |
| 11 | **Planner support for regulatory exams** | **PARTIAL — generic LIVE, regulatory-specific DATA-ONLY** | Generic: `_pyq_planner_resolver` stamps `pyq_practice` for `retrieval_practice` / `revision` on any topic+exam (`subject_runtime_policy.py:288-303`). Regulatory-specific: `shared_core.py` computes the shared-core partition, fail-closed global-only mastery reuse and the 70/20/10 allocation, exposed at `GET /api/study/regulatory-overlap` (`app/backend/app/api/study_os.py:600-613`) — **but grep finds no consumer of `regulatory-overlap` anywhere in `app/frontend/src`**, and the module's own docstring says applying the allocation inside `_compute_plan` "is increment 2" (`shared_core.py:4-5`). The combined multi-regulatory plan does not exist. |

**Two further absences found while searching, not on the mandated list:**

| # | Item | Verdict | Evidence |
|---|---|---|---|
| 12 | Regulatory mock templates / blueprints | **ABSENT** | The only seeded `mock_templates` row in the whole migration set is `ibps-po-prelims-mock-1` (`135_mock_engine_core.sql:203-205`). Regulatory mocks exist only as PYQ-projected paper/topic practice. |
| 13 | Operator-validation gates for Lane R | **ABSENT** | `docs/operator-validation/registry.json` contains **zero** occurrences of `sebi`, `nabard`, `pfrda`, `ifsca`, `irdai` or `regulatory`. Every Lane R "VALIDATION PENDING" row in the checklist is tracked in the checklist only, with no registered operator gate. This is a live violation of the `CLAUDE.md` rule that operator status is registry-owned. |

---

## 5. Doc-vs-code mismatches

| # | Doc claim | Code reality | Verdict |
|---|---|---|---|
| 1 | `financial-regulatory-development-family.md` header: **"Status: PLANNING — architecture proposal, no code landed."** | §3 stream contract landed as `242_exam_streams_schema.sql`; §6 identities landed as `244_financial_regulatory_family_identity_seed.sql`; §4 eligibility landed as `248_exam_stream_eligibility.sql` + `254_exam_eligibility_stream_aware_activation.sql`; §9 classifier fix landed at `recruitment_classifier.py:58-90`; §8 items 1–2 landed as `ExamStreamBreakdown.jsx` + `shared_core.py`. | **Header is stale.** The doc's own §4 body contradicts it ("Status — A2 (CODE-FIXED, VALIDATION PENDING)"). Gap: the front-matter status was never updated as the lane shipped. |
| 2 | Family doc §9 classifier fix: *"Replace with explicit `"trai"`; add `"ifsca"`."* | The landed fix is structurally different — boundary-aware acronym regex matching, because `"trai"` alone still false-matches `training`/`trainee` (`recruitment_classifier.py:79-85`; rationale recorded at `career-copilot-checklist.md:553`). | **Doc prescribes a narrower fix than the code implements.** Code is correct; doc §9 was not revised. |
| 3 | Family doc §8 item 2: *"Shared-core Study OS plan — deterministic planner; reuses mastered common topics across concurrent cycles."* | `shared_core.py` computes the partition and the allocation, but explicitly "does NOT touch `_compute_plan` (increment 2)" (`shared_core.py:4-5`), and `GET /api/study/regulatory-overlap` has **no frontend consumer**. | **Doc says X, code partially found.** The substrate exists; the plan feature does not. Gap: an aspirant cannot see or use shared-core reuse. |
| 4 | Family doc §7 / handoff §"The subjects are genuinely shared": one catalogue, four exams, seven shared domain subjects. | Confirmed in the catalogue data (`topic_catalog_regulatory.json`: finance 100, companies-act 91, management 78, economics 73, commerce-accountancy 62, costing 58, pension-sector 31). **But no numbered migration creates any of these subjects or microtopics.** `275`/`277` cover NABARD + QRE only; `273` covers general-knowledge. The regulatory domain taxonomy exists live-only, seeded through untracked root scratch SQL (`add_nabard_subjects.sql`, `add_gk.sql`, `add_qre_microtopics.sql`, `fix_esi.sql`, `activate_reg_exams.sql`, `gap_microtopics.sql`). | **Doc says X, migration not found.** Same defect class the framework doc already admits for GK International Relations ("the live taxonomy is ahead of the migration history", `subject-practice-framework.md` §1.1.1). Scope is far wider than that one section: **the entire SEBI/IFSCA/PFRDA/RBI domain subject set is unmigrated.** Gap: a rebuild from migrations produces a database with no regulatory subjects. |
| 5 | `subject-practice-framework.md` §1.1.1: the RBI GA durable carve-out makes 202 questions "eligible for PYQ tagging and projection". | `workbench/rbi-ga-classification.csv` and `workbench/rbi-gk-microtopic-map.csv` exist; **no tagging or projection has occurred** — the handoff records RBI as 0 verified / 0 tagged / 0 projected. The doc itself says so ("Nothing here tags or projects a question"). | **Consistent, but the carve-out is inert.** Gap: eligibility was granted, work not done. |
| 6 | `subject-practice-framework.md` §2.2 registry lists four subject families and says "Adding a mode to a vertical is a registry edit". | `_GROUP_FAMILY` and `_SLUG_FAMILY` (`subject_runtime_policy.py:74-98`) contain **no regulatory subject slug**. Every regulatory domain subject silently resolves to `_GENERIC_POLICY`. | **Not a contradiction — the doc never claimed regulatory coverage** (its §1 scope is GA/Quant/Reasoning). Recording it because the silent fallback is invisible: a regulatory subject gets generic behaviour with no diagnostic. Gap: no `finance`/`costing`/`law` family, so no domain-specific runtime is expressible. |
| 7 | Handoff § State: *"The three regulatory exams are keyed, tagged to microtopics, verified and projected"* with counts 402 / 362 / 142. | These are **live database counts**. Nothing in the repository can confirm or refute them — the exports under `review_out_*` carry question rows, not projection state. | **Unverifiable from code.** Flagged per the validation rule: treat the counts as doc-asserted DB state, not repo-verified. |
| 8 | `Regulatory-corpus-decision-provenance-2026-09-06.md` §2: the backlog doc records 121 `needs_correction`, "the exports record **101 / 60 / 18**". | The backlog doc itself still prints 121 (`Regulatory-PYQ-needs-correction-backlog-2026-08-31.md`, count table). | **Known stale count, already documented as stale.** No action; recorded so a reader of the backlog doc alone is not misled. |
| 9 | Family doc §6 evidence matrix: every regulator source `reviewer_status = draft (unverified)`, `document_id = pending`. | `docs/reference/pyq/` holds the actual PDFs on disk (SEBI subject-wise Phase-1 and Phase-2 books, NABARD, RBI, IFSCA, PFRDA). They are repo files, not ingested `document_assets` rows. | **Consistent.** Gap: the source books that back every catalogue and corpus decision are unverified reference material, so no regulatory syllabus or eligibility rule can currently be promoted to `verified` under the `257` document trust gate. |
| 10 | Checklist:561 — Compass current-cycle band "CODE-FIXED, VALIDATION PENDING (browser/live proof pending)". | Code present (`ExamStreamBreakdown.jsx`, `EligibleExamsCard.jsx`, `evaluator._load_verified_cycles`). No operator gate registered. | **Registry gap** (same as ABSENT #13). Per `CLAUDE.md`, a validation-pending item needs a `validation_pending` gate in `registry.json`; none exists for any Lane R row. |

---

## 6. One-line gap notes

- **Taxation has no representation at all** — no subject, no microtopics, no corpus, though SEBI/RBI Phase-II syllabi assume it.
- **IRDAI has draft streams but zero content** — no PYQ corpus, no catalogue beyond IFSCA's 26 insurance microtopics.
- **RBI Grade B is the largest corpus on the platform and is entirely unreviewed** — 999 questions, 0 verified, 0 tagged, 0 projected.
- **The regulatory domain taxonomy is unmigrated** — live-only, created by deleted/untracked root scratch SQL.
- **Every domain subject stops at generic PYQ practice** — no notes, cards, formula sheets, calculators or domain evaluators above the shared chain.
- **`/api/study/regulatory-overlap` is built and unreachable** — no frontend consumer, no planner integration.
- **No Lane R operator-validation gate exists** in `registry.json`, despite eight checklist rows marked VALIDATION PENDING.
- **Multi-paper year grouping is still open** — 43 undifferentiated SEBI paper cards in the PYQ Explorer (handoff § Suggested order, item 5).
- **No difficulty rubric for regulatory papers** — 906 tagged questions carry none, and the UPSC traceability rubric transfers only partly.

---

*Read-only inventory. No repository file was modified, no commit or branch was created, and no live API or database was queried.*

---

## 7. DB-verified corrections (operator, 2026-09-22)

Live-database readings supplied by the operator. These supersede the repo-derived
claims in §2 and §3 where they conflict; the earlier sections are left unedited so
the repo-only view stays auditable against the SHA in §1.

### 6.1 RBI Grade B — corpus is half-verified and projected

| Metric | Value |
|---|---|
| Questions | 999 |
| verified | 531 |
| projected to `mock_question_bank` | 531 |
| pending | 440 |
| needs_correction | 28 |

`docs/status/HANDOFF-regulatory-corpus-2026-09-05.md` § State ("0 verified, 0 tagged,
0 projected") and the §2.3 / §3 rows that repeat it are **STALE**.

**Section 3 correction — Finance row, RBI:** the `PYQ corpus` and `Mock projection`
cells read "RBI 999 loaded but 0 verified" / "(RBI not projected)". Both are wrong.
Mark the Finance RBI cell **LIVE partial** — 531 of 999 verified and projected,
440 still pending, 28 needing correction.

### 6.2 Content tables are schema-live and content-empty

| Table | Rows |
|---|---|
| `content_cards` | 2 |
| `content_card_links` | 1 |
| `flashcards` | 0 |
| `flashcard_decks` | 1 |
| `revision_items` | 0 |
| `pyq_question_explanations` | 0 |
| `personal_notes` | 0 |

**Section 3 correction — shared-QRE `Notes/cards` cell:** currently ✅ on the strength
of `content_cards` existing (migration `291`). Two rows is not a content library.
Downgrade that cell to **◐ — schema LIVE, content empty**, not ✅.

This also confirms, from the database rather than from code inspection, ABSENT items
#1, #2, #4, #5, #7 and #8 in §4: the authoring surfaces exist and hold no content.

### 6.3 Regulatory mock bank — projected, unexplained

| Metric | Value |
|---|---|
| Regulatory rows in `mock_question_bank` | 2,484 |
| `reviewer_status = 'published'` | 2,484 (all) |
| `explanation` non-empty | 0 |
| `common_trap` non-empty | 0 |

Every regulatory question a learner can reach is published with no explanation and
no trap note. Projection is complete; post-attempt learning value is zero.

### 6.4 Per-exam verified vs projected

| Exam | verified | projected | Gap |
|---|---|---|---|
| NABARD | 1048 | 1047 | **1** |
| SEBI | 402 | 402 | — |
| IFSCA | 362 | 362 | — |
| PFRDA | 142 | 142 | — |

The single NABARD gap is **Q.32, `ac2bd1dd-28cf-4183-8f89-1decb38957f9`** — 0 topic
tags and stimulus-dependent, so it fails projection on both counts.

SEBI / IFSCA / PFRDA are at exact parity, which also confirms the doc-asserted
402 / 362 / 142 counts flagged as unverifiable in §5 row 7.

### 6.5 Current affairs

| Metric | Value |
|---|---|
| `current_affairs_sources` | 7 |
| `current_affairs_question_candidates` | 0 |

Ingestion is wired (§2.6) and has produced no question candidates. The GA practice
runtime has no regulatory-sourced inventory behind it.
