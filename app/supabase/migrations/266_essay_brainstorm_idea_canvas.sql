-- 266_essay_brainstorm_idea_canvas.sql
-- Extends `essay_brainstorm_blocks` (migration 265, unseeded) to carry the
-- Idea Canvas content model from the essay idea-and-spine-builder mockup
-- (`repoadditions/docs/design/essay-idea-and-spine-builder/IdeaCanvas.dc.html`).
--
-- Two gaps in the 265 schema:
--
--   1. `block_type` covered the Spine screen only (hook -> thesis -> body ->
--      counter -> closing). The Idea Canvas helper rail also drops Vocabulary,
--      Books & authors, and Stats-to-verify cards onto the canvas. "Quotes" and
--      "Examples" already map onto the existing `quote` / `example` values, so
--      only three new values are needed.
--   2. There was no column at all for WHICH mind-map branch a card hangs off.
--      The canvas organises every sticky under one of six thematic lenses; the
--      values below are the six branch labels exactly as an aspirant reads them
--      on the canvas, snake_cased (not the mockup's internal JS keys
--      econ/global/gov/personal/equity/historical).
--
-- `lens` is nullable on purpose: Spine-stage blocks (hook / thesis /
-- closing_thought ...) are not attached to a branch. Lens is Idea-Canvas-only.
--
-- Also closes an RLS gap: 265 created `essay_brainstorm_blocks` with no row
-- level security, leaving one aspirant's private notes reachable by any other
-- through PostgREST. The table is locked to service_role only (see §3);
-- per-aspirant ownership is enforced by the API's `created_by` scoping.
-- `essay_themes` / `essay_pyq_tags` are deliberately NOT touched here — they
-- are shared admin-reviewed reference data with a live admin CMS surface, and
-- re-gating them is a separate change.

-- ── 1. block_type: add the Idea Canvas resource types ──────────────────────
-- 265 declared block_type with an inline column CHECK, so the constraint
-- carries Postgres' generated name. Discover it rather than assuming, then
-- replace it with an explicitly named one.
do $$
declare
  con_name text;
begin
  select c.conname into con_name
  from pg_constraint c
  join pg_class t on t.oid = c.conrelid
  join pg_namespace n on n.oid = t.relnamespace
  where n.nspname = 'public'
    and t.relname = 'essay_brainstorm_blocks'
    and c.contype = 'c'
    and pg_get_constraintdef(c.oid) ilike '%block_type%'
  limit 1;

  if con_name is not null then
    execute format(
      'alter table public.essay_brainstorm_blocks drop constraint %I', con_name
    );
  end if;
end $$;

alter table public.essay_brainstorm_blocks
  add constraint essay_brainstorm_blocks_block_type_check
  check (block_type in (
    -- Spine stages (unchanged, from 265)
    'hook', 'thesis', 'argument_for', 'argument_against',
    'example', 'quote', 'counter_narrative', 'closing_thought',
    -- Idea Canvas helper-rail resource types (new)
    'vocab_term', 'book_reference', 'stat_to_verify'
  ));

-- ── 2. lens: which mind-map branch the card hangs off ──────────────────────
alter table public.essay_brainstorm_blocks
  add column if not exists lens text;

alter table public.essay_brainstorm_blocks
  drop constraint if exists essay_brainstorm_blocks_lens_check;

alter table public.essay_brainstorm_blocks
  add constraint essay_brainstorm_blocks_lens_check
  check (lens is null or lens in (
    'economic_efficiency',        -- "Economic Efficiency"
    'global_comparative',         -- "Global & Comparative"
    'governance_implementation',  -- "Governance & Implementation"
    'personal_onground',          -- "Personal & On-ground"
    'social_equity_access',       -- "Social Equity & Access"
    'historical_precedent'        -- "Historical Precedent"
  ));

-- Canvas reads are "my blocks for this theme, optionally on this branch".
create index if not exists idx_essay_brainstorm_blocks_owner
  on public.essay_brainstorm_blocks(created_by, theme_id);

create index if not exists idx_essay_brainstorm_blocks_lens
  on public.essay_brainstorm_blocks(theme_id, lens)
  where lens is not null;

-- ── 3. RLS: close the gap left by 265 ─────────────────────────────────────
-- Migration 265 created this table with no row level security at all, so the
-- anon/authenticated PostgREST roles could reach every aspirant's private
-- brainstorm rows. Every legitimate path goes through the FastAPI Essay
-- Builder endpoints on the service-role client, which scope reads and writes
-- to `created_by = <caller>`. So this follows the hardened contract set by
-- migration 195 §4 and reaffirmed by 195 §5c: RLS on, ZERO client policies,
-- no direct anon/authenticated privileges. service_role bypasses RLS and
-- remains the only way in. Adding an owner INSERT/UPDATE policy later would
-- re-open direct PostgREST writes (forged `usage_count`, `metadata`, or
-- `source_note` on a row the API never validated) for no gain — the frontend
-- has no reason to bypass its own endpoints.
alter table public.essay_brainstorm_blocks enable row level security;

revoke all on public.essay_brainstorm_blocks from public;
revoke all on public.essay_brainstorm_blocks from anon;
revoke all on public.essay_brainstorm_blocks from authenticated;
grant select, insert, update, delete on public.essay_brainstorm_blocks to service_role;

notify pgrst, 'reload schema';
