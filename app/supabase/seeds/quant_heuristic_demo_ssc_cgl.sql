-- GQR-S2 — Quant heuristic demo seed (SSC-CGL), idempotent and audited.
--
-- Authors pending rows through service-role table writes, then verifies each
-- heuristic through cms_review_quant_heuristic (migration 246). This preserves
-- CAS + audit ownership instead of publishing by direct reviewer_status writes.
-- Question-link review remains a service-role UPDATE because v1 has no link RPC.
--
-- Depends on:
--   exam_intelligence_demo_ssc_cgl.sql
--   pilot_content_ssc_cgl_banking.sql
--   migrations 243 and 246
--
-- Required psql variables:
--   actor_user_id — an existing auth.users.id for the reviewing operator
--   actor_email   — that operator's audit email
--
-- Manual run:
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
--     -v actor_user_id="<admin-auth-user-uuid>" \
--     -v actor_email="<admin-email>" \
--     -f app/supabase/seeds/quant_heuristic_demo_ssc_cgl.sql
--
-- Re-runs are stable: unchanged verified rows are not re-reviewed. If content
-- differs, the row returns to pending and the RPC creates a fresh audit record.
-- Links resolve the heuristic by heuristic_code, so a pre-existing row with the
-- same code but a different UUID cannot break the FK.

begin;

create temporary table quant_seed_actor (
  user_id uuid primary key,
  email text
) on commit drop;

insert into pg_temp.quant_seed_actor (user_id, email)
values (:'actor_user_id'::uuid, nullif(:'actor_email', ''));

do $$
begin
  if not exists (
    select 1
    from auth.users u
    join pg_temp.quant_seed_actor a on a.user_id = u.id
  ) then
    raise exception 'seed_actor_not_found: actor_user_id must reference auth.users';
  end if;
end $$;

-- Author pending content. Existing rows are reset to pending only when their
-- governed content changes; unchanged verified rows remain untouched.
insert into public.quant_heuristics as existing
  (id, topic_id, heuristic_code, name, heuristic_type, applicability_rule,
   formula_latex, standard_method, shortcut_method, worked_example, common_traps,
   reviewer_status, is_active, created_by)
select v.id, v.topic_id, v.heuristic_code, v.name, v.heuristic_type,
       v.applicability_rule, v.formula_latex, v.standard_method,
       v.shortcut_method, v.worked_example, v.common_traps,
       'pending', true, a.user_id
from (
  values
    ('a0000000-0000-0000-0000-0000000d5201'::uuid,
     '66666666-6666-6666-6666-666666666661'::uuid,
     'QH-SSC-SUCCESSIVE-PCT', 'Successive percentage change', 'shortcut',
     '{"pattern": "successive_percentage"}'::jsonb,
     'a + b + \frac{ab}{100}',
     'Apply each percentage change in turn to the running value.',
     'net% = a + b + a*b/100 with signs; +20% then -20% → -4%.',
     'A price rises 20% then falls 20%: net = 20 - 20 - 400/100 = -4% (a fall).',
     'Adding the two percentages to zero and forgetting the ab/100 term.'),
    ('a0000000-0000-0000-0000-0000000d5202'::uuid,
     'cccccc01-0000-0000-0000-000000000001'::uuid,
     'QH-SSC-RATIO-UNITARY', 'Ratio via a single unit value', 'shortcut',
     '{"pattern": "ratio_total_to_parts"}'::jsonb,
     '\text{part} = \frac{\text{share}}{\text{sum of parts}} \times \text{total}',
     'Divide the total by the sum of ratio parts to get one unit, then scale.',
     'unit = total / (sum of parts); each share = unit × its part.',
     'Split 6000 in 2:3:1 → sum 6 → unit 1000 → 2000, 3000, 1000.',
     'Summing the parts wrong, or scaling before finding the unit value.')
) as v(
  id, topic_id, heuristic_code, name, heuristic_type, applicability_rule,
  formula_latex, standard_method, shortcut_method, worked_example, common_traps
)
cross join pg_temp.quant_seed_actor a
on conflict (heuristic_code) do update
set topic_id = excluded.topic_id,
    name = excluded.name,
    heuristic_type = excluded.heuristic_type,
    applicability_rule = excluded.applicability_rule,
    formula_latex = excluded.formula_latex,
    standard_method = excluded.standard_method,
    shortcut_method = excluded.shortcut_method,
    worked_example = excluded.worked_example,
    common_traps = excluded.common_traps,
    reviewer_status = 'pending',
    reviewer_notes = null,
    reviewed_by = null,
    reviewed_at = null,
    is_active = true,
    updated_at = now()
where (
  existing.topic_id, existing.name, existing.heuristic_type,
  existing.applicability_rule, existing.formula_latex,
  existing.standard_method, existing.shortcut_method,
  existing.worked_example, existing.common_traps, existing.is_active
) is distinct from (
  excluded.topic_id, excluded.name, excluded.heuristic_type,
  excluded.applicability_rule, excluded.formula_latex,
  excluded.standard_method, excluded.shortcut_method,
  excluded.worked_example, excluded.common_traps, excluded.is_active
);

-- Route every non-verified target through the lifecycle matrix, then verify it.
-- Unchanged verified rows are no-ops, keeping re-runs audit-idempotent.
do $$
declare
  v_h record;
  v_actor uuid;
  v_email text;
  v_status text;
  v_updated_at timestamptz;
begin
  select user_id, email into v_actor, v_email
  from pg_temp.quant_seed_actor;

  for v_h in
    select id, heuristic_code, reviewer_status, updated_at
    from public.quant_heuristics
    where heuristic_code in ('QH-SSC-SUCCESSIVE-PCT', 'QH-SSC-RATIO-UNITARY')
    order by heuristic_code
  loop
    if v_h.reviewer_status in ('rejected', 'needs_correction') then
      perform public.cms_review_quant_heuristic(
        v_h.id, v_h.reviewer_status, v_h.updated_at, 'pending', null,
        'Demo seed reopens governed Quant content for review', v_actor, v_email
      );
      select reviewer_status, updated_at
        into v_status, v_updated_at
      from public.quant_heuristics
      where id = v_h.id;
      v_h.reviewer_status := v_status;
      v_h.updated_at := v_updated_at;
    end if;

    if v_h.reviewer_status = 'pending' then
      perform public.cms_review_quant_heuristic(
        v_h.id, 'pending', v_h.updated_at, 'verified', null,
        'Demo seed verifies reviewed SSC-CGL Quant content', v_actor, v_email
      );
    elsif v_h.reviewer_status <> 'verified' then
      raise exception 'seed_unexpected_status: heuristic % has status %',
        v_h.heuristic_code, v_h.reviewer_status;
    end if;
  end loop;
end $$;

-- Assign the successive-percentage heuristic only to a question admitted by
-- the mock-pipeline gate. Resolve by heuristic_code to survive UUID conflicts.
insert into public.quant_question_heuristics as existing
  (id, question_id, heuristic_id, relevance, reviewer_status)
select '11110000-0000-0000-0000-0000000d5201'::uuid,
       q.id, h.id, 'primary', 'pending'
from public.mock_question_bank q
join public.quant_heuristics h
  on h.heuristic_code = 'QH-SSC-SUCCESSIVE-PCT'
where q.id = 'b1000001-0000-0000-0000-000000000001'::uuid
  and q.reviewer_status in ('verified', 'live', 'published')
on conflict (question_id, heuristic_id) do update
set relevance = excluded.relevance,
    reviewer_status = 'pending',
    reviewed_by = null,
    reviewed_at = null
where existing.relevance is distinct from excluded.relevance;

update public.quant_question_heuristics l
set reviewer_status = 'verified',
    reviewed_by = a.user_id,
    reviewed_at = now()
from public.quant_heuristics h
cross join pg_temp.quant_seed_actor a
where l.heuristic_id = h.id
  and h.heuristic_code = 'QH-SSC-SUCCESSIVE-PCT'
  and l.question_id = 'b1000001-0000-0000-0000-000000000001'::uuid
  and l.reviewer_status <> 'verified';

commit;
