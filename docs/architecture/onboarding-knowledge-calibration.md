# Onboarding knowledge calibration — planner priors from self-assessment

**Status:** IMPLEMENTED — PR #778. D1 (subject-level), D2 (attempt-count confidence blend), D3 (Study Plan interstitial) APPROVED.
**Track:** Plan personalization (cold-start). Orthogonal to PYQ Intelligence v2 delivery order.
**Author origin:** Product question — "do first-attempt aspirants with little knowledge and experienced multi-attempt aspirants get the same first study plan? Are we validating preparation level?"

**Decision log:** D1 / D2 / D3 APPROVED as recommended; PR #778 ships subject-level capture, attempt-count confidence blend, and the Study Plan interstitial. An owner review hardened the contract: a dedicated `user_exam_calibration` gate record (not "any assessment row exists"), owner-SELECT-only RLS with no client write policy on either table, a fail-closed mastery read, and a non-blocking `needs_update` re-prompt instead of re-gating.

> This document is the source of truth for the as-built feature. Section anchors below are kept stable; the SQL/pseudo-code blocks mirror the implementation in `app/supabase/migrations/195_user_topic_self_assessment.sql`, `196_user_exam_calibration.sql`, `app/backend/app/api/study_os.py` (self-assessment routes), `app/backend/app/study_os/planner.py`, and `app/backend/app/study_os/task_reasoning.py`.

## 1. Problem

The planner produces an identical cold-start plan for a complete beginner and a third-attempt veteran. Both have zero rows in `user_topic_mastery` until they log practice, so `_score_topic()` falls to its no-mastery default (`mastery_gap = 55.0`, `_task_type → concept_learning`) for every topic. A veteran who is strong on Polity but weak on Economy is scheduled `concept_learning` blocks across all of Polity for weeks — the same as someone who has never opened a book. There is no step in the "get your study plan" journey that captures prior knowledge or preparation level.

Verified today (no existing mechanism):
- `user_topic_mastery` (migration 033) has **no `source`/origin column**; the planner reads `mastery_score` with no provenance.
- `recompute_topic_mastery()` (`mastery.py`) upserts on `(user_id, topic_id, exam_id, exam_phase_id)` — it **overwrites** any row not produced by a mock.
- `MasteryWriter` (live mode) reads current mastery as the baseline for deltas and is gated behind `FF_MOCK_MASTERY_WRITES` under an open "DO NOT PROCEED TO LIVE" validation.
- `aspirant_exam_attempts.attempts_used` already records prior attempts per exam but is **never read by the planner**.

## 2. Core principle (non-negotiable)

Self-assessment is a **subordinate prior**, not mastery.

1. **Separate tables.** Priors live in `user_topic_self_assessment` (evidence) and the gate lives in `user_exam_calibration` (gate record). The onboarding path **never writes `user_topic_mastery`** and **never touches `MasteryWriter`**, `recompute_topic_mastery`, or any `FF_MOCK_MASTERY_*` flag. The gated mastery-validation apparatus stays completely isolated.
2. **Validated evidence always wins.** When a topic has a real `user_topic_mastery` row (mock/practice derived), the prior is ignored entirely at read time. The prior only fills the gap where there is no validated evidence yet.
3. **Server-owned mapping (no client-supplied numbers).** The client submits **only a band**. The server owns `band → prior_mastery` (`{strong:80, decent:60, weak:35, new:NULL}`) and `attempts_used → report_confidence` (`{0:0.5, 1:0.75, 2+:1.0}`). Clients cannot forge `prior_mastery`, `report_confidence`, `attempts_used`, or `source`.
4. **Auditable.** Every task influenced by a prior records `mastery_source` and a reasoning-trace row that says, in plain words, that this came from self-report and is not yet validated by practice.

This mirrors the discipline already proven in P-slice-2 (locked snapshots): a new, clearly-labelled, bounded, confidence-weighted signal that degrades gracefully and is fully traceable.

### 2.1 Security model (critical)

The trust boundary is enforced at the database, not just in the API:

- **Two tables, one purpose each.** `user_topic_self_assessment` holds the evidence — one band row per `(user, exam, subject)` (with a power-user per-`(user, exam, topic)` override slot). `user_exam_calibration` holds the **gate record** per `(user, exam)`: `status` (`completed` | `skipped`), `required_subject_set_hash`, and `attempts_used`.
- **RLS is OWNER-SELECT-ONLY on both tables. There is NO client write policy.** Each table enables RLS and grants only `FOR SELECT USING (user_id = auth.uid())`. The absence of any INSERT/UPDATE/DELETE policy means an authenticated or anon PostgREST caller **cannot write** — the only writers are the backend routes using the **service-role client** (which bypasses RLS). A permissive write policy here would let a signed-in client set arbitrary `prior_mastery` / `report_confidence` / `attempts_used` / `source` directly, bypassing the server-owned mapping. So clients read their own rows for prefill and submit only a band; the server derives every number.
- **The feature never writes `user_topic_mastery`.** It does not call `MasteryWriter` and does not read or set any `FF_MOCK_MASTERY_*` flag. Validated mastery always wins; a self-report can never overwrite or masquerade as validated evidence.

## 3. Data model

Two tables (migrations `195_user_topic_self_assessment.sql`, `196_user_exam_calibration.sql`).

### Evidence table — `user_topic_self_assessment`

```sql
CREATE TABLE public.user_topic_self_assessment (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  exam_id uuid NOT NULL REFERENCES public.exams(id) ON DELETE CASCADE,

  -- Granularity: subject-level by default (D1). topic_id set only for an explicit per-topic override.
  subject_id uuid REFERENCES public.subjects(id) ON DELETE CASCADE,
  topic_id   uuid REFERENCES public.topics(id)   ON DELETE CASCADE,

  band text NOT NULL CHECK (band IN ('strong','decent','weak','new')),
  prior_mastery numeric(5,2)        -- server-derived from band; NULL for band='new'
    CHECK (prior_mastery IS NULL OR (prior_mastery >= 0 AND prior_mastery <= 100)),

  -- Confidence in the self-report, driven by prior-attempt count (D2).
  report_confidence numeric(4,3) NOT NULL DEFAULT 0.5
    CHECK (report_confidence >= 0 AND report_confidence <= 1),
  attempts_used int,                 -- snapshot of aspirant_exam_attempts at capture time

  source text NOT NULL DEFAULT 'onboarding_self_report',
  assessed_at timestamptz NOT NULL DEFAULT now(),
  superseded_at timestamptz,         -- optional: stamped once validated mastery exists for the topic
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,

  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),

  -- Exactly one of subject_id / topic_id (subject-level row XOR topic override).
  CHECK ((subject_id IS NOT NULL) <> (topic_id IS NOT NULL))
);

-- One subject-level row per (user, exam, subject); one topic-level override per (user, exam, topic).
CREATE UNIQUE INDEX uq_self_assessment_subject
  ON public.user_topic_self_assessment(user_id, exam_id, subject_id)
  WHERE subject_id IS NOT NULL AND topic_id IS NULL;
CREATE UNIQUE INDEX uq_self_assessment_topic
  ON public.user_topic_self_assessment(user_id, exam_id, topic_id)
  WHERE topic_id IS NOT NULL;
CREATE INDEX idx_self_assessment_user_exam
  ON public.user_topic_self_assessment(user_id, exam_id);

ALTER TABLE public.user_topic_self_assessment ENABLE ROW LEVEL SECURITY;
-- OWNER-SELECT ONLY. No INSERT/UPDATE/DELETE policy ⇒ clients cannot write;
-- the backend writes via the service-role key (bypasses RLS) so the server owns
-- band→prior_mastery and attempts→report_confidence. A permissive write policy
-- would let a client forge prior_mastery/report_confidence/attempts_used/source.
CREATE POLICY "owner_select" ON public.user_topic_self_assessment
  FOR SELECT USING (user_id = auth.uid());
```

RLS is **owner-SELECT-only with no write policy** (see §2.1) — deliberately stricter than a generic owner read/write family, because every numeric field is server-derived.

### Gate table — `user_exam_calibration`

The explicit per-`(user, exam)` gate record. This row — **not** "any assessment row exists" — controls whether the pre-plan interstitial shows and whether plan generation is unlocked.

```sql
CREATE TABLE public.user_exam_calibration (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  exam_id uuid NOT NULL REFERENCES public.exams(id)     ON DELETE CASCADE,
  status text NOT NULL CHECK (status IN ('completed','skipped')),
  required_subject_set_hash text,   -- required set captured at decision time
  attempts_used int CHECK (attempts_used IS NULL OR attempts_used >= 0),
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_user_exam_calibration ON public.user_exam_calibration(user_id, exam_id);
CREATE INDEX idx_user_exam_calibration_user ON public.user_exam_calibration(user_id);

ALTER TABLE public.user_exam_calibration ENABLE ROW LEVEL SECURITY;
-- OWNER-SELECT ONLY (backend owns gate transitions via the service-role key).
CREATE POLICY "owner_select" ON public.user_exam_calibration
  FOR SELECT USING (user_id = auth.uid());
```

- `status='completed'` ⇒ the user answered the **full** required subject set.
- `status='skipped'` ⇒ the user explicitly skipped. Persisted, so a reload does **not** re-show the interstitial.
- `required_subject_set_hash` snapshots the required set at decision time so a later coverage change can drive a non-blocking re-prompt without re-gating (see §3.1).

### Band → prior mapping (server-owned)

| Band     | `prior_mastery` | Intent |
|----------|-----------------|--------|
| `strong` | 80              | Confident; bias toward revision/retrieval, deprioritize |
| `decent` | 60              | Some grounding; retrieval practice |
| `weak`   | 35              | Shaky; concept learning but flagged as known-weak |
| `new`    | `NULL`          | Never studied — explicit. Planner applies today's cold-start default (no change) |

`new` writes a row (with `prior_mastery = NULL`) so we can distinguish "user says never studied" from "user skipped the question." The planner treats a `NULL` prior exactly as no prior.

### 3.1 Calibration gate contract

`calibrated` is **derived from the gate record, not from evidence-row existence**:

- **Source of truth.** `calibrated = true` iff the `user_exam_calibration` row has `status ∈ {completed, skipped}` **OR** the required subject set for this user/exam is empty (nothing to calibrate ⇒ auto-calibrated). It is **never** inferred from "an assessment row exists" — and the frontend hook never infers it from `items.length`.
- **Required set.** The required set is the subjects of the exam's **locked-coverage** topics, **minus** subjects whose locked topics are already **fully covered by validated `user_topic_mastery`** for this user. A subject is required only if at least one of its locked topics still lacks a validated mastery row. An empty required set ⇒ auto-calibrated (`calibrated=true`, no interstitial).
- **Completeness (all-or-nothing unlock).** The gate flips to `completed` **only when the FULL required set is answered** (existing evidence ∪ this submission covers every required subject). Partial answers never unlock; empty submissions are rejected (422) and a failed save does not advance the gate.
- **Skip is persisted server-side** (`status='skipped'`). A reload does **not** re-show the interstitial.
- **Per-exam.** Calibration is scoped to the target exam. Switching exams triggers an independent gate check (the frontend hook resets all gate state on exam change so one exam's state can't leak to another).
- **`required_subject_set_hash` (coverage drift, no re-gating).** The hash captures the required set at decision time. After the first unlock, later coverage changes do **NOT** re-block plan generation. Instead `GET` compares the current required-set hash to the stored one and returns `needs_update=true`, which drives a **non-blocking** "Update your starting point" prompt for already-calibrated users.

## 4. Capture

- **Granularity (D1 — recommended subject-level).** Capture one band per **subject** (`subjects` rows for the exam — e.g. Polity, Modern History, Economy, Geography, Environment, S&T). UPSC GS has on the order of ~10 subjects; a per-topic survey (hundreds of topics) is hostile UX. The band propagates to every `topics` row with that `subject_id` as the per-topic prior. A power-user "refine specific topics" affordance can write topic-level overrides later (`topic_id` set), but v1 ships subject-level only.
- **Attempt count.** The interstitial asks once ("How many times have you attempted this exam? First attempt / 1 / 2+"); the client sends the chosen `attempts_used` with the submission. The server snapshots it onto each evidence row and onto the gate record, and derives `report_confidence` from it (D2) — clients never send the confidence.

## 5. API surface (`/api/study/self-assessment`)

All three routes resolve the target exam server-side and write evidence/gate rows via the service-role client. Clients submit bands only.

- **`GET /api/study/self-assessment`** — returns the calibration state for the target exam: `calibrated`, `status` (`completed` | `skipped` | `none`), `needs_update`, `required_subjects` (`[{subject_id, subject_name}]`), `items` (saved bands for prefill), and `attempts_used` (prefilled from the gate record, else the max across evidence rows). With no target exam it returns `calibrated:false, status:"none"`; with an empty required set it returns `calibrated:true`.
- **`PUT /api/study/self-assessment`** — body `{bands:[{subject_id, band}], attempts_used}`. **Validation before persist** (so 422 is never remapped to 500): empty submission → 422; duplicate subject → 422; any subject not in the required set → 422. On success it upserts evidence rows on `(user_id, exam_id, subject_id)` with server-derived `prior_mastery`/`report_confidence`. It then writes the **`completed`** gate **only when the full required set is now covered** (existing evidence ∪ this submission). Returns `{ok, upserted_count, calibrated, missing_subject_ids}` — `missing_subject_ids` lists required subjects still unanswered (non-empty ⇒ gate not yet completed).
- **`POST /api/study/self-assessment/skip`** — writes the **`skipped`** gate (with the current `required_subject_set_hash` and optional `attempts_used`). Returns `{ok, calibrated:true, status:"skipped"}`. Persisted, so the interstitial does not reappear on reload.

## 6. Planner consumption (the behavioral change)

At read time the planner resolves mastery in `_load_user_signals()` (validated read) + `_load_topic_priors()` (priors) and blends in the scoring loop:

```
effective_mastery(topic) =
  validated_mastery(topic)              # user_topic_mastery row → ALWAYS wins
  ?? blended_prior(topic)               # else, self-assessment prior (subject- or topic-level)
  ?? None                               # else, today's cold-start default (gap 55)
```

**Priors fill the cold-start gap only; validated mastery wins.** A topic with a `user_topic_mastery` row keeps `mastery_source='validated'` and the prior is never read for it.

**FAIL-CLOSED on the validated read.** `_load_user_signals()` returns a `mastery_ok` flag. If the `user_topic_mastery` read **failed**, priors are **NOT consumed** (`_load_topic_priors` is skipped) — a transient failure must never let a self-report override validated evidence we simply couldn't load this request. `input_context.mastery_read_failed=true` records it. (Distinct from the prior loader's own DB failure, which returns `{}` and the plan still generates with the standard 55-pt gap.)

The prior is **confidence-blended toward neutral** so an unvalidated claim never carries the full weight of validated mastery (D2):

```
neutral = 45.0                          # equals today's no-mastery default (gap 55)
effective = report_confidence * prior_mastery + (1 - report_confidence) * 45.0
report_confidence = {0 attempts: 0.5, 1 attempt: 0.75, 2+ attempts: 1.0}
```

`band='new'` → `prior_mastery = NULL` → no blend; the cold-start gap is preserved (topic_mastery stays `None`, 55-pt gap) but recorded with `mastery_source='self_reported'` so an explicit "never studied" is **distinguishable from "no response"** (which stays `none`).

Effect — a first-timer (`0 attempts`) self-rating Polity **strong** (80) yields `0.5·80 + 0.5·45 = 62.5`: meaningfully deprioritized vs a `weak` subject, but still hedged because the claim is unproven. A third-attempt veteran rating Polity **strong** yields the full `80` → those topics resolve to `revision`/`retrieval_practice` and drop down the schedule. This is exactly the first-timer-vs-veteran differentiation the product question asked for.

`_task_type()` consumes the same `effective_mastery`, so a `strong` veteran subject schedules `revision` blocks instead of `concept_learning`.

**Provenance (per task in `why_this_task`).**
- `mastery_source ∈ {validated, self_reported, none}`.
- When a prior contributed (including `band='new'`), the persisted `why_this_task` carries `self_assessment_band` (incl. `'new'`), `self_assessment_prior_mastery`, `self_assessment_confidence`, and `self_assessment_level` (`subject` | `topic`).
- **Honest user-facing wording.** The summary line for a self-report reads *"you rated yourself '<band>' here — a self-assessment estimate (~N%), not yet validated by practice"* (or *"marked this as never studied …"* for `new`). Only **validated** mastery may be phrased as *"your recent accuracy is N%"* — a blended prior is **never** labelled as recent accuracy.

**Audit rollup.** `input_context.self_assessment_summary` (built by `_self_assessment_summary()`, mirroring `snapshot_set_summary`) carries `topics_with_prior`, `by_band` counts, `attempts_used`, `assessment_level`, and the distinct contributing `subject_ids`; it is `None` when no prior fed the plan.

**Reasoning trace.** `task_reasoning` emits a `self_assessment_prior` trace row (layer `user`) — `band`, `assessment_level`, `report_confidence`, `prior_mastery`, and `status: "not yet validated by practice"` — built **from the persisted `why_this_task` lineage with no re-query** (it mirrors the `locked_score_snapshot` trace row).

**No double-write, no contamination.** The prior is read-only input to scoring. When the first validated mastery row appears for a topic, `validated_mastery` wins automatically; optionally stamp `superseded_at` for audit (nice-to-have, not required for correctness).

## 7. Frontend

The pre-plan interstitial (`PrePlanCalibration`) lives on the Study Plan page (`StudyPlan.jsx`) and is driven by the `useCalibrationPriors` hook.

- **Placement (D3 — Study Plan interstitial).** A one-time "Calibrate your starting point" step shown **after** exam selection and **before** first plan generation (`calibrated === false` and no plan tasks yet). The onboarding chat flow runs pre-exam-selection and cannot enumerate subject areas, so it is the wrong host. Defense-in-depth: the page also short-circuits draft/apply while `calibrated === false`.
- **Renders the required subjects** (`required_subjects` from GET), each with a 4-way band control (Strong / Decent / Weak / Never studied), plus the attempts question (First attempt / 1 / 2+).
- **"Save & continue" requires all required subjects answered** — the button is disabled until every required subject has a band; a helper shows `answered/total`. Submit sends `{bands, attempts_used}` then refetches authoritative gate state (a partial save leaves `calibrated` false).
- **Prefills from saved `items`** (matched on `subject_id`) and the prefilled `attempts_used`, so an editing user sees their saved answers selected.
- **Skippable, persisted.** "Skip for now" calls the skip route; the persisted `skipped` gate means a reload does not re-show the interstitial.
- **Non-blocking edit/revisit for calibrated users.** Already-calibrated users get an "update anytime" affordance; when `needs_update=true` (coverage drift) a non-blocking "Update your starting point" prompt is shown without re-gating plan generation.
- **`calibrated` is never inferred locally** from `items.length`; the hook sets it only from the GET response (`null` while loading), resets all gate state on exam change, and exposes `retry`/`error` so a fetch failure isn't treated as permanently uncalibrated.
- Copy states plainly that this is self-reported and will be refined by actual practice.

## 8. Slicing (mirrors P-slice-1 → P-slice-2 discipline)

All slices below shipped in PR #778. The hardened gate (`user_exam_calibration`, owner-SELECT-only RLS, fail-closed read, `needs_update`) was added across slices 1–3 by the owner review.

| Slice | Scope | Status |
|-------|-------|--------|
| **O-slice-1 — data + capture** | Migrations for `user_topic_self_assessment` + `user_exam_calibration`; `GET/PUT /api/study/self-assessment` + `POST …/skip` (server owns band→prior + confidence; gate transitions); snapshot `attempts_used`. **Planner unchanged.** | Done (PR #778). |
| **O-slice-2 — planner consumption** | Gap-fill prior resolution; confidence blend; fail-closed validated read; `mastery_source` + `self_assessment_prior` trace row + `self_assessment_summary`; tests. | Done (PR #778). |
| **O-slice-3 — frontend** | Calibration interstitial + attempts capture, wired to O-slice-1; gate-derived `calibrated`; non-blocking `needs_update` prompt; regression tests. | Done (PR #778). |

## 9. Test plan (the behavioral slice)

- First-timer (`0 attempts`) **strong** subject → topics hedged (~62) but still ranked above a **weak** subject; not dropped to `revision`.
- Veteran (`2+ attempts`) **strong** subject → full prior (80) → `_task_type` = `revision`/`retrieval_practice`, deprioritized.
- Topic with a real `user_topic_mastery` row → prior **ignored** (validated wins); `mastery_source = validated`.
- Subject-level prior propagates to all child topics lacking a topic-level override.
- Topic-level override beats subject-level for that topic.
- `new` band → cold-start default unchanged (byte-compatible with no-prior path except `mastery_source = none` and the explicit-new marker).
- `mastery_source` correctly one of validated/self_reported/none per task.
- Reasoning trace contains the self-assessment row with band + "not yet validated" language.
- Determinism preserved — same inputs → same plan.

## 10. Explicitly NOT in scope

- **No adaptive placement quiz.** A scored diagnostic MCQ set is a separate, optional future calibration that can write higher-confidence priors. Self-report ships first because it is fast and low-friction.
- **No writes to `user_topic_mastery`**, no changes to `MasteryWriter`, `recompute_topic_mastery`, or any `FF_MOCK_MASTERY_*` flag.
- **No per-question or per-microtopic capture** in v1. (The `topic_id` override slot exists in the schema but v1 captures subject-level only.)

## 11. Decisions (resolved — APPROVED)

- **D1 — Granularity: subject-level capture, propagated to topics.** APPROVED. One band per subject, expanded to every locked-coverage topic with that `subject_id`; per-topic override slot reserved but unused in v1.
- **D2 — Attempt modulation: confidence-blend toward neutral, weighted by `attempts_used`.** APPROVED. `report_confidence = {0:0.5, 1:0.75, 2+:1.0}`, `effective = rc·prior + (1−rc)·45`.
- **D3 — Screen placement: Study Plan interstitial after exam selection.** APPROVED. Rendered before first plan generation, not in the onboarding chat flow.
