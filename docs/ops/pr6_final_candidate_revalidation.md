# PR6: Final Study OS Shadow Candidate Revalidation

**Type:** Operator validation  
**Prerequisite:** PRs 2–5 merged and deployed together on one fixed SHA;
  PR-4 (`attempt_derivation.py`) present for shadow-replay and correction-parity gates  
**Status:** Pending

## Purpose

Validate on one pinned deployment SHA that all system invariants hold before
starting the 14-day shadow observation window. This becomes the **baseline SHA**
for the shadow gate.

## Shadow Gate Tool

The shadow analysis tool (`tools/mastery_shadow_analysis/shadow_analysis.py`)
now implements truthful gate logic. Old thresholds (sign agreement ≥ 80%,
task overlap ≥ 60%) are **removed** — they relied on invalid comparators or
cross-population topic identity that is not available. The valid gates are:

- `shadow-replay`: exact_match_pct = 100.0, coverage_pct = 100.0, zero violations
- `correction-parity`: exact_parity_pct = 100.0 (min 10 decisions)

See docs/ops/pr7_shadow_gate_results.md for the full threshold table.

## Pre-conditions

- PRs 2 (source-based writer authority), 3 (real shadow analysis), 4 (correction
  preview), and 5 (correction uniqueness) are all deployed on the same SHA.
- PR-4 (`app/backend/app/study_os/attempt_derivation.py`) is present on the
  deployed SHA (required for shadow-replay and correction-parity subcommands).
- `FF_MOCK_MASTERY_WRITES=shadow` is active.
- At least one platform attempt has completed since the SHA deployed.

## Validation Checklist

### A. Source-based writer guard (PR2)

- [ ] `POST /api/study/mocks/<platform_mock_id>/review` with `topic_breakdowns`
      returns HTTP 409 with `error: platform_attempt_breakdowns_rejected`.
- [ ] Verify no `mock_topic_breakdowns` rows were written for that mock_id.
- [ ] `POST /api/study/mocks/<platform_mock_id>/review` without `topic_breakdowns`
      returns HTTP 200; `review_status` is updated.

### B. Correction-preview classification parity (PR4)

- [ ] `GET /api/admin/study-os/mocks/<platform_mock_id>/mastery-preview` returns
      200 with non-empty `correction_drafts`.
- [ ] Each `correction_drafts` entry has a `category` that is one of the five
      canonical categories: `concept_gap`, `memory_gap`, `careless`, `speed_issue`,
      `option_trap`.
- [ ] `classification_counts` keys match the `error_type` values in
      `mock_attempt_response_classification` for that attempt.

### C. Deterministic correction categories

- [ ] Call the preview endpoint twice for the same mock_id; verify the
      `correction_drafts` list is identical (same categories, titles, topic_ids).

### D. Null-selection behavior

- [ ] For an attempt with at least one unanswered question (no `selected_option_id`),
      the preview endpoint's `response_counts.null` is > 0.
- [ ] Unanswered questions do not appear in `mastery_deltas` (they are correction-only).

### E. Shadow idempotency

- [ ] Re-trigger shadow analysis for the same attempt (e.g., manual sweeper kick).
- [ ] `mock_mastery_shadow` row count for that `attempt_id` does not increase
      (unique index on `attempt_id, topic_id, flag_state` prevents duplicates).

### F. Shadow-replay gate (PR-5A tool)

- [ ] Run: `python tools/mastery_shadow_analysis/shadow_analysis.py --json shadow-replay --days 1`
- [ ] Exit code 0 (PASS or FAIL) or 3 (INSUFFICIENT_DATA if <20 attempts yet).
      Exit code 2 (PREREQUISITE_MISSING) means attempt_derivation.py is absent — fix first.
- [ ] Attach JSON output to this PR.

### G. Correction-parity gate (PR-5A tool)

- [ ] Run: `python tools/mastery_shadow_analysis/shadow_analysis.py --json correction-parity --days 1`
- [ ] Attach JSON output to this PR.

### H. Automatic scheduler drain (see PR1 checklist)

- [ ] Scheduler drain evidence captured per `docs/ops/pr1_scheduler_drain_verification.md`.

### I. No live-table mutation

- [ ] `user_topic_mastery` rows for the test users were **not** updated since the
      SHA deployed (shadow mode must not write live mastery).
- [ ] `user_topic_mastery_audit` has no rows with `reason='mock_submit'` since the
      SHA deployed.
- [ ] `study_tasks` has no new correction-task rows from the platform submit flow
      (corrections are live-only; shadow mode must not draft them into study_tasks).

### J. Compatibility-row parity

- [ ] `mock_tests` row exists for each validated platform attempt
      (`source_type='platform_attempt'`, `trust_level='platform_verified'`).
- [ ] `mock_mastery_shadow` row exists for each attempt with `flag_state='shadow'`.

## Evidence Location

| Artifact | Where to store |
|---|---|
| HTTP response screenshots / curl output | Attach to this PR |
| SQL query results | Attach to this PR |
| shadow-replay JSON output | Attach to this PR |
| correction-parity JSON output | Attach to this PR |
| Baseline SHA | Record below |

**Baseline SHA:** `______________________________`  
**Deployed at:** `______________________________`  
**Validated by:** `______________________________`  
**Date:** `______________________________`
