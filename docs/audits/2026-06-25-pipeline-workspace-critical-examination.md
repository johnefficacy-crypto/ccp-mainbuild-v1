---
owner: eng
status: review
last_verified_against_code: 2026-06-25
source_of_truth: code
related_code:
  - app/frontend/src/pages/admin/OperationsConsole.jsx
  - app/frontend/src/features/admin/workflow
  - app/backend/app/api/admin_scrape.py
  - app/backend/app/api/admin_trust.py
  - app/backend/app/api/admin_conflicts.py
  - app/backend/app/scraping/promotion_gate.py
  - app/backend/app/scraping/runner.py
related_migrations:
  - app/supabase/migrations/130_public_catalog_rls_repair.sql
review_cadence: ad-hoc
---

# Pipeline Workspace — Critical Examination (2026-06-25)

Critical review of the admin **Pipeline Workspace** (Operations Console,
`/admin/operations`) and all its components/modules — logic, intention, and
implementation across frontend and backend. Findings below were surfaced by a
multi-pass review and then **verified directly against source** (each item cites
`file:line` and was confirmed, not just asserted).

As-built reference: [../admin/pipeline-workspace.md](../admin/pipeline-workspace.md).

## Verdict

The **frontend is high-craft** — sound state machine (`computeProgress`),
cancel-token fetches, focus-trapped modals, defensive score clamping, client-side
gate mirroring as defense-in-depth, and near-perfect adherence to the field-action
backend contract. The **backend trust gate is real but narrow**: it is correctly
enforced on the two _promote_ paths and nowhere else, and several adjacent write
paths sit outside it. The most serious issues are (a) a second canonical-write path
(`merge-into`) with no gate, (b) an entire conflict-resolution subsystem that is
unwired in production, and (c) a non-idempotent promote. None is an open
anonymous-write hole — every endpoint requires admin permission — but each
undermines the "Trust > Speed" invariant the workspace exists to enforce.

## Backend findings

### P0 — correctness / invariant

- **P0-1 · `merge-into` bypasses the promotion gate.**
  `admin_scrape.py:1915-1961` (`merge_queue_item_into_recruitment`) patches canonical
  `recruitments` fields (`official_notification_url`, `official_apply_url`,
  apply/notification dates, `total_vacancies`, `source_pdf_url`, and reassigns
  `source_id`) directly. It never calls `evaluate_promotion_gate`, never checks
  `official_source_resolved` / unverified fields / open conflicts, and does not even
  `select` `is_dry_run`. A rejected or synthetic dry-run row can mutate live
  recruitment data. The merge UI is a primary path (the console prefers merge when a
  duplicate slug exists). _Direction:_ run the gate (and a dry-run block) before
  applying the merge patch.

- **P0-2 · State machine unenforced on merge / mark-duplicate / approve.**
  Each does a blind `UPDATE … .eq("id", queue_id)` with no allowed-prior-state guard
  (`merge-into` 1953; `mark-duplicate` 1964-1981; `approve` 1984-2008). Merge-after-
  reject, duplicate-after-promote, approve-from-any-state are all reachable. Only
  `reopen` (2045-2064) validates its source state (`rejected → pending`). _Direction:_
  add a shared allowed-state check; use conditional updates (`.eq("status", expected)`)
  for atomicity.

- **P0-3 · Conflict subsystem unwired in production.**
  The admin resolve/reject UI (`admin_conflicts.py`), the `useConflicts` hook, and the
  promote-path gate `_open_conflict_field_keys` (`runner.py:89-110`) all read/write the
  `recruitment_verification_conflicts` table — which has **no production writer**
  (verified: zero `.insert`/SQL-insert anywhere outside tests). Live consensus conflicts
  are persisted to `recruitment_verification_reports.conflicts` (jsonb) by
  `verification_reports.write_conflicts` (`:527`), read by a _different_ gate
  (`check_gateway_promotion._has_unresolved_conflict`) that itself never runs on
  promote. Net: in production no consensus conflict ever blocks promotion and the
  "Resolve conflict" UI has nothing to act on. Additionally the resolve endpoint
  requires `confirmation_text == "CONFIRM_OVERRIDE"` (`admin_conflicts.py:57,267`) that
  the frontend never sends → any UI resolve 422s. _Direction:_ pick one canonical
  conflict store and wire the gate, endpoints, and consensus writer to it; align the
  resolve contract with the UI.

- **P0-4 · `promote_queue_item` is non-idempotent (TOCTOU).**
  `admin_scrape.py:1499-1607` reads status → runs gate → **creates the recruitment** →
  _then_ unconditionally `UPDATE status='approved' WHERE id=?` (no compare-and-swap).
  Two concurrent/retried promotes can both pass and both create recruitments; if the
  final status write fails after creation, the recruitment is orphaned and the queue
  row stays `pending` (re-promotable on retry). `promote_run` has the same shape.
  _Direction:_ make the status flip the concurrency guard (conditional update / single
  RPC/transaction).

### P1 — likely bug / significant smell

- **P1-1 · Documented "two gates in sequence" is not wired.**
  `promotion_gate.py` previously claimed both `evaluate_promotion_gate` **and**
  `check_gateway_promotion` run on promote. `check_gateway_promotion` is referenced
  only by `admin_verification_reports.py:517` and tests — never by the promote path.
  (Comment corrected in this change.)

- **P1-2 · `promotion-preview.ok` diverges from the real gate.**
  `admin_scrape.py:1356-1371` computes missing high-risk fields with a **flat**
  `field_name → status` map, ignoring `entity_type`/`entity_key`, whereas the gate
  (`promotion_gate.py:164-189`) requires a verified evidence row **per post** for
  `requires_domicile`. Preview can show "Ready" while promote 409s (or vice-versa).
  `list_scrape_queue` (1256-1281) does the scoped computation correctly; `promotion-
  preview` and the eligibility-queue `_shape` (≈2148) do not.

- **P1-3 · `publish` has no re-publish guard.**
  `admin_trust.py:303-311` re-runs readiness (good — not a stale flag) but does not
  early-return when already `published`: re-clicking clobbers `published_by`/
  `published_at` and re-fans-out eligibility recompute over every onboarded profile.

- **P1-4 · `verify` is advisory / state machine not enforced server-side.**
  `publish` does not require `publish_status == 'verified'`. The draft→verified→
  published sequence is enforced only in the workspace UI; the separate Recruitments
  page can publish a `needs_review` row directly.

- **P1-5 · `list_scrape_queue` total/paging is wrong under the `source_type` facet.**
  The `source_type` filter is applied in Python to the current page after a pre-filter
  `count`, so `total` is overstated and later-page matches can be unreachable
  (`admin_scrape.py` ≈1068-1083).

- **P1-6 · Conflict `resolve`/bulk-resolve are non-atomic** (`admin_conflicts.py`):
  multiple independent Supabase writes (queue payload, recruitment column, conflict
  row) with no transaction or rollback; a mid-sequence failure (e.g. non-allowlisted
  field raising 400 after the queue patch already wrote) leaves a torn write.

### P2 — minor / latent

- Broad `except Exception` blocks in `list_scrape_queue` zero out evidence/conflict
  maps; the conflict reset can make a row read as promotable (`open_conflicts=0`) on a
  transient read failure.
- `_audit` in `admin_trust.py` stringifies structured metadata into a `notes` column
  (lossy/unqueryable) where `admin_conflicts._audit` stores structured JSON.
- `_evaluate_readiness` swallows all exceptions into a generic `readiness_check_failed`
  blocker and leaks `str(exc)` into `warnings`.
- Inconsistent `queue_id` validation; merge/duplicate/approve don't validate it at all
  (PostgREST parameterization makes this low-risk).

### Cross-cutting (RLS) — flag

- **Public RLS exposes `needs_review` recruitments.**
  `migrations/130_public_catalog_rls_repair.sql:34,46` sets the public read policy to
  `publish_status in ('published','needs_review')` for recruitments **and** posts. Since
  promotion creates `needs_review` rows, **promotion (not publish) is the de-facto
  public-visibility boundary today** — which contradicts the "only published reaches
  users" mental model in the README/architecture docs. Confirm whether `needs_review`
  exposure is intentional; if not, restrict the policy to `published`. If it is
  intentional, the publish-lifecycle docs should say so.

## Frontend findings

Overall quality is high; the field-review components and the console's hydration
design are well-reasoned, and the field-action contract matches the backend exactly
(`POST /api/admin/scrape/items/{id}/fields/{field}/{verify|correct|reject}` with
`{notes, corrected_value, entity_type, entity_key}`).

- **P1 · Dead resilience logic in `AdminFixPanel`.** Its `queueFieldAction`
  (`AdminFixPanel.jsx:150-175`) assumes `onFieldAction` **throws** to drive a 503
  auto-retry and to skip the post-write preview refresh. In production the handler is
  `useAdminAction.runAction`, which **catches every error, toasts, and returns `false`**
  — so the catch never fires, the 503 retry never runs, and the preview refetches on
  failure. Tests pass only because they inject a throwing handler. _Direction:_ rethrow
  in `runAction` (it already stores `error`) or move the retry into `runAction`.

- **P2 · `CurrentActionCard` "All steps clear" headline is unreachable.** It requires
  all 13 steps `complete`, but the console never passes `eligibilityOps`, so
  `eligibility_monitored` never completes. Minor dead UI state.

- **P2 · `PostEligibilityReviewGroup` checkbox can drift** from server truth after a
  reload (local `useState` seeded once, no resync on new `corrected_value`).

- **P2 · `AdminPhaseRail.jsx` is dead code** (imported nowhere) — remove or wire.

- **P2 · `?mode=queue` is ignored** by `OperationsConsole` (legacy redirect param);
  harmless but dead.

- **Notes corrected during verification (NOT bugs):** `RecruitmentCriteriaPanel.jsx`
  **does** exist at `features/admin/recruitments/` (no missing-module/build issue);
  `InlineTrustFixes` **is** used by `pages/admin/Recruitments.jsx` (not orphaned).

## Test-coverage gaps

- `FieldReviewGroup` and `PostEligibilityReviewGroup` are well tested.
- **No frontend test** for the promote-gate composition (`blockedFromPromote`), the
  conflict-row integration, merge handoff, `RecruitmentBlockerFixForm`, or the
  `OperationsConsole` page itself (selection hydration / reload-after-write).
- Backend `evaluate_promotion_gate` has unit tests; the ungated merge/duplicate/approve
  paths and the conflict wiring do not.

## Recommended remediation order

1. Decide the canonical conflict store and wire it (P0-3) — confirm whether this
   feature is meant to be live.
2. Gate `merge-into` and add state guards to merge/duplicate/approve (P0-1, P0-2).
3. Make promote idempotent (P0-4).
4. Confirm/repair the `needs_review` RLS exposure (cross-cutting).
5. Fix `promotion-preview` post-scoping (P1-2), the re-publish guard (P1-3), and the
   dead `AdminFixPanel` retry wiring (frontend P1).

_Documentation was updated in this change (this audit, the as-built
`admin/pipeline-workspace.md`, the corrected `promotion_gate.py` comment, the
`admin-scrape-workflow.md` gate-scope note, and as-built banners on the gateway
specs). The code-level fixes above are intentionally **not** applied here._
