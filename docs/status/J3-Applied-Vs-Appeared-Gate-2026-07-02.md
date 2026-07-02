# Applied vs Appeared Counts Gate — J3 sub-item

- Document type: J3 sub-slice implementation contract — candidate **applied** vs **appeared** counts for competition-pressure / vacancy analytics
- Status: **AMENDED TO MATCH APPROVED RESOLUTIONS — OPERATOR SIGN-OFF PENDING.** Body reconciled with docs/status/J3-OD-Resolutions-Locked-2026-07-02.md (2026-07-02). Implementation remains BLOCKED until explicit operator approval is recorded on the PR.
- Date: 2026-07-02
- Parent track: `J3 — schema/domain redesign` (`docs/status/career-copilot-checklist.md`, J3 row: "Phase/category competition cutoffs, applied vs appeared counts, mixed-format PDF extraction, evidence-based coverage scoring").
- Sibling gate (cross-reference, non-overlapping): `docs/status/J3-Competition-Cutoffs-Gate-2026-07-02.md` — owns the **cutoffs/vacancy JSONB** redesign (`cutoff_trend`, `vacancy_by_category`, `vacancy_total`). **This gate does NOT touch those columns.** This gate owns exclusively the **applied vs appeared candidate counts** and their granularity, evidence model, and reviewer lifecycle. If the sibling gate is not yet drafted, the JSONB boundary in §B (PD-6) still holds: applied/appeared counts must not be encoded inside `vacancy_by_category` or any cutoff JSONB.
- Authority: `docs/architecture/domain-model.md` (entity canonicity); CLAUDE.md non-negotiable domain rules (verified-only reads, determinism, no new AI writes); structural template `docs/status/Topic-Prerequisite-Semantics-Gate-2026-07-01.md`.

---

## How to use this document

This gate **reconciles the existing implementation** — it does not design from scratch. Every section states a LOCKED decision or an exact specification. The body has been reconciled with the approved resolutions in `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md`; all former `OPERATOR DECISION REQUIRED` items are resolved (Section E).

**Implementation is PR 2 in `docs/status/J3-Implementation-Checklist-2026-07-02.md` (branches from merged PR 1). Dispatch remains blocked ONLY on explicit operator sign-off recorded on the PR.**

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

## Section B — Semantic & data-model decisions (all LOCKED — reconciled with the approved resolutions)

| ID | Decision |
|---|---|
| PD-1 | **Entity canonicity (LOCKED).** All applied/appeared rows reference `exam_id references public.exams(id)` and optionally `exam_cycle_id references public.exam_cycles(id)` / `exam_phase_id references public.exam_phases(id)`. **Never `recruitment_id`.** Candidate volumes are exam-intelligence data, canonical to `public.exams` per `domain-model.md`. Applicant counts on a specific *notification* (recruitments/posts application tracking) are a separate concern and out of scope. |
| PD-2 | **Applied vs Appeared are distinct, non-derivable facts (LOCKED).** "Applied" = candidates who registered / submitted the form for a cycle. "Appeared" = candidates who actually sat a given phase. Appeared is never inferred from applied by heuristic (Determinism > Heuristics); each is an observed, evidenced count or is `null`. |
| PD-3 | **Scope shape (LOCKED per OD-3).** `applied` is **always cycle-scoped** (`scope_kind='cycle'`, `exam_phase_id IS NULL`). `appeared` is **either** phase-scoped (`scope_kind='phase'`, `exam_phase_id` set) **or** an explicitly-labelled cycle aggregate (`scope_kind='cycle'`, `exam_phase_id IS NULL`) for authorities that publish only aggregate appearance data. `exam_cycle_id` is **always required**. `scope_kind ∈ {cycle, phase}` is a constrained CHECK, and a write validator confirms the phase belongs to the same exam **and** cycle. |
| PD-4 | **Category / reservation axis (LOCKED per OD-1 + OD-4).** Support **both totals and optional per-category** counts: `reservation_category_id = NULL` means the official total; category rows are captured only when official data exists — supported, never mandatory. The category axis is a **FK to the shared `reservation_categories` taxonomy + aliases** (resolution §6, created in the Competition PR) — not free text, not a PG enum. |
| PD-5 | **Table vs extend (LOCKED per OD-2).** New typed **`exam_candidate_counts` table** — not two more nullable columns on the overloaded competition row. Applied and appeared arrive at different times with independent evidence and lifecycles. Additionally (OD-5): APIs **consume the new reviewed/locked counts immediately**, with ratio denominator preference **appeared → applied → null**; this PR must **never alter `competition_pressure_score`** itself — only count display and the pressure explanation text change (§1.2 PR-2 atomic switch). |
| PD-6 | **JSONB boundary (LOCKED).** Applied/appeared counts must NOT be encoded inside `vacancy_by_category`, `cutoff_trend`, or any JSONB owned by the sibling cutoffs gate. Counts are first-class typed data (typed columns or a typed child table), not opaque JSONB — so they are checkable (`>= 0`), indexable, and reviewable. |
| PD-7 | **`applicant_count` disposition (LOCKED per OD-6 — Option B).** The column is NOT deleted (immutability, no data loss) and is deprecated-in-place; it is never blanket-relabelled as "applied". Migrate only rows whose evidence **explicitly proves** the value means "applied". Preserve all other `applicant_count` values as **legacy unknown** and exclude them from ratios. Record converted / unknown / zero-loss counts in migration evidence. **Ambiguous rows are never silently converted** (acceptance test F.4). |
| PD-8 | **Ratio derivation (LOCKED per OD-5 / resolution §1.2).** `selection_ratio` is deprecated in place (PR 1); PR 2 performs the **atomic switch** of ratio derivation and **all** ratio consumers together, with denominator preference **appeared → applied → null** using reviewed/locked counts only. Only a provenance-proven denominator produces a non-null `selection_rate`; `ratio_denominator` records which was used (`"appeared"` \| `"applied"` \| null). `competition_pressure_score` is never altered by this PR. No new AI/heuristic derivation. |

---

## Section C — Evidence & reviewer lifecycle (LOCKED)

- **Reviewer lifecycle reused unchanged:** five-state `reviewer_status` (`draft → pending_review → reviewed → locked`, with `rejected`), mirroring `exam_competition_metrics` / `exam_topic_coverage`. No new state machine is invented.
- **Verified-only reads (LOCKED, CLAUDE.md).** All aspirant/planner-facing reads of applied/appeared counts filter to `reviewer_status in ('reviewed','locked')` — never `draft`/`pending_review`/`rejected`. **Correction (checkpost):** the competition read path is reviewed+locked with **locked preferred** (`competition_context.py::_READABLE_STATUSES = ("locked","reviewed")`), NOT locked-only; AGENTS.md locks the Study OS copy as "reviewed or locked rows feed the planner; locked preferred." This gate PRESERVES that contract — applied/appeared reads follow the same reviewed+locked (locked-preferred) rule. It does NOT redefine planner reads to locked-only; any such change would be a separate OD with the runtime/UI migration.
- **Source basis / provenance (LOCKED).** Each count carries `source_basis` from the existing constrained set (`manual`,`official`,`reviewed_analysis`,`derived`,`model_generated`) plus `confidence_score` and a **derived** `evidence_count` (count of child evidence rows), so applied (typically `official` at notification) and appeared (typically `official` post-result) each state their own provenance. Because OD-2 locks a **separate `exam_candidate_counts` row per count**, every count is its own claim with its own lifecycle and evidence — the per-count-provenance concern that argued against the extend option is resolved structurally. `reviewed_analysis` is never acceptable as the sole primary evidence for official counts (resolution §7).
- **No AI writes (LOCKED).** No pipeline may write appeared/applied counts as `model_generated` into a reviewed/locked state without passing the human review lifecycle. `model_generated` rows start `draft`.

---

## Section D — Migration decision (LOCKED per resolution §2/§2.1/§3/§4.1/§6)

- A single forward migration in **PR 2** (branches from merged PR 1, which lands `reservation_categories` and the two-lane competition model). **Migration number:** resolved from the live `schema_migrations` ledger at implementation time — never inferred from filenames; coordinate with the sibling J3 cutoffs gate.
- **New table `exam_candidate_counts` (LOCKED — the extend option is rejected per OD-2):**
  - Identity/scope: `id`, `exam_id` (not null, FK `public.exams`), `exam_cycle_id` (**not null** — always required), `exam_phase_id` (nullable), `scope_kind text check (scope_kind in ('cycle','phase'))`, `count_type text check (count_type in ('applied','appeared'))`.
  - Shape CHECKs per OD-3: `applied` ⇒ `scope_kind='cycle'` and `exam_phase_id IS NULL`; `appeared` ⇒ (`scope_kind='phase'` and `exam_phase_id IS NOT NULL`) or (`scope_kind='cycle'` and `exam_phase_id IS NULL`, explicitly-labelled cycle aggregate). Write validator confirms the phase belongs to the same exam and cycle.
  - Category axis: `reservation_category_id uuid references public.reservation_categories(id)` (nullable = official total) — the shared taxonomy from resolution §6, NOT free text.
  - Value + provenance: `count_value integer check (count_value >= 0)`, `source_basis`, `confidence_score`; `evidence_count` **derived** by counting child evidence rows.
  - Lifecycle + two-lane revision model (§2): full `reviewer_status` five-state columns plus `version_no`, `supersedes_id` (self-FK, no self-reference), `superseded_at`, `is_current_published`; `*_current_published_state` / `*_superseded_not_current` CHECKs; promotion RPC + published-parent UPDATE/DELETE guards (content columns frozen once published).
  - **Uniqueness (NULL-safe, §2.1)** — not an ordinary nullable unique tuple: partial unique indexes with **`NULLS NOT DISTINCT`** over `(exam_id, exam_cycle_id, scope_kind, exam_phase_id, count_type, reservation_category_id)` — one for the current-published lane (`where is_current_published`) and one for the working lane (`where reviewer_status in ('draft','pending_review') and superseded_at is null`); fallback `coalesce(col, zero-uuid)` expression indexes if the target PG lacks `NULLS NOT DISTINCT`. Per-scope `version_no` uniqueness (`NULLS NOT DISTINCT` over scope tuple + `version_no`) and RPC/trigger same-scope-ancestry rule apply.
- **Evidence child table `exam_candidate_count_evidence` (§4.1):** **no `claim_field`, no `reservation_category_id`** — the parent row IS the single claim and carries the category. `claim_value` snapshots `{count_type, scope_kind, exam_phase_id, reservation_category_code, count_value}`; server-computed unique `evidence_key`; append-only; INSERT/UPDATE/DELETE trigger-blocked once the parent is published; promotion requires ≥1 qualifying primary evidence whose `claim_value` matches the current parent value/scope/category; §7 source-trust validation.
- **Backfill (OD-6 Option B):** convert to `applied` only rows with explicit provenance proving "applied"; all others preserved as legacy unknown and excluded from ratios; record pre-migration non-null `applicant_count` count, converted vs unknown counts, zero-loss assertion, competition-pressure read output preserved for a representative exam, and an assertion that no ambiguous row was written as `applied`.
- **RLS (LOCKED, exact predicate per §3):** enable RLS on `exam_candidate_counts`; non-admin read requires `reviewer_status IN ('reviewed','locked')` (mirrors migration 057's predicate) but the admin check uses **app-metadata roles, NOT the deprecated `profiles.is_admin`**. Writes are **service-role only** through permission-gated FastAPI routes. Evidence table: RLS enabled, no anon/authenticated direct access. **Verify with `SELECT * FROM pg_policies WHERE tablename='<name>'` before marking complete.**
- Migrations immutable once merged; do not edit 055.

---

## Section E — OPERATOR DECISIONS — RESOLVED (pending sign-off)

Resolved 2026-07-02 per docs/status/J3-OD-Resolutions-Locked-2026-07-02.md §3. Full SQL and cross-cutting model live in that resolution doc. Implementation dispatch remains blocked until explicit operator sign-off is recorded on the PR.

| ID | Resolution |
|---|---|
| **OD-1** | Support **both totals and optional per-category** counts. `reservation_category_id = NULL` means the official total; category rows are captured **only when official data exists**. Category detail is supported but never mandatory. |
| **OD-2** | New typed **`exam_candidate_counts` table** (not two more nullable fields on the overloaded competition row). Applied and appeared arrive at different times with independent evidence and lifecycles. |
| **OD-3** | Add **`scope_kind ∈ {cycle, phase}`** (constrained CHECK). `exam_cycle_id` is **always required**. `applied` → `scope_kind='cycle'`, `exam_phase_id IS NULL`. `appeared` → either `scope_kind='phase'` with `exam_phase_id` set, **or** an explicitly-labelled cycle aggregate (`scope_kind='cycle'`, `exam_phase_id IS NULL`) for authorities that publish only aggregate appearance data. A write validator confirms the phase belongs to the same exam **and** cycle. |
| **OD-4** | Reuse the **shared `reservation_categories` vocabulary + aliases** (§6 of the resolution doc) via FK — not free text, not a hard-to-extend PG enum. |
| **OD-5** | **Consume the new reviewed/locked counts immediately** in APIs (prefer `appeared`, then `applied`, else return no ratio). Do **NOT** let this PR alter `competition_pressure_score` itself — only fix count display and the pressure **explanation** text. The §1.2 transitional contract makes PR 2 the point where ratio derivation and all ratio consumers switch atomically. |
| **OD-6** | **Option B** — migrate only rows whose evidence explicitly proves the value means "applied." Preserve all other `applicant_count` values as **legacy unknown** and exclude them from ratios. Record converted / unknown / zero-loss counts in migration evidence. Ambiguous rows are **never** silently converted. |

### Resolved additions folded in

From docs/status/J3-OD-Resolutions-Locked-2026-07-02.md (§2, §2.1, §3, §4.1, §6, §7, §1.2 — see that doc for full SQL):

- **New typed `exam_candidate_counts` table (OD-2)** — first-class typed counts, not extra nullable columns on `exam_competition_metrics`; applied and appeared carry independent evidence and lifecycles.
- **`scope_kind ∈ {cycle, phase}` (OD-3)** — constrained CHECK plus the phase/cycle shape CHECK (`applied` → cycle/`exam_phase_id IS NULL`; `appeared` → phase with `exam_phase_id`, or an explicit cycle aggregate) and a **write validator** confirming the phase belongs to the same exam and cycle.
- **Shared `reservation_categories` FK (OD-4 / §6)** — `exam_candidate_counts.reservation_category_id` and `exam_candidate_count_evidence` (via parent) reference the shared taxonomy + aliases created in the Competition PR; no free text, no parallel enum.
- **Two-lane revision model + NULL-safe uniqueness (§2 / §2.1)** — `exam_candidate_counts` uses the same one-current-published / at-most-one-current-working lane model (`version_no`, `supersedes_id`, `superseded_at`, `is_current_published`). Lanes enforced by partial unique indexes with **`NULLS NOT DISTINCT`** over `(exam_id, exam_cycle_id, scope_kind, exam_phase_id, count_type, reservation_category_id)` (fallback: `coalesce(col, zero-uuid)` expression indexes on PG < 15), because `exam_phase_id` and `reservation_category_id` are legitimately NULL within a lane. Same `*_current_published_state` / `*_superseded_not_current` CHECKs, `version_no > 0`, self-FK `supersedes_id` with no self-reference, per-scope `version_no` uniqueness, and RPC/trigger same-scope-ancestry rule apply.
- **`exam_candidate_count_evidence` (§4.1)** — first-class evidence table with **no `claim_field`** and **no `reservation_category_id`** (the parent row IS the single claim; parent carries the category). Append-only; `claim_value` snapshots the exact fact (`{count_type, scope_kind, exam_phase_id, reservation_category_code, count_value}`); server-computed `evidence_key`; `evidence_count` derived by counting child rows. **Immutability / published-parent guards:** INSERT/UPDATE/DELETE trigger-blocked once the parent is published; published-parent UPDATE freezes content columns and published-parent DELETE is trigger-blocked (§2). Do NOT attach applied/appeared facts to the generic `exam_competition_metric_evidence` row.
- **Promotion comparison (§4.1)** — an `appeared`/`applied` count promotes only when ≥1 qualifying **primary** evidence row exists whose `claim_value.count_value` equals the parent `count_value` and whose category/scope fields match; stale evidence does not qualify. `reviewed_analysis` is not acceptable as the sole primary evidence for official counts (§7).
- **Exact RLS reviewed/locked read predicate (§3)** — five-state `reviewer_status` vocabulary matching `exam_competition_metrics`; non-admin reads require `reviewer_status IN ('reviewed','locked')` (RLS mirrors migration 057's predicate) but the admin check uses **app-metadata roles, NOT the deprecated `profiles.is_admin`**. Evidence tables: RLS enabled, no anon/authenticated direct access, service-role permission-gated routes only. This supersedes any migration-057-style `profiles.is_admin` policy referenced in Section D.
- **§1.2 PR-2 atomic ratio switch** — PR 2 introduces `exam_candidate_counts`, then in the same PR switches ratio derivation and **all** ratio consumers together: denominator preference **appeared → applied → null** (reviewed/locked counts only). Only rows with a provenance-proven denominator produce a non-null `selection_rate`. **Do NOT alter `competition_pressure_score`** — fix only count display and the pressure explanation text. Consumers moving together: `admin_exam_intel_cms.py`, `admin_exam_intelligence.py`, `competition.py`, `competition_context.py`, `evidence.py`, `status.py`, `CompetitionMetricsTable.jsx`, `CompetitionPanel.jsx`.

---

## Section F — Acceptance tests

### F.1 Entity canonicity & shape (approved schema)
```
[ ] every exam_candidate_counts row references exam_id (public.exams); no recruitment_id column exists
[ ] exam_cycle_id is NOT NULL on every row (always required)
[ ] applied rows: scope_kind='cycle' and exam_phase_id IS NULL (CHECK-enforced)
[ ] appeared rows: scope_kind='phase' with exam_phase_id set, OR explicit cycle aggregate (scope_kind='cycle', phase NULL)
[ ] write validator rejects a phase that does not belong to the same exam AND cycle
[ ] count_value rejects negatives (>= 0 check)
[ ] applied and appeared are independently storable (neither derived from the other)
```
### F.2 Category axis & NULL-safe uniqueness
```
[ ] reservation_category_id is an FK to reservation_categories; free-text/enum category rejected
[ ] NULL category (official total) and category rows coexist for the same scope
[ ] NULLS NOT DISTINCT lane indexes: a second current-published row for the same
    (exam, cycle, scope_kind, phase-NULL, count_type, category-NULL) tuple is rejected (NULL-safe uniqueness test)
[ ] same test for the working lane (draft/pending_review, superseded_at IS NULL)
[ ] per-scope version_no uniqueness holds; supersedes_id self-reference rejected
[ ] counts not smuggled into vacancy_by_category or any cutoff JSONB (PD-6)
```
### F.3 Lifecycle, evidence & verified-only reads
```
[ ] draft/pending_review/rejected counts never appear in aspirant/planner reads
[ ] RLS: non-admin sees only reviewer_status IN ('reviewed','locked'); admin authority via app_metadata (NOT profiles.is_admin)
[ ] writes are service-role only; anon/authenticated direct mutation rejected (counts + evidence tables)
[ ] model_generated counts start in draft; cannot land reviewed/locked without human review
[ ] claim-value-match promotion: promotion succeeds only when >=1 qualifying PRIMARY evidence row's
    claim_value.count_value equals the parent count_value AND scope/category fields match;
    stale evidence (attached before a later parent edit) fails promotion
[ ] reviewed_analysis as sole primary evidence for an official count fails promotion (§7)
[ ] published-parent UPDATE against frozen content columns and published-parent DELETE are trigger-rejected
    (direct service-role attempts, not only endpoint behavior); evidence UPDATE/DELETE/INSERT blocked once parent published
[ ] evidence_count is derived from child rows, not operator input
```
### F.4 Migration & backfill (OD-6 Option B)
```
[ ] only provenance-proven rows converted to `applied`; all others preserved as legacy unknown and excluded from ratios
[ ] ambiguous (no-provenance) legacy rows are NOT silently converted (asserted; zero-loss + converted/unknown counts recorded)
[ ] competition-pressure read output preserved for a representative exam post-migration
    (competition_pressure_score is never altered by this PR)
[ ] exam_candidate_counts RLS verified via pg_policies before completion
```
### F.5 Read paths (PR-2 atomic ratio switch, §1.2)
```
[ ] ratio derivation and ALL ratio consumers switch together in this PR:
    admin_exam_intel_cms.py, admin_exam_intelligence.py, competition.py, competition_context.py,
    evidence.py, status.py, CompetitionMetricsTable.jsx, CompetitionPanel.jsx
[ ] denominator preference appeared -> applied -> null, reviewed/locked counts only;
    ratio_denominator records which was used; selection_rate non-null only with a provenance-proven denominator
[ ] competition.py / competition_context.py read explicit counts (not the overloaded applicant_count)
[ ] pressure explanation text fixed; competition_pressure_score output unchanged
```

---

## Section G — Files to change (PR 2, on operator sign-off)

| File | Change |
|---|---|
| `app/supabase/migrations/<next>_applied_vs_appeared_counts.sql` | `exam_candidate_counts` + `exam_candidate_count_evidence` (§4.1) + OD-3 scope CHECKs + §2.1 NULLS NOT DISTINCT lane/version indexes + two-lane lifecycle columns + immutability/published-parent triggers + promotion RPC + OD-6 Option B backfill (zero-loss, no-silent-convert assertions) + exact §3 RLS (reviewed/locked non-admin read, app-metadata admin, service-role writes). Number from the live `schema_migrations` ledger; coordinate with sibling J3 cutoffs gate. |
| `app/backend/app/exam_intelligence/competition.py` | Read/surface explicit applied + appeared from `exam_candidate_counts` (reviewed/locked, current-published lane); part of the atomic ratio-consumer switch. |
| `app/backend/app/study_os/competition_context.py` | Migrate pressure read off overloaded `applicant_count`; denominator appeared → applied → null with `ratio_denominator` recorded; fix pressure **explanation** only — `competition_pressure_score` unchanged. |
| `app/backend/app/api/admin_exam_intel_cms.py` + admin read (`admin_exam_intelligence.py`) and `evidence.py`, `status.py` | Editors + review lifecycle + evidence attach/promotion for counts; remaining ratio consumers switch in the same PR (§1.2). |
| `app/frontend` — `CompetitionMetricsTable.jsx`, `CompetitionPanel.jsx` | Display explicit counts + derived rate fields; part of the atomic consumer switch. |
| backend + frontend tests | Section F — incl. claim-value-match promotion, NULL-safe uniqueness, OD-6 backfill assertions, trigger-immutability, pressure-output-preserved. |
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

*Status: AMENDED TO MATCH APPROVED RESOLUTIONS — OPERATOR SIGN-OFF PENDING. Body reconciled with docs/status/J3-OD-Resolutions-Locked-2026-07-02.md (2026-07-02; §0, §2, §2.1, §3, §4.1, §6, §7, §1.2). OD-1…OD-6 resolved; implementation remains BLOCKED until explicit operator approval is recorded on the PR. Implementation is PR 2 of docs/status/J3-Implementation-Checklist-2026-07-02.md (branches from merged PR 1). Cross-references the sibling J3 cutoffs/vacancy-JSONB gate; JSONB boundary (PD-6) prevents overlap.*
</content>
</invoke>
