-- 139_mock_templates_authoring.sql
-- PR2d template authoring backend (additive only)

create table if not exists public.mock_template_sections (
  id uuid primary key default gen_random_uuid(),
  template_id uuid not null references public.mock_templates(id) on delete cascade,
  section_index int not null,
  name text not null,
  subject_id uuid references public.subjects(id) on delete set null,
  question_count int not null check (question_count > 0),
  duration_sec int,
  marks_per_correct numeric not null,
  marks_per_wrong numeric not null default 0,
  section_timer_mode text not null default 'common' check (section_timer_mode in ('per_section','common')),
  allow_switching boolean not null default true,
  selector jsonb not null,
  unique(template_id, section_index)
);

create table if not exists public.mock_template_audit_log (
  id uuid primary key default gen_random_uuid(),
  template_id uuid not null references public.mock_templates(id) on delete cascade,
  actor_id uuid references auth.users(id) on delete set null,
  action text not null,
  from_status text,
  to_status text,
  diff jsonb not null default '{}'::jsonb,
  notes text,
  at timestamptz not null default now()
);

create index if not exists idx_mock_template_sections_template on public.mock_template_sections(template_id);
create index if not exists idx_mock_template_audit_template on public.mock_template_audit_log(template_id, at desc);
