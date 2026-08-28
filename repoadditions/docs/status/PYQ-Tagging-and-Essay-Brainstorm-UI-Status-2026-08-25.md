# PYQ tagging & essay brainstorm UI — status (2026-08-25)

## GS1–4 Mains PYQ topic tagging — COMPLETE

All years 2013–2025 tagged against the `topics` taxonomy via
`pyq_question_topic_tags`. **1031 / 1031 questions tagged**, zero
outstanding. Reusable workflow, per-year paper/question counts, and the 11
data-quality bugs found along the way are documented in the project doc
`claude/upsc-pyq-topic-tagging-status.md` (not in this repo — Claude
project knowledge). Nothing queued on this track.

## Essay-paper theme taxonomy — COMPLETE, LIVE in backend

Essays don't map to GS syllabus topics (they're argued through a theme, not
recalled against a syllabus point), so they got a separate taxonomy:

- Migration `265_essay_theme_taxonomy.sql` — adds `essay_themes`,
  `essay_pyq_tags`, `essay_brainstorm_blocks`. Applied to Supabase.
- Router endpoints (`/essay-themes`, `/essay-pyq-tags` — GET/POST/PATCH/
  DELETE, both registered in `_IMPORT_CONFIG` for `/bulk-import`) added to
  `app/backend/app/api/admin_exam_intel_cms.py`. Deployed to
  `ccp-api-demo.onrender.com`, commit `8c0743c`.
- **15 themes live** (11 active + 4 reserved, extensible for future years —
  see `claude/upsc-essay-topic-scheme.md`).
- **100 / 100 Essay PYQs tagged** (2013–2025), imported via `/bulk-import`.
  20 carry a `secondary_theme_id` for genuinely dual-theme questions.

`essay_brainstorm_blocks` exists but is **not seeded** — no content yet,
schema settled ahead of the UI work below.

**Update (2026-08-28) — schema/backend step done, not yet live-validated.**
Migration `266_essay_brainstorm_idea_canvas.sql` extends the table for the Idea
Canvas content model (three new `block_type` values — `vocab_term`,
`book_reference`, `stat_to_verify` — plus a nullable `lens` column carrying the
six mind-map branches) and closes 265's RLS gap. `app/backend/app/api/
essay_builder.py` adds the aspirant-facing CRUD (`/api/essay-brainstorm-blocks`,
own rows only) and a read-only verified-only `/api/essay-pyq-tags`. Migration
`267_essay_brainstorm_canvas_position.sql` follows it with the nullable
`canvas_x` / `canvas_y` coordinates the free-drag mind-map needs (both axes
move together; null means "not placed yet"). Applying 266 and 267 and proving
the deployed behaviour is gate `essay-builder-266-live-validation` in the
operator-validation registry.

Two consequences worth knowing before the UI work:
- The 100 imported essay PYQ tags were forced to `reviewer_status='pending'` by
  the CMS bulk-import trust gate, so the aspirant-facing `/api/essay-pyq-tags`
  read correctly returns an empty list until they are promoted to `verified`.
- Seed content strategy (system-authored starter blocks vs. aspirant-populated
  only) is still an open decision; the endpoints work correctly with zero rows.

## New this session: essay brainstorm UI concept mockup (not built, not wired)

Design exploration for the essay brainstorming tool. Source under
`docs/design/essay-idea-and-spine-builder/`, also published as a live
click-through preview (see `docs/design/README.md` for the link). Not
connected to real data or a real endpoint yet.

**Essay idea canvas + spine builder** — freeform theme mind-map with a
vocab/quote/book/example helper panel, feeding into a word-counted intro →
body → conclusion sequencer. Maps directly onto the `essay_brainstorm_blocks`
schema above.

Two other concepts (a syllabus "constellation map" star-view, and an essay
"tug-of-war" argument-balance tool) were explored alongside this one but
are not being pursued — not included here.

## Known gap blocking real syllabus-progress tracking

Flagged while reviewing an unrelated requirements doc against this repo
(full notes in project doc `claude/syllabus-mastery-tracking-notes.md`):

- The "365 micro-themes" already exist as `topics` rows with
  `level='microtopic'` (see `scripts/ingest_upsc_gs_syllabus.py` and
  `docs/reference/syllabus/upsc_cse_mains_gs_micro_themes_v2026.3.json`) —
  no new table needed for that part.
- No `estimated_hours` (or equivalent) column exists anywhere on `topics`.
  Any 12-week/adaptive scheduling math has no data source until this is
  added, with real per-microtopic hour estimates supplied.
- Mastery is currently a continuous 0–100 `mastery_score`
  (`_HIGH_YIELD_MASTERED_THRESHOLD = 75.0` in `report_cards.py`), not a
  discrete state enum. Reconcile before building any syllabus-progress UI
  on top of either model. (Not a blocker for the essay tooling below —
  that's a separate track.)

## Next step

Nothing queued on PYQ tagging or the essay taxonomy — both complete. The
`essay_brainstorm_blocks` schema/backend step is done (see the update above);
what remains is the Idea Canvas / Spine frontend against those endpoints, the
seed-content decision, and the live validation of migration 266.
