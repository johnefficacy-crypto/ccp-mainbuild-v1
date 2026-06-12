---
owner: ops
status: live
last_verified_against_code: 2026-06-12
source_of_truth: merged PRs
related_migrations:
  - app/supabase/migrations/172_exam_portfolio_lanes.sql
review_cadence: on-change
---

# Exam Identity, Portfolio Lanes & Operator Wizard — Merged Work

Records completed/merged actions and locked invariants for the exam-identity
operator tooling sprint (PRs #623–#635, merged 2026-06).

---

## Merged actions

### Admin exam-list server-side pagination (#623 / #625)

`GET /api/admin/exams` supports server-side pagination with:

- Query params: `q` (name search), `exam_type`, `is_active`, `active_state`
- Response envelope: `{ items, total_count, has_next }`

Previously the endpoint returned all rows; large registries caused timeout on
the admin list page.

### Portfolio lanes on `public.exams` (migration 172)

Two nullable columns added to `public.exams`:

| Column | Enum values | Notes |
|---|---|---|
| `management_mode` | `core`, `light`, `index_only`, `archive` | Operator priority lane |
| `cadence` | `annual`, `recurring`, `irregular`, `one_off`, `unknown` | Cycle regularity |

Indexes added on both columns. Backfill: 226 existing exams set to
`light` / `unknown`. Create defaults: `light` / `unknown`. The CMS update
path never re-fires defaults on existing rows (presence-based enum
validation: only validates `management_mode`/`cadence` if present in the
request body).

### Lane/cadence wired into exam CMS create/edit (#627)

`POST /api/admin/exams` and `PATCH /api/admin/exams/{id}` accept and validate
`management_mode` and `cadence`. Presence-based validation: omitting a field
on PATCH leaves the existing value unchanged.

### Copy rename: Deactivate → Retire (#630)

The "Deactivate" button in the exam CMS is renamed to **"Retire"** throughout
UI copy and `data-testid` (`cms-retire`). Behaviour unchanged: writes
`is_active = false` only.

### Importer-leftover cleanup (#631)

Deleted files (with their tests):

- `scripts/import_exam_registry.py`
- `scripts/import_subordinate_boards.py`
- `scripts/seed_exam_phases.py`
- `scripts/dedupe_state_psc_orgs.py`
- 5 associated test files

Removed the `scripts/tests` CI step. **Kept:**
`validate_exam_intelligence_seed.py` — live readiness gate, not an importer.

### Guided identity wizard (#632)

`GuidedExamWizard.jsx` — multi-step operator wizard:

- Steps: Org → Exam → Cycle → Phase → Review & Create
- Deferred sequential create: each entity created only on final confirmation
- Resume-on-failure: partial completion is recoverable without re-entering
  earlier steps

### "Add cycle to existing exam" wizard + template clone (#635)

`AddCycleWizard.jsx`:

- Clone from generic (cycle-agnostic) templates or existing cycles
- Template-slug collision guard before insert
- Clone copies `negative_marking` and `metadata` fields
- Recomputes cycle-bound slug from exam slug + year + cycle_name; assigns
  new `cycle_id` — original template is never mutated

---

## Locked decisions / invariants

### Retire semantics (option C)

`is_active = false` = retired. Public `/api/exams` filters `is_active = true`,
so retiring hides the exam from aspirants.

`management_mode = 'archive'` = SEPARATE operator lane for LIVE low-priority
exams. **Retire NEVER writes `archive`.** These are orthogonal states.

### Wizard as sole identity-change path

`import_exam_registry.py` is retired. All identity changes (new exams,
cycles, phases) go through the operator wizard. Bulk imports that previously
used the script must be recreated as wizard flows or migration data files.

### Slug immutability

`exams.slug` is fenced in `EDIT_EXCLUDED_FIELDS`. It is set at create time
(generated from name) and immutable thereafter. Editing breaks bulk-import
idempotency (slug = upsert key for seeded rows). The same invariant applies
to cycle-bound slugs.

### Uniqueness constraints

| Entity | Unique key |
|---|---|
| Cycle | `(exam_id, year, cycle_name)` |
| Phase | `(exam_id, exam_cycle_id, phase_slug)` |
| Generic template | `(exam_id, phase_slug) WHERE exam_cycle_id IS NULL` |

### Domain entity separation

DB entity = `public.exams` (exam master identity) + `public.recruitments`
(recruitment notification). Frontend label = "exam" for both contexts.
The two tables are separate and must not be merged. See
`docs/architecture/domain-model.md` and ADR 0005 (amended).

---

## Dedup status (closed items)

These were tracked as open dedup tasks; all are now closed.

| Case | Status | Notes |
|---|---|---|
| UPSC CSE canary | **Closed** | Merged 2026-06-04. Survivor `5466e62f-7382-4a38-ba96-2fe5fbfeaba2` (slug `upsc-cse`). Clean inventory, zero stale children. |
| IBPS PO, RBI Grade B, RRB NTPC, SBI PO "empty-seed retires" | **Voided** | Not empty — each has phases + eligibility_rules, high-demand. Remain live in `light`. |
| SEBI Grade A orphan | **Closed** | Already parented to family `cd0caf85`, typed, active. Nothing to promote. |
