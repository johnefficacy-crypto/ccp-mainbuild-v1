# Mock Mastery Write-back (PR5)

## Flag states
- `FF_MOCK_MASTERY_WRITES=off` (default): disabled.
- `...=shadow`: writes only to `mock_mastery_shadow`.
- `...=live`: writes shadow + `user_topic_mastery` + `user_topic_mastery_audit` + `mock_correction_tasks`.

## Cutover plan
1. Keep `off` at deploy.
2. Flip to `shadow` for 14 days.
3. Run weekly shadow analysis and verify sign agreement >=80%, overlap >=60%, no outliers.
4. Flip to `live`.

## Rollback SQL (last N days)
```sql
with reverted as (
  select id, user_id, topic_id, before_mastery_db
  from public.user_topic_mastery_audit
  where at >= now() - interval ':days days' and reason='mock_submit'
)
update public.user_topic_mastery utm
set mastery_score = r.before_mastery_db
from reverted r
where utm.user_id=r.user_id and utm.topic_id=r.topic_id;

insert into public.user_topic_mastery_audit (
  id,user_id,topic_id,attempt_id,before_mastery_db,after_mastery_db,delta_applied_db,reason
)
select gen_random_uuid(), a.user_id, a.topic_id, a.attempt_id, a.after_mastery_db, a.before_mastery_db,
       (a.before_mastery_db-a.after_mastery_db), 'rollback'
from public.user_topic_mastery_audit a
where a.at >= now() - interval ':days days' and a.reason='mock_submit';
```
