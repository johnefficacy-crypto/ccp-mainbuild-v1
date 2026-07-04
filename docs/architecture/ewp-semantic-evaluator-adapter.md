# EWP Semantic Evaluator Adapter — Design Proposal (NOT YET APPROVED FOR IMPLEMENTATION)

> Status: **PROPOSAL**. No code in this repository implements this design. It
> exists to satisfy CLAUDE.md's rule that an LLM adapter may only be added
> "when explicitly justified in an architecture doc" — this is that
> justification, submitted for product-owner review before any evaluator code
> is written. Until a dated "APPROVED" line is added below by the product
> owner, `correction`/`grammar`/`vocabulary_in_context` prompt types remain
> **BLOCKED** for activation (checklist: "Prompt bank seed").

## 1. Problem this closes

Migration 221/222 surfaced `prompt_text`/`source_text` on the evaluation-claim
payload (`ewp_claim_evaluation_job`), but `evaluation_worker.py` still calls
`language_evaluator.evaluate_language(answer_text, exercise_type=...)` — it
never receives or consumes `source_text`. For the 150 `sentence_correction` /
`grammar` rows and the source-bearing `vocabulary_in_context` rows in the
prompt-bank seed, correctness is defined as *"the aspirant's answer is a
meaning-preserving correction of `source_text`"* — a property the current
mock evaluator cannot check at all (it only pattern-matches the answer in
isolation: double spaces, a fixed informal-word list, a handful of
subject-verb bigrams). A clean, fluent, but entirely unrelated sentence
currently passes.

## 2. Why the two already-tried shortcuts are rejected

Both were tried and reverted (PR #882) and must not be reattempted:

1. **Heuristic "does it mention words from source_text" scoring.** Case-only
   corrections produced false must-fix flags; punctuation-only evasions
   passed; and the `off_topic` issue_type — the only §5.1 taxonomy entry that
   fits "ignored the source" — projects to `misread_question`/`concept_gap`
   in the §6 canonical-error table. Misfiring it on a *correctly executed*
   correction poisons real mastery evidence, not just this one exercise.
2. **Any deterministic string-similarity threshold** (edit distance, token
   overlap %, etc.) — these are trivially gamed (copy `source_text` verbatim
   plus one token) and trivially wrong on legitimate rewrites (a correct fix
   that changes many surface tokens, e.g. rewriting passive to active voice).

Meaning-preservation is a semantic judgment. It requires either a human
reviewer per submission (not scalable — this is a practice loop, not a
one-off review queue) or a language model. This doc proposes the latter,
gated.

## 3. Proposed design

### 3.1 Adapter boundary (unchanged shape, new implementation)

`language_evaluator.py` already defines the adapter seam:

```python
class LanguageEvaluator(Protocol):
    def evaluate(self, answer_text: str, *, exercise_type: str,
                 active_prior_issues=None, resolved_prior_lineages=None) -> LanguageResult: ...

def get_language_evaluator() -> LanguageEvaluator:
    # TODO: select the real adapter here behind a feature flag
    return MockLanguageEvaluator()
```

This proposal:

- Adds `source_text: str | None = None` to `LanguageEvaluator.evaluate()`'s
  signature (both implementations; the mock ignores it — the mock's contract
  does not change otherwise).
- Adds `LlmLanguageEvaluator` implementing the same Protocol, calling the
  Claude API with a structured-output tool matching `LanguageIssueOut`
  exactly (`extra="forbid"`, the fixed §5.1 `IssueType` enum, UTF-16 span
  fields) — the API contract the rest of the pipeline already expects does
  not change; only what produces it does.
- `evaluation_worker.py`'s `run_worker_pass` passes `claim["source_text"]`
  (already present on the claim payload since migration 222) through to
  `lang.evaluate_language(...)`.
- Model: `claude-sonnet-5` (structured-output tool-call, not chat text
  parsing — the harness already retries on tool-schema mismatch, matching the
  pattern this codebase uses elsewhere for forced structured output).
- New issue_type is NOT introduced for "unrelated to source" — see §3.4.

### 3.2 Feature flag and rollout (mirrors the existing mastery Lane-A gate)

```
FF_WRITING_LLM_EVAL: off | shadow | live      (default: off)
```

- **off** (default, current state): `get_language_evaluator()` returns
  `MockLanguageEvaluator` unconditionally. No behavior change from today.
- **shadow**: both evaluators run per submission. The mock's result is what
  the aspirant sees and what drives state transitions (unchanged blast
  radius); the LLM result is persisted to a new `writing_language_shadow`
  table (mirrors the existing `writing_mastery_shadow` pattern — same
  append-only, same no-live-effect posture) for offline false-positive/
  false-negative rate measurement against a human-labelled sample (§16 gate 5
  already requires this measurement to exist; shadow mode is how it gets
  produced without touching a live aspirant flow).
- **live**: the LLM result replaces the mock as the persisted
  `language_result` for exercise types that need source-comparison
  (`sentence_correction`, `grammar`'s underlying type, `vocabulary_in_context`
  when source-bearing). Exercise types that don't need `source_text`
  (`sentence_construction`, `paragraph_writing`) keep using the mock
  indefinitely — there is no meaning-preservation check to make for those,
  so introducing model variance there would be a strictly worse trade.

Flag resolution follows the same per-user override precedence as
`mastery_flag.py`'s `resolve_effective_writing_mastery_flag` (global default,
overridable). No new precedence design needed — reuse that helper's shape.

### 3.3 Fail-closed behavior (the hard requirement)

- **Adapter error, timeout, or malformed structured output** → the job fails
  via the existing `ewp_fail_evaluation_job` retry path (same as any other
  evaluator exception today — `evaluation_worker.py`'s existing
  `except Exception` wrapper already does this; no new code path). It must
  **never** silently fall back to the mock for a `live`-flagged exercise type
  — a silent fallback would defeat the entire point (a mock pass on an
  unrelated sentence) while *looking* like a real semantic check happened.
- **Low-confidence model output**: the structured-output schema gains a
  required `meaning_preserved_confidence: float` field (0–1) alongside the
  issue list, mirroring the existing Stage-3 rubric confidence-gating pattern
  (§5.4: "if confidence < 0.6 ... flagged for human review"). Below the same
  0.6 threshold, `needs_human_review=true` is set on the evaluation row (the
  column already exists — Stage-3 sets it today) and the unit's must_fix
  issues from the model are still applied fail-closed (never auto-pass on
  low confidence).
- **Cost/latency budget**: one Claude call per submission, same call site as
  today's synchronous-adjacent-but-actually-async Stage-2 job (§8.1: "runs
  OUTSIDE any DB transaction"). No change to the transaction/locking design —
  the call already happens outside the DB transaction specifically so a slow
  or hung call only holds the lease, not a lock. Target p95 latency and per-
  request cost must be measured in shadow mode before any `live` flip; this
  doc does not pre-commit a number.

### 3.4 What the model is asked to check — and NOT asked to check

The model receives `source_text` and `answer_text` and is asked to identify:

- language issues per the existing frozen §5.1 `IssueType` enum (unchanged —
  the model is not given a new vocabulary), AND
- whether `answer_text` is a **meaning-preserving correction** of
  `source_text` (a boolean-ish signal, not a new issue_type).

**The "not meaning-preserving" signal does NOT reuse `off_topic`.** `off_topic`
already has a defined §6 projection (`misread_question`/`concept_gap`) for a
*different* failure mode (the aspirant addressed the wrong prompt entirely,
e.g. in `sentence_construction`/`paragraph_writing` where there is no
`source_text` to compare against). Conflating "ignored the sentence I was
asked to fix" into the same bucket is exactly the PR #882 mistake. This
proposal instead adds a **new, source-comparison-specific outcome** that
short-circuits BEFORE issue-event insertion:

- If `meaning_preserved = false` (and confidence is high enough to trust it),
  the evaluation is NOT completed as a normal pass/fail-with-issues. It is
  routed to `needs_human_review=true` with zero issue events and zero
  positive mastery evidence — the architecture already defines "unprojected
  issues are excluded from mastery evidence but available in the Error Lab"
  (§6) as the safe default for anything the system cannot confidently
  categorize; this reuses that existing safe default rather than inventing a
  new projection or overloading an existing one. A human reviewer (EWP-3
  review producer UI, already the mechanism for correcting projections)
  makes the final call.

This keeps the canonical error taxonomy (§6) exactly as-is — no new frozen
category, no change to `correction_policy.py`, no change to any existing
projection rule.

### 3.5 Governance compliance

- **"No new AI writes"** (CLAUDE.md): this does not add a new AI-authored
  *database write path*. The model's structured output flows through the
  IDENTICAL `writing_issue_events`/`writing_evaluations` write path Stage-2
  already uses today (that path already accepts LLM-shaped structured output
  by design — §5.3's doc header literally says "Async LLM call with
  structured output schema" for Stage 2; the mock is explicitly a stand-in
  for that, not the target state). No Neo4j/Pinecone/LangGraph/pgvector is
  introduced. No unreviewed AI-authored row bypasses review: `off`/`shadow`
  writes nothing live; `live` writes exactly what Stage-2 already writes
  today, still fed through the same backend-owned taxonomy-mapping validation
  (§5.3: "the model returns only `issue_type`... the backend owns the
  mapping" — unchanged).
- **Determinism > Heuristics / Trust > Speed**: honored by keeping `off` the
  default, requiring a measured shadow-mode false-positive/negative rate
  against a human-labelled benchmark (§16 gate 5) before any `live` flip per
  exercise type, and by the fail-closed behavior in §3.3.

## 4. What must exist before any `live` flip (operator + code gates)

1. This doc has a dated **APPROVED** line from the product owner.
2. `LlmLanguageEvaluator` implemented + unit-tested (schema validation,
   fail-closed on adapter error, confidence-gating) — behind `FF_WRITING_LLM_EVAL=off` default.
3. Shadow mode run against a real (or curated) submission sample; false-
   positive/negative rate measured and recorded in the checklist against §16
   gate 5's "acceptable false-positive rate for grammar feedback" bar.
4. Cost/p95-latency measured in shadow mode and recorded.
5. Per-exercise-type activation is independent: `sentence_correction`/
   `grammar`/source-bearing `vocabulary_in_context` gate on this design;
   `sentence_construction`/`paragraph_writing` are UNAFFECTED (mock stays,
   indefinitely, unless a future doc proposes otherwise for a different
   reason).
6. Operator sign-off recorded in `docs/status/career-copilot-checklist.md`.

## 5. Explicitly out of scope for this doc

- Stage-3 rubric evaluation (`rubric_evaluator.py`) — already async-shaped
  and already confidence-gated; a real-adapter proposal for it is a separate
  doc if/when paragraph rubrics land (checklist: "No paragraph rubric"
  blocker, itself gated on EWP-6 §16).
- Any change to the mastery evidence key, evidence tiers, or projection
  rules — none are touched by this proposal.
- Any change to `writing_prompts`/`writing_sessions` schema — the source
  text is already available via the migration-222 session snapshot; this doc
  only proposes a new consumer of it.
