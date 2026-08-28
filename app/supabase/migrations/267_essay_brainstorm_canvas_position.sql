-- 267_essay_brainstorm_canvas_position.sql
-- Adds free-drag canvas coordinates to `essay_brainstorm_blocks`.
--
-- Migration 266 gave an Idea Canvas block its `lens` (which of the six
-- mind-map branches it hangs off) but nothing about WHERE on the canvas it
-- sits. The mockup
-- (`repoadditions/docs/design/essay-idea-and-spine-builder/IdeaCanvas.dc.html`)
-- is a free-drag mind map, not a set of fixed lens-grouped sections: every
-- sticky carries its own position and is rendered as
-- `left:${x}px; top:${y}px` (IdeaCanvas.dc.html:236), moved by accumulating
-- pointer deltas `dx = e.clientX - lastX` (:245-248). So position is real
-- per-block state the aspirant authors, and it needs real columns.
--
-- Type choice — `numeric(10,2)`:
--   * Signed. Nothing in the mockup clamps a drag, so a sticky can be dragged
--     to a negative coordinate; the canvas only `overflow:hidden`s it (:39).
--   * Fractional. `clientX`/`clientY` are doubles, so accumulated deltas are
--     sub-pixel on zoomed / HiDPI displays. 0.01px resolution is far finer
--     than the UI can express, so nothing an aspirant does is rounded away.
--   * Exact decimal rather than a float type, so a value round-trips through
--     PostgREST and back unchanged instead of drifting on repeated drags.
--   * ±99,999,999.99 leaves room for any future pan/zoom coordinate space
--     without ever being the thing that has to change.
-- Matches the repo's habit of declaring precision on numeric columns
-- (cf. `essay_pyq_tags.confidence_score numeric(4,3)`, migration 265).
--
-- Deliberately NO bound on the values themselves. Canvas size, pan and zoom
-- are frontend concerns that will change; hard-coding 1440x900 into the
-- database would make the schema a hostage to a CSS decision.
--
-- Nullable, and null is a permanently valid state — not a migration
-- placeholder: Spine-stage blocks (lens IS NULL) never live on the canvas at
-- all, and an Idea Canvas block exists from the moment it is created, which
-- can precede the aspirant actually placing it.
--
-- RLS: nothing to do here, and that is verified rather than assumed.
-- Migration 266 §3 enabled row level security on this table and set
-- TABLE-level privileges (`revoke all ... from anon/authenticated`,
-- `grant select, insert, update, delete ... to service_role`). RLS is a
-- per-table property, and a table-level grant automatically extends to
-- columns added later — only column-level grants would need re-issuing, and
-- this repo issues none anywhere. So `canvas_x` / `canvas_y` are born under
-- the same service-role-only posture as every other column on the table.

alter table public.essay_brainstorm_blocks
  add column if not exists canvas_x numeric(10,2);

alter table public.essay_brainstorm_blocks
  add column if not exists canvas_y numeric(10,2);

-- A position is one point, so the pair is meaningful only together: a row
-- with x but no y cannot be rendered (the frontend would have no `top` to
-- write) and is not a state any interaction can produce — the mockup's drag
-- handler moves both axes in the same update (:247) and both seeding paths
-- set both (:215, :226). This constraint is about that null-consistency, not
-- about where on the canvas a block may sit.
alter table public.essay_brainstorm_blocks
  drop constraint if exists essay_brainstorm_blocks_canvas_position_check;

alter table public.essay_brainstorm_blocks
  add constraint essay_brainstorm_blocks_canvas_position_check
  check ((canvas_x is null) = (canvas_y is null));

notify pgrst, 'reload schema';
