-- 209_exam_phase_kind_and_cycle_planner_exposure.sql
--
-- D12 v1 — required-phase completeness + light planner-exposure applicability.
--
-- (1) D05 §1 authorizes a constrained canonical `exam_phases.phase_kind` classification.
--     Existing rows remain NULL until an operator classifies them. NULL and 'other' are
--     UNCLASSIFIED (D05: "requires operator classification before a blocking policy is
--     applied") and never count toward D12 required-phase completeness. The 7 concrete kinds
--     are the classified set. This column MUST NOT be permanently inferred from phase slug,
--     name, question count, negative marking, or the unconstrained `exam_phases.mode` field.
--
-- (2) D12/D14: `light` review_activate is applicable "only when the exam/cycle is exposed to
--     Study OS or planner activation". `exam_cycles.planner_activation_enabled` is the
--     canonical authority for that exposure — cycle-scoped (cycle-canonical, consistent with
--     D12's selected-cycle readiness) and fail-closed (default false). It is DISTINCT from
--     `exams.is_active`, which is aspirant visibility / retirement per the domain model and
--     MUST NOT be used as a planner-activation signal.
--
-- Both tables already have RLS enabled (migration 035); ADD COLUMN inherits existing policies,
-- so no new RLS policy is required. Migrations are immutable once merged.

alter table public.exam_phases
  add column if not exists phase_kind text
    check (
      phase_kind is null
      or phase_kind in (
        'objective_written',
        'descriptive_written',
        'mixed_written',
        'interview',
        'physical_test',
        'medical',
        'document_verification',
        'other'
      )
    );

comment on column public.exam_phases.phase_kind is
  'D05 canonical phase classification. NULL or ''other'' = unclassified (requires operator '
  'action); the 7 concrete kinds are the classified set used by D12 required-phase completeness. '
  'Must not be permanently inferred from slug/name/mode/counts.';

alter table public.exam_cycles
  add column if not exists planner_activation_enabled boolean not null default false;

comment on column public.exam_cycles.planner_activation_enabled is
  'D12/D14 canonical planner / Study-OS exposure authority for this cycle. When false, a '
  'management_mode=light exam''s review_activate step is not_applicable (planner_activation_disabled). '
  'Distinct from exams.is_active (aspirant visibility). Fail-closed default: false.';
