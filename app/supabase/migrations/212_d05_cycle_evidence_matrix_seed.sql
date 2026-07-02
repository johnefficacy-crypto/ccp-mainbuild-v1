-- 212_d05_cycle_evidence_matrix_seed.sql
--
-- D12 v1 (PR-2): seed the CYCLE-scoped subset of the D05 "Mandatory evidence matrix" that
-- migration 211 deliberately left for this PR. Together with 211's phase-scoped rows, the
-- exam_evidence_requirements policy is now complete enough for the document_policy evaluator.
--
-- Mapping (D05 "Mandatory evidence matrix"):
--   * "Current notification or primary cycle document" -> primary_cycle_document (cycle, BLOCK,
--     required for every OPERATIONAL cycle). The "verified official exam/organization source"
--     row is NOT a separate policy row — it is the source-authority PREDICATE
--     (requires_verified_source=true) evaluated against source_registry on this document.
--   * corrigendum            -> conditional (corrigendum_known), advisory (warn).
--   * phase schedule/calendar-> conditional (cycle_dates_published), advisory (warn).
--   * application instructions-> conditional (application_tracking_enabled), advisory (warn).
--
-- Only `core` and `light` carry cycle activation evidence; index_only/archive do not enter
-- planner activation. `light`'s "when exposed" gating is applied by the evaluator/PR-3, not per
-- row. Idempotent via ON CONFLICT on the identity index.

insert into public.exam_evidence_requirements
  (management_mode, phase_kind, evidence_kind, satisfied_by, requirement_level, gate_effect,
   scope, minimum_count, requires_verified_source, requires_human_review, requires_extraction,
   condition_code, priority)
values
  -- core (cycle-scoped)
  ('core', null, 'primary_cycle_document', 'document_asset', 'required', 'block', 'cycle', 1, true,  true,  true,  'cycle_is_operational', 90),
  ('core', null, 'corrigendum',            'document_asset', 'required', 'warn',  'cycle', 1, true,  true,  false, 'corrigendum_known', 90),
  ('core', null, 'phase_schedule',         'document_asset', 'required', 'warn',  'cycle', 1, true,  true,  false, 'cycle_dates_published', 90),
  ('core', null, 'application_instructions','document_asset','required', 'warn',  'cycle', 1, true,  true,  false, 'application_tracking_enabled', 90),
  -- light (cycle-scoped) — primary cycle document required when the operational cycle is exposed
  ('light', null, 'primary_cycle_document', 'document_asset', 'required', 'block', 'cycle', 1, true,  true,  true,  'study_os_enabled', 90),
  ('light', null, 'corrigendum',            'document_asset', 'required', 'warn',  'cycle', 1, true,  true,  false, 'corrigendum_known', 90),
  ('light', null, 'phase_schedule',         'document_asset', 'required', 'warn',  'cycle', 1, true,  true,  false, 'cycle_dates_published', 90),
  ('light', null, 'application_instructions','document_asset','required', 'warn',  'cycle', 1, true,  true,  false, 'application_tracking_enabled', 90)
on conflict (management_mode, coalesce(exam_type, ''), coalesce(phase_kind, ''), evidence_kind, scope)
do nothing;

-- Assertion: core cycle primary_cycle_document is a blocker gated on operational cycle.
do $$
declare v_gate text; v_cond text;
begin
  select gate_effect, condition_code into v_gate, v_cond
    from public.exam_evidence_requirements
    where management_mode='core' and phase_kind is null
      and evidence_kind='primary_cycle_document' and scope='cycle';
  if v_gate is distinct from 'block' or v_cond is distinct from 'cycle_is_operational' then
    raise exception 'seed assert failed: core cycle primary_cycle_document must be block/cycle_is_operational (got %/%)', v_gate, v_cond;
  end if;
end $$;

notify pgrst, 'reload schema';
