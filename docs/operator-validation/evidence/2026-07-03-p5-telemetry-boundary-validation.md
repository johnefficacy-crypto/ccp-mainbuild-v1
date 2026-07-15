# Operator validation evidence — P5 telemetry and fingerprint boundary

## Record

| Field | Value |
|---|---|
| Gate ID | `v1-p5-telemetry-boundary` |
| Result | `passed` |
| Environment | staging |
| Approved source SHA | `6171027a42fce011ea295cf9e07609bf3f25ac3a` |
| Freeze-candidate digest | `51cd69281302813d6254673ec6829deaeb8c24e2ece96d117035d5a71ffe74f4` |
| Recorded at | 2026-07-03 |
| Canonical repository record | PR #864 and `docs/ops/mastery_validation_fingerprint_manifest_v2*` |

Repository cross-check: PR #827 is the P6 scheduler-drain operator-pass record. P5 completion and boundary approval are recorded by PR #864.

## Validation result

| Check | Result | Evidence summary |
|---|---|---|
| 3A backend-origin authenticated delivery | PASS | Authenticated `question.visited` telemetry reached the configured backend with HTTP 200. |
| 3B retain and resend after HTTP 500 | PASS | The event batch was retained after the forced failure, resent successfully, and the durable queue emptied only after acknowledgement. |
| 3C partial-coverage analytics | PASS | Persisted analytics recorded fallback and event coverage (`fallback_question_count=12`, `events_used=5`, `event_covered_questions=3`, `events_malformed=0`). |
| 36-file boundary | PASS | Operator explicitly approved the boundary and the canonical Git-blob attestation. |

## Defects found and fixed

| ID | Defect | Fix |
|---|---|---|
| `v1-p5-01` | Visibility/unmount batches could be dropped because `sendBeacon` could not send auth and removal occurred before acknowledgement. | PR #800 added authenticated keepalive delivery, retain-on-failure, retry, and acknowledgement-based removal. |
| `v1-p5-02` | Partial event coverage fallback could occur without a warning/count. | PR #800 added coverage counters and persisted partial-fallback reporting. |

## Disposition

**PASSED.** P5 is closed. The later T0 process must still create a fresh fingerprint attestation for the selected final release SHA; that is not a reopening of P5.
