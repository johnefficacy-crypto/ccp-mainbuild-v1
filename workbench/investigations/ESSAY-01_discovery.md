# ESSAY-01 — Essay Builder discovery (read-only)

Scope: what exists today across the two essay routes, the
`essay_brainstorm_blocks` / `essay_themes` / `essay_pyq_tags` tables, and the
navigation into both surfaces. Findings only — no proposal.

Evidence is repository code at `origin/main` (`c6962d6`). Anything that can
only be answered from the live Supabase database is marked as such; this
session has no Supabase credentials and made no live query.

---

## 1. What each route renders

### `/app/study/essay` — Idea Canvas

Route: `app/frontend/src/routes/appRoutes.jsx:128`, a child of `/app/study`, so
it renders **inside `StudyShell`** and inside `RouteErrorBoundary`.

Component tree:

```
EssayIdeaCanvas            app/frontend/src/pages/study/EssayIdeaCanvas.jsx
├── ThemeSelector          features/study/essay/ThemeSelector.jsx      (when ?theme= is absent)
└── IdeaCanvas             features/study/essay/IdeaCanvas.jsx         (when ?theme= is present)
    ├── useEssayBlocks     features/study/essay/useEssayBlocks.js
    ├── Sticky (xN)        (local component inside IdeaCanvas.jsx)
    └── PyqTagsSidebar     features/study/essay/PyqTagsSidebar.jsx
```

Theme selection lives in the query string (`?theme=<uuid>&theme_name=<label>`),
so the canvas is deep-linkable and the selector is skipped once a theme is set.

Fetches:

| Component | Call |
| --- | --- |
| `ThemeSelector` | `GET /api/essay-themes` (raw `api.get`, own `useState`) |
| `useEssayBlocks` | `GET /api/essay-brainstorm-blocks?theme_id=<id>` |
| `useEssayBlocks` | `POST /api/essay-brainstorm-blocks` |
| `useEssayBlocks` | `PATCH /api/essay-brainstorm-blocks/{id}` (canvas_x + canvas_y) |
| `useEssayBlocks` | `DELETE /api/essay-brainstorm-blocks/{id}` |
| `PyqTagsSidebar` | `GET /api/essay-pyq-tags?theme_id=<id>` (raw `api.get`, own `useState`) |

What an aspirant can do:

- Pick a theme from the catalogue, or — if the themes fetch fails or returns
  zero rows — paste a raw `theme_id` UUID into a manual-entry input
  (`ThemeSelector.jsx:77-101`). The manual fallback is still in the code even
  though `GET /api/essay-themes` now exists and is registered
  (`app/backend/server.py:361`); the component's header comment still describes
  the endpoint as not existing.
- Select one of six lens branches (`essayConstants.js` `LENSES`).
- `+ add idea` on a branch → `window.prompt()` for free text → creates a block of
  type `argument_for` with that `lens`.
- Helper rail: five buttons (`vocab_term`, `quote`, `book_reference`, `example`,
  `stat_to_verify`). Clicking one creates a block of that type in the currently
  active lens, with `block_text` hard-set to the button's own label
  (`IdeaCanvas.jsx:124-131`) — there is no text entry for a helper block.
- Drag a sticky; one `PATCH` fires on mouse-up carrying both coordinates.
- Delete a sticky (`×`).
- Read the "Real questions on this theme" sidebar.

There is **no edit affordance** for block text on this surface — only create,
drag, delete.

### `/app/study/essay/spine/:themeId?` — Spine

Route: `appRoutes.jsx:141`, declared **outside** the `/app/study` parent route,
so it renders **without `StudyShell`** — no study chrome, no shared nav.

Component tree:

```
EssaySpine                 app/frontend/src/pages/study/EssaySpine.jsx
└── EssaySpineScreen       features/study/essay/EssaySpineScreen.jsx
    ├── useSpineBlocks     features/study/essay/useSpineBlocks.js
    │   └── useApiCollection x2
    ├── SpineSlot (x6)     features/study/essay/SpineSlot.jsx
    └── EmptyState / ErrorState / LoadingSkeleton (shared/ui)
```

Fetches — two reads on every mount (`useSpineBlocks.js:31-38`):

| Purpose | Call |
| --- | --- |
| Slot content | `GET /api/essay-brainstorm-blocks?theme_id=<id>` |
| Theme switcher | `GET /api/essay-brainstorm-blocks?limit=500` (unfiltered) |
| Create | `POST /api/essay-brainstorm-blocks` (`theme_id`, `block_type`, `block_text` only) |
| Edit | `PATCH /api/essay-brainstorm-blocks/{id}` (`block_text` only) |
| Delete | `DELETE /api/essay-brainstorm-blocks/{id}` |

With no theme selected the two reads are identical, by design and by comment.

What an aspirant can do:

- Pick from a list of theme **UUIDs** they already have blocks under — rendered
  as raw monospace ids, no names (`EssaySpineScreen.jsx:96-108`). The screen has
  no themes-endpoint call at all, so it cannot show a theme name and cannot
  start a brand-new theme.
- Write, edit and delete text in six slots across three sections: Hook, Thesis
  (Introduction); Supporting argument, Counter-consideration, Counter-narrative
  (Body); Closing thought (Conclusion).
- See a planned-word-count readout against a 1000–1200 target.
- See a read-only "From your brainstorm" list — see §2 for why it is always
  empty in practice.

Writes never send `lens` or canvas coordinates.

### Do their jobs overlap?

**Yes, on the read path; no, on the write path.**

- Both read the same endpoint with the same `theme_id` filter. Neither read
  filters by `lens` or `block_type` server-side.
- **The Idea Canvas renders Spine blocks.** `useEssayBlocks` fetches every block
  for the theme, and `IdeaCanvas` maps all of them to stickies. A Spine block has
  `lens === null`, so `positionFor()` falls through to the default
  `{x: 480, y: 420}` (`IdeaCanvas.jsx:22`) — every Spine block the aspirant has
  ever written for that theme stacks near the centre of the canvas, on top of the
  central theme node, with a jitter of up to 4 × 24px. They are draggable and
  deletable from the canvas.
- The Spine does **not** render Canvas blocks in its slots: `isSpineBlock()`
  filters to `lens == null` (`spineSlots.js:83-85`), and every Canvas-created
  block carries a lens.
- Write-side, the two surfaces have disjoint `block_type` sets (see §2), so
  neither creates content the other treats as its own.

The overlap is therefore one-directional and unintended-looking: the Canvas
is the one surface that shows both kinds of block.

---

## 2. `essay_brainstorm_blocks` — every read and write path

### Backend

`app/backend/app/api/essay_builder.py`, router prefix `/essay-brainstorm-blocks`,
mounted at `server.py:359`. Table constant `_TABLE = "essay_brainstorm_blocks"`.

| Method | Path | Auth dep | Notes |
| --- | --- | --- | --- |
| GET | `""` | `get_current_user` | filters `created_by`, optional `theme_id` / `lens` / `block_type`, `limit` 1–500 (default 200), ordered `created_at desc` |
| GET | `/{block_id}` | `get_current_user` | ownership-scoped; 404 for both "missing" and "not yours" |
| POST | `""` | `get_current_user_required_permanent` | rate-limited `essay_blocks.write` (60/60s) |
| PATCH | `/{block_id}` | `get_current_user_required_permanent` | rate-limited; `exclude_unset` semantics |
| DELETE | `/{block_id}` | `get_current_user_required_permanent` | rate-limited |

No other backend module touches the table. `admin_exam_intel_cms.py` covers
`essay_themes` and `essay_pyq_tags` only.

Every path goes through `get_supabase_admin()` (service-role) with an explicit
`.eq("created_by", user["id"])` on read, update and delete. RLS on the table is
**enabled with zero policies** and all privileges revoked from `anon` and
`authenticated` (migration 266 §3), so the FastAPI endpoints are the only way in.

`_shape()` never returns `created_by` or `metadata`; it does return
`linked_gs_topic_id`, `source_note` and `usage_count`.

### Frontend

Two independent data layers against the same endpoint, built on different
primitives:

- `useEssayBlocks.js` — bespoke `useState`/`useRef`, optimistic updates with
  rollback. Used by Idea Canvas only.
- `useSpineBlocks.js` — `useApiCollection` + `api.*`, server-confirmed refresh.
  Used by Spine only.

`ThemeSelector` and `PyqTagsSidebar` call `api.get` directly with their own
`useState`, bypassing both hooks (those are theme/tag reads, not block reads).

### `block_type` — enum vs. UI

Enum, 11 values (migration 266 CHECK constraint; mirrored by the `BlockType`
`Literal` in `essay_builder.py:64-76` and validated by Pydantic):

| block_type | Created by | Rendered by |
| --- | --- | --- |
| `hook` | Spine slot | Spine slot; Canvas (as an unpositioned sticky) |
| `thesis` | Spine slot | Spine slot; Canvas |
| `argument_for` | Spine slot **and** Canvas `+ add idea` | Spine slot (lens-null rows only); Canvas |
| `argument_against` | Spine slot | Spine slot; Canvas |
| `counter_narrative` | Spine slot | Spine slot; Canvas |
| `closing_thought` | Spine slot | Spine slot; Canvas |
| `example` | Canvas helper rail | Canvas only |
| `quote` | Canvas helper rail | Canvas only |
| `vocab_term` | Canvas helper rail | Canvas only |
| `book_reference` | Canvas helper rail | Canvas only |
| `stat_to_verify` | Canvas helper rail | Canvas only |

All 11 enum values are creatable somewhere. None is enum-only.

`argument_for` is the one value both surfaces write. The Canvas uses it as its
generic free-text idea type (`BRANCH_IDEA_BLOCK_TYPE`, `essayConstants.js:44`);
the Spine uses it as "Supporting argument". They do not collide in the Spine's
slots because the lens filter excludes the Canvas rows — but a Canvas
`argument_for` block and a Spine `argument_for` block are the same row type
distinguished only by whether `lens` is null.

### Dead path: `promotedBlocks`

`promotedBlocks()` (`spineSlots.js:103-107`) selects blocks with
`lens == null` whose `block_type` is **not** one of the six Spine types — i.e.
`example`, `quote`, `vocab_term`, `book_reference`, `stat_to_verify` with a
cleared lens. It powers the "From your brainstorm" section
(`EssaySpineScreen.jsx:169-186`).

**Nothing in the codebase produces such a row.** The Canvas always sets a lens
on create and never clears it; the Spine only creates the six slot types. There
is no promote action, no "send to spine" control, and no `PATCH` anywhere that
sends `lens: null`. The API supports clearing `lens` via an explicit null
(`BlockPatch` + `exclude_unset`), but no caller does it. The section is
therefore unreachable through the UI as shipped. Its own test
(`EssaySpineScreen.test.jsx:125`) confirms the section has no create affordance.

### Fields written / never written

| Column | Written by | Read/rendered by |
| --- | --- | --- |
| `theme_id` | both surfaces on create | Canvas header, Spine switcher |
| `block_type` | both on create | both |
| `block_text` | both on create; Spine on PATCH | both |
| `lens` | Canvas only, on create | Canvas (sticky colour + anchor); Spine (as a filter) |
| `canvas_x` / `canvas_y` | Canvas only, on drag-end PATCH | Canvas only |
| `created_by` | server, from the token | never returned |
| `linked_gs_topic_id` | never (see §3) | returned by the API; no component reads it |
| `source_note` | never written by any code path | returned by the API; no component reads it |
| `usage_count` | never written (defaults to 0) | returned by the API; no component reads it |
| `metadata` | never written | never returned |

---

## 3. `linked_gs_topic_id`

Every occurrence in the repository:

- `265_essay_theme_taxonomy.sql:75` — column definition, `uuid references public.topics(id) on delete set null`.
- `essay_builder.py` — present in `_SELECT` (`:58`), on `BlockCreate` (`:99`) and
  `BlockPatch` (`:113`), validated by `_require_topic()` (`:219-222`, must be a
  UUID and must exist in `topics`), written on create (`:306-315`), validated on
  patch (`:345-346`), and returned by `_shape()` (`:188`).
- `test_essay_builder.py:151` (expected shape, `None`), `:276` (a create test
  passing a topic id).
- `EssaySpineScreen.test.jsx:35` — a fixture field, `null`.
- `docs/status/coverage-pipeline-and-design-inventory-2026-08-27.md:207` — prose
  listing it as part of the schema.

**No frontend component sends it, and no frontend component reads it.** Neither
`useEssayBlocks` nor `useSpineBlocks` includes it in any payload; no JSX
references it; no other backend module reads it. It is fully plumbed through the
API contract (create, patch, validate, return) and terminates there.

It is a column with a working, validated, unused API surface. Nothing in the
product populates it, nothing renders it.

---

## 4. Seeding

**There is no seed script, fixture or admin path that creates brainstorm blocks.**

- Migration 265 states it explicitly: *"Not seeded by this migration -- no
  content exists yet"* (`265_essay_theme_taxonomy.sql:66-67`).
- Nothing under `scripts/` touches `essay_brainstorm_blocks` — the only
  references across the whole repo are the three migrations, `essay_builder.py`,
  the two test files, the frontend feature folder, and documentation.
- `admin_exam_intel_cms.py` has no `essay_brainstorm_blocks` route and no
  `_IMPORT_CONFIG` entry for it. Its `/bulk-import` config covers `essay-themes`
  and `essay-pyq-tags` only (`:4672-4701`).
- `test_migrations_contract.py:83` asserts that migration 267 contains no
  `update public.essay_brainstorm_blocks` — the migration is deliberately
  backfill-free.
- The API's `POST` handler always stamps `created_by` from the caller's token.
  There is no service-authored path with a different owner.

**Aspirants are the only writers.** Every row in the table originates from a
`POST /api/essay-brainstorm-blocks` made by the aspirant who owns it, from one
of the two essay surfaces.

The status doc records this as an open decision, not an omission: *"Seed content
strategy (system-authored starter blocks vs. aspirant-populated only) is still an
open decision"*
(`repoadditions/docs/status/PYQ-Tagging-and-Essay-Brainstorm-UI-Status-2026-08-25.md`).

---

## 5. `essay_themes`

### RLS state

**No row level security is enabled on `essay_themes`.** Migration 265 creates it
with a primary key, a unique constraint on `theme_code`, a `status` index, and
nothing else — no `enable row level security`, no policies, no `revoke`, no
`grant`. Grepping all migrations for RLS/grant/revoke statements naming
`essay_themes` returns nothing.

Migration 266 §3 states the exclusion deliberately: it locks down
`essay_brainstorm_blocks` and notes *"`essay_themes` / `essay_pyq_tags` are
deliberately NOT touched here — they are shared admin-reviewed reference data
with a live admin CMS surface, and re-gating them is a separate change."*

The same is true of `essay_pyq_tags` — created in 265, no RLS anywhere.

So both tables sit at whatever the database's default grants for `anon` /
`authenticated` are. That has not been proven live; the Essay Builder
operator-validation gate (`essay-builder-266-live-validation`) is
`validation_pending` with blockers recording that migrations 266 and 267 are not
yet applied in the target environment
(`docs/operator-validation/registry.json:502-527`).

### `parent_theme_id` exposure

`parent_theme_id` is a self-referential nullable FK
(`265_essay_theme_taxonomy.sql:20`).

- **Aspirant endpoint `GET /api/essay-themes`: not exposed.** The select list is
  explicitly `"id, theme_code, theme_name, description, status"`
  (`essay_builder.py:411-413`), and the response is rebuilt field-by-field from
  those five keys (`:416-424`). The docstring states the exclusion of authoring
  fields as intentional.
- **Admin CMS `GET /api/admin/exam-intelligence-cms/essay-themes`: exposed for
  write, and validated.** `_ESSAY_THEME_FIELDS` includes `parent_theme_id`; the
  create endpoint validates that the referenced parent exists
  (`admin_exam_intel_cms.py:3524`), and the bulk-import config notes the seed
  batch lists parents before children (`:4677-4681`).

So the hierarchy exists in the schema and is writable by admins, but no
aspirant-facing endpoint returns it, and no frontend component references it.
The `ThemeSelector` renders a flat grid.

### Which of the 15 themes have tagged PYQs

**Not determinable from the repository.** The 15 themes and the 100 PYQ tags
exist only as rows in Supabase — there is no `essay_themes.json`, no seed SQL,
and no fixture in this repo. (`admin_exam_intel_cms.py:4679` refers to an
`essay_themes.json` that is not checked in.) This session has no Supabase
credentials and made no live query.

What the repository does record
(`repoadditions/docs/status/PYQ-Tagging-and-Essay-Brainstorm-UI-Status-2026-08-25.md`):

- 15 themes live: 11 `active`, 4 `reserved`.
- 100 / 100 Essay PYQs (2013–2025) tagged and imported via `/bulk-import`.
- 20 of those carry a `secondary_theme_id`.
- The full theme-by-theme scheme lives in a Claude project doc
  (`claude/upsc-essay-topic-scheme.md`), **not in this repo**.

One thing is determinable from code regardless of the per-theme distribution:
**no theme currently surfaces any PYQ to an aspirant.** `/bulk-import` forces
`reviewer_status: "pending"` on every imported tag
(`admin_exam_intel_cms.py:4689`), and the aspirant read filters
`.eq("reviewer_status", "verified")` (`essay_builder.py:459`). Until those 100
tags are promoted, `GET /api/essay-pyq-tags` returns an empty list for every
theme — which the sidebar is written to expect and renders as a calm "not yet
available" note.

Answering the per-theme split requires a live query against `essay_pyq_tags`
grouped by `theme_id` (and `secondary_theme_id`), joined to `essay_themes`.

---

## 6. `essay_pyq_tags` — what reads it

Three read paths, one aspirant-facing:

1. **`GET /api/essay-pyq-tags`** (`essay_builder.py:441-519`) — shared reference
   data, no ownership scoping, any authenticated caller. Verified-only enforced
   conjunctively across three tables: the tag (`reviewer_status = 'verified'`),
   its `pyq_questions` row (`reviewer_status = 'verified'`), and that question's
   `pyq_papers` row (`trust_status = 'verified'`). A tag whose question or paper
   fails the check is dropped from the response, not just unjoined
   (`:501-508`). Optional `theme_id` filter, `limit` 1–200. `in_()` filters are
   chunked at 250 ids for the PostgREST URL ceiling.
2. **Admin CMS** (`admin_exam_intel_cms.py:3582-3690`) — full GET / POST / PATCH
   / DELETE plus a `/bulk-import` entry, behind the `exam_intelligence.cms`
   permission and the admin Study OS flag, with audit entries on every write.
3. Nothing else. No report, no analytics read, no other API module.

**Exactly one frontend surface reads it: `PyqTagsSidebar`**, rendered only inside
`IdeaCanvas` (`IdeaCanvas.jsx:257`), i.e. only on `/app/study/essay` and only
once a theme is selected. It calls `GET /api/essay-pyq-tags?theme_id=` directly
via `api.get`.

The Spine never reads it. No admin React surface reads it either — there is no
frontend component calling the admin CMS essay-tag routes.

The sidebar renders `year` and `question_text` per tag. The API also returns
`theme_id`, `secondary_theme_id`, `essay_type`, `quote_source_type` and
`question_number`; none of those reach the screen.

---

## 7. Routing — links between the two surfaces, and nav

### Internal links between the two essay routes

**There are none, in either direction.**

Every occurrence of the string `study/essay` outside the essay feature folder
itself:

| Location | What it is |
| --- | --- |
| `appRoutes.jsx:128` | route definition, `/app/study/essay` |
| `appRoutes.jsx:141` | route definition, `/app/study/essay/spine/:themeId?` |
| `pages/study/StudyLearningHub.jsx:41` | `to: "/app/study/essay"` — a hub card |
| `features/study/essay/__tests__/EssayIdeaCanvas.test.js:37,166` | test `MemoryRouter` entries |

No `<Link>`, `navigate()`, `<a href>`, redirect or button in `IdeaCanvas.jsx`,
`EssayIdeaCanvas.jsx`, `ThemeSelector.jsx` or `PyqTagsSidebar.jsx` points at the
Spine. No such link in `EssaySpineScreen.jsx`, `EssaySpine.jsx` or
`SpineSlot.jsx` points back at the Canvas.

The two screens' own comments state this as known: the Canvas route comment says
*"Spine is the deliberate next task this unblocks"* (`appRoutes.jsx:126-127`),
and `EssaySpineScreen.jsx:32-33` says *"Theme selection is intentionally
self-contained… Stitching the two screens into one flow is a separate task."*

The only connection between them is the **shared data**: the Spine's unfiltered
`limit=500` theme scan lists any theme the aspirant has a block under, so a theme
first created on the Canvas will appear in the Spine's switcher — as a bare UUID.
That is a data-level consequence, not a link.

### Nav entries

**Neither route appears in any sidebar or navigation config.** Grepping the shell
and layout components (`shared/layouts/`, `StudyShell.jsx`, `AdminShell.jsx`,
`DashShell.jsx`) for "essay" returns nothing. This matches the no-new-surface
rule the route comment cites.

The single navigational entry point in the entire app is the **"Essay canvas"**
card on the Learning Hub (`/app/study/learning`), `StudyLearningHub.jsx:36-42`:

```
title:       "Essay canvas"
description: "Brainstorm an essay theme across six thematic lenses."
to:          "/app/study/essay"
icon:        PenLine
```

### A user's path into each surface

**`/app/study/essay` (Idea Canvas):**

1. Sidebar → Learning (`/app/study/learning`) → "Essay canvas" card.
2. Lands on `ThemeSelector` (no `?theme=`).
3. Picks an `active` theme (`reserved` themes render disabled), or — if
   `GET /api/essay-themes` fails or returns zero rows — types a raw UUID into the
   manual-entry fallback.
4. `?theme=<id>&theme_name=<name>` is set; `IdeaCanvas` mounts.

**`/app/study/essay/spine/:themeId?` (Spine):**

**There is no path.** No nav entry, no hub card, no link from the Canvas, no
link from anywhere else in the application. The route resolves if typed or
bookmarked, and its test file drives it via `MemoryRouter`, but there is no
in-product route to it.

If reached directly without a `:themeId`, the screen shows either an
`EmptyState` ("No essay theme yet") or a list of raw theme UUIDs the aspirant
already has blocks under. It renders without `StudyShell`, so it also has no
sidebar to navigate away from.

---

## Cross-cutting facts

- `GET /api/essay-themes` exists and is mounted (`server.py:361`), but two
  places still describe it as absent: `ThemeSelector.jsx:8-10` (*"there is no
  aspirant-facing essay-themes list endpoint yet"*) and
  `EssaySpineScreen.jsx:35-41` (*"KNOWN GAP: there is no aspirant-facing endpoint
  that lists `essay_themes`"*). The Canvas calls it anyway and works; the Spine
  does not call it and still renders bare UUIDs.
- Operator gate `essay-builder-266-live-validation` is `validation_pending`,
  `review_by` `2026-09-25T18:00:00Z`, zero evidence records, with blockers
  recording that migrations 266 and 267 are not applied live and that
  cross-aspirant isolation has only been proven against a stubbed Supabase
  client.
- The two surfaces use different shared-UI vocabularies: the Spine uses
  `EmptyState` / `ErrorState` / `LoadingSkeleton` and `useApiAction`; the Canvas
  hand-rolls its loading, error and mutation-error states and uses
  `window.prompt` and `window.confirm`-free inline deletes.
