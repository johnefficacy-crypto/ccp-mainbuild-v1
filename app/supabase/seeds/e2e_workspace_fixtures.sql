-- E2E workspace fixtures — exam-intelligence workspace track (PR8).
--
-- Seeds a minimal but complete graph for the three workspace E2E specs:
--   workspace-shell    — exam + subject + topics (shell loads, tabs render)
--   topic-edit-drawer  — CMS API: PATCH topic, POST/DELETE topic-alias
--   pyq-bulk-import    — pyq_paper enables PYQ tab; CSV upload → preflight → commit
--
-- All rows use fixed UUIDs and ON CONFLICT upserts — fully idempotent.
-- The admin user (super_admin role) is created at runtime by the Playwright
-- global setup via the Supabase admin API; it cannot be seeded as plain SQL.

do $$
declare
  v_family_id  uuid := 'e2e0e2e0-0000-4000-8000-000000000001';
  v_exam_id    uuid := 'e2e0e2e0-0000-4000-8000-000000000002';
  v_subject_id uuid := 'e2e0e2e0-0000-4000-8000-000000000003';
  v_topic_id   uuid := 'e2e0e2e0-0000-4000-8000-000000000004';
  v_paper_id   uuid := 'e2e0e2e0-0000-4000-8000-000000000005';
begin

  -- 1) Exam family
  insert into public.exam_families (id, slug, name, is_active)
  values (v_family_id, 'e2e-workspace-family', 'E2E Workspace Family', true)
  on conflict (id) do update set name = excluded.name, is_active = true;

  -- 2) Exam
  insert into public.exams (id, exam_family_id, slug, name, exam_type, is_active)
  values (v_exam_id, v_family_id, 'e2e-workspace-exam', 'E2E Workspace Exam', 'recruitment', true)
  on conflict (id) do update set name = excluded.name, is_active = true;

  -- 3) Subject
  insert into public.subjects (id, name, slug, subject_group, is_active)
  values (v_subject_id, 'E2E Polity', 'e2e-polity', 'social_science', true)
  on conflict (id) do update set name = excluded.name, is_active = true;

  -- 4) Topic (used by topic-edit-drawer spec)
  insert into public.topics (
    id, subject_id, parent_topic_id, slug, name, level, default_difficulty_level, is_active, metadata
  )
  values (
    v_topic_id, v_subject_id, null,
    'e2e-federalism', 'E2E Federalism', 'topic', 'medium', true, '{}'::jsonb
  )
  on conflict (id) do update set
    name = excluded.name,
    slug = excluded.slug,
    is_active = true,
    default_difficulty_level = excluded.default_difficulty_level;

  -- 5) PYQ paper (presence makes pyq_workbench readiness "partial", enabling the tab)
  insert into public.pyq_papers (id, exam_id, year, source_type, trust_status, metadata)
  values (v_paper_id, v_exam_id, 2024, 'community', 'pending', '{}'::jsonb)
  on conflict (id) do update set exam_id = excluded.exam_id, year = excluded.year;

end $$;
