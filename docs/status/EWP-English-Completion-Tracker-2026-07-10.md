# English Writing Practice — Completion Tracker

**Created:** 2026-07-10 · **Owner:** Study OS / EWP
**Verified against:** `main` post-#937 (Subject Practice Hub merged)
**Related contracts:**
`docs/architecture/english-writing-practice.md` (EWP runtime),
`docs/architecture/ewp-semantic-evaluator-adapter.md` (semantic evaluator, PROPOSAL),
`docs/status/career-copilot-checklist.md` (Lane H rows).

This tracker records the remaining work to finish the English writing template
after the Subject Practice Hub (`/app/study/subjects`) shipped. The hub can
launch English `sentence_construction` practice, but four gaps remain. They
collapse onto **two root gates + one standalone slice**.

## Status vocabulary
`MERGED` · `CODE-FIXED, VALIDATION PENDING` · `PLANNED` · `BLOCKED` · `OPERATOR PENDING`

---

## 1. Confirmed gaps (verified in code)

| # | Gap | Confirmed evidence | Root blocker |
|---|---|---|---|
| 1 | Only `sentence_construction` runtime-ready | `cms_writing_runtime_ready_types()` = `['sentence_construction']` (`226_ewp_prompt_activation_lifecycle.sql:70`); source-dependent/paragraph types gated | Semantic-evaluator gate (Track B) |
| 2 | English exam mode unavailable | `create_session` 400s on `mode!=learning` (`app/backend/app/api/writing_practice.py:327`); RPC raises `ewp_mode_unsupported` (`222:122`, `207:316`) | Standalone runtime slice (Track A) |
| 3 | Error Lab grammar drills "coming soon" | `ErrorReview.jsx:110` `grammar-lab-stub` is a hard-disabled button | Downstream of gap 1 (Track B) |
| 4 | Writing mastery shadow-only | `LANE_A_LIVE_UNBLOCKED=False` forces every `live`→`shadow` (`mastery_flag.py:20`) | Lane A mastery gate + missing aggregator (Track C) |

Key correctness notes found during the audit:
- The semantic evaluator adapter exists but is **shadow-only and not wired into
  the authoritative path**: `get_language_evaluator()` returns the *Mock* even in
  `live` (`language_evaluator.py:461`). Flipping the gate is necessary but **not
  sufficient** — this selection must also change.
- The **unified mastery aggregator does not exist in code**. No Python process
  reads `user_topic_mastery_evidence` → writes `user_topic_mastery`; only a
  read-only fold view exists. Live writing mastery cannot publish anywhere yet.
- The mock mastery live gate (`FF_MOCK_MASTERY_WRITES=live`) is **BLOCKED** and its
  P8 shadow window was **terminated by the owner (2026-07-08)** — a fresh T0 + P9
  canary must still run (checklist line 20).

---

## 2. Tracks & dependency graph

```
Track A  Exam mode          — standalone, all code, actionable now
Track B  Semantic eval → runtime-ready types → Error Lab drills — chained; gated on measurement + sign-off
Track C  Writing mastery live — furthest; needs new aggregator subsystem + Lane A gate + operator windows
```

Only **Track A** (and Track B's Error Lab *plumbing*) is unblocked today.

---

## 3. Track A — English exam mode  `PLANNED → IN PROGRESS`

Schema already supports exam mode (`status='submitted'`, `submitted_at`,
`feedback_released_at`, `submission_kind='blank'`, `_feedback_released()`),
so this is runtime wiring, not schema design.

### Deliverables
- [ ] **A1 — Session-submit RPC** `ewp_submit_writing_session(p_user, p_session, p_unit_results)`: canonical lock order (session → all units ascending, §8.0); create blank versions for `not_started`/empty units with **`answer_text=''`, `submission_kind='blank'`, `content_hash = SHA-256('') = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`** (never empty/null — an empty/null hash violates the immutable version + version-set-hash contract); drafted units → `evaluation_pending`; session `active → submitted` + stamp `submitted_at`; compute `feedback_released_at` from the copied policy; enqueue language-eval jobs. New migration (number = live `max(version)+1`; 239 on main → **240**, VERIFY DB). `CREATE OR REPLACE` only.
- [ ] **A2 — `feedback_released_at` writer**: set at submit for `immediate`/`on_submit`/`scheduled_after_submit`; set by the finalizer for `on_evaluation_terminal`.
- [ ] **A2b — Mode-aware finalizer (BACKEND invariant, not a frontend guard)**: exam-mode rollup MUST NOT produce unit or session `rewrite_required` (§4.4b). Today's authoritative rollup (`238_ewp_rollup_completed_at.sql::ewp_apply_session_rollup`) is learning-shaped — it writes `rewrite_required` when terminal units fail coverage or carry unresolved `must_fix`. For `mode='exam'` that remediation/rewrite path must be bypassed: terminal deterministic/language findings stay reportable behind the feedback-release policy, but the session flows `active → submitted → evaluation_pending → completed` and never reopens. `CREATE OR REPLACE` the finalizer; learning-mode behavior unchanged. (This lives in A1/A2/A4's SQL layer — NOT A5.)
- [ ] **A3 — Submit endpoint** `POST /api/study/practice/english/sessions/{id}/submit` (exam-only): batch per-unit Stage-1 deterministic eval in Python (mirrors `submit_unit`), pass results + blanks into A1.
- [ ] **A4 — Lift guards**: API `writing_practice.py:327`; RPC mode guards (`222:122`, `207:316`); generalize `_create_learning_session` to stop hardcoding `p_mode`/`p_policy`.
- [ ] **A5 — Frontend exam behavior**: lock inputs after submit; session-submit control; feedback hidden until `feedback_released_at` (+ scheduled-release countdown). The `rewrite_required` bypass is enforced in the backend (A2b) — the UI just renders the exam terminal-feedback + completion states; it does not "hide" a rewrite state the RPC could still emit.
- [ ] **A6 — Tests + verify + checklist row**. Must include: blank-version SHA-256('') digest; per-policy `feedback_released_at`; idempotent re-submit; append-only enforcement; and an assertion that **the RPC/API can never return `rewrite_required` for an exam session** (A2b).

### Frozen contract (coordination artifact)
```
POST /sessions                       body adds mode:"exam"  (guard lifted)
POST /sessions/{id}/submit           → session payload {status:"submitted", feedback_released}
RPC  ewp_submit_writing_session(p_user, p_session, p_unit_results jsonb)
     p_unit_results[]: {unit_number, answer_text|null, server_wc, content_hash, det_result, det_version}
States: active → submitted → (rollup) evaluation_pending → completed ; feedback gated by feedback_released_at
```
Learning mode is untouched (exam is purely additive). Governing contracts to honor: §9 exam runtime, §8.0 lock order, §4.5 blank-version immutability, §4.3 feedback policy.

### Parallelization (lanes)
```
Lane 0  DB migration + RPCs + SQL regression   ── SERIAL, foundation, blocks all
              │
        ┌─────┴─────┐
     Lane 1 API   Lane 2 Frontend               ── PARALLEL after contract freeze (disjoint files)
        └─────┬─────┘
        Lane 3 integration/verify + checklist + PR   ── SERIAL
```
- **Lane 0 is not fannable.** It carries append-only immutability triggers, the deadlock-free lock order, and the single session-birth path — one owner, one session, sequential (the serial-delivery rule for EWP RPCs). No two agents touch its migration/RPC file.
- **Lanes 1 & 2 fan out only after the contract freezes.** They touch disjoint files (backend `api/writing_practice.py` + service vs. frontend `EnglishPracticeShell`) → no worktree isolation needed. Each lane owner writes its own tests (no separate test-writer agent — avoids contract drift).
- **Cross-session option**: Session-0 lands/shares the branch first; Sessions 1 & 2 branch off the frozen contract; a coordinating loop holds this doc.

---

## 4. Track B — Runtime-ready expansion + Error Lab drills  `BLOCKED (gate) / plumbing PLANNED`

1. [ ] **Measurement/sign-off (operator)** — run the semantic evaluator in shadow; capture adapter doc §5.2 acceptance evidence (FP ≤5%, FN ≤10%, source-mismatch precision ≥90%, p95 ≤8s, cost ≤$0.02, ≥500 labeled samples **per type**, 0 determinism regressions) + operator sign-off in the checklist.
2. [ ] **Code (after 1)** — migration to open `cms_writing_gate_open('semantic_evaluator')` **and** add source-dependent types to the runtime-ready allowlist (they still fail `exercise_type_not_runtime_ready` otherwise); set `FF_WRITING_LLM_EVAL=live` **and** fix `get_language_evaluator()` to return the semantic adapter in live with fail-closed semantics.
3. [ ] **Content** — author + verify grammar prompts per English microtopic.
4. [ ] **Error Lab plumbing** — backend: add English `subject_id` to the `error-lab` payload per group; frontend: replace `ErrorReview.jsx:110` `grammar-lab-stub` with a launcher that POSTs `/api/study/subjects/{subject_id}/practice/start` and navigates (409 → graceful "no verified drill yet"). **Resolver gap (correction, per checkpost #950):** Error Lab groups are keyed by `microtopic_id` (a `topics.id` at `level='microtopic'`), but `resolve_launch_prompt_id` / `_verified_active_prompts` currently filter **`writing_prompts.topic_id` only — they do NOT select or filter `microtopic_id`**. Passing a microtopic id as `topic_id` will 409 (unless a prompt wrongly stored the microtopic in `topic_id`). So this step is **not** "already supported": it requires a decision + one of — (a) add a `microtopic_id` launch parameter and a resolver branch filtering `writing_prompts.microtopic_id`, or (b) resolve microtopic → parent `topic_id` and launch by topic — plus deciding whether drills target the exact microtopic or the parent topic. Even after wiring, it 409s until Track B steps 2–3 (gate open + authored verified grammar prompts) land.

---

## 5. Track C — Writing mastery live  `BLOCKED`

1. [ ] **Mock mastery live proven stable (operator/time)** — fresh P8 14-day shadow window (re-T0 after owner termination) + P9 canary + live migrations.
2. [ ] **Build the unified mastery aggregator (large code — missing entirely)** — the single writer consuming `user_topic_mastery_evidence` → `user_topic_mastery` (locked rule 19: never write `user_topic_mastery` directly).
3. [ ] **Live aggregator-publish branch** in `mastery_outbox_worker.py` (today an explicit no-op stub, lines 11-12) + flip `LANE_A_LIVE_UNBLOCKED` + enabling migration.
4. [ ] **Writing shadow window (T0) + §10.3 promotion gates + operator sign-off** — no writing T0 started yet.
5. [ ] **Deferred**: transactional writing-task generator (planner personalization off live mastery).

Shadow evidence production (deriver, outbox drain, shadow table, fold view, flag resolver) is already built and shadow-only.

---

## 6. Sequencing recommendation

1. **Track A now** — fully unblocked; one cohesive PR via the lane plan above.
2. **Track B step 4 (Error Lab plumbing)** — safe to land alongside; degrades gracefully until the gate + prompts exist.
3. **Track B steps 1–3 and all of Track C** — governance/measurement-gated; do not start without owner direction.
4. **Cleanup** — reconcile the checklist P8 inconsistency (line 20 says P8 ended; P8/T0 rows still read "IN PROGRESS").

---

## Change log
- 2026-07-10 — Tracker created; Track A moved to IN PROGRESS (Lane 0 foundation starting).
- 2026-07-10 — Checkpost #950 corrections: (A1) blank-version hash stated as explicit `SHA-256('')` digest, not "empty"; (A2b) added mode-aware finalizer as a BACKEND invariant so exam mode never rolls into `rewrite_required` (moved out of frontend A5); (Track B step 4) corrected — the current resolver filters `topic_id` only, so microtopic-targeted Error Lab launches need a new `microtopic_id` branch or microtopic→topic resolution, not "already supported".
