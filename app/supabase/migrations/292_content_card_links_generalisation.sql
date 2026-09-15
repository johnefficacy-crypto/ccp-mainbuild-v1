-- 292_content_card_links_generalisation.sql
--
-- CONTENT-02 — generalise the three content-card junction tables into one.
--
-- Follow-up to migration 291, which merged the two content authorities into
-- `content_cards` and left three near-identical link tables behind. PR #1120
-- recorded that as a problem only half-moved: three junctions, each with its own
-- hard FK pair and no discriminator, carrying the same "add a type, copy a
-- table" pressure the content merge had just removed.
--
-- Applied version = MAX(filesystem)+1 at authoring (291). Reconcile against the
-- deployed state with:
--   SELECT MAX(version) FROM schema_migrations;
-- before applying to any environment. Migrations are immutable once merged.
--
-- WHAT THIS DOES
-- --------------
-- A. content_card_links — one reviewed link table for every card type and both
--    link targets.
-- B. Data move — count-agnostic INSERT ... SELECT from all three sources, ids
--    preserved.
-- C. The three source tables dropped.
--
-- HOW THE TARGET IS DISCRIMINATED, AND WHY NOT target_type + target_id
-- --------------------------------------------------------------------
-- The three sources had two distinct left-hand parents:
--
--   quant_question_heuristics      question_id  -> mock_question_bank
--   reasoning_question_strategies  question_id  -> mock_question_bank
--   reasoning_stimulus_strategies  stimulus_id  -> pyq_stimuli
--
-- The first two were column-for-column identical after 291's repoint; the third
-- differed in exactly one column. So this is two target kinds, not three link
-- shapes.
--
-- A textbook polymorphic association — `target_type text` + `target_id uuid` —
-- is REJECTED here. PostgreSQL cannot foreign-key one column at two tables, so
-- that shape buys its generality by giving up referential integrity: a deleted
-- question would leave a link pointing at nothing, and nothing in the database
-- would say so. Both sources cascade on delete today and that must survive.
--
-- Instead this uses two NULLABLE typed FK columns with a CHECK that exactly one
-- is set. Both FKs stay real, both cascades stay real, and the "exactly one" rule
-- is enforced by the database rather than by convention. This is already the
-- house shape for a discriminated target: writing_prompt_targets (migration 214)
-- picks one of {global, family, exam, phase} with
-- `CHECK num_nonnulls(exam_family_id, exam_id, exam_phase_id) + (is_global)::int = 1`,
-- and content_cards itself scopes with a nullable topic_id/microtopic_id pair.
--
-- Adding a THIRD target kind is then one nullable FK column plus one term in the
-- CHECK — a small, reviewable migration that keeps integrity — rather than a
-- fourth copy of the table. Adding a new CARD TYPE needs nothing here at all,
-- which is the point: card type lives on content_cards.content_type, and this
-- table never mentions it.
--
-- WHAT DOES NOT CHANGE
-- --------------------
-- relevance, reviewer_status (the link's OWN three-value lifecycle, distinct
-- from the card's four-value one), reviewed_by, reviewed_at and created_at are
-- carried over unchanged, as are the per-target uniqueness rules and the
-- service-role-only posture.
--
-- CONSEQUENCE, STATED PLAINLY
-- ---------------------------
-- After 291 the two subjects still had separate LINK tables, so a link-table
-- outage stayed subject-local. That is now gone too: one table backs both. What
-- survives is code-level isolation — study_os.solution_strategies reads each
-- subject through its own reader inside its own try/except, so one subject's
-- read failing still yields empty strategies for that subject rather than
-- failing the response. Storage-level isolation between the two subjects no
-- longer exists at any layer.

begin;

-- ═════════════════════════════════════════════════════════════════════════
-- A. The merged link table
-- ═════════════════════════════════════════════════════════════════════════

create table if not exists public.content_card_links (
  id uuid primary key default gen_random_uuid(),
  card_id uuid not null references public.content_cards(id) on delete cascade,
  -- EXACTLY ONE target must be set (CHECK below). Both stay real FKs with real
  -- cascades; see the header for why this is not target_type + target_id.
  question_id uuid references public.mock_question_bank(id) on delete cascade,
  stimulus_id uuid references public.pyq_stimuli(id) on delete cascade,
  relevance text not null default 'primary'
    check (relevance in ('primary', 'secondary', 'related')),
  -- The LINK's own lifecycle. Three values, not the card's four: a link is never
  -- 'needs_correction' — an unsound link is rejected and re-made, not revised.
  -- Carried over from 243/262/263 unchanged.
  reviewer_status text not null default 'pending'
    check (reviewer_status in ('pending', 'verified', 'rejected')),
  reviewed_by uuid references auth.users(id) on delete set null,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  constraint content_card_links_one_target
    check (num_nonnulls(question_id, stimulus_id) = 1)
);

comment on table public.content_card_links is
  'Reviewed links from a content_card to exactly one target (a bank question or a PYQ stimulus). Merges quant_question_heuristics, reasoning_question_strategies and reasoning_stimulus_strategies (migration 292). Card TYPE is not represented here — it lives on content_cards.content_type.';
comment on constraint content_card_links_one_target on public.content_card_links is
  'Exactly one target column is set. Two nullable typed FKs rather than target_type+target_id, so both foreign keys and both delete cascades stay real.';

-- Replaces unique (question_id, heuristic_id) and unique (stimulus_id, strategy_id).
-- Partial, because the unused target column is NULL on every row and a plain
-- UNIQUE would not constrain the pairs the sources constrained.
create unique index if not exists content_card_links_question_card_uidx
  on public.content_card_links(question_id, card_id)
  where question_id is not null;
create unique index if not exists content_card_links_stimulus_card_uidx
  on public.content_card_links(stimulus_id, card_id)
  where stimulus_id is not null;

create index if not exists idx_ccl_card            on public.content_card_links(card_id);
create index if not exists idx_ccl_question        on public.content_card_links(question_id) where question_id is not null;
create index if not exists idx_ccl_stimulus        on public.content_card_links(stimulus_id) where stimulus_id is not null;
create index if not exists idx_ccl_reviewer_status on public.content_card_links(reviewer_status);

-- ═════════════════════════════════════════════════════════════════════════
-- B. Data move — count-agnostic
-- ═════════════════════════════════════════════════════════════════════════
-- No row count is assumed. ids are preserved so nothing downstream that holds a
-- link id is invalidated.

insert into public.content_card_links
  (id, card_id, question_id, stimulus_id, relevance, reviewer_status,
   reviewed_by, reviewed_at, created_at)
select l.id, l.card_id, l.question_id, null::uuid, l.relevance, l.reviewer_status,
       l.reviewed_by, l.reviewed_at, l.created_at
from public.quant_question_heuristics l;

insert into public.content_card_links
  (id, card_id, question_id, stimulus_id, relevance, reviewer_status,
   reviewed_by, reviewed_at, created_at)
select l.id, l.card_id, l.question_id, null::uuid, l.relevance, l.reviewer_status,
       l.reviewed_by, l.reviewed_at, l.created_at
from public.reasoning_question_strategies l;

insert into public.content_card_links
  (id, card_id, question_id, stimulus_id, relevance, reviewer_status,
   reviewed_by, reviewed_at, created_at)
select l.id, l.card_id, null::uuid, l.stimulus_id, l.relevance, l.reviewer_status,
       l.reviewed_by, l.reviewed_at, l.created_at
from public.reasoning_stimulus_strategies l;

-- Row-for-row assertion. Fails the transaction rather than landing a partial
-- move, and checks the target column actually landed on the right side — a bare
-- count would pass a question/stimulus mix-up.
do $$
declare
  v_src bigint;
  v_dst bigint;
  v_bad bigint;
begin
  select (select count(*) from public.quant_question_heuristics)
       + (select count(*) from public.reasoning_question_strategies)
       + (select count(*) from public.reasoning_stimulus_strategies)
    into v_src;
  select count(*) into v_dst from public.content_card_links;
  if v_dst <> v_src then
    raise exception 'content_card_links migration: row count mismatch src=% dst=%', v_src, v_dst;
  end if;

  select count(*) into v_bad
  from public.quant_question_heuristics s
  where not exists (
    select 1 from public.content_card_links t
    where t.id = s.id and t.card_id = s.card_id
      and t.question_id = s.question_id and t.stimulus_id is null
      and t.relevance = s.relevance and t.reviewer_status = s.reviewer_status);
  if v_bad > 0 then
    raise exception 'content_card_links migration: % quant link(s) did not round-trip', v_bad;
  end if;

  select count(*) into v_bad
  from public.reasoning_question_strategies s
  where not exists (
    select 1 from public.content_card_links t
    where t.id = s.id and t.card_id = s.card_id
      and t.question_id = s.question_id and t.stimulus_id is null
      and t.relevance = s.relevance and t.reviewer_status = s.reviewer_status);
  if v_bad > 0 then
    raise exception 'content_card_links migration: % reasoning question link(s) did not round-trip', v_bad;
  end if;

  select count(*) into v_bad
  from public.reasoning_stimulus_strategies s
  where not exists (
    select 1 from public.content_card_links t
    where t.id = s.id and t.card_id = s.card_id
      and t.stimulus_id = s.stimulus_id and t.question_id is null
      and t.relevance = s.relevance and t.reviewer_status = s.reviewer_status);
  if v_bad > 0 then
    raise exception 'content_card_links migration: % stimulus link(s) did not round-trip', v_bad;
  end if;

  raise notice 'content_card_links: migrated % link row(s)', v_src;
end $$;

-- ═════════════════════════════════════════════════════════════════════════
-- C. Retire the source tables
-- ═════════════════════════════════════════════════════════════════════════
-- No CASCADE: if anything still depends on these, this migration must fail
-- loudly rather than silently dropping a dependant.

drop table if exists public.quant_question_heuristics;
drop table if exists public.reasoning_question_strategies;
drop table if exists public.reasoning_stimulus_strategies;

-- ═════════════════════════════════════════════════════════════════════════
-- D. RLS — service-role only, unchanged posture
-- ═════════════════════════════════════════════════════════════════════════

alter table public.content_card_links enable row level security;

do $$
begin
  execute 'revoke all on public.content_card_links from public';
  execute 'revoke all on public.content_card_links from anon';
  execute 'revoke all on public.content_card_links from authenticated';
  execute 'grant select, insert, update, delete on public.content_card_links to service_role';
  -- Admin/service-role only, exactly as the three source tables were. Learner
  -- delivery is served server-side and gates conjunctively on the card being
  -- verified AND active AND this link row being verified.
end $$;

commit;
