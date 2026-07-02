# I9 deferred items — v1-vs-v2 recommendation (F2)

**Status:** RECOMMENDATION — requires product/operator sign-off. Nothing here changes the
authoritative `docs/status/career-copilot-checklist.md` until accepted; on acceptance, update
the "I9 implementation" row and (for D12) open the v1 fix.
**Author input:** decision records `Exam-Cycle-Setup-D06-D08 / D11 / D12-D16-*`, current code
in `app/backend/app/exam_intelligence/cycle_readiness.py` + `work_queue.py` + the
`CycleActivationChecklist.jsx` renderer.
**Scope:** provides the **decision artifact required to close gate F2** by classifying the five
I9 deferred items (D06, D11, D12, D14, D15) as **v1 (must-fix before GA)** or **v2 (explicitly
deferred)**. **F2 remains OPEN** until product/operator sign-off **and** checklist reconciliation
in `career-copilot-checklist.md`; this document does not itself close the gate.

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

| Item | What's deferred | Risk | **Recommendation** |
|------|-----------------|------|--------------------|
| **D12** | Step 9 `review_activate` verdict is exam-wide + mode-blind | **fail-OPEN** | **v1 — must-fix** |
| D06 | extraction `metrics` + `other_documents_unresolved` advisory not emitted | non-gating (under-reports; never over-blocks) | **v2 — defer** |
| D11 | reviewed/locked collapsed to `ready` (no `locked`); no `partial` for core pending; no draft/pending counts | fail-closed (understates trust / over-blocks) | **v2 — defer** |
| D14 | applicability derived from `gate_class`, not the explicit per-mode matrix | cosmetic (non-gating; field not rendered) | **v2 — defer** |
| D15 | **existing** vocab violation (`no_phases_in_cycle` unapproved) + no runtime validation | non-gating (not rendered) | **v2 — defer** |

**Net: 1 v1 item (D12), 4 v2 deferrals.** F2 closes once this split is accepted and the D12
fix is scheduled as v1 work.

> **Update (D12 v1 IN PROGRESS — operator scope decision required):** PR #841 (cross-cycle
> fail-open) is merged. PR #843 adds migration **210** (`exam_phases.phase_kind` D05 §1 +
> `exam_cycles.planner_activation_enabled`) and wires Step 9 to gate required-phase completeness
> on canonical phase **classification** and `light` applicability on the exposure flag. Review of
> #843 flagged **two contract blockers that block calling D12 v1 delivered**:
> 1. **Completeness ≠ classification.** D05/D12 define "required phases complete" as satisfying the
>    full D05 evidence policy (phase-kind-specific evidence + independent predicates), not
>    classification alone; classification-only is still a false-ready path. But D05 §2–5 (the
>    evidence-policy engine) is, by D05's own boundary, gated on **D06 and D08** — which this very
>    document defers to **v2**. So genuinely completing D12 v1's completeness half requires either
>    pulling D06/D08 into v1, or an operator-approved amendment narrowing D12 v1 completeness to
>    canonical classification.
> 2. **Exposure authority not canonical.** `study_os/planner.py::_compute_plan()` does not consume
>    `planner_activation_enabled`, so readiness could mark `light` N/A while the planner still runs.
>    Readiness + planner must share the authority (land planner enforcement + backfill together), or
>    `light` applicability stays fail-closed/open.
>
> **Pending operator decision** (see PR #843): (A) authorize the classification-level D12 v1
> boundary + shared-authority plan via a decision-record amendment; (B) expand v1 scope to the full
> D05 evidence engine + D06/D08 + planner enforcement; or (C) keep D12 partial and fail-closed,
> landing migration 210 columns as forward scaffolding only.

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

**Fix (v1 scope — evaluate prerequisites directly, per D12 L75):** Step 9 must stop consuming
the exam-wide `classify_exam` verdict and instead check the **selected cycle**:
(a) selected-cycle details complete (Step 1); (b) **required phases COMPLETE under D05/D14** —
test completeness, not merely "≥1 phase row" / the current minimal Step 2 check; (c) ≥1 locked
coverage row *applicable to the selected cycle under the D08 scope/inheritance contract*.
Mode-awareness is more than `index_only`/`archive` → N/A: **`light` is conditional on
Study-OS/planner-activation-enabled** — the fix must identify the **canonical source** for
"planner activation enabled" rather than assume always-applicable. Regression tests:
"Cycle A no coverage + Cycle B locked → Step 9 NOT ready"; `light` with planner disabled;
phases present-but-incomplete → NOT ready.
*Touches `cycle_readiness.py`/`work_queue.py`/`management_read_model.py`, which the I9 owner is
actively editing — schedule with that owner to avoid collision.*

---

## D06 — **v2 defer** (fail-closed)

**Mandate** (`D06-D08` record): one-success extraction threshold; the ready step must expose
`metrics` (total/succeeded/extracting/review_pending/failed/not_started) and an
`other_documents_unresolved` advisory; **blockers stay empty**.

**Current behavior:** the one-success threshold and the mixed-state precedence
(`review_pending > extracting > uploaded > missing`) are **implemented correctly**
(`cycle_readiness.py` ~L401–428). What's missing is only the populated `metrics` and the
`advisories` array (`_step()` doesn't emit `advisories`; `metrics` defaults to `{}`).

**Risk:** **non-gating observability gap** — precise wording: the missing `metrics` +
`other_documents_unresolved` advisory **under-report** unresolved work; they do **not** over-block,
and the one-success readiness result stays contractually correct. No path to a false-ready
selected cycle; operators can inspect the Documents tab. → **v2.**

---

## D11 — **v2 defer** (fail-closed)

**Mandate** (`D11` record): competition readiness is **selected-cycle scoped** and mode-aware
(`light`/`index_only`/`archive` → `not_applicable` when the selected cycle has no reviewed/locked
row); preserve draft/pending counts for operator visibility.

**Current behavior:** Step 8 is correctly cycle-scoped (`exam_cycle_id == cycle_id`) and returns
`not_applicable` for optional modes — so it **cannot** fall back to another cycle. But it has
**three** gaps vs the D11 contract (reviewed→`ready`, locked→`locked`, core pending-only→`partial`):
1. **No locked-vs-reviewed distinction** — it groups `reviewer_status in ('reviewed','locked')`
   and always emits `ready` (`cycle_readiness.py` ~L602–607); the `locked` state is never surfaced.
2. **No `partial` state** — core with draft/pending-only evidence emits `missing` (~L618), not the
   contractual `partial`.
3. **No draft/pending metrics** for operator visibility.

**Risk:** fail-closed — each gap **understates trust** (`ready` shown where `locked` is due) or
**over-blocks** (`missing` where `partial` is due); none can produce a false-ready. Scope is
respected. → **v2.** (The *exam-wide Step 9* leak that surfaced here is the **D12** item, not
D11's competition scope.)

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

**Current behavior:** no schema/runtime enforcement (`_na_step()` accepts `None` or any string,
`cycle_readiness.py` L53/L80–93). This is an **existing violation, not just a future risk**:
runtime emits **`no_phases_in_cycle`** (L318), which is **not** in the approved D15 vocabulary
(`optional_for_management_mode`, `planner_activation_disabled`, `archive_reference_only`,
`unsupported_exam_type`, `no_selected_cycle`). Tests asserting `no_phases_in_cycle` do **not**
amend the decision record.

**Risk:** non-gating. The reason field never gates activation and is not rendered in
`CycleActivationChecklist.jsx`, so the out-of-vocabulary code has no user-facing or gating
effect today. → **v2** (add the enum validation + reconcile `no_phases_in_cycle` — either
approve it into the vocabulary or replace it).

---

## What closing F2 requires (next steps)

1. **Product/operator sign-off** on this split (D12 → v1; D06/D11/D14/D15 → v2).
2. On acceptance, update the **`career-copilot-checklist.md`** "I9 implementation" row: mark
   D06/D11/D14/D15 **v2-deferred** (not "pending remediation"), and record **D12 as a v1
   must-fix** work item.
3. Schedule the **D12 Step-9 selected-cycle reconciliation** fix with the I9 owner (small,
   testable; regression: Cycle-A-empty + Cycle-B-locked must NOT yield Step 9 ready).
4. F2 is then frozen: v1 scope = D12 fix; v2 scope = the other four.
