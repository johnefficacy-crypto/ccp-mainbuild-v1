# RPC EXECUTE Grant Audit — v1 Release

**Status:** 4 grant gaps found and fixed in migration `202_rpc_grant_hardening_v1.sql`.
4 functions have no explicit grant statement in any migration and must be verified against
live grants at apply time (see "Functions with no explicit grant" below).
**Scope:** All callable RPCs defined across `app/supabase/migrations/` are enumerated below
(security-sensitive / mutating functions in full detail; triggers and internal helpers
listed for completeness). Each is checked for (a) SECURITY DEFINER vs INVOKER, (b) which
roles hold EXECUTE per migration source, and (c) whether the backend calls it with the
service-role client or a user JWT. **Migration source is not live truth** — the post-apply
operator query at the end is authoritative, because functions can hold grants (e.g. default
`anon`/`authenticated`) that no migration text reveals.

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
| `review_pyq_paper(text×6)` | 185 | DEFINER | revoked PUBLIC+anon+authenticated; service_role | ✓ admin, hardened |
| `cms_set_pyq_paper_provenance(text,text,text,jsonb,text,jsonb,boolean)` | 188 / hardened 190 | DEFINER | revoked PUBLIC+anon+authenticated; service_role | ✓ admin, hardened |
| `cms_link_document_to_pyq_paper(text,text,text,text,text,boolean)` | 188 / hardened 190 | DEFINER | revoked PUBLIC+anon+authenticated; service_role | ✓ admin, hardened |
| `cms_set_pyq_paper_provenance(...)+pyq_source_id` | 191 | DEFINER | revoked PUBLIC+anon+authenticated; service_role | ✓ admin, hardened |
| `cms_pyq_onboarding(text,text,text,text,text,text,jsonb,jsonb,text)` | 192 | DEFINER | revoked PUBLIC+anon+authenticated; service_role | ✓ admin, hardened |
| `cms_review_pyq_source(text×6)` | 201 | DEFINER | revoked PUBLIC+anon+authenticated; service_role | ✓ admin, hardened |

The community counter RPCs (089) are the only `authenticated`-granted functions that are
**correct** — they are SECURITY DEFINER counters deliberately called from the browser with
a user JWT, and they only mutate a single denormalised count.

The PYQ/CMS admin RPCs (185–201) are the reference for correct hardening: each revokes
EXECUTE from **PUBLIC, anon, and authenticated** explicitly and grants only `service_role`.
Migration **190** is the documented cause — it records on staging that migrations 188/189
revoked only PUBLIC at creation time, which left explicit `anon`/`authenticated` grants in
place, so those had to be revoked separately. This is the precedent migration 202 follows.

## Functions with no explicit grant (verify against live grants)

The following callable functions have **no `grant`/`revoke` statement in any migration**, so
their effective grants depend on PostgreSQL/Supabase defaults (which can include `PUBLIC` →
`anon`/`authenticated`). These are **not** asserted correct — the operator query below must
confirm their grantees at apply time, and any holding `anon`/`authenticated` EXECUTE on a
mutating function need a follow-up hardening migration:

| Function | Likely intent | Action |
|----------|---------------|--------|
| `apply_mock_mastery_delta(...)` | service-role (mastery writeback) | verify live; harden if anon/authenticated present |
| `claim_mock_mastery_retry(...)` | service-role (scheduler) | verify live; harden if anon/authenticated present |
| `complete_mock_mastery_retry(...)` | service-role (scheduler) | verify live; harden if anon/authenticated present |
| `refresh_course_stats(...)` | service-role / trigger | verify live |
| `refresh_enrollment_count(...)` | service-role / trigger | verify live |
| `is_admin(uuid)` | SECURITY DEFINER helper called *inside* RLS policies | `authenticated` EXECUTE is expected/required here (policies evaluate it); confirm it is not additionally exploitable |

Trigger functions (`tg_set_updated_at`, `fn_set_updated_at`, `touch_verification_report_updated_at`,
`fn_mock_question_fingerprint`, `fn_profiles_protect_privileged_columns`, `content_access_requests_check_*`,
`fn_invalidate_*`, `fn_block_projection_for_question`, `fn_enqueue_eligibility_for_new_recruitment`,
`fn_fanout_alert_event`) are invoked by the trigger machinery, not via `/rpc/`, and do not
require EXECUTE grants.

---

## Guidance for new RPCs

- **SECURITY INVOKER** (default): grant EXECUTE to `service_role` only, unless the feature
  genuinely calls it with a user JWT and you have verified RLS protects the target tables.
- **SECURITY DEFINER**: never leave it grantable to `public`/`anon`/`authenticated` unless a
  user JWT is meant to call it.
- **`REVOKE … FROM PUBLIC` is NOT sufficient.** In this Supabase setup `anon` and
  `authenticated` can hold *explicit* per-role EXECUTE grants that survive a PUBLIC revoke
  (documented on staging in migration 190). Every new RPC migration must revoke **all three**
  roles explicitly and then grant only the intended role:

  ```sql
  revoke execute on function public.<fn>(<args>) from public;
  revoke execute on function public.<fn>(<args>) from anon;
  revoke execute on function public.<fn>(<args>) from authenticated;
  grant  execute on function public.<fn>(<args>) to service_role;  -- or the intended role
  ```

  Migrations `190`, `201`, and `202` are the reference for this idiom.

---

## Operator verification (post-apply)

After migration 202 applies on staging/prod, confirm the grants resolved as intended:

```sql
select p.proname,
       pg_get_function_identity_arguments(p.oid) as args,
       -- aclexplode renders a PUBLIC grant with grantee OID 0, which has no
       -- pg_roles row; coalesce it to 'PUBLIC' so a leaked PUBLIC grant is never
       -- silently dropped from the result.
       coalesce(r.rolname, case when a.grantee = 0 then 'PUBLIC' else null end) as grantee,
       a.privilege_type
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
order by p.proname, grantee;
```

**Expected:** each function lists `service_role` (and the function owner) only — **no
`PUBLIC`, no `authenticated`, no `anon`**. Note: when `proacl` is NULL the function uses
default privileges (which in Supabase grant EXECUTE to PUBLIC) — that case shows as a NULL
acl and MUST be treated as a finding, not a pass. Then smoke-test the four backend flows
(recruitment promotion, verification report create/supersede, scrape claim) to confirm the
service-role paths still work.

Run the same query (widening the `proname in (...)` list) against the functions in
"Functions with no explicit grant" above to confirm none of them holds `anon`/`authenticated`
EXECUTE on a mutating RPC.
