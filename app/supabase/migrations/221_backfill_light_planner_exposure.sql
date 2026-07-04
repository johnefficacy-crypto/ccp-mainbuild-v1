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
-- >=1 locked topic-coverage row APPLICABLE TO THAT CYCLE. New light cycles keep the fail-closed
-- default (false) and require an explicit operator opt-in.
--
-- Selected-cycle coverage canonicity (D08 / D12): applicability is resolved PER CYCLE, exactly as
-- cycle_readiness `_resolve_coverage` does — a cycle is covered by its own cycle-scoped rows
-- (tc.exam_cycle_id = c.id) UNION exam-wide rows (tc.exam_cycle_id IS NULL). A locked row scoped to
-- a DIFFERENT cycle must NOT expose this one: without the per-cycle predicate, one locked row for
-- Cycle B would opt every operational cycle of the same exam (incl. Cycle A, which has no
-- applicable coverage) into planner activation, and the planner's exam-wide coverage fallback would
-- then generate Cycle A's plan from Cycle B's data — the cross-cycle leak D12 forbids.
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
      and (tc.exam_cycle_id = c.id or tc.exam_cycle_id is null)
  );

notify pgrst, 'reload schema';
