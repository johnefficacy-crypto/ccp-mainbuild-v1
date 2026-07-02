# J3 Operator-Decision Resolutions — LOCKED

- Document type: consolidated operator-decision resolution record for the four J3 sub-item gates.
- Status: **LOCKED — OPERATOR APPROVED for implementation** (pending the four gate documents being amended to match; see §7).
- Date: 2026-07-02
- Supersedes: the open `OPERATOR DECISION REQUIRED` items in all four J3 gate documents.
- Parent track: `J3 — schema/domain redesign` (`docs/status/career-copilot-checklist.md`).

## Authority & read order

This record resolves every `OD-*` item across:

1. `docs/status/J3-Competition-Cutoffs-Gate-2026-07-02.md` (OD-1…OD-11)
2. `docs/status/J3-Applied-Vs-Appeared-Gate-2026-07-02.md` (OD-1…OD-6)
3. `docs/status/J3-Mixed-Format-PDF-Gate-2026-07-02.md` (OD-1…OD-3)
4. `docs/status/J3-Evidence-Coverage-Scoring-Gate-2026-07-02.md` (OD-1…OD-6, OD-5a)

Invariants that bound every decision below (CLAUDE.md, non-negotiable): verified-only reads; Determinism > Heuristics; Trust > Speed; Control > Automation; no new AI writes; `public.exams` vs `public.recruitments` canonicity — competition/candidate/coverage intelligence is `exam_id`-scoped exam-master data, **never** `recruitment_id`.

---

## 0. Three repo defects these resolutions fix

1. **No canonical uniqueness on `exam_competition_metrics`.** Different readers either aggregate every reviewed row or pick one by cycle/status/creation time — two readers can return divergent answers for the same scope. Fixed by two-lane versioning + `metric_kind` + a shared current-row selector (Competition OD-10/OD-11).
2. **`cutoff_trend` shape disagreement.** `CompetitionPanel.jsx` writes the string `"rising"`; the aspirant reader (`competition.py`) expects a `{category: marks}` map, so operator-entered workspace data silently produces an EMPTY aspirant cutoff series. It also permits a direct `draft → locked` jump. Fixed by the `cutoff_by_category` object shape + a DB-enforced lifecycle (Competition OD-3/OD-5/OD-8, naming amendment).
3. **`selection_ratio` undefined-persisted-semantics + inverse UI.** The column is constrained `0..1`, but `CompetitionPanel.jsx` computes `applicant_count / vacancy_total` (the inverse of a selection rate). We cannot prove every stored value uses the wrong formula; we **can** prove the contract is ambiguous and the UI calculation is inverse to a selection rate. Fixed by deprecating `selection_ratio` in place and deriving `selection_rate` / `candidates_per_vacancy` / `ratio_denominator` at read time (ratio amendment).

---

## 1. Competition-Cutoffs — OD-1…OD-11

| OD | LOCKED decision |
|---|---|
| **OD-1** | v1 canonical **vertical** categories: `general`, `ews`, `obc`, `sc`, `st`. Aliases normalized via the shared taxonomy (`ur → general`, `gen → general`, `obc_ncl → obc`). PwBD / ex-servicemen / domicile are a **separate horizontal dimension** added later — never mixed into this single vertical axis. |
| **OD-2** | `source_basis='model_generated'` rows may remain **`draft` only**. Before submission a human must attach evidence and change `source_basis` to `official` or `reviewed_analysis`. Revalidate on the `submit`, `→ reviewed`, and `→ locked` transitions. |
| **OD-3** | Cutoff/difficulty **direction is derived at read time, never stored**. Derive direction only across **≥ 2 comparable cycles** matching the same phase, category and non-null `max_marks`; otherwise return `null`. `difficulty_assessment` is a structured **descriptive** fact — **not** planner input. **Remove `stage` from each cutoff object** (`exam_phase_id` is the canonical phase; a second `stage` field creates a contradictory source of truth). Direction derivation lives in **backend code** (`competition.py`), not SQL. |
| **OD-4** | `sum(categories) > vacancy_total` → **hard error**. `sum(categories) < vacancy_total` → **warning** (official notices legitimately omit buckets). Add a `breakdown_complete` boolean; strict equality is enforced **only when `breakdown_complete = true`**. |
| **OD-5** | **Selective normalization, not grandfathering.** Normalize valid category→number maps into `cutoff_by_category`. Move strings (`"rising"`), bare numbers and lists into `metadata.legacy_*`, **clear the canonical field, and return the affected row to `draft`**. Never manufacture marks from `"rising"` or an unlabeled number. Record pre/post counts in migration evidence. |
| **OD-6** | Dedicated **`exam_competition_metric_evidence` child table** (full schema §4). `evidence_count` becomes **read-derived from active child rows** and is removed from operator write input. |
| **OD-7** | Reviewed/locked rows are **not editable in place**. A notes-required **`reopen_for_edit`** operation **clones** the published row into a new `draft` revision (it does **not** move the published row back to `draft` — see §2 two-lane model), preserving aspirant-visible published intelligence during correction. |
| **OD-8** | Enforce lifecycle + CAS through a **DB RPC / state machine**, with matching app-layer validation. Multiple service-role write surfaces make app-only validation insufficient. |
| **OD-9** | **Workspace → Competition remains the canonical editor.** The review table (`CompetitionMetricsTable.jsx`) is the lifecycle/review surface and MUST display all cutoff, vacancy and evidence fields. **No new surface** (no-new-surface rule). |
| **OD-10** | **Two current lanes per (scope, `metric_kind`)** — refined from the earlier single-unsuperseded-row idea (a draft replacement must coexist with the published row): one **current published** row (`reviewer_status ∈ {reviewed, locked}`) and at most one **current working** row (`reviewer_status ∈ {draft, pending_review}`). Columns: `version_no`, `supersedes_id`, `superseded_at`, `is_current_published`. Partial unique indexes enforce **one current row per lane**. All readers use one shared current-published selector — no per-reader "best row" heuristic. |
| **OD-11** | Keep one table; add **`metric_kind ∈ {cycle_summary, phase_cutoff}`**. `cycle_summary` requires `exam_phase_id IS NULL` and owns vacancy / pressure. `phase_cutoff` requires a phase and owns cutoffs / difficulty. DB CHECKs prohibit cross-granularity fields (a phase row cannot carry cycle-level vacancy and vice-versa). |

### 1.1 Naming amendment (additive deprecation — no breaking rename)

Do **not** rename or drop columns in place (PostgREST schema-reload vs. app-rollout ordering would break). **Add** replacement columns, backfill, switch consumers, then deprecate:

| New column | Replaces (deprecated-in-place) |
|---|---|
| `cutoff_by_category` | `cutoff_trend` (legacy) |
| `difficulty_assessment` | `difficulty_trend` (legacy) |

Legacy columns are removed only in a **later cleanup migration** after all consumers and historical values are verified.

### 1.2 Ratio amendment (API-contract migration)

`selection_ratio` has undefined persisted semantics and an inverse UI calculation. **Deprecate in place**; stop persisting new values; derive and return at read time:

```jsonc
{
  "selection_rate":         0.00125,   // vacancies / denominator
  "candidates_per_vacancy": 800,       // denominator / vacancies
  "ratio_denominator":      "appeared", // "appeared" | "applied"
  "selection_ratio_legacy": 0.00125    // old column, audit/back-compat only
}
```

Steps: (1) remove `selection_ratio` from operator-write allowlists; (2) stop new computations from it; (3) add the derived fields above; (4) retain the column for audit/back-compat; (5) drop it in a later cleanup migration after all consumers move.

**This is an API-contract migration even though the physical column stays** — all readers move together: `admin_exam_intel_cms.py` (write/validate), `admin_exam_intelligence.py` (admin read), `competition.py` (aspirant series), `competition_context.py` (pressure explanation), `evidence.py` (evidence row), `status.py` (transitive via `/api/exam-intelligence/exams/{slug}` → `competition_series`), `CompetitionMetricsTable.jsx` (display), `CompetitionPanel.jsx` (inverse local ratio).

---

## 2. Two-lane revision model (Competition + Candidate Counts)

Applies to `exam_competition_metrics` and `exam_candidate_counts` (both introduce correction history). **Not** applied to `exam_topic_coverage` (see §5).

```text
one current published row per (scope, kind):
  reviewer_status in ('reviewed','locked')   is_current_published = true

at most one current working row per (scope, kind):
  reviewer_status in ('draft','pending_review')
```

Columns: `version_no`, `supersedes_id`, `superseded_at`, `is_current_published`.

**Promotion RPC (atomic):** (1) validate shape + evidence; (2) mark the previous published revision superseded; (3) mark the new revision current-published; (4) preserve the previous row and its evidence.

**Reopen-for-edit:** clones the published row into a new draft revision — the published row is untouched and stays aspirant-visible until the new revision is promoted.

`exam_candidate_counts` uses the same revision model so a plain unique tuple does not prevent preserving corrected historical official counts.

---

## 3. Applied-vs-Appeared — OD-1…OD-6

| OD | LOCKED decision |
|---|---|
| **OD-1** | Support **both totals and optional per-category** counts. `reservation_category = NULL` means the official total; category rows are captured **only when official data exists**. Category detail is supported but never mandatory. |
| **OD-2** | New typed **`exam_candidate_counts` table** (not two more nullable fields on the overloaded competition row). Applied and appeared arrive at different times with independent evidence and lifecycles. |
| **OD-3** | Add **`scope_kind ∈ {cycle, phase}`** (constrained CHECK). `exam_cycle_id` is **always required**. `applied` → `scope_kind='cycle'`, `exam_phase_id IS NULL`. `appeared` → either `scope_kind='phase'` with `exam_phase_id` set, **or** an explicitly-labelled cycle aggregate (`scope_kind='cycle'`, `exam_phase_id IS NULL`) for authorities that publish only aggregate appearance data. A write validator confirms the phase belongs to the same exam **and** cycle. |
| **OD-4** | Reuse the **shared `reservation_categories` vocabulary + aliases** (§6) via FK — not free text, not a hard-to-extend PG enum. |
| **OD-5** | **Consume the new reviewed/locked counts immediately** in APIs (prefer `appeared`, then `applied`, else return no ratio). Do **NOT** let this PR alter `competition_pressure_score` itself — only fix count display and the pressure **explanation** text. |
| **OD-6** | **Option B** — migrate only rows whose evidence explicitly proves the value means "applied." Preserve all other `applicant_count` values as **legacy unknown** and exclude them from ratios. Record converted / unknown / zero-loss counts in migration evidence. Ambiguous rows are **never** silently converted. |

**Uniqueness (current unsuperseded fact per scope, with the §2 revision model):**

```text
(exam_id, exam_cycle_id, scope_kind, exam_phase_id, count_type, reservation_category)
```

with deterministic null handling. **Evidence:** applied/appeared facts get their **own** first-class evidence relationship (`exam_candidate_count_evidence` or equivalent) — do NOT attach them to the generic competition-metric evidence row; their lifecycle and parent identity differ.

---

## 4. Competition evidence child table (`exam_competition_metric_evidence`)

```sql
create table public.exam_competition_metric_evidence (
  id uuid primary key default gen_random_uuid(),

  metric_id uuid not null
    references public.exam_competition_metrics(id) on delete cascade,

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
- **Lifecycle:** evidence may be attached/corrected only for a working `draft`/`pending_review` revision; evidence on a published `reviewed`/`locked` revision is **immutable**; promotion validates every populated high-risk claim has qualifying **primary** evidence; `evidence_count` is derived from active child rows, never caller-supplied.
- **RLS:** enable RLS; **no** anon/authenticated direct read or write; access only through permission-gated FastAPI evidence/review routes using the service role. **Do NOT** copy migration 057's `profiles.is_admin` policy — AGENTS.md marks profile-based authority deprecated; app metadata is the role source of truth.

---

## 5. Evidence-Coverage — OD-1…OD-6, OD-5a

| OD | LOCKED decision |
|---|---|
| **OD-1** | Add **`source_basis='evidence_derived'`** (OD-5a already needs a migration, so the enum value is nearly free and it keeps row-ownership unambiguous). Store `pyq` vs `hybrid` detail in metadata. |
| **OD-2** | Deterministic `coverage_depth` buckets (below). **No row is generated when both syllabus mentions and PYQ evidence are zero.** |
| **OD-3** | **Option A — break the input edge.** `score_snapshots.py` MUST exclude `source_basis='evidence_derived'` coverage from its `coverage_component` input. This is a **read-model / scoring invariant enforced by unit/integration tests**, NOT a row-promotion validator check. |
| **OD-4** | **Manual operator-triggered derivation only** for v1. No scheduler, no piggy-back on snapshot computation. |
| **OD-5** | Leave manual/reviewed/locked coverage untouched. Store the proposed-vs-current **delta** in the audit record or derivation-result metadata. **No parallel shadow coverage rows.** |
| **OD-5a** | Add the **exam-wide partial unique index** (below) before enabling exam-wide derivation. Existing indexes constrain only cycle+phase and phase-only scopes; the all-NULL exam-wide scope is unconstrained. |
| **OD-6** | Support **exam-wide and phase-scoped** derivation in v1. Do **NOT** support cycle-only derivation (score snapshots are cycle-independent). Each invocation targets **one explicit scope**. |

### 5.1 `coverage_depth` buckets (LOCKED)

```text
mentioned : syllabus_mentions >= 1 and evidence_count = 0
light     : evidence_count 1–2
normal    : evidence_count 3–5
deep      : evidence_count 6–9
core      : evidence_count >= 10 AND syllabus_mentions >= 1 AND snapshot.is_high_yield = true
```

No derived row for zero syllabus mentions + zero PYQ evidence. Snapshot `priority`, `confidence` and `is_high_yield` are **copied unchanged** — J3 projects, it does not recompute.

### 5.2 Coverage does NOT get two-lane versioning

The unique scope/topic index remains the single canonical coverage row. Derivation conflict rules:

```text
existing manual/admin/official row at scope      → skip derivation for that scope
existing evidence_derived DRAFT row              → recompute/update via the controlled derivation action
existing reviewed/locked evidence_derived row    → leave unchanged; explicit operator replacement workflow
```

### 5.3 Exam-wide uniqueness index (OD-5a)

```sql
create unique index <name>
  on public.exam_topic_coverage (exam_id, topic_id)
  where exam_cycle_id is null and exam_phase_id is null;
```

**Duplicate handling = fail-closed (C) + manual resolution (B).** Do NOT auto-keep latest `reviewed_at` (latest ≠ correct, especially manual vs. evidence-derived). Process: (1) preflight report grouped by `(exam_id, topic_id)` where cycle+phase both NULL, including row IDs, status, source_basis, priority, high-yield, reviewed timestamps, evidence metadata; (2) operator selects canonical row; (3) merge legitimate evidence/notes into it; (4) audited repair removes/consolidates the duplicate; (5) record pre/post counts + selected IDs; (6) apply the index. The migration carries a defensive `DO` block that raises a descriptive exception if any duplicate remains.

### 5.4 Coverage migration packaging

Both changes ship in **one** migration (atomic derivation precondition): add `source_basis='evidence_derived'` **and** the exam-wide unique index. No benefit to splitting.

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

| OD | LOCKED decision |
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
   `reservation_categories` + aliases; additive `cutoff_by_category` / `difficulty_assessment` columns; two-lane competition revisions (`version_no`/`supersedes_id`/`superseded_at`/`is_current_published`); `metric_kind`; current-row uniqueness/supersession + shared selector; JSON validation trigger (category keys vs `reservation_categories.code`); `exam_competition_metric_evidence` child table; promotion RPC + evidence/source trust validation; OD-5 selective legacy normalization; derived ratio fields + `selection_ratio` deprecation; UI/read parity (all consumers move together); legacy-compat response.
2. **PR 2 — Applied-vs-Appeared** (branch from merged PR 1)
   `exam_candidate_counts` + `exam_candidate_count_evidence`; RLS; `scope_kind` + phase/cycle CHECK + write validator; same revision model + shared taxonomy; conservative OD-6 legacy migration; read-model switch; derived pressure denominators (no change to `competition_pressure_score` itself).
3. **PR 3 — Mixed-Format Option B** (independent)
   `document_assets.metadata.mixed_format` declaration; pre-OCR `ExtractionMixedFormatError`; operator control + SOP doc. No migration unless metadata validation needs a DB constraint.
4. **PR 4 — Coverage derivation** (coordinate migration slot after PR 2)
   `source_basis='evidence_derived'` + exam-wide unique index (one migration); manual derivation endpoint; exclude `evidence_derived` from `score_snapshots.py` `coverage_component` (test-enforced); delta reporting; fail-closed exam-wide duplicate resolution.

Competition and Applied/Appeared must not run concurrently (shared read models + operator surface). Mixed-PDF is independent. Coverage is logically independent but coordinates its migration slot after PR 2.

---

## 10. Gate-document amendments required before operator sign-off

Each gate document must be amended to replace its `OPERATOR DECISION REQUIRED` sections with the resolutions above:

- **Competition-Cutoffs gate:** OD-1…OD-11 resolved; add the `cutoff_by_category`/`difficulty_assessment` naming amendment, the ratio amendment, the two-lane revision model, `metric_kind`, the evidence child schema, and the `reservation_categories` taxonomy.
- **Applied-vs-Appeared gate:** OD-1…OD-6 resolved; add `exam_candidate_counts` + `exam_candidate_count_evidence`, `scope_kind`, the revision model, shared taxonomy, OD-6 Option B backfill, immediate-consume-without-touching-pressure-score.
- **Mixed-Format-PDF gate:** OD-1 = B, OD-2 = B1, OD-3 = N/A-now (record Option A child-table + no-backfill for later).
- **Evidence-Coverage gate:** OD-1…OD-6 + OD-5a resolved; add the bucket table, break-the-edge-as-test-invariant, single-migration packaging, fail-closed duplicate resolution, and the explicit "no two-lane versioning for coverage" note.

Implementation checklist and sequencing: `docs/status/J3-Implementation-Checklist-2026-07-02.md`.
