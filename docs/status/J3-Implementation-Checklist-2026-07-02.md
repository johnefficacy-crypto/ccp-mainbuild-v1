# J3 Implementation Checklist — sequencing, migrations, consumer switchover, rollback

- Document type: implementation execution checklist for the four J3 sub-items.
- Status: **UNBLOCKED — 2026-07-02.** Both §10 authority steps are complete: the four gate documents are deep-amended (`OPERATOR APPROVED — 2026-07-02`) and `J3-OD-Resolutions-Locked-2026-07-02.md` reads `OPERATOR APPROVED` on the strength of the operator's explicit approval recorded on PR #861. PR 1 (Competition structure) may now dispatch as the serial anchor; PR 2 branches from merged PR 1; PR 3 is independent; PR 4 coordinates its migration slot after PR 2.
- Date: 2026-07-02 (revised same day per PR #857 and PR #861 checkpost reviews; unblocked 2026-07-02 on recorded operator approval)
- Decision authority: the four J3 gate documents, as amended per `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md` (the "what" lives there; this file is the "how/when").

## Cross-cutting rules (apply to every PR)

- [ ] Migration numbers resolved from the **live `schema_migrations` ledger**, not inferred from filenames. Latest landed at drafting was migration `209`+ — verify at implementation time.
- [ ] Migrations are **immutable once merged** — never edit a landed migration. Corollary: **rollback is forward-only** (see Rollback posture) — never "drop the migration".
- [ ] Every new table gets an RLS policy; verify with `SELECT * FROM pg_policies WHERE tablename='<name>'` before marking complete. Do NOT copy migration 057's `profiles.is_admin` policy — app metadata is the role source of truth (AGENTS.md).
- [ ] Do NOT mark live-deployment / Supabase-operator steps complete from code inspection — use `OPERATOR PENDING` / `VERIFY DB`.
- [ ] `graphify update .` after each PR's code lands.
- [ ] Update `docs/status/career-copilot-checklist.md` in the **same** PR that changes implementation/decision status.
- [ ] Entity canonicity: every new row is `exam_id`-scoped (`public.exams`); never `recruitment_id`.

---

## PR 1 — Competition structure

**Serial anchor.** Nothing in the competition read/write surface may be branched concurrently.

**Status: CODE-FIXED, VALIDATION PENDING** (implemented on branch `claude/j3-pr1-competition-structure`, migration `216_j3_competition_structure.sql`). Every item below is implemented in code; the boxes are left unchecked because none has live/staging proof yet (per the cross-cutting rule: code inspection alone does not close a checklist item). See the `career-copilot-checklist.md` "J3 PR 1" row for the detailed file-by-file summary and the explicitly deferred/simplified items (no live-duplicate fixture for §1.4; PR 2 not started).

### Migration(s)
- [ ] `reservation_categories` + `reservation_category_aliases` tables (resolutions §6). Seed `general/ews/obc/sc/st`; aliases `ur→general`, `gen→general`, `obc_ncl→obc`. RLS admin/service-role only.
- [ ] Additive columns on `exam_competition_metrics`: `cutoff_by_category jsonb`, `difficulty_assessment jsonb`, `metric_kind text`, `version_no int`, `supersedes_id uuid`, `superseded_at timestamptz`, `is_current_published boolean`, `breakdown_complete boolean`. **Do NOT** rename/drop `cutoff_trend`/`difficulty_trend`/`selection_ratio` (deprecate in place).
- [ ] Consistency CHECKs per resolutions §2.1: `metric_kind` shape (`cycle_summary` ⇒ phase NULL / `phase_cutoff` ⇒ phase set), `metric_kind IS NOT NULL ⇒ exam_cycle_id IS NOT NULL`, `is_current_published ⇒ reviewer_status IN ('reviewed','locked') AND superseded_at IS NULL`, `superseded_at IS NOT NULL ⇒ NOT is_current_published`. All `metric_kind` CHECKs gated on `metric_kind IS NOT NULL` until disposition completes.
- [ ] **Legacy `metric_kind` disposition (resolutions §1.3), fail-closed:** preflight report (populated fields × phase × cycle × status, committed as evidence); cycle-level-only rows → `cycle_summary` in place; combined rows with known phase → split (cycle fields → new/existing `cycle_summary` revision, cutoff/difficulty stays as `phase_cutoff`); phaseless cutoff content → payload to `metadata.legacy_*` + working draft for operator triage; cycle-less rows → operator triage; published rows never returned to draft (valid fields stay published; malformed content → `metadata.legacy_*` + separate working draft); terminal `DO` block raising on any `metric_kind IS NULL` remainder, any pre/post count mismatch, or any published-row data loss.
- [ ] **Current-lane initialization (resolutions §1.4), fail-closed, after §1.3 and before indexes/reader switch:** duplicate scope/lane report; sole published row → mechanically `is_current_published=true`; multiple published rows → fail-closed until audited operator canonical selection (others superseded, preserved); duplicate working rows → audited disposition (one kept, rest `superseded_at`-stamped); `version_no` 1..N + `supersedes_id` chain backfilled per scope (ordered by `COALESCE(reviewed_at, created_at)`); **legacy trust disposition per `source_basis`** (manual/official/reviewed_analysis/derived reviewed-locked → grandfathered current + `metadata.legacy_unvalidated_evidence=true` + revalidation worklist, evidence required prospectively at next transition; `model_generated` reviewed-locked → fail-closed operator triage, never auto-grandfathered); terminal zero-availability-loss `DO` block (every previously-published scope has exactly one current row, except operator-triaged `model_generated` scopes enumerated in the report; zero rows deleted).
- [ ] Two-lane partial unique indexes + per-scope `version_no` uniqueness indexes exactly per resolutions §2.1 (scope-specific; NULL-safe — plain UNIQUE over nullable scope columns does not enforce uniqueness). Enable only after §1.3 + §1.4 complete.
- [ ] Field-ownership + lineage constraints per §2.1: `ecm_kind_field_ownership` (cycle rows carry no cutoff/difficulty; phase rows carry no vacancy/pressure/count), `version_no NOT NULL > 0` for new-model rows, self-FK `supersedes_id` + no-self-reference, RPC/trigger same-scope-ancestry + `version_no = parent + 1`.
- [ ] JSON-validation trigger per resolutions §1.5: `cutoff_by_category` keys vs `reservation_categories.code`, values `{marks (≥0), max_marks (>0, optional)}`, **no `stage`**, reject bare string/number/list — with the explicit migration conversion `{"general": 120}` → `{"general": {"marks": 120}}` before enabling; `vacancy_by_category` keys vs taxonomy AND **values non-negative integers** (no in-map nulls; `{}` = no breakdown) so the OD-4 sum rule is executable; `difficulty_assessment` locked shape `{level: harder|stable|easier, basis: text 8–500}` (bare string rejected).
- [ ] `exam_competition_metric_evidence` child table (resolutions §4 full schema) + indexes + RLS + **immutability triggers** (block INSERT/UPDATE/DELETE of evidence on a published parent; block DELETE of a published parent metric row — cascade fires only for genuinely-draft cleanup) + **published-parent BEFORE UPDATE guard** (§2: content columns frozen on published rows; only lifecycle/supersession columns mutable per the state machine) + `notify pgrst`.
- [ ] OD-5 selective legacy normalization: valid category→number maps → `cutoff_by_category`; strings/bare numbers/lists → `metadata.legacy_*`, clear canonical field; lane-aware disposition (draft/pending → back to `draft`; published → stays published + separate working draft carries the legacy payload). Record pre/post counts. Never manufacture marks.

### Backend
- [ ] Lifecycle + CAS **DB RPC / state machine** (OD-8) enforcing `draft → pending_review → reviewed → locked`, `→ rejected`, notes-required `reopen_for_edit` (clone-to-draft, resolutions §2). App-layer validation mirrors it.
- [ ] Promotion validation: shape valid; every populated high-risk claim has qualifying **primary** evidence **whose `claim_value` matches the current parent field/category value** (stale evidence attached before a later working-parent edit does not qualify); category vocabulary valid; vacancy-sum rule (OD-4: `sum>total` hard error, `sum<total` warning, equality only when `breakdown_complete`); `model_generated` barred from reviewed/locked without human evidence + `source_basis` change (OD-2); source trust (resolutions §7: `is_active`/`is_verified`/`discovery_only=false`/`source_type≠aggregator`/url-or-doc present).
- [ ] `evidence_count` derived by counting the revision's child rows (append-only model); removed from write allowlist.
- [ ] **Ratio contract, PR-1 half only (resolutions §1.2):** remove `selection_ratio` from write allowlists; stop new computations from it; add derived fields with the **null contract** (`selection_rate`/`candidates_per_vacancy`/`ratio_denominator` = null until a provenance-proven denominator exists — do NOT derive from legacy `applicant_count`); **the existing `selection_ratio` response key is preserved as a deprecated alias** (verbatim legacy value, alongside `selection_ratio_legacy` — external clients unbroken; removal only in the later cleanup/versioning step); all consumers keep rendering the legacy value → zero silent behavior change. The atomic derivation switch happens in PR 2.
- [ ] Cutoff/difficulty **direction derived at read time** in `competition.py` (≥2 comparable cycles: same phase, category, non-null `max_marks`; else `null`).
- [ ] Shared current-published selector used by every reader (`competition.py`, `competition_context.py`, admin reads) — no per-reader "best row" heuristic.

### Frontend
- [ ] `CompetitionPanel.jsx` → category-map editor for `cutoff_by_category`; add `vacancy_by_category` inputs; stop writing `"rising"` string; remove inverse local ratio calc (render `selection_ratio_legacy` labelled as legacy until PR 2).
- [ ] `CompetitionMetricsTable.jsx` (review surface) displays all cutoff + vacancy + evidence fields (OD-9). No new surface.

### Tests / status
- [ ] Acceptance: schema validation (§1.5 contracts incl. bare-number conversion, vacancy value validation, difficulty shape), entity canonicity, lifecycle matrix (reject `draft→locked`), two-lane coexistence + NULL-safe uniqueness, lineage invariants (version monotonicity, same-scope ancestry, no self-reference), §1.3 disposition + §1.4 lane initialization (duplicate fail-closed, legacy trust disposition per basis, zero-availability-loss), evidence immutability **including direct service-role UPDATE/DELETE of published evidence, published-parent DELETE, and published-parent UPDATE of frozen content columns (all trigger-rejected)**, promotion claim-value-match (stale evidence rejected), ratio null contract + `selection_ratio` alias preserved + display parity, read/UI parity round-trip, RLS (authenticated cannot read/mutate evidence).
- [ ] Checklist row updated; `graphify update .`.

---

## PR 2 — Applied-vs-Appeared (branch from merged PR 1)

### Migration(s)
- [ ] `exam_candidate_counts`: `exam_id` (not null), `exam_cycle_id` (not null), `exam_phase_id`, `scope_kind text CHECK (scope_kind in ('cycle','phase'))`, `count_type text CHECK (count_type in ('applied','appeared'))`, `reservation_category_id uuid` (FK, NULL = official total), `count_value int CHECK (>=0)`, `source_basis`/`confidence_score`, revision columns (`version_no`/`supersedes_id`/`superseded_at`/`is_current_published`) + the same `is_current_published`/`superseded_at` consistency CHECKs as PR 1, full reviewer lifecycle, timestamps.
- [ ] Scope CHECKs: `applied` ⇒ `scope_kind='cycle'` + `exam_phase_id IS NULL`; `appeared` ⇒ (`scope_kind='phase'` + phase set) OR (`scope_kind='cycle'` + phase NULL, labelled aggregate).
- [ ] Two-lane unique indexes per resolutions §2.1: `(exam_id, exam_cycle_id, scope_kind, exam_phase_id, count_type, reservation_category_id)` **`NULLS NOT DISTINCT`** (PG15+; fallback: `coalesce(..., zero-uuid)` expression indexes), partial on published lane / working lane; plus per-scope `version_no` uniqueness and the same lineage constraints (`version_no > 0`, self-FK, no self-reference) as PR 1.
- [ ] `exam_candidate_count_evidence` per the **exact §4.1 schema** (`count_id` parent FK; no `claim_field`/`reservation_category_id` — the parent row is the single claim; `claim_value` snapshot of `{count_type, scope_kind, exam_phase_id, reservation_category_code, count_value}`; server-computed `evidence_key`) + immutability triggers + RLS.
- [ ] **Published-parent BEFORE UPDATE guard** on `exam_candidate_counts` (content columns frozen on published rows; lifecycle/supersession columns only, per §2).
- [ ] RLS on both new tables with the **exact predicate**: non-admin read requires `reviewer_status IN ('reviewed','locked')`; writes service-role/app-metadata-admin only. Verify via `pg_policies`.
- [ ] OD-6 Option B backfill: convert only rows whose evidence proves "applied"; preserve rest as legacy unknown; exclude from ratios. Record converted/unknown/zero-loss counts. Assert no ambiguous row written as `applied`.

### Backend
- [ ] Write validator: phase belongs to same exam + cycle.
- [ ] Same lifecycle RPC/revision model as PR 1.
- [ ] **Ratio contract, PR-2 half (atomic switch):** ratio derivation moves to reviewed/locked candidate counts (prefer `appeared` → `applied` → null) and **all ratio consumers switch in this PR together** (`competition.py`, `competition_context.py`, admin reads, both frontends). Document the denominator via `ratio_denominator`. **Do NOT** alter `competition_pressure_score`; only fix count display + pressure explanation text.
- [ ] `competition.py` / `competition_context.py` read explicit fields (not the overloaded `applicant_count`).

### Tests / status
- [ ] Acceptance: canonicity, scope/phase consistency, per-count evidence with **promotion claim-value comparison** (`claim_value.count_value` == parent `count_value`, category/scope match; stale evidence rejected) + service-role trigger tests (evidence UPDATE/DELETE, parent DELETE, parent UPDATE of frozen columns), NULL-safe uniqueness (duplicate NULL-category/phase rows rejected), backfill zero-loss + no-silent-convert, verified-only reads (exact predicate), ratio switch (appeared preferred, applied fallback, null otherwise), pressure output preserved for a representative exam.
- [ ] Checklist row; `graphify update .`.

---

## PR 3 — Mixed-Format Option B (independent, may run in parallel with PR 1/2)

- [ ] `document_assets.metadata.mixed_format=true` admin-declared flag (B1); validated. No migration unless a DB constraint is chosen for the flag.
- [ ] `ExtractionMixedFormatError` raised in `extraction/pipeline.py` scope-fence **before OCR**; zero `pyq_questions` writes; message links the SOP.
- [ ] Admin control to declare mixed-format on a document.
- [ ] Create `docs/engineering/mixed-format-pdf-workaround-v1.md` (split-and-reupload SOP).
- [ ] Record in the gate doc that a later Option A uses `document_format_segments` (child table, non-overlap constraint) with **no backfill**.
- [ ] Acceptance: declared-mixed rejects pre-OCR with zero writes; homogeneous `mcq_bilingual_two_column` still extracts as today; split sub-documents extract independently.
- [ ] Checklist rows (both mixed-format rows) flipped from DEFERRED.

---

## PR 4 — Coverage derivation (coordinate migration slot after PR 2)

### Migration (single, atomic)
- [ ] Extend the `exam_topic_coverage.source_basis` **text CHECK constraint** (not a PG enum) with `'evidence_derived'` **and** add the exam-wide partial unique index `(exam_id, topic_id) WHERE exam_cycle_id IS NULL AND exam_phase_id IS NULL` — one migration.
- [ ] **Fail-closed** `DO` block raising a descriptive exception if any exam-wide `(exam_id, topic_id)` duplicate remains. Duplicate resolution is **manual/operator** (report → operator selects canonical → merge evidence/notes → audited repair → record pre/post + IDs → apply index). Never auto-keep latest `reviewed_at`.

### Backend
- [ ] New `coverage_derivation.py`: deterministic projection of the **latest locked** `exam_topic_score_snapshots` (+ verified syllabus mentions) into a `draft` `exam_topic_coverage` row. Fingerprint-idempotent; fail-closed on read error. Copies snapshot priority/confidence/high_yield **unchanged**.
- [ ] `coverage_depth` buckets per resolutions §5.1 — **total function** (incl. the `deep` fallback for `evidence_count >= 10` failing any `core` predicate); no row when syllabus=0 AND evidence=0.
- [ ] Conflict rules per resolutions §5.2 — **complete over the full `source_basis` vocabulary** (`manual`/`admin_review`/`official_syllabus`/`pyq_analysis`/`hybrid` → skip+delta; `model_generated` → skip+triage; `evidence_derived` by status → update/skip/leave/update).
- [ ] Scope: exam-wide + phase-scoped only; **no cycle-only** (snapshots cycle-independent); one explicit scope per invocation.
- [ ] Manual operator-invoked "derive coverage" action (OD-4); permission-gated; audited. **No new top-level route.** No scheduler.
- [ ] **Break-the-edge invariant:** `score_snapshots.py` excludes `source_basis='evidence_derived'` from `coverage_component`. Enforced by **unit/integration tests** (this is a scoring invariant, not a promotion check).
- [ ] Delta (proposed-vs-current) stored in audit/derivation metadata; no shadow rows.

### Tests / status
- [ ] Acceptance: determinism/idempotency + bucket totality (every valid input produces exactly one bucket); evidence-only + primary-only; conflict-rule coverage for every `source_basis` × status combination; break-the-edge (no self-reinforcement across recompute); lifecycle/provenance; scope isolation; exam-wide duplicate fail-closed.
- [ ] Checklist row; cross-reference `docs/architecture/pyq-intelligence-v2.md` (P1 elaboration, no scoring re-spec); `graphify update .`.

---

## Rollback posture (forward-only — migrations are immutable and data may already exist)

Never drop landed tables/indexes/CHECK values as "rollback". Rollback = disable the new read/write path, restore the legacy reader, preserve all new data; physical removal only via a later corrective migration once proven safe.

| PR | Rollback risk | Forward-only mitigation |
|---|---|---|
| PR 1 | Ratio/columns contract touches 8 consumers | PR 1 is additive with display parity (legacy value still rendered), so "rollback" = keep serving `selection_ratio_legacy` and ignore the null derived fields. Legacy columns remain authoritative until PR 2; new tables/columns/indexes stay in place, inert. |
| PR 2 | Legacy `applicant_count` reinterpretation + ratio switch | OD-6 converts only provenance-proven rows; unknowns preserved untouched. Rollback = switch ratio readers back to the PR-1 legacy path via code revert; `exam_candidate_counts` rows are preserved (never dropped); corrective migration only if ever needed and proven safe. |
| PR 3 | Extraction rejection path | Pure pre-OCR guard; rollback = remove the flag check (code revert); no schema, no data. |
| PR 4 | Exam-wide unique index + `source_basis` CHECK value | Fail-closed migration cannot land with duplicates present → no partial state. Rollback = disable the derivation action (code revert); the index and CHECK value remain (harmless); derived `draft` rows stay inert — they are never planner-visible unless an operator locks them. |

## Verification gates before "done"

- [ ] `pg_policies` proof for every new table (competition evidence, candidate counts, candidate evidence, `reservation_categories`, aliases).
- [ ] RPC EXECUTE grant matrix: anon/authenticated denied, service_role allowed, on every new SECURITY DEFINER RPC.
- [ ] Trigger-enforcement proof: direct service-role UPDATE/DELETE of published evidence, published-parent DELETE, **and published-parent UPDATE of frozen content columns** are rejected on BOTH `exam_competition_metrics` and `exam_candidate_counts` (not just endpoint-level tests).
- [ ] Migration evidence artifacts (pre/post counts) committed for the §1.3 metric_kind disposition, the **§1.4 lane initialization** (duplicate resolutions, per-basis legacy trust disposition, zero-availability-loss report), OD-5 (competition legacy normalization incl. bare-number conversions), OD-6 (applicant_count disposition), and the coverage exam-wide duplicate resolution.
- [ ] Operator validation on staging captured in a dated audit before any production apply.
