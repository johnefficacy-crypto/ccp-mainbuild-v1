# Mock Mastery Write-back (PR5)

## Flag states
- `FF_MOCK_MASTERY_WRITES=off` (default): disabled.
- `...=shadow`: writes only to `mock_mastery_shadow`.
- `...=live`: writes shadow + `user_topic_mastery` + `user_topic_mastery_audit` + `mock_correction_tasks`.

## Apply guarantees (live)
- **Cap**: per-attempt delta bounded to ±0.15 unit (±15 db) in `_apply_mastery`,
  separate from the [0,100] safety clamp. See docs/study_os/mock_submit_flow.md.
- **Idempotent + atomic**: applied via the `apply_mock_mastery_delta` RPC
  (migration 145) — skips if an audit row already exists for
  `(user, topic, attempt)`, and writes mastery + audit in one transaction.
  Re-submitting an attempt is a silent no-op.
- **Ordering**: derived inline from raw responses (implementation B), independent
  of PR4 derivation completing.

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
