# Flagged ("rejected") status audit — admin scrape field review

## Semantic clarification (source of truth)

The field-level `reviewer_status` state machine (`extracted_field_evidence`):

| status      | meaning                                                            | terminal? | promotion gate |
| ----------- | ------------------------------------------------------------------ | --------- | -------------- |
| `pending`   | admin hasn't reviewed (frontend fallback label: `unverified`)      | no        | blocking       |
| `verified`  | admin confirmed the extracted value is correct                     | yes       | **pass**       |
| `corrected` | admin replaced the value with a correction (non-null)              | yes       | **pass**       |
| `rejected`  | admin flagged value as wrong; correction owed before promotion     | **no**    | **blocking**   |

The backend already implements this correctly. The frontend mislabels
`rejected` as a peer of `verified` (terminal-resolved). **That is the bug.**
This PR is frontend-only — backend is correct as-is.

UI semantic for `rejected` / "flagged":

- Counts toward "unresolved" / "fields blocking promotion".
- Excluded from "Verify all" auto-action (admin explicitly chose to flag;
  do not bulk-override their judgement).
- Distinct visual treatment (existing destructive `badge blocker` token,
  label "Flagged — correction required") signalling action owed.
- Inline "Correct value" CTA so admin can transition rejected → corrected
  in one click without re-navigating.

## Backend confirmation (read-only — no changes)

All four pre-flight claims verified against
`app/backend/app/api/admin_scrape.py` and
`app/backend/app/scraping/promotion_gate.py`:

- `POST /admin/scrape/items/{id}/fields/{name}/reject` writes
  `reviewer_status="rejected"` and **requires notes** — 422 without
  (`admin_scrape.py:586-588`).
- `build_effective_extracted_data()` applies **only**
  `reviewer_status="corrected"` rows with non-null `corrected_value`;
  rejected rows are skipped (`admin_scrape.py:491-530`, guard at `:512`).
- `promotion_gate.py` accepts **only** `{"verified", "corrected"}` as
  valid evidence states (`_VERIFIED_STATUSES`, `promotion_gate.py:47`).
  Rejected does not count.
- `list_scrape_queue()` computes `unverified_fields` using **only**
  `{"verified", "corrected"}` as resolution; rejected fields stay in
  `unverified_fields` → `promotable=false` (`admin_scrape.py:1230`,
  also `:1315`, `:2097`).

The evidence-detail object surfaced to the frontend includes
`reviewer_notes` (`admin_scrape.py:1153`), so the flag reason can be
shown inline.

## Pre-flight grep results

Commands:

```
grep -rn '"rejected"\|reviewer_status.*rejected' app/frontend/src/features/admin/
grep -rn '"rejected"\|reviewer_status.*rejected' app/frontend/src/pages/admin/
```

### Field-level `reviewer_status` checks (the bug — IN SCOPE)

| file:line | context (what the check controls) | intended behavior in this PR |
| --------- | --------------------------------- | ---------------------------- |
| `features/admin/workflow/FieldReviewGroup.jsx:74` | `STATUS_BADGE.rejected` label/color — shows `badge neutral` "flagged" | Treat as terminal-but-blocking: relabel "Flagged — correction required" with existing destructive `badge blocker` token. |
| `features/admin/workflow/FieldReviewGroup.jsx:265` | "Verify all" pending filter — `rejected` excluded (correct) but `corrected` was NOT excluded (latent bug: would re-verify corrected fields) | Keep rejected excluded (explicit, with comment); also exclude `corrected`. Filter intent shifts to "exclude {verified, corrected, explicitly-flagged}". |
| `features/admin/workflow/FieldReviewGroup.jsx:275` | `anyUnresolved` — resolved set was `{verified, rejected}` (rejected wrongly treated as resolved; corrected wrongly omitted) | Resolved set becomes `{verified, corrected}`. Rejected now counts as unresolved. |

### Queue-item-level `status` checks (different domain — LEAVE ALONE)

These read `scrape_queue.status` (the candidate state machine:
`pending`/`approved`/`rejected`/`duplicate`/`merged`), **not** field
`reviewer_status`. A rejected *candidate* is genuinely terminal for the
queue row, so these are correct.

| file:line | context | decision |
| --------- | ------- | -------- |
| `features/admin/workflow/AdminProgressBar.jsx:60` | `queueItem.status === "rejected"` — candidate-level progress bar | leave alone (queue status, not field status) |
| `features/admin/workflow/AdminFixPanel.jsx:50` | `statusBadge(item)` — candidate status badge | leave alone (queue status) |
| `features/admin/workflow/AdminFixPanel.jsx:386` | `item.status === "rejected"` → show "Reopen for review" | leave alone (queue status) |
| `pages/admin/Scraper.jsx:42,63,288-290,439` | source-health / candidate-status filters & Promise.allSettled `.status` | leave alone (unrelated) |
| `pages/admin/OperationsConsole.jsx:23,39` | ops candidate status filter/badge | leave alone (unrelated) |
| `pages/admin/exam-intelligence/*`, `pages/admin/{Marketplace,Mentors,Copyright}.jsx`, `community/ResourcesReviewQueue.jsx`, `sources/SourceHealthBadge.jsx`, `exam-intelligence/*Table.jsx` | exam-intelligence / marketplace / mentors / copyright / source-health review queues — separate domains with their own state machines | leave alone (out of scope) |

### Blast-radius files checked but NOT modified

- `features/admin/workflow/AdminFixPanel.jsx` — overall progress/blockers
  derive from backend `item.unverified_fields` (`AdminFixPanel.jsx:130`),
  which already keeps rejected fields. No frontend-side resolved logic to
  fix. The two grep hits are queue-item status (above). **No change.**
- `features/admin/workflow/PromotionPreviewPanel.jsx` — reads
  `blocker.unverified_fields` from the backend gate. No field-level
  resolved logic. Grep found no matching pattern. **No change.**
- `features/admin/workflow/PostEligibilityReviewGroup.jsx` — quoted-`"rejected"`
  grep found no hit (it uses a bare `rejected:` object key at line 15).
  Its verify gate checks only `statusKey === "verified"` (line 50), so it
  does **not** treat rejected as resolved, and it has no count/"Verify all"
  aggregation. Its one interactive field is `requires_domicile`, which is
  explicitly out of scope for this PR, and its checkbox toggle already
  issues a `correct` action inline. **No change** (respects blast-radius
  gate).

## Scope summary

Edited: `features/admin/workflow/FieldReviewGroup.jsx` + new tests.
Backend, promotion_gate.py, admin_scrape.py, other field-action endpoints,
audit logging, and all queue-item-status checks are untouched.
