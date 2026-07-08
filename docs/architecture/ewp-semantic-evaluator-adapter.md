# EWP Semantic (LLM) Evaluator Adapter — Design Proposal

> **Status: PROPOSAL / governance record.** This document is the explicit
> architecture justification required by the locked CLAUDE.md invariant *"Add
> pgvector or LLM adapter only when explicitly justified in an architecture
> doc."* It **authorizes building the semantic adapter in SHADOW mode only.**
> LIVE mode (model outcomes affecting the evaluation lifecycle or mastery)
> stays **BLOCKED** until the promotion gates in §5 pass with captured evidence
> and operator sign-off is recorded in `docs/status/career-copilot-checklist.md`.
> Until then `sentence_correction` / `grammar` / source-bearing
> `vocabulary_in_context` prompt types remain **inactive** (checklist:
> "Prompt bank seed" runtime blocker).
>
> Scope: English Writing Practice (EWP) Stage-2 language evaluation only. This
> doc authorizes no other evaluation path and no new AI *write*. It does not
> authorize Neo4j, Pinecone, LangGraph, or pgvector.

Read with: `docs/architecture/english-writing-practice.md` (§4.10 review,
§5 evaluation stages, §6 canonical-error taxonomy, §10.3 shadow-to-live, §16
release gates), the **EWP-SP1 / EWP-SP1a** and **prompt-bank-seed** rows in
`docs/status/career-copilot-checklist.md`, and the current code:
`app/backend/app/study_os/writing_practice/language_evaluator.py`,
`evaluation_worker.py`. Migration 222
(`222_ewp_prompt_snapshot_and_exam_derivation.sql`) already snapshots
`prompt_text`/`source_text` per session.

---

## 1. Problem

Stage-2 language evaluation is **content-blind**. The shipped evaluator
(`language_evaluator.py`, `lang-mock-v1`) is a pure, deterministic, rule-based
mock: double spaces, a lowercase sentence start, a fixed informal-token lexicon,
naive subject-verb bigrams, and periodless run-ons. It never sees the prompt or
the source text and cannot reason about meaning.

For three prompt families this is not merely incomplete — it is **wrong**:

- **Sentence correction** — the aspirant is given a flawed `source_text` and must
  fix it *while preserving its meaning*. A clean, fluent, but entirely unrelated
  sentence currently passes. Correctness requires comparing the answer against
  the source: was the required error actually fixed, and was the meaning kept?
- **Grammar** — many items require judging whether a construction is correct *in
  the context of the intended sentence*, not by surface pattern.
- **Vocabulary (in context)** — word-choice / collocation correctness depends on
  the intended sense, which a lexicon cannot resolve.

Migration 222 already snapshots the runtime-affecting prompt contract onto
`writing_sessions.prompt_snapshot` (immutable, guarded by
`ewp_guard_session_snapshot`), and `ewp_claim_evaluation_job` surfaces
`prompt_text`/`source_text` to the worker. **The data is available; the worker
does not yet consume it** — `evaluation_worker.py` still calls
`evaluate_language(answer_text, exercise_type=...)` only. This is the
"worker half, design-gated" runtime blocker on the prompt-bank-seed checklist
row: the affected prompt types stay inactive until source-aware semantic
comparison exists behind a governed adapter.

Source-aware meaning-preservation **cannot be judged deterministically** with
acceptable fidelity. String-similarity thresholds (edit distance, token overlap)
are trivially gamed (copy `source_text` verbatim plus one token) and trivially
wrong on legitimate rewrites (passive→active recasting changes many tokens). It
is a semantic judgment: either a human reviewer per submission (not scalable for
a practice loop) or a language model. That, narrowly, is the sole justification
for an LLM adapter.

---

## 2. Adapter boundary contract

The adapter lives behind the existing `LanguageEvaluator` Protocol
(`language_evaluator.py`) and is selected in `get_language_evaluator()` behind
the `FF_WRITING_LLM_EVAL` flag (§3). The deterministic mock stays the default.

### 2.1 Evaluate signature

```
evaluate(
    answer_text: str,
    *,
    exercise_type: str,
    prompt_text: str | None,
    source_text: str | None,
    active_prior_issues: list[dict] | None = None,
    resolved_prior_lineages: list[dict] | None = None,
) -> LanguageResult
```

`prompt_text` and `source_text` are added to the current Protocol signature and
are read from the **session snapshot** (migration 222), never live
`writing_prompts`. The deterministic mock ignores the two new parameters, so the
addition is backward-compatible and `lang-mock-v1` behavior does not change.

The result stays the existing `LanguageResult`
(`issues: list[LanguageIssueOut]`, `evaluator_version`). The adapter reports its
own `evaluator_version` (e.g. `lang-llm-v1`, including model + prompt-template
version) so historical findings stay auditable (§4.6). Every returned
`LanguageIssueOut` MUST satisfy the shipped contract: an `issue_type` from the
frozen §5.1 taxonomy (the model is given no new vocabulary), UTF-16 spans that
verify against `answer_text` (§4.5b), and `predecessor_issue_event_id` only
referencing an `active_prior_issues` id (validated in `evaluate_language`,
unchanged). The backend still owns the taxonomy→microtopic mapping (§5.3).

### 2.2 Deterministic source-comparison result states (SP1 baseline)

EWP-SP1 shipped three **deterministic** source-comparison outcome states. They
are the authority the semantic adapter **augments, never replaces**:

| State | Meaning (deterministic) |
|---|---|
| `source_unchanged` | The answer is normalization-equivalent to `source_text` — no correction was attempted. Deterministic, high-confidence; the adapter is never consulted to overturn it. |
| `meaning_not_preserved` | A deterministic signal (e.g. the required correction target was deleted, or divergence past a deterministic bound) shows the source meaning was lost. |
| `source_comparison_uncertain` | The deterministic layer cannot decide meaning-preservation. **This is the hand-off point** where the semantic adapter contributes signal. |

**Augment, never replace.** The adapter runs *after* the deterministic layer and
may only:

1. On `source_comparison_uncertain`, contribute a semantic judgment that either
   ADDS a language issue or routes the unit to human review (§2.3); or
2. On any state, ADD independently-detected grammar/vocabulary issues the mock
   missed.

The adapter may **never** clear a `meaning_not_preserved`, never overturn a
deterministic `must_fix`, and never convert a deterministic fail into a pass.
Determinism holds authority; the semantic layer is additive signal only.

### 2.3 Source-mismatch outcome — do NOT reuse `off_topic`

When the adapter judges the answer to not preserve / not address the source, the
unit routes to **human review** via the existing `needs_human_review` mechanism
(the same evaluation-row field the Stage-3 rubric evaluator already sets,
consumed by `ewp_complete_language_evaluation` as `p_needs_human_review`), with
zero issue events and zero positive mastery evidence. A dedicated
source-comparison outcome carries this — it is **never** encoded by reusing the
`off_topic` `issue_type`.

> Reusing `off_topic` for source mismatch was the PR #882 mistake this design
> replaces. `off_topic` has a defined §6 projection (`misread_question` /
> `concept_gap`) for a *different* failure mode (the aspirant addressed the wrong
> prompt entirely). Firing it on a correctly-executed correction poisons real
> mastery evidence, not just this one exercise. The two judgments must stay
> distinct to preserve the §5.1 taxonomy and its microtopic mapping.

Routing to `needs_human_review` reuses the architecture's existing safe default
for anything the system cannot confidently categorize; the EWP-3 review producer
UI (already the mechanism for correcting projections) makes the final call. No
new frozen taxonomy category, no change to any existing projection rule.

---

## 3. `FF_WRITING_LLM_EVAL` state machine

A single flag, defaulting **off**, drives a three-state machine. It is
independent from `FF_WRITING_MASTERY_WRITES` (Lane A) and does not relax it — a
LIVE semantic outcome still writes mastery evidence only in whatever mode the
mastery flag independently permits (shadow today).

### OFF (current, default)

Deterministic mock only. Zero model calls, zero network — identical to today.
This is the state on `main` and the only state the adapter runs in until §5 gate
evidence is captured.

### SHADOW (what this doc authorizes building)

- The semantic adapter **is called** for the affected exercise types.
- Its output is **recorded for measurement only** — model-vs-deterministic
  disagreement, latency, token cost, and self-reported confidence — to an
  append-only shadow sink (mirrors the existing `writing_mastery_shadow`
  no-live-effect pattern).
- **ZERO lifecycle effect and ZERO mastery effect.** The persisted evaluation,
  issue events, unit transition, review lifecycle, and mastery outbox are driven
  **exclusively** by the deterministic result, exactly as in OFF. Shadow output
  never reaches `ewp_complete_language_evaluation` as authoritative issues.
- This mode produces the human-labelled false-positive / false-negative,
  latency, and cost evidence the §5 gates require.

### LIVE (BLOCKED until §5 gates pass)

- The model outcome is **allowed to affect the lifecycle** — its issues persist,
  its source-comparison judgment can route a unit to human review.
- **Still fail-closed.** On adapter error, timeout, low confidence, malformed
  structured output, or a `source_comparison_uncertain` the model cannot
  resolve, the unit routes to `needs_human_review` — it does **not** silently
  pass, does **not** fabricate a verdict, and does **not** silently fall back to
  the mock (a mock pass on an unrelated sentence would defeat the whole point).
  Fail-closed is the safety floor in every mode.
- LIVE still cannot overturn a deterministic denial (§2.2) and still does not
  reuse `off_topic` (§2.3).

Transitions are one-directional under gate control (off → shadow → live) and
operator-reversible (live → shadow → off) at any time without data migration.

---

## 4. Flag mechanics, cost, and safety controls

- `FF_WRITING_LLM_EVAL ∈ {off, shadow, live}`, default `off`, resolved
  server-side with the same per-user override precedence as
  `mastery_flag.py::resolve_effective_writing_mastery_flag` — never
  client-supplied. It is read once per job in
  `evaluation_worker.run_worker_pass` and pinned for that job (mirroring the
  mastery-flag pin) so a mid-flight flip cannot split one evaluation.
- **Per-exercise-type activation is independent.** `sentence_correction` /
  `grammar` / source-bearing `vocabulary_in_context` gate on this design;
  `sentence_construction` / `paragraph_writing` are UNAFFECTED (no
  meaning-preservation check to make — the mock stays indefinitely).
- **No unreviewed AI writes.** The adapter writes nothing to canonical tables
  directly. All persistence flows through the existing
  `ewp_complete_language_evaluation` RPC and the §4.10 review lifecycle; in
  SHADOW its output is not passed to that RPC at all. Issues it contributes in
  LIVE remain subject to `writing_issue_review_events` correction exactly like
  mock-authored issues.
- **Determinism authority unchanged.** Eligibility and every other deterministic
  surface are untouched; within EWP the adapter can only ADD an issue or route
  to human review, never grant a pass a deterministic rule denied.
- **Timeout:** the adapter call runs OUTSIDE the DB transaction (worker §8.1
  step 3), so a hang only holds the lease and the sweeper reclaims it. Hard
  per-call wall timeout (default 20 s) → treated as adapter error → fail-closed.
- **Retry:** at most 2 retries with exponential backoff on transient / 5xx /
  timeout; a non-transient (validation/refusal) response is not retried.
- **Circuit breaker:** consecutive failures over a threshold trip to
  deterministic-only for a cooldown window (logged, observable). A tripped
  breaker in LIVE degrades affected units to `needs_human_review`, never to
  auto-pass.
- **Cost controls:** one model call per submission, structured-output tool call
  matching `LanguageIssueOut` (no free-text parsing); per-unit cost ceiling
  enforced as a promotion gate (§5, G5-e).
- **Confidence gating:** the structured output carries a required
  `meaning_preserved_confidence ∈ [0,1]`, mirroring the Stage-3 rubric 0.6
  threshold; below threshold → `needs_human_review=true`, never auto-pass.
- **PII posture:** only **session-snapshot text** leaves the boundary —
  `answer_text`, `prompt_text`, `source_text`, `exercise_type`, and the
  structured `active_prior_issues` / `resolved_prior_lineages` needed for
  lineage. **No user identifiers, no exam identifiers, no mastery state, no auth
  metadata** are sent to the provider. Payloads are the minimum to evaluate one
  answer against one source.

---

## 5. Promotion gates (off → shadow → live)

Promotion is **evidence-gated, not time-gated**, and ties to §16 **gate 5**
(*"Acceptable false-positive rate for grammar feedback (human-labelled
sample)"*) of `english-writing-practice.md`, extended here with concrete,
measurable exit criteria. All rates are measured on a curated, human-labelled
benchmark of correction / grammar / vocabulary answers.

### 5.1 off → shadow (authorized by this doc)

- This document is merged (governance record exists).
- The adapter is implemented behind the boundary, computing the deterministic
  result first and discarding model authority (SHADOW semantics proven by test).
- The shadow telemetry sink records disagreement / latency / cost / confidence.
- Timeout, retry, and circuit breaker (§4) are wired.

No model-quality thresholds are required to *enter* shadow — shadow exists to
*measure* them.

### 5.2 shadow → live (BLOCKED until all pass, with captured evidence)

Measured over a **minimum sample of 500 human-labelled answers per affected
exercise type** (correction, grammar, vocabulary evaluated independently):

| Gate | Metric | Exit criterion |
|---|---|---|
| G5-a | False-positive rate (adapter flags an issue a human rejects) | ≤ **5%** per exercise type |
| G5-b | False-negative rate (adapter misses a human-confirmed `must_fix`) | ≤ **10%** per exercise type |
| G5-c | Source-mismatch precision (correction only) | ≥ **90%** of adapter "source mismatch → human review" routes agreed by the human labeller |
| G5-d | p95 adapter latency (call, outside DB txn) | ≤ **8 s** |
| G5-e | Cost ceiling | ≤ **US$0.02** per evaluated unit at the benchmark model/settings |
| G5-f | Minimum sample size | ≥ **500** labelled answers **per** affected exercise type before any rate is trusted |
| G5-g | Determinism-authority regression | **0** cases where the adapter cleared a deterministic `must_fix` or turned a deterministic fail into a pass |
| G5-h | Operator approval | Recorded in the checklist with the captured evidence linked |

Any gate failing keeps the flag at `shadow`. **G5-g failing is a hard block** — it
means the augment-never-replace boundary leaked and must be fixed before any
further promotion. Rates are recomputed on the then-current default model before
each promotion; a model or provider swap resets the shadow evidence window.
Promotion is per exercise type: one type may reach LIVE while others stay in
SHADOW.

---

## 6. Model / provider posture

- **Default to the latest Claude models** per environment guidance at build time.
  The exact model id is resolved from configuration, **never hardcoded** in this
  doc or in source, and **no secrets** appear here or in the repo (keys come from
  the environment).
- The adapter is **provider-swappable** behind the `LanguageEvaluator` boundary:
  the §2 contract is provider-neutral, so a different provider or a local model
  can be substituted without touching callers. A provider/model swap resets the
  §5.2 shadow evidence window.

---

## 7. Governance decision record

**Authorized by this document:**

- Build the semantic (LLM) adapter behind the `LanguageEvaluator` boundary and
  the `FF_WRITING_LLM_EVAL` flag.
- Run it in **SHADOW** mode (measurement only, zero lifecycle / mastery effect)
  to capture the §5.2 evidence.
- Add `prompt_text` / `source_text` to the evaluator Protocol and consume the
  migration-222 session-snapshot source in the worker for shadow measurement.

**Explicitly still BLOCKED (not authorized here):**

- **LIVE** mode — blocked until every §5.2 gate passes with captured,
  human-labelled evidence and operator approval is recorded in the checklist.
- Activation of `sentence_correction` / `grammar` / source-bearing
  `vocabulary_in_context` prompt types for aspirants — remains gated on LIVE plus
  the existing prompt-bank review lifecycle.
- Any AI *write* into a canonical table; any new vector store (pgvector,
  Pinecone), Neo4j, or LangGraph. Out of scope; the prohibition is unchanged.

This is a deliberate, scoped exception to "no new AI writes": the adapter adds
**read / evaluate** capability under shadow measurement, not authoritative AI
writes. LIVE authority requires a separate, evidence-backed promotion recorded in
`docs/status/career-copilot-checklist.md`.

## 8. Explicitly out of scope

- Stage-3 rubric evaluation (`rubric_evaluator.py`) — already async-shaped and
  confidence-gated; a real-adapter proposal for it is a separate doc if/when
  paragraph rubrics land (gated on EWP-6 §16).
- Any change to the mastery evidence key, evidence tiers, or projection rules.
- Any change to `writing_prompts` / `writing_sessions` schema — the source text
  is already available via the migration-222 session snapshot; this doc only
  proposes a new consumer of it.
