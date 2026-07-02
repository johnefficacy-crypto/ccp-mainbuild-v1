# J3 Operator-Decision Resolutions — consolidated record

- Document type: consolidated operator-decision resolution record for the four J3 sub-item gates.
- Status: **DRAFT-FINAL — OPERATOR PENDING.** §10 step (a) is complete: all four gate documents have been deep-amended in place so their bodies encode these resolutions (headers: `AMENDED TO MATCH APPROVED RESOLUTIONS — OPERATOR SIGN-OFF PENDING`). §10 step (b) is outstanding: an **explicit operator approval event recorded on the PR** (comment/review by the operator, or a linked dated decision artifact). An agent-authored assertion inside a commit is not approval evidence (governance: operator steps are never marked complete from code inspection alone). Implementation dispatch remains blocked until that event exists; then this status flips to `OPERATOR APPROVED` and PR 1 (Competition structure) dispatches first.
- Date: 2026-07-02 (revised same day per PR #857 and PR #861 checkpost reviews)
- Relationship to the gates: **consolidates, does not supersede.** The gate bodies now match this record; on the recorded operator approval event this record flips to `OPERATOR APPROVED` and implementation dispatch unblocks.
- Parent track: `J3 — schema/domain redesign` (`docs/status/career-copilot-checklist.md`).

## Authority & read order

This record consolidates resolutions for every `OD-*` item across:

1. `docs/status/J3-Competition-Cutoffs-Gate-2026-07-02.md` (OD-1…OD-11)
2. `docs/status/J3-Applied-Vs-Appeared-Gate-2026-07-02.md` (OD-1…OD-6)
3. `docs/status/J3-Mixed-Format-PDF-Gate-2026-07-02.md` (OD-1…OD-3)
4. `docs/status/J3-Evidence-Coverage-Scoring-Gate-2026-07-02.md` (OD-1…OD-6, OD-5a)

Invariants that bound every decision below (CLAUDE.md, non-negotiable): verified-only reads; Determinism > Heuristics; Trust > Speed; Control > Automation; no new AI writes; `public.exams` vs `public.recruitments` canonicity — competition/candidate/coverage intelligence is `exam_id`-scoped exam-master data, **never** `recruitment_id`.

---

## 0. Three repo defects these resolutions fix

1. **No canonical uniqueness on `exam_competition_metrics`.** Different readers either aggregate every reviewed row or pick one by cycle/status/creation time — two readers can return divergent answers for the same scope. Fixed by two-lane versioning + `metric_kind` + a shared current-row selector (Competition OD-10/OD-11) with **executable NULL-safe DDL** (§2.1).
2. **`cutoff_trend` shape disagreement.** `CompetitionPanel.jsx` writes the string `"rising"`; the aspirant reader (`competition.py`) expects a `{category: marks}` map, so operator-entered workspace data silently produces an EMPTY aspirant cutoff series. It also permits a direct `draft → locked` jump. Fixed by the `cutoff_by_category` object shape + a DB-enforced lifecycle (Competition OD-3/OD-5/OD-8, naming amendment).
3. **`selection_ratio` undefined-persisted-semantics + inverse UI.** The column is constrained `0..1`, but `CompetitionPanel.jsx` computes `applicant_count / vacancy_total` (the inverse of a selection rate). We cannot prove every stored value uses the wrong formula; we **can** prove the contract is ambiguous and the UI calculation is inverse to a selection rate. Fixed by deprecating `selection_ratio` in place and deriving `selection_rate` / `candidates_per_vacancy` / `ratio_denominator` at read time, under the **transitional contract** in §1.2 (the authoritative denominator only exists after PR 2).

---

## 1. Competition-Cutoffs — OD-1…OD-11

| OD | Resolution |
|---|---|
| **OD-1** | v1 canonical **vertical** categories: `general`, `ews`, `obc`, `sc`, `st`. Aliases normalized via the shared taxonomy (`ur → general`, `gen → general`, `obc_ncl → obc`). PwBD / ex-servicemen / domicile are a **separate horizontal dimension** added later — never mixed into this single vertical axis. |
| **OD-2** | `source_basis='model_generated'` rows may remain **`draft` only**. Before submission a human must attach evidence and change `source_basis` to `official` or `reviewed_analysis`. Revalidate on the `submit`, `→ reviewed`, and `→ locked` transitions. |
| **OD-3** | Cutoff/difficulty **direction is derived at read time, never stored**. Derive direction only across **≥ 2 comparable cycles** matching the same phase, category and non-null `max_marks`; otherwise return `null`. `difficulty_assessment` is a structured **descriptive** fact — **not** planner input. **Remove `stage` from each cutoff object** (`exam_phase_id` is the canonical phase; a second `stage` field creates a contradictory source of truth). Direction derivation lives in **backend code** (`competition.py`), not SQL. |
| **OD-4** | `sum(categories) > vacancy_total` → **hard error**. `sum(categories) < vacancy_total` → **warning** (official notices legitimately omit buckets). Add a `breakdown_complete` boolean; strict equality is enforced **only when `breakdown_complete = true`**. |
| **OD-5** | **Selective normalization, not grandfathering.** Normalize valid category→number maps into `cutoff_by_category`. Move strings (`"rising"`), bare numbers and lists into `metadata.legacy_*` and clear the canonical field. **Disposition depends on lane (reconciled with OD-7 — published rows are never reopened in place):** a malformed row already in `draft`/`pending_review` returns to `draft`; a malformed **reviewed/locked** row keeps its published status (its valid fields stay aspirant-visible; the aspirant reader was already silently dropping the malformed shape, so clearing the canonical field loses nothing user-visible) and a **separate working draft revision** is created carrying the `metadata.legacy_*` payload for operator correction. Never manufacture marks from `"rising"` or an unlabeled number. Record pre/post counts in migration evidence. Full legacy disposition (including `metric_kind` assignment) in §1.3. |
| **OD-6** | Dedicated **`exam_competition_metric_evidence` child table** (full schema §4). `evidence_count` is **derived by counting the child rows of that revision** (append-only model — no "active" sub-state; see §4 lifecycle) and is removed from operator write input. |
| **OD-7** | Reviewed/locked rows are **not editable in place**. A notes-required **`reopen_for_edit`** operation **clones** the published row into a new `draft` revision (it does **not** move the published row back to `draft` — see §2 two-lane model), preserving aspirant-visible published intelligence during correction. |
| **OD-8** | Enforce lifecycle + CAS through a **DB RPC / state machine**, with matching app-layer validation. Multiple service-role write surfaces make app-only validation insufficient. |
| **OD-9** | **Workspace → Competition remains the canonical editor.** The review table (`CompetitionMetricsTable.jsx`) is the lifecycle/review surface and MUST display all cutoff, vacancy and evidence fields. **No new surface** (no-new-surface rule). |
| **OD-10** | **Two current lanes per (scope, `metric_kind`)** — refined from the earlier single-unsuperseded-row idea (a draft replacement must coexist with the published row): one **current published** row (`reviewer_status ∈ {reviewed, locked}`) and at most one **current working** row (`reviewer_status ∈ {draft, pending_review}`). Columns: `version_no`, `supersedes_id`, `superseded_at`, `is_current_published`. Enforced by the **executable partial-index DDL and consistency CHECKs in §2.1** (NULL-safe — a plain UNIQUE over nullable scope columns does not enforce uniqueness). All readers use one shared current-published selector — no per-reader "best row" heuristic. |
| **OD-11** | Keep one table; add **`metric_kind ∈ {cycle_summary, phase_cutoff}`**. `cycle_summary` requires `exam_phase_id IS NULL` and owns vacancy / pressure. `phase_cutoff` requires a phase and owns cutoffs / difficulty. DB CHECKs prohibit cross-granularity fields (a phase row cannot carry cycle-level vacancy and vice-versa). **`exam_cycle_id` is required for every new-model row** (`metric_kind IS NOT NULL`): competition facts are cycle-anchored; exam-wide (cycle-less) competition rows are NOT supported in v1 — any legacy cycle-less row goes to operator triage in the §1.3 disposition. Cross-granularity CHECKs are gated on `metric_kind IS NOT NULL` so undisposed legacy rows (`metric_kind IS NULL`) do not violate them mid-migration; the disposition migration fails closed if any row is left unassigned (§1.3). |

### 1.1 Naming amendment (additive deprecation — no breaking rename)

Do **not** rename or drop columns in place (PostgREST schema-reload vs. app-rollout ordering would break). **Add** replacement columns, backfill, switch consumers, then deprecate:

| New column | Replaces (deprecated-in-place) |
|---|---|
| `cutoff_by_category` | `cutoff_trend` (legacy) |
| `difficulty_assessment` | `difficulty_trend` (legacy) |

Legacy columns are removed only in a **later cleanup migration** after all consumers and historical values are verified.

### 1.2 Ratio amendment — transitional contract (two-step; the denominator lands in PR 2)

`selection_ratio` has undefined persisted semantics and an inverse UI calculation. **Deprecate in place.** The derived replacement fields depend on a provenance-proven applied/appeared denominator, which does not exist until PR 2 — so the switchover is explicitly two-step. PR 1 must NOT derive rates from the ambiguous legacy `applicant_count` (that would violate Applied-vs-Appeared OD-6) and must NOT silently change displayed behavior.

**PR 1 (additive, no behavior change):**
1. Remove `selection_ratio` from operator-write allowlists; stop all new computations from it.
2. Add the derived response fields with an explicit null contract:

```jsonc
{
  "selection_rate":         null,       // vacancies / denominator — null until a provenance-proven denominator exists
  "candidates_per_vacancy": null,       // denominator / vacancies — same null contract
  "ratio_denominator":      null,       // "appeared" | "applied" | null
  "selection_ratio":        0.00125,    // EXISTING KEY PRESERVED — deprecated alias, verbatim legacy value
  "selection_ratio_legacy": 0.00125     // explicit legacy field, same value, labelled legacy/unverified-denominator
}
```

3. **The existing `selection_ratio` response key is NOT removed in PR 1** — external clients may read it. It is served as a deprecated alias carrying the verbatim legacy value alongside `selection_ratio_legacy` (additive compatibility response). Internal consumers move to the explicit fields; the alias is removed only in the later cleanup migration/endpoint-version step after external-consumer verification. Display parity, zero silent change.

**PR 2 (atomic switch):** introduce `exam_candidate_counts`, then in the same PR switch ratio derivation and **all** ratio consumers together: denominator preference `appeared` → `applied` → null (reviewed/locked counts only). Only rows with a provenance-proven denominator ever produce a non-null `selection_rate`.

**Consumers that move together** (API-contract migration even though the physical column stays): `admin_exam_intel_cms.py` (write/validate), `admin_exam_intelligence.py` (admin read), `competition.py` (aspirant series), `competition_context.py` (pressure explanation), `evidence.py` (evidence row), `status.py` (transitive via `/api/exam-intelligence/exams/{slug}` → `competition_series`), `CompetitionMetricsTable.jsx` (display), `CompetitionPanel.jsx` (inverse local ratio — removed in PR 1).

The old column is retained for audit/back-compat and dropped only in a later cleanup migration after all consumers and historical values are verified.

### 1.3 Legacy-row disposition for `metric_kind` (fail-closed preflight; required before cross-granularity CHECKs)

Existing `exam_competition_metrics` rows can legitimately carry vacancy, cutoff, difficulty and pressure in one row; the new CHECKs make `cycle_summary` and `phase_cutoff` own disjoint fields. The PR 1 migration therefore runs a deterministic disposition, and the cross-granularity CHECKs are enabled **only after** it completes:

1. **Preflight report** classifying every existing row by populated fields × `exam_phase_id` × `exam_cycle_id` × reviewer_status. Committed as migration evidence.
2. **Cycle-level-only rows** (vacancy/applicant/pressure populated; no cutoff/difficulty content; `exam_phase_id IS NULL`, `exam_cycle_id` set) → assigned `metric_kind='cycle_summary'` in place.
3. **Combined rows with a known phase** (`exam_phase_id` set) → **split**: cycle-level fields move to a new `cycle_summary` revision for `(exam_id, exam_cycle_id)` (created only if one does not already exist — else operator triage); cutoff/difficulty content stays on the original row, which becomes `metric_kind='phase_cutoff'`. Review stamps (`reviewer_status`, `reviewed_by/at`) carry forward to both.
4. **Cutoff/difficulty content with `exam_phase_id IS NULL`** → phase identity cannot be assigned deterministically: canonical cutoff fields are NOT populated; the payload is preserved in `metadata.legacy_*`; the row becomes `cycle_summary` (keeping its valid cycle-level fields); a **working draft** revision is created for operator triage to assign the phase.
5. **Cycle-less rows** (`exam_cycle_id IS NULL`) → operator triage (v1 requires a cycle; see OD-11). Not auto-assigned.
6. **Published (reviewed/locked) rows are never returned to draft** (OD-7). Their valid fields stay published on the disposed revision(s); malformed/unassignable content moves to `metadata.legacy_*` with a separate working draft carrying it for correction (per OD-5 as amended).
7. **Fail-closed assertion:** a `DO` block at the end of the disposition raises a descriptive exception if any row remains with `metric_kind IS NULL`, if any pre/post field-value count mismatches (zero-loss), or if any published row lost aspirant-visible valid data. Only then does §1.4 lane initialization run; the cross-granularity CHECKs and §2.1 indexes are enabled only after §1.4 completes.

### 1.4 Current-lane initialization (fail-closed; runs after §1.3, before indexes/reader switch)

The existing table has no uniqueness or current marker: multiple reviewed/locked rows and multiple draft/pending rows can already coexist for what becomes one scope. `is_current_published` must not default to false everywhere (readers switching to the shared selector would black out aspirant data) and must not be set on several rows (index creation fails). A dedicated initialization phase therefore backfills the lanes:

1. **Duplicate report:** per `(exam_id, exam_cycle_id, exam_phase_id, metric_kind)` after §1.3, list every scope with >1 published-lane row (`reviewer_status IN ('reviewed','locked')`) or >1 working-lane row (`draft`/`pending_review`). Committed as migration evidence.
2. **Published lane:** where exactly one published row exists → it is mechanically marked `is_current_published = true`. Where multiple exist → **fail-closed**: the migration raises until the operator records an audited canonical selection (same posture as §5.3 — never auto-keep latest); the selected row becomes current, the others are marked superseded (`superseded_at` stamped, `is_current_published = false`) and remain fully preserved.
3. **Working lane:** where multiple working rows exist, the operator-audited disposition keeps one working row (default recommendation: the most recently updated) and marks the rest superseded (`superseded_at` stamped) so the working-lane partial index can build. No row is deleted.
4. **Version/lineage backfill:** within each scope, rows are ordered by `COALESCE(reviewed_at, created_at)` and assigned `version_no` 1..N monotonically; `supersedes_id` chains each revision to its predecessor. All new-model rows end with `version_no > 0` and a consistent chain (§2.1 lineage constraints).
5. **Legacy trust/evidence disposition (per `source_basis`):** legacy rows have only an integer `evidence_count` and no child evidence to backfill, but removing them would destroy all visible data. Policy for entering the published lane:
   - `manual`, `official`, `reviewed_analysis`, `derived` reviewed/locked rows → **grandfathered** as current-published (they passed the human review lifecycle), flagged `metadata.legacy_unvalidated_evidence = true`. The §4 primary-evidence requirement applies **prospectively**: at their next lifecycle transition (reopen-for-edit → promotion) qualifying child evidence is mandatory. They are surfaced in a revalidation worklist.
   - `model_generated` reviewed/locked rows → **NOT auto-grandfathered**. Fail-closed operator triage: the operator either attaches qualifying evidence and re-bases `source_basis` (audited) so the row can be current-published, or demotes it via an audited action. This is the only case where visibility may change, and only by explicit operator decision.
   - All working-lane legacy rows keep their status; the evidence requirement binds at promotion as usual.
6. **Zero-availability-loss assertion:** a terminal `DO` block verifies that every scope which had ≥1 published row before initialization has exactly one `is_current_published` row after it (excepting only scopes the operator explicitly triaged under the `model_generated` rule, which are enumerated in the report), and that no row was deleted. Only then are the §2.1 partial unique indexes created and readers switched to the shared selector.

### 1.5 Canonical JSONB contracts (validator-enforced; closes the residual opacity)

- **`cutoff_by_category`** — object of `{ "<category>": { "marks": <number ≥ 0>, "max_marks": <number > 0, optional> } }`. Keys validated against `reservation_categories.code`. Bare string/number/list values rejected by the validator. **Migration conversion rule (OD-5):** a legacy bare-number map value is explicitly normalized into object form — `{"general": 120}` → `{"general": {"marks": 120}}` — before the validator is enabled; only non-numeric/unlabelable payloads go to `metadata.legacy_*`.
- **`vacancy_by_category`** — object of `{ "<category>": <integer ≥ 0> }`. Keys validated against `reservation_categories.code`; **values validated as non-negative integers** (no nulls inside the map — omit the key instead; `{}` means "no breakdown"). This makes the OD-4 sum rule executable.
- **`difficulty_assessment`** — locked shape `{ "level": "harder" | "stable" | "easier", "basis": "<text 8–500 chars>" }`. Validator enforces the `level` enum and `basis` length. Descriptive only — never planner input (OD-3). A bare string (the legacy `difficulty_trend` form) is rejected.

---

## 2. Two-lane revision model (Competition + Candidate Counts)

Applies to `exam_competition_metrics` and `exam_candidate_counts` (both introduce correction history). **Not** applied to `exam_topic_coverage` (see §5).

```text
one current published row per (scope, kind):
  reviewer_status in ('reviewed','locked')   is_current_published = true

at most one current working row per (scope, kind):
  reviewer_status in ('draft','pending_review')   superseded_at is null
```

Columns: `version_no`, `supersedes_id`, `superseded_at`, `is_current_published`.

**Promotion RPC (atomic):** (1) validate shape + evidence; (2) mark the previous published revision superseded (`superseded_at`, `is_current_published=false`); (3) mark the new revision current-published; (4) preserve the previous row and its evidence.

**Reopen-for-edit:** clones the published row into a new draft revision — the published row is untouched and stays aspirant-visible until the new revision is promoted.

**Published-parent UPDATE guard (DB-enforced on BOTH tables — OD-7 is not app-only):** service-role callers can update tables directly today, so a `BEFORE UPDATE` trigger on `exam_competition_metrics` and `exam_candidate_counts` enforces immutability of published rows: when the existing row is published (`reviewer_status IN ('reviewed','locked')`), **all content columns are frozen** (cutoffs, vacancy fields, difficulty, pressure, counts, scope/identity columns, `source_basis`, `confidence_score`, `breakdown_complete`, metadata payload fields) — only the lifecycle/supersession columns may change (`reviewer_status` per the transition matrix, `superseded_at`, `is_current_published`, `reviewed_by`/`reviewed_at`/`reviewer_notes`, `updated_at`), and only in the combinations the state machine permits (`reviewed → locked`, `locked → reviewed` reopen with notes, atomic supersession by the promotion RPC). Implementation note: the lifecycle RPC may additionally set a transaction-local GUC (`set_config('app.lifecycle_rpc','1',true)`) that the trigger checks for the supersession combination, but the column allowlist holds regardless of caller. **Direct service-role parent-UPDATE attempts against published rows are a required test** (verification gates), alongside the evidence and parent-DELETE trigger tests.

`exam_candidate_counts` uses the same revision model so a plain unique tuple does not prevent preserving corrected historical official counts.

### 2.1 Executable uniqueness DDL + consistency constraints (NULL-safe)

A plain `UNIQUE` index over nullable scope columns does **not** enforce uniqueness (PostgreSQL treats NULLs as distinct). The lanes are therefore enforced with **scope-specific partial unique indexes** — the NULL/non-NULL split of `exam_phase_id` is carried by the `metric_kind` predicate, so no nullable column appears in an index key with NULL ambiguity:

```sql
-- consistency CHECKs (new-model rows only; legacy rows have metric_kind IS NULL until §1.3 disposes them)
alter table public.exam_competition_metrics
  add constraint ecm_new_model_requires_cycle
    check (metric_kind is null or exam_cycle_id is not null),
  add constraint ecm_kind_phase_shape
    check (metric_kind is null
           or (metric_kind = 'cycle_summary' and exam_phase_id is null)
           or (metric_kind = 'phase_cutoff'  and exam_phase_id is not null)),
  add constraint ecm_current_published_state
    check (not is_current_published
           or (reviewer_status in ('reviewed','locked') and superseded_at is null)),
  add constraint ecm_superseded_not_current
    check (superseded_at is null or not is_current_published),
  -- cross-granularity FIELD-OWNERSHIP checks (the asserted OD-11 rule, executable):
  -- cycle rows cannot carry cutoff/difficulty; phase rows cannot carry vacancy/pressure/count fields
  add constraint ecm_kind_field_ownership
    check (metric_kind is null
           or (metric_kind = 'cycle_summary'
               and (cutoff_by_category is null or cutoff_by_category = '{}'::jsonb)
               and (difficulty_assessment is null or difficulty_assessment = '{}'::jsonb))
           or (metric_kind = 'phase_cutoff'
               and vacancy_total is null
               and vacancy_by_category = '{}'::jsonb
               and applicant_count is null
               and competition_pressure_score is null)),
  -- version-lineage invariants (backfilled by §1.4; enforced for every new-model row)
  add constraint ecm_version_no_positive
    check (metric_kind is null or (version_no is not null and version_no > 0)),
  add constraint ecm_no_self_supersede
    check (supersedes_id is null or supersedes_id <> id);

-- supersedes_id is a self-FK:
--   supersedes_id uuid references public.exam_competition_metrics(id) on delete restrict
-- Cross-row lineage invariants that a CHECK cannot express are enforced in the lifecycle
-- RPC + a validation trigger: the supersedes_id target must share the same
-- (exam_id, exam_cycle_id, exam_phase_id, metric_kind) scope; version_no must equal
-- parent.version_no + 1; cycles are impossible given monotonic version_no + the
-- per-scope version uniqueness indexes below.

-- version_no is unique per scope (monotonic chain, no duplicates):
create unique index ecm_version_cycle_summary_uq
  on public.exam_competition_metrics (exam_id, exam_cycle_id, version_no)
  where metric_kind = 'cycle_summary';
create unique index ecm_version_phase_cutoff_uq
  on public.exam_competition_metrics (exam_id, exam_cycle_id, exam_phase_id, version_no)
  where metric_kind = 'phase_cutoff';

-- one current PUBLISHED row per scope
create unique index ecm_current_pub_cycle_summary_uq
  on public.exam_competition_metrics (exam_id, exam_cycle_id)
  where metric_kind = 'cycle_summary' and is_current_published;

create unique index ecm_current_pub_phase_cutoff_uq
  on public.exam_competition_metrics (exam_id, exam_cycle_id, exam_phase_id)
  where metric_kind = 'phase_cutoff' and is_current_published;

-- at most one current WORKING row per scope
create unique index ecm_working_cycle_summary_uq
  on public.exam_competition_metrics (exam_id, exam_cycle_id)
  where metric_kind = 'cycle_summary'
    and reviewer_status in ('draft','pending_review') and superseded_at is null;

create unique index ecm_working_phase_cutoff_uq
  on public.exam_competition_metrics (exam_id, exam_cycle_id, exam_phase_id)
  where metric_kind = 'phase_cutoff'
    and reviewer_status in ('draft','pending_review') and superseded_at is null;
```

For `exam_candidate_counts`, `exam_phase_id` and `reservation_category_id` are legitimately NULL inside a lane (cycle scope / official total), so the lane indexes must make NULLs compare equal. Preferred: `NULLS NOT DISTINCT` (PostgreSQL 15+, available on Supabase); fallback if the target PG version lacks it: expression indexes over `coalesce(col, '00000000-0000-0000-0000-000000000000'::uuid)`:

```sql
create unique index ecc_current_pub_uq
  on public.exam_candidate_counts
    (exam_id, exam_cycle_id, scope_kind, exam_phase_id, count_type, reservation_category_id)
  nulls not distinct
  where is_current_published;

create unique index ecc_working_uq
  on public.exam_candidate_counts
    (exam_id, exam_cycle_id, scope_kind, exam_phase_id, count_type, reservation_category_id)
  nulls not distinct
  where reviewer_status in ('draft','pending_review') and superseded_at is null;
```

(The same `*_current_published_state` / `*_superseded_not_current` CHECKs, the `version_no > 0` + self-FK `supersedes_id` + no-self-reference lineage constraints, the per-scope `version_no` uniqueness index (`NULLS NOT DISTINCT` over the scope tuple + `version_no`), and the RPC/trigger same-scope-ancestry rule apply identically to `exam_candidate_counts`.)

---

## 3. Applied-vs-Appeared — OD-1…OD-6

| OD | Resolution |
|---|---|
| **OD-1** | Support **both totals and optional per-category** counts. `reservation_category_id = NULL` means the official total; category rows are captured **only when official data exists**. Category detail is supported but never mandatory. |
| **OD-2** | New typed **`exam_candidate_counts` table** (not two more nullable fields on the overloaded competition row). Applied and appeared arrive at different times with independent evidence and lifecycles. |
| **OD-3** | Add **`scope_kind ∈ {cycle, phase}`** (constrained CHECK). `exam_cycle_id` is **always required**. `applied` → `scope_kind='cycle'`, `exam_phase_id IS NULL`. `appeared` → either `scope_kind='phase'` with `exam_phase_id` set, **or** an explicitly-labelled cycle aggregate (`scope_kind='cycle'`, `exam_phase_id IS NULL`) for authorities that publish only aggregate appearance data. A write validator confirms the phase belongs to the same exam **and** cycle. |
| **OD-4** | Reuse the **shared `reservation_categories` vocabulary + aliases** (§6) via FK — not free text, not a hard-to-extend PG enum. |
| **OD-5** | **Consume the new reviewed/locked counts immediately** in APIs (prefer `appeared`, then `applied`, else return no ratio). Do **NOT** let this PR alter `competition_pressure_score` itself — only fix count display and the pressure **explanation** text. The §1.2 transitional contract makes PR 2 the point where ratio derivation and all ratio consumers switch atomically. |
| **OD-6** | **Option B** — migrate only rows whose evidence explicitly proves the value means "applied." Preserve all other `applicant_count` values as **legacy unknown** and exclude them from ratios. Record converted / unknown / zero-loss counts in migration evidence. Ambiguous rows are **never** silently converted. |

**Uniqueness:** enforced by the NULL-safe two-lane DDL in §2.1 over `(exam_id, exam_cycle_id, scope_kind, exam_phase_id, count_type, reservation_category_id)`. **Reviewer lifecycle & RLS read predicate (exact):** the same five-state `reviewer_status` vocabulary as `exam_competition_metrics`; non-admin reads require `reviewer_status IN ('reviewed','locked')` (RLS mirrors migration 057's predicate, but the admin check uses app-metadata roles, **not** the deprecated `profiles.is_admin`). **Evidence:** applied/appeared facts get their **own** first-class evidence table — exact schema and promotion-comparison rules in **§4.1** — do NOT attach them to the generic competition-metric evidence row; their lifecycle and parent identity differ.

---

## 4. Competition evidence child table (`exam_competition_metric_evidence`)

```sql
create table public.exam_competition_metric_evidence (
  id uuid primary key default gen_random_uuid(),

  metric_id uuid not null
    references public.exam_competition_metrics(id) on delete cascade,
    -- cascade is retained ONLY for draft-cleanup; deleting a published parent is
    -- blocked by trigger (see lifecycle enforcement below), so published evidence
    -- can never be cascade-deleted.

  claim_field text not null
    check (claim_field in (
      'vacancy_total','vacancy_by_category','cutoff_by_category',
      'difficulty_assessment','competition_pressure_score')),

  reservation_category_id uuid
    references public.reservation_categories(id) on delete restrict,

  evidence_kind text not null
    check (evidence_kind in (
      'official_notification','official_result','official_statistics',
      'corrigendum','official_page','reviewed_analysis')),

  evidence_role text not null default 'primary'
    check (evidence_role in ('primary','supporting')),

  source_id uuid references public.source_registry(id) on delete set null,
  document_asset_id uuid references public.document_assets(id) on delete set null,

  evidence_url text,           -- may be MORE specific than source_registry.official_url
  source_label text,
  source_page integer check (source_page is null or source_page >= 1),
  source_excerpt text,

  claim_value jsonb not null,  -- exact value/object this evidence supported when attached
  content_hash text,
  evidence_key text not null unique,  -- server-computed idempotency hash

  captured_at timestamptz not null default now(),
  created_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb,

  check (num_nonnulls(source_id, document_asset_id, evidence_url) >= 1),
  check (
    (claim_field in ('vacancy_by_category','cutoff_by_category') and reservation_category_id is not null)
    or
    (claim_field in ('vacancy_total','difficulty_assessment','competition_pressure_score') and reservation_category_id is null)
  )
);

create index exam_comp_metric_evidence_metric_idx
  on public.exam_competition_metric_evidence(metric_id);
create index exam_comp_metric_evidence_claim_idx
  on public.exam_competition_metric_evidence(metric_id, claim_field, reservation_category_id);
```

- **No `unique(metric_id, source_url)`** — one official PDF can validly prove several categories/claims. `evidence_key` hashes the normalized (metric, claim, category, source/page, claim_value), computed **server-side only**.
- **Lifecycle — append-only, DB-enforced (no "active" sub-state):**
  - Evidence rows are **append-only**: attached only while the parent revision is `draft`/`pending_review`; a wrong attachment on a working revision is corrected by **deleting and re-inserting while still in the working lane** — never by UPDATE.
  - `evidence_count` = **count of all child rows of that revision** (there is no soft-delete/supersession sub-state on evidence; corrections after publication happen by cloning a new working revision with fresh evidence, per §2).
  - **DB triggers (service-role writers can bypass app rules, so app-only enforcement is insufficient):** (1) `BEFORE UPDATE OR DELETE` on evidence → raise when the parent revision's `reviewer_status IN ('reviewed','locked')`; (2) `BEFORE DELETE` on `exam_competition_metrics` → raise when the row is published (`reviewer_status IN ('reviewed','locked')` or `is_current_published`) — the FK cascade therefore only ever fires for genuinely-draft cleanup; (3) `BEFORE INSERT` on evidence → raise when the parent revision is published.
  - Promotion validates every populated high-risk claim has qualifying **primary** evidence **whose `claim_value` matches the current parent field/category value** — mere existence of a primary evidence row is insufficient, otherwise stale evidence attached before a later working-parent edit would survive. A claim-value mismatch is a promotion failure requiring fresh evidence.
  - **Tests must include direct service-role UPDATE/DELETE attempts against published evidence, a published-parent DELETE attempt, and a published-parent UPDATE attempt against frozen content columns** (asserting the triggers reject them), not only endpoint behavior.
- **RLS:** enable RLS; **no** anon/authenticated direct read or write; access only through permission-gated FastAPI evidence/review routes using the service role. **Do NOT** copy migration 057's `profiles.is_admin` policy — AGENTS.md marks profile-based authority deprecated; app metadata is the role source of truth.

### 4.1 Candidate-count evidence (`exam_candidate_count_evidence`) — exact schema

The candidate-count parent row IS the single claim (one `count_value` for one scope/category), so this table has **no `claim_field`** and **no `reservation_category_id`** (the parent carries the category). It does not "mirror §4" mechanically:

```sql
create table public.exam_candidate_count_evidence (
  id uuid primary key default gen_random_uuid(),

  count_id uuid not null
    references public.exam_candidate_counts(id) on delete cascade,
    -- cascade fires only for genuinely-draft cleanup; published-parent DELETE is trigger-blocked

  evidence_kind text not null
    check (evidence_kind in (
      'official_notification','official_result','official_statistics',
      'corrigendum','official_page','reviewed_analysis')),

  evidence_role text not null default 'primary'
    check (evidence_role in ('primary','supporting')),

  source_id uuid references public.source_registry(id) on delete set null,
  document_asset_id uuid references public.document_assets(id) on delete set null,

  evidence_url text,
  source_label text,
  source_page integer check (source_page is null or source_page >= 1),
  source_excerpt text,

  -- snapshot of the exact fact this evidence supported when attached:
  -- { count_type, scope_kind, exam_phase_id, reservation_category_code, count_value }
  claim_value jsonb not null,
  content_hash text,
  evidence_key text not null unique,  -- server-computed hash of
                                      -- (parent scope tuple, count_type, category, source/page, claim_value)

  captured_at timestamptz not null default now(),
  created_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb,

  check (num_nonnulls(source_id, document_asset_id, evidence_url) >= 1)
);

create index exam_candidate_count_evidence_count_idx
  on public.exam_candidate_count_evidence(count_id);
```

- **Same enforcement posture as §4:** append-only; attach only while the parent is `draft`/`pending_review`; INSERT/UPDATE/DELETE trigger-blocked once the parent is published; published-parent UPDATE/DELETE guards per §2; RLS with no anon/authenticated access; `evidence_count` derived by counting child rows.
- **Promotion comparison:** an `appeared`/`applied` count may be promoted only when ≥1 qualifying **primary** evidence row exists whose `claim_value.count_value` equals the parent `count_value` AND whose `claim_value` category/scope fields match the parent — stale evidence (attached before a later edit of the working parent) does not qualify. `reviewed_analysis` is not acceptable as the sole primary evidence for official counts (§7).
- **Source-trust validation** identical to §7 (`is_active`, `is_verified`, `discovery_only=false`, `source_type != 'aggregator'`, url-or-doc present).

---

## 5. Evidence-Coverage — OD-1…OD-6, OD-5a

| OD | Resolution |
|---|---|
| **OD-1** | Add **`source_basis='evidence_derived'`** to the `exam_topic_coverage` `source_basis` **text CHECK constraint** (it is a CHECK today, not a PG enum). OD-5a already needs a migration, so the value is nearly free and it keeps row-ownership unambiguous. Store `pyq` vs `hybrid` detail in metadata. |
| **OD-2** | Deterministic, **total** `coverage_depth` buckets (§5.1 — every valid input has exactly one result). **No row is generated when both syllabus mentions and PYQ evidence are zero.** |
| **OD-3** | **Option A — break the input edge.** `score_snapshots.py` MUST exclude `source_basis='evidence_derived'` coverage from its `coverage_component` input. This is a **read-model / scoring invariant enforced by unit/integration tests**, NOT a row-promotion validator check. |
| **OD-4** | **Manual operator-triggered derivation only** for v1. No scheduler, no piggy-back on snapshot computation. |
| **OD-5** | Leave manual/reviewed/locked coverage untouched. Store the proposed-vs-current **delta** in the audit record or derivation-result metadata. **No parallel shadow coverage rows.** |
| **OD-5a** | Add the **exam-wide partial unique index** (§5.3) before enabling exam-wide derivation. Existing indexes constrain only cycle+phase and phase-only scopes; the all-NULL exam-wide scope is unconstrained. |
| **OD-6** | Support **exam-wide and phase-scoped** derivation in v1. Do **NOT** support cycle-only derivation (score snapshots are cycle-independent). Each invocation targets **one explicit scope**. |

### 5.1 `coverage_depth` buckets (total function — every valid input maps to exactly one bucket)

```text
(no row)  : evidence_count = 0 AND syllabus_mentions = 0      -- derivation writes nothing
mentioned : evidence_count = 0 AND syllabus_mentions >= 1
light     : evidence_count 1–2
normal    : evidence_count 3–5
deep      : evidence_count 6–9
core      : evidence_count >= 10 AND syllabus_mentions >= 1 AND snapshot.is_high_yield = true
deep      : evidence_count >= 10 AND NOT (syllabus_mentions >= 1 AND snapshot.is_high_yield = true)
            -- fallback: high evidence volume that fails any `core` predicate is `deep`
```

Snapshot `priority`, `confidence` and `is_high_yield` are **copied unchanged** — J3 projects, it does not recompute.

### 5.2 Conflict rules — complete over the full `source_basis` vocabulary

With the single-row canonical model (no two-lane versioning for coverage, §5.4) and the exam-wide unique index, every existing-row case needs an explicit rule. The full vocabulary after OD-1 is `{official_syllabus, pyq_analysis, admin_review, hybrid, manual, model_generated, evidence_derived}`:

| Existing row at scope | Rule |
|---|---|
| `manual`, `admin_review`, `official_syllabus` (any status) | **Skip** — human-authored; record delta only. |
| `pyq_analysis`, `hybrid` (any status) | **Skip** — legacy human-entered provenance claims predating `evidence_derived`; treated as human-authored (the new enum value exists precisely so the derivation only ever owns rows it created). Record delta. |
| `model_generated` (any status) | **Skip + flag for operator triage** — never updated or overwritten by the derivation. |
| `evidence_derived` + `draft` | **Recompute/update** via the controlled derivation action (derivation-owned). |
| `evidence_derived` + `pending_review` | **Skip** — under review; record delta. Operator may reject back to `draft` to re-derive. |
| `evidence_derived` + `reviewed`/`locked` | **Leave unchanged**; explicit operator replacement workflow required. |
| `evidence_derived` + `rejected` | **Recompute/update** (returns to `draft` with fresh inputs). |

### 5.3 Exam-wide uniqueness index (OD-5a)

```sql
create unique index <name>
  on public.exam_topic_coverage (exam_id, topic_id)
  where exam_cycle_id is null and exam_phase_id is null;
```

**Duplicate handling = fail-closed (C) + manual resolution (B).** Do NOT auto-keep latest `reviewed_at` (latest ≠ correct, especially manual vs. evidence-derived). Process: (1) preflight report grouped by `(exam_id, topic_id)` where cycle+phase both NULL, including row IDs, status, source_basis, priority, high-yield, reviewed timestamps, evidence metadata; (2) operator selects canonical row; (3) merge legitimate evidence/notes into it; (4) audited repair removes/consolidates the duplicate; (5) record pre/post counts + selected IDs; (6) apply the index. The migration carries a defensive `DO` block that raises a descriptive exception if any duplicate remains.

### 5.4 Coverage does NOT get two-lane versioning

The unique scope/topic index remains the single canonical coverage row. Conflict handling is §5.2.

### 5.5 Coverage migration packaging

Both changes ship in **one** migration (atomic derivation precondition): extend the `source_basis` text CHECK with `'evidence_derived'` **and** add the exam-wide unique index. No benefit to splitting.

---

## 6. Shared category taxonomy (created in the Competition PR)

No canonical category dimension exists today (category lives only as free-form JSONB keys in `vacancy_by_category`). Create a **shared** taxonomy — it must eventually serve eligibility too, so it is `reservation_categories`, not `exam_categories`.

```sql
create table public.reservation_categories (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  label text not null,
  category_axis text not null default 'vertical'
    check (category_axis in ('vertical','horizontal')),
  sort_order integer not null default 0,
  is_active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.reservation_category_aliases (
  id uuid primary key default gen_random_uuid(),
  category_id uuid not null references public.reservation_categories(id) on delete cascade,
  alias text not null unique,
  created_at timestamptz not null default now()
);
```

Seed codes: `general`, `ews`, `obc`, `sc`, `st`. Aliases: `ur → general`, `gen → general`, `obc_ncl → obc`.

**FK posture:**
- `exam_candidate_counts.reservation_category_id` → FK.
- `exam_competition_metric_evidence.reservation_category_id` → FK.
- `exam_competition_metrics` cannot FK directly (categories remain JSONB keys) — its JSON-validation trigger MUST verify every key against `reservation_categories.code`.
- If cutoff/vacancy facts are later normalized into child rows, those rows use the FK directly.

**RLS:** admin/service-role only (reference data; no end-user read).

---

## 7. `source_registry` (dependency resolved — do NOT recreate)

`public.source_registry` already exists and is actively used (permission-gated source-management APIs; canonical `official_url`; trust/verification/lifecycle fields; existing UUID FK `syllabus_documents.source_id → source_registry.id`).

- **Do NOT** add `evidence_kind` values (`official_notification`, `official_result`, …) to `source_registry.source_type`. `source_type` = **how the origin is accessed** (`official_html | official_pdf | rss | api | sitemap | aggregator`); `evidence_kind` = **what the artifact proves** — kept on the evidence child row. Example: an official result PDF is `source_type='official_pdf'` + `evidence_kind='official_result'`.
- FK: `source_id uuid references public.source_registry(id) on delete set null`. The evidence row keeps its own `evidence_url` (the cited notification/result PDF can be more specific than the registry's `official_url` root; legacy `source_registry.source_url` was removed).
- **Promotion validation for primary evidence** supporting cutoff / vacancy / candidate-count facts requires: source exists, `is_active=true`, `is_verified=true`, `discovery_only=false`, `source_type != 'aggregator'` (aggregators are discovery-only, never final official proof), and (`evidence_url` OR `document_asset_id`) present. `reviewed_analysis` may support a difficulty assessment but is **not** accepted as the sole primary evidence for official vacancy/cutoff/applied/appeared counts.
- **RLS:** leave `source_registry` RLS unchanged (no broad redesign). Enable RLS on the three new tables; keep competition evidence behind service-role permission-gated APIs; add migration tests proving ordinary authenticated users cannot directly select/mutate evidence rows.

---

## 8. Mixed-Format PDF — OD-1…OD-3

| OD | Resolution |
|---|---|
| **OD-1** | **Option B** — reject mixed PDFs loudly and document the split/re-upload workaround. (v1 applies one two-column MCQ strategy to every selected page and supports only `pyq_paper`; page-range infrastructure would not extract non-MCQ sections anyway.) |
| **OD-2** | **B1 admin-declared** detection via validated `document_assets.metadata.mixed_format=true`. Do **not** add B2 heuristic detection yet. |
| **OD-3** | Not applicable now. Record that a later Option A must use the proposed `document_format_segments` child table with **no backfill**. |

**Required behavior:**

```text
mixed flag
  → ExtractionMixedFormatError before OCR
  → zero question writes
  → error links to the split-and-reupload SOP
```

No migration required for the metadata approach (unless metadata validation needs a DB constraint). Create the SOP doc (`docs/engineering/mixed-format-pdf-workaround-v1.md`).

---

## 9. Locked implementation order

Two **sequential PRs** (not one combined PR) for the competition pair; independent PRs for the rest. "Serial delivery" = same owner/agent, no concurrent branches touching the shared schema/read models, PR 2 based on merged PR 1, migration numbers resolved from the live `schema_migrations` ledger (never inferred from filenames), migrations immutable once merged.

1. **PR 1 — Competition structure**
   `reservation_categories` + aliases; additive `cutoff_by_category` / `difficulty_assessment` columns; two-lane competition revisions + §2.1 DDL/CHECKs (incl. field-ownership + lineage constraints); `metric_kind` + §1.3 legacy disposition (fail-closed) + **§1.4 current-lane initialization** (fail-closed duplicate resolution, version/lineage backfill, per-basis legacy trust disposition, zero-availability-loss assertion); §1.5 JSONB contracts + validation trigger; shared current-published selector; `exam_competition_metric_evidence` child table + immutability triggers + **published-parent UPDATE guard** (§2); promotion RPC + evidence/source trust + claim-value-match validation; OD-5 selective legacy normalization (incl. bare-number → `{marks}` conversion); §1.2 **PR-1 half** of the ratio contract (additive fields; existing `selection_ratio` key preserved as deprecated alias); UI/read parity.
2. **PR 2 — Applied-vs-Appeared** (branch from merged PR 1)
   `exam_candidate_counts` + `exam_candidate_count_evidence`; RLS (exact reviewed/locked predicate); `scope_kind` + phase/cycle CHECK + write validator; same revision model + shared taxonomy; conservative OD-6 legacy migration; §1.2 **PR-2 half**: atomic switch of ratio derivation + all ratio consumers (appeared → applied → null); pressure explanation fix (no change to `competition_pressure_score` itself).
3. **PR 3 — Mixed-Format Option B** (independent)
   `document_assets.metadata.mixed_format` declaration; pre-OCR `ExtractionMixedFormatError`; operator control + SOP doc. No migration unless metadata validation needs a DB constraint.
4. **PR 4 — Coverage derivation** (coordinate migration slot after PR 2)
   `source_basis='evidence_derived'` CHECK extension + exam-wide unique index (one migration); manual derivation endpoint; §5.2 conflict rules; exclude `evidence_derived` from `score_snapshots.py` `coverage_component` (test-enforced); delta reporting; fail-closed exam-wide duplicate resolution.

Competition and Applied/Appeared must not run concurrently (shared read models + operator surface). Mixed-PDF is independent. Coverage is logically independent but coordinates its migration slot after PR 2.

---

## 10. Path to authority (gate amendments + operator sign-off)

This record becomes authoritative only when both steps complete, in order:

1. **Amend the four gate documents** to replace their `OPERATOR DECISION REQUIRED` sections with the resolutions above:
   - **Competition-Cutoffs gate:** OD-1…OD-11 resolved; add the `cutoff_by_category`/`difficulty_assessment` naming amendment, the §1.2 transitional ratio contract, the two-lane revision model + §2.1 DDL, `metric_kind` + §1.3 legacy disposition, the evidence child schema + immutability triggers, and the `reservation_categories` taxonomy.
   - **Applied-vs-Appeared gate:** OD-1…OD-6 resolved; add `exam_candidate_counts` + `exam_candidate_count_evidence`, `scope_kind`, the revision model + NULL-safe uniqueness, shared taxonomy, OD-6 Option B backfill, the PR-2 atomic ratio switch.
   - **Mixed-Format-PDF gate:** OD-1 = B, OD-2 = B1, OD-3 = N/A-now (record Option A child-table + no-backfill for later).
   - **Evidence-Coverage gate:** OD-1…OD-6 + OD-5a resolved; add the total bucket table, the complete §5.2 conflict rules, break-the-edge-as-test-invariant, single-migration packaging, fail-closed duplicate resolution, and the explicit "no two-lane versioning for coverage" note.
2. **Record operator approval** in each amended gate and flip this document's status to `OPERATOR APPROVED`.

Until both steps complete, no implementation PR may dispatch.

Implementation checklist and sequencing: `docs/status/J3-Implementation-Checklist-2026-07-02.md`.
