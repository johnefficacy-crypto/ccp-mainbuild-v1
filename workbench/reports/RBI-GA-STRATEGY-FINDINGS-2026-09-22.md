# RBI Grade B — General Awareness strategy, GA↔GK separation, and the "Finance & Management" taxonomy

**Generated:** 2026-09-22 · read-only investigation · no live API or DB was queried by this pass.

> **Note on structure.** The commissioning task's OUTPUT section was truncated before it enumerated
> its sections. The nine sections below are derived from the task's stated goals (locate the GA
> strategy of record; establish how GA is kept separate from GK; resolve the RBI "Finance &
> Management" taxonomy) plus the section-9 contents the requester specified explicitly. If the
> intended outline differs, the content maps across without re-investigation.

---

## 1. Preflight

| Gate | Result |
|---|---|
| `git rev-parse HEAD` | `69daddeacce42025c41944c20c0e63ef524262e0` |
| `git branch --show-current` | `claude/reg-subject-inventory-2026-09-22` |
| Working tree | clean |
| Writes performed | none during investigation; this report is the only file created |
| `graphify-out` present | yes |
| Graph freshness | **STALE** — built from `8dca18e4` (`graphify-out/GRAPH_REPORT.md:13`), HEAD is `69dadde` |

Priming order honoured: `AGENTS.md` → `graphify-out/GRAPH_REPORT.md` → `graphify-out/wiki/index.md`
before any source file.

**Search terms:** `general awareness`, `GA lane`, `GA track`, `perishable`, `shelf life`, `stale`,
`expiry`, `valid_until`, `event_anchor`, `current affairs`, `CA-RSS`, `weekly_current_affairs`,
`GK vs GA`, `general-knowledge`, `general_studies`, `ssc-cgl`, `finance-management`,
`finance & management`, `_GROUP_FAMILY`, `_SLUG_FAMILY`, `subject_group`, `is_current`,
`is_current_based`, `source_kind`, `current_event`, `GQR-G`.

**Scope searched:** `docs/status/`, `docs/audits/`, `docs/runbooks/`, `docs/reference/`,
`docs/architecture/`, `workbench/` (incl. `reports/`, `prompts/`, `catalogs/`, `ga-classification/`),
`memory/`, `app/backend/app/`, `app/supabase/migrations/`, `scripts/`, `tools/`, and `git log`.

---

## 2. The GA strategy of record

**Primary document:** `docs/architecture/current-affairs-pipeline.md` —
*"architecture decision — APPROVED 2026-07-12 (johnefficacy-crypto); GATES the LLM pipeline PR
(gate CLEARED)"* (`:3`, restated at `:36`).

**Companion product lock:** `docs/architecture/subject-practice-framework.md` §1.1
(`:44-52`) — GA v1 is **current-affairs practice only**, modes `weekly_current_affairs` /
`monthly_current_affairs`, explicitly excluding PYQ ingestion/projection, static-GK practice,
permanent topic mastery, long-term SRS, standalone sectional mocks, permanent Mistake Book entries,
and automatic publication of AI-generated questions.

Perishability is not a convention — it is enforced at four independent layers:

| Layer | Mechanism | Evidence |
|---|---|---|
| Promotion | approved candidate enters the objective bank with `source_kind='current_event'`, `is_current_based=true`, `valid_until=<relevance window>` | `current-affairs-pipeline.md:368-381` |
| Generated-mock isolation | `is_current` / `is_current_based` / expired `valid_until` filtered out of the base pool | `app/backend/app/study_os/mock_blueprint_selection.py:255-264` |
| Template-mock isolation | same predicate, mirrored term-for-term | `app/backend/app/study_os/mock_engine.py:400-414` |
| Attempts | own tables (`current_affairs_attempts`), never `mock_attempts` | `current-affairs-pipeline.md:403-433`; migration `253_current_affairs_bundles_attempts.sql` |
| Mastery | no write to `user_topic_mastery`, long-term SRS, permanent Mistake Book, or correction tasks | `current-affairs-pipeline.md:446-452`; `subject_runtime_policy.py:385-395` |

Runtime policy for the GA family (`subject_runtime_policy.py:385-395`) sets
`mastery_enabled=False`, `correction_enabled=False`, `retry_policy="ephemeral_ca"`,
`attempt_kind="current_affairs_attempt"`, and `planner_resolver=_no_launch_planner_resolver`
(`:306-311`) — so a General-Awareness retrieval or revision task can **never** be stamped
`pyq_practice`. Retry is short-lived by construction (`current_affairs_retry_items`, `due_at` /
`expires_at`, `current-affairs-pipeline.md:453-458`).

**Delivery status.** Lane GQR rows GQR-G0 through GQR-G6 are all **CODE-FIXED, VALIDATION PENDING**
(`docs/status/career-copilot-checklist.md:502-510`). Supporting migrations all present:
`241_current_affairs_source_evidence.sql`, `247_current_affairs_generation.sql`,
`249_current_affairs_promotion.sql`, `253_current_affairs_bundles_attempts.sql`,
`255_current_affairs_attempt_start_hardening.sql`, `258_ca_monthly_retry.sql`.

---

## 3. How GA is kept separate from GK

### 3.1 The product decision

`docs/architecture/subject-practice-framework.md:54-57` — **"Amended 2026-09-07 — see §1.1.1"** —
narrows §1.1's blanket GA exclusion. The amendment itself is §1.1.1
(`:58-99`, *"Amendment — RBI Grade B GA durable carve-out (2026-09-07)"*).

The classification table (`:67-72`):

| Bucket | Count | Detail (verbatim from `:69-71`) |
|---|---|---|
| Durable, answer inside an existing finance subject | **112** | banking 71, economics 24, capital-market 15, financial-awareness 1, pension-sector 1 |
| Durable, non-finance | **90** | static GK — geography, polity, history, science, international relations |
| Perishable | **118** | a dated instance, an as-of figure, or a per-edition datum |
| **Total** | **320** | |

**Reconciliation of the two count shapes.** `112 + 90 = 202` is the split of **one and the same
durable set** — it is not a second, competing tally. The doc reports durable *by destination
subject*; `workbench/rbi-ga-classification.csv` reports the same rows *by classification only*,
giving `DURABLE 202 / PERISHABLE 118`. Both sum to 320 and describe identical rows. The CSV's
`suggested_subject` column confirms the identity exactly: 112 rows carry a finance subject
(banking 71, economics 24, capital-market 15, pension-sector 1, financial-awareness 1 — matching
`:69` value-for-value) and 208 are blank (= 90 durable-non-finance + 118 perishable).

The boundary rule (`:74-76`): *"a durable subject with a dated instance is perishable — 'which body
regulates X' is durable, 'what did X reach in FY22' is not."*

The carve-out (`:78-83`): durable GA questions become eligible for PYQ tagging and projection — the
112 against existing finance subjects, the 90 against `general-knowledge`. The 118 perishable
**stay excluded** under §1.1, contribute no permanent topic mastery, and are never projected. The
doc is explicit that this *"narrows §1.1's exclusion from 'GA' to 'perishable GA'"*, does not reopen
GA current-affairs for mastery, and *"does not extend to any other body's GA section"* (`:83-85`).

### 3.2 The enforcing mechanism in code

The separation is carried entirely by the family resolver in
`app/backend/app/study_os/subject_runtime_policy.py`:

- `_GROUP_FAMILY` (`:74-84`) maps `general-awareness`, `general_awareness` and `current-affairs`
  → `FAMILY_GENERAL_AWARENESS`.
- `_SLUG_FAMILY` (`:86-97`) maps `general-awareness`, `general-awareness-current-affairs` and
  `current-affairs` → `FAMILY_GENERAL_AWARENESS`.
- **`general-knowledge` appears in neither map.** `family_for_subject` (`:100-117`) therefore returns
  `None`, and `policy_for_family` (`:411-417`) falls through to `_GENERIC_POLICY` (`:401-408`), which
  sets `mastery_enabled=True`, `correction_enabled=True`, `retry_policy="normal_srs"`,
  `wired_runtime_modes=(MODE_ENGLISH_WRITING, MODE_TOPIC_PYQ)` and
  `planner_resolver=_pyq_planner_resolver`.

That asymmetry **is** the separation: GK behaves as an ordinary PYQ-backed, mastery-accruing subject;
GA is fenced into the bundle-driven, mastery-free runtime. Nothing else distinguishes them at
runtime, which is why §9 item (c) matters.

`:74-79` also records a deliberate exclusion: UPSC's `gs` group is *not* mapped to
`general_awareness`, because those are PYQ-backed subjects that must keep the generic runtime.

### 3.3 Growth signal recorded in the contract

`:87-97` tracks durable-non-finance by year — 2023: 17, 2024: 16, 2025: 28, 2026: 29 — and warns
*"RBI GA is moving toward static GK at least as fast as toward banking… sizing decisions that assume
GA ≈ banking will be wrong."*

---

## 4. The classification corpus, and an unresolved conflict

### 4.1 Two passes exist over the same 320 questions

| File | Rows | DURABLE | PERISHABLE |
|---|---|---|---|
| `workbench/rbi-ga-classification.csv` (combined; header `:1`, data `:2-321`) | 320 | **202** | **118** |
| `workbench/ga-classification/rbi-ga-2023-classification.csv` (`:2-81`) | 80 | 44 | 36 |
| `workbench/ga-classification/rbi-ga-2024-classification.csv` (`:2-81`) | 80 | 53 | 27 |
| `workbench/ga-classification/rbi-ga-2025-classification.csv` (`:2-81`) | 80 | 49 | 31 |
| `workbench/ga-classification/rbi-ga-2026-classification.csv` (`:2-81`) | 80 | 46 | 34 |
| **per-year total** | **320** | **192** | **128** |

Both sets cover an identical universe of 320 `question_id` values — zero IDs are unique to either
side. Only the verdicts differ.

`docs/architecture/subject-practice-framework.md:64-66` cites the **combined** file by name
(*"were classified in `workbench/rbi-ga-classification.csv`"*), and its 202/118 split matches that
file exactly. The per-year set is cited by no document.

### 4.2 The 12 disagreements, located

| Year | Q# | combined line | per-year line | per-year says | combined says |
|---|---|---|---|---|---|
| 2023 | 1 | `rbi-ga-classification.csv:2` | `rbi-ga-2023-classification.csv:2` | DURABLE | PERISHABLE |
| 2023 | 27 | `:28` | `rbi-ga-2023-classification.csv:28` | PERISHABLE | DURABLE |
| 2024 | 7 | `:88` | `rbi-ga-2024-classification.csv:8` | PERISHABLE | DURABLE |
| 2024 | 16 | `:97` | `rbi-ga-2024-classification.csv:17` | PERISHABLE | DURABLE |
| 2024 | 75 | `:156` | `rbi-ga-2024-classification.csv:76` | PERISHABLE | DURABLE |
| 2025 | 1 | `:162` | `rbi-ga-2025-classification.csv:2` | PERISHABLE | DURABLE |
| 2025 | 65 | `:226` | `rbi-ga-2025-classification.csv:66` | PERISHABLE | DURABLE |
| 2025 | 71 | `:232` | `rbi-ga-2025-classification.csv:72` | PERISHABLE | DURABLE |
| 2025 | 80 | `:241` | `rbi-ga-2025-classification.csv:81` | PERISHABLE | DURABLE |
| 2026 | 3 | `:244` | `rbi-ga-2026-classification.csv:4` | PERISHABLE | DURABLE |
| 2026 | 24 | `:265` | `rbi-ga-2026-classification.csv:25` | PERISHABLE | DURABLE |
| 2026 | 77 | `:318` | `rbi-ga-2026-classification.csv:78` | PERISHABLE | DURABLE |

Net: 11 PERISHABLE→DURABLE and 1 DURABLE→PERISHABLE, giving the combined file its extra 10 durable
rows. The 2023 Q1 row shows the conflict cleanly: combined
(`workbench/rbi-ga-classification.csv:2`) reads *"BSR anniversary year count tied to October 2022"*
→ PERISHABLE; per-year (`workbench/ga-classification/rbi-ga-2023-classification.csv:2`) reads
*"BSR code structure and its fixed 50-year anniversary count; answer does not change"* → DURABLE.
Same question, opposite reasoning.

### 4.3 Destination subjects also diverge

`suggested_subject`, combined vs per-year: banking 71 / 72, economics 24 / **6**,
capital-market 15 / 14, financial-awareness 1 / **27**, pension-sector 1 / 2. Total assigned
112 vs **121**. The economics↔financial-awareness swing is the largest single divergence and is
independent of the DURABLE/PERISHABLE disagreement above.

### 4.4 No ordering signal

Both the combined file and the entire `workbench/ga-classification/` directory entered history in
the same merge — `7935ff3` (2026-09-11, *"Merge pull request #1090 from
johnefficacy-crypto/fix/syllabus-verbatim-flag"*). Neither supersedes the other by date, and neither
carries a header declaring precedence.

### 4.5 Disposition

**The 12 disagreements and the orphan per-year CSV set are UNRESOLVED, and no tagging of the 320 RBI
Grade B GA questions should start until one file is declared of record.** Tagging against the wrong
file would place up to 12 questions in the wrong lifecycle — a perishable question projected as
permanent, or a durable one withheld — and would route up to 21 more to the wrong destination
subject. Both outcomes violate §1.1's rule that perishable GA contributes no permanent mastery, and
both are expensive to reverse once tags exist, because retagging a projected paper takes it offline
until re-synced (`docs/status/HANDOFF-regulatory-corpus-2026-09-05.md`, §"What applies here" §11).

---

## 5. RBI Grade B "Finance & Management" — resolving the taxonomy

### 5.1 The live shape

Per the supplied live facts: subject `finance-management`
(`faf44664-795d-44e0-9dc8-fbbb9d8fa01d`), `subject_group` **NULL**, **0 topics**, referenced only by
`exam_phase_sections` — one `"Finance & Management"` row plus four
`"Finance & Management - Descriptive"` rows across five phases.

### 5.2 What the repository documents

**`finance-management` does not appear anywhere in the repository** — no migration, architecture doc,
status doc, runbook, script, catalogue or prompt. A case-insensitive search for the slug and for the
phrase *"Finance & Management" / "Finance and Management"* across `docs/`, `workbench/`, `app/`,
`scripts/` and `tools/` returns no definition of it as a subject.

What the repository *does* document is the opposite arrangement.
`scripts/pyq_question_review.py:868-871`:

> *"precisely because the regulatory bodies SHARE subjects — RBI Grade B sits on the same Finance /
> Management / Economics / Commerce & Accountancy / Costing / QRE rows as SEBI, PFRDA and IFSCA."*

Restated in the same file's CLI contract at `:59-62`:

> *"one file spans the bodies that share subjects (RBI Grade B / SEBI / PFRDA / IFSCA sit on the same
> Finance, Management, Economics, Commerce & Accountancy, Costing and QRE microtopics)"*

The built RBI catalogue agrees. `workbench/catalogs/topic_catalog_rbi_full.json` (429 microtopic
rows) resolves to six subjects — `finance` **100**, `management` **78**, `economics` 73,
`english-language` 66, `general-intelligence-reasoning` 57, `quantitative-aptitude` 55. Finance and
Management are two separate subjects in the RBI catalogue; no merged subject appears.

This matches the live tagging already in progress: `finance` 17/100 and `management` 10/78 tagged
(supplied live facts), against catalogue sizes of exactly 100 and 78.

### 5.3 Resolution

**"Finance & Management" is RBI's *paper/section label*, not a subject.** The `finance-management`
row is a placeholder created to satisfy the `exam_phase_sections.subject_id` foreign key when those
five sections were seeded; its NULL `subject_group` and zero topics are consistent with a row that
was never intended to carry taxonomy.

The intended taxonomy for the section's content is the **shared `finance` and `management`
subjects**, split per question, since the paper mixes both domains. Consequences:

- `finance-management` should remain at 0 topics and receive no microtopics and no question tags.
- The 72 RBI Phase-II ESI+FM 2025 questions tag onto `economics` / `economic-social-issues` (ESI)
  and `finance` / `management` (FM), on the same microtopic rows SEBI, PFRDA and IFSCA already use.
- Because `finance-management` has `subject_group = NULL` and a slug absent from both
  `_SLUG_FAMILY` and `_GROUP_FAMILY` (`subject_runtime_policy.py:74-97`), it resolves to
  `_GENERIC_POLICY` — so had it carried topics, it would have silently behaved as a full
  mastery-accruing PYQ subject alongside the real `finance`/`management`, double-counting the domain.

### 5.4 A related gap found while resolving this

No catalogue or migration carries an `"rbi"` key in `topics.metadata.exams` — a search for `"rbi"`
across `workbench/catalogs/` and `app/supabase/migrations/` returns nothing. Since
`catalog_rows()` (`scripts/pyq_question_review.py:855-880`) selects microtopics by
`metadata.exams INTERSECTS bodies`, invoking it with `--body rbi` would today return an empty
catalogue. `topic_catalog_rbi_full.json` must therefore have been built by another route, or the
`exams` keys exist only in the live database. Either way the documented tooling path for RBI is not
reproducible from the repository as it stands.

---

## 6. The RBI GA corpus today

From the supplied live facts: RBI Grade B carries **440 pending questions, all untagged** — 320 GA
(80 each on 2023 / 2024 / 2025 / 2026 Phase I), 72 Phase-II ESI+FM 2025, 48 descriptive-only.

Cross-checks against the repository:

- The 320 figure is exactly the population classified in §4, and matches
  `docs/architecture/subject-practice-framework.md:72`.
- `docs/status/Regulatory-corpus-decision-provenance-2026-09-06.md` §4 independently fixes the
  untouched-GA count at **320** (80 each in `rbi-{2023,2024,2025,2026}-worksheet.csv`) and warns that
  *"a 400 figure is not reproducible from anything in the repo"*.
- NABARD's GA section was excluded from loading on the same §1.1 grounds —
  `workbench/nabard_load.py:5-7` excludes *"General Awareness (100,
  subject-practice-framework.md §1.1)"*. §1.1.1 is explicit (`:83-85`) that the carve-out is per
  corpus and extends to no other body, so NABARD's 100 stay excluded.

The carve-out is therefore **granted but entirely inert**: nothing in the 320 has been tagged or
projected. §1.1.1 says so itself (`:117-119`): *"Nothing here tags or projects a question. Tagging
remains a separate, reviewed step."*

---

## 7. Pipeline state vs. content state

The GA machinery is built; it has produced nothing.

| Signal | Value | Source |
|---|---|---|
| `current_affairs_sources` | 7 | supplied live facts |
| `current_affairs_question_candidates` | 0 | supplied live facts |
| Seeded sources in contract | 7 (PIB, RBI press/notifications/speeches, SEBI, UNESCO WHC, The Hindu) | `current-affairs-pipeline.md:110-119` |

The live source count matches the contract's seeded table exactly. Candidate count is zero, so no
question has been generated, reviewed, promoted, or bundled — the perishable path has no content,
just as the durable path (§6) has no tags. Neither half of the GA strategy has yet reached a learner.

`mock_question_bank` carries the freshness columns the contract relies on — `is_current`,
`is_current_based`, `event_anchor_date`, `valid_from`, `valid_until`, `current_affairs_item_id`
(supplied live facts; introduced by migration 159 per `current-affairs-pipeline.md:369-372`) — so the
isolation machinery is in place ahead of the content.

---

## 8. Answers to the three questions asked

1. **The GA strategy of record** is `docs/architecture/current-affairs-pipeline.md` (APPROVED
   2026-07-12, `:3`), scoped by `subject-practice-framework.md` §1.1 (`:44-52`). GA is treated as a
   perishable class: promoted with an explicit `valid_until`, excluded from both mock selectors,
   attempted on its own tables, and barred from mastery, SRS, the Mistake Book and correction tasks.

2. **GA is kept separate from GK** by the family resolver, not by naming convention:
   `general-awareness` resolves to `FAMILY_GENERAL_AWARENESS` (mastery off, bundle-driven, no PYQ
   stamp); `general-knowledge` is absent from both lookup maps and falls to `_GENERIC_POLICY`
   (mastery on, PYQ on). The 2026-09-07 carve-out (`subject-practice-framework.md:58-99`) routes
   durable RBI GA into that GK/finance lane while leaving the 118 perishable rows under the original
   exclusion.

3. **"Finance & Management" is a section label, not a subject.** The documented taxonomy puts RBI
   Grade B on the shared `finance` and `management` subjects alongside SEBI/PFRDA/IFSCA
   (`scripts/pyq_question_review.py:868-871`; `workbench/catalogs/topic_catalog_rbi_full.json`). The
   live `finance-management` row is an undocumented FK placeholder and should stay empty.

---

## 9. Doc-vs-live contradictions

| # | Contradiction | Documented / code position | Live reality | Consequence |
|---|---|---|---|---|
| a | **`finance-management` exists live with 5 sections and 0 topics, documented nowhere** | No migration, doc, script or catalogue defines the slug; the documented model puts RBI on shared `finance`/`management` (`scripts/pyq_question_review.py:59-62`, `:868-871`; `workbench/catalogs/topic_catalog_rbi_full.json` — finance 100, management 78 as separate subjects) | subject `faf44664-795d-44e0-9dc8-fbbb9d8fa01d`, `subject_group` NULL, 0 topics, referenced by 1 `"Finance & Management"` + 4 `"Finance & Management - Descriptive"` `exam_phase_sections` rows | An undocumented taxonomy node sits in the section graph. Were it ever populated it would resolve to `_GENERIC_POLICY` (`subject_runtime_policy.py:401-408`) and double-count the FM domain against the real `finance`/`management` subjects |
| b | **`general-awareness` row exists live with 7 topics; the code asserts it does not** | `app/backend/app/study_os/subject_runtime_policy.py:46-52`: GA *"has no real `subjects` row and never appears via locked `exam_topic_coverage`"*, hence sentinel `CURRENT_AFFAIRS_VIRTUAL_SUBJECT_ID` (`:53`). `:28` calls the SSC GA seed *"a tracked prerequisite"* | subject `f8034c83-cb92-4878-a4ce-eef118b0ecec` exists with 7 topics, 0 microtopics, 0 tagged questions. No migration creates it — `110_exam_eligibility_rules.sql:87` creates only the `ssc-cgl` **exam** | The sentinel's stated premise is false. The row was seeded outside the migration set (same defect class as the `general-knowledge` International Relations gap already admitted at `subject-practice-framework.md:111-116`), so a rebuild from migrations produces a database the code's comment describes but the live system contradicts |
| c | **`subject_group='ssc-cgl'` puts GA on the `_SLUG_FAMILY` fallback, not `_GROUP_FAMILY`** | `subject_runtime_policy.py:100-117` states `subject_group` *"(the governed taxonomy column) is authoritative; `slug` is a fallback"*. `_GROUP_FAMILY` (`:74-84`) expects `general-awareness` / `general_awareness` / `current-affairs` | live `subject_group` is `ssc-cgl` — an **exam** slug in the subject-group column. That key is absent from `_GROUP_FAMILY`, so the primary lookup misses and GA resolves only via `_SLUG_FAMILY` at `:112` | GA's mastery-free fencing currently survives on the backup path. Renaming the subject slug, or any change that reaches `family_for_subject` by group first, would silently drop GA into `_GENERIC_POLICY` and switch `mastery_enabled` to True — the precise outcome §1.1 forbids, with no error raised |
| d | **PARKED comment stale against the shipped fix** | `app/backend/app/study_os/mock_blueprint_selection.py:40-46`: *"PARKED — TEMPLATE-PATH POOL DIVERGENCE … `mock_engine._select_criteria_question_ids` / `select_questions_for_template` build a LOOSER pool … NO `is_current` exclusion … Aligning the template path is parked for a later PR"* | `app/backend/app/study_os/mock_engine.py:400-414` excludes both `is_current` and `is_current_based`, citing GQR-G0 by name at `:413`. `docs/status/career-copilot-checklist.md:502` records GQR-G0 as CODE-FIXED | A reader of the blueprint selector is told a ship-blocking correctness gap is still open when it was closed. Risks either redundant re-fixing or false reliance on a warning that no longer describes the code |
| e | **Lane verdict stale against its own table** | `docs/status/career-copilot-checklist.md:494`: *"Current verdict: **CONTRACT-FIRST / PLANNED. Two architecture contracts landed (this PR); no runtime code shipped.**"* | The table immediately below, `:502-510`, lists GQR-G0, G2, G3, G4a, G4b, G5a, G5a-h, G5b and G6 all as CODE-FIXED, VALIDATION PENDING, with migrations 241/247/249/253/255/258 all present on disk | The lane's headline verdict contradicts its own evidence rows. Anyone reading only the verdict concludes GA has no runtime, when the full backend arc has shipped and awaits operator validation |

### Related: no operator gate covers any of this

`docs/operator-validation/registry.json` contains no entry for GA, current affairs, RBI, or Lane GQR.
Every GQR-G row above is marked VALIDATION PENDING in the checklist alone. Under `CLAUDE.md`'s
operator-validation hygiene rules, mutable operator status belongs in the registry, not in the
checklist — so the nine pending validations currently have no tracked gate, deadline or owner.

---

*Read-only investigation. No repository file was modified other than the creation of this report, no
live API or database was queried by this pass, and all live values are the ones supplied with the
task and treated as given.*
