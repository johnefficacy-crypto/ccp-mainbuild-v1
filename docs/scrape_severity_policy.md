# Scrape-run severity policy

Defines how `run_scraping_pass` maps a finished run to a `scrape_runs.status`
value. This is the source of truth for Task 8 (`degraded` +
`completed_with_warnings`). Written before the runner change per the
pre-flight contract.

## Column type

`scrape_runs.status` is a plain `text` column (migration 002), default
`'running'`, with **no** enum type and **no** `CHECK` constraint. Adding new
status values therefore needs **no migration** — `text` accepts them.

## Status values

| Status | Meaning |
|---|---|
| `running` | Set on row creation; replaced at finalize. |
| `completed` | Every source processed, no errors, no severity signals. |
| `completed_with_warnings` | No source errors, but soft severity signals tripped (degraded is a strict superset of these). |
| `partial` | At least one — but not every — source errored, and no degraded trigger fired. |
| `degraded` | A hard severity signal tripped (see thresholds), regardless of how many sources errored (short of all). |
| `failed` | Every source in the run errored (or a critical pre-loop read failed). |

## Run metrics

Collected per run and passed to the severity predicates:

| Metric | Incremented when |
|---|---|
| `anthropic_calls` | A non-mock `extract_recruitment_data` model call is issued. |
| `low_quality_count` | The low-confidence gate diverts an extraction to `low_quality_extractions`. |
| `source_auto_disabled_count` | A source hits the strike limit and is auto-disabled mid-run. |
| `source_registry_draft_failures` | A `source_drafts` insert raises (counted from its returned `failed` list). |
| `notification_document_failures` | A queue row is written with `notification_document_id IS NULL` on a non-mock run (evidence-document linkage lost). |
| `extractor_timeout_count` | The extractor catches an `anthropic.APITimeoutError`. |

`low_quality_ratio = low_quality_count / max(anthropic_calls, 1)` — the
`max(…, 1)` keeps a zero-call run from dividing by zero (ratio `0.0`).

## Thresholds

```text
triggers_degraded = (
    low_quality_ratio > 0.40
    or source_auto_disabled_count    > 0
    or source_registry_draft_failures > 0
    or notification_document_failures > 0
)

# Strict superset of triggers_degraded with softer thresholds.
any_warnings = (
    low_quality_ratio > 0.20
    or extractor_timeout_count > 0
)
```

Both ratio thresholds are strict `>` (a run sitting exactly at `0.20` or
`0.40` is on the safe side of the boundary). The boolean signals are `> 0`.

## Decision order (first match wins)

```text
if every_source_errored:        failed
elif triggers_degraded:         degraded
elif any_source_errored:        partial
elif any_warnings:              completed_with_warnings
else:                           completed
```

`degraded` is evaluated **before** `partial`: a hard severity signal
outranks a mere "some sources errored" outcome, so a run with one failing
source plus an auto-disable is reported `degraded`, not `partial`.

## Worked examples

| Scenario | low_quality_ratio | disables | draft fails | doc fails | errored sources | Status |
|---|---|---|---|---|---|---|
| Clean run | 0.00 | 0 | 0 | 0 | none | `completed` |
| 25% low-quality | 0.25 | 0 | 0 | 0 | none | `completed_with_warnings` |
| 45% low-quality | 0.45 | 0 | 0 | 0 | none | `degraded` |
| One source auto-disabled | any | 1 | 0 | 0 | none | `degraded` |
| One source_drafts 400 | any | 0 | 1 | 0 | none | `degraded` |
| Reference log run | 0.61 | 6 | 8 | n | some | `degraded` |
| All sources errored | n/a | n/a | n/a | n/a | all | `failed` |
