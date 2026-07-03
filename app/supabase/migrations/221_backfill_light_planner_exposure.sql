-- 221_backfill_light_planner_exposure.sql
--
-- D12 v1 (PR-3): planner enforcement of the canonical exposure authority
-- `exam_cycles.planner_activation_enabled` (added in migration 210). study_os/planner.py now
-- refuses to generate a plan for a `light` exam whose target cycle is not exposed, and
-- cycle_readiness Step 9 marks such a cycle's review_activate not_applicable — the two paths
-- share the same authority.
--
-- Backfill so this does NOT regress any `light` exam that was already planner-usable under the
-- prior (flag-ignoring) behavior: expose the operational cycles of light exams that already have
-- >=1 locked topic-coverage row (the planner's readiness signal). New light cycles keep the
-- fail-closed default (false) and require an explicit operator opt-in.
--
-- core exams are unaffected (the flag does not gate core); index_only/archive do not plan.
-- Idempotent: only flips false -> true where the exposure condition holds.

update public.exam_cycles c
set planner_activation_enabled = true,
    updated_at = now()
from public.exams e
where c.exam_id = e.id
  and e.management_mode = 'light'
  and c.status in ('expected', 'open', 'active')
  and c.planner_activation_enabled = false
  and exists (
    select 1 from public.exam_topic_coverage tc
    where tc.exam_id = e.id
      and tc.reviewer_status = 'locked'
  );

notify pgrst, 'reload schema';
