---
owner: exam-intelligence
status: PROPOSAL — contract-first, not yet operator-approved, no implementation may start
last_reconciled: 2026-07-08
source_of_truth: code
related_code:
  - app/backend/app/exam_intelligence/coverage.py
  - app/backend/app/exam_intelligence/score_snapshots.py
  - app/backend/app/exam_intelligence/coverage_derivation.py
  - app/backend/app/study_os/planner.py
  - app/backend/app/api/admin_exam_intelligence.py
related_migrations:
  - app/supabase/migrations/032_pyq_question_intelligence.sql
  - app/supabase/migrations/033_exam_topic_analytics_snapshots.sql
  - app/supabase/migrations/204_atomic_snapshot_review_transition.sql
related_docs:
  - docs/architecture/pyq-intelligence-v2.md
  - docs/architecture/english-writing-practice.md
  - docs/status/J3-Competition-Cutoffs-Gate-2026-07-02.md
review_cadence: on next implementation dispatch
---

# Exam Knowledge Compiler v1 — Architecture Contract

**Status: PROPOSAL.** This document is a contract draft only. No code, migration, or
API in this doc has been written. It requires explicit operator sign-off
(Section 8) before any implementation PR is opened, matching the J1/J2/J3
contract-first gate pattern (`docs/status/J3-Competition-Cutoffs-Gate-2026-07-02.md`).

## Relationship to `docs/architecture/pyq-intelligence-v2.md`

`pyq-intelligence-v2.md` is the standing architecture decision for the whole
PYQ-intelligence surface. It already documents the "versioned analytical
snapshot layer" as canonical architecture, lists `topic_relation_edges` and
`pyq_option_patterns` as **schema present, not populated**, and puts
distractor/cognitive classification in its P2 gap bucket with an explicit
"add a reviewed classification record" contract. This document does **not**
re-derive any of that — it is the bounded, code-grounded implementation
contract for one slice of it: **compiling `topic_relation_edges` rows from
verified PYQ tag data.** Anything already decided in `pyq-intelligence-v2.md`
(no Neo4j/Pinecone, additive-snapshot pattern, primary-only tag semantics,
`exam_topic_score_snapshots` as the score authority) is inherited here
verbatim and not repeated except where this document adds a concrete
schema/algorithm on top of it.

Where the two documents could be read as overlapping — P2's "governed
cognitive and distractor classification" — Section 7 explicitly defers that
work; this contract covers topic-pair co-occurrence only.

---

## 1. Problem statement

The only backend "intelligence" surface today is
`app/backend/app/exam_intelligence/coverage.py`, which exposes exactly three
functions, all consumed by `app/backend/app/study_os/planner.py`:

- `locked_topic_coverage_summary(supabase, exam_id)` — joins
  `exam_topic_coverage` (`reviewer_status='locked'` only) with `topics`/
  `subjects`.
- `verified_pyq_topic_counts(supabase, exam_id)` — counts verified PYQ
  questions per topic, **filtered to `tag_role='primary'`**. Questions with
  more than one primary tag are logged as "ambiguous" and **excluded
  entirely** (coverage.py lines 187–286) — one verified question must not
  inflate more than one topic's count.
- `locked_topic_coverage(supabase, exam_id)` — same locked-only contract,
  sorted for "top N" consumption.

`planner.py` blends these with `locked_score_snapshots()`
(`score_snapshots.py`) as a confidence-weighted additive signal. That is the
entire deterministic-intelligence input the planner has today: per-topic
priority, per-topic verified frequency, per-topic locked score. There is no
compiled signal about how topics **relate to each other**.

Concretely, the gap: `verified_pyq_topic_counts` computes a
`q_to_topics: dict[str, set[str]]` map internally (question → set of
primary-tagged topic ids) purely to *detect and discard* multi-topic
questions — `ambiguous = [q for q, topics in q_to_topics.items() if
len(topics) > 1]`. That is exactly the raw signal for topic co-occurrence
(two topics genuinely combined in one verified question), and it is
currently computed, logged as a warning, and thrown away.

Separately, migration `032_pyq_question_intelligence.sql` already defines
`public.topic_relation_edges` — `source_topic_id`, `target_topic_id`,
`exam_id`, `relation_type` (`prerequisite | co_occurs_with |
frequently_combined | confusion_pair | alternate_route | revision_cluster |
cross_subject_link`), `strength`, `evidence_count`, `last_observed_year` —
and `public.question_relation_edges` / `public.pyq_option_patterns` for
question-template and distractor relations. All three are, per
`pyq-intelligence-v2.md`'s own audit table, "schema present" with **zero
rows written anywhere in the codebase.** No compiler, no writer, no reader
exists for any of them today. `grep -r "topic_relation_edges" app/backend`
returns only the migration file.

Planner and mock consumers therefore have no way to answer "what else tends
to appear with this topic" — a bundling signal a deterministic planner could
use to schedule related topics together, or a mock blueprint could use to
avoid over-concentrating a set on one micro-cluster. This document specifies
the minimum compiler that turns already-gated verified tag data into
reviewable `topic_relation_edges` rows, without inventing a new table and
without touching planner scoring in v1.

---

## 2. Scope of v1

**In scope:** compile `relation_type='co_occurs_with'` edges into the
existing `topic_relation_edges` table, from **verified PYQ papers only**,
using the same conjunctive trust gates `verified_pyq_topic_counts` already
uses (`pyq_papers.trust_status='verified'` → `pyq_questions.reviewer_status
='verified'` → `pyq_question_topic_tags.reviewer_status='verified' AND
tag_role='primary'`). A co-occurrence edge is emitted only for the
**same-question, multi-primary-topic** case described in Section 1 — i.e.
the precise signal already computed and discarded by
`verified_pyq_topic_counts`.

**Explicitly out of scope for v1** (see Section 7 for the full list and
rationale): paper-level co-occurrence (topics appearing anywhere in the same
paper, not the same question), secondary/trap/calculation_layer/
conceptual_layer tag roles as co-occurrence input, `frequently_combined` /
`confusion_pair` / `alternate_route` / `revision_cluster` /
`cross_subject_link` relation types, `question_relation_edges` (template/
duplicate detection), `pyq_option_patterns` (distractor compilation),
current-affairs linkage, microtopic-specific tuning beyond what falls out
naturally from `topics.level`, cross-exam co-occurrence, and any planner
scoring change.

This is deliberately the smallest slice that (a) reuses data already
computed under an existing, tested trust gate, (b) writes into a table that
already exists with the right shape, and (c) requires no new taxonomy
decisions. Everything else in the "compile pattern-level intelligence"
wishlist (traps, templates, recurring question families, current affairs)
needs its own contract — none of it is close to this tractable.

---

## 3. Data model

### 3.1 Extend `topic_relation_edges` (additive migration, not a new table)

`topic_relation_edges` (migration 032) already has the right shape for edge
data (`source_topic_id`, `target_topic_id`, `exam_id`, `relation_type`,
`strength`, `evidence_count`, `last_observed_year`, `metadata`) but has
**no reviewer lifecycle** — any row written today would be immediately
readable with no review gate, which violates this repo's verified-only /
locked-only read contract for analytical output. `pyq-intelligence-v2.md`'s
correction #2 is explicit: derived aggregates that "change when the corpus,
trust state, review status, time window, or model changes" must be
"versioned snapshots with evidence and model version," not raw mutable
columns with no lifecycle.

v1 therefore proposes an **additive** migration (number resolved from the
live `schema_migrations` ledger at implementation time — do not hardcode)
that adds reviewer-lifecycle and provenance columns to
`topic_relation_edges`:

```sql
alter table public.topic_relation_edges
  add column if not exists reviewer_status text not null default 'draft'
    check (reviewer_status in ('draft', 'reviewed', 'locked', 'rejected')),
  add column if not exists reviewed_by uuid references public.profiles(id) on delete set null,
  add column if not exists reviewed_at timestamptz,
  add column if not exists reviewer_notes text,
  add column if not exists model_version text,
  add column if not exists input_fingerprint text,
  add column if not exists computed_at timestamptz;
```

No existing column is renamed or dropped (migrations are immutable once
merged; this table has zero live rows today so there is no backfill risk,
but the migration must still be additive-only per repo convention). RLS
must be verified with `SELECT * FROM pg_policies WHERE tablename =
'topic_relation_edges'` before this is marked complete — today the table
has no RLS policy at all (it was created with no rows and no reader), so
this migration must also add an RLS policy: authenticated read restricted to
`reviewer_status in ('reviewed', 'locked')` (mirrors
`exam_competition_metrics_read_reviewed` in migration 057), admin/service
role unrestricted, no INSERT/UPDATE/DELETE for non-service roles (writes go
through the compiler job and the review RPC only, both service-role).

### 3.2 Gating at each stage

| Stage | Gate |
|---|---|
| Compiler input (raw evidence) | `pyq_papers.trust_status='verified'` AND `pyq_questions.reviewer_status='verified'` AND `pyq_question_topic_tags.reviewer_status='verified' AND tag_role='primary'` — identical conjunctive gate to `verified_pyq_topic_counts`, filtered at query AND loop level (defense in depth, same pattern as coverage.py) |
| Compiler output (write) | `topic_relation_edges.reviewer_status='draft'` on first write or on evidence change |
| Admin review surface | operator reads `draft`/`reviewed` rows through the review RPC (Section 5); never aspirant-facing |
| Consumer read (Section 6) | `topic_relation_edges.reviewer_status='locked'` only, `relation_type='co_occurs_with'` only — mirrors `locked_topic_coverage`'s locked-only contract |

No new table for raw evidence is introduced in v1. The compiler recomputes
directly from `pyq_question_topic_tags` on each run (same approach as
`verified_pyq_topic_counts` — no cached intermediate table), so there is no
separate "evidence" table to keep in sync; the audit trail lives in
`metadata` (contributing question ids, capped) and `admin_audit_logs` (via
the review RPC, Section 5).

---

## 4. Compilation logic

Deterministic, no LLM, no heuristic scoring. Implemented as
`app/backend/app/exam_intelligence/knowledge_compiler.py`, structured like
`score_snapshots.py::compute_exam_topic_scores` (paginated reads, SHA-256
input fingerprint, idempotent skip-if-unchanged).

```
1. Read verified papers for exam_id:
     pyq_papers WHERE exam_id = :exam_id AND trust_status = 'verified'
   (paginated, same as verified_pyq_topic_counts step 1)

2. Read verified questions for those papers:
     pyq_questions WHERE pyq_paper_id IN (paper_ids)
                     AND reviewer_status = 'verified'
   (batched + paginated)

3. Read verified PRIMARY tags for those questions:
     pyq_question_topic_tags WHERE question_id IN (question_ids)
                                AND reviewer_status = 'verified'
                                AND tag_role = 'primary'
   Build q_to_topics: {question_id: set(topic_id)}   -- identical map
   verified_pyq_topic_counts already builds internally.

4. For every question_id where len(q_to_topics[question_id]) >= 2:
     for every unordered pair (topic_a, topic_b) drawn from that set,
     canonicalise the pair so source_topic_id < target_topic_id
     (lexicographic UUID text compare — deterministic, no ordering
     ambiguity), and record one evidence unit:
       (topic_a, topic_b) -> {question_id, paper_id, year}

5. Aggregate evidence per canonical pair:
     evidence_count      = count(distinct question_id)
     last_observed_year  = max(year) across contributing papers
                            (null-safe; papers without a year contribute
                            no year but still contribute evidence_count)
     contributing_question_ids = sorted list, capped at 50 in metadata
                                  (audit sample, not the full set, to keep
                                  row size bounded)

6. Compute a LOCAL primary_topic_question_count[topic_id]: the count of
   distinct verified, primary-tagged questions for that topic INCLUDING
   multi-topic (ambiguous) questions. This is deliberately NOT the same
   number verified_pyq_topic_counts returns (that function excludes
   multi-topic questions on purpose, for a different metric — single-topic
   frequency). Do not conflate the two; this count exists only inside the
   compiler to normalise co-occurrence strength.

7. strength(topic_a, topic_b) =
     evidence_count(topic_a, topic_b)
     / min(primary_topic_question_count[topic_a],
           primary_topic_question_count[topic_b])
   This is the overlap coefficient. It is mathematically bounded to (0, 1]
   by construction (evidence_count for a pair cannot exceed either topic's
   own primary_topic_question_count), needs no clamping, and needs no
   model beyond arithmetic. relation_type is fixed to 'co_occurs_with' for
   every row v1 writes.

8. Input fingerprint (mirrors score_snapshots._build_fingerprint):
     SHA-256(exam_id : model_version : sorted(paper_ids) :
              sorted(question_ids) :
              sorted("question_id:topic_id" for every contributing
                     primary tag))
   One fingerprint per exam (not per pair) — same corpus-level fingerprint
   shape as compute_exam_topic_scores, since a single tag change can shift
   more than one pair's evidence set.

9. For every canonical pair with evidence_count >= 1, UPSERT into
   topic_relation_edges on the existing unique constraint
   (source_topic_id, target_topic_id, exam_id, relation_type):
     - New pair (no existing row): INSERT with reviewer_status='draft'.
     - Existing row whose stored input_fingerprint matches the freshly
       computed corpus fingerprint: SKIP (idempotent no-op — this is the
       "re-run with same corpus skips unchanged topics" behaviour
       score_snapshots.py already implements).
     - Existing row whose input_fingerprint differs (new/changed evidence):
       UPDATE strength/evidence_count/last_observed_year/metadata/
       computed_at/model_version/input_fingerprint, and reset
       reviewer_status to 'draft' regardless of its prior status —
       a locked pair whose underlying evidence changed must be re-reviewed
       before it is trusted again; it must never silently keep serving a
       stale 'locked' status against new evidence. (This mirrors the
       "no draft/reviewed snapshot reaches consumers" rule, applied to the
       recompute-invalidates-trust direction.)

10. Never write directly to a 'locked' or 'reviewed' status from the
    compiler. Every row the compiler touches lands in (or stays in) 'draft'
    until an operator reviews it. Never write relation_type values other
    than 'co_occurs_with' in v1.
```

`MIN_EVIDENCE_COUNT` for whether a pair is written at all (evidence_count
>= 1 vs a higher floor to reduce single-question noise) is an open question
— Section 8, OQ-4.

---

## 5. Review lifecycle

Reuses the exact transition-matrix + SECURITY DEFINER RPC shape from
migration `204_atomic_snapshot_review_transition.sql`
(`cms_review_exam_topic_snapshot`), which is itself the pattern
`pyq-intelligence-v2.md` and the checklist point to as the reusable review
authority for analytical outputs. v1 proposes a new function,
`cms_review_topic_relation_edge`, with the **same** matrix:

```
draft    → reviewed | rejected
reviewed → locked   | rejected | draft
locked   → reviewed
rejected → draft
```

Mirroring migration 204's contract exactly:

- `SELECT ... FOR UPDATE` the edge row before any transition check
  (concurrent-modification guard).
- Distinguishable errors: `P0404` not_found, `P0409` concurrent_modification,
  `P0422` transition_not_allowed / invalid_target_status /
  invalid_reviewer_notes / missing_actor_id.
- Fail closed on `p_actor_user_id IS NULL` — no unaudited actor can review
  via a direct RPC call.
- `locked → reviewed` requires non-empty `reviewer_notes` (reversal must be
  justified), same as the snapshot RPC.
- Audit INSERT (`admin_audit_logs`, `action='topic_relation_edge_status
  _transition'`, `entity_type='topic_relation_edge'`) and the
  `topic_relation_edges` UPDATE happen in one transaction — no orphan audit
  rows, no silent status changes.
- `SECURITY DEFINER`, fixed `search_path`, `REVOKE ALL` from `PUBLIC`/
  `anon`/`authenticated`, `GRANT EXECUTE` to `service_role` only.

The Python-side transition matrix mirrored in the API layer
(`_EDGE_TRANSITIONS`, same shape as `_SNAPSHOT_TRANSITIONS` in
`admin_exam_intelligence.py`) is a fast-path validation only; the DB
function is the enforcement authority, per the existing "app-only
enforcement is insufficient, multiple service-role write surfaces exist"
rule already applied to `exam_competition_metrics` (J3 OD-8).

**Admin surface:** per the no-new-surface rule, v1 does not add a new
top-level admin page. The natural home is a tab inside the existing PYQ
Workbench, alongside the score-snapshot review panel (`ScoreSnapshotPanel`)
that already reviews a structurally similar draft→reviewed→locked
analytical output for the same operator audience. Whether that tab ships in
the v1 implementation PR or is deferred to a v1.1 follow-up (operator
reviews via direct RPC call in the interim) is Section 8, OQ-6.

---

## 6. Consumers

**New module, not an extension of `coverage.py`.** `coverage.py`'s own
docstring scopes it narrowly: "Reads `exam_topic_coverage` joined with
`topics` + `subjects`... PYQ aggregates filter strictly to
`pyq_question_topic_tags.reviewer_status='verified'`." It is a per-topic
aggregate reader. `topic_relation_edges` is a graph-edge table with its own
review RPC and its own table-level trust gate (`locked`, not `verified`) —
structurally the same reason `score_snapshots.py` is a separate module from
`coverage.py` rather than folded into it. v1 adds
`app/backend/app/exam_intelligence/topic_relations.py`:

```python
def locked_topic_cooccurrence(
    supabase: Any, exam_id: str, topic_id: str | None = None
) -> list[dict[str, Any]]:
    """Return locked co_occurs_with edges for exam_id, optionally filtered
    to edges touching topic_id (as source or target). Only
    reviewer_status='locked' rows are returned — mirrors
    locked_topic_coverage's locked-only contract."""
```

Row shape: `{source_topic_id, source_topic_name, target_topic_id,
target_topic_name, strength, evidence_count, last_observed_year}` (topic
names joined the same two-step way `locked_topic_coverage_summary` joins
`topics`, so behaviour is identical against the live client and unit-test
stubs).

**Planner/mock wiring is explicitly NOT part of v1.** This repeats the
`score_snapshots` delivery precedent on purpose: activating the snapshot
authority (`compute_exam_topic_scores` + review RPC, PR #767/#810) and
wiring it into planner scoring (`locked_score_snapshots()` as a 0–15pt
additive signal, PR #773) were two separate, sequentially-reviewed PRs. v1
here is the "activate the authority" step only. A future PR would decide
*how* co-occurrence should influence the planner (e.g., a same-session
bundling nudge) or mock blueprint selection (e.g., a diversity/
concentration check) — that is a scoring-design decision requiring its own
review, not something to fold into a compiler contract. The v1 deliverable
is: the data exists, is reviewable, and is readable by any future consumer
through `locked_topic_cooccurrence()`. No caller is added to `planner.py` or
`mock_blueprint_selection.py` in this slice.

---

## 7. Explicit non-goals for v1

| Deferred item | Why |
|---|---|
| Distractor/trap pattern compilation (`pyq_option_patterns`) | Different table, different input shape (option-level, not tag-level), no existing "discarded signal" to reuse the way ambiguous multi-tag questions feed co-occurrence. Needs its own contract; `pyq-intelligence-v2.md` P2 already scopes this as "governed cognitive and distractor classification" with its own reviewed-record shape. |
| Question template / near-duplicate detection (`question_relation_edges`) | Requires a similarity/hashing strategy (`normalized_question_hash` exists but no dedup algorithm is specified anywhere in the repo) — a genuinely separate, non-trivial deterministic algorithm design, not a byproduct of existing gated reads. |
| Paper-level co-occurrence (same paper, not same question) | Much noisier signal (every topic in a 100-question paper "co-occurs" with every other); no existing computation to build on; would need its own strength/threshold design and its own review of whether it's even a useful signal before building it. |
| Secondary/trap/calculation_layer/conceptual_layer tags as co-occurrence input | `verified_pyq_topic_counts` deliberately excludes non-primary roles from frequency for a documented reason (role-weighting is an open future option per `pyq-intelligence-v2.md`). Mixing roles into co-occurrence without the same role-weighting decision would silently contradict that contract. |
| `frequently_combined`, `confusion_pair`, `alternate_route`, `revision_cluster`, `cross_subject_link` relation types | Each needs its own semantic definition and evidence source; `co_occurs_with` is the only one with a ready-made, already-gated evidence source (Section 1). |
| Current-affairs / microtopic-level topical linkage beyond what `topics.level='microtopic'` already gives for free | `pyq-intelligence-v2.md` correction #5 is explicit that current affairs needs its own source/provenance/trust model, separate from `exam_policy_updates`, and is P5 in that doc's gap analysis. |
| Cross-exam co-occurrence | v1 edges are `exam_id`-scoped (matches the existing `topic_relation_edges` unique constraint); cross-exam aggregation is a different product question (do two exams' corpora even belong in one strength number?) requiring its own sign-off. |
| Planner/mock scoring wiring | Section 6 — deliberately split into a future PR, mirroring the score-snapshot precedent. |
| Cognitive-demand / Bloom classification | Already P2 in `pyq-intelligence-v2.md`; explicitly out of scope here. |
| Appearance/recurrence prediction | Already P7 in `pyq-intelligence-v2.md` (requires backtesting infrastructure this repo does not have yet); nothing in this document changes that gate. |

---

## 8. Open questions requiring operator/product sign-off

- **OQ-1 (strength formula).** Confirm the overlap coefficient
  (`evidence_count / min(topic_a_count, topic_b_count)`, Section 4 step 7)
  is the desired v1 semantic, versus an alternative normalisation (e.g. a
  PMI-style measure). The overlap coefficient was chosen for
  interpretability (bounded, no arbitrary constants) but a different metric
  may be preferred for downstream ranking.
- **OQ-2 (target table vs. new snapshot table).** Confirm extending
  `topic_relation_edges` in place (Section 3.1, additive columns) is
  preferred over the two-step "versioned snapshot table +
  `coverage_derivation.py`-style projector" pattern J3/coverage_derivation
  uses elsewhere. The in-place approach is simpler and the table has zero
  live rows today (no backfill risk); the two-step approach gives a
  permanent audit trail independent of the mutable edge row but adds a
  second table and a derivation step for a v1 slice this bounded.
- **OQ-3 (recompute-invalidates-trust default).** Confirm that a fingerprint
  change on an already-`locked` pair should silently reset it to `draft`
  (Section 4 step 9) rather than, e.g., keeping the locked row live while a
  new draft revision is queued for review (closer to the J3 two-lane
  revision model). The simpler reset-to-draft means a locked pair can
  temporarily disappear from consumer reads after a corpus update, until
  re-reviewed.
- **OQ-4 (minimum evidence floor).** Confirm whether `evidence_count >= 1`
  is an acceptable floor for writing a draft pair, or whether a higher
  floor (e.g. `>= 2`, requiring the pair to recur across at least two
  verified questions) should gate even a draft write, to reduce reviewer
  noise from single-question coincidences in small corpora.
- **OQ-5 (RLS read scope).** Confirm the proposed `reviewer_status in
  ('reviewed','locked')` authenticated-read policy (Section 3.1) is
  correct, or whether — given v1 ships with no consumer wired in (Section
  6) — the table should stay service-role/admin-only in v1 and the
  authenticated-read policy should be added only alongside the future
  planner/mock consumer PR.
- **OQ-6 (review UI timing).** Confirm whether the PYQ Workbench review tab
  (Section 5) is required in the v1 implementation PR, or whether v1 may
  ship compiler + RPC only, with operators reviewing via direct
  service-role RPC calls until a UI PR follows — mirroring how the
  score-snapshot RPC (migration 204) and its workbench UI (PR #810) were
  separate PRs.
- **OQ-7 (scheduling).** Confirm how the compiler runs — on-demand
  admin-triggered job (matching `mock_readiness_cli.py`'s CLI-trigger
  pattern) vs. an APScheduler job — and at what cadence, given PYQ corpora
  change infrequently (new papers reviewed in batches, not continuously).

---

*This document is a contract draft. It does not authorize any migration,
API, or code change. An implementation PR against this contract must not
be opened until Section 8 is resolved and operator sign-off is recorded,
per this repo's contract-first gate process.*
