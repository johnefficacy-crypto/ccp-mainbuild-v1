---
owner: ops
status: failed
validation_date: 2026-06-18
environment: seed
source_of_truth: operator_evidence
verified_main_sha: c2d228258f853f8bab077e49c29b8aff45596988
verified_backend_sha: 5ef4438429841205338767084703bbe6b4a32406
related_code:
  - app/backend/app/study_os/mastery_writer.py
  - app/backend/app/study_os/mock_engine.py
  - app/backend/app/study_os/mastery_engine
  - app/backend/app/study_os/correction_policy.py
related_migrations:
  - app/supabase/migrations/144_mock_mastery_dark_launch.sql
review_cadence: after-remediation
---

# SSC CGL Generated Mock — Shadow Validation Report

> **What this is.** A durable, evidence-backed record of the operator-executed
> off/shadow validation of the Track A generated-mock → Study OS mastery
> write-back, run against the `seed` environment on 2026-06-18. It is immutable
> once filed (audit convention); live per-PR status lives in the PR tracker, and
> the durable decision/plan lives in
> [`docs/study_os/mock-engine-v2-study-os-integration.md`](../study_os/mock-engine-v2-study-os-integration.md).
>
> **Provenance.** Findings are transcribed from the operator's local read-only
> evidence bundle (`shadow-validation-20260617T193144Z`). That bundle is
> operator-held **outside** the repository and is **not** committed (it may carry
> environment-specific identifiers). This documentation PR did **not** query the
> database, call live APIs, or change any flag — see [§2](#62-scope-and-method).
>
> **Verification discipline.** Claims that could not be tied to a captured row,
> a source excerpt, or an explicit operator confirmation are tagged `[VERIFY]`.
> Unverified claims are never rendered as PASS. A retryable defect remains FAIL.

---

## 6.1 Executive verdict

```text
DO NOT PROCEED TO LIVE
```

The generated-attempt machinery is sound, but the mastery write-back is **not
safe** to apply to live tables. Specifically:

- **Generated attempt start and frozen-snapshot scoring passed.** A 100-question
  SSC CGL generated mock started from a persisted blueprint (`template_id` null,
  `generated_blueprint_id` populated), froze 100 distinct MCQs, scored
  completely against the frozen snapshot, and the independent score
  recomputation matched the API result.
- **Off-mode isolation passed.** With `FF_MOCK_MASTERY_WRITES=off`, no Study OS
  table received any write (all off-mode negative counts were zero).
- **Shadow-mode live-table isolation passed.** With `FF=shadow`, writes landed
  only in `mock_mastery_shadow`; `user_topic_mastery`,
  `user_topic_error_patterns`, `mock_correction_tasks`, and the planner tables
  were untouched.
- **Shadow correctness FAILED.** The proposed mastery data was **unsafe and
  non-idempotent**: 28 untouched (frozen-but-not-attempted) topics received
  negative deltas, classification evidence never reached the writer, and a
  resubmit duplicated the shadow rows (31 → 62).

Because the shadow **correctness** gate failed, **live remains blocked**. This
verdict is **not** "continue shadow", "conditionally ready", "nearly passed", or
"ready after minor fixes". It is a hard stop pending remediation and a clean
repeat of the same validation.

---

## 6.2 Scope and method

- This report **documents a previously executed operator run**. The operator
  performed the validation; this PR converts the read-only evidence into
  repository documentation and status updates.
- This documentation PR **did not query the database**.
- This documentation PR **did not call any live API**.
- This documentation PR **did not alter any feature flag**.
- All evidence came from the operator's local bundle
  `shadow-validation-20260617T193144Z`; the raw bundle remains operator-held
  outside the repository and is not committed.
- The canary used the **fixed SSC CGL exam and phase IDs** (set-light text-MCQ
  canary, per decision-doc §4c / D4) — not a randomized exam selection.

---

## 6.3 Environment and provenance

| Field | Value |
| --- | --- |
| Validation date | 2026-06-18 |
| Environment | `seed` |
| Supabase project reference | `ylfnbxyqiyiqvxtthhum` (public ref) |
| Verified main SHA | `c2d228258f853f8bab077e49c29b8aff45596988` |
| Deployed backend SHA | `5ef4438429841205338767084703bbe6b4a32406` (Render service `ccp-api-demo`) |
| Frontend deployment SHA | `[VERIFY: operator-supplied, recorded in env.sh; not captured in committed evidence]` |
| Disposable operator user ID | `902ceffb-87b1-4433-bf52-8a9eee7e7268` (operator-confirmed disposable) |
| Phase A attempt ID / blueprint ID | `9abb5a98-00f6-429c-834c-0a7a71e9d5c2` / `501fbd35-d9ad-4bba-92fd-34f9b20ed8f3` |
| Phase B attempt ID / blueprint ID | `79277b89-19d2-4576-8055-f8c3196844a0` / `552593ba-c490-4c4a-95a8-886d322b610e` |
| Phase B canary topics | POS `a5f810db-2afb-4aff-8de3-a73dac0db297`; NEG `e931b58d-1722-4f60-8787-a93d16828d27`; MIX `00ee2e5e-8040-49bc-a6bb-4646a15f4867` |
| Validation start / end | `2026-06-17T19:31:44Z` → `2026-06-18T06:48:00Z` (approx) |

**Backend behind main.** The deployed backend SHA
(`5ef4438429841205338767084703bbe6b4a32406`) was **4 commits behind** `main`
(`c2d228258f853f8bab077e49c29b8aff45596988`), the difference being **frontend /
docs only**. The operator reported that the validation-relevant backend files —
`mastery_writer.py`, `correction_policy.py`, `correction_tasks.py`, `mocks.py` —
were **byte-identical** between the deployed SHA and `main`, so the findings
apply to both.

`[VERIFY]` — the byte-identity statement is recorded in `final-report.md` as an
operator assertion; no dedicated diff-capture file is listed in the evidence
index, so it is **operator-asserted, not independently re-verified** in this
documentation PR.

---

## 6.4 Schema introspection

- **Present tables (17):** `mock_attempt_jobs`,
  `mock_attempt_response_classification`, `mock_attempt_responses`,
  `mock_attempt_section_breakdown`, `mock_attempt_summary`,
  `mock_attempt_topic_breakdown`, `mock_attempts`, `mock_correction_tasks`,
  `mock_generated_blueprints`, `mock_mastery_shadow`, `mock_tests`,
  `study_adaptation_events`, `study_plans`, `study_tasks`,
  `user_topic_error_patterns`, `user_topic_mastery`, `user_topic_mastery_audit`.
- **Absent (1):** `mock_attempt_questions` — there is **no** per-attempt question
  table (expected).
- **Frozen questions** are therefore held in **`mock_attempt_responses`** (the
  `question_snapshot` payload freezes `topic_id`/`difficulty`/`correct_option_id`
  and options), not in a dedicated questions table.
- **`mock_mastery_shadow` columns (all 11, per `table-columns.txt`):**
  `attempt_id`, `user_id`, `topic_id`, `proposed_delta_unit`, `proposed_delta_db`,
  `proposed_delta_db_unweighted`, `current_mastery_db`, `would_be_mastery_db`,
  `decided_at`, `flag_state`, `trust_level`.
- **Constraints / indexes:** PK on `id`; FKs to `mock_attempts` / topics /
  profiles; `CHECK (flag_state in ('shadow','live'))`; btree index on
  `attempt_id`. **No unique constraint** on `(attempt_id, topic_id, flag_state)`
  — confirmed absent (`shadow-constraints-indexes.txt`). This absence is the
  structural cause of the Phase C duplication; see
  [§6.7](#67-phase-c--idempotency) and DEFECT-002.
- **Schema deviations** noted during introspection (re-queried accordingly):
  `exam_phases.phase_name` (not `name`/`stage_name`); `study_tasks` has
  `updated_at`, not `created_at`; `mock_attempt_section_breakdown` has no
  `attempted` column.

> Full column lists from `table-columns.txt` are otherwise not reproduced; only
> the shadow table (central to DEFECT-002) is given in full.

---

## 6.5 Phase A — flag off

`FF_MOCK_MASTERY_WRITES=off`. A generated SSC CGL attempt was started, answered,
and submitted. The intent of Phase A is to prove the generated attempt path
works end-to-end **and** that with the flag off, **nothing** flows into Study OS.

- **Flag state:** `off` (operator-confirmed effective; all 5 off-mode negatives
  = 0 rows).
- **Generated origin:** `template_id` **null**; `generated_blueprint_id` =
  `501fbd35-…` **populated**; `status=in_progress`, `generated=true`;
  `snapshot_exam_id`/`phase_id` match the canary IDs.
- **Frozen questions:** 100 frozen rows; 100 **distinct** question IDs; 0
  duplicate rows; 100 **MCQ**; `topic_id`/`difficulty`/`correct_option_id`/
  options present on all; **25 per section** across the four SSC CGL Tier-1
  sections (General Intelligence and Reasoning, General Awareness, Quantitative
  Aptitude, English Comprehension).
- **Answer design:** 3 correct (45/60/70 s), 3 wrong (5/180/120 s), 1
  marked-unanswered (10 s); 7 distinct topics.
- **Submit result:** HTTP **200**; score **5.25**; **3 correct / 3 wrong / 94
  unattempted**. Independent frozen-snapshot recomputation **matched** the stored
  score.
- **Analytics:** `mock_attempt_summary` computed; `analytics_quality` =
  `events_used=0, events_malformed=8` (DEFECT-007). `mock_attempt_section_breakdown`
  returned **1** row labelled "General" (DEFECT-004).
  `mock_attempt_topic_breakdown` returned 31 rows (7 touched with correct counts;
  24 untouched at `attempted=0`).
- **Classification:** `mock_attempt_response_classification` had **100** rows —
  3 correct, 1 `silly_mistake`, 2 `knowledge_gap`, 1 `marked_unanswered`, 93
  `time_pressure_unattempted` — all consistent with the answer design.
- **Jobs / compatibility:** `mock_attempt_jobs` held a single `mock_tests_retry`
  job at `status=pending, attempts=0`, `last_error` 22P02 `"200.0" -> integer`
  (DEFECT-005); the `mock_tests` row was therefore **absent**.
- **Off-mode negatives:** `mock_mastery_shadow=0`, `user_topic_mastery_audit=0`,
  corrections-via-`mock_tests`=0, corrections-by-user-in-window=0,
  `study_adaptation_events=0` — **off-isolation passes**.

| Check | Expected | Observed | Result | Evidence |
| ----- | -------: | -------: | ------ | -------- |
| Generated origin (`template_id` null) | null | null | PASS | `phase-a-origin-selection.txt` |
| Generated origin (`generated_blueprint_id` set) | set | set | PASS | `phase-a-origin-selection.txt` |
| Frozen questions | 100 | 100 | PASS | `phase-a-origin-selection.txt` |
| Distinct question IDs | 100 | 100 | PASS | `phase-a-origin-selection.txt` |
| MCQ-only | 100 | 100 | PASS | `phase-a-origin-selection.txt` |
| Per-section count | 25 | 25 | PASS | `phase-a-origin-selection.txt` |
| Snapshot completeness | 100 | 100 | PASS | `phase-a-score-check.txt` |
| Submit HTTP result | success | success | PASS | `phase-a-score-check.txt` |
| Independent score match | match | match | PASS | `phase-a-score-check.txt` |
| Analytics / classification | produced | produced | PASS | `phase-a-analytics-jobs.txt` |
| Off-mode shadow writes | 0 | 0 | PASS | `phase-a-off-negatives.txt` |
| Off-mode mastery writes | 0 | 0 | PASS | `phase-a-off-negatives.txt` |
| Off-mode error-pattern writes | 0 | 0 | PASS | `phase-a-off-negatives.txt` |
| Off-mode correction writes | 0 | 0 | PASS | `phase-a-off-negatives.txt` |

**Phase A verdict: PASS.** Generated start, frozen-snapshot scoring, result
integrity, and off-mode isolation all hold.

---

## 6.6 Phase B — shadow

`FF_MOCK_MASTERY_WRITES=shadow`. A second generated SSC CGL attempt was answered
with a **designed** topic pattern (strong-positive, strong-negative, mixed, and
deliberately **untouched** topic roles) so the deltas are predictable, then
submitted. Shadow writes should land **only** in `mock_mastery_shadow`.

- **Baselines:** operator had **0** prior rows in `user_topic_mastery`,
  `user_topic_error_patterns`, `user_topic_mastery_audit`,
  `mock_correction_tasks`, active `study_plans`, and `study_tasks`
  (`phase-b-isolation-counts.txt`).
- **Answer design:** 5 POS all correct at expected time; 5 NEG all wrong at 2×
  expected time (≥120 s); 4 MIX alternating correct / wrong-fast /
  marked-unanswered / correct. ATTEMPT_B distinct from A; **14** answers in DB at
  submit (the marked-unanswered one has `selected_option_id` NULL).
- **Score verification:** HTTP **200**; score **12.50**; **7 correct / 6 wrong /
  87 unattempted**; independent frozen-snapshot recomputation **matched**
  (`phase-b-score-check.txt`).
- **Shadow row count:** **31** rows written to `mock_mastery_shadow`, one per
  topic in the attempt (`phase-b-shadow-rows.txt`).
- **Trust state:** all 31 shadow rows `flag_state=shadow`,
  `trust_level=platform_verified` (`phase-b-trust.txt`).
- **Mathematical invariants:** all delta caps, scaling, clamping, sign, and
  formula checks held (`phase-b-shadow-math.txt`).
- **Live-table isolation:** `user_topic_mastery`, `user_topic_error_patterns`,
  `mock_correction_tasks`, and planner tables showed **zero** diff vs baseline
  (`phase-b-isolation-counts.txt`).
- **Source / trust compatibility:** `mock_tests` had **0** rows for ATTEMPT_B
  (DEFECT-005), so `MasteryWriter._load_trust_level` fell back to
  `platform_verified` — benign for this run but masks the missing compatibility
  row.
- **Attempted-semantics: FAILED.** 28 topics that were **frozen but never
  attempted** (0 selected, `analytics_attempted=0`) received **negative** deltas
  of −6 to −15 db — e.g. `1056e16d` (4 frozen, 0 selected) → −15; `cf7e589d` (1
  frozen, 0 selected) → −6. The writer treats every frozen response as
  attempted, so a topic with N frozen / 0 selected looks like N/N wrong = 0%
  accuracy, producing maximum cap-bounded negative deltas
  (`phase-b-attempted-semantics.txt`).

| Metric                                     | Observed | Result |
| ------------------------------------------ | -------: | ------ |
| Shadow rows                                |       31 | PASS   |
| Wrong flag rows                            |        0 | PASS   |
| Wrong trust rows                           |        0 | PASS   |
| Unit-cap violations                        |        0 | PASS   |
| DB-cap violations                          |        0 | PASS   |
| Scale violations                           |        0 | PASS   |
| Clamp violations                           |        0 | PASS   |
| Formula violations                         |        0 | PASS   |
| Untouched topics receiving negative deltas |       28 | FAIL   |

Representative topic evidence (`phase-b-attempted-semantics.txt`):

| Topic role         | Frozen | Selected | Analytics attempted |     Delta |
| ------------------ | -----: | -------: | ------------------: | --------: |
| Strong positive    |      5 |        5 |                   5 |       +15 |
| Strong negative    |      5 |        5 |                   5 |       -15 |
| Mixed              |      4 |        3 |                   3 |       -10 |
| Untouched examples |      N |        0 |                   0 | -6 to -15 |

**Interpretation — math correct, semantics wrong.** The delta arithmetic was
**internally consistent with the writer's input**: every cap, scale, clamp, and
sign check passed. But the **writer's input semantics were wrong** — it counted
frozen-but-unattempted responses as attempted, so untouched topics were scored
as if answered incorrectly. **Mathematical consistency does not make the output
safe.** A topic the user never touched must not move mastery.

**Phase B verdict: FAIL** on attempted-semantics (DEFECT-001), despite the
isolation and math sub-checks passing.

---

## 6.7 Phase C — idempotency

The same shadow attempt was **resubmitted** to test retry-safety
(`phase-c-before.txt`, `phase-c-after.txt`, `phase-c-resubmit-result.json`).

- **Before resubmit:** `shadow_rows=31`, `compat_rows=0`, `audit_rows=0`,
  `score_raw=12.50`, `submitted_at=2026-06-18T06:44:15.083998+00`.
- **Resubmit:** HTTP **200**; result body identical; `submitted_at` unchanged;
  score unchanged.
- **After resubmit:** `shadow_rows=`**62**, `compat_rows=0`, `audit_rows=0`,
  score/submitted unchanged.
- **All 31 attempt/topic/state groups duplicated** (every topic now has 2 shadow
  rows for the same `(attempt_id, topic_id, flag_state)`).
- **Compatibility-row count remained zero** (see DEFECT-005A).

**Correct interpretation:**

- Shadow persistence was **not idempotent** — there is no DB uniqueness on
  `(attempt_id, topic_id, flag_state)` (see [§6.4](#64-schema-introspection)), so
  repeated writer execution **duplicates** shadow rows.
- Repeated writer execution is demonstrated; the writer ran again on resubmit and
  appended a second full set of shadow rows.
- **Live mastery RPC application is separately audit-idempotent.** The live path
  applies deltas through the `apply_mock_mastery_delta` RPC
  (`mastery_writer.py:77-78`), which is audit-protected; this run did **not**
  prove that live mastery would double-apply.
- Resubmit may still **replay other writer side effects** (e.g. error-pattern
  upserts, correction drafts) and therefore remains **unsafe** until the full
  pipeline is made retry-safe.

> Recorded interpretation (verbatim):
>
> ```text
> resubmitting proved shadow duplication and repeat writer execution; live mastery
> RPC application is separately audit-idempotent, while other live side effects
> still require retry-safety verification.
> ```

**Phase C verdict: FAIL** on shadow idempotency (DEFECT-002).

---

## 6.8 Phase D — correction evidence propagation

Phase D checked whether the persisted question-level classifications actually
reach `MasteryWriter` to drive correction drafts
(`phase-d-classified-responses.json`, `phase-d-correction-diagnostic.json`).

- **100 / 100 persisted classifications** in
  `mock_attempt_response_classification`, with rich error types across 31 topics.
- **Enriched diagnostic drafts: 30** — the enriched pipeline (with
  classifications) produces 30 correction drafts.
- **Writer-equivalent drafts: 1** — re-running `derive_correction_tasks` with
  `error_type=None` (mirroring production) produces 1 draft.
- **29 of 30 classified topics differed** between the enriched diagnostic and the
  writer-equivalent output (`phase-d-correction-diagnostic.json`).
- **Root cause:** `MasteryWriter._load_analytics()` reads `error_type` from a
  `mock_attempt_responses` row that **does not contain that column**, and it does
  **not** load `mock_attempt_response_classification`. (Confirmed in code:
  `_load_analytics` selects only
  `question_id,is_correct,time_spent_sec,question_snapshot` at
  `mastery_writer.py:112`, then reads `r.get("error_type")` at
  `mastery_writer.py:133` — that key is always absent.)

**Differentiation — #704 vs runtime integration:**

- **#704 shared correction policy: merged and code-level parity tested.** The
  source-neutral `correction_policy.select_categories(...)` exists
  (`correction_policy.py:170`) and both production adapters call it
  (`mocks.py:344`, `mastery_engine/correction_tasks.py:82`); adapter parity is
  test-pinned.
- **Production submit integration: FAILED.** The classification inputs never
  reached the writer, so the merged policy ran on empty/degraded evidence.

This is **not** a claim that #704 itself was invalid. #704's shared policy is
sound; the **runtime integration needed to realize it** (feeding persisted
classifications into `MasteryWriter`) was **incomplete**.

**Phase D verdict: FAIL** on classification propagation (DEFECT-003).

---

## 6.9 Phase E — parity and trust

Two **separate** conclusions, kept distinct (`phase-e-manual-parity.json`,
`phase-e-trust-weight-check.txt`).

### Confirmed

- **Trust constants:** `platform_verified = 1.0`; `self_reported = 0.3`. The
  pure weighting check: `platform_verified` weighted base `0.15 → 0.150`;
  `self_reported` weighted base `0.15 → 0.045`; ratio = **0.3**. PASS.
- **Manual adapter parity:** 30 of 31 topics matched between
  `mocks._draft_corrections_from_mock` and `select_categories` — the single
  mismatch is the all-correct POS_TOPIC (see Unconfirmed / DEFECT-006).
- This was a **constant-level** check of configured weights — **not** a measured
  runtime manual mastery delta.
- The **manual draft path does not itself run `MasteryWriter`**, so this does not
  exercise the live mastery write.

### Unconfirmed

- The reported "all-correct manual divergence" used **unequal inputs**:
  - the manual adapter received a **weak topic**;
  - the direct generated policy did **not** receive an equivalent
    `weak_topic=True`.
- Because the two sides were not given equivalent inputs, **DEFECT-006 is NOT
  confirmed by this run**. It is marked `[VERIFY] / NOT PROVEN` and is **not**
  counted among the blocking defects.

Correction-policy parity:

| Evidence case                           | Generated                      | Manual        | Result                          |
| --------------------------------------- | ------------------------------ | ------------- | ------------------------------- |
| Equivalent recognized errors            | same ordered categories/titles | same          | PASS                            |
| All-correct + unequal weak-topic inputs | no draft vs concept fallback   | unequal input | NOT PROVEN                      |
| Trust weight                            | 1.0                            | 0.3           | PASS — configured constant only |

**Phase E verdict: PASS** on trust constants and equivalent-input parity;
**NOT PROVEN** on the all-correct divergence (unequal fallback inputs).

---

## 6.10 Defect register

### Confirmed blockers

**DEFECT-001 — attempted-semantics.** HIGH. Untouched frozen responses are
treated as attempted; **28** untouched topics received negative deltas
(Phase B). **Blocks live.**

**DEFECT-002 — shadow persistence idempotency.** HIGH. **31 rows became 62** on
resubmit; no DB uniqueness on `(attempt_id, topic_id, flag_state)`. **Blocks the
shadow gate and live progression.** *Corrected live-RPC interpretation:* live
mastery application uses an audit-idempotent RPC and is **not** proven to
double-apply; the proven failure is **shadow** duplication plus repeat writer
execution, with other live side effects still needing retry-safety verification.

**DEFECT-003 — classification propagation.** HIGH. Persisted classifications do
**not** reach `MasteryWriter` (`_load_analytics` never loads
`mock_attempt_response_classification` and reads a non-existent `error_type`
column). **Blocks correction-task correctness.**

**DEFECT-005A — compatibility-row numeric coercion.** MEDIUM. `"200.0"` was
rejected by the integer `total_marks` column (Postgres 22P02), so the
`mock_tests` compatibility row was **absent** for both attempts.
`_load_trust_level` then fell back to `platform_verified`. **Blocks dependable
integration behavior.** *(The operator's `defects.md` logs this as a single
DEFECT-005 "observability"; this report splits the **proven** coercion failure —
005A — from the **unproven** worker-progress claim below.)*

### Confirmed non-blocking findings

**DEFECT-004 — section breakdown collapse.** MEDIUM. The section breakdown
collapsed to a single "General" section. Analytics/UX issue; does not block live.

**DEFECT-007 — malformed event telemetry.** LOW. `analytics_quality` reported
`events_used=0` with `events_malformed=8` (Phase A) and `=15` (Phase B) — every
answer-endpoint event was treated as malformed. Scores/classifications were
still reconstructed from the response rows, so this does not block live.

### Unverified or split findings

**DEFECT-005 (retry-worker portion) — split.** The pending mastery/analytics job
remained at `attempts=0`, but the scheduler configuration was **not captured**
sufficiently. The worker is **not** declared broken without proof that
`ENABLE_SCHEDULER=true`. Labeled `[VERIFY: deployment scheduler state not
captured]`.

**DEFECT-006 — all-correct manual divergence.** `NOT PROVEN — unequal fallback
inputs`. The operator's `defects.md` logs this as LOW, but the reproduction fed
the manual adapter `weak_topics=[topic]` while `select_categories()` received no
equivalent `weak_topic=True`; the divergence is an artifact of **unequal
inputs**, so it is **not confirmed** by this run and is **not** counted as a
blocker (see [§6.9](#69-phase-e--parity-and-trust)).

| ID | Status | Severity | Blocks live | Owner |
| -- | ------ | -------- | ----------- | ----- |
| DEFECT-001 | Confirmed | HIGH | Yes | study-os |
| DEFECT-002 | Confirmed | HIGH | Yes | study-os |
| DEFECT-003 | Confirmed | HIGH | Yes | study-os |
| DEFECT-004 | Confirmed | MEDIUM | No | study-os |
| DEFECT-005 (worker) | NOT PROVEN | — | `[VERIFY]` | ops |
| DEFECT-005A | Confirmed | MEDIUM | Yes | study-os |
| DEFECT-006 | NOT PROVEN | — | No | study-os |
| DEFECT-007 | Confirmed | LOW | No | study-os |

**Confirmed blocking defects: 4** (DEFECT-001, -002, -003, -005A).

---

## 6.11 Pass/fail matrix

| Gate | Result | Evidence |
| ---- | ------ | -------- |
| #704 present on main | PASS | code: `correction_policy.py:170`; `mocks.py:344`; `correction_tasks.py:82` |
| Disposable operator user | PASS | `session.txt` |
| Canary readiness (SSC CGL ready) | PASS | `phase-a-origin-selection.txt` |
| Generated start (`template_id` null, `generated_blueprint_id` set) | PASS | `phase-a-origin-selection.txt` |
| 100 questions | PASS | `phase-a-origin-selection.txt` |
| Section counts (25 each) | PASS | `phase-a-origin-selection.txt` |
| MCQ-only | PASS | `phase-a-origin-selection.txt` |
| Frozen scoring completeness | PASS | `phase-a-score-check.txt` |
| Submit result | PASS | `phase-a-score-check.txt` |
| Independent score match | PASS | `phase-a-score-check.txt` / `phase-b-score-check.txt` |
| Off isolation | PASS | `phase-a-off-negatives.txt` |
| Shadow rows (31) | PASS | `phase-b-shadow-rows.txt` |
| Trust state | PASS | `phase-b-trust.txt` |
| Delta cap | PASS | `phase-b-shadow-math.txt` |
| Scale | PASS | `phase-b-shadow-math.txt` |
| Clamp | PASS | `phase-b-shadow-math.txt` |
| Sign | PASS | `phase-b-shadow-math.txt` |
| Untouched-topic semantics | FAIL | `phase-b-attempted-semantics.txt` (DEFECT-001) |
| Duplicate shadow rows (idempotency) | FAIL | `phase-c-after.txt` (DEFECT-002) |
| Live mastery isolation | PASS | `phase-b-isolation-counts.txt` |
| Live error-pattern isolation | PASS | `phase-b-isolation-counts.txt` |
| Live audit isolation | PASS | `phase-b-isolation-counts.txt` |
| Correction isolation | PASS | `phase-b-isolation-counts.txt` |
| Planner isolation | PASS | `phase-b-isolation-counts.txt` |
| Classifications persisted (100) | PASS | `phase-d-classified-responses.json` |
| Classifications propagated to writer | FAIL | `phase-d-correction-diagnostic.json` (DEFECT-003) |
| Policy parity (equivalent inputs) | PASS | `phase-e-manual-parity.json` |
| Trust constants (1.0 / 0.3) | PASS | `phase-e-trust-weight-check.txt` |
| Compatibility row | FAIL | `phase-c-resubmit-result.json` (DEFECT-005A) |
| All-correct manual divergence | NOT PROVEN | `phase-e-manual-parity.json` (DEFECT-006, unequal inputs) |
| Retry-worker progress | NOT PROVEN | `[VERIFY]` scheduler state not captured |
| Frontend deployment SHA | NOT APPLICABLE | `[VERIFY: not captured in evidence bundle]` |

---

## 6.12 Recommendation and next gate

```text
DO NOT PROCEED TO LIVE
```

Required remediation **before** operator revalidation:

1. **Selected-response-only mastery attempted semantics** — only attempted
   selected responses move mastery; untouched frozen topics must not (DEFECT-001).
2. **Classification-table propagation into `MasteryWriter`** — load
   `mock_attempt_response_classification` and feed question-level `error_type`
   into the shared policy (DEFECT-003).
3. **DB-enforced shadow idempotency and conflict-safe writes** — uniqueness on
   `(attempt_id, topic_id, flag_state)` plus upsert/on-conflict (DEFECT-002).
4. **Schema-safe integral `mock_tests.total_marks` persistence** — coerce to the
   integer column so the compatibility row is written (DEFECT-005A).
5. **Deploy the remediation.**
6. **Repeat the same off/shadow operator validation** (identical SSC CGL canary
   and phases).
7. **Only a clean repeat may change the recommendation.**

This report does **not** authorize `live`. `FF_MOCK_MASTERY_WRITES` stays out of
`live` until the repeated gate passes cleanly.

---

## 6.13 Evidence index

The following local evidence filenames (from
`shadow-validation-20260617T193144Z`) were used in this report. They are **not**
committed; the raw bundle remains operator-held outside the repository, and the
Windows path is intentionally **not** rendered as a clickable link.

- `final-report.md`
- `defects.md`
- `pass-fail-matrix.md`
- `session.txt`
- `table-existence.txt`
- `table-columns.txt`
- `phase-a-origin-selection.txt`
- `phase-a-score-check.txt`
- `phase-a-analytics-jobs.txt`
- `phase-a-off-negatives.txt`
- `phase-b-score-check.txt`
- `phase-b-shadow-rows.txt`
- `phase-b-shadow-math.txt`
- `phase-b-attempted-semantics.txt`
- `phase-b-isolation-counts.txt`
- `phase-b-trust.txt`
- `shadow-constraints-indexes.txt`
- `diff-user-topic-mastery.txt`, `diff-error-patterns.txt`,
  `diff-mastery-audit.txt`, `diff-corrections.txt`, `diff-active-plan.txt`,
  `diff-study-tasks.txt`
- `phase-c-before.txt`
- `phase-c-after.txt`
- `phase-c-resubmit-result.json`
- `phase-d-classified-responses.json`
- `phase-d-correction-diagnostic.json`
- `phase-e-manual-parity.json`
- `phase-e-trust-weight-check.txt`
- `file-list.txt`
