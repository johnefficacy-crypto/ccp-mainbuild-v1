# Mock Trust Model

## Decision

**Chosen: Option B — Trust-aware coexistence.** Both manual logs and platform
attempts are retained in `mock_tests`, differentiated by `source_type` and
`trust_level` columns. Option A (deprecating manual logging) was considered but
deferred for evaluation at the 12-month mark, when exam-template coverage is
expected to be broader.

### Why not Option A now?
Template coverage for major exam families is still incomplete (est. 6-month
roadmap to parity). Removing manual logging today would leave users with no way
to record self-study mocks for exams not yet in the template library. The
feature regression outweighs the architectural benefit at this stage.

### Scheduled re-evaluation
At the 12-month mark (or when template coverage crosses ~80% of active exam
slugs), revisit whether manual logging can be deprecated. The migration and
code paths introduced here make Option A a straightforward follow-on: gate
`create_mock` behind a feature flag, stop writing `manual_log` rows, and the
trust-weight machinery becomes irrelevant.

---

## Schema

Three columns added to `mock_tests` (migration 148):

| Column | Type | Values | Default |
|---|---|---|---|
| `source_type` | `text` | `manual_log`, `platform_attempt`, `imported_result` | `manual_log` |
| `trust_level` | `text` | `self_reported`, `platform_verified`, `admin_verified` | `self_reported` |
| `mock_attempt_id` | `uuid → mock_attempts.id` | FK, nullable | `null` |

Rows written by `mock_engine._emit_mock_tests_row` (platform submit path) get
`source_type='platform_attempt'` and `trust_level='platform_verified'`.

Rows written by `mocks.create_mock` (manual log path) get
`source_type='manual_log'` and `trust_level='self_reported'`.

### Backfill
Existing platform-attempt rows were identified by the presence of
`metadata->>'mock_attempt_id'` (written by the engine before this PR).
Migration 148 backfills them to `source_type='platform_attempt'` and
`trust_level='platform_verified'`.

### Transition period
`_emit_mock_tests_row` continues writing `metadata.mock_attempt_id` alongside
the new `mock_attempt_id` FK for 6 months so any consumers that relied on the
metadata path keep working. After that period, stop writing the metadata field.

---

## Trust weighting in mastery deltas

Manual self-reports receive **0.3× weight** relative to platform attempts.
Concretely: the same topic accuracy on a self-reported mock produces a mastery
delta ~3.33× smaller than the equivalent platform attempt.

```
TRUST_WEIGHT = {
    "platform_verified": 1.0,
    "admin_verified":    1.0,
    "self_reported":     0.3,
}
```

**Rationale.** A user who claims 70% accuracy on a Polity section may be
misremembering, rounding up, or counting differently. The platform knows the
exact correct/wrong count and question identity. The 0.3 factor was chosen to
keep manual logs as useful signals (better than nothing) while ensuring a
single self-reported session cannot dominate a topic's mastery trajectory.
Users who always self-report will see slower mastery growth than those who take
platform mocks — an intentional incentive toward the more trustworthy signal.

The weight is applied after the ±0.15 unit cap, so a self-reported mock's
maximum single-session delta is ±0.045 unit (±4.5 db), vs ±0.15 unit (±15 db)
for platform attempts.

---

## UI

- Every row in `Mocks.jsx` shows a trust badge (green "Platform Attempt" or
  gray "Self-Logged") next to the review-state pill.
- Self-reported mock detail views show a caveat banner: "Self-reported mock.
  Analytics are based on the score you entered. Mastery updates carry reduced
  weight."
- `CorrectionTaskCard` shows an origin badge ("Platform" / "Self-logged") so
  reviewers know whether the driving signal was verified.

---

## Correction task lineage

Platform-attempt correction tasks carry canonical UUIDs in their evidence:

```json
{
  "source_trust": "platform_verified",
  "source_attempt_id": "<uuid>",
  "canonical_topic_id": "<uuid>",
  "canonical_microtopic_id": "<uuid or null>"
}
```

Self-reported tasks carry `source_trust: "self_reported"` and
`canonical_topic_id: null` (the planner falls back to text matching).

---

## RLS

Unchanged. Users see only their own `mock_tests` rows regardless of
`source_type` or `trust_level`.

---

## Sign-off

Architecture decision documented 2026-05-27. Requires product/leadership
acknowledgement before PR5 shadow→live cutover. Evaluate Option A at the
12-month mark (approx. 2027-05).
