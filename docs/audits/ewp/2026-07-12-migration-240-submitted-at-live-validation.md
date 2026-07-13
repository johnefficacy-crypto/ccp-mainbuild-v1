# EWP Migration 240 — `submitted_at` live validation

**Date:** 2026-07-12 19:57:54 UTC  
**Environment:** live Supabase DB  
**Evidence name:** `migration_240_submitted_at_live_validation`

## Summary

Migration `240` is live-applied as `ewp_rollup_submitted_at`, and the live `ewp_private.ewp_apply_session_rollup(uuid)` function contains the `submitted_at` rollup write path.

The operator re-ran the rollup on a completed historical EWP session and confirmed that:

- `status` stayed `completed`.
- `evaluation_outcome` stayed `fully_evaluated`.
- `completed_at` stayed unchanged.
- `submitted_at` was populated by the live rollup.

This validates the migration-240 behavior end-to-end for the live DB. Remaining `submitted_at IS NULL` rows are historical rows from before the validation/backfill event; migration 240 is intentionally not retroactive.

## Migration state

```json
{
  "live_schema_max": 244,
  "migration_240_name": "ewp_rollup_submitted_at"
}
```

The live migration history had already advanced through migrations `241`–`244`; no renumber or re-apply was required for `240` because version `240` was already present as the EWP submitted-at migration.

## Function-body verification

The live function inspection returned:

```json
[
  {
    "proname": "ewp_apply_session_rollup",
    "has_submitted_at_logic": true,
    "writes_submitted_at": true,
    "still_writes_completed_at": true
  }
]
```

## Validation session

```json
{
  "validated_session_id": "3c90846c-20b6-43d4-8f97-bdf035f1f948",
  "user_id": "664d94c6-907d-482a-8a0b-95571712075f",
  "study_task_id": "05988024-f518-46c7-a625-318a031c923a",
  "prompt_id": "82961b19-8d4e-41a6-b677-b94433a4389c",
  "status": "completed",
  "evaluation_outcome": "fully_evaluated",
  "completed_at_before": "2026-07-10 15:07:27.428837+00",
  "completed_at_after": "2026-07-10 15:07:27.428837+00",
  "submitted_at_before": null,
  "submitted_at_after": "2026-07-12 19:55:04.454804+00"
}
```

## Pre-mutation safety checks

The selected session was safe to re-finalize:

```json
[
  {
    "unit_number": 1,
    "unit_status": "ready",
    "version_number": 1,
    "unit_version_submitted_at": "2026-07-10 15:07:10.562975+00",
    "overall_status": "completed",
    "deterministic_status": "completed",
    "language_status": "completed",
    "check_type": "required_word_coverage",
    "coverage_passed": true,
    "coverage_checked_at": "2026-07-10 15:07:10.866495+00"
  }
]
```

```json
[
  {
    "has_unresolved_must_fix": false
  }
]
```

## Aggregate state after validation

```json
[
  {
    "status": "completed",
    "total_sessions": 3,
    "with_submitted_at": 1,
    "missing_submitted_at": 2,
    "with_completed_at": 2
  }
]
```

Interpretation: one completed session now proves the live rollup write; the two remaining missing `submitted_at` values are pre-validation historical rows and are expected under the non-retroactive migration contract.

## Checklist status wording

Use this wording when updating the status checklist row:

> Migration 240 — LIVE VALIDATED. Live `schema_migrations` max = 244; version 240 is `ewp_rollup_submitted_at`. Validated at 2026-07-12 19:57:54 UTC on session `3c90846c-20b6-43d4-8f97-bdf035f1f948`. Re-running `ewp_private.ewp_apply_session_rollup` kept `status=completed`, `evaluation_outcome=fully_evaluated`, `completed_at` unchanged, and populated `submitted_at=2026-07-12 19:55:04 UTC`. Remaining null `submitted_at` rows are pre-validation historical rows; migration 240 is not retroactive.
