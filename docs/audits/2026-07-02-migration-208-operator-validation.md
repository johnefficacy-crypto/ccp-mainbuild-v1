# Migration 208 — Topic Prerequisite Lifecycle and Concurrency Validation Snapshot

**Project:** `ccp-mainbuild-v1`
**Validation date:** July 2, 2026
**Migration:** `208_topic_prerequisite_lifecycle.sql`
**Environment:** Linked Supabase PostgreSQL database
**Result:** **PARTIAL PASS — concurrency + lifecycle-state CAS proven on live PostgreSQL; PD-D planner-preservation evidence and the same-state `updated_at` guard NOT independently captured (see §5, §7, §18)**

> Operator VERIFY DB evidence for J2-A′ (gate `docs/status/Topic-Prerequisite-Semantics-Gate-2026-07-01.md`; implementation PR #835 `3e3d930`). This provides the live-PostgreSQL proof for migration 208's concurrency + lifecycle-state CAS behavior that unit tests cannot reproduce (the emulator advisory lock is a no-op). Two items remain not-independently-captured (PD-D pre/post planner preservation; same-state `updated_at` race) — see §5, §7, §18.

## 1. Validation objective

Migration 208 introduces:

* Topic-prerequisite review lifecycle fields.
* Grandfathering of existing prerequisite edges as `locked`.
* A locked-only planner trust boundary.
* Removal of direct prerequisite-table reads for `anon` and `authenticated`.
* A cycle-safe `SECURITY DEFINER` write RPC.
* Global advisory locking for concurrent ordering-edge writes.
* Lifecycle-state and timestamp CAS protection.
* Restricted RPC execution for `service_role`.

The repository explicitly requires the concurrency and CAS behavior to be proven against real PostgreSQL because unit tests cannot reproduce the advisory-lock behavior.

## 2. Database and operator setup

The validation was run using three simultaneous PostgreSQL sessions:

* Session 1: `j2a_s1`
* Session 2: `j2a_s2`
* Session 3: `j2a_s3`

The sessions used extended statement and idle-transaction timeouts to support controlled concurrency testing.

Verified operator permissions (identities anonymized — emails and profile
UUIDs are intentionally NOT recorded in this public repo; the permission tokens
are what the RBAC proof requires):

* Manage operator (anonymized): permission `exam_intelligence.manage`
* Review operator (anonymized): permission `exam_intelligence.review`

## 3. Migration structure findings

The deployed schema contained all required lifecycle fields:

* `reviewer_status`
* `reviewed_by`
* `reviewed_at`
* `review_notes`
* `created_by`
* `updated_at`

The lifecycle status constraint permits:

* `draft`
* `pending_review`
* `reviewed`
* `locked`
* `rejected`

The `reviewer_status` index was present.

The migration defines new rows as `draft` and backfills existing rows to `locked`.

## 4. RLS and RPC security findings

Verified:

* Direct `SELECT` access was revoked from `anon`.
* Direct `SELECT` access was revoked from `authenticated`.
* The previous permissive authenticated read policy was removed.
* Existing admin/service-mediated access remained available.
* The write function is `SECURITY DEFINER`.
* The function has a fixed `search_path = public`.
* RPC execution was revoked from:
  * `PUBLIC`
  * `anon`
  * `authenticated`
* RPC execution was granted only to `service_role`.

This prevents unreviewed edges and internal review metadata from being exposed through direct PostgREST reads.

## 5. Grandfathered-edge backfill findings

The three existing prerequisite edges were checked after migration:

| Metric                       | Result |
| ---------------------------- | -----: |
| Existing/grandfathered edges |      3 |
| `locked` edges               |      3 |
| Non-locked legacy edges      |      0 |

Result:

```text
grandfathered_total = 3
locked_count        = 3
non_locked_count    = 0
```

This confirms the **post-migration** state: all 3 prerequisite edges are `locked`, 0 in another status.

> **PD-D evidence gap (correction):** PD-D requires a **pre-migration existing-edge count** and a **representative planner behavior preservation** check (pre/post). This run captured only the post-migration `3 locked / 0 non-locked` state. The pre-migration count and a live representative planner run were not separately recorded, so backfill-preservation is evidenced by post-state + the deterministic backfill statement, not by a captured pre/post planner comparison.

## 6. Concurrent transitive-cycle test

A temporary subject containing three topics was created:

* Topic A: `0a41042b-dc22-403f-b149-798c875ddb0e`
* Topic B: `73f07c30-548f-4ae7-b451-39886ab471af`
* Topic C: `641e2ca5-d9e7-4e9d-a05f-a6e138711f30`

Three concurrent ordering writes were attempted:

* Session 1: A → B
* Session 2: B → C
* Session 3: C → A

Committed edges:

* A → B: `ca5e000b-7c89-4e74-9d58-6900b7dc656e`
* B → C: `26b89fa2-5d31-4fe2-b3f9-84f1d59569c1`

The cycle-closing C → A write failed with:

```text
ERROR: cycle: adding this prerequisite would create a transitive cycle
```

Post-test verification showed:

```text
A → B = 1
B → C = 1
C → A = 0
detected_cycle_count = 0
```

Finding: the single global advisory lock correctly serialized all ordering writes and prevented three independently initiated transactions from jointly committing a cycle.

The RPC uses one shared transaction-scoped lock and a recursive reachability query for ordering relations.

## 7. Manage-edit versus lifecycle-transition CAS race

Initial edge state:

```text
reviewer_status = draft
strength        = 1.000
```

Concurrent actions:

* Session 1 read the edge as `draft` and prepared a manage edit.
* Session 2 changed the edge from `draft` to `pending_review`.
* Session 1 then attempted its stale RPC update.

Result:

```text
ERROR: concurrent_modification:
edge changed review state; re-fetch and retry
```

Post-race verification:

```text
reviewer_status = pending_review
strength        = 1.000
```

Finding: the stale manage edit did not overwrite the newer review-state transition.

> **Scope note (correction):** this specific race changed `reviewer_status`
> (`draft → pending_review`) before the stale write, so `p_expected_status`
> alone rejects it — this run proves the **lifecycle-state** CAS but does NOT
> isolate the `p_expected_updated_at` **same-state** lost-update guard (two
> edits that both stay `draft`). The `updated_at` guard is present in the RPC
> and covered by the unit suite, but a same-state live-DB race was not run
> here; it remains to be independently exercised.

## 8. Submit CAS guard

A stale submit operation was attempted after the edge had already left an eligible manage state.

Result:

```text
UPDATE 0
```

Finding: submit transitions apply only when the edge remains `draft` or `rejected`. A concurrent state change causes the API-level operation to fail rather than overwrite the newer state.

## 9. Review CAS race

Session 1 observed the edge as `pending_review`.

Session 2 completed:

```text
pending_review → reviewed
```

The committed review included:

* Reviewer: review operator (anonymized)
* Review notes: `Concurrency validation review`
* Timestamp: `2026-07-02 00:10:14.342518+00`

Session 1 then attempted its stale transition:

```text
pending_review → rejected
```

Result:

```text
UPDATE 0
```

Finding: two reviewers cannot independently transition the same previously observed state using last-write-wins behavior.

## 10. Delete CAS guard

A stale manage delete was attempted after the edge reached `reviewed`.

Result:

```text
DELETE 0
```

The reviewed edge remained present.

Finding: a concurrent lifecycle transition cannot be silently discarded by a stale delete.

## 11. Lifecycle completion test

The validation edge was successfully transitioned:

```text
reviewed → locked
```

Final persisted values included:

* Status: `locked`
* Reviewer: review operator (anonymized)
* Notes: `Concurrency validation completed; locking edge`

Finding: the normal trusted lifecycle path successfully reaches `locked`.

The governing lifecycle is:

```text
draft → pending_review → reviewed → locked
                       ↘ rejected
```

Manage authority is restricted to editing `draft`/`rejected` and submitting to `pending_review`; trust-state transitions remain review-only.

## 12. Locked-edge manage restrictions

A grandfathered locked edge was tested:

```text
77777777-7777-7777-7777-777777777771
```

Manage-style edit predicate:

```text
reviewer_status IN ('draft', 'rejected')
```

Result:

```text
UPDATE 0
```

Manage-style delete predicate:

```text
reviewer_status IN ('draft', 'rejected')
```

Result:

```text
DELETE 0
```

Finding: manage operators cannot edit or delete a `locked` edge without review-authority rollback. This matches the locked C.3 contract.

## 13. Grandfathered locked-row reopen path

The grandfathered edge was tested inside a reversible transaction.

Review-authority reopen:

```text
locked → reviewed
```

Result:

```text
UPDATE 1
review_notes = Validation: reopen grandfathered locked edge
```

Review-authority rollback:

```text
reviewed → draft
```

Result:

```text
UPDATE 1
```

Manage edit after reopen:

```text
strength     = 0.875
source_basis = Validation: manage edit after review reopen
```

Result:

```text
reviewer_status = draft
```

Finding: the complete reopen-to-edit path works:

```text
locked
  → reviewed       review authority, notes required
  → draft          review authority
  → manage edit    manage authority
```

This proves that grandfathered locked rows are protected without creating an operational dead end.

## 14. Reopen transaction rollback and restoration

The reopen/edit transaction was rolled back.

The grandfathered row returned to its exact original values:

```text
id              = 77777777-7777-7777-7777-777777777771
reviewer_status = locked
strength        = 0.900
source_basis    = admin_review
reviewed_by     = null
reviewed_at     = null
review_notes    = null
updated_at      = 2026-07-01 22:46:06.350007+00
```

Finding: no production grandfathered data was modified by the reversible validation.

## 15. Planner trust-boundary findings

Representative fixture results:

| Edge  | Status   | Planner eligible |
| ----- | -------- | ---------------- |
| A → B | `locked` | Yes              |
| B → C | `draft`  | No               |

Finding: only `locked` prerequisite edges are planner-authoritative. (This table is **derived** from row `reviewer_status` + the planner's `.eq("reviewer_status","locked")` filter; it is not a captured before/after run of `generate_plan` — see the PD-D evidence gap in §5.)

The planner contract explicitly requires filtering by:

```python
.eq("reviewer_status", "locked")
```

Draft, pending-review, reviewed, and rejected rows must not influence planner ordering.

## 16. Validation-fixture cleanup

Temporary validation subject:

```text
d59526cc-9ba2-400c-98ef-6285effa690f
```

The subject was deleted after validation.

Final cleanup verification:

```text
subjects_remaining = 0
topics_remaining   = 0
edges_remaining    = 0
```

Finding: all temporary subjects, topics, and prerequisite edges were removed. No validation fixture data remains.

## 17. Final findings

The live database validation demonstrated that:

1. Migration 208 is deployed.
2. Lifecycle columns, constraints, defaults, and index are present.
3. Direct anonymous and authenticated prerequisite-table reads are blocked.
4. The write RPC is correctly security-hardened.
5. All existing prerequisite edges were grandfathered to `locked`.
6. No legacy edge remained in another lifecycle status.
7. The global advisory lock prevents concurrent transactions from jointly forming a cycle.
8. Recursive cycle detection rejects the transitive path-closing edge.
9. The resulting graph remained acyclic.
10. Manage-edit CAS prevents stale lifecycle overwrites (lifecycle-state guard).
11. Timestamp (`updated_at`) same-state CAS is present in the RPC and unit-covered, but was NOT isolated by this live run (see §7).
12. Submit, review, and delete conditional writes reject stale operations.
13. Locked edges cannot be manage-edited or manage-deleted.
14. The review-authority reopen path works.
15. Reopened edges become manage-editable only after review rollback to `draft`.
16. Planner authority is limited to `locked` edges.
17. Grandfathered production data was restored unchanged after testing.
18. All temporary fixture data was deleted.

## 18. Scope not independently exercised in this live DB session

The following broader acceptance items were not independently proven by this operator database run and should continue to rely on application/API tests or separate smoke validation:

* Out-of-exam topic scope rejection and allowed-scope creation.
* Direct self-edge rejection.
* Direct-reverse rejection as an isolated test.
* `supports → requires` cycle-closing promotion.
* Advanced Repair/CMS cycle-safety parity.
* HTTP-level permission responses such as `403` for manage/review separation.
* Super-admin bypass.
* Rejected lifecycle branch and rejected resubmission.
* Review-only list access.
* Audit-row emission through every HTTP write endpoint.
* Planner behavior for out-of-candidate-set prerequisites.
* Strength being ignored by planner ordering/scoring.
* **Pre-migration existing-edge count + representative planner before/after run** (PD-D preservation evidence — only post-migration state captured here; see §5).
* **Same-state `updated_at` lost-update race** — a two-session race where both observe `draft`, one commits while remaining `draft`, and the stale edit fails solely because `updated_at` changed (see §7).

These items are part of the full repository acceptance matrix but are distinct from the completed real-PostgreSQL concurrency + lifecycle-state CAS validation. They are covered by the J2-A′ backend/frontend unit suites merged in PR #835.

## 19. Final status

**Migration 208 live PostgreSQL VERIFY DB: PARTIAL PASS**

Proven on the live database: concurrent transitive-cycle prevention (global advisory lock), lifecycle-state CAS for manage/submit/review/delete, grandfathered locked-edge handling + reversible reopen path, RLS/RPC hardening, post-migration locked-only state, and fixture cleanup.

Not independently captured in this run (tracked in §18): the PD-D pre-migration count + representative planner pre/post preservation, and the same-state `updated_at` lost-update race. Those remain covered by unit tests / a follow-up DB check before claiming a full PD-D PASS.
