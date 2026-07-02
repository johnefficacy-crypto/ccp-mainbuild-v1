# Applied vs Appeared Counts Gate — J3 sub-item

- Document type: J3 sub-slice implementation contract — candidate **applied** vs **appeared** counts for competition-pressure / vacancy analytics
- Status: **DRAFT — OPERATOR APPROVAL REQUIRED**
- Note: every item marked **LOCKED** below is a **PROPOSED lock** — nothing in this document is authoritative until operator approval. Agents must not treat draft text as approved policy.
- Date: 2026-07-02
- Parent track: `J3 — schema/domain redesign` (`docs/status/career-copilot-checklist.md`, J3 row: "Phase/category competition cutoffs, applied vs appeared counts, mixed-format PDF extraction, evidence-based coverage scoring").
- Sibling gate (cross-reference, non-overlapping): `docs/status/J3-Competition-Cutoffs-Gate-2026-07-02.md` — owns the **cutoffs/vacancy JSONB** redesign (`cutoff_trend`, `vacancy_by_category`, `vacancy_total`). **This gate does NOT touch those columns.** This gate owns exclusively the **applied vs appeared candidate counts** and their granularity, evidence model, and reviewer lifecycle. If the sibling gate is not yet drafted, the JSONB boundary in §B (PD-6) still holds: applied/appeared counts must not be encoded inside `vacancy_by_category` or any cutoff JSONB.
- Authority: `docs/architecture/domain-model.md` (entity canonicity); CLAUDE.md non-negotiable domain rules (verified-only reads, determinism, no new AI writes); structural template `docs/status/Topic-Prerequisite-Semantics-Gate-2026-07-01.md`.

---

## How to use this document

This gate **reconciles the existing implementation** — it does not design from scratch. Every section states a LOCKED decision or an exact specification. Items marked **OPERATOR DECISION REQUIRED** must be resolved by operator approval and not guessed.

**No implementation PR may be dispatched until this document is OPERATOR APPROVED.**

**Serial delivery rule (locked):** the applied/appeared slice touches the competition read path (`competition_context.py`, `competition.py`) shared with the sibling cutoffs gate. Implementation across the two J3 competition gates must be **one owner's sequential work** — no fan-out — because both edit the same read models and (potentially) the same migration slot.

---

## Section 0 — Actual implementation baseline

### 0.1 Table (`exam_competition_metrics`, migration 055)

The only place any applicant volume is stored today:

```sql
create table public.exam_competition_metrics (
  id uuid primary key default gen_random_uuid(),
  exam_id uuid not null references public.exams(id) on delete cascade,
  exam_cycle_id uuid references public.exam_cycles(id) on delete cascade,
  exam_phase_id uuid references public.exam_phases(id) on delete set null,

  vacancy_total integer check (vacancy_total is null or vacancy_total >= 0),
  vacancy_by_category jsonb not null default '{}'::jsonb,
  applicant_count integer check (applicant_count is null or applicant_count >= 0),
  selection_ratio numeric(8,6) check (... 0..1),

  cutoff_trend jsonb not null default '{}'::jsonb,
  difficulty_trend jsonb not null default '{}'::jsonb,
  competition_pressure_score numeric(5,2) check (... 0..100),

  source_basis text not null default 'manual'
    check (source_basis in ('manual','official','reviewed_analysis','derived','model_generated')),
  confidence_score numeric(4,3) not null default 0 check (0..1),
  evidence_count integer not null default 0 check (>= 0),
  reviewer_status text not null default 'draft'
    check (reviewer_status in ('draft','pending_review','reviewed','locked','rejected')),
  reviewed_by uuid references public.profiles(id) on delete set null,
  reviewed_at timestamptz,
  reviewer_notes text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

**Findings:**
- There is exactly **one** volume integer: `applicant_count`. Its name and check say nothing about whether it means **applied** (registered / form submitted) or **appeared** (actually sat the exam). It is semantically overloaded and undocumented.
- There is **no `appeared_count`** column anywhere in the schema.
- Category / reservation breakdown exists **only for vacancy** (`vacancy_by_category` JSONB). There is **no applied-by-category or appeared-by-category** representation.
- `selection_ratio` (0..1) exists but its denominator is undefined — it could be vacancy/applied or vacancy/appeared. This ambiguity is a direct consequence of the missing applied-vs-appeared distinction.
- Granularity available on the row: `exam_id` (required) + `exam_cycle_id` (nullable) + `exam_phase_id` (nullable). So the table can already be scoped to exam, cycle, or phase, but has no category axis for counts.
- Lifecycle already present: full `reviewer_status` five-state model + `reviewed_by/at`, `reviewer_notes`, `source_basis`, `confidence_score`, `evidence_count`.

### 0.2 Granularity context (migration 030)

- `exam_cycles` (`exam_id`, `year`, `cycle_name`, status, dates) — per-attempt cycle identity.
- `exam_phases` (`exam_id`, `exam_cycle_id?`, `phase_name`, `phase_order`, ...) — Prelims / Mains / Interview etc. "Appeared" is fundamentally **per phase** (candidates appear for Prelims, a subset appear for Mains).
- No category/reservation dimension table exists for candidate volumes; category appears only as free-form JSONB keys inside `vacancy_by_category`.

### 0.3 RLS (migration 057)

- `exam_competition_metrics` RLS: authenticated read allowed only when `reviewer_status in ('reviewed','locked')` OR admin; `*_admin_all` for admin write. Service role bypasses and applies authoritative filtering in `app/study_os/*_context.py`.

### 0.4 Read/write code paths

- `app/backend/app/exam_intelligence/competition.py:99,139,141,224` — selects and surfaces `applicant_count`; builds vacancy trend points from `vacancy_total` only (no applicant/appeared trend).
- `app/backend/app/study_os/competition_context.py:38,131,155,169-177` — planner-facing competition pressure read: pulls `applicant_count`, `selection_ratio`; `_pressure_reason` phrases pressure from `selection_ratio`. Defaults `applicant_count`/`selection_ratio` to `None` on the safe path.
- No code writes or reads any "appeared" concept — it does not exist.

---

## Section A — Gaps this gate closes

| # | Gap | Consequence |
|---|---|---|
| G-1 | `applicant_count` is semantically overloaded (applied vs appeared undefined) | Competition-pressure math and any surfaced ratio are ambiguous; two operators can enter different meanings into the same column. |
| G-2 | No `appeared_count` at all | Cannot compute true appearance-based competition (vacancy ÷ appeared), the metric aspirants actually care about; drop-off (applied→appeared) is unrepresentable. |
| G-3 | No category/reservation axis for candidate counts | Reservation-aware competition (e.g. OBC vacancy ÷ OBC appeared) is impossible; only vacancy has a category JSONB. |
| G-4 | `selection_ratio` denominator undefined | Ratio cannot be trusted or recomputed deterministically. |
| G-5 | No evidence/source-basis granularity for counts | Applied counts (official notification) and appeared counts (post-exam official statistics) have different provenance and arrive at different times; a single row's `source_basis` cannot express both. |

---

## Section B — Semantic & data-model decisions (LOCKED unless flagged)

| ID | Decision |
|---|---|
| PD-1 | **Entity canonicity (LOCKED).** All applied/appeared rows reference `exam_id references public.exams(id)` and optionally `exam_cycle_id references public.exam_cycles(id)` / `exam_phase_id references public.exam_phases(id)`. **Never `recruitment_id`.** Candidate volumes are exam-intelligence data, canonical to `public.exams` per `domain-model.md`. Applicant counts on a specific *notification* (recruitments/posts application tracking) are a separate concern and out of scope. |
| PD-2 | **Applied vs Appeared are distinct, non-derivable facts (LOCKED).** "Applied" = candidates who registered / submitted the form for a cycle. "Appeared" = candidates who actually sat a given phase. Appeared is never inferred from applied by heuristic (Determinism > Heuristics); each is an observed, evidenced count or is `null`. |
| PD-3 | **Appeared is phase-scoped; Applied is cycle-scoped (LOCKED semantics).** A candidate applies once per cycle but appears per phase. Therefore an appeared count is only meaningful with an `exam_phase_id`; an applied count is meaningful at cycle level (phase optional/null). Enforcement of this shape is an **OPERATOR DECISION** — see PD-7. |
| PD-4 | **Category / reservation axis (OPERATOR DECISION REQUIRED — see OD-1).** Whether counts are stored per reservation category or only as totals is not decided here. Do not guess. |
| PD-5 | **Table vs extend (OPERATOR DECISION REQUIRED — see OD-2).** Whether to add typed columns to `exam_competition_metrics` or create a dedicated `exam_candidate_counts` table depends on the category-axis decision (PD-4). Do not guess. |
| PD-6 | **JSONB boundary (LOCKED).** Applied/appeared counts must NOT be encoded inside `vacancy_by_category`, `cutoff_trend`, or any JSONB owned by the sibling cutoffs gate. Counts are first-class typed data (typed columns or a typed child table), not opaque JSONB — so they are checkable (`>= 0`), indexable, and reviewable. |
| PD-7 | **`applicant_count` disposition — OPERATOR DECISION REQUIRED (corrected per checkpost).** The column is semantically overloaded/unknown (G-1), so it **must NOT be blanket-relabelled as "applied"** — that would manufacture certainty and can corrupt competition ratios. LOCKED only: the column is NOT deleted (immutability, no data loss) and is deprecated-in-place. The disposition of its values is an auditable operator choice (see OD-6): (a) preserve every legacy value as `legacy_unknown` and require review before it feeds any ratio; (b) backfill to `applied` ONLY rows with explicit provenance proving "applied", leaving the rest null/unknown; (c) quarantine ambiguous rows and leave the new explicit fields null. **Ambiguous rows must never be silently converted** (acceptance test F.4). |
| PD-8 | **`selection_ratio` (LOCKED).** Once explicit counts exist, `selection_ratio` becomes a derived, display-only convenience whose denominator MUST be documented (vacancy ÷ appeared preferred where appeared is known, else vacancy ÷ applied). The engine does not persist a new derived ratio without recording which denominator was used. No new AI/heuristic derivation. |

---

## Section C — Evidence & reviewer lifecycle (LOCKED)

- **Reviewer lifecycle reused unchanged:** five-state `reviewer_status` (`draft → pending_review → reviewed → locked`, with `rejected`), mirroring `exam_competition_metrics` / `exam_topic_coverage`. No new state machine is invented.
- **Verified-only reads (PROPOSED LOCK, CLAUDE.md).** All aspirant/planner-facing reads of applied/appeared counts filter to `reviewer_status in ('reviewed','locked')` — never `draft`/`pending_review`/`rejected`. **Correction (checkpost):** the competition read path is reviewed+locked with **locked preferred** (`competition_context.py::_READABLE_STATUSES = ("locked","reviewed")`), NOT locked-only; AGENTS.md locks the Study OS copy as "reviewed or locked rows feed the planner; locked preferred." This gate PRESERVES that contract — applied/appeared reads follow the same reviewed+locked (locked-preferred) rule. It does NOT redefine planner reads to locked-only; any such change would be a separate OD with the runtime/UI migration.
- **Source basis / provenance (LOCKED).** Each count carries `source_basis` from the existing constrained set (`manual`,`official`,`reviewed_analysis`,`derived`,`model_generated`) plus `confidence_score` and `evidence_count`, so applied (typically `official` at notification) and appeared (typically `official` post-result) can each state their own provenance. If applied and appeared live on the same row (PD-5 = extend), a **per-count source basis is required** — a single row-level `source_basis` cannot honestly describe two facts from different sources at different times; this is a decisive input to OD-2.
- **No AI writes (LOCKED).** No pipeline may write appeared/applied counts as `model_generated` into a reviewed/locked state without passing the human review lifecycle. `model_generated` rows start `draft`.

---

## Section D — Migration decision (LOCKED shape; specifics gated on OD-1/OD-2)

- A single forward migration. **Migration number:** pick the next free slot at implementation time (latest landed is `209`; do not hardcode — coordinate with the sibling J3 cutoffs gate to avoid a contended slot).
- **If OD-2 = extend `exam_competition_metrics`:** add typed nullable columns `applied_count integer check (>= 0)`, `appeared_count integer check (>= 0)`, `applied_source_basis text`, `appeared_source_basis text` (+ per-count evidence if approved). Constraint that `appeared_count` requires `exam_phase_id is not null` (per PD-3, subject to OD-3).
- **If OD-2 = new table `exam_candidate_counts`:** `id`, `exam_id` (not null), `exam_cycle_id`, `exam_phase_id`, `count_type text check (count_type in ('applied','appeared'))`, `reservation_category text` (nullable; per OD-1), `count_value integer check (>= 0)`, full `source_basis`/`confidence_score`/`evidence_count`, full reviewer-lifecycle columns (`reviewer_status`, `reviewed_by/at`, `reviewer_notes`), `created_at`/`updated_at`. Unique index over `(exam_id, exam_cycle_id, exam_phase_id, count_type, reservation_category)` with the null-handling partial-index pattern used by `exam_topic_coverage`. This is the recommended option if OD-1 = per-category (avoids JSONB and lets each count be independently reviewed).
- **Backfill (per the OD-6 disposition chosen for PD-7 — NOT a blanket "applied" relabel):** backfill must record: pre-migration non-null `applicant_count` row count; count converted vs. count left `legacy_unknown`/null; zero rows lost; competition-pressure read output preserved for a representative exam; and an assertion that no ambiguous (no-provenance) row was written as `applied`.
- **RLS (LOCKED).** If a new table: enable RLS and add the verified-only read policy (`reviewer_status in ('reviewed','locked')` OR admin) + admin-all write policy, mirroring migration 057. **Verify with `SELECT * FROM pg_policies WHERE tablename='<name>'` before marking complete** (migration discipline). Every new table needs an RLS policy.
- Migrations immutable once merged; do not edit 055.

---

## Section E — OPERATOR DECISION REQUIRED

| ID | Decision needed | Why it cannot be guessed |
|---|---|---|
| **OD-1** | **Category/reservation granularity of counts.** Options: (a) totals only (applied/appeared as single integers); (b) per reservation category (General/OBC/SC/ST/EWS/PwD/…). | Drives whether counts are scalar columns or a typed child table with a `reservation_category` axis. Reservation-aware competition is a stated product value ("category competition"), but per-category official appeared data is often unavailable — an operator/product call, not a technical default. |
| **OD-2** | **Extend `exam_competition_metrics` vs new `exam_candidate_counts` table.** | Depends on OD-1 and on §C provenance: two facts (applied/appeared) with different sources at different times argue for a typed child table; totals-only argues for two columns. Structural, entity-shaping decision. |
| **OD-3** | **Enforce PD-3 shape at the DB level?** i.e. hard `CHECK` that `appeared` rows require `exam_phase_id`, and `applied` at cycle level. | Some exams publish appeared counts only at cycle level (no phase split). Hard-enforcing may reject legitimate real-world data. Operator must confirm the phase-mandatory rule vs advisory. |
| **OD-4** | **Reservation category vocabulary/source of truth**, if OD-1 = per-category — free-text vs a constrained enum vs an existing categories reference table. | Affects checkability and cross-exam comparability; must align with the eligibility engine's category vocabulary rather than invent a parallel one. |
| **OD-5** | **Does any planner/pressure consumer switch to the new counts on landing, or is this schema-only (data captured, read paths unchanged until a later slice)?** | Changing `competition_context.py` pressure math is a behavior change to user-facing analytics; operator must approve scope (schema-first capture vs immediate consumption). |
| **OD-6** | **Legacy `applicant_count` disposition (PD-7):** (a) preserve all as `legacy_unknown` + require review; (b) convert to `applied` ONLY rows with explicit provenance, rest null; (c) quarantine ambiguous rows, new fields null. | The column is semantically unknown; blanket relabelling to `applied` manufactures certainty and can corrupt ratios. Must be auditable; ambiguous rows never silently converted. |

---

## Section F — Acceptance tests

### F.1 Entity canonicity & shape
```
[ ] every applied/appeared row references exam_id (public.exams); no recruitment_id column exists
[ ] appeared rows carry exam_phase_id (per PD-3 / OD-3 outcome); applied rows valid at cycle level
[ ] count_value / *_count rejects negatives (>= 0 check)
[ ] applied and appeared are independently storable (neither derived from the other)
```
### F.2 Category axis (per OD-1 outcome)
```
[ ] if per-category: same (exam,cycle,phase,count_type,category) cannot be duplicated (unique index)
[ ] if totals-only: no category column exists; counts not smuggled into vacancy_by_category JSONB (PD-6)
```
### F.3 Lifecycle & verified-only reads
```
[ ] draft/pending_review/rejected counts never appear in aspirant/planner reads
[ ] reviewed/locked counts are readable; RLS enforces it (non-admin sees only reviewed/locked)
[ ] model_generated counts start in draft; cannot land reviewed/locked without human review
[ ] each count records source_basis + confidence_score + evidence_count (per-count if same-row model)
```
### F.4 Migration & backfill
```
[ ] legacy applicant_count handled per the chosen OD-6 disposition; pre/post counts recorded; zero rows lost
[ ] ambiguous (no-provenance) legacy rows are NOT silently converted to `applied` (asserted)
[ ] competition-pressure read output preserved for a representative exam post-migration
[ ] new table (if chosen) has RLS verified via pg_policies before completion
[ ] selection_ratio, where recomputed, records its denominator (vacancy÷appeared or ÷applied)
```
### F.5 Read paths
```
[ ] competition.py / competition_context.py read explicit fields (not the overloaded applicant_count) after migration
[ ] scope of behavior change matches OD-5 (schema-only vs consuming)
```

---

## Section G — Files to change (on approval)

| File | Change |
|---|---|
| `app/supabase/migrations/<next>_applied_vs_appeared_counts.sql` | Typed columns OR `exam_candidate_counts` table (per OD-2) + constraints + indexes + backfill (per PD-7/§D) + RLS/grants (per OD-1). Pick next free migration slot; coordinate with sibling J3 cutoffs gate. |
| `app/backend/app/exam_intelligence/competition.py` | Read/surface explicit applied + appeared (currently only `applicant_count`, `vacancy_total`); add appeared trend if OD-5 = consume. |
| `app/backend/app/study_os/competition_context.py` | Migrate pressure read off overloaded `applicant_count`; document `selection_ratio` denominator (PD-8); scope per OD-5. |
| admin CMS / manage endpoints (`app/backend/app/api/admin_exam_intel_cms.py` and/or manage router) | Editors + review lifecycle for applied/appeared counts (per-count source basis). |
| backend + frontend tests | Section F. |
| `docs/status/career-copilot-checklist.md` | J3 applied-vs-appeared sub-row status update. |

---

## Appendix A — Code evidence index

- `app/supabase/migrations/055_exam_competition_metrics.sql:8-40` — sole applicant volume column `applicant_count` (overloaded), `vacancy_by_category` JSONB, `selection_ratio`, full reviewer lifecycle + `source_basis`/`confidence_score`/`evidence_count`. No `appeared` column.
- `app/supabase/migrations/057_competition_policy_rls.sql:11-49` — verified-only read RLS (`reviewer_status in ('reviewed','locked')` OR admin) + admin-all write.
- `app/supabase/migrations/030_exam_registry_cycles_phases.sql:31-75` — `exam_cycles`, `exam_phases` (granularity anchors; appeared is inherently per-phase).
- `app/backend/app/exam_intelligence/competition.py:99,139,141,224-225` — selects/surfaces `applicant_count`; vacancy-only trend.
- `app/backend/app/study_os/competition_context.py:38,131,155,169-177` — pressure read consumes `applicant_count` + `selection_ratio`; `_pressure_reason` phrasing; safe-null defaults.
- `docs/status/career-copilot-checklist.md:234,235,282` — J3 row and DEFERRED — CONTRACT-FIRST competition-metrics decision blocker.

---

*Status: DRAFT — OPERATOR APPROVAL REQUIRED. No implementation PR may be dispatched until this gate is OPERATOR APPROVED. Blocking operator decisions: OD-1 (category granularity), OD-2 (extend vs new table), OD-3 (phase-mandatory enforcement), OD-4 (category vocabulary), OD-5 (consume now vs schema-first), OD-6 (legacy applicant_count disposition). Cross-references the sibling J3 cutoffs/vacancy-JSONB gate; JSONB boundary (PD-6) prevents overlap.*
</content>
</invoke>
