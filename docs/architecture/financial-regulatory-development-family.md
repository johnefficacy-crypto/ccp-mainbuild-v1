# Financial Regulatory & Development Institutions — product & data model

**Status:** PLANNING — architecture proposal, no code landed. Supersedes the
chat-only "Financial Regulatory Officers" plan and the earlier
`regulatory-officers-family-model.md` draft. Corrections here are grounded in a
direct read of the schema/backend (evidence cited inline as `path:line`) and in
the PR #953 checkpost review (owner dispositions, 2026-07-11).

Checklist lane: `docs/status/career-copilot-checklist.md` § "Financial
Regulatory & Development Institutions — Lane R".

**Scope boundary (owner-locked):** this workstream owns **regulatory/development
domain knowledge and domain-content rubrics only**. Generic aptitude
(Quantitative, Reasoning, general GA/current-affairs), the English-language
evaluator (objective and descriptive), and the Phase-I aptitude mock path are
owned by **separate workstreams** (see Lane GQR, Lane H) and appear here only as
external shared-subject dependencies — never as Lane R deliverables.

---

## 1. Decision & family naming

Model these as a single **Financial Regulatory & Development Institutions**
family. The earlier "Regulatory Officers" name was inaccurate: NABARD, SIDBI,
NHB, EXIM and NaBFID are development-finance institutions, not regulators.

The shared foundation is the business case — one aspirant prepares for several
of these exams on a single subscription — while stream/regulator layers preserve
eligibility and syllabus accuracy.

### Portfolio matrix

Core list is owner-specified; the light/index split for the remainder is a
proposed classification pending owner confirmation.

| Institution | Exam / streams | Type | Tier |
|---|---|---|---|
| RBI | Grade B — General, DEPR, DSIM | Regulator (central bank) | **Core** |
| SEBI | Grade A — General, Legal, IT, Research, Official Language, Engineering | Regulator | **Core** |
| NABARD | Grade A / Grade B — Generalist (RDBS) + specialist streams | Development finance | **Core** |
| IRDAI | Assistant Manager — Generalist, Actuarial, Finance, Law, IT, Research | Regulator | **Core** |
| PFRDA | Grade A — General, Finance & Accounts, IT, Research (Eco/Stats), Actuarial, Legal, Official Language | Regulator | **Core** |
| IFSCA | Grade A — streams *unverified* until advertisement ingested | Regulator | **Core** |
| SIDBI | Grade A / Assistant Manager — General + specialist | Development finance | **Core** |
| NHB | Assistant Manager (Generalist/specialist) | Development finance | Light — promote on open cycle |
| EXIM Bank | Management Trainee / specialist officer | Development finance | Light — promote on open cycle |
| NaBFID | Analyst / officer streams | Development finance | Light — promote on open cycle |
| NPS Trust | Officer / Grade cadres | Pension-sector body | Index-only (identity + notifications) |
| EPFO | APFC / SSA (Labour ministry, adjacent) | Provident-fund body | Index-only |
| ECGC | PO / specialist | Export-credit insurer | Index-only |
| IBBI | Grade A / research | Insolvency regulator | Index-only |

- **Core** — full identity, cycles, streams, eligibility, syllabus, PYQ, mocks.
- **Light** — identity + eligibility + cycles maintained; prep content authored
  only when a cycle opens; promoted to Core on demand.
- **Index-only** — track identity and notifications for discovery; no prep build
  until reclassified.

Per-exam accuracy chain (note: *paper* is an attribute, not an entity — the
schema has phases and sections only; `paper_name` is a column,
`205_english_writing_practice_schema.sql:142`):

```text
exam → cycle → [stream] → phase → section → syllabus
                                   └─ paper_name = attribute label
```

---

## 2. External shared-subject dependencies (NOT Lane R deliverables)

These are consumed, never owned, by this workstream:

| Shared area | Owning workstream | Lane R relationship |
|---|---|---|
| Quantitative aptitude, Reasoning | Lane GQR (aptitude) | Consume topic coverage; do not author |
| General awareness / generic current affairs | Lane GQR (GA/CA) | Consume; Lane R owns only *regulatory-domain* current affairs |
| English objective | English workstream | Consume |
| English descriptive evaluator | English Writing Practice (Lane H, migration 205 + EWP-2/2B) | Reuse the evaluator; do not fork it |
| Phase-I aptitude mock path | Mock Engine v2 | Consume; Lane R adds only stream-specific **domain** Paper-2 mocks |

Lane R **owns**: regulatory/development-institution domain knowledge (securities,
pension, insurance, IFSC, development-finance), regulatory-domain current affairs,
and **domain-content descriptive rubrics** (distinct from the English-grammar
rubric path).

---

## 3. Stream schema — complete normalized contract (P0)

A `stream_id` on sections alone cannot represent the stated chain, because
`exam_phases` owns duration/questions/marks/negative marking
(`029_exam_registry_cycles_phases.sql:50-67`), and the existing section
uniqueness key `(exam_phase_id, subject_id, section_label)` (`029:92`) rejects
the same subject/label across streams. Full contract (all additive; new
migration(s), never edits to merged 029):

```text
exam_streams(
  id, exam_id FK, stream_key text, name, is_active, metadata,
  unique(exam_id, stream_key))                         -- canonical stream identity

exam_cycle_streams(
  id, exam_cycle_id FK, stream_id FK,
  availability text  -- 'offered' | 'not_offered' | 'expected',
  vacancy_count int NULL, status, metadata,
  unique(exam_cycle_id, stream_id))                    -- per-cycle availability/activation

-- phase-level stream scoping: a phase may be common (stream_id NULL) or a
-- stream-specific variant carrying its own duration/marks/negative_marking.
exam_phases.stream_id  uuid NULL FK -> exam_streams     -- add column
  -> replace the two partial unique indexes (029:69-75) with stream-aware keys
     that COALESCE(stream_id, zero-uuid) so common and per-stream phases coexist.

-- section-level stream scoping
exam_phase_sections.stream_id  uuid NULL FK -> exam_streams   -- add column
  -> replace unique(exam_phase_id, subject_id, section_label) with
     unique(exam_phase_id, COALESCE(stream_id, zero-uuid), subject_id, section_label)

exam_topic_coverage.stream_id  uuid NULL FK -> exam_streams   -- optional, for
  stream-scoped high-yield coverage; NULL = applies to all streams
```

Migrate the existing loose `stream_key text` on
`exam_descriptive_requirements` (`205:136`) and `writing_prompts` to reference
`exam_streams.id` so there is one canonical representation, not two.

---

## 4. Eligibility — baseline vs current-cycle truth (P0)

Migration 110 defines `exam_eligibility_rules` as **exam-level baseline
eligibility**, explicitly separate from recruitment/vacancy eligibility
(`110_exam_eligibility_rules.sql:5-14`). The distinction must be preserved:

- **Baseline (stable) eligibility** -> `exam_eligibility_rules`. May carry an
  optional `stream_id` for stream-stable facts (e.g. SEBI Legal always needs
  LLB; IRDAI Law always needs LLB 60%). Extend the `rule_type` CHECK
  (`110:45-46`) via a **new** migration with: `discipline`, `min_percentage`,
  `certification`, `qualification_combination`, `stream_availability`. Add a
  `stream` dimension (not overloading category `scope`, `110:43-44`) and matching
  evaluator branches in `evaluator.py`, preserving the four-state
  eligible/conditional/not_eligible/unknown contract and knockout semantics.
- **Cycle / notification-specific eligibility** (percentages, experience,
  stream availability, professional-qualification cut-offs that change per
  advertisement) -> **do NOT write into baseline rows**. These live at the
  recruitment/vacancy layer already computed by `eligibility_runner`
  (`age_criteria` / `education_criteria` / `recruitment_question_requirements`)
  and/or a new cycle-scoped `exam_cycle_stream_eligibility` table keyed on
  `(exam_cycle_id, stream_id)`.

**Compass provenance rule:** the Regulatory Exam Compass shows two clearly
labelled bands — *baseline guidance* ("based on your profile you appear eligible
for SEBI General") sourced from `exam_eligibility_rules`, and *verified
current-cycle eligibility* ("for the open 2025 cycle") sourced from the
recruitment/cycle layer with its own source + verification date. Baseline is
never presented as cycle-confirmed.

**Status — A2 (CODE-FIXED, VALIDATION PENDING; live/browser proof pending):** the
current-cycle band is now real and trust-gated, not a placeholder. The evaluator's
additive `cycle` payload is verified-only (migration 261 trust gate via
`_load_verified_cycles`, filtering `reviewer_status='verified'`) and carries nested
per-cycle metadata (`cycle_name`/`year`/`notification_date`/`cutoff_date`/`source_url`/
`verified_at`/`status`/`streams[]`); `cycle_notification` age resolves on the verified
cycle's `notification_date`. `ExamStreamBreakdown.jsx` + `EligibleExamsCard.jsx` render
cycle name + notification/cutoff date, streams grouped eligible/conditional/
not_eligible/unknown with missing fields + reasons, the official source link +
verification date, and an explicit "No verified cycle eligibility available" empty
state. Unverified/absent cycles are dropped — the baseline band is never substituted
for the current-cycle band.

The current SEBI baseline collapses to graduation + age + Indian
(`110:171-178`) — materially insufficient for stream rules and must be corrected
under this contract.

---

## 5. Repo readiness — corrected

- **Descriptive-answer subsystem already exists (schema + runtime).** Migration
  205 (EWP-1) lands rubrics, prompts, `exam_descriptive_requirements`
  (paper_name/marks/duration/feedback policy/`stream_key`, `205:131-185`),
  immutable append-only answer history (`205:241-260`), evaluations with
  `human_review_status` (`205:265-285`), and mastery-evidence tiers incl.
  `descriptive_mock`/`production` (`205:499-532`). EWP-2 API + EWP-2B workers are
  MERGED (Lane H). **The descriptive workbench is not a from-scratch build.** New
  Lane R work = the **domain (non-English) rubric path** only; the grammar
  issue-type taxonomy (`205:308-312`) does not fit IRDAI ESI / Insurance &
  Management or SEBI Legal domain answers. All domain scoring stays in the
  `shadow -> live` mastery lifecycle (`205:715-769`); no new AI writes.
- **Shared stimuli AND media are first-class.** Text/table stimuli landed in
  migration 223; **migration 233 (`233_pyq_stimuli_media_assets.sql`) already
  lands media** — `document_asset_id`, `asset_locator`, `alt_text`, an integrity
  guard, CMS authoring, and the frontend renderer (`docs/architecture/pyq-media.md`
  slice 1). Genuinely deferred (later PR-11 slices, per that doc §Deferred): the
  asset **upload flow**, **bulk-importer** media support, **projection/snapshot
  wiring**, and **advanced answer runtimes/scorers** (MSQ, integer, descriptive).
- **Registry** supports cycles/phases/sections/marks/negative marking/durations
  (`029:31-93`), trust-gated topic coverage (`029:95-122`), and exam-level
  eligibility (`110`).
- **Regulatory recruitments are already Tier A** in the verification gateway
  (`recruitment_classifier.py:47-65`).

---

## 6. Recent exam analysis — evidence matrix

All prep content is subject to verified-only reads (nothing aspirant-visible
until `reviewer_status='verified'`). Facts below are **draft/unverified** until
the official notification/handout is ingested as a `document_assets` row and
reviewed; `document_id` is `pending` until ingestion. Retrieval date reflects the
research pass, not official confirmation.

| Exam | Cycle | Official source (locator) | Retrieved | reviewer_status | document_id |
|---|---|---|---|---|---|
| SEBI Grade A | 2025 | sebi.gov.in — advertisement + Phase I/II info handouts | 2026-07-11 | draft (unverified) | pending |
| PFRDA Grade A | 2025 | pfrda.org.in — Phase II info handout (28 Sep 2025) | 2026-07-11 | draft (unverified) | pending |
| IFSCA Grade A | latest | ifsca.gov.in — advertisement (dynamic page; PDF not yet ingested) | 2026-07-11 | **draft — blocked on PDF** | pending |
| IRDAI Assistant Manager | 2024 | irdai.gov.in — advertisement + Phase I/II details | 2026-07-11 | draft (unverified) | pending |
| RBI Grade B | 2025 | rbi.org.in — advertisement | 2026-07-11 | draft (unverified) | pending |
| NABARD Grade A/B | 2025 | nabard.org — advertisement | 2026-07-11 | draft (unverified) | pending |
| SIDBI Grade A | latest | sidbi.in — advertisement | 2026-07-11 | draft (unverified) | pending |

Analytical summary (to be confirmed against the ingested sources above):

- **SEBI Grade A 2025** — streams General/Legal/IT/Research/Official
  Language/Electrical & Civil Eng. Phase II: common 60-min English descriptive
  (essay/précis/comprehension) + stream Paper 2 (General = 100 MCQ/90 min);
  one-fourth negative on objective papers; stream-dependent eligibility.
- **PFRDA Grade A 2025** — 8 streams incl. Actuarial. Phase II: Paper 1 English
  descriptive (3 Q/100/60 min); Paper 2 stream (50 MCQ/100/40 min); General adds
  pension sector; one-fourth negative; paper + aggregate cut-offs.
- **IFSCA Grade A** — broad cross-regulatory remit; **stream eligibility,
  durations and syllabus remain unverified** pending the advertisement PDF.
- **IRDAI Assistant Manager 2024** — 6 streams. Phase I objective (160 Q/90 min,
  one-fourth negative); Phase II three descriptive papers (English; Economic &
  Social Issues impacting Insurance; Insurance & Management); Phase II:interview =
  85:15; stream-specific quals (Actuarial = grad 60% + 7 IAI papers; Law = LLB 60%).
- **RBI/NABARD/SIDBI** — patterns to be captured from the sources above before
  becoming plan-of-record content.

---

## 7. Common preparation structure

**Regulatory/Development Domain Core** — owned by Lane R:

```text
Economics (regulatory-relevant) · Finance & financial markets
Companies Act & corporate governance · Regulatory-domain current affairs
```

Delivered via existing `subjects`/`topics`/`exam_topic_coverage` + per-stream
section mapping (§3). Regulator deltas:

```text
SEBI   securities markets, intermediaries, securities regulation
PFRDA  NPS, pension products/intermediaries, retirement economics, pension regs
IFSCA  IFSC banking, capital markets, insurance, fund mgmt, payments, sust. finance
IRDAI  insurance principles/regulation, risk, solvency, products, intermediaries, ESI
RBI    monetary policy, banking regulation, DEPR/DSIM domain
NABARD/SIDBI  rural/development finance, priority sector, MSME finance
```

Generic Quant/Reasoning/English/GA are **external dependencies** (§2, Lane GQR /
Lane H), not authored here.

---

## 8. Aspirant support

Each item names its governance guardrail; **no item may add a new top-level
sidebar destination** unless it removes ≥2 (no-new-surface rule, locked
2026-06-21).

1. **Regulatory Exam Compass** — inside the existing Eligibility area. Two
   provenance bands per §4 (baseline vs current-cycle). Eligible/conditional/
   missing streams, cycles/windows, phase dates, pattern deltas, cross-exam
   overlap, last verified source.
2. **Shared-core Study OS plan** — deterministic planner; reuses mastered common
   topics across concurrent cycles. Domain delta owned here; generic subjects
   pulled from their workstreams. No new AI writes.
3. **Domain mock + descriptive** — stream-specific **domain** Paper-2 mocks
   (Lane R) on the Mock Engine v2 path (external). English descriptive reuses
   EWP; **new work = domain rubric path** only.
4. **Regulatory-domain current-affairs feed** — verified feed (circulars,
   regulations, consultation papers, annual/committee reports, enforcement),
   tagged regulator/date/exam/cycle/stream/topic/window/source-trust/plan-impact.
   Flows through the existing review lifecycle + Tier-A verification; reuses an
   existing surface; no unreviewed AI writes. Generic GA stays external (Lane GQR).
5. **PYQ intelligence** — reuses `pyq_*` + 223 stimuli + 233 media.
6. **Interview preparation** — regulator mandate/actions, stream technical bank,
   mock interview. Reused surface.
7. **Application & document tracker** — discipline, %/CGPA, professional quals,
   experience, category/EWS/PwBD docs, fee, call letters, shifts. Justifies the
   §4 eligibility extension. Reused surface.

---

## 9. Rollout

```text
R1 — Truth & eligibility (P0/P1)
  Classifier fix (below). Full stream contract (§3). Baseline vs cycle
  eligibility (§4). Core-tier identities/cycles/streams/sources/syllabus
  (IFSCA draft). Light/index tiers get identity + notifications only.
R2 — Aspirant utility
  Compass (Eligibility area), domain planner delta, regulatory-domain feed,
  application/document tracker — reused surfaces, verified data only.
R3 — Preparation
  Domain PYQ + stream Paper-2 domain mocks (reuse pyq_* + 223 + 233).
  Domain descriptive rubric path (new); English descriptive reused from EWP.
R4 — Adaptive
  Domain mock corrections, mastery-informed adaptation, multi-exam overlap,
  interview readiness.
```

### Classifier fix (P0, ship first)

`recruitment_classifier.py:60` — `("regulatory", ("sebi","irdai","pfrda","tra"))`.
`"tra"` is an unsafe substring (matches `extra`/`registration`/`arbitration`/
`administration`/`central`) -> false Tier-A. Replace with explicit `"trai"`; add
`"ifsca"`. RBI (`:52`), NABARD + SIDBI (`:53`) are already present — do not
re-add. Development-institution aliases (NHB, EXIM, NaBFID) and out-of-family
regulators (TRAI/IBBI/CCI) may be added for tiering but stay outside prep scope
except where the portfolio matrix (§1) lists them. Self-contained, no schema
change.

---

## 10. Invariants this plan must not break

- Verified-only reads; no pending/rejected leakage.
- Eligibility verdicts from the deterministic engine only — never AI/heuristics.
- Baseline vs notification eligibility kept separate (§4).
- No new AI writes (feed + domain scoring stay in review/shadow lifecycles).
- No new top-level sidebar destination unless it removes ≥2.
- Migrations immutable once merged; new stream tables / rule types / columns =
  new migrations.
- `exam_id` vs `recruitment_id` stays explicit.
- Lane R owns domain knowledge + domain rubrics only; generic aptitude, the
  English evaluator, and the aptitude mock path stay with their workstreams.
