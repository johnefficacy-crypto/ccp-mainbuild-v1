# Evidence-Based Coverage Scoring Gate — J3 sub-item

- Document type: J3 implementation contract — deterministic, evidence-derived `exam_topic_coverage` scoring, its review lifecycle, and its relationship to the already-locked `exam_topic_score_snapshots` pipeline.
- Status: **APPROVED — OD RESOLVED 2026-07-02.** Operator sign-off recorded; resolutions folded in from docs/status/J3-OD-Resolutions-Locked-2026-07-02.md §5. Every previously-PROPOSED lock is now LOCKED. Implementation per docs/status/J3-Implementation-Checklist-2026-07-02.md PR 4 (migration slot after PR 2).
- Date: 2026-07-02
- Parent track: `J3 — schema/domain redesign` (checklist row: "evidence-based coverage scoring"), `DEFERRED — CONTRACT-FIRST`.
- Authority: `docs/architecture/pyq-intelligence-v2.md` (scoring contracts, snapshot authority, "do not write directly into locked `exam_topic_coverage` from an AI job"); `docs/architecture/domain-model.md` (entity canonicity); `CLAUDE.md` invariants (Determinism > Heuristics, verified-only reads, primary-only PYQ frequency, no new AI writes).
- Prerequisite gates cleared: PYQ-Intelligence-v2 slice-1/3 (frequency semantics + `exam_topic_score_snapshots` activation), PRs #767 / #773 / #810, all MERGED.

---

## How to use this document

This gate **reconciles the existing implementation** — a large evidence-scoring pipeline already exists (Section 0). It does not design from scratch. Every section states a LOCKED decision or an exact specification. The operator-decision items (OD-1…OD-6, OD-5a) are now **RESOLVED** (Section E) with the resolutions folded in from `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md` §5.

**Operator approval recorded 2026-07-02.** Implementation dispatches as PR 4 in `docs/status/J3-Implementation-Checklist-2026-07-02.md` (migration slot after PR 2).

**Serial delivery rule (locked):** J3 coverage scoring touches shared exam-intelligence write paths (`admin_exam_intel_manage.py`, `admin_exam_intel_cms.py`) and the score-snapshot computation module — one owner's sequential work, no fan-out.

---

## Section 0 — Actual implementation baseline (what evidence-based scoring EXISTS today)

### 0.1 `exam_topic_coverage` (migration 030, lines 95–122)

Canonical, human-curated exam-topic overlay:

```sql
coverage_depth text  in ('unknown','none','mentioned','light','normal','deep','core')  default 'unknown'
exam_priority_score numeric(5,2)  0..100  default 0
is_high_yield boolean  default false
confidence_score numeric(4,3)  0..1  default 0
source_basis text  in ('official_syllabus','pyq_analysis','admin_review','hybrid','manual','model_generated')  default 'manual'
model_version text
reviewer_status text  in ('draft','pending_review','reviewed','locked','rejected')  default 'draft'
reviewed_by / reviewed_at / review_notes
```

- **Only `reviewer_status='locked'` rows are planner-ready / aspirant-visible** (`coverage.py::locked_topic_coverage`, `locked_topic_coverage_summary`).
- Today these scores are **entered/edited manually** through the Manage-Exam and CMS coverage editors (`admin_exam_intel_manage.py`, `admin_exam_intel_cms.py`); `source_basis` records the claimed provenance but there is **no deterministic computation that derives `exam_priority_score` / `is_high_yield` / `coverage_depth` from evidence and writes them into this table.** The `source_basis` enum already anticipates evidence provenance (`pyq_analysis`, `official_syllabus`, `hybrid`) but nothing populates the numbers from that evidence.

### 0.2 `exam_topic_score_snapshots` (migration 033) + `score_snapshots.py` — ALREADY EVIDENCE-BASED

This is the merged, locked, evidence-scoring authority. Do **not** re-specify it here.

- `compute_exam_topic_scores()` reads **only verified evidence**: verified `pyq_papers` (`trust_status='verified'`) → verified `pyq_questions` (`reviewer_status='verified'`) → **primary-only** verified `pyq_question_topic_tags` (`reviewer_status='verified'`, `tag_role='primary'`), plus **locked** `exam_topic_coverage` as one input component.
- Deterministic + idempotent: SHA-256 `fingerprint` over all inputs (papers, questions, primary-tag tuples, locked-coverage values); re-runs with an unchanged corpus skip unchanged topics. `MODEL_VERSION="v1.0"`.
- Primary-only frequency, ambiguous multi-primary questions excluded, phase-isolated (`exam_phase_id IS NULL` vs equals), all reads paginated, fail-closed on read error.
- Current formula (snapshot): `exam_priority_score = freq_component*50 + cov_component*40 + evidence_quality*10`; `is_high_yield = locked_coverage.is_high_yield OR freq_component > 0.15`; `confidence_score = min(0.3 + evidence_quality*0.7, 1)`.
- Lifecycle `draft → reviewed → locked | rejected` via atomic RPC (migration 204); `locked→reviewed` reopen permitted. **No AI/compute writes into locked rows.**
- `locked_score_snapshots()` feeds the planner as a bounded additive signal (0–15 pt, PR #773). Aspirant/planner reads see **locked only**.

### 0.3 The gap this creates (why J3 exists)

The evidence pipeline (0.2) currently **consumes** locked `exam_topic_coverage` (0.1) as its `coverage_component` — but that coverage priority is itself a **manual/heuristic admin entry**. So the deterministic snapshot rests partly on a hand-entered number, and the canonical coverage table it feeds back into the planner (`coverage.py`) is never itself evidence-derived. `pyq-intelligence-v2.md` P1 explicitly forbids an AI job writing locked coverage directly; J3 must supply the **governed, deterministic, reviewed** path that fills that gap without violating that rule.

---

## Section A — Scope of J3 (what this item ADDS; LOCKED boundaries)

| In scope | Out of scope (cross-reference) |
|---|---|
| A deterministic derivation of `exam_topic_coverage.exam_priority_score`, `is_high_yield`, `coverage_depth`, `confidence_score` from **verified evidence only**, written as **`draft`** rows for review. | The snapshot computation, fingerprinting, and planner-signal wiring — already merged; see §0.2 and `pyq-intelligence-v2.md`. Do not modify snapshot scoring under this gate. |
| The review lifecycle for evidence-derived coverage rows (`draft → pending_review → reviewed → locked`), reusing the existing `exam_topic_coverage.reviewer_status` machinery. | Appearance/recurrence prediction, cognitive-demand classification (`pyq-intelligence-v2.md` P2/P7). |
| `source_basis` provenance for derived rows and the relationship/circularity resolution with `exam_topic_score_snapshots` (Section D). | Competition-metrics JSONB, mixed-PDF extraction (separate J3 sub-items with their own gates). |
| Migration/RLS/reviewer/acceptance decisions needed to land it. | Any new top-level admin surface (no-new-surface rule). |

**Locked framing:** J3 does not create a second scoring engine. Evidence signals are already computed in `exam_topic_score_snapshots`. J3 defines how a **locked** snapshot is deterministically **projected into a reviewable `draft` `exam_topic_coverage` row**, closing §0.3 while preserving "no AI writes into locked coverage."

---

## Section B — Decisions (LOCKED)

| ID | Decision |
|---|---|
| PD-1 | **Evidence-only inputs.** Derived coverage scores are a pure deterministic function of verified evidence already aggregated by the snapshot pipeline (verified papers/questions/primary-verified tags) and verified syllabus mentions (`syllabus_topic_mentions.reviewer_status='verified'`). No AI/heuristic verdict, no unverified data, no scraped input. Reuses the primary-only frequency contract (query- AND loop-level filtered) — never re-implemented. |
| PD-2 | **Determinism + idempotency.** The derivation is a pure function of its inputs; identical inputs produce identical output and re-running writes nothing new (fingerprint-guarded, mirroring `score_snapshots.py`). |
| PD-3 | **Draft-only writes; review before lock.** The job writes/updates `exam_topic_coverage` rows only in `reviewer_status='draft'`. Promotion `draft → pending_review → reviewed → locked` is operator-driven through the existing coverage review lifecycle. **No compute path ever writes or mutates a `locked` (or `reviewed`) coverage row** — satisfies CLAUDE.md "no new AI writes" and `pyq-intelligence-v2.md` P1. |
| PD-4 | **Locked wins over recompute.** A topic whose coverage row is already `reviewed`/`locked` is never overwritten by the derivation; the job skips it (records a "would-differ" delta in `input_summary`/audit for operator visibility, but does not mutate). Manual `admin_review` locked rows are likewise preserved. |
| PD-4a | **Row-ownership / conflict model (LOCKED — added per checkpost; corrects the PD-4 gap that only protected reviewed/locked).** **Uniqueness caveat (per Codex review):** the existing `exam_topic_coverage` unique indexes are *partial* — they only cover scopes where `exam_phase_id` is non-null (and the cycle-scoped variants); an **exam-wide** row (`exam_cycle_id` AND `exam_phase_id` both NULL) is NOT constrained, so manual and derived exam-wide rows can silently duplicate. This gate therefore does NOT rely on a blanket "one row per scope/topic" guarantee — enforcing it is a **precondition** (see OD-5 / migration decision): before the derivation may run on the exam-wide scope, either a partial unique index covering the all-NULL scope is added, or a separate delta table is used. Given that, ownership rules: (1) the derivation may write/update a row ONLY when that row is **derivation-owned** — identified by `source_basis ∈ {derived provenance set}` AND `model_version` set by the derivation (i.e. a row it previously created); (2) a row in ANY state (incl. `draft`) that is human/manual-authored (`source_basis ∈ {manual, admin_review}`) is NEVER overwritten — a manual `draft` is protected exactly like a locked row; (3) if the canonical scope/topic already has a manual or reviewed/locked row, the derivation does NOT create a second row — it records a **delta** (see PD-4b) instead of upserting, and MUST match-by-scope explicitly (not rely on the DB rejecting a duplicate) on the unconstrained exam-wide scope. |
| PD-4b | **Comparison storage without violating uniqueness (LOCKED requirement; mechanism = OD-5).** "Would-differ" / comparison-vs-locked evidence is stored WITHOUT a parallel `exam_topic_coverage` row — options: an audit/delta record, a snapshot delta field, or the `input_summary` blob. A shadow `draft` row **alongside** a locked row is NOT implementable on the no-new-table path (uniqueness); OD-5 must therefore either drop the shadow-alongside option or accept a schema change (a separate delta/shadow table). |
| PD-5 | **Provenance.** Derived draft rows set `source_basis='pyq_analysis'` (evidence-only) or `'hybrid'` (evidence + verified syllabus mention), and set `model_version` to the derivation version. `'manual'` / `'admin_review'` remain reserved for human-entered rows. (Whether to add a distinct `'evidence_derived'` enum value is **OD-1**.) |
| PD-6 | **Single source of evidence numbers.** The frequency/high-yield/priority signals come from the **locked `exam_topic_score_snapshots`** authority, NOT a parallel recomputation, to guarantee one number across planner, snapshot, and coverage surfaces (resolves §0.3 circularity — see Section D). |

---

## Section C — Deterministic scoring model (LOCKED shape; two knobs are OD)

**Input** (per topic, per scope `exam_id` + `exam_phase_id|NULL`): the **latest locked** `exam_topic_score_snapshots` row (`exam_priority_score`, `is_high_yield`, `confidence_score`, `score_components`, `evidence_count`) plus verified `syllabus_topic_mentions` count for the topic.

**Output** written to a `draft` `exam_topic_coverage` row:

```
exam_priority_score := locked_snapshot.exam_priority_score           # already 0..100, deterministic
is_high_yield       := locked_snapshot.is_high_yield
confidence_score    := locked_snapshot.confidence_score
coverage_depth      := f(verified_syllabus_mention_count, evidence_count)   # deterministic bucketing — OD-2
source_basis        := 'pyq_analysis' | 'hybrid'                     # PD-5 / OD-1
model_version       := DERIVATION_VERSION
metadata.evidence   := { snapshot_id, evidence_count, syllabus_mentions, fingerprint }
reviewer_status     := 'draft'
```

- **No new arithmetic beyond a documented monotonic bucketing** for `coverage_depth`. Priority/high-yield/confidence are copied verbatim from the reviewed-and-locked snapshot — the deterministic scoring already passed operator review at the snapshot gate, so J3 does not re-score, it **projects**.
- Idempotent via a fingerprint over (snapshot_id, snapshot fingerprint, syllabus-mention count, DERIVATION_VERSION) stored in `metadata`; unchanged inputs → skip.
- Fail-closed: a read failure is a compute failure, not "no evidence" (mirror `score_snapshots.py` `read_error`).
- Scope isolation identical to snapshots: exam-wide reads use `exam_phase_id IS NULL`; phase reads use equality. Never mix scopes.

---

## Section D — Relationship to `exam_topic_score_snapshots` (LOCKED + one OD)

The circularity in §0.3 (snapshot reads locked coverage as `coverage_component`; J3 would derive coverage from the snapshot) MUST be broken deterministically:

- **LOCKED:** J3 coverage derivation reads the **locked snapshot only** and writes a **draft coverage** row. Because it writes only `draft` and the snapshot's `coverage_component` reads only `locked` coverage, a freshly derived draft cannot feed back into the snapshot until an operator locks it — no automatic feedback loop. One human review sits on every edge.
- **OD-3 (OPERATOR DECISION REQUIRED):** the residual steady-state loop — once a derived coverage row is locked, the next snapshot recompute will fold it back into `coverage_component`, which then re-projects into coverage. Options:
  - (a) **Break the input edge:** stop `score_snapshots.py` from reading `exam_topic_coverage` for topics whose coverage `source_basis` is evidence-derived (avoid self-reinforcement); keep it only for genuinely manual/`admin_review` coverage.
  - (b) **Keep the edge, rely on fingerprint idempotency + human review** at each lock to damp it.
  - (c) **Zero the `coverage_component` for evidence-derived rows** so priority is frequency+evidence only.
  This changes merged snapshot behavior, so it is operator-gated and MUST NOT be guessed.

---

## Section E — OPERATOR DECISIONS — RESOLVED

Resolved 2026-07-02, folded in from `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md` §5.

| ID | Resolved decision |
|---|---|
| **OD-1** | **Add `source_basis='evidence_derived'`** to the `exam_topic_coverage` `source_basis` **text CHECK constraint** (it is a CHECK today, not a PG enum). OD-5a already needs a migration, so the value is nearly free and it keeps row-ownership unambiguous. Store `pyq` vs `hybrid` detail in metadata. |
| **OD-2** | **Deterministic, total `coverage_depth` buckets** (§5.1 below — every valid input has exactly one result). **No row is generated when both syllabus mentions and PYQ evidence are zero.** |
| **OD-3** | **Option A — break the input edge.** `score_snapshots.py` MUST exclude `source_basis='evidence_derived'` coverage from its `coverage_component` input. This is a **read-model / scoring invariant enforced by unit/integration tests**, NOT a row-promotion validator check. |
| **OD-4** | **Manual operator-triggered derivation only** for v1. No scheduler, no piggy-back on snapshot computation. |
| **OD-5** | **Leave manual/reviewed/locked coverage untouched.** Store the proposed-vs-current **delta** in the audit record or derivation-result metadata. **No parallel shadow coverage rows.** |
| **OD-5a** | **Add the exam-wide partial unique index** (§5.3 below) before enabling exam-wide derivation. Existing indexes constrain only cycle+phase and phase-only scopes; the all-NULL exam-wide scope is unconstrained. |
| **OD-6** | **Support exam-wide and phase-scoped derivation** in v1. Do **NOT** support cycle-only derivation (score snapshots are cycle-independent). Each invocation targets **one explicit scope**. |

### Resolved additions folded in

The following exact specifications from `docs/status/J3-OD-Resolutions-Locked-2026-07-02.md` §5 are incorporated by reference and govern implementation. They are consistent with the PD-4a/PD-4b row-ownership notes in Section B.

**§5.1 — `coverage_depth` buckets (total function; every valid input maps to exactly one bucket):**

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

**§5.2 — Conflict rules, complete over the full `source_basis` vocabulary.** After OD-1 the vocabulary is `{official_syllabus, pyq_analysis, admin_review, hybrid, manual, model_generated, evidence_derived}`; every existing-row case has an explicit rule (single-row canonical model — no two-lane versioning for coverage, §5.4):

| Existing row at scope | Rule |
|---|---|
| `manual`, `admin_review`, `official_syllabus` (any status) | **Skip** — human-authored; record delta only. |
| `pyq_analysis`, `hybrid` (any status) | **Skip** — legacy human-entered provenance claims predating `evidence_derived`; treated as human-authored (the new enum value exists precisely so the derivation only ever owns rows it created). Record delta. |
| `model_generated` (any status) | **Skip + flag for operator triage** — never updated or overwritten by the derivation. |
| `evidence_derived` + `draft` | **Recompute/update** via the controlled derivation action (derivation-owned). |
| `evidence_derived` + `pending_review` | **Skip** — under review; record delta. Operator may reject back to `draft` to re-derive. |
| `evidence_derived` + `reviewed`/`locked` | **Leave unchanged**; explicit operator replacement workflow required. |
| `evidence_derived` + `rejected` | **Recompute/update** (returns to `draft` with fresh inputs). |

This aligns with PD-4a (derivation writes only derivation-owned rows; human/manual rows in ANY state are never overwritten) and PD-4b (comparison stored as delta, never a shadow row).

**§5.3 — Exam-wide uniqueness index (OD-5a); fail-closed + manual duplicate resolution:**

```sql
create unique index <name>
  on public.exam_topic_coverage (exam_id, topic_id)
  where exam_cycle_id is null and exam_phase_id is null;
```

**Duplicate handling = fail-closed (C) + manual resolution (B).** Do NOT auto-keep latest `reviewed_at` (latest ≠ correct, especially manual vs. evidence-derived). Process: (1) preflight report grouped by `(exam_id, topic_id)` where cycle+phase both NULL, including row IDs, status, source_basis, priority, high-yield, reviewed timestamps, evidence metadata; (2) operator selects canonical row; (3) merge legitimate evidence/notes into it; (4) audited repair removes/consolidates the duplicate; (5) record pre/post counts + selected IDs; (6) apply the index. The migration carries a defensive `DO` block that raises a descriptive exception if any duplicate remains.

**§5.4 — Coverage does NOT get two-lane versioning.** The unique scope/topic index remains the single canonical coverage row. Conflict handling is §5.2 above.

**§5.5 — Single-migration packaging.** Both changes ship in **one** migration (atomic derivation precondition): extend the `source_basis` text CHECK with `'evidence_derived'` **and** add the exam-wide unique index. No benefit to splitting.

---

## Section F — Migration decision (LOCKED shape; gated on OD-1)

- **If OD-1 = reuse existing enum:** *no migration required* — `exam_topic_coverage` already has `source_basis`, `model_version`, `reviewer_status`, `reviewed_by/at`, `review_notes`, and the necessary indexes (030). This is the preferred minimal path.
- **If OD-1 = add `'evidence_derived'`:** one forward migration alters the `source_basis` CHECK constraint. **Migration number:** pick the next free slot at implementation time; do not hardcode from a stale branch. Migrations are immutable once merged.
- No new table. No new FK. Entity canonicity unchanged: this is `exam_id`-scoped exam-identity data (`public.exams`), never recruitment (`docs/architecture/domain-model.md`).

---

## Section G — RLS

- `exam_topic_coverage` RLS already exists (migration 035 / hardening 195). J3 adds **no new table**, so no new policy is required in the reuse path. If OD-1 adds an enum value, RLS is unaffected (constraint-only change).
- Verify before marking complete: `SELECT * FROM pg_policies WHERE tablename = 'exam_topic_coverage';` — confirm authenticated read is locked-only at the query layer and writes are service-role/definer-gated. Mark `VERIFY DB` until captured against live Supabase.

---

## Section H — Reviewer lifecycle (LOCKED)

Reuse the existing `exam_topic_coverage` review machinery — do not invent a parallel one.

```
draft → pending_review → reviewed → locked
                       ↘ rejected
locked → reviewed (reopen, notes required)
```

- The derivation writes/updates only `draft` (PD-3). `pending_review`/`reviewed`/`locked` are operator transitions via the existing coverage review endpoints (`exam_intelligence.review`).
- `manage` may edit a derived `draft` (e.g. correct `coverage_depth`) before submitting; edits under `reviewed`/`locked` require a review reopen (parity with the prerequisite gate C.3 posture).
- Every derivation write and every transition emits an `admin_audit_logs` row via the shared `_audit()` helper (best-effort, consistent with the CMS surface).

---

## Section I — Acceptance tests

### I.1 Determinism / idempotency (PD-2, Section C)
```
[ ] identical inputs → identical derived draft (byte-stable priority/high_yield/confidence)
[ ] re-run with unchanged snapshot + syllabus counts writes nothing (fingerprint skip)
[ ] changing the locked snapshot changes the derived draft on next run
```
### I.2 Evidence-only + primary-only (PD-1)
```
[ ] derivation reads ONLY locked snapshots + verified syllabus mentions
[ ] no draft/reviewed/rejected snapshot influences the derived coverage row
[ ] primary-only frequency contract inherited (no re-implementation; parity with coverage.py)
```
### I.3 No AI writes into locked coverage (PD-3, PD-4)
```
[ ] derivation writes only reviewer_status='draft'
[ ] a reviewed/locked coverage row is NEVER mutated by the job (skipped)
[ ] manual/admin_review locked rows preserved; delta recorded in audit/metadata only
```
### I.4 Feedback-loop safety (Section D / OD-3 once chosen)
```
[ ] a freshly derived draft does NOT feed the snapshot coverage_component until locked
[ ] chosen OD-3 option behaves as specified (no runaway self-reinforcement across recompute cycles)
```
### I.5 Lifecycle + provenance (PD-5, Section H)
```
[ ] derived draft carries source_basis + model_version + evidence metadata
[ ] draft → pending_review → reviewed → locked transitions work via existing endpoints
[ ] planner/aspirant reads still see locked-only coverage (coverage.py unchanged contract)
```
### I.6 Scope isolation (Section C / OD-6)
```
[ ] exam-wide derivation uses exam_phase_id IS NULL; phase derivation uses equality; no scope mixing
```

---

## Section J — Files to change (on approval)

| File | Change |
|---|---|
| `app/backend/app/exam_intelligence/` (new module, e.g. `coverage_derivation.py`) | deterministic projection of locked snapshots (+ verified syllabus mentions) into `draft` `exam_topic_coverage`; fingerprint idempotency; fail-closed; PD-3/PD-4 guards. Reuses `score_snapshots.py` / `coverage.py` helpers; no new frequency logic. |
| `app/backend/app/exam_intelligence/score_snapshots.py` | **only if OD-3 = (a)/(c)** — adjust `coverage_component` input for evidence-derived rows. No change otherwise. |
| `app/backend/app/api/admin_exam_intelligence.py` (or the existing snapshot compute surface) | operator-invoked "derive coverage" action per OD-4; permission-gated; audited. **No new top-level admin route** (no-new-surface rule). |
| `app/supabase/migrations/<next>_coverage_source_basis_evidence.sql` | **only if OD-1 approved** — extend `source_basis` CHECK; next free slot; immutable. |
| backend tests | Section I. |
| `docs/status/career-copilot-checklist.md` | J3 "evidence-based coverage scoring" row status update in the same branch. |
| `docs/architecture/pyq-intelligence-v2.md` | cross-reference the coverage-derivation projection (P1 elaboration); no scoring re-spec. |

---

## Appendix A — Code / schema evidence index

- `app/supabase/migrations/030_exam_registry_cycles_phases.sql:95–166` — `exam_topic_coverage` schema (coverage_depth, exam_priority_score, is_high_yield, confidence_score, source_basis enum, model_version, reviewer_status lifecycle) + indexes.
- `app/supabase/migrations/033_exam_topic_analytics_snapshots.sql:5–34` — `exam_topic_score_snapshots` schema (draft/reviewed/locked/rejected, evidence_count, input_summary, score_components).
- `app/backend/app/exam_intelligence/score_snapshots.py` — `compute_exam_topic_scores` (evidence-only, primary-only, SHA-256 idempotent, phase-isolated, fail-closed), `locked_score_snapshots`, `list_exam_score_snapshots`; `MODEL_VERSION="v1.0"`.
- `app/backend/app/exam_intelligence/coverage.py:80–371` — `locked_topic_coverage_summary`, `verified_pyq_topic_counts` (primary-only, query+loop filtered), `locked_topic_coverage` (locked-only, planner/aspirant read).
- `app/backend/app/api/admin_exam_intel_manage.py` / `admin_exam_intel_cms.py` — current manual coverage write/edit paths.
- `app/backend/app/study_os/planner.py` — consumes locked coverage + locked snapshots (0–15 pt additive signal, PR #773).
- `docs/architecture/pyq-intelligence-v2.md` (§Scoring contracts, P1) — "do not write directly into locked `exam_topic_coverage` from an AI job"; snapshot authority; primary-only frequency.

---

*Status: APPROVED — OD RESOLVED 2026-07-02. Reconciles a substantial existing evidence-scoring pipeline (`exam_topic_score_snapshots` + `score_snapshots.py`, merged PRs #767/#773/#810); J3 adds only the governed, deterministic projection of locked snapshots into reviewable `draft` `exam_topic_coverage` rows. All operator-decision items (OD-1…OD-6, OD-5a) are RESOLVED per docs/status/J3-OD-Resolutions-Locked-2026-07-02.md §5; implementation dispatches as PR 4 (migration slot after PR 2) per docs/status/J3-Implementation-Checklist-2026-07-02.md.*
