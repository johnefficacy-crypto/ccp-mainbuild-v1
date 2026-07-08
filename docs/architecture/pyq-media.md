# PYQ Media & Advanced Question Types (PR-11)

_Last updated: 2026-07-08_

Migration 223 shipped shared **text** stimuli (`passage` / `caselet` / `table`)
and explicitly deferred first-class media storage to PR-11. This is that lane.

## Slice 1 — media storage on `pyq_stimuli` (migration 233)

`public.pyq_stimuli` gains:

| Column | Purpose |
|---|---|
| `document_asset_id` | FK → `document_assets` — the stored image/chart/diagram binary. |
| `asset_locator` | jsonb page/region locator (`page_number`, `bbox`, …) for a crop within a larger asset. |
| `alt_text` | Accessibility (WCAG) text for the media. |

### Governance (mirrors the 223 posture)

- **Asset integrity** (`pyq_stimuli_media_guard`): a linked `document_asset_id`
  must be a live `admin_exam_intelligence` **image** asset — `scope =
  admin_exam_intelligence`, `document_kind = 'image'` (image/chart/diagram are
  stored as image binaries; non-media kinds are rejected), and `status` not in
  (`failed`, `archived`). Same posture as migration 186's provenance check for
  `pyq_papers.source_document_id`.
- **Fail-closed accessibility + renderability**: a media stimulus (`image` /
  `chart` / `diagram`) cannot be `reviewer_status='verified'` without `alt_text`
  **and** a linked image asset (`document_asset_id`). `content_text` is **not** a
  substitute — the renderer shows the asset or the alt-text fallback and never
  renders `content_text` for media, so a content_text-only "verified" media
  stimulus would reach attempts with its content omitted. Enforced on INSERT and
  UPDATE.
- **Re-review on media edit**: the 223 verified-content downgrade is extended so
  editing `alt_text` / `document_asset_id` / `asset_locator` on a verified
  stimulus forces it back to `needs_correction`.

Additive + idempotent; no importer or projection contract changes here.
Regression: `app/supabase/tests/regression_233_pyq_stimuli_media_assets.sql`
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

## Slice 1 — admin authoring (backend)

The exam-intelligence CMS stimulus endpoints (`admin_exam_intel_cms.py`,
`POST`/`PATCH /pyq-stimuli`) now author media stimuli:

- `_STIMULUS_TYPES_CREATABLE` includes `image` / `chart` / `diagram` (was
  text-only); `other` stays deferred (no authoring contract yet).
- The write allowlist accepts `document_asset_id`, `asset_locator`, `alt_text`.
- The endpoints pass the fields straight to the row; migration 233's
  `pyq_stimuli_media_guard()` enforces asset integrity (live
  `admin_exam_intelligence` `image` asset, not `failed`/`archived`) and the
  verify-time accessibility contract. Those guard raises are mapped to HTTP 422.
- `reviewer_status` is still never settable here — promotion stays with the
  review router; new media rows land `pending`.

Tests: `test_pyq_stimulus_review_api.py` (image create persists media fields;
patch to a media type allowed; `other` still 422; DB guard rejection → 422).

## Deferred (later PR-11 slices, out of scope here)

- **Asset upload flow** — an admin surface to upload the image binary to a
  `document_assets` row before linking it. Bounded by the no-new-surface rule
  and left for a dedicated slice.
- **Bulk importer** (`pyq_bulk_import.py`) media/advanced-type support — still
  fixed A–D MCQ; media stimuli come through the single-row CMS path above.
- Wiring the media fields (`asset_url`, `alt_text`) through the mock projection /
  attempt snapshot — that surface is owned by the PR-4 projection work; this
  slice lands the canonical model, authoring, and renderer only.
- Advanced answer runtimes (MSQ, integer/numeric input, descriptive) and their
  scorers — these depend on the mock runtime/scoring surface and are sequenced
  separately.
