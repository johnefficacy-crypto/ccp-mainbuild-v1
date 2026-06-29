# RPC EXECUTE Grant Audit — v1 Release

**Status:** 16 grant gaps found and fixed in migration `202_rpc_grant_hardening_v1.sql`:
- **A (4)** SECURITY INVOKER RPCs explicitly granted to `authenticated`.
- **B (4)** backend RPCs with no explicit grant → held the default `PUBLIC` (3 DEFINER + the legacy `fn_fanout_alert_event`).
- **C (4)** SECURITY DEFINER RPCs that only `GRANT ... TO service_role` and never revoked the default `PUBLIC` (a GRANT does not remove it).
- **D (4)** SECURITY DEFINER RPCs that revoked only `PUBLIC` — insufficient, since migration 190 proved Supabase also holds explicit `anon`/`authenticated` grants.

The repo has no `ALTER DEFAULT PRIVILEGES` (only a comment in migration 174), so any
function without an explicit revoke retains PostgreSQL's default `PUBLIC` EXECUTE.
`is_admin` (intentionally authenticated, used by RLS policies) and the `refresh_*` trigger
helpers are the only remaining no-explicit-grant functions and are out of scope by design.
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
- For a **SECURITY INVOKER** function (4 of the 16 below) it runs as the caller, so the
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
| `claim_source_for_scrape(uuid, integer)` | 054 | INVOKER | authenticated, service_role | `scraping/runner.py` (service_role) | revoke public/anon/authenticated |
| `apply_mock_mastery_delta(uuid,uuid,uuid,numeric,text)` | 145 | INVOKER | **default PUBLIC** (no explicit grant) | `study_os/mastery_writer.py` (service_role) | revoke public/anon/authenticated |
| `claim_mock_mastery_retry(uuid,text,timestamptz)` | 180 | **DEFINER** | **default PUBLIC** (no explicit grant) | `study_os/mock_engine.py` (service_role) | revoke public/anon/authenticated |
| `complete_mock_mastery_retry(uuid)` | 180 | **DEFINER** | **default PUBLIC** (no explicit grant) | `study_os/mock_engine.py` (service_role) | revoke public/anon/authenticated |
| `fn_fanout_alert_event(uuid)` | 007 | **DEFINER** | **default PUBLIC** (no explicit grant) | none (legacy/dead; trigger-invoked) | revoke public/anon/authenticated |

### Groups C & D — DEFINER RPCs left exposed by incomplete grant hygiene (fixed in 202)

These were previously (incorrectly) listed as "✓ backend-only" because they grant
`service_role`. But a `GRANT` does not remove the default `PUBLIC`, and a `REVOKE FROM
PUBLIC` does not remove explicit `anon`/`authenticated` grants (migration 190). All are
backend-only (service-role callers), so revoking the public roles is a no-op for behaviour.

| Function | Def | Security | Prior grant state | Fix |
|----------|-----|----------|-------------------|-----|
| `claim_eligibility_queue(integer)` | 010 | DEFINER | grant service_role; **default PUBLIC kept** | revoke public/anon/authenticated |
| `enqueue_eligibility_recompute(uuid,uuid,text,jsonb)` | 041 | DEFINER | grant service_role; **default PUBLIC kept** | revoke public/anon/authenticated |
| `upsert_field_review(uuid,text,text,text,text,uuid,text,jsonb,jsonb,text,uuid)` | 127 | DEFINER | grant service_role; **default PUBLIC kept** | revoke public/anon/authenticated |
| `consume_profile_merge_claim(text,uuid)` | 128 | DEFINER | grant service_role; **default PUBLIC kept** | revoke public/anon/authenticated |
| `update_pyq_question_review_atomic(uuid,text,uuid,timestamptz)` | 162 | DEFINER | revoke PUBLIC only | revoke public/anon/authenticated |
| `start_attempt_from_blueprint(uuid,uuid,uuid,jsonb,jsonb,jsonb,timestamptz)` | 179 | DEFINER | revoke PUBLIC only | revoke public/anon/authenticated |
| `fn_invalidate_projection_for_question(uuid)` | 184 | DEFINER | revoke PUBLIC only | revoke public/anon/authenticated |
| `fn_block_projection_for_question(uuid,text)` | 184 | DEFINER | revoke PUBLIC only | revoke public/anon/authenticated |

None of the sixteen is called with a user JWT. The Group A four were explicitly granted to
`authenticated` (verified **no later migration** revoked them). Migration 202 now revokes `PUBLIC`/`anon`/`authenticated` and grants only
`service_role` for all sixteen (Group D's `PUBLIC` revoke is a no-op on a clean DB but
makes the migration self-contained).

---

## Functions checked and found correct (no change)

| Function | Def | Security | Grants | Verdict |
|----------|-----|----------|--------|---------|
| `fn_enqueue_eligibility_for_new_recruitment()` | 007 | DEFINER | (trigger) | ✓ trigger-only |
| `community_inc_thread_reply_count(uuid,integer)` | 089 | DEFINER | authenticated, service_role | ✓ called with user JWT (community runtime) |
| `community_inc_thread_vote_count(uuid,integer)` | 089 | DEFINER | authenticated, service_role | ✓ called with user JWT |
| `community_inc_reply_vote_count(uuid,integer)` | 089 | DEFINER | authenticated, service_role | ✓ called with user JWT |
| `community_inc_resource_upvote_count(uuid,integer)` | 089 | DEFINER | authenticated, service_role | ✓ called with user JWT |
| `community_inc_resource_report_count(uuid,integer)` | 089 | DEFINER | authenticated, service_role | ✓ called with user JWT |
| `replace_document_pages(uuid,text,text,jsonb)` | 113 | DEFINER | revoke public/anon/authenticated; service_role | ✓ backend-only |
| `ensure_mock_correction_draft(...)` | 182 | DEFINER | revoke public/anon/authenticated; service_role | ✓ backend-only |
| `ensure_mock_correction_drafts(...)` | 182 | DEFINER | revoke public/anon/authenticated; service_role | ✓ backend-only |
| `replace_manual_mock_correction_drafts(...)` | 182 | DEFINER | revoke public/anon/authenticated; service_role | ✓ backend-only |
| `project_pyq_question_to_mock_bank(uuid,uuid,text)` | 184 → redefined 186/187 (**187 effective**) | DEFINER | revoke public/anon/authenticated; service_role | ✓ backend-only |
| `fn_invalidate_pyq_projection()` | 184 | DEFINER | service_role | ✓ trigger/backend |
| `accept_partner_request(uuid,uuid)` | 193 | DEFINER | revoke public/anon/authenticated; service_role | ✓ backend-only |
| `review_pyq_paper(text×6)` | 185 → redefined 186/187 (**187 effective**) | DEFINER | revoked PUBLIC+anon+authenticated; service_role | ✓ admin, hardened |
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

## Functions with no explicit grant

The three backend-only **mastery** RPCs that previously sat here (`apply_mock_mastery_delta`,
`claim_mock_mastery_retry`, `complete_mock_mastery_retry`) held the PostgreSQL default
`PUBLIC` grant and are now **fixed in migration 202** (see the Gaps table). The only
remaining no-explicit-grant functions are intentional / out of scope:

| Function | Disposition |
|----------|-------------|
| `is_admin(uuid)` | SECURITY DEFINER helper evaluated *inside* RLS policies; `authenticated` EXECUTE is required here. Left as-is by design. |
| `refresh_course_stats(...)`, `refresh_enrollment_count(...)` | trigger helpers, not `/rpc/`-callable; no EXECUTE grant needed. |

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

**Enumerate EVERY non-trigger function in `public`** (not a curated name list) and flag any
that leaves `PUBLIC`/`anon`/`authenticated` with EXECUTE — this catches functions added or
redefined after this audit so the same omission cannot recur:

```sql
-- Every non-trigger function in `public` that is reachable by PUBLIC/anon/authenticated.
-- Includes the NULL-acl (default-PUBLIC) case. Empty result = clean.
select p.proname,
       pg_get_function_identity_arguments(p.oid) as args,
       case when p.prosecdef then 'DEFINER' else 'INVOKER' end as security,
       case
         when p.proacl is null then 'DEFAULT (PUBLIC)'   -- no explicit ACL ⇒ PUBLIC EXECUTE
         else coalesce(r.rolname, case when a.grantee = 0 then 'PUBLIC' else null end)
       end as grantee
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
left join lateral aclexplode(p.proacl) a on true
left join pg_roles r on r.oid = a.grantee
where n.nspname = 'public'
  and p.prorettype <> 'pg_catalog.trigger'::regtype          -- exclude trigger helpers
  and (
        p.proacl is null                                     -- default PUBLIC
     or exists (                                             -- explicit PUBLIC/anon/authenticated
          select 1 from aclexplode(p.proacl) x
          left join pg_roles xr on xr.oid = x.grantee
          where x.privilege_type = 'EXECUTE'
            and (x.grantee = 0 or xr.rolname in ('anon','authenticated'))
        )
      )
order by p.proname;
```

**Expected:** the only rows should be the **intentional** exceptions — `is_admin`
(authenticated, RLS helper) and the `community_inc_*` counters (089, called with a user
JWT). **Any other function in the result is a finding** and needs a follow-up hardening
migration. In particular, all sixteen RPCs fixed in migration 202 must be ABSENT from this
result. Then smoke-test the backend flows (recruitment promotion, verification create/
supersede, scrape claim, mastery writeback + retry, eligibility recompute, field review,
profile-merge claim, PYQ review, attempt-from-blueprint, projection invalidate/block) to
confirm the service-role paths still work.
