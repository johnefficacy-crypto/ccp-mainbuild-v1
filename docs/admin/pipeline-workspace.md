---
owner: ops
status: live
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
  - app/supabase/migrations
review_cadence: per-sprint
---

# Admin Pipeline Workspace (Operations Console)

The **Pipeline Workspace** is the single admin surface for the trust pipeline:
**scrape → review → promote → publish**. This doc describes the system
**as built** (verified against code on 2026-06-25), including the known gaps
between the shipped behaviour and the older design specs.

> Forward-looking design lives in [../scraping/verification-gateway-spec.md](../scraping/verification-gateway-spec.md)
> and [../scraping/verification-gateway-pr-plan.md](../scraping/verification-gateway-pr-plan.md);
> those describe a planned architecture that is only **partially** implemented.
> The action-phase table in [../engineering/admin-scrape-workflow.md](../engineering/admin-scrape-workflow.md)
> is accurate and complements this doc.

## Identity

- **Nav label:** "Pipeline Workspace" (`AdminShell.jsx` → `/admin/operations`).
- **Route / component:** `/admin/operations` → `app/frontend/src/pages/admin/OperationsConsole.jsx`.
- Candidate review is **merged into this single console** — there is no separate
  review page. Legacy routes `/admin/eligibility-queue` and `/admin/promotion-queue`
  redirect here (`adminRoutes.jsx`); the `?mode=queue` param on those redirects is
  currently a no-op (the workspace opens on the Candidates tab by default).
- The former `VerificationGatewayConsole` demo scaffold has been **removed**. The
  separate verification surfaces are `VerificationReports.jsx`
  (`/admin/verification-reports`) and `ReverificationBatches.jsx`.

## UI structure (single page)

`OperationsConsole.jsx` renders one `ReviewAndPublish` surface — there is **no**
"Setup & Run / Review & Publish" two-mode split (that was specced but never built).
Layout:

- **Current action card + selection context** — `CurrentActionCard` shows the single
  most-actionable step derived from `computeProgress()` (`AdminProgressBar.jsx`);
  `SelectionContextBanner` shows the active source / queue item / recruitment chips.
- **Left rail (two tabs):** `Candidates` (scrape queue → `QueueList`) and `Drafts`
  (recruitments → `RecruitmentList`), with a status filter on Candidates.
- **Right pane:** `AdminFixPanel` — the work surface. For a selected **queue item** it
  hosts official-source resolution, consensus-conflict rows, per-field review
  (`FieldReviewGroup` / `PostEligibilityReviewGroup`), a promotion preview, the
  duplicate list, and the sticky **promote bar**. For a selected **recruitment** it
  hosts blocker fixes (`RecruitmentBlockerFixForm`, `RecruitmentCriteriaPanel`) and
  the validate → verify → publish buttons.

Selection is URL-param driven (`source_id`, `queue_id`, `recruitment_id`,
`queue_status`). Heavy per-item detail is hydrated on demand via an
`include_detail=true&item_id=…` fetch and overlaid on the lightweight list row, so a
candidate that sorts off the first page after a write stays selectable.

## Item lifecycle & state machine (authoritative)

1. **Scrape pass** (`runner.run_scraping_pass`) inserts `scrape_queue` rows with
   `status = pending` (real), `duplicate` (dedup hit), or `dry_run` (mock). **Nothing
   auto-promotes** — no path in the scrape pass writes `recruitments`/`posts`
   (invariant per ADR-0003). SerpApi discovery lands in `aggregator_listings`, never
   as a promotable queue row.
2. **Per-field review** writes `extracted_field_evidence` via
   `verify` / `correct` / `reject`. `correct` also patches the queue item's effective
   `scrape_queue.extracted_data`. Only `verified` / `corrected` statuses count toward
   the gate. Field review is **post-scoped** (`entity_type` / `entity_key`) for
   `requires_domicile`.
3. **Official-source resolution** (`OfficialSourceQuickResolver`) creates/verifies a
   source draft and links it, flipping `official_source_resolved = true`.
4. **Promote** (`POST /api/admin/scrape/items/{id}/promote`) runs
   `evaluate_promotion_gate`, builds the effective recruitment, creates
   `recruitments` + `posts` + criteria, and flips the queue row to `approved` with a
   `promoted_recruitment_id`. The new recruitment is created at
   `publish_status = needs_review`. **Promotion sends no user alerts**; it only
   enqueues internal eligibility-recompute rows (best-effort).
5. **Recruitment publish lifecycle:** `draft / needs_review` → (`validate-publish`,
   read-only readiness) → `verify` (`publish_status = verified`) → `publish`
   (`publish_status = published`). Publishing is what triggers eligibility
   recompute fan-out and user alerts. Editing a critical field on a published
   recruitment demotes it back to `needs_review`.
   - Frontend gates: **Mark verified** is enabled only when `validateResult.ready`;
     **Publish** is enabled only when `publish_status === "verified"`
     (`AdminFixPanel.jsx`).

### The promotion gate (`evaluate_promotion_gate`)

Runs on the two promote paths only. Blocks (in order) on:

| reason code | meaning |
|---|---|
| `dry_run_not_promotable` | `is_dry_run` truthy (hard block) |
| `unverified_official_source` | `official_source_resolved is False` |
| `high_risk_fields_unverified` | any required high-risk field lacks a `verified`/`corrected` evidence row (recruitment-level: `apply_end_date`, `official_notification_url`, `official_apply_url`, `organization_name`, `total_vacancies`; post-scoped per post: `requires_domicile`) |
| `data_contradictions` | re-running the normalizer flags `date_order_invalid`, `notification_after_apply_end`, `age_range_invalid`, or `vacancy_sum_mismatch` |

The promote endpoint additionally requires queue `status ∈ {approved, pending,
needs_review}` and blocks on open rows in `recruitment_verification_conflicts`
(via `_open_conflict_field_keys`).

## Endpoint inventory

| Endpoint | Owner | Purpose |
|---|---|---|
| `GET /api/admin/sources` | `admin_scrape.py` | source registry (also served from `admin_trust.py`) |
| `GET /api/admin/scrape/runs` | `admin_scrape.py` | recent scrape runs |
| `GET /api/admin/scrape/queue` | `admin_scrape.py` | candidate queue (`status`, `limit`, `include_detail`, `include_duplicates`, `item_id`) |
| `POST /api/admin/scrape/items/{id}/fields/{field}/{verify\|correct\|reject}` | `admin_scrape.py` | per-field review |
| `POST /api/admin/scrape/items/{id}/promote` | `admin_scrape.py` | gated promote → new recruitment |
| `POST /api/admin/scrape/items/{id}/merge-into/{rec}` | `admin_scrape.py` | merge fields into existing recruitment (**ungated** — see gaps) |
| `POST /api/admin/scrape/items/{id}/{mark-duplicate\|approve\|reject\|reopen}` | `admin_scrape.py` | status transitions |
| `GET .../promotion-preview`, `GET .../merge-preview/{rec}` | `admin_scrape.py` | read-only previews |
| `POST .../resolve-official-source`, `POST .../draft-sources` | `admin_scrape.py` | official-source resolution |
| `GET /api/admin/scrape/items/{id}/conflicts` | `admin_scrape.py` | open consensus conflicts for an item |
| `POST /api/admin/conflicts/{id}/{resolve\|reject}` | `admin_conflicts.py` | conflict adjudication |
| `GET /api/admin/recruitments` | `admin_trust.py` | recruitment drafts + `blocking_issues` |
| `POST /api/admin/recruitments/{id}/{validate-publish\|verify\|publish}` | `admin_trust.py` | publish lifecycle |

## Frontend module map (`features/admin/workflow/`)

`AdminProgressBar` (`computeProgress` state machine) · `CurrentActionCard` ·
`SelectionContextBanner` · `AdminFixPanel` (orchestrator) · `FieldReviewGroup` /
`PostEligibilityReviewGroup` (per-field review) · `OfficialSourceQuickResolver` ·
`ConflictResolver` · `DuplicateMergePreview` · `PromotionPreviewPanel` ·
`BlockerList` · `useConflicts` / `useAdminAction` / `scoreUtils` /
`adminWorkflowContract`.

Note: `BulkActionPreview`, `VerificationReportCard`, `ReverificationBatchAlert` live
in this folder but belong to the **Verification-Reports** surface, not the workspace.
`AdminPhaseRail.jsx` is **dead code** (imported nowhere). `InlineTrustFixes` is used
by the separate Recruitments page, not the workspace.

## Known gaps

These are documented current behaviours / latent bugs, not aspirational design. Full
detail (severity, file:line) in
[../audits/2026-06-25-pipeline-workspace-critical-examination.md](../audits/2026-06-25-pipeline-workspace-critical-examination.md):

1. **Merge / mark-duplicate / approve bypass the promotion gate.** `merge-into` writes
   canonical recruitment fields with no gate and no `is_dry_run` check; a rejected or
   dry-run row can mutate live data.
2. **State machine unenforced** on merge / mark-duplicate / approve (blind status
   writes); only `reopen` validates its prior state.
3. **Conflict subsystem is unwired in production.** The resolve/reject UI and the
   promote-path conflict gate read `recruitment_verification_conflicts`, which has no
   production writer; live consensus conflicts go to
   `recruitment_verification_reports.conflicts`. The resolve endpoint also requires a
   `confirmation_text = "CONFIRM_OVERRIDE"` the frontend never sends (would 422).
4. **`promote_queue_item` is non-idempotent** (read → create recruitment → then flip
   status, with no compare-and-swap) — concurrent/retried promotes risk duplicate or
   orphaned recruitments.
5. **The documented "two gates in sequence" is not wired.** `check_gateway_promotion`
   runs only on the Verification-Reports preview, never on promote.
6. **`promotion-preview.ok` diverges from the real gate** for post-scoped
   `requires_domicile` (flat vs per-post evidence check).
7. **`publish` has no re-publish guard** (clobbers `published_by/at`, re-fans-out);
   `verify` is advisory and not enforced server-side. RLS migration 130 exposes
   `needs_review` recruitments (and posts) to anonymous reads — promotion, not
   publish, is the de-facto public-visibility boundary today.
8. **Frontend:** the 503 auto-retry / skip-refresh-on-failure logic in `AdminFixPanel`
   is dead because `useAdminAction.runAction` swallows errors instead of rethrowing.
