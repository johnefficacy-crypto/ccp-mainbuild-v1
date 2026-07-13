# Operator runbook — SP1b semantic evaluator, SHADOW provisioning + evidence

**Audience:** operator with API-service env access + a provider API key.
**Goal:** run the already-merged SP1b semantic adapter in **SHADOW only** for correction / grammar / vocabulary, collect the `writing_language_evaluator_runs` telemetry, and drive the §5.2 evidence window. **LIVE stays BLOCKED** — nothing here promotes to live.

The adapter is code-complete on `main` (`app/backend/app/study_os/writing_practice/semantic_evaluator.py`). This runbook is **operational only** — no code changes.

> **Scope — SP1b's *evidence* is for source-dependent types** (`sentence_correction`, grammar, `vocabulary_in_context`); the §5.2 gates and any eventual LIVE promotion apply per-type to those. **But the shadow probe as currently coded is FLAG-WIDE, not type-scoped** — see the ⚠️ warning below. Shadow output never affects a learner: it is written to an append-only telemetry table and discarded for authority.
>
> ⚠️ **The worker does NOT gate the shadow provider call by exercise type.** `run_worker_pass` calls `_run_semantic_shadow_probe(...)` **unconditionally** after every deterministic evaluation; `get_semantic_shadow_evaluator()` gates only on `FF_WRITING_LLM_EVAL=shadow`; and `SemanticLanguageEvaluator.evaluate()` makes the provider call for **any** `exercise_type` (no construction skip). `_is_source_dependent()` only controls the **deterministic source-comparison**, not whether the shadow provider runs. **Consequence:** enabling the flag on a live worker with active `sentence_construction` traffic will send those construction submissions to the provider too — counting toward cost and sending answer text to the provider. Plan for this (see §3) or land a code gate first (see §6).

---

## 1. What SHADOW mode is (and its guardrails)

`FF_WRITING_LLM_EVAL ∈ {off, shadow, live}`, **fails closed to `off`**. Structural guarantees (do not weaken):
- `get_semantic_shadow_evaluator()` returns the adapter **only** when the flag is exactly `shadow`; the canonical `get_language_evaluator()` always returns the deterministic mock.
- Shadow output is written **only** via `ewp_record_language_evaluator_run` → `public.writing_language_evaluator_runs` (append-only, immutability trigger, `role CHECK ('shadow')`, service-role only).
- **No raw text** is persisted — only a SHA-256 `input_hash` + counts/summary + telemetry (provider/model/tokens/cost/latency/status).
- The shadow probe runs inside a try/except in the eval worker and is discarded for authority; a deterministic verdict can never be turned into a pass.

---

## 2. Provision the shadow run

Set on the **API service + the eval-worker/scheduler process** (same deployment):
```bash
FF_WRITING_LLM_EVAL=shadow
ANTHROPIC_API_KEY=<provider key>          # read by the Anthropic SDK; never hardcoded/committed
# optional — pin the benchmark model; defaults to the adapter's built-in default:
EWP_SEMANTIC_MODEL=<current-default Claude model id>
```
Notes:
- Keep the key in the environment/secret store only — it must never land in the repo or logs.
- `off` (or unset) → the adapter is never constructed; `live` → still returns `None` from the shadow seam (live is blocked by design).
- A **model/provider swap resets** the §5.2 evidence window — pin `EWP_SEMANTIC_MODEL` for the whole window and record it.

---

## 3. Generate shadow telemetry

The shadow probe fires from the async evaluator pass (`evaluation_worker.run_worker_pass`) after **every** processed evaluation job while the flag is `shadow` — for **all** exercise types, not just source-dependent ones (see the ⚠️ warning above). To accumulate the *evidence you care about* (correction / grammar / vocabulary) without incidentally sending unrelated `sentence_construction` traffic to the provider, **isolate the workload** rather than flipping the flag on general live traffic:
1. Run the eval worker/scheduler with the §2 env on an **isolated instance / environment** that only processes a controlled job set (it is single-instance: `max_instances=1`, `coalesce=True`). Do NOT enable the flag on a worker draining live `sentence_construction` traffic unless you accept those submissions hitting the provider (cost + answer text sent out).
2. Feed it correction / grammar / vocabulary **learning-mode** submissions (these types can be imported+verified for authoring even though they are not learner-activatable — see the prompt-bank runbook), or a curated **replay set** of source-dependent jobs.
3. Each processed job appends one row to `writing_language_evaluator_runs`; filter to the source-dependent types when computing the §5.2 gates (`WHERE exercise_type IN ('sentence_correction','vocabulary_in_context', …)`). Any `sentence_construction` rows that appear are incidental and are excluded from the evidence set.

Inspect accumulation:
```sql
-- rows per exercise type + status (service-role connection)
SELECT exercise_type, status, count(*)
FROM public.writing_language_evaluator_runs
GROUP BY 1,2 ORDER BY 1,2;
```

---

## 4. §5.2 promotion gates (evidence-gated, NOT time-gated)

Measured over **≥ 500 human-labelled answers per affected type** (correction, grammar, vocabulary independently), on the then-current default model. Source: `docs/architecture/ewp-semantic-evaluator-adapter.md` §5.2.

| Gate | Metric | Exit criterion |
|---|---|---|
| G5-a | False-positive rate (adapter flags an issue a human rejects) | ≤ **5%** per type |
| G5-b | False-negative rate (adapter misses a human-confirmed `must_fix`) | ≤ **10%** per type |
| G5-c | Source-mismatch precision (correction only) | ≥ **90%** agreement |
| G5-d | p95 adapter latency (outside DB txn) | ≤ **8 s** |
| G5-e | Cost ceiling | ≤ **US$0.02** per evaluated unit |
| G5-f | Minimum sample size | ≥ **500** labelled answers **per** type |
| G5-g | Determinism-authority regression | **0** cases where the adapter cleared a deterministic `must_fix` or turned a deterministic fail into a pass — **hard block** |
| G5-h | Operator approval | recorded in the checklist with evidence linked |

Latency (G5-d), cost (G5-e), token counts, and confidence come straight from `writing_language_evaluator_runs`. FP/FN/source-mismatch (G5-a/b/c) require a **human-labelled benchmark** compared against the recorded adapter verdicts (join telemetry to labels by `input_hash`). G5-g is proven from telemetry: no shadow run may correspond to a deterministic `must_fix` being cleared.

**Any gate failing keeps the flag at `shadow`.** Promotion is **per exercise type** — one type may reach LIVE while others stay in SHADOW. G5-g failing means the augment-never-replace boundary leaked and must be fixed in code first.

---

## 5. Record + checklist

- Write a dated evidence report under `docs/audits/` with, per exercise type: sample size, FP/FN, source-mismatch precision, p95 latency, per-unit cost, determinism-regression count (must be 0), and the pinned model id.
- Update the `EWP-SP1b` checklist row from `VALIDATION PENDING` with the captured window; keep LIVE marked **BLOCKED** until every G5 gate passes for a type **and** operator approval (G5-h) is recorded.
- Do **not** flip `FF_WRITING_LLM_EVAL=live` from this runbook — live promotion is a separate, gated decision with the evidence attached.

### Quick reference
| Env | Effect |
|---|---|
| `FF_WRITING_LLM_EVAL=off` (default) | adapter never constructed; deterministic mock only |
| `FF_WRITING_LLM_EVAL=shadow` | adapter runs for **every** processed job (all exercise types), telemetry recorded, **zero learner-facing / authority effect** — but answer text for all types is sent to the provider (see §6) |
| `FF_WRITING_LLM_EVAL=live` | returns `None` from the shadow seam — LIVE is blocked by design |
| `ANTHROPIC_API_KEY` | provider key (env/secret only) |
| `EWP_SEMANTIC_MODEL` | pin the benchmark model for the window (swap resets evidence) |

---

## 6. Recommended code follow-up (optional, separate PR)

The shadow probe is currently **flag-wide** (no exercise-type gate — verified in `evaluation_worker._run_semantic_shadow_probe` / `semantic_evaluator.SemanticLanguageEvaluator.evaluate`). If the team wants to run shadow directly on general live traffic **without** sending `sentence_construction` (and other non-source-dependent) answers to the provider, gate the probe in code — e.g. skip `_run_semantic_shadow_probe` (or short-circuit `evaluate()` to a `status='skipped'` telemetry row with no provider call) when `_is_source_dependent(exercise_type)` is false. That is a code change with behaviour tests, out of scope for this docs PR; until it lands, use the isolation approach in §3.
