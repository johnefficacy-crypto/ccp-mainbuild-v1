# Phase/Category Competition Cutoffs & Competition-Metrics Structure Gate — J3

- Document type: J3 sub-item domain contract — phase/category competition cutoffs, `cutoff_trend`/`vacancy_by_category` JSONB schema, evidence model, reviewer lifecycle.
- Status: **APPROVED — OD RESOLVED 2026-07-02.** Operator sign-off recorded; resolutions folded in from docs/status/J3-OD-Resolutions-Locked-2026-07-02.md (§0–§2, §4, §6, §7, §9). Every previously-PROPOSED lock is now LOCKED. Implementation per docs/status/J3-Implementation-Checklist-2026-07-02.md PR 1.
- Date: 2026-07-02
- Parent track: `J3 — competition metrics structure` (checklist: "Competition metrics structure DEFERRED — CONTRACT-FIRST: Opaque JSONB `cutoff_trend`/`vacancy_by_category`; no locked schema. Needs domain contract + JSON/schema decision + evidence model + reviewer lifecycle.")
- Authority: `docs/architecture/domain-model.md` (entity canonicity); `docs/status/Exam-Cycle-Setup-D11-Competition-Applicability-Decision-2026-06-23.md` (competition applicability + lifecycle-as-evidence); `CLAUDE.md` (verified-only reads, determinism > heuristics, no new AI writes).
- Prerequisite gates: D11 (competition applicability) merged; migrations 055/057 (table + RLS) landed.
- Blocks: any J3 competition-structure implementation PR. Does NOT block unrelated J-track work.

---

## How to use this document

This gate **reconciles the existing implementation** — the `exam_competition_metrics` table, RLS, CMS write path, review endpoint, planner read helper, and both operator UIs already exist. It does not design from scratch. Every section states either a LOCKED decision, an exact specification, or an **OPERATOR DECISION REQUIRED** item that must be resolved by operator approval and not guessed.

**This document is OPERATOR APPROVED (2026-07-02).** All OD-1…OD-11 items are resolved (Section F below) and every previously-PROPOSED lock is now authoritative. Implementation dispatch is unblocked per `docs/status/J3-Implementation-Checklist-2026-07-02.md` PR 1.

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

## Section B — Locked domain schema (PROPOSED — subject to operator approval)

### B.1 `cutoff_trend` (LOCKED shape proposal)

Category-keyed, phase-aware, per row (a row is already scoped to one cycle and optionally one phase). Cutoffs are per (category) for the row's phase; the year comes from the joined cycle, so it is NOT duplicated in the JSONB.

```jsonc
{
  "general":  { "marks": 105.34, "max_marks": 200, "stage": "final" },
  "obc":      { "marks":  98.10, "max_marks": 200, "stage": "final" },
  "sc":       { "marks":  88.00, "max_marks": 200, "stage": "final" },
  "st":       { "marks":  85.50, "max_marks": 200, "stage": "final" },
  "ews":      { "marks": 101.20, "max_marks": 200, "stage": "final" }
}
```

- Keys: lowercase category codes from a LOCKED enum (see B.4).
- Value: object with required `marks` (number ≥ 0), optional `max_marks` (number > 0), optional `stage` (enum, e.g. `prelims`/`mains`/`interview`/`final` — reconcile with `exam_phases.phase_slug`).
- The `"rising"/"flat"/"falling"` string form is **RETIRED**. A qualitative direction, if wanted, is a DERIVED read-time computation across cycles, never a stored field. **OPERATOR DECISION OD-3** below.
- Backward-compat: `cutoff_series()` currently also accepts bare number / list-of-numbers. Migration must decide whether to normalize legacy rows (**OD-5**).

### B.2 `vacancy_by_category` (LOCKED shape proposal)

```jsonc
{ "general": 442, "obc": 285, "sc": 158, "st": 79, "ews": 106 }
```

- Category-keyed, integer counts ≥ 0. `vacancy_total` remains the authoritative cycle total; sum of categories SHOULD reconcile to `vacancy_total` (warn on mismatch; hard-fail is **OD-4**).
- Vacancy stays cycle-level (matches the existing collapse-to-earliest-phase read behavior); it is NOT phase-scoped.

### B.3 `difficulty_trend` (LOCKED shape proposal)

Retire the free string. Model as an object: `{ "level": "harder"|"stable"|"easier", "basis": "<text>" }` where `level` is a LOCKED enum. Keep it a **descriptive** field — it does NOT drive planner scoring (parallels J2-A′ PD-4 strength).

### B.4 Category enum (LOCKED)

`general`, `obc`, `sc`, `st`, `ews`, plus `pwd`/`ex_servicemen` as sub-quotas — final list is **OD-1** (must match the eligibility engine's category taxonomy; determinism requires one canonical category vocabulary across eligibility and competition).

### B.5 Phase/category breakdown model (LOCKED)

- A cutoff row is `(exam_id, exam_cycle_id, exam_phase_id, category)`-addressable: `exam_phase_id` selects the phase, the `cutoff_trend` map keys select the category. One row per (cycle, phase); categories inside the JSONB.
- Vacancy is `(exam_id, exam_cycle_id, category)`-addressable (cycle-level; `exam_phase_id` NULL or ignored for vacancy).
- Cross-cycle "trend" series is a READ-TIME aggregation over rows (as `competition.py` already does), never a stored trend blob.

### B.6 Row identity, uniqueness & supersession (LOCKED requirement; mechanics = OD-10/OD-11 — added per checkpost)

The current `exam_competition_metrics` table has **no uniqueness/supersession rule** for `(exam_id, exam_cycle_id, exam_phase_id)`, and the proposed migration (Section E) only added JSON-shape validation. Without an identity rule, multiple `reviewed`/`locked` rows for the same scope can coexist and two readers (one "pick best", one "aggregate") return different answers. This gate therefore REQUIRES the following to be locked before implementation:

1. **Canonical row identity + uniqueness/versioning (OD-10):** either a unique constraint on the canonical scope (one live row per scope, superseded rows archived/soft-deleted) OR an explicit version column with a deterministic "current" selector. One of these MUST be chosen — coexisting live rows for the same scope are prohibited.
2. **Row kind separation (OD-11):** cycle-level vacancy and phase-level cutoff are addressed at different granularities (B.5). Lock whether they are (a) **separate row kinds** (a `metric_kind` discriminator: `vacancy` rows carry `exam_phase_id IS NULL`; `cutoff` rows require `exam_phase_id`) or (b) **separate child fact tables**. A single undiscriminated row shape is rejected — it lets a phase row carry a competing cycle-level vacancy value.
3. **Deterministic supersession/selection:** the read helper MUST select exactly one row per scope by a deterministic rule (latest version / max `reviewed_at` with `locked` preferred), not "first returned". This selector is specified once and shared by every reader (no per-caller "best row" heuristics).
4. **Constraint preventing cross-granularity leakage:** a DB CHECK (or the child-table split) MUST prevent a phase-scoped cutoff row from carrying cycle-level vacancy and vice-versa.

---

## Section C — Evidence model (PROPOSED)

- Keep `source_basis` (enum), `confidence_score` (0–1), and `metadata.source_url`.
- **G-6 fix — replace the bare `evidence_count` integer** with a structured, per-claim evidence array so a reviewer can audit provenance:

```jsonc
// metadata.evidence  (or a dedicated column — see OD-6)
[
  { "url": "https://ssc.gov.in/...", "label": "SSC CGL 2024 final result PDF",
    "field": "cutoff_trend", "captured_at": "2026-07-01" }
]
```

- `evidence_count` becomes DERIVED (length of the evidence array) or is dropped. **OD-6** decides column vs. `metadata` vs. a new `exam_competition_metrics_evidence` child table (child table is the strongest audit posture; JSONB is cheapest).
- No AI-authored evidence. `source_basis='model_generated'` rows may exist as drafts but MUST NOT reach `reviewed`/`locked` without human evidence attached (aligns with "no new AI writes" and verified-only reads). Enforcement point is **OD-2**.

---

## Section D — Reviewer lifecycle (LOCKED alignment)

The lifecycle states already exist; this gate locks the transition discipline (currently absent, G-5), mirroring the J2-A′ precedent.

```
draft → pending_review → reviewed → locked
                       ↘ rejected
locked → reviewed (reopen; reviewer_notes required)
rejected → draft (reset)
```

- Only `reviewed`/`locked` are aspirant-readable (already enforced by RLS + read helper). **Correction (checkpost):** `competition_context.py` reads `reviewer_status in ('locked','reviewed')` with **locked preferred** (`_READABLE_STATUSES = ("locked","reviewed")`, l.19/137) — it is NOT locked-only. This gate PRESERVES that existing reviewed+locked / locked-preferred contract (matching AGENTS.md "reviewed or locked rows feed the planner; locked preferred"); it does not redefine it. Any move to locked-only would be a separate OPERATOR DECISION with the required runtime/UI migration.
- LOCKED: `PATCH /competition-metrics/{id}/review` MUST enforce this matrix server-side and reject out-of-matrix jumps with 409 (today it accepts any jump). Reopen (`locked → reviewed`) requires `reviewer_notes`.
- LOCKED: shape validation (Section B) MUST run on the `draft → pending_review` submit AND on the `→ reviewed`/`→ locked` promotion, so malformed JSONB cannot be promoted even if it was inserted before validation existed.
- Whether editing a `reviewed`/`locked` row requires review-rollback first (J2-A′ C.3 posture) is **OD-7**.

---

## Section E — Migration decision (PROPOSED shape)

**Structured JSONB with CHECK/validation, NOT new columns.** The table shape is sound; the fix is (a) a JSONB shape guarantee and (b) transition enforcement.

Recommended forward migration:
1. Add a `CHECK` (or a `SECURITY DEFINER` validation trigger) asserting `cutoff_trend`/`vacancy_by_category`/`difficulty_trend` conform to Section B when non-empty. A trigger is preferred over a raw CHECK for readable per-key validation. **OD-5** covers legacy-row normalization/backfill before the constraint is enforced.
2. Optionally add `exam_competition_metrics_evidence` child table (**OD-6**), with its own RLS mirroring the parent's verified-only read.
3. No change to `exam_id`/`exam_cycle_id`/`exam_phase_id` (entity canonicity already correct — no `recruitment_id`, ever).
4. RLS: existing policies stay; any new child table needs its own RLS policy (verify `SELECT * FROM pg_policies WHERE tablename='exam_competition_metrics_evidence'` before marking complete). Do not mark live/operator steps complete from code inspection — use `VERIFY DB`/`OPERATOR PENDING`.
5. Migration number: pick the next free slot at implementation time; do not hardcode.

Transition-matrix + CAS enforcement is a backend change to the review endpoint, not necessarily a migration (can be app-layer), but a DB-level state-machine trigger is the stronger option — **OD-8**.

---

## Section F — OPERATOR DECISIONS — RESOLVED

All eleven items are RESOLVED and operator-approved (2026-07-02). Resolutions are folded in verbatim-in-substance from `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md` §1 (OD-1…OD-11). See "Resolved additions folded in" below for the structural amendments (§1.1–§1.5, §2.1, §4, §6, §7) and the resolution doc for full SQL/detail.

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

The following structural amendments are approved alongside the OD resolutions. Full DDL/detail lives in `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md`; this gate references rather than duplicates the SQL.

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

## Section G — Acceptance tests (on approval)

### G.1 Schema validation (Section B)
```
[ ] cutoff_trend accepts the locked category-object shape; rejects bare string ("rising")
[ ] cutoff_trend rejects unknown category keys (per OD-1 enum)
[ ] cutoff_trend rejects negative / non-numeric marks
[ ] vacancy_by_category accepts {category:int>=0}; rejects negative / non-int
[ ] vacancy_by_category vs vacancy_total mismatch behaves per OD-4
[ ] difficulty_trend accepts the locked object; rejects free string
[ ] validation runs on create, on submit, and on promote-to-reviewed/locked
```
### G.2 Entity canonicity
```
[ ] row rejects any attempt to set/reference a recruitment_id (column does not exist; assert no cross-wire)
[ ] exam_id is required and must resolve to public.exams
```
### G.3 Reviewer lifecycle (Section D)
```
[ ] out-of-matrix transition (e.g. draft→locked) rejected (409)
[ ] locked→reviewed reopen requires reviewer_notes
[ ] malformed legacy row cannot be promoted to reviewed/locked (blocked by shape validation)
[ ] only reviewed/locked rows visible to a non-admin (RLS); planner reads reviewed+locked with locked preferred (per `_READABLE_STATUSES = ("locked","reviewed")`) — a reviewed-but-not-locked row must remain planner-visible, never silently dropped
```
### G.4 Evidence (Section C)
```
[ ] evidence array shape validated; evidence_count derived/consistent (per OD-6)
[ ] model_generated row cannot reach reviewed/locked without human evidence (per OD-2)
```
### G.5 Read/UI parity
```
[ ] aspirant cutoff_series/vacancy_series render from the locked shape (no silent empty)
[ ] reviewer surface DISPLAYS cutoff_trend + vacancy_by_category (G-7 fix)
[ ] workspace write path and read helper agree on shape (round-trip test)
```

---

## Section H — Files to change (on approval)

| File | Change |
|---|---|
| `app/supabase/migrations/<next>_competition_metrics_schema.sql` | JSONB shape trigger/CHECK; optional evidence child table + its RLS; legacy normalization/backfill per OD-5. Next free migration number at implementation time; do not hardcode. |
| `app/backend/app/api/admin_exam_intel_cms.py` | Extend `_validate_competition_payload` to enforce Section B shapes on create/patch. |
| `app/backend/app/api/admin_exam_intelligence.py` | `review_competition_metric`: enforce Section D transition matrix + CAS + reopen-notes; run shape validation on promote. |
| `app/backend/app/exam_intelligence/competition.py` | Read the locked object shape (drop the tolerant number/list convention once legacy is normalized). |
| `app/backend/app/study_os/competition_context.py` | Confirm the existing reviewed+locked (locked-preferred) read still holds against the new shape; do NOT narrow to locked-only without a separate OD. |
| `app/frontend/.../CompetitionPanel.jsx` | Replace string-enum cutoff/difficulty inputs with the category-map editor; add `vacancy_by_category` inputs (per OD-9). |
| `app/frontend/.../CompetitionMetricsTable.jsx` | Display cutoff_trend + vacancy_by_category on the review surface (G-7). |
| backend + frontend tests | Section G. |
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

*Status: APPROVED — OD RESOLVED 2026-07-02. Operator sign-off recorded; every "LOCKED" item is now authoritative and all eleven OPERATOR DECISION items (OD-1…OD-11) are resolved (folded in from `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md` §0–§2, §4, §6, §7, §9). Reconciles the existing `exam_competition_metrics` table/RLS/CMS/review/read implementation; the core defects (opaque JSONB with three contradictory shapes AND the absence of any row-identity/uniqueness rule) are resolved via the additive `cutoff_by_category`/`difficulty_assessment` naming amendment, the two-lane revision model + §2.1 NULL-safe DDL, `metric_kind` + fail-closed legacy disposition, the evidence child table, and the shared `reservation_categories` taxonomy. Implementation per `docs/status/J3-Implementation-Checklist-2026-07-02.md` PR 1.*
