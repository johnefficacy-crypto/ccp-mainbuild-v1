# Onboarding knowledge calibration — planner priors from self-assessment

**Status:** SPEC / contract-first. No code in this PR. Awaiting decision sign-off (D1–D3 below).
**Track:** Plan personalization (cold-start). Orthogonal to PYQ Intelligence v2 delivery order.
**Author origin:** Product question — "do first-attempt aspirants with little knowledge and experienced multi-attempt aspirants get the same first study plan? Are we validating preparation level?"

## 1. Problem

The planner produces an identical cold-start plan for a complete beginner and a third-attempt veteran. Both have zero rows in `user_topic_mastery` until they log practice, so `_score_topic()` falls to its no-mastery default (`mastery_gap = 55.0`, `_task_type → concept_learning`) for every topic. A veteran who is strong on Polity but weak on Economy is scheduled `concept_learning` blocks across all of Polity for weeks — the same as someone who has never opened a book. There is no step in the "get your study plan" journey that captures prior knowledge or preparation level.

Verified today (no existing mechanism):
- `user_topic_mastery` (migration 033) has **no `source`/origin column**; the planner reads `mastery_score` with no provenance.
- `recompute_topic_mastery()` (`mastery.py`) upserts on `(user_id, topic_id, exam_id, exam_phase_id)` — it **overwrites** any row not produced by a mock.
- `MasteryWriter` (live mode) reads current mastery as the baseline for deltas and is gated behind `FF_MOCK_MASTERY_WRITES` under an open "DO NOT PROCEED TO LIVE" validation.
- `aspirant_exam_attempts.attempts_used` already records prior attempts per exam but is **never read by the planner**.

## 2. Core principle (non-negotiable)

Self-assessment is a **subordinate prior**, not mastery.

1. **Separate table.** Priors live in a new `user_topic_self_assessment` table. The onboarding path **never writes `user_topic_mastery`** and **never touches `MasteryWriter`** or its feature flags. This keeps the gated mastery-validation apparatus completely isolated.
2. **Validated evidence always wins.** When a topic has a real `user_topic_mastery` row (mock/practice derived), the prior is ignored entirely at read time. The prior only fills the gap where there is no validated evidence yet.
3. **Server-owned mapping.** Bands map to a numeric prior on the server; the client submits only the band. No client-supplied scores.
4. **Auditable.** Every task influenced by a prior records `mastery_source` and a reasoning-trace row that says, in plain words, that this came from self-report and is not yet validated by practice.

This mirrors the discipline already proven in P-slice-2 (locked snapshots): a new, clearly-labelled, bounded, confidence-weighted signal that degrades gracefully and is fully traceable.

## 3. Data model

New table (migration, O-slice-1):

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

  CHECK (subject_id IS NOT NULL OR topic_id IS NOT NULL)
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
```

RLS: owner-only read/write (`user_id = auth.uid()`), matching the `user_topic_mastery` policy family.

### Band → prior mapping (server-owned)

| Band     | `prior_mastery` | Intent |
|----------|-----------------|--------|
| `strong` | 80              | Confident; bias toward revision/retrieval, deprioritize |
| `decent` | 60              | Some grounding; retrieval practice |
| `weak`   | 35              | Shaky; concept learning but flagged as known-weak |
| `new`    | `NULL`          | Never studied — explicit. Planner applies today's cold-start default (no change) |

`new` writes a row (with `prior_mastery = NULL`) so we can distinguish "user says never studied" from "user skipped the question." The planner treats a `NULL` prior exactly as no prior.

## 4. Capture

- **Granularity (D1 — recommended subject-level).** Capture one band per **subject** (`subjects` rows for the exam — e.g. Polity, Modern History, Economy, Geography, Environment, S&T). UPSC GS has on the order of ~10 subjects; a per-topic survey (hundreds of topics) is hostile UX. The band propagates to every `topics` row with that `subject_id` as the per-topic prior. A power-user "refine specific topics" affordance can write topic-level overrides later (`topic_id` set), but v1 ships subject-level only.
- **Attempt count.** Read/confirm `aspirant_exam_attempts.attempts_used` for the target exam. If unknown, ask once ("How many times have you attempted this exam? 0 / 1 / 2+"). Snapshot it onto each prior row as `attempts_used` and derive `report_confidence` (D2).

## 5. Planner consumption (the behavioral change — O-slice-2)

At read time, extend the mastery resolution in `_load_user_signals()` / `_score_topic()`:

```
effective_mastery(topic) =
  validated_mastery(topic)              # user_topic_mastery row → ALWAYS wins
  ?? blended_prior(topic)               # else, self-assessment prior (subject or topic level)
  ?? None                               # else, today's cold-start default (gap 55)
```

Where the prior is **confidence-blended toward neutral** so an unvalidated claim never carries the full weight of validated mastery (D2):

```
neutral = 45.0                          # equals today's no-mastery default (gap 55)
blended_prior = report_confidence * prior_mastery + (1 - report_confidence) * neutral
report_confidence = {0 attempts: 0.5, 1 attempt: 0.75, 2+ attempts: 1.0}
```

Effect — a first-timer (`0 attempts`) self-rating Polity **strong** (80) yields `0.5·80 + 0.5·45 = 62.5`: meaningfully deprioritized vs a `weak` subject, but still hedged because the claim is unproven. A third-attempt veteran rating Polity **strong** yields the full `80` → those topics resolve to `revision`/`retrieval_practice` and drop down the schedule. This is exactly the first-timer-vs-veteran differentiation the product question asked for.

`_task_type()` consumes the same `effective_mastery`, so a `strong` veteran subject schedules `revision` blocks instead of `concept_learning`.

Provenance, recorded per task in `why_this_task` and surfaced by `build_task_reasoning_detail()`:
- `mastery_source ∈ {validated, self_reported, none}`
- when `self_reported`: `self_assessment_band`, `prior_mastery`, `report_confidence`, `assessment_level ∈ {subject, topic}`
- a reasoning-trace row: *"Based on your self-assessment (Strong) for Polity — not yet validated by practice; will update as you take mocks."*

`input_context` gains a `self_assessment_summary` (counts per band, attempts_used) for auditability, mirroring `snapshot_set_summary`.

**No double-write, no contamination.** The prior is read-only input to scoring. When the first validated mastery row appears for a topic, `validated_mastery` wins automatically; optionally stamp `superseded_at` for audit (nice-to-have, not required for correctness).

## 6. Frontend (O-slice-3)

- **Placement (D3 — recommended Study Plan interstitial).** A one-time "Calibrate your starting point" step on the Study Plan page, shown **after** exam selection and **before** first plan generation (exam is known → its `subjects` are loadable). The onboarding chat flow runs pre-exam-selection and cannot enumerate subject areas, so it is the wrong host.
- Subject list with a 4-way band control (Strong / Decent / Weak / Never studied) per subject, plus the attempts question. Skippable — skipping = today's cold-start behavior.
- Re-entrant: user can revisit and adjust until validated mastery accrues.
- Copy must state plainly that this is self-reported and will be refined by actual practice.

## 7. Slicing (mirrors P-slice-1 → P-slice-2 discipline)

| Slice | Scope | Merge safety |
|-------|-------|--------------|
| **O-slice-1 — data + capture** | Migration for `user_topic_self_assessment`; `PUT/GET /api/study/self-assessment` (server owns band→prior + confidence); snapshot `attempts_used`. **Planner unchanged.** | Safe — zero plan-output change. |
| **O-slice-2 — planner consumption** | Gap-fill prior resolution; confidence blend; `mastery_source` + trace row + `self_assessment_summary`; tests. | Behavioral; plans change only for users who self-assessed. |
| **O-slice-3 — frontend** | Calibration interstitial + attempts capture, wired to O-slice-1; regression tests. | UI-gated; backend already live. |

## 8. Test plan (O-slice-2, the behavioral slice)

- First-timer (`0 attempts`) **strong** subject → topics hedged (~62) but still ranked above a **weak** subject; not dropped to `revision`.
- Veteran (`2+ attempts`) **strong** subject → full prior (80) → `_task_type` = `revision`/`retrieval_practice`, deprioritized.
- Topic with a real `user_topic_mastery` row → prior **ignored** (validated wins); `mastery_source = validated`.
- Subject-level prior propagates to all child topics lacking a topic-level override.
- Topic-level override beats subject-level for that topic.
- `new` band → cold-start default unchanged (byte-compatible with no-prior path except `mastery_source = none` and the explicit-new marker).
- `mastery_source` correctly one of validated/self_reported/none per task.
- Reasoning trace contains the self-assessment row with band + "not yet validated" language.
- Determinism preserved — same inputs → same plan.

## 9. Explicitly NOT in scope

- **No adaptive placement quiz.** A scored diagnostic MCQ set is a separate, optional future calibration that can write higher-confidence priors. Self-report ships first because it is fast and low-friction.
- **No writes to `user_topic_mastery`**, no changes to `MasteryWriter`, `recompute_topic_mastery`, or any `FF_MOCK_MASTERY_*` flag.
- **No per-question or per-microtopic capture** in v1.

## 10. Decisions to confirm

- **D1 — Granularity:** subject-level capture, propagated to topics (recommended) vs per-topic capture.
- **D2 — Attempt modulation:** confidence-blend toward neutral, weighted by `attempts_used` (recommended) vs flat value haircut vs no modulation.
- **D3 — Screen placement:** Study Plan interstitial after exam selection (recommended) vs onboarding chat flow.
