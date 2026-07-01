# I9 deferred items — v1-vs-v2 recommendation (F2)

**Status:** RECOMMENDATION — requires product/operator sign-off. Nothing here changes the
authoritative `docs/status/career-copilot-checklist.md` until accepted; on acceptance, update
the "I9 implementation" row and (for D12) open the v1 fix.
**Author input:** decision records `Exam-Cycle-Setup-D06-D08 / D11 / D12-D16-*`, current code
in `app/backend/app/exam_intelligence/cycle_readiness.py` + `work_queue.py` + the
`CycleActivationChecklist.jsx` renderer.
**Scope:** closes gate **F2** — freeze the five I9 deferred items (D06, D11, D12, D14, D15) as
either **v1 (must-fix before GA)** or **v2 (explicitly deferred)**.

---

## Decision rule (grounded in the repo's locked invariants)

From `CLAUDE.md`: **Trust > Speed**, **Determinism > Heuristics**, **verified-only reads**, and
entity/cycle canonicity (a selected cycle's readiness must not be satisfied by another cycle's
data). Applying those:

- **v1 (must-fix)** if the deferred behavior is **fail-OPEN** — it can mark a cycle/exam
  READY/activatable when the *selected cycle* is not actually ready, i.e. it can surface an
  under-verified activation signal. This violates Trust-over-Speed and cycle canonicity.
- **v2 (defer)** if the behavior is **fail-CLOSED** — it only over-blocks, or is a
  label/observability/validation-hardening gap with no path to a false-ready signal. Annoying
  to operators, safe for aspirants; consistent with Trust-over-Speed.

The `cycle_readiness.steps[]` array is an operator checklist; it does not itself unlock content
for aspirants today. So "blast radius" is scored on **whether a human or future automation can
be led to activate an under-verified selected cycle**, not on immediate aspirant exposure.

---

## Recommendation summary

| Item | What's deferred | Fail direction | **Recommendation** |
|------|-----------------|----------------|--------------------|
| **D12** | Step 9 `review_activate` verdict is exam-wide + mode-blind | **fail-OPEN** | **v1 — must-fix** |
| D06 | extraction `metrics` + `other_documents_unresolved` advisory not emitted | fail-closed | **v2 — defer** |
| D11 | competition step missing draft/pending lifecycle counts | fail-closed | **v2 — defer** |
| D14 | applicability derived from `gate_class`, not the explicit per-mode matrix | fail-closed | **v2 — defer** |
| D15 | no runtime validation of the `not_applicable_reason` vocabulary | fail-closed | **v2 — defer** |

**Net: 1 v1 item (D12), 4 v2 deferrals.** F2 closes once this split is accepted and the D12
fix is scheduled as v1 work.

---

## D12 — **v1 must-fix** (the only fail-open item)

**Mandate** (`D12-D16` record): the Review-&-Activate minimum is **selected-cycle aware** —
"selected cycle details complete AND required phases complete AND at least one *applicable*
locked topic-coverage row exists", evaluated per management mode, and the step "must evaluate
its prerequisite inputs directly" (no binding to a pre-computed exam-wide verdict).

**Current behavior:** Step 9 (`cycle_readiness.py` ~L641–651) binds directly to
`activation_verdict` from `work_queue.classify_exam(aggregate(sb, [exam]))`
(`management_read_model.py` ~L247), which is **exam-wide and cycle-blind** — its
`locked_coverage_count` sums coverage across *all* cycles (`work_queue.py` ~L216–225, L294).

**Fail-open scenario (concrete):** selected Cycle A has 0 locked coverage rows; Cycle B has 1.
- Step 5 (`syllabus_mapping`, cycle-scoped) → **missing**.
- Step 9 (exam-wide verdict) → **ready** (Cycle B's locked row satisfies `classify_exam`).
- Result: **Step 9 says "ready" while its own prerequisite Step 5 says "missing"** — Cycle B's
  verification leaks into Cycle A's activation signal. That is a verified-content / cycle-canonicity
  violation (Trust > Speed).

**Why v1:** it is the one item that can produce a *false-ready activation signal for the wrong
cycle*. Even though Step 9 is advisory today, a bulk/scripted activation — or a future
`activate()`/planner path that trusts the verdict — would propagate Cycle B's coverage into
Cycle A. Shipping a fail-open activation gate contradicts the locked invariants.

**Fix (v1 scope, small + testable):** make Step 9 reconcile to the **selected cycle** —
evaluate its prerequisites directly per D12: (a) selected-cycle details complete (Step 1),
(b) required phases present, (c) ≥1 locked coverage row *applicable to the selected cycle under
the D08 scope/inheritance contract* — instead of trusting the exam-wide `classify_exam` status.
Keep the existing mode gating (`index_only`/`archive` → N/A). Add regression tests:
"Cycle A no coverage + Cycle B locked → Step 9 NOT ready", and the mode-aware variants.
*This touches `cycle_readiness.py`/`work_queue.py`, which the I9 owner is actively editing —
schedule it with that owner or as a scoped follow-up to avoid collision.*

---

## D06 — **v2 defer** (fail-closed)

**Mandate** (`D06-D08` record): one-success extraction threshold; the ready step must expose
`metrics` (total/succeeded/extracting/review_pending/failed/not_started) and an
`other_documents_unresolved` advisory; **blockers stay empty**.

**Current behavior:** the one-success threshold and the mixed-state precedence
(`review_pending > extracting > uploaded > missing`) are **implemented correctly**
(`cycle_readiness.py` ~L401–428). What's missing is only the populated `metrics` and the
`advisories` array (`_step()` doesn't emit `advisories`; `metrics` defaults to `{}`).

**Fail direction:** fail-closed. Ready/not-ready is correct; extraction is `advisory` gate_class
so it can't independently block; unresolved docs are simply not surfaced in-payload. Operators
lose an at-a-glance count + a stable advisory code, but can inspect the Documents tab. No path
to a false-ready selected cycle. → **v2.**

---

## D11 — **v2 defer** (fail-closed)

**Mandate** (`D11` record): competition readiness is **selected-cycle scoped** and mode-aware
(`light`/`index_only`/`archive` → `not_applicable` when the selected cycle has no reviewed/locked
row); preserve draft/pending counts for operator visibility.

**Current behavior:** Step 8 is correctly cycle-scoped (`exam_cycle_id == cycle_id`,
`reviewer_status in ('reviewed','locked')`) and returns `not_applicable` for optional modes
(`cycle_readiness.py` ~L596–614) — so it **cannot** fall back to another cycle. The only gap is
the missing draft/pending lifecycle **counts** in the step's metrics.

**Fail direction:** fail-closed (the N/A path prevents a false-ready; scope is respected). Pure
operator-visibility gap. → **v2.** (Note: the *exam-wide Step 9* concern that surfaced while
reviewing D11 is the **D12** item above, not D11's own competition scope.)

---

## D14 — **v2 defer** (fail-closed)

**Mandate** (`D12-D16` record, "D14"): every step exposes `required | conditional |
not_applicable`, **independent of status/weight**, from an explicit per-step × per-mode matrix.

**Current behavior:** `_step()` approximates it from `gate_class` (`hard→required`,
`advisory→conditional`), so several steps are mislabeled (e.g. `extraction` for `core` should be
`required` but shows `conditional`).

**Fail direction:** fail-closed / cosmetic. The `status` field stays truthful, `classify_exam`
gates activation **independently of `applicability`**, and the frontend
(`CycleActivationChecklist.jsx`) **does not even render `applicability`**. No activation effect.
→ **v2** (implement the explicit 9×4 matrix then). This is the item the checklist already labels
"KNOWN NONCOMPLIANCE" — keep that label; it is honest and safe.

---

## D15 — **v2 defer** (fail-closed)

**Mandate** (`D12-D16` record, "D15"): backend must reject `not_applicable` without an approved
reason code; non-N/A serializes `null`; frontend falls back safely on unknown codes; tests
assert codes.

**Current behavior:** no schema/runtime enforcement — relies on developer discipline. But **all
current N/A emissions use approved codes** (`optional_for_management_mode`, `no_selected_cycle`,
`no_phases_in_cycle`) and the tests assert exact codes, so a stray code would fail CI.

**Fail direction:** fail-closed. The reason is informational, not rendered today, and never
gates activation. The risk is a *future* unapproved code, already backstopped by tests. → **v2**
(add the Pydantic/enum validation then).

---

## What closing F2 requires (next steps)

1. **Product/operator sign-off** on this split (D12 → v1; D06/D11/D14/D15 → v2).
2. On acceptance, update the **`career-copilot-checklist.md`** "I9 implementation" row: mark
   D06/D11/D14/D15 **v2-deferred** (not "pending remediation"), and record **D12 as a v1
   must-fix** work item.
3. Schedule the **D12 Step-9 selected-cycle reconciliation** fix with the I9 owner (small,
   testable; regression: Cycle-A-empty + Cycle-B-locked must NOT yield Step 9 ready).
4. F2 is then frozen: v1 scope = D12 fix; v2 scope = the other four.
