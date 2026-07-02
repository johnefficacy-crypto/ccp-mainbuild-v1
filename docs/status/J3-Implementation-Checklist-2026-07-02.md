# J3 Implementation Checklist — sequencing, migrations, consumer switchover, rollback

- Document type: implementation execution checklist for the four J3 sub-items.
- Status: **READY — pending gate-document amendments + operator sign-off** (see `J3-OD-Resolutions-Locked-2026-07-02.md` §10).
- Date: 2026-07-02
- Decision authority: `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md` (all OD resolutions live there; this file is the "how/when", not the "what").

## Cross-cutting rules (apply to every PR)

- [ ] Migration numbers resolved from the **live `schema_migrations` ledger**, not inferred from filenames. Latest landed at drafting was migration `209`+ — verify at implementation time.
- [ ] Migrations are **immutable once merged** — never edit a landed migration.
- [ ] Every new table gets an RLS policy; verify with `SELECT * FROM pg_policies WHERE tablename='<name>'` before marking complete. Do NOT copy migration 057's `profiles.is_admin` policy — app metadata is the role source of truth (AGENTS.md).
- [ ] Do NOT mark live-deployment / Supabase-operator steps complete from code inspection — use `OPERATOR PENDING` / `VERIFY DB`.
- [ ] `graphify update .` after each PR's code lands.
- [ ] Update `docs/status/career-copilot-checklist.md` in the **same** PR that changes implementation/decision status.
- [ ] Entity canonicity: every new row is `exam_id`-scoped (`public.exams`); never `recruitment_id`.

---

## PR 1 — Competition structure

**Serial anchor.** Nothing in the competition read/write surface may be branched concurrently.

### Migration(s)
- [ ] `reservation_categories` + `reservation_category_aliases` tables (§6 schema). Seed `general/ews/obc/sc/st`; aliases `ur→general`, `gen→general`, `obc_ncl→obc`. RLS admin/service-role only.
- [ ] Additive columns on `exam_competition_metrics`: `cutoff_by_category jsonb`, `difficulty_assessment jsonb`, `metric_kind text`, `version_no int`, `supersedes_id uuid`, `superseded_at timestamptz`, `is_current_published boolean`, `breakdown_complete boolean`. **Do NOT** rename/drop `cutoff_trend`/`difficulty_trend`/`selection_ratio` (deprecate in place).
- [ ] `metric_kind` CHECK (`cycle_summary | phase_cutoff`) + cross-granularity CHECKs: `cycle_summary` ⇒ `exam_phase_id IS NULL` (owns vacancy/pressure); `phase_cutoff` ⇒ `exam_phase_id IS NOT NULL` (owns cutoffs/difficulty).
- [ ] Partial unique indexes for the **two-lane** model: one current published row per `(exam_id, exam_cycle_id, exam_phase_id, metric_kind)` where `is_current_published`; at most one current working row per same scope where `reviewer_status IN ('draft','pending_review')`.
- [ ] JSON-validation trigger: `cutoff_by_category` / `vacancy_by_category` keys validated against `reservation_categories.code`; `cutoff_by_category` value = `{marks (≥0), max_marks (>0, optional), ...}` with **no `stage` field**; reject bare string/number/list.
- [ ] `exam_competition_metric_evidence` child table (§4 full schema) + indexes + RLS + `notify pgrst`.
- [ ] OD-5 selective legacy normalization: valid category→number maps → `cutoff_by_category`; strings/bare numbers/lists → `metadata.legacy_*`, clear canonical field, set row to `draft`. Record pre/post counts. Never manufacture marks.

### Backend
- [ ] Lifecycle + CAS **DB RPC / state machine** (OD-8) enforcing `draft → pending_review → reviewed → locked`, `→ rejected`, notes-required `reopen_for_edit` (clone-to-draft, §2). App-layer validation mirrors it.
- [ ] Promotion validation: shape valid; every populated high-risk claim has qualifying **primary** evidence; category vocabulary valid; vacancy-sum rule (OD-4: `sum>total` hard error, `sum<total` warning, equality only when `breakdown_complete`); `model_generated` barred from reviewed/locked without human evidence + `source_basis` change (OD-2); source trust (§7: `is_active`/`is_verified`/`discovery_only=false`/`source_type≠aggregator`/url-or-doc present).
- [ ] `evidence_count` derived from active child rows; removed from write allowlist.
- [ ] Ratio amendment: remove `selection_ratio` from write allowlists; stop new computations; add derived `selection_rate` / `candidates_per_vacancy` / `ratio_denominator` + `selection_ratio_legacy`.
- [ ] Cutoff/difficulty **direction derived at read time** in `competition.py` (≥2 comparable cycles: same phase, category, non-null `max_marks`; else `null`).
- [ ] Move all `selection_ratio` consumers together (API-contract migration): `admin_exam_intel_cms.py`, `admin_exam_intelligence.py`, `competition.py`, `competition_context.py`, `evidence.py`, `status.py` (`competition_series`).

### Frontend
- [ ] `CompetitionPanel.jsx` → category-map editor for `cutoff_by_category`; add `vacancy_by_category` inputs; stop writing `"rising"` string; remove inverse local ratio calc.
- [ ] `CompetitionMetricsTable.jsx` (review surface) displays all cutoff + vacancy + evidence fields (OD-9). No new surface.

### Tests / status
- [ ] Acceptance tests: schema validation, entity canonicity, lifecycle matrix (reject `draft→locked`), two-lane coexistence, evidence immutability on published, read/UI parity round-trip, RLS (authenticated cannot read/mutate evidence).
- [ ] Checklist row updated; `graphify update .`.

---

## PR 2 — Applied-vs-Appeared (branch from merged PR 1)

### Migration(s)
- [ ] `exam_candidate_counts`: `exam_id` (not null), `exam_cycle_id` (required), `exam_phase_id`, `scope_kind text CHECK (cycle|phase)`, `count_type text CHECK (applied|appeared)`, `reservation_category_id uuid` (FK, nullable = total), `count_value int CHECK (>=0)`, `source_basis`/`confidence_score`, revision columns (`version_no`/`supersedes_id`/`superseded_at`/`is_current_published`), full reviewer lifecycle, timestamps.
- [ ] CHECKs: `applied` ⇒ `scope_kind='cycle'` + `exam_phase_id IS NULL`; `appeared` ⇒ (`scope_kind='phase'` + phase set) OR (`scope_kind='cycle'` + phase null, labelled aggregate).
- [ ] Unique (current unsuperseded) index: `(exam_id, exam_cycle_id, scope_kind, exam_phase_id, count_type, reservation_category)` with deterministic null handling + two-lane partial indexes.
- [ ] `exam_candidate_count_evidence` (own first-class evidence table, mirroring §4 posture) + RLS.
- [ ] RLS on both new tables (verified-only read; admin/service-role write). Verify via `pg_policies`.
- [ ] OD-6 Option B backfill: convert only rows whose evidence proves "applied"; preserve rest as legacy unknown; exclude from ratios. Record converted/unknown/zero-loss counts. Assert no ambiguous row written as `applied`.

### Backend
- [ ] Write validator: phase belongs to same exam + cycle.
- [ ] Same lifecycle RPC/revision model as PR 1.
- [ ] Consume reviewed/locked counts in APIs immediately (prefer appeared → applied → no ratio). Document `selection_rate`/`candidates_per_vacancy` denominator. **Do NOT** alter `competition_pressure_score`; only fix count display + pressure explanation text.
- [ ] `competition.py` / `competition_context.py` read explicit fields (not overloaded `applicant_count`).

### Tests / status
- [ ] Acceptance: canonicity, scope/phase consistency, per-count evidence, uniqueness, backfill zero-loss + no-silent-convert, verified-only reads, pressure output preserved for a representative exam.
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
- [ ] Add `source_basis='evidence_derived'` to the `exam_topic_coverage` CHECK **and** the exam-wide partial unique index `(exam_id, topic_id) WHERE exam_cycle_id IS NULL AND exam_phase_id IS NULL` — one migration.
- [ ] **Fail-closed** `DO` block raising a descriptive exception if any exam-wide `(exam_id, topic_id)` duplicate remains. Duplicate resolution is **manual/operator** (report → operator selects canonical → merge evidence/notes → audited repair → record pre/post + IDs → apply index). Never auto-keep latest `reviewed_at`.

### Backend
- [ ] New `coverage_derivation.py`: deterministic projection of the **latest locked** `exam_topic_score_snapshots` (+ verified syllabus mentions) into a `draft` `exam_topic_coverage` row. Fingerprint-idempotent; fail-closed on read error. Copies snapshot priority/confidence/high_yield **unchanged**.
- [ ] `coverage_depth` buckets per §5.1; no row when syllabus=0 AND evidence=0.
- [ ] Conflict rules (§5.2): skip if manual/admin/official row exists; update own `evidence_derived` draft; leave reviewed/locked `evidence_derived` untouched (explicit operator replacement).
- [ ] Scope: exam-wide + phase-scoped only; **no cycle-only** (snapshots cycle-independent); one explicit scope per invocation.
- [ ] Manual operator-invoked "derive coverage" action (OD-4); permission-gated; audited. **No new top-level route.** No scheduler.
- [ ] **Break-the-edge invariant:** `score_snapshots.py` excludes `source_basis='evidence_derived'` from `coverage_component`. Enforced by **unit/integration tests** (this is a scoring invariant, not a promotion check).
- [ ] Delta (proposed-vs-current) stored in audit/derivation metadata; no shadow rows.

### Tests / status
- [ ] Acceptance: determinism/idempotency; evidence-only + primary-only; no mutation of reviewed/locked; break-the-edge (no self-reinforcement across recompute); lifecycle/provenance; scope isolation; exam-wide duplicate fail-closed.
- [ ] Checklist row; cross-reference `docs/architecture/pyq-intelligence-v2.md` (P1 elaboration, no scoring re-spec); `graphify update .`.

---

## Rollback posture

| PR | Rollback risk | Mitigation |
|---|---|---|
| PR 1 | API-contract migration (ratio + column moves) touches 8 consumers | Additive columns + deprecate-in-place → old columns still answer; feature-flag the new derived response if a staged cutover is wanted; all readers ship in one PR so there is no split-brain window. |
| PR 2 | Legacy `applicant_count` reinterpretation | Option B converts only provenance-proven rows; unknowns preserved untouched → revert = drop new table + restore read path; no legacy data mutated destructively. |
| PR 3 | Extraction rejection path | Pure guard before OCR; revert = remove the flag check; no schema, no data. |
| PR 4 | Exam-wide unique index + enum value | Fail-closed migration cannot land with duplicates present → no partial state; revert = drop index + enum value (no rows written by derivation are locked without operator action). |

## Verification gates before "done"

- [ ] `pg_policies` proof for every new table (evidence, candidate counts, candidate evidence, `reservation_categories`, aliases).
- [ ] RPC EXECUTE grant matrix: anon/authenticated denied, service_role allowed, on every new SECURITY DEFINER RPC.
- [ ] Migration evidence artifacts (pre/post counts) committed for OD-5 (competition legacy normalization), OD-6 (applicant_count disposition), and the coverage exam-wide duplicate resolution.
- [ ] Operator validation on staging captured in a dated audit before any production apply.
