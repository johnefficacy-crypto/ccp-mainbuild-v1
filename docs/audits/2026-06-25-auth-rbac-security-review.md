# Auth / RBAC / Onboarding Security Review

- **Date:** 2026-06-25
- **Scope:** Authentication, sign-in, CAPTCHA, user onboarding, RBAC, account
  creation, password reset, and anonymous-login flows — frontend and backend.
- **Stack:** React (CRA) + `@supabase/supabase-js` (auth is fully client-side) →
  FastAPI backend that *verifies* Supabase bearer tokens → PostgreSQL with **RLS
  as the real data-authorization layer** (clients also talk directly to PostgREST
  with the public anon key). 192 SQL migrations at time of review.
- **Method:** Six parallel deep-dive passes (frontend flows, Supabase RLS/RBAC,
  onboarding/anonymous, backend route-authorization, adversarial verification,
  and secrets/config/CI), with every Critical/High finding independently
  re-verified against the source.

> **Status legend:** ✅ fix landed in this branch · 🛠️ fix in progress ·
> 📋 follow-up (tracked, not yet implemented).

---

## The one theme behind most criticals

**Role and ownership are repeatedly resolved from the wrong source.**

- The canonical auth role is `auth.users.app_metadata.role` (settable only by the
  service role). The backend additionally trusted the **user-writable**
  `user_metadata.role`, and several RLS policies still trust the **deprecated**
  `profiles.is_admin` column.
- Many write-handlers use the service-role Supabase client (which **bypasses
  RLS**) but forget the `user_id` ownership predicate, so any caller can mutate
  another user's row by id.

Fixing those three patterns closes most of this list.

---

## Severity overview

| # | Sev | Finding | Location | Status |
|---|-----|---------|----------|--------|
| 1 | 🔴 Critical | Privilege escalation to **super_admin** via client-writable `user_metadata.role` | `app/backend/app/core/auth.py:159` | ✅ |
| 2 | 🔴 Critical | Self-promote via direct PostgREST: `PATCH profiles.is_admin=true` → full R/W/**delete** on 23+ exam tables | `004` + `035/057/060/149` | 🛠️ |
| 3 | 🔴 Critical | Payment forgery: free "captured" mentor bookings, no signature check | `app/backend/app/api/accountability.py:99` | 🛠️ |
| 4 | 🔴 Critical | 4 mock-question tables world-writable (`USING(true) FOR ALL`, incl. `anon`, incl. the audit log) | migration `136` | 🛠️ |
| 5 | 🟠 High | Audit/PII tables created with **no RLS** (who-investigated-whom trail) | migrations `102`, `104` | 🛠️ |
| 6 | 🟠 High | Study/social **IDOR cluster** — tamper with any user's tasks/sessions/partnerships | `canonical.py`, `social_sessions.py` | 🛠️ |
| 7 | 🟠 High | CAPTCHA is client-only and **fails open**; committed config has it off | frontend + `config.toml` | 📋 |
| 8 | 🟠 High | Committed **live super_admin password** | `memory/test_credentials.md:14` | ✅ |
| 9 | 🟠 High | Supabase session **+ refresh token in `localStorage`** → XSS = persistent account takeover; no CSP | `app/frontend/src/lib/supabase.js:12` | 📋 |
| 10 | 🟡 Medium | Merge-claim token in **URL** + not bound to destination identity | `GoogleLinkBanner.jsx:37` | 📋 |
| 11 | 🟡 Medium | `stitch-anonymous` trusts client `anonymous_id` (no ownership proof) → absorb a guest's PII | `onboarding_unified.py:457` | 📋 |
| 12 | 🟡 Medium | Anonymous-cleanup job is **dead** (`profiles.is_anonymous` never set) → PII never purged | `anonymous_cleanup.py:34` | 📋 |
| 13 | 🟡 Medium | Password reset: no re-auth + recovery token in URL hash | `ResetPassword.jsx`, `config.toml` | 📋 |
| 14 | 🟡 Medium | Weak auth baseline: min-pw **6**, no email confirmation, **no MFA** even for admins | `config.toml` | 📋 |
| 15 | 🟡 Medium | `attest_mock` self-verify / `mentor-feedback` fabrication; `admin` bypasses granular perms | `mock_verification.py`, `admin_community_governance.py:63` | 📋 |
| 16 | 🔵 Low | User enumeration on login/signup error copy | `Login.jsx`, `Signup.jsx` | 📋 |
| 17 | 🔵 Low | CORS reads `CORS_ORIGINS` env with `allow_credentials=True` and no `*` guard | `server.py:214` | 📋 |
| 18 | 🔵 Low | `extractor-acceptance.yml` runs in-repo PR head with a real service-role secret | `.github/workflows/extractor-acceptance.yml` | 📋 |
| 19 | 🔵 Low | Merge null-fill is allow-by-default (`role`/`plan` not in denylist) | migration `128:147` | 📋 |
| 20 | 🔵 Low | Latent IDORs (flashcards/revision/ai) guarded only by a prior select; `update_deck` mass-assign overwrite; library upload allows anonymous | various | 📋 |

---

## Critical findings

### 1. Privilege escalation to super_admin via `user_metadata.role` — ✅ fixed

`_serialize_user` (`app/backend/app/core/auth.py`) resolved role as
`app_metadata.role → user_metadata.role → claim.role → "user"` and did **not**
coerce a valid role like `"super_admin"`. `user_metadata` is writable by the user
themselves via `supabase.auth.updateUser({ data: { role: "super_admin" } })`, and
normal signups have no `app_metadata.role` (there is no signup trigger that sets
it — verified), so the fallback always fired.

**Exploit (red-team confirmed end-to-end):** sign up → `updateUser({data:{role:
"super_admin"}})` → call any admin route (`require_super_admin` reads this exact
value and passes) → `PUT /api/admin/users/{self}/role` writes `app_metadata.role`,
making the escalation permanent (it then even survives the authoritative
`/api/auth/me` recheck).

**Fix:** Role is now resolved **only** from `app_metadata.role`; the
`user_metadata.role` and JWT-claim-role fallbacks are removed. (`memory/test_credentials.md`
guidance that mentioned `user_metadata` for roles was also corrected.)

### 2. RLS self-promotion → full control of exam-intelligence data — 🛠️ in progress (migration 193)

`profiles_update_own` (`004_core_rls_policies.sql`) permits an owner to update
their own row with **no column restriction and no guarding trigger**, so a direct
`PATCH /rest/v1/profiles?id=eq.<self>` body `{"is_admin":true}` succeeds. Policies
in `035/057/060/149` then gate writes on the **deprecated**
`exists(... profiles.is_admin = true)` predicate (migration `151` declares that
column "no longer consulted", but those four never switched to the canonical
`public.is_admin()`). Net: a normal user grants themselves `FOR ALL`
(read/insert/update/**delete**) on ~23 catalog tables feeding eligibility and
study plans.

**Confirmed LIVE:** the repo never revokes Supabase's default `authenticated`
table grants (confirmed via the `174`/`190` migration comments), so the PostgREST
path is reachable.

**Fix (migration 193):** a `BEFORE UPDATE` trigger on `profiles` forces privileged
columns (`is_admin`, `is_mentor`, `admin_role`, `plan_id`) back to their prior
values for any non-service-role session; the `035/057/060/149` admin policies are
repointed to `public.is_admin(auth.uid())`.

### 3. Payment forgery — free mentor bookings — 🛠️ in progress

`accountability.py` `book_mentor` set `payment_status="captured"` from the mere
presence of a client-supplied `payment_id` string — no Razorpay signature/order/
amount verification (contrast `marketplace.py`, which verifies the HMAC and fails
closed).

**Exploit:** `POST /api/accountability/mentors/book {"mentor_id":"…","payment_id":
"pay_anything"}` → a paid session marked captured for free.

**Fix:** require `razorpay_order_id`/`payment_id`/`signature`, verify the
signature, confirm order amount == server-derived price and the order's
`notes.user_id == caller`, and only then mark captured; require a permanent
(non-anonymous) identity.

### 4. Four mock-question tables are world-writable — 🛠️ in progress (migration 193)

`136_mock_question_workflow.sql` creates four policies
(`mqg_admin_all`, `mqtt_admin_all`, `mqs_admin_all`, `mqrl_admin_all`) as
`for all using (true) with check (true)` with **no `TO` clause** → they apply to
`anon`. Anyone with the public anon key can insert/update/**delete**
`mock_question_groups`, `…_topic_tags`, `…_sources`, and the
`mock_question_review_log` integrity/audit trail. The same migration gets
`mock_question_bank` right (checks `app_metadata.role`), proving these four are an
oversight.

**Fix (migration 193):** recreate all four to mirror `mock_question_bank_admin_all`
(service_role OR `app_metadata.role in ('admin','super_admin')`).

---

## High findings

### 5. Audit/PII tables with no RLS — 🛠️ in progress (migration 193)
`support_content_access` (`102`) and `content_access_requests` (`104`) record
which admin opened which user's private content; added after the auto-RLS trigger
was removed (`131`), they never got `ENABLE ROW LEVEL SECURITY`. With default
`authenticated` grants, any logged-in user could read the "who-investigated-whom"
trail or forge/destroy the 4-eyes approval log. **Fix:** enable RLS (service-role
only) on these (and `mock_breakdown_recompute_runs`).

### 6. Study/social IDOR cluster — 🛠️ in progress
Handlers use the service-role client and filter only by resource `id`:
- `canonical.py` study_tasks `toggle`/`update`/`complete`/`skip`/`reschedule`
  and `focus/stop` → tamper with any user's tasks/sessions and write arbitrary
  notes.
- `social_sessions.py` `end_session`, `checkin_session`, `request_partner` →
  terminate anyone's group session, manipulate shared-session trust, or force an
  **active** partnership onto a victim without consent.

**Fix:** add `.eq("user_id", caller)` / membership checks to every mutating query
(404/403 on no match); start partnerships as non-active pending consent.

### 7. CAPTCHA is a client-side suggestion — 📋 follow-up
Enablement is inferred from a public build var (`REACT_APP_TURNSTILE_SITE_KEY`); on
captcha *timeout* the login/signup code falls through and calls Supabase **without**
a token; the committed `config.toml` has `[auth.captcha]` commented out. Real
enforcement depends entirely on the prod dashboard. **Fix:** enforce captcha in the
Supabase project; add a prod-build assertion that the site key is present; fail
**closed** on timeout.

### 8. Committed live super_admin password — ✅ fixed
`memory/test_credentials.md` held a working `super_admin` password in plaintext.
Removed from the file and replaced with provisioning guidance. **Action still
required:** rotate or delete that Supabase account — a committed credential must be
treated as compromised. (The repo is private, which bounds exposure to
repo-access holders, but history retains the value.)

### 9. Tokens in `localStorage` — 📋 follow-up
`lib/supabase.js` uses default storage, so the access **and refresh** tokens sit in
`localStorage`; any XSS on the origin yields persistent, offline account takeover.
There is **no CSP** anywhere (verified). This is the standard supabase-js SPA
posture, but it is ranked because the same store holds admin sessions. **Fix:**
cookie-based storage (`@supabase/ssr`) and/or a strict CSP + Trusted Types.

---

## Medium findings (condensed)

- **10. Merge-claim token in URL** (`/login?merge_claim=…`): the bearer token
  leaks via Referer/history/logs; consume isn't bound to the conflicting identity,
  so a captured token lets any account absorb the victim's onboarding PII (and
  denies the victim their merge). The token *core* is otherwise well-designed
  (hash-only, single-use, 15-min TTL, target = caller's own id). **Fix:** keep it
  out of the URL; bind the claim to the target email.
- **11. `stitch-anonymous` ownership gap**: trusts a client-supplied
  `anonymous_id` and reassigns those rows to the caller — a logged-in attacker who
  learns a guest's id can absorb their answers (DOB/domicile/category). **Fix:**
  require a minted token / same anon-`sub` proof. The newer `profile/onboarding.py`
  flow (keyed on the validated `user.id`) is the right model.
- **12. Dead cleanup**: `profiles.is_anonymous` defaults false and is **never set
  true** (the `onboarding.py` references are response payloads, not writes), so the
  30-day purge matches 0 rows; anonymous accounts + PII persist forever and the
  merge-claim "cron backstop" is illusory. **Fix:** persist `is_anonymous` via an
  `auth.users` trigger.
- **13. Reset flow**: `secure_password_change=false` (no re-auth to change
  password) + recovery token delivered in URL hash. **Fix:** enable secure
  password change; use the token-hash recovery template.
- **14. Weak config baseline**: `minimum_password_length=6`, empty
  `password_requirements`, `enable_confirmations=false`, no TOTP MFA. The committed
  config also has `enable_anonymous_sign_ins=false` despite the app depending on
  it — confirmed **config drift** vs prod. **Fix:** raise the floor, gate admin
  roles behind MFA, make committed config match prod.
- **15. Trust/role integrity**: `attest_mock` lets a user mint a "verified/tier_1"
  attestation on their own mock with a client-chosen `attester_role`;
  `mentor-feedback` lets any mentor-role user rate any mentee;
  `admin_community_governance.py:63`'s trailing `if role=="admin": return user`
  makes granular perms (e.g. `mentors.manage` for payout holds) a no-op for any
  admin. **Fix:** derive trust tier/role server-side; remove the admin-bypass
  branch.

---

## Low / informational

- **16.** User enumeration on login/signup error copy (forgot-password is
  correctly neutral). Normalize the messages.
- **17.** CORS reads `CORS_ORIGINS` env with `allow_credentials=True`; default is a
  safe localhost allowlist and there is no `*` in code, but add a guard rejecting
  `*` when credentials are on.
- **18.** `extractor-acceptance.yml` runs in-repo PR head with a real service-role
  secret. Fork PRs are safe (`pull_request`, not `pull_request_target`); restrict
  to post-merge / a low-privilege staging key.
- **19.** Merge null-fill (`128`) is allow-by-default over all `profiles` columns;
  add `role`/`plan`/`plan_id` to the denylist and a drift test.
- **20.** Latent IDORs in `flashcards/revision/ai` (currently saved by a prior
  ownership-checked select); `update_deck` mass-assign overwrite (missing
  `exclude_unset`); `library.py` upload accepts anonymous users (should require a
  permanent identity).

---

## Verified strengths (do not regress)

- Token cache + per-token single-flight design in `core/auth.py`.
- The `require_admin` / `require_super_admin` / `require_permission` gates and the
  **RBAC role-change endpoint** (super_admin-gated, last-super-admin protection,
  audit logging, canonical `app_metadata` writes, `mentor` rejected as a role).
- Merge-claim **core** (hash-only, single-use, 15-min TTL, target bound to the
  caller's own id; claim tables are service-role-only).
- Onboarding answer validation (allowlisted, no mass-assignment); profile-update
  allowlist (`_PROFILE_IDENTITY_FIELDS` excludes `is_admin`/`role`/`plan_id`).
- **JWT verification is correct** — Supabase verifies the signature;
  `verify_signature=False` is used only to read claims from an already-validated
  token.
- Payments/marketplace webhooks verify the Razorpay HMAC and fail closed;
  open-redirect protections (`resolvePostAuthRedirect`) are solid.
- **No** `pull_request_target`; **no** wildcard-CORS-with-credentials; **no**
  service-role key in the frontend; **no** committed production API keys.

---

## Remediation roadmap

**This branch (`security/auth-rbac-hardening`)**
1. ✅ Remove `user_metadata`/claim role fallbacks (#1).
2. ✅ Scrub committed credential + correct role-source docs (#8).
3. 🛠️ Migration 193: profiles privileged-column guard trigger; repoint
   `035/057/060/149` to `is_admin()`; fix the four `136` policies; enable RLS on
   the `102/104` tables (#2, #4, #5).
4. 🛠️ Verify Razorpay payment in `book_mentor` (#3).
5. 🛠️ Add `user_id`/membership predicates to the study/social handlers (#6).

**Operational (out-of-repo, do now)**
- Rotate/delete the previously-committed super_admin Supabase account (#8).
- Confirm prod Supabase enforces CAPTCHA, email confirmation, secure password
  change, and (ideally) MFA for admin roles (#7, #13, #14).

**Follow-ups (subsequent PRs)**
- CAPTCHA fail-closed + prod-build assertion (#7); cookie storage / CSP (#9);
  merge-claim URL + identity binding (#10); anonymous-session ownership proof
  (#11); persist `is_anonymous` + working cleanup (#12); config hardening (#14);
  trust/role integrity (#15); the Low items (#16–#20).
