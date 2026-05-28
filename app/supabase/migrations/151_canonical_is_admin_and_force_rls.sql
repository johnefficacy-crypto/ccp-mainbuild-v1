begin;

create or replace function public.is_admin(uid uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from auth.users u
    where u.id = uid
      and coalesce(u.raw_app_meta_data ->> 'role', '') in ('admin','super_admin')
  );
$$;

comment on function public.is_admin(uuid) is
  'Returns true if uid has role admin or super_admin in '
  'auth.users.raw_app_meta_data.role. Source of truth per migration 134. '
  'profiles.is_admin is DEPRECATED and no longer consulted.';

alter table public.extraction_runs           force row level security;
alter table public.pyq_questions             force row level security;
alter table public.pyq_options               force row level security;
alter table public.pyq_question_topic_tags   force row level security;
alter table public.syllabus_topic_mentions   force row level security;
alter table public.exam_topic_coverage       force row level security;
alter table public.exam_policy_updates       force row level security;
alter table public.exam_competition_metrics  force row level security;

commit;
