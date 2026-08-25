-- 265_essay_theme_taxonomy.sql
-- Essay-paper theme taxonomy: separate from the GS1-4 topics/subjects tree
-- (essays are argued through a theme, not recalled against a syllabus point
-- -- tagging them onto `topics` would be a category error). Adds:
--   - essay_themes            (the ~11 active + reserved theme catalog)
--   - essay_pyq_tags          (question -> theme, mirrors pyq_question_topic_tags)
--   - essay_brainstorm_blocks (draggable canvas cards for the essay-builder UI;
--                              seeded later, schema settled now)
--
-- See project doc claude/upsc-essay-topic-scheme.md for the full design
-- rationale and the theme-by-theme boundary rules.

create table if not exists public.essay_themes (
  id uuid primary key default gen_random_uuid(),
  theme_code text not null unique,
  theme_name text not null,
  description text,
  parent_theme_id uuid references public.essay_themes(id) on delete set null,
  status text not null default 'reserved'
    check (status in ('active', 'reserved')),
  first_seen_year integer,
  sort_order integer not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_essay_themes_status
  on public.essay_themes(status);

create table if not exists public.essay_pyq_tags (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references public.pyq_questions(id) on delete cascade,
  theme_id uuid not null references public.essay_themes(id) on delete restrict,
  secondary_theme_id uuid references public.essay_themes(id) on delete set null,
  essay_type text not null default 'quote_abstract'
    check (essay_type in ('quote_abstract', 'issue_concrete')),
  quote_source_type text
    check (quote_source_type is null or quote_source_type in (
      'indian_thinker', 'western_philosopher', 'proverb', 'literary',
      'political_leader', 'other'
    )),
  tagging_source text not null default 'manual'
    check (tagging_source in ('manual', 'admin', 'ai', 'rule', 'imported')),
  confidence_score numeric(4,3) not null default 0 check (confidence_score >= 0 and confidence_score <= 1),
  reviewer_status text not null default 'pending'
    check (reviewer_status in ('pending', 'verified', 'rejected', 'needs_correction')),
  reviewed_by uuid references public.profiles(id) on delete set null,
  reviewed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(question_id, theme_id)
);

create index if not exists idx_essay_pyq_tags_question
  on public.essay_pyq_tags(question_id);

create index if not exists idx_essay_pyq_tags_theme
  on public.essay_pyq_tags(theme_id);

create index if not exists idx_essay_pyq_tags_review
  on public.essay_pyq_tags(reviewer_status);

-- Not seeded by this migration -- no content exists yet. Schema settled now
-- so the brainstorm-canvas UI has a stable target from day one.
create table if not exists public.essay_brainstorm_blocks (
  id uuid primary key default gen_random_uuid(),
  theme_id uuid not null references public.essay_themes(id) on delete cascade,
  block_type text not null
    check (block_type in (
      'hook', 'thesis', 'argument_for', 'argument_against',
      'example', 'quote', 'counter_narrative', 'closing_thought'
    )),
  block_text text not null,
  linked_gs_topic_id uuid references public.topics(id) on delete set null,
  source_note text,
  usage_count integer not null default 0,
  created_by uuid references public.profiles(id) on delete set null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_essay_brainstorm_blocks_theme
  on public.essay_brainstorm_blocks(theme_id, block_type);

notify pgrst, 'reload schema';
