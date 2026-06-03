-- 170_exam_registry_actions.sql
--
-- Corrigendum review → exam lifecycle update (PR5 continuation).
--
-- An operator reviewing a corrigendum_detected / stale / lifecycle
-- verification report may apply the verified value to the exam registry
-- (exam_cycle date, exam_phase date window, or exam_policy_update) through
-- a human gate. Every such mutation is recorded here.
--
-- Trust invariants enforced structurally:
--   * report_id NOT NULL — every action is tied to a verified report.
--   * The CHECK constraint ensures at least one target FK is set.
--   * ON DELETE RESTRICT on exam_cycle_id and exam_phase_id — an action
--     row must never silently lose its target (no hard-delete path exists
--     today; RESTRICT is the correct defence against future drift).
--   * policy_update_id is ON DELETE SET NULL because a policy_update can
--     be superseded by a later CMS edit; the action record still stands.
--   * event_source_id is ON DELETE SET NULL — the discovery event is
--     informational; losing it does not invalidate the action.

begin;

create table if not exists public.exam_registry_actions (
  id               uuid        primary key default gen_random_uuid(),
  report_id        uuid        not null
                               references public.recruitment_verification_reports(id)
                               on delete restrict,
  event_source_id  uuid        references public.recruitment_events(id)
                               on delete set null,
  exam_cycle_id    uuid        references public.exam_cycles(id)
                               on delete restrict,
  exam_phase_id    uuid        references public.exam_phases(id)
                               on delete restrict,
  policy_update_id uuid        references public.exam_policy_updates(id)
                               on delete set null,
  action_type      text        not null
                               check (action_type in (
                                 'cycle_date_update',
                                 'phase_date_update',
                                 'policy_update_create',
                                 'policy_update_edit'
                               )),
  applied_by       uuid        not null references public.profiles(id),
  applied_at       timestamptz not null default now(),
  notes            text,
  metadata         jsonb       not null default '{}'::jsonb,

  -- At least one target must be specified.
  constraint chk_registry_action_has_target
    check (
      exam_cycle_id    is not null
      or exam_phase_id is not null
      or policy_update_id is not null
    )
);

create index if not exists idx_exam_registry_actions_report
  on public.exam_registry_actions(report_id, applied_at desc);

create index if not exists idx_exam_registry_actions_cycle
  on public.exam_registry_actions(exam_cycle_id)
  where exam_cycle_id is not null;

create index if not exists idx_exam_registry_actions_phase
  on public.exam_registry_actions(exam_phase_id)
  where exam_phase_id is not null;

create index if not exists idx_exam_registry_actions_policy
  on public.exam_registry_actions(policy_update_id)
  where policy_update_id is not null;

create index if not exists idx_exam_registry_actions_actor
  on public.exam_registry_actions(applied_by, applied_at desc);

commit;

notify pgrst, 'reload schema';
