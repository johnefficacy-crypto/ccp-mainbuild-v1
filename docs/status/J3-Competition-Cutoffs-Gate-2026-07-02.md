# Phase/Category Competition Cutoffs & Competition-Metrics Structure Gate — J3

- Document type: J3 sub-item domain contract — phase/category competition cutoffs, `cutoff_by_category`/`vacancy_by_category`/`difficulty_assessment` JSONB schema, evidence model, reviewer lifecycle.
- Status: **OPERATOR APPROVED — 2026-07-02.** Resolutions from docs/status/J3-OD-Resolutions-Locked-2026-07-02.md are approved by the operator (recorded on PR #861, 2026-07-02). Implementation may dispatch as PR 1 (Competition structure, serial anchor) per docs/status/J3-Implementation-Checklist-2026-07-02.md.
- Date: 2026-07-02
- Parent track: `J3 — competition metrics structure` (checklist: "Competition metrics structure DEFERRED — CONTRACT-FIRST: Opaque JSONB `cutoff_trend`/`vacancy_by_category`; no locked schema. Needs domain contract + JSON/schema decision + evidence model + reviewer lifecycle.")
- Authority: `docs/architecture/domain-model.md` (entity canonicity); `docs/status/Exam-Cycle-Setup-D11-Competition-Applicability-Decision-2026-06-23.md` (competition applicability + lifecycle-as-evidence); `CLAUDE.md` (verified-only reads, determinism > heuristics, no new AI writes).
- Prerequisite gates: D11 (competition applicability) merged; migrations 055/057 (table + RLS) landed.
- Blocks: any J3 competition-structure implementation PR. Does NOT block unrelated J-track work.

---

## How to use this document

This gate **reconciles the existing implementation** — the `exam_competition_metrics` table, RLS, CMS write path, review endpoint, planner read helper, and both operator UIs already exist. It does not design from scratch. Every section below encodes the approved resolutions from `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md`; nothing remains PROPOSED and no section may be read against the old proposed contract.

**Operator sign-off is recorded.** All OD-1…OD-11 items are resolved (Section F below) and this body has been reconciled to those resolutions; operator approval was recorded on PR #861 (2026-07-02), and implementation may proceed following `docs/status/J3-Implementation-Checklist-2026-07-02.md` PR 1.

**Serial delivery note:** J3 touches `study_os/competition_context.py` and the Exam Workspace Competition surface. It does NOT touch routing/navigation/AdminShell, so the serial-delivery rule does not apply, but the CMS write path and the aspirant read helper must move together (a schema change breaks both).

---

## Section 0 — Actual implementation baseline

### 0.1 Table (`exam_competition_metrics`, migration 055)

```sql
create table public.exam_competition_metrics (
  id uuid primary key default gen_random_uuid(),
  exam_id uuid not null references public.exams(id) on delete cascade,
  exam_cycle_id uuid references public.exam_cycles(id) on delete cascade,
  exam_phase_id uuid references public.exam_phases(id) on delete set null,

  vacancy_total integer check (... >= 0),
  vacancy_by_category jsonb not null default '{}'::jsonb,
  applicant_count integer check (... >= 0),
  selection_ratio numeric(8,6) check (... between 0 and 1),

  cutoff_trend jsonb not null default '{}'::jsonb,
  difficulty_trend jsonb not null default '{}'::jsonb,
  competition_pressure_score numeric(5,2) check (... between 0 and 100),

  source_basis text default 'manual'
    check (source_basis in ('manual','official','reviewed_analysis','derived','model_generated')),
  confidence_score numeric(4,3) default 0 check (... between 0 and 1),
  evidence_count integer default 0 check (>= 0),
  reviewer_status text default 'draft'
    check (reviewer_status in ('draft','pending_review','reviewed','locked','rejected')),

  reviewed_by uuid references public.profiles(id) on delete set null,
  reviewed_at timestamptz,
  reviewer_notes text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

- **Entity canonicity is already correct:** the row is `exam_id`-scoped (FK to `public.exams`), optionally narrowed by `exam_cycle_id` and `exam_phase_id`. No `recruitment_id` — competition intelligence is exam-master data, not a recruitment notification. This is compliant with domain-model.md and must be preserved.
- **A reviewer lifecycle already exists** (`draft → pending_review → reviewed → locked → rejected`), with `reviewed_by`/`reviewed_at`/`reviewer_notes`.
- **`cutoff_trend`, `vacancy_by_category`, `difficulty_trend` are opaque JSONB** — no `jsonb` shape check, no domain constraint. This is the gap.

### 0.2 RLS (migration 057)

- `enable row level security`. Read policy `exam_competition_metrics_read_reviewed`: authenticated users see rows only when `reviewer_status in ('reviewed','locked')`, OR the caller is an admin. `_admin_all` policy grants admins full read/write. Service role bypasses RLS; app applies authoritative filtering. **RLS is present and compliant.**

### 0.3 CMS write path (`admin_exam_intel_cms.py`)

- `POST /exam-competition-metrics` (perm `PERM_CMS`): whitelists `_COMPETITION_FIELDS` (includes `vacancy_by_category`, `cutoff_trend`, `difficulty_trend`, `evidence_count`, `source_basis`, `confidence_score`, `metadata`). Forces `reviewer_status='draft'`. Validates `exam_id` resolves, and range-checks `selection_ratio`, `confidence_score`, `competition_pressure_score`, and `source_basis` enum. **`_validate_competition_payload` does NOT validate the shape or contents of `cutoff_trend`/`vacancy_by_category`/`difficulty_trend` at all** — any JSON is accepted.
- `PATCH /exam-competition-metrics/{id}` mirrors the same whitelist; audited via best-effort `_audit`.

### 0.4 Review endpoint (`admin_exam_intelligence.py`)

- `PATCH /competition-metrics/{id}/review` (perm `ADMIN_PERM`): sets `reviewer_status` to the requested value + `reviewed_by`/`reviewed_at`. **No transition matrix is enforced** — any status may jump to any status (the frontend hints the graph, the backend does not gate it). Contrast with the J2-A′ topic-prerequisite gate, which locks an explicit transition matrix and CAS.

### 0.5 Aspirant read helper (`exam_intelligence/competition.py`)

- Reads only `reviewer_status in ('reviewed','locked')` (verified-only compliant).
- **Documents a de-facto `cutoff_trend` convention** that is NOT enforced anywhere: `{ "<category>": <number> }` or `{ "<category>": [<n1>,<n2>,...] }`; `cutoff_series()` flattens to `{category: [{year, marks, phase_slug}]}` and silently drops anything non-numeric.
- `vacancy_series()` reads `vacancy_by_category` as `{category: <number>}`, collapses to earliest phase per cycle (vacancy treated as cycle-level, not phase-level).
- No AI/inference; empty in → empty out.

### 0.6 Operator UIs — TWO CONTRADICTORY SHAPES IN USE (core finding)

- `CompetitionPanel.jsx` (Exam Workspace) writes `cutoff_trend` and `difficulty_trend` as **string enums** — `cutoff_trend ∈ {"rising","flat","falling"}`, `difficulty_trend ∈ {"harder","stable","easier"}` — and never writes `vacancy_by_category`. It displays them as a single badge.
- `competition.py` (aspirant read) expects `cutoff_trend` to be a **category→number(s) map**. A `"rising"` string is silently dropped by `cutoff_series()` (not a dict), so operator-entered workspace data produces an EMPTY aspirant cutoff series.
- `CompetitionMetricsTable.jsx` (review surface) displays vacancy/applicants/ratio/pressure/source/confidence/status — but **does not display `cutoff_trend` or `vacancy_by_category` at all**, so a reviewer cannot see the very fields they are approving.
- Net: the field name `cutoff_trend` means one thing to the writer, another to the reader, and is invisible to the reviewer. This is exactly the "opaque JSONB, no locked schema" deferral the checklist flags.

---

## Section A — Gaps J3 closes

| # | Gap | Consequence |
|---|---|---|
| G-1 | No locked JSON schema for `cutoff_trend`/`vacancy_by_category` | Writer/reader/reviewer disagree on shape; aspirant cutoff series silently empties. |
| G-2 | Workspace writes string enums into `cutoff_trend`/`difficulty_trend` | Contradicts the read helper's category-map convention; heuristic label, not deterministic data. |
| G-3 | No shape validation in CMS write path | Malformed JSON passes review and reaches aspirants; violates determinism > heuristics. |
| G-4 | No phase/category breakdown model | `exam_phase_id` exists but cutoffs are not modeled per (phase, category); vacancy is forced cycle-level by collapse heuristic. |
| G-5 | Review endpoint has no transition matrix / CAS | Any status → any status; no reopen-notes discipline (unlike J2-A′). |
| G-6 | Evidence model is a bare `evidence_count` integer + `metadata.source_url` | No linkage to actual evidence rows; a reviewer cannot audit provenance; `evidence_count` is unverifiable and self-asserted. |
| G-7 | Reviewer surface omits cutoff/vacancy JSONB | Reviewer approves fields they cannot see. |

---

## Section B — Locked domain schema (LOCKED per resolutions §1.1/§1.5/§6; sign-off pending)

**Naming (additive deprecation, §1.1):** the canonical columns are **new additive columns** `cutoff_by_category` (replacing legacy `cutoff_trend`) and `difficulty_assessment` (replacing legacy `difficulty_trend`). Legacy columns are **deprecated in place** — never renamed or dropped in this PR (PostgREST schema-reload vs. app-rollout ordering); they are removed only in a later cleanup migration after all consumers and historical values are verified. `vacancy_by_category` keeps its name with a locked shape.

### B.1 `cutoff_by_category` (LOCKED shape, §1.5)

Category-keyed, per row (a row is scoped to one cycle and, for `metric_kind='phase_cutoff'`, exactly one phase). Cutoffs are per category for the row's phase; the year comes from the joined cycle, so it is NOT duplicated in the JSONB.

```jsonc
{
  "general":  { "marks": 105.34, "max_marks": 200 },
  "obc":      { "marks":  98.10, "max_marks": 200 },
  "sc":       { "marks":  88.00, "max_marks": 200 },
  "st":       { "marks":  85.50, "max_marks": 200 },
  "ews":      { "marks": 101.20, "max_marks": 200 }
}
```

- Keys: lowercase category codes validated against `reservation_categories.code` (see B.4).
- Value: object with required `marks` (number ≥ 0), optional `max_marks` (number > 0). **There is NO `stage` field** (OD-3): `exam_phase_id` is the canonical phase identity; a second `stage` field inside the JSONB would create a contradictory source of truth.
- Bare string / bare number / list values are rejected by the §1.5 validation trigger. The legacy `"rising"/"flat"/"falling"` string form is **RETIRED**; qualitative direction is a DERIVED read-time computation in backend code (`competition.py`, ≥ 2 comparable cycles with matching phase, category and non-null `max_marks`, else `null`) — never a stored field (OD-3).
- Legacy `cutoff_trend` rows are handled by OD-5 selective normalization: valid category→number maps convert to object form (`{"general": 120}` → `{"general": {"marks": 120}}`); strings/bare numbers/lists move to `metadata.legacy_*` per §1.3 disposition. Never manufacture marks from `"rising"` or an unlabeled number.

### B.2 `vacancy_by_category` (LOCKED shape, §1.5)

```jsonc
{ "general": 442, "obc": 285, "sc": 158, "st": 79, "ews": 106 }
```

- Category-keyed, **non-negative integers only** (no nulls inside the map — omit the key instead; `{}` means "no breakdown"). Keys validated against `reservation_categories.code`.
- `vacancy_total` remains the authoritative cycle total. OD-4 sum rule: `sum(categories) > vacancy_total` → **hard error**; `sum(categories) < vacancy_total` → **warning** (official notices legitimately omit buckets); a `breakdown_complete` boolean makes strict equality enforceable **only when `breakdown_complete = true`**.
- Vacancy stays cycle-level (owned by `metric_kind='cycle_summary'` rows, `exam_phase_id IS NULL`); it is NOT phase-scoped.

### B.3 `difficulty_assessment` (LOCKED shape, §1.5)

The free string (`difficulty_trend`) is retired. Locked shape: `{ "level": "harder" | "stable" | "easier", "basis": "<text 8–500 chars>" }`; the validator enforces the `level` enum and `basis` length; a bare string is rejected. **Descriptive only** — it does NOT drive planner scoring (OD-3; parallels J2-A′ PD-4 strength).

### B.4 Category taxonomy (LOCKED, OD-1 + §6)

v1 canonical **vertical** categories: `general`, `ews`, `obc`, `sc`, `st` — seeded into the shared `reservation_categories` table (created in this PR; it also serves eligibility, so one canonical vocabulary spans eligibility and competition). Aliases normalized via `reservation_category_aliases`: `ur → general`, `gen → general`, `obc_ncl → obc`. **PwBD / ex-servicemen / domicile are a separate horizontal dimension added later — never mixed into this single vertical axis.** `exam_competition_metrics` JSONB keys cannot FK directly, so the §1.5 validation trigger verifies every key against `reservation_categories.code`.

### B.5 Phase/category breakdown model (LOCKED, OD-11)

- One table with **`metric_kind ∈ {cycle_summary, phase_cutoff}`**: `phase_cutoff` rows require `exam_phase_id` and own cutoffs/difficulty; `cycle_summary` rows require `exam_phase_id IS NULL` and own vacancy/pressure/counts. DB CHECKs (resolution §2.1 `ecm_kind_field_ownership`) prohibit cross-granularity fields.
- A cutoff fact is `(exam_id, exam_cycle_id, exam_phase_id, category)`-addressable: `exam_phase_id` selects the phase, `cutoff_by_category` map keys select the category. Vacancy is `(exam_id, exam_cycle_id, category)`-addressable, cycle-level.
- `exam_cycle_id` is required for every new-model row (`metric_kind IS NOT NULL`); cycle-less rows are not supported in v1 (legacy cycle-less rows go to operator triage, §1.3).
- Cross-cycle "trend" series is a READ-TIME aggregation over rows (as `competition.py` already does), never a stored trend blob.

### B.6 Row identity, uniqueness & supersession (LOCKED, OD-10/OD-11 + §2/§2.1)

The pre-J3 table has no uniqueness/supersession rule, so multiple `reviewed`/`locked` rows for one scope can coexist and readers diverge. Resolved as the **two-lane revision model**:

1. Per `(scope, metric_kind)`: one **current published** row (`reviewer_status ∈ {reviewed, locked}`, `is_current_published = true`) and at most one **current working** row (`reviewer_status ∈ {draft, pending_review}`, `superseded_at IS NULL`). Columns: `version_no`, `supersedes_id`, `superseded_at`, `is_current_published`.
2. Enforced by the **executable NULL-safe partial unique indexes + consistency CHECKs in resolution §2.1** (a plain UNIQUE over nullable scope columns does not enforce uniqueness); version-lineage constraints (self-FK `supersedes_id`, `version_no > 0`, per-scope version uniqueness).
3. **Deterministic selection:** all readers use one shared current-published selector — no per-caller "best row" heuristics.
4. **Cross-granularity leakage prevented** by the `metric_kind` field-ownership CHECKs (gated on `metric_kind IS NOT NULL` during the §1.3 migration window; the disposition migration fails closed if any row is left unassigned).

---

## Section C — Evidence model (LOCKED per OD-6 + resolution §4/§7; sign-off pending)

- Keep `source_basis` (enum) and `confidence_score` (0–1).
- **G-6 fix — the dedicated `exam_competition_metric_evidence` child table is MANDATORY** (OD-6; full schema in resolution §4). There is **no `metadata.evidence` array** — the array-in-metadata option was rejected; per-claim evidence lives in first-class child rows (`claim_field`, `reservation_category_id`, `evidence_kind`, `evidence_role`, `source_id` → `source_registry`, `document_asset_id`, `evidence_url`/`source_label`/`source_page`/`source_excerpt`, `claim_value`, server-computed `evidence_key`).
- **Append-only, DB-enforced immutability (§4):** evidence rows are attached only while the parent revision is `draft`/`pending_review`; corrections in the working lane are delete-and-reinsert, never UPDATE. Triggers block INSERT/UPDATE/DELETE on evidence once the parent is published, and block DELETE of a published parent (the FK cascade fires only for genuinely-draft cleanup).
- **`evidence_count` is DERIVED by counting the child rows of that revision** and is removed from operator write input. There is no "active" sub-state; post-publication corrections happen by cloning a new working revision with fresh evidence (§2).
- **Promotion validation:** every populated high-risk claim needs qualifying **primary** evidence whose `claim_value` matches the current parent field/category value (stale evidence fails). Source trust per §7: `is_active`, `is_verified`, `discovery_only=false`, `source_type != 'aggregator'`, url-or-doc present; `reviewed_analysis` is never sole primary evidence for official vacancy/cutoff counts.
- **RLS:** enable RLS on the child table with no anon/authenticated direct access — service-role, permission-gated FastAPI routes only; role checks from app metadata, not the deprecated `profiles.is_admin`.
- No AI-authored evidence. `source_basis='model_generated'` rows may remain **draft only** (OD-2): a human must attach evidence and re-base `source_basis` to `official`/`reviewed_analysis` before submission; revalidated on submit and on every promotion.

---

## Section D — Reviewer lifecycle (LOCKED alignment)

The lifecycle states already exist; this gate locks the transition discipline (currently absent, G-5) under the **two-lane revision model** (OD-7/OD-8, resolution §2).

```
working lane:   draft → pending_review → (promotion RPC) → published
                                       ↘ rejected → draft (reset)
published lane: reviewed → locked; locked → reviewed (audited, notes required —
                lifecycle-status change only, content columns stay frozen)
correction:     reopen_for_edit (notes required) CLONES the published row into a
                new draft revision — the published row is NEVER edited in place
                and NEVER returned to draft
```

- **Published rows are immutable in place (OD-7):** a `BEFORE UPDATE` guard on `exam_competition_metrics` freezes all content columns when `reviewer_status ∈ ('reviewed','locked')`; only lifecycle/supersession columns may change, and only in state-machine-permitted combinations (§2). Correction always goes through notes-required `reopen_for_edit`, which clones into a new working-lane draft while the published row stays aspirant-visible.
- **Promotion is an atomic RPC (§2):** validate shape + evidence → mark the previous published revision superseded (`superseded_at`, `is_current_published=false`) → mark the new revision current-published → preserve the previous row and its evidence. Two lanes per `(scope, metric_kind)`: one current published + at most one current working row.
- **Enforcement is a DB RPC / state machine (OD-8)** with matching app-layer validation — multiple service-role write surfaces make app-only enforcement insufficient. Out-of-matrix jumps are rejected (409 at the API).
- Only `reviewed`/`locked` are aspirant-readable (already enforced by RLS + read helper). **Correction (checkpost):** `competition_context.py` reads `reviewer_status in ('locked','reviewed')` with **locked preferred** (`_READABLE_STATUSES = ("locked","reviewed")`, l.19/137) — it is NOT locked-only. This gate PRESERVES that existing reviewed+locked / locked-preferred contract (matching AGENTS.md "reviewed or locked rows feed the planner; locked preferred"); it does not redefine it. Any move to locked-only would be a separate OPERATOR DECISION with the required runtime/UI migration.
- LOCKED: `PATCH /competition-metrics/{id}/review` delegates to the DB RPC/state machine and rejects out-of-matrix jumps with 409 (today it accepts any jump). `locked → reviewed` and `reopen_for_edit` both require `reviewer_notes`.
- LOCKED: shape validation (Section B, §1.5 trigger) MUST run on the `draft → pending_review` submit AND on promotion, together with the §4 claim-value-matched primary-evidence check, so malformed or unevidenced content cannot be promoted even if inserted before validation existed.
- SUPERSEDED — the former open question "does editing a reviewed/locked row require review-rollback first" is resolved by OD-7: no in-place edit or rollback of published rows exists at all; `reopen_for_edit` clones a new draft revision.

---

## Section E — Migration decision (LOCKED per resolutions §1.1–§1.5, §2/2.1, §4, §6; sign-off pending)

**Additive replacement columns + validator-enforced JSONB contracts + DB RPC/state machine.** (SUPERSEDED — the earlier "structured JSONB, NOT new columns / app-layer transition enforcement" proposal is replaced by §1.1 additive deprecation and OD-8 DB enforcement.)

PR 1 migration content (order matters; see `docs/status/J3-Implementation-Checklist-2026-07-02.md` PR 1):
1. **Shared taxonomy (§6):** create `reservation_categories` + `reservation_category_aliases`; seed `general`/`ews`/`obc`/`sc`/`st` + aliases; admin/service-role-only RLS. Reuse `source_registry` (§7) — do NOT recreate it.
2. **Additive columns (§1.1):** add `cutoff_by_category` and `difficulty_assessment`; legacy `cutoff_trend`/`difficulty_trend` deprecated in place, dropped only in a later cleanup migration.
3. **Two-lane model columns + `metric_kind` (OD-10/OD-11):** `metric_kind ∈ {cycle_summary, phase_cutoff}`, `version_no`, `supersedes_id`, `superseded_at`, `is_current_published`.
4. **Fail-closed legacy disposition (§1.3):** deterministic preflight classification; cycle-only rows → `cycle_summary`; combined phased rows split; phase-less cutoff payloads and cycle-less rows → operator triage via `metadata.legacy_*` + working drafts; published rows never returned to draft; terminal `DO`-block asserts zero rows left `metric_kind IS NULL`, zero-loss field counts, and no published row losing aspirant-visible data.
5. **OD-5 selective normalization:** valid category→number maps normalized into `cutoff_by_category` (bare number → `{"marks": n}`); strings/lists to `metadata.legacy_*`; pre/post counts recorded as migration evidence.
6. **Current-lane initialization (§1.4, fail-closed):** duplicate report; per-lane current-marker backfill (multiple published rows → operator-audited canonical selection, never auto-keep-latest); version/lineage backfill; per-basis legacy trust disposition (`model_generated` published rows NOT auto-grandfathered); zero-availability-loss terminal assertion before indexes/reader switch.
7. **§2.1 NULL-safe DDL:** scope-specific partial unique indexes (published + working lanes), field-ownership CHECKs, `ecm_new_model_requires_cycle`, lineage constraints — enabled only after §1.3/§1.4 complete.
8. **§1.5 validation trigger:** locked JSONB shapes for `cutoff_by_category` / `vacancy_by_category` (OD-4 sum rule + `breakdown_complete`) / `difficulty_assessment`, keys validated against `reservation_categories.code`.
9. **Evidence child table (§4, MANDATORY):** `exam_competition_metric_evidence` + append-only immutability triggers + published-parent DELETE guard + published-parent BEFORE UPDATE content-freeze guard (§2) + its own RLS (verify `SELECT * FROM pg_policies WHERE tablename='exam_competition_metric_evidence'`; app-metadata roles, not `profiles.is_admin`). Do not mark live/operator steps complete from code inspection — use `VERIFY DB`/`OPERATOR PENDING`.
10. **Lifecycle RPC/state machine (OD-8):** DB-enforced transitions + CAS + atomic promotion/supersession + claim-value-matched primary-evidence validation, with matching app-layer validation. App-only enforcement is rejected — service-role write surfaces bypass it.
11. **§1.2 ratio contract, PR-1 half:** deprecate `selection_ratio` in place; remove from operator-write allowlists; add derived response fields (`selection_rate`, `candidates_per_vacancy`, `ratio_denominator`, `selection_ratio_legacy`) as **null until PR 2**; the existing `selection_ratio` response key is preserved as a deprecated alias with the verbatim legacy value — zero behavior change in PR 1; the atomic consumer switch happens in PR 2 with `exam_candidate_counts` (denominator preference `appeared → applied → null`).
12. No change to `exam_id`/`exam_cycle_id`/`exam_phase_id` entity canonicity (no `recruitment_id`, ever). Migration numbers resolved from the live `schema_migrations` ledger at implementation time; do not hardcode.

---

## Section F — OPERATOR DECISIONS — RESOLVED (pending sign-off)

All eleven items are RESOLVED (2026-07-02); operator sign-off on the PR is pending. Resolutions are folded in verbatim-in-substance from `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md` §1 (OD-1…OD-11). See "Resolved additions folded in" below for the structural amendments (§1.1–§1.5, §2.1, §4, §6, §7) and the resolution doc for full SQL/detail.

| ID | Resolution |
|---|---|
| **OD-1** | v1 canonical **vertical** categories: `general`, `ews`, `obc`, `sc`, `st`. Aliases normalized via the shared taxonomy (`ur → general`, `gen → general`, `obc_ncl → obc`). PwBD / ex-servicemen / domicile are a **separate horizontal dimension** added later — never mixed into this single vertical axis. |
| **OD-2** | `source_basis='model_generated'` rows may remain **`draft` only**. Before submission a human must attach evidence and change `source_basis` to `official` or `reviewed_analysis`. Revalidate on the `submit`, `→ reviewed`, and `→ locked` transitions. |
| **OD-3** | Cutoff/difficulty **direction is derived at read time, never stored**. Derive direction only across **≥ 2 comparable cycles** matching the same phase, category and non-null `max_marks`; otherwise return `null`. `difficulty_assessment` is a structured **descriptive** fact — **not** planner input. **Remove `stage` from each cutoff object** (`exam_phase_id` is the canonical phase; a second `stage` field creates a contradictory source of truth). Direction derivation lives in **backend code** (`competition.py`), not SQL. |
| **OD-4** | `sum(categories) > vacancy_total` → **hard error**. `sum(categories) < vacancy_total` → **warning** (official notices legitimately omit buckets). Add a `breakdown_complete` boolean; strict equality is enforced **only when `breakdown_complete = true`**. |
| **OD-5** | **Selective normalization, not grandfathering.** Normalize valid category→number maps into `cutoff_by_category`. Move strings (`"rising"`), bare numbers and lists into `metadata.legacy_*` and clear the canonical field. **Disposition depends on lane (reconciled with OD-7 — published rows are never reopened in place):** a malformed `draft`/`pending_review` row returns to `draft`; a malformed **reviewed/locked** row keeps its published status (valid fields stay aspirant-visible; clearing the malformed canonical field loses nothing user-visible) and a **separate working draft revision** is created carrying the `metadata.legacy_*` payload for operator correction. Never manufacture marks from `"rising"` or an unlabeled number. Record pre/post counts in migration evidence. Full legacy disposition (incl. `metric_kind` assignment) in resolution §1.3. |
| **OD-6** | Dedicated **`exam_competition_metric_evidence` child table** (full schema in resolution §4). `evidence_count` is **derived by counting the child rows of that revision** (append-only model — no "active" sub-state) and is removed from operator write input. |
| **OD-7** | Reviewed/locked rows are **not editable in place**. A notes-required **`reopen_for_edit`** operation **clones** the published row into a new `draft` revision (it does **not** move the published row back to `draft` — see the two-lane model) preserving aspirant-visible published intelligence during correction. |
| **OD-8** | Enforce lifecycle + CAS through a **DB RPC / state machine**, with matching app-layer validation. Multiple service-role write surfaces make app-only validation insufficient. |
| **OD-9** | **Workspace → Competition remains the canonical editor.** The review table (`CompetitionMetricsTable.jsx`) is the lifecycle/review surface and MUST display all cutoff, vacancy and evidence fields. **No new surface** (no-new-surface rule). |
| **OD-10** | **Two current lanes per (scope, `metric_kind`)** — one **current published** row (`reviewer_status ∈ {reviewed, locked}`) and at most one **current working** row (`reviewer_status ∈ {draft, pending_review}`). Columns: `version_no`, `supersedes_id`, `superseded_at`, `is_current_published`. Enforced by the **executable NULL-safe partial-index DDL and consistency CHECKs in resolution §2.1** (a plain UNIQUE over nullable scope columns does not enforce uniqueness). All readers use one shared current-published selector — no per-reader "best row" heuristic. |
| **OD-11** | Keep one table; add **`metric_kind ∈ {cycle_summary, phase_cutoff}`**. `cycle_summary` requires `exam_phase_id IS NULL` and owns vacancy / pressure; `phase_cutoff` requires a phase and owns cutoffs / difficulty. DB CHECKs prohibit cross-granularity fields. **`exam_cycle_id` is required for every new-model row** (`metric_kind IS NOT NULL`): competition facts are cycle-anchored; cycle-less rows are NOT supported in v1 (legacy cycle-less rows go to operator triage per §1.3). Cross-granularity CHECKs are gated on `metric_kind IS NOT NULL` so undisposed legacy rows do not violate them mid-migration; the disposition migration fails closed if any row is left unassigned. |

### Section F.1 — Resolved additions folded in

The following structural amendments accompany the OD resolutions (same pending-sign-off status). Full DDL/detail lives in `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md`; this gate references rather than duplicates the SQL.

- **Additive-deprecation naming (§1.1):** add `cutoff_by_category` (replacing legacy `cutoff_trend`) and `difficulty_assessment` (replacing legacy `difficulty_trend`) as **new** columns — backfill, switch consumers, then deprecate. No in-place rename/drop (PostgREST schema-reload vs. app-rollout ordering). Legacy columns removed only in a later cleanup migration.
- **Transitional two-step ratio contract (§1.2):** `selection_ratio` is **deprecated in place**. PR 1 is additive with zero behavior change — the existing `selection_ratio` response key is preserved as a deprecated alias, and the derived fields (`selection_rate`, `candidates_per_vacancy`, `ratio_denominator`, `selection_ratio_legacy`) are **null until PR 2** introduces `exam_candidate_counts` and switches all ratio consumers atomically (denominator preference `appeared → applied → null`).
- **Two-lane revision model + §2.1 NULL-safe DDL/CHECKs:** `metric_kind ∈ {cycle_summary, phase_cutoff}`; `version_no` / `supersedes_id` / `superseded_at` / `is_current_published`; scope-specific partial unique indexes (NULL-safe), field-ownership CHECKs (cycle rows cannot carry cutoff/difficulty; phase rows cannot carry vacancy/pressure/count fields), and version-lineage constraints (self-FK `supersedes_id`, `version_no > 0`, per-scope version uniqueness).
- **Fail-closed legacy `metric_kind` disposition (§1.3):** deterministic preflight classification + split/assignment; published rows never returned to draft; terminal `DO`-block assertion raises if any row is left `metric_kind IS NULL`, any field-value count mismatches (zero-loss), or any published row lost aspirant-visible data. Cross-granularity CHECKs and §2.1 indexes are enabled only after it completes.
- **Fail-closed current-lane initialization (§1.4):** duplicate report, per-lane current-marker backfill (fail-closed on multiple published rows — operator records an audited canonical selection, never auto-keep latest), version/lineage backfill, **per-basis legacy trust disposition** (`manual`/`official`/`reviewed_analysis`/`derived` reviewed/locked rows grandfathered as current-published with prospective evidence requirement; `model_generated` rows NOT auto-grandfathered — fail-closed operator triage), and a **zero-availability-loss** terminal assertion before indexes/reader switch.
- **Canonical JSONB contracts + validation trigger (§1.5):** locked shapes for `cutoff_by_category`, `vacancy_by_category`, and `difficulty_assessment` (`{level, basis}`), keys validated against `reservation_categories.code`, with the OD-5 bare-number → `{marks}` conversion applied before the validator is enabled.
- **`exam_competition_metric_evidence` child table (§4):** per-claim evidence with append-only immutability triggers (INSERT/UPDATE/DELETE blocked once the parent revision is published), the published-parent DELETE guard, and the **published-parent UPDATE guard** (§2 — content columns frozen on published rows; direct service-role attempts are a required test). `evidence_count` derived by counting child rows. Promotion requires qualifying **primary** evidence whose `claim_value` matches the current parent field/category value.
- **Shared `reservation_categories` taxonomy (§6):** created in this PR (serves eligibility too); seed `general`/`ews`/`obc`/`sc`/`st` + aliases; `exam_competition_metrics` JSONB keys validated against `reservation_categories.code` (cannot FK directly).
- **`source_registry` reuse (§7):** already exists — do **not** recreate. `source_type` = how the origin is accessed; `evidence_kind` = what the artifact proves (kept on the evidence child row). Primary-evidence promotion validation requires `is_active`/`is_verified`/`discovery_only=false`/`source_type != 'aggregator'` + url-or-doc; `reviewed_analysis` is never sole primary evidence for official vacancy/cutoff counts.

---

## Section G — Acceptance tests (on operator sign-off; align with Implementation Checklist PR 1)

### G.1 Schema validation (Section B / §1.5)
```
[ ] cutoff_by_category accepts the locked category-object shape ({marks, optional max_marks}); rejects bare string ("rising"), bare number, and list values
[ ] cutoff_by_category rejects a `stage` key inside cutoff objects (OD-3 — exam_phase_id is canonical)
[ ] cutoff_by_category / vacancy_by_category reject keys not in reservation_categories.code; aliases (ur, gen, obc_ncl) normalize on write, not stored raw
[ ] cutoff_by_category rejects negative / non-numeric marks; max_marks must be > 0 when present
[ ] vacancy_by_category accepts {category:int>=0}; rejects negatives, non-ints, and nulls inside the map
[ ] OD-4 sum rule: sum > vacancy_total hard-errors; sum < total warns; strict equality enforced only when breakdown_complete = true
[ ] difficulty_assessment accepts {level ∈ harder|stable|easier, basis 8–500 chars}; rejects free string and bad enum/length
[ ] legacy bare-number map normalizes to {"marks": n} in migration; strings/lists land in metadata.legacy_* with the canonical field cleared
[ ] validation runs on create, on submit, and inside the promotion RPC
```
### G.2 Entity canonicity & metric_kind
```
[ ] row rejects any attempt to set/reference a recruitment_id (column does not exist; assert no cross-wire)
[ ] exam_id is required and must resolve to public.exams; exam_cycle_id required for every metric_kind IS NOT NULL row
[ ] metric_kind CHECKs: cycle_summary requires exam_phase_id IS NULL; phase_cutoff requires a phase
[ ] field-ownership CHECKs: cycle_summary row cannot carry cutoff_by_category/difficulty_assessment; phase_cutoff row cannot carry vacancy/pressure/count fields
```
### G.3 Lifecycle RPC & two-lane model (Section D / §2, §2.1)
```
[ ] out-of-matrix transition (e.g. draft→locked) rejected (409) by the DB RPC/state machine, not only app code
[ ] direct service-role UPDATE of a published row's content columns rejected by the BEFORE UPDATE guard (required test)
[ ] reopen_for_edit requires notes and CLONES a new draft revision; the published row is untouched and stays aspirant-visible
[ ] published rows are never returned to draft in place
[ ] two-lane uniqueness: second current-published row for a scope rejected by the partial unique index; second current working row likewise
[ ] promotion RPC atomically supersedes the previous published revision (superseded_at set, is_current_published flipped) and preserves it + its evidence
[ ] version lineage: version_no > 0, per-scope version uniqueness, no self-supersede; supersedes_id target shares the same scope
[ ] all readers use the shared current-published selector (no per-reader "best row" heuristic)
[ ] only reviewed/locked rows visible to a non-admin (RLS); planner reads reviewed+locked with locked preferred (per `_READABLE_STATUSES = ("locked","reviewed")`) — a reviewed-but-not-locked row must remain planner-visible, never silently dropped
```
### G.4 Evidence child table (Section C / §4, §7)
```
[ ] exam_competition_metric_evidence rows attach only while the parent is draft/pending_review; INSERT on a published parent trigger-rejected
[ ] direct service-role UPDATE/DELETE of evidence under a published parent trigger-rejected; published-parent DELETE trigger-rejected (required tests)
[ ] evidence_count is derived by counting child rows; not operator-writable
[ ] promotion requires qualifying PRIMARY evidence whose claim_value matches the current parent field/category value; stale claim_value fails promotion
[ ] source-trust validation: is_active, is_verified, discovery_only=false, source_type != 'aggregator', url-or-doc present; reviewed_analysis never sole primary evidence for official vacancy/cutoff counts
[ ] model_generated row cannot leave draft without human evidence + source_basis re-base (OD-2)
[ ] RLS: ordinary authenticated users cannot select/mutate evidence rows directly
```
### G.5 Read/UI parity & ratio contract
```
[ ] aspirant cutoff_series/vacancy_series render from cutoff_by_category/vacancy_by_category (no silent empty); derived direction only across >= 2 comparable cycles, else null
[ ] reviewer surface (CompetitionMetricsTable.jsx) DISPLAYS cutoff, vacancy, and evidence fields (G-7 fix, OD-9)
[ ] workspace write path and read helper agree on shape (round-trip test)
[ ] §1.2 PR-1 ratio contract: selection_ratio response key preserved verbatim as deprecated alias; selection_rate/candidates_per_vacancy/ratio_denominator null until PR 2; selection_ratio removed from write allowlists
```

---

## Section H — Files to change (on operator sign-off; per Implementation Checklist PR 1)

| File | Change |
|---|---|
| `app/supabase/migrations/<next>_*.sql` (numbers from the live `schema_migrations` ledger; do not hardcode) | `reservation_categories` + aliases + seed + RLS (§6); additive `cutoff_by_category`/`difficulty_assessment` columns (§1.1); `metric_kind` + two-lane columns; §1.3 fail-closed legacy disposition + OD-5 selective normalization; §1.4 fail-closed current-lane initialization; §2.1 NULL-safe partial unique indexes + field-ownership/lineage CHECKs; §1.5 JSONB validation trigger; **mandatory** `exam_competition_metric_evidence` child table + append-only immutability triggers + published-parent UPDATE/DELETE guards + its RLS; lifecycle RPC/state machine (OD-8). |
| `app/backend/app/api/admin_exam_intel_cms.py` | Write path targets `cutoff_by_category`/`difficulty_assessment`; enforce §1.5 shapes on create/patch; remove `selection_ratio` and `evidence_count` from write allowlists (§1.2, OD-6); evidence attach routes for the child table. |
| `app/backend/app/api/admin_exam_intelligence.py` | `review_competition_metric` delegates to the lifecycle RPC (transition matrix + CAS + reopen-notes + claim-value-matched evidence validation); `reopen_for_edit` clone endpoint. |
| `app/backend/app/exam_intelligence/competition.py` | Read `cutoff_by_category` via the shared current-published selector; derived direction (OD-3, >= 2 comparable cycles else null); drop the tolerant number/list convention once legacy is normalized; §1.2 PR-1 ratio response fields (nulls + deprecated `selection_ratio` alias). |
| `app/backend/app/study_os/competition_context.py` | Switch to the shared selector + new columns; confirm the existing reviewed+locked (locked-preferred) read still holds; do NOT narrow to locked-only without a separate OD. |
| `app/frontend/.../CompetitionPanel.jsx` | Replace string-enum cutoff/difficulty inputs with the `cutoff_by_category` category-object editor (`{marks, max_marks}`, no `stage`) and `difficulty_assessment` `{level, basis}` inputs; add `vacancy_by_category` + `breakdown_complete` inputs; remove the inverse local ratio calc (§1.2); evidence attachment UI (OD-9 — workspace remains the canonical editor; no new surface). |
| `app/frontend/.../CompetitionMetricsTable.jsx` | Display cutoff_by_category, vacancy_by_category, and evidence fields on the review surface (G-7, OD-9); lifecycle actions call the RPC-backed endpoints. |
| backend + frontend tests | Section G, including the required direct service-role trigger tests. |
| `docs/status/career-copilot-checklist.md` | J3 competition-metrics-structure row. |

---

## Appendix A — Code evidence index

- `app/supabase/migrations/055_exam_competition_metrics.sql:8–48` — table shape; `cutoff_trend`/`vacancy_by_category`/`difficulty_trend` opaque JSONB; existing reviewer lifecycle columns; `exam_id`/`exam_cycle_id`/`exam_phase_id` scoping (no `recruitment_id`).
- `app/supabase/migrations/057_competition_policy_rls.sql:11–77` — RLS: verified-only read (`reviewed`/`locked`) + admin-all.
- `app/backend/app/api/admin_exam_intel_cms.py:1996–2065` — `_COMPETITION_FIELDS`, `_validate_competition_payload` (no JSONB shape check), `POST` forces `draft`.
- `app/backend/app/api/admin_exam_intelligence.py:975–1006` — `review_competition_metric`: sets any `reviewer_status` with no transition matrix.
- `app/backend/app/exam_intelligence/competition.py:10–24, 93–112, 160–239` — verified-only read; unenforced `cutoff_trend` category-map convention; `cutoff_series`/`vacancy_series` flatten + silent-drop.
- `app/frontend/src/pages/admin/exam-workspace/panels/CompetitionPanel.jsx:29–105, 176–199` — writes `cutoff_trend`/`difficulty_trend` as STRING ENUMS; never writes `vacancy_by_category`.
- `app/frontend/src/features/admin/exam-intelligence/CompetitionMetricsTable.jsx:13–25, 57–131` — review surface omits cutoff/vacancy columns; declares the lifecycle transitions client-side only.
- `docs/status/Exam-Cycle-Setup-D11-Competition-Applicability-Decision-2026-06-23.md:46–131` — competition applicability, lifecycle-as-usable-evidence, cycle-scoping requirement.

---

*Status: OPERATOR APPROVED — 2026-07-02. Body reconciled with `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md` (2026-07-02); all eleven OPERATOR DECISION items (OD-1…OD-11) are resolved (folded in from §0–§2, §4, §6, §7, §9), and operator approval is recorded on PR #861 (2026-07-02) at PR head de7d3d54f113b4a5492823591a3984b68e25346d. Reconciles the existing `exam_competition_metrics` table/RLS/CMS/review/read implementation; the core defects (opaque JSONB with three contradictory shapes AND the absence of any row-identity/uniqueness rule) are resolved via the additive `cutoff_by_category`/`difficulty_assessment` naming amendment, the two-lane revision model + §2.1 NULL-safe DDL, `metric_kind` + fail-closed legacy disposition, the evidence child table, and the shared `reservation_categories` taxonomy. Implementation per `docs/status/J3-Implementation-Checklist-2026-07-02.md` PR 1.*
