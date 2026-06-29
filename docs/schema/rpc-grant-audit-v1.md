# RPC EXECUTE Grant Audit — v1 Release

**Status:** 4 grant gaps found and fixed in migration `202_rpc_grant_hardening_v1.sql`.
**Scope:** Every SQL function defined across `app/supabase/migrations/` was checked for
(a) SECURITY DEFINER vs INVOKER, (b) which roles hold EXECUTE, and (c) whether the backend
calls it with the service-role client or a user JWT.

---

## Threat model

PostgREST exposes every function the calling role can EXECUTE at `/rpc/<name>`. The
backend always uses the **service-role** key (`get_supabase_admin()`), which bypasses RLS
and holds every grant — so a `service_role` grant is necessary and sufficient for all
current call sites. Granting EXECUTE to **`authenticated`** additionally lets any
logged-in end user invoke the function directly via the public PostgREST endpoint:

- For a **SECURITY DEFINER** function this is the most dangerous (runs as the owner).
- For a **SECURITY INVOKER** function (the four below) it runs as the caller, so the
  blast radius is bounded by table RLS/grants — but these functions encode admin/worker
  business logic with **no in-function authorization check**, so the only thing standing
  between an `authenticated` caller and a privileged write is RLS on the underlying
  tables. That is a defense-in-depth gap, not least-privilege.

**Principle applied:** backend-only RPCs get `service_role` only. `authenticated`/`anon`
are granted EXECUTE *only* when a feature deliberately calls the RPC with a user JWT.

---

## Gaps found (fixed in migration 202)

| Function | Def migration | Security | Was granted | Backend caller (role) | Fix |
|----------|---------------|----------|-------------|------------------------|-----|
| `promote_recruitment(jsonb)` | 043→059 (latest 059) | INVOKER | authenticated, service_role | `api/admin_scrape.py`, `scraping/runner.py` (service_role) | revoke authenticated/anon |
| `create_verification_report(jsonb)` | 076 | INVOKER | authenticated, service_role | `scraping/verification_reports.py`, `verification_gateway.py` (service_role) | revoke authenticated/anon |
| `supersede_and_create_verification_report(uuid, jsonb)` | 076 | INVOKER | authenticated, service_role | `scraping/verification_gateway.py` (service_role) | revoke authenticated/anon |
| `claim_source_for_scrape(uuid, integer)` | 054 | INVOKER | authenticated, service_role | `scraping/runner.py` (service_role) | revoke authenticated/anon |

None of the four is called anywhere with a user JWT, so revoking `authenticated` is a
no-op for application behaviour. Verified that **no later migration** already revoked these
grants (059 is the latest `promote_recruitment` redefinition and still grants
`authenticated`; 076 and 054 are the sole definitions of the others).

---

## Functions checked and found correct (no change)

| Function | Def | Security | Grants | Verdict |
|----------|-----|----------|--------|---------|
| `claim_eligibility_queue(integer)` | 010 | DEFINER | service_role | ✓ backend-only |
| `enqueue_eligibility_recompute(uuid,uuid,text,jsonb)` | 041 | DEFINER | service_role | ✓ backend-only |
| `fn_enqueue_eligibility_for_new_recruitment()` | 007 | DEFINER | (trigger) | ✓ trigger-only |
| `fn_fanout_alert_event(uuid)` | 007 | DEFINER | (trigger) | ✓ trigger-only |
| `community_inc_thread_reply_count(uuid,integer)` | 089 | DEFINER | authenticated, service_role | ✓ called with user JWT (community runtime) |
| `community_inc_thread_vote_count(uuid,integer)` | 089 | DEFINER | authenticated, service_role | ✓ called with user JWT |
| `community_inc_reply_vote_count(uuid,integer)` | 089 | DEFINER | authenticated, service_role | ✓ called with user JWT |
| `community_inc_resource_upvote_count(uuid,integer)` | 089 | DEFINER | authenticated, service_role | ✓ called with user JWT |
| `community_inc_resource_report_count(uuid,integer)` | 089 | DEFINER | authenticated, service_role | ✓ called with user JWT |
| `replace_document_pages(uuid,text,text,jsonb)` | 113 | DEFINER | service_role | ✓ backend-only |
| `upsert_field_review(...)` | 127 | DEFINER | service_role | ✓ backend-only |
| `consume_profile_merge_claim(text,uuid)` | 128 | DEFINER | service_role | ✓ backend-only |
| `update_pyq_question_review_atomic(uuid,text,uuid,timestamptz)` | 162 | DEFINER | service_role | ✓ backend-only |
| `start_attempt_from_blueprint(...)` | 179 | DEFINER | service_role | ✓ backend-only |
| `ensure_mock_correction_draft(...)` | 182 | DEFINER | service_role | ✓ backend-only |
| `ensure_mock_correction_drafts(...)` | 182 | DEFINER | service_role | ✓ backend-only |
| `replace_manual_mock_correction_drafts(...)` | 182 | DEFINER | service_role | ✓ backend-only |
| `project_pyq_question_to_mock_bank(uuid,uuid,text)` | 184 | DEFINER | service_role | ✓ backend-only |
| `fn_invalidate_pyq_projection()` | 184 | DEFINER | service_role | ✓ trigger/backend |
| `fn_invalidate_projection_for_question(uuid)` | 184 | DEFINER | service_role | ✓ trigger/backend |
| `fn_block_projection_for_question(uuid,text)` | 184 | DEFINER | service_role | ✓ backend-only |
| `accept_partner_request(uuid,uuid)` | 193 | DEFINER | service_role | ✓ backend-only |

The community counter RPCs (089) are the only `authenticated`-granted functions that are
**correct** — they are SECURITY DEFINER counters deliberately called from the browser with
a user JWT, and they only mutate a single denormalised count.

---

## Guidance for new RPCs

- **SECURITY INVOKER** (default): grant EXECUTE to `service_role` only, unless the feature
  genuinely calls it with a user JWT and you have verified RLS protects the target tables.
- **SECURITY DEFINER**: never leave it grantable to `public`. Supabase auto-grants EXECUTE
  to `public` on creation, so always follow with
  `revoke all on function … from public;` then grant explicitly to the intended roles.
- Every new RPC migration must end with an explicit `revoke all … from public;` + targeted
  grant block. Migration `202` is the reference for the revoke idiom.

---

## Operator verification (post-apply)

After migration 202 applies on staging/prod, confirm the grants resolved as intended:

```sql
select p.proname,
       pg_get_function_identity_arguments(p.oid) as args,
       r.rolname as grantee
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
left join lateral aclexplode(p.proacl) a on true
left join pg_roles r on r.oid = a.grantee
where n.nspname = 'public'
  and p.proname in (
    'promote_recruitment',
    'create_verification_report',
    'supersede_and_create_verification_report',
    'claim_source_for_scrape'
  )
order by p.proname, r.rolname;
```

**Expected:** each function lists `service_role` (and the function owner) only — **no
`authenticated`, no `anon`**. Then smoke-test the four backend flows (recruitment
promotion, verification report create/supersede, scrape claim) to confirm the service-role
paths still work.
