# PYQ Media & Advanced Question Types (PR-11)

_Last updated: 2026-07-08_

Migration 223 shipped shared **text** stimuli (`passage` / `caselet` / `table`)
and explicitly deferred first-class media storage to PR-11. This is that lane.

## Slice 1 — media storage on `pyq_stimuli` (migration 232)

`public.pyq_stimuli` gains:

| Column | Purpose |
|---|---|
| `document_asset_id` | FK → `document_assets` — the stored image/chart/diagram binary. |
| `asset_locator` | jsonb page/region locator (`page_number`, `bbox`, …) for a crop within a larger asset. |
| `alt_text` | Accessibility (WCAG) text for the media. |

### Governance (mirrors the 223 posture)

- **Asset integrity** (`pyq_stimuli_media_guard`): a linked `document_asset_id`
  must be a live `admin_exam_intelligence` asset (not `archived`) — same shape
  as migration 186's provenance check for `pyq_papers.source_document_id`.
- **Fail-closed accessibility**: a media stimulus (`image` / `chart` / `diagram`)
  cannot be `reviewer_status='verified'` without `alt_text` **and** real content
  (a linked asset or `content_text`). Enforced on INSERT and UPDATE.
- **Re-review on media edit**: the 223 verified-content downgrade is extended so
  editing `alt_text` / `document_asset_id` / `asset_locator` on a verified
  stimulus forces it back to `needs_correction`.

Additive + idempotent; no importer or projection contract changes here.
Regression: `app/supabase/tests/regression_232_pyq_stimuli_media_assets.sql`
(8 cases: asset scope/status integrity, both verify preconditions, compliant
verify, media-edit downgrade, non-media verify).

## Slice 1 — rendering (frontend)

`QuestionStimuli` (inside the existing mock attempt shell — **no new surface**,
per the no-new-surface rule) now renders media stimuli:

- `image` / `chart` / `diagram` with an `asset_url` → an `<img>` with `alt`
  = `alt_text`, lazy-loaded.
- A media stimulus with no resolvable `asset_url` → the `alt_text` shown as a
  text fallback (`role="img"` + `aria-label`), so the reference is never blank
  or inaccessible.
- Text stimuli (`passage` / `caselet` / `table`) are unchanged.

Backward-compatible: the component reads optional `asset_url` / `alt_text` off
the frozen stimulus snapshot and degrades gracefully when absent. Tests:
`QuestionRenderer.test.jsx` (image renders with alt; fallback when no URL; media
does not leak `content_text`).

## Deferred (later PR-11 slices, out of scope here)

- Importer support for media stimulus types and the asset upload flow.
- Wiring the media fields (`asset_url`, `alt_text`) through the mock projection /
  attempt snapshot — that surface is owned by the PR-4 projection work; this PR
  only lands the canonical model + the renderer's ability to display it.
- Advanced answer runtimes (MSQ, integer/numeric input, descriptive) and their
  scorers — these depend on the mock runtime/scoring surface and are sequenced
  separately.
