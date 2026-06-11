-- Portfolio-lane columns: management_mode + cadence.
-- Additive only. No row classification in this migration.
alter table public.exams
  add column management_mode text,
  add column cadence         text;

alter table public.exams
  add check (management_mode is null or management_mode in ('core','light','index_only','archive')),
  add check (cadence is null or cadence in ('annual','recurring','irregular','one_off','unknown'));

create index idx_exams_management_mode         on public.exams(management_mode);
create index idx_exams_cadence                 on public.exams(cadence);
create index idx_exams_management_mode_name    on public.exams(management_mode, name);
