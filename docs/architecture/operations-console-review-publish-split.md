# Operations Console — Review & Publish Split (Contract-First)

- Document type: architecture contract — scope split for `app/frontend/src/pages/admin/OperationsConsole.jsx`
- Status: **PROPOSED — OPERATOR APPROVAL REQUIRED before any implementation PR.**
- Date: 2026-07-08
- Parent track: internal audit finding — Operations Console still owns scrape-execution/source-config data fetching alongside review/publish workflow.
- Authority: `CLAUDE.md` Frontend governance (no-new-surface rule, locked 2026-06-21; one API source of truth per surface); `docs/status/Manage-Exam-Operational-Editors-Gate-2026-07-01.md` and `docs/status/J3-Competition-Cutoffs-Gate-2026-07-02.md` (contract-first style/rigor precedent).
- Scope note: this doc is **frontend data-loading and page-scope only**. No backend router split is proposed — see Section 3.4.

---

## How to use this document

Every section states either a grounded fact about the current file (with line citations) or a proposed target that requires operator sign-off before implementation. Nothing here has been implemented. Do not dispatch an implementation PR against this doc until it is marked **OPERATOR APPROVED**.

---

## Section 1 — Current state (grounded in `OperationsConsole.jsx`, 820 lines)

### 1.1 Single `loadAll` fan-out (lines 100–120)

`loadAll` fires four independent reads in parallel on every mount and after nearly every mutation:

```js
const [s, r, q, recs] = await Promise.all([
  api.get("/api/admin/sources"),
  api.get("/api/admin/scrape/runs?limit=10"),
  api.get("/api/admin/scrape/queue?status=all&limit=50"),
  api.get("/api/admin/recruitments"),
]);
```

- `sources` (line 58, 110) and `runs`/`latestRun` (lines 59, 111, 244) are consumed only to feed `computeProgress`'s `progressState` (lines 256–263) and `CurrentActionCard`'s "what phase is this source/run in" messaging (`onPrimaryAction`, lines 268–291) — i.e., read-only status context, not editable here.
- Every mutating action that calls `loadAll()` (`promote` line 317, `verify` line 346, `publish` line 357, `markDuplicate` line 391, `confirmReject` line 427, `resolveConflict` line 452, `rejectConflict` line 468) re-fetches sources and runs even though none of those actions can change a source or a scrape run.

### 1.2 Scope actually exercised by the component

| Concern | Evidence in file |
|---|---|
| Candidate review (field verify/reject/correct) | `queueFieldAction` (293–307) → `POST /api/admin/scrape/items/{id}/fields/{field}/{action}` |
| Conflict resolution | `resolveConflict`/`rejectConflict` (432–471), `useConflicts` hook (line 85), `conflictTarget` state (67) |
| Duplicate/merge handling | `openMergePreview`/`confirmMerge` (363–380), `markDuplicate` (382–394), `DuplicateMergePreview` render (727–734) |
| Promotion to recruitment draft | `promote` (309–326) → `POST /api/admin/scrape/items/{id}/promote` |
| Reject/reopen candidate | `rejectCandidate`/`confirmReject` (396–430), `reopenCandidate` (402–413), `RejectCandidateDialog` (557–602) |
| Validate / verify / publish recruitment | `validate` (328–337), `verify` (339–349), `publish` (351–361) |
| **Scrape execution triggers** | **Not present** — `run`/`run-dry` live only in `Scraper.jsx`. |
| **Source CRUD/verify** | **Not present** — create/edit/verify/activate live only in `Sources.jsx`. |

So the component's own mutation surface is *already* scoped to review/promote/validate/verify/publish — the file does not itself run scrapes or edit source config. The problem is narrower than "mixed concerns everywhere": it is that `loadAll` still pulls `sources` and `runs` as read-only context data that two other surfaces already own and fetch independently (Section 2.2), and that this coupling makes every review/publish mutation pay for an unrelated read.

### 1.3 Structure

`OperationsConsole` (52–555, default export) → renders `ReviewAndPublish` (605–740, local, not exported) which lays out `CurrentActionCard` + `SelectionContextBanner` (progress/state banner), then a two-column workspace: left rail `QueueList`/`RecruitmentList` (742–820) driven by `leftView` ("candidates" | "drafts", state at line 71), right column `AdminFixPanel` (imported from `features/admin/workflow/`) + `DuplicateMergePreview`. `RejectCandidateDialog` (557–602) is a local modal.

### 1.4 Existing nav/route ownership (already split, pre-dates this doc)

Three separate top-level `AdminShell.jsx` nav entries already exist (`app/frontend/src/pages/admin/AdminShell.jsx:22,26,27`):

| Nav label | Route (`adminRoutes.jsx:75,84,85`) | Page |
|---|---|---|
| Pipeline Workspace | `/admin/operations` | `OperationsConsole.jsx` (this file) |
| Source Registry | `/admin/sources` | `Sources.jsx` (531 lines) |
| Scrape Monitor | `/admin/scraper` | `Scraper.jsx` (683 lines) |

`Sources.jsx` already independently owns source CRUD/verify/activate (`Sources.jsx:313,335,336,343,344` — `GET/PUT/POST /api/admin/sources`, `POST /api/admin/sources/{id}/verify`, `/activate`, `/deactivate`). `Scraper.jsx` already independently owns run triggering and a **richer** queue view (`Scraper.jsx:241,250,256,351,367,394` — `GET /api/admin/scrape/runs`, `GET /api/admin/sources`, `POST /api/admin/scrape/run-dry`, `POST /api/admin/scrape/run`, and its own `GET /api/admin/scrape/queue` with `status`, `sort`, `risk`, `q`, `limit=100` params for pre-promotion triage). `onPrimaryAction` in `OperationsConsole.jsx` (271–274) already `navigate("/admin/scraper")` for `source_ready`/`dry_scrape`/`live_scrape` action kinds — the console already hands off scrape-setup actions to Scrape Monitor by routing, it just also still fetches the read-only status data itself.

---

## Section 2 — Problem

### 2.1 Redundant fan-out on every review action

Because `loadAll` (Section 1.1) is the only reload primitive most mutations call, every promote/verify/publish/merge/reject/conflict-resolve action re-fetches `/api/admin/sources` and `/api/admin/scrape/runs?limit=10` even though none of those endpoints' data changes as a result. `reloadQueue` (128–137) exists specifically to *avoid* this for field-level actions ("one click is one read, not four" — comment at line 126), which is the component's own acknowledgment that the four-way fan-out is heavier than most actions need — it just wasn't extended to the recruitment-level actions (promote/verify/publish/merge/reject/conflict-resolve all still call the full `loadAll`).

### 2.2 Duplicated data ownership across three surfaces

`sources` and (queue-shaped) scrape data are independently fetched by all three top-level admin surfaces:

- `OperationsConsole.jsx:105,107` — `sources`, `queue` (limit 50, status=all)
- `Sources.jsx:313` — `sources` (full CRUD view)
- `Scraper.jsx:250,256,241` — `runs`, `sources`, `queue` (limit 100, sort/risk/q params, its own triage view)

Three independent client-side fetchers for the same two endpoints (`/api/admin/sources`, `/api/admin/scrape/queue`) means query-param changes, caching behavior, or field additions must be reconciled in three places instead of one. `OperationsConsole`'s copy is the one that contributes nothing back — it never triggers a run, never edits a source, and its queue fetch (limit 50, `status=all`, no sort/risk controls) is a strict subset of what `Scraper.jsx` already renders.

### 2.3 Cognitive load: one 820-line file spans five workflow stages plus status telemetry

The file currently threads together: (a) source/run status telemetry for `CurrentActionCard` context, (b) candidate field review, (c) conflict resolution, (d) duplicate/merge handling, (e) promotion, and (f) validate/verify/publish. An engineer opening this file to fix a publish-flow bug must first read past the `sources`/`runs` fetch, `selectedSource`/`latestRun` derivation, and `onPrimaryAction`'s scrape-setup routing branch (lines 271–274) before reaching any publish-related code — none of which they can act on from this surface (there is no source-edit or run-trigger control in this file at all; `selectedSource` is read-only display).

### 2.4 `AdminFixPanel`/`sources` prop is a narrower, legitimate dependency — not part of the problem

`AdminFixPanel` consumes `sources` (`AdminFixPanel.jsx:63,92,109,213,492`) to power the official-source resolver inside the field-review workflow (attaching/confirming an official source URL against a candidate) and the recruitment fix section. This is a **read-only lookup used during review**, not source configuration — it must be distinguished from `loadAll`'s full-list refetch. See Section 3.3.

---

## Section 3 — Target scope

### 3.1 Stays in Operations Console (Review & Publish)

Route `/admin/operations`, nav label "Pipeline Workspace" — **unchanged, no rename required by this doc** (rename is a separate, non-blocking decision — see Open Questions).

- Candidate queue review: list, filter, field verify/reject/correct (`queueFieldAction`).
- Conflict resolution (`useConflicts`, `resolveConflict`, `rejectConflict`).
- Duplicate/merge handling (`openMergePreview`, `confirmMerge`, `markDuplicate`).
- Promotion to recruitment draft (`promote`).
- Recruitment validate/verify/publish (`validate`, `verify`, `publish`).
- Reject/reopen candidate (`rejectCandidate`, `confirmReject`, `reopenCandidate`).
- `AdminFixPanel` and `DuplicateMergePreview` (already imported from `features/admin/workflow/` — unchanged).

### 3.2 Moves out (already owned elsewhere — this is consolidation, not a new build)

| Concern | Already owned by | Action required |
|---|---|---|
| Scrape run triggering (dry/live) | `Scraper.jsx` (`/admin/scraper`) | None — already there. Remove `OperationsConsole`'s redundant `runs` fetch. |
| Source CRUD/verify/activate | `Sources.jsx` (`/admin/sources`) | None — already there. Remove `OperationsConsole`'s redundant full-`sources`-list fetch used only for status display. |
| Scrape-run status telemetry (`latestRun`, `runs`) used in `CurrentActionCard` | N/A today | Either drop from `progressState` (simplest) or replace with a lightweight, purpose-built read (Open Question 1). |

### 3.3 API / data-loading boundary

| Endpoint | Owning surface | Notes |
|---|---|---|
| `GET /api/admin/scrape/runs` | Scrape Monitor only | Remove from Operations Console `loadAll`. |
| `POST /api/admin/scrape/run`, `/run-dry` | Scrape Monitor only | Already exclusive to `Scraper.jsx`. |
| `GET /api/admin/sources` (full list, for CRUD/status display) | Source Registry (primary); Scrape Monitor (source-picker for run triggering) | Remove Operations Console's `loadAll`-level full-list fetch. |
| `GET /api/admin/sources` (read-only lookup for official-source resolver inside field review) | **Stays in Operations Console**, but scoped as a dependency of `AdminFixPanel`'s resolver, not of `loadAll` | See Open Question 2 — whether this needs its own lighter endpoint/shape or can keep reusing the existing list call. |
| `GET /api/admin/scrape/queue` (triage view: sort/risk/search, limit 100, pre-promotion) | Scrape Monitor | Already the richer owner; unaffected. |
| `GET /api/admin/scrape/queue` (review view: status filter, limit 50, drives `QueueList`/`AdminFixPanel`) | Operations Console | Stays — this is the review surface's own list, a distinct read shape from Scrape Monitor's triage list (different filter defaults, no sort/risk controls). |
| `GET /api/admin/recruitments` | Operations Console | Stays — drafts list for the "Drafts" left-rail tab; not owned elsewhere. |
| `POST /api/admin/scrape/items/{id}/fields/{field}/{verify,reject,correct}` | Operations Console | Stays — unchanged. |
| `POST /api/admin/scrape/items/{id}/{promote,merge-into,mark-duplicate,reject,reopen}` | Operations Console | Stays — unchanged. |
| `GET /api/admin/scrape/items/{id}/conflicts`, `GET /api/admin/recruitments/{id}/conflicts`, `POST /api/admin/conflicts/{id}/{resolve,reject}` | Operations Console | Stays — unchanged. |
| `POST /api/admin/recruitments/{id}/{validate-publish,verify,publish}` | Operations Console | Stays — unchanged. |

### 3.4 Backend is not split

All of the above endpoints already live in two existing backend routers (`app/backend/app/api/admin_scrape.py`, `admin_conflicts.py`, `admin_trust.py`) that are not organized per-frontend-surface today (e.g. `admin_scrape.py` serves both Scrape Monitor's run/queue endpoints and Operations Console's item-mutation endpoints). This doc proposes **no backend route moves, no new router, no new file** — the split is entirely in which frontend page calls which existing endpoint on mount. This keeps the change low-risk and independently revertible per PR slice.

---

## Section 4 — Migration plan (phased, mergeable PR slices)

Mirrors the J2/J3 gate PR-slice pattern: each PR is independently shippable and independently revertible.

### PR1 — Drop redundant `sources`/`runs` fan-out from `loadAll`

- Scope: `OperationsConsole.jsx` only.
- Remove `api.get("/api/admin/sources")` and `api.get("/api/admin/scrape/runs?limit=10")` from `loadAll` (lines 104–113).
- Resolve Open Question 1 first (what, if anything, replaces `selectedSource`/`latestRun` in `progressState`/`CurrentActionCard`). This PR cannot ship until that question is answered, since `computeProgress` (imported from `features/admin/workflow/AdminProgressBar`) currently depends on `progressState.source`/`progressState.latestRun`.
- `sources` prop passed into `AdminFixPanel` (line 507) is **kept** — resolve Open Question 2 for its final source/shape, but do not block PR1 on it if the existing `GET /api/admin/sources` call can be kept solely for this purpose (renamed/scoped, not removed) while the `loadAll`-level status-display usage is dropped.
- File scope: `app/frontend/src/pages/admin/OperationsConsole.jsx` (and `AdminProgressBar.jsx`/`CurrentActionCard.jsx` only if Open Question 1 requires a `progressState` shape change).
- Independently shippable: yes — pure deletion of unused-for-mutation reads, no route/nav change.

### PR2 — Scope mutation-triggered reloads away from the dropped fields

- Scope: same file.
- Update the seven `loadAll()` call sites in mutation handlers (Section 1.1) to call a narrower reload (reuse the existing `reloadQueue` pattern, or a new `reloadRecruitments` for verify/publish/promote) instead of the full four-way `loadAll`.
- File scope: `app/frontend/src/pages/admin/OperationsConsole.jsx` only.
- Independently shippable: yes, but depends on PR1 landing first (otherwise there is nothing to narrow).

### PR3 — Rename nav label / masthead copy (only if Open Question 3 resolves toward it)

- Scope: `AdminShell.jsx` nav label text only ("Pipeline Workspace" → e.g. "Review & Publish") and any masthead string inside `OperationsConsole.jsx`.
- **Serial delivery rule applies** (`CLAUDE.md`): this PR touches `AdminShell.jsx` and must be one owner's sequential work, not fanned out, and must not run concurrently with any other PR touching `AdminShell.jsx`/`adminRoutes.jsx`.
- No route change (`/admin/operations` path stays — changing the path is out of scope and not justified by this doc).
- Independently shippable: yes, and optional — can be skipped entirely if Open Question 3 resolves toward "keep current label."

### PR4 (optional, only if Open Question 2 resolves toward a new endpoint) — Purpose-built official-source lookup

- Scope: backend — a narrower read endpoint (e.g. `GET /api/admin/sources?fields=id,name,tier` or similar) for the `AdminFixPanel` official-source resolver, if the full `/api/admin/sources` list proves too heavy or leaks fields not needed for review-time attachment.
- File scope: `app/backend/app/api/admin_scrape.py` (or wherever `/admin/sources` is defined) + `OperationsConsole.jsx`/`AdminFixPanel.jsx` call site.
- Independently shippable: yes, deferred until PR1–PR2 land and the lookup's actual field needs are confirmed against real usage.

No PR in this plan touches `adminRoutes.jsx` route paths, `Sources.jsx`, or `Scraper.jsx` — those surfaces already own their concerns (Section 1.4) and need no code change from this split.

---

## Section 5 — Explicit non-goals

- **No new top-level sidebar destination.** Source Registry and Scrape Monitor already exist as separate nav entries (`AdminShell.jsx:26,27`) and already own source config and scrape execution respectively. This split consolidates Operations Console's redundant reads into those existing surfaces — it does not create a fourth destination. The no-new-surface rule's "≥2 removals" trade is **not triggered** because **zero new destinations are proposed**.
- No new route. `/admin/operations` path is unchanged; PR3 (optional) only changes display text, not the path.
- No backend router split (Section 3.4) — endpoint ownership by frontend surface changes, not endpoint location.
- No change to `Sources.jsx` or `Scraper.jsx` beyond what they already do today.
- No change to the review/promote/validate/verify/publish mutation contracts or request/response shapes — this is a read-scope reduction only.
- No change to RBAC/permission gates on any of the touched endpoints.
- No change to `AdminFixPanel.jsx`'s or `DuplicateMergePreview.jsx`'s internal behavior beyond what Open Question 2 might require for the `sources` prop shape.

---

## Section 6 — Open questions requiring operator/product sign-off

1. **`progressState.source` / `progressState.latestRun` replacement.** `CurrentActionCard`'s `computeProgress` (via `AdminProgressBar.jsx`) currently uses `selectedSource`/`latestRun` to decide whether to show "source not verified yet" / "no scrape run yet" prompts and to route the primary action to `/admin/scraper` (lines 271–274). If Operations Console stops fetching `sources`/`runs`, does `CurrentActionCard` (a) drop those states entirely and only handle post-scrape states (candidate exists in queue), pushing all pre-scrape guidance to Scrape Monitor, or (b) keep a lightweight read (e.g. a single boolean "any source needs setup" flag) so the card can still nudge an admin toward Scrape Monitor? This changes `computeProgress`'s contract and must be decided before PR1.
2. **Official-source resolver's `sources` dependency.** Is the full `/api/admin/sources` list (same shape `Sources.jsx` uses for CRUD) acceptable to keep fetching from Operations Console solely for `AdminFixPanel`'s resolver, or does this need a narrower purpose-built read (PR4)? Affects whether PR4 is needed at all.
3. **Nav label rename.** Is "Pipeline Workspace" renamed to something like "Review & Publish" to match the new scope (PR3), or does the label stay as-is since the route already narrows in practice? This is cosmetic and non-blocking for PR1/PR2, but should be decided once so PR3 isn't built speculatively.
4. **`queueFilter`/`leftView` URL-param scope.** Out of scope for this doc, but noted: Scrape Monitor's queue view already has independent `queueFilter`/`queueSort`/`queueRisk`/`queueQuery` state; Operations Console has its own `queueFilter`. No consolidation of these two independent queue views is proposed here — confirm that remains intentional (two different read shapes for two different workflows) rather than a future target for further consolidation.

---

*Status: PROPOSED. Awaiting operator approval on Section 6 before any implementation PR (PR1–PR4) is dispatched, per the contract-first pattern established in `docs/status/Manage-Exam-Operational-Editors-Gate-2026-07-01.md` and `docs/status/J3-Competition-Cutoffs-Gate-2026-07-02.md`.*
