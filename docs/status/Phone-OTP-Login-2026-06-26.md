# Phone/SMS OTP Login — Decision + Implementation Note

- Date: 2026-06-26
- Status: CODE-FIXED, VALIDATION PENDING (operator must provision the SMS provider + run a live click-through)

## Locked decisions (operator, 2026-06-26)
1. **Phone/SMS OTP replaces email+password login entirely.** Email+password sign-in is removed.
2. **Applies to all users incl. admins/super-admins** — no email/password fallback.
3. **Keep Google OAuth + anonymous (guest) sign-in** (neither uses a password).
4. **Email stays optional** — collected at signup (→ user_metadata), used for receipts/notifications, never for login.
5. Passwords are gone → forgot-password / reset-password flows removed.

## Flow
- Send: `supabase.auth.signInWithOtp({ phone, options: { shouldCreateUser: true, data?, captchaToken? } })` (one flow serves login + signup).
- Verify: `supabase.auth.verifyOtp({ phone, token, type: "sms" })` → session → `hydrate()` → role redirect.
- Phone normalized to E.164 client-side (`lib/phone.js`; bare 10-digit ⇒ +91). Turnstile CAPTCHA retained on the send step.

## Change surface (this branch)
- `lib/authContext.jsx`: add `requestPhoneOtp` / `verifyPhoneOtp`; remove `login` / `register` / `sendPasswordReset` / `updatePassword`; `mergeUser` now carries `phone`.
- `pages/auth/Login.jsx`, `Signup.jsx`: phone → OTP two-step (Google + anonymous kept; email optional on signup).
- `routes/publicRoutes.jsx`: removed `/forgot-password`, `/reset-password`; deleted those pages.
- `lib/phone.js` (+ test): E.164 normalizer.
- Backend `core/auth.py`: `_serialize_user` exposes `phone`; `/api/auth/me` already spreads it. Role source of truth (`raw_app_meta_data.role`) unchanged.
- `supabase/config.toml`: `[auth.sms]` enabled + `[auth.sms.twilio] enabled = true` in local/CI; dev `[auth.sms.test_otp]` map retained for E2E.
- `scripts/build-supabase-prod-config.mjs`: creates a separate production artifact, removes `[auth.sms.test_otp]`, and sets `[auth.email].enable_signup = false` without mutating the checked-in config.
- `scripts/check-supabase-prod-gate.mjs`: rejects test OTPs, a missing/disabled real SMS provider, or email signup not explicitly disabled.
- `.github/workflows/supabase-prod-gate.yml`: validates and uploads the sanitized config, then the `production` environment job downloads and revalidates that exact artifact before `supabase config push`; Twilio credentials are supplied only from production environment secrets.
- No DB migration: `profiles.phone` already exists; Supabase stores phone + confirmation on `auth.users`.

## Tests
- Frontend: 44 auth tests (Login/Signup OTP flow, authContext requestPhoneOtp/verifyPhoneOtp, removed-method guard, phone normalizer).
- Backend: `test_auth_phone.py` (serialized `phone` from user object / JWT claim / absent).
- CI production-gate self-test covers the unsafe checked-in config, generated safe artifact, disabled SMS provider, email signup enabled, and source-file immutability.

## ⛔ DEPLOYMENT GATE (do NOT roll out before all are done)
Password UI is removed for **every** user including admins. Deploying before the
steps below locks out all email/password-only accounts. This branch must NOT be
deployed to production until the operator completes:
1. **SMS provider provisioned** (below) and a live OTP verified end-to-end.
2. **Admin + user phone migration** done (below) — at least every admin has a
   confirmed phone, verified by a real admin phone-OTP login.
3. **Email/password provider disabled** in hosted Supabase (below).
The production workflow is a manual `workflow_dispatch` and its deploy job uses
the GitHub `production` environment. The environment must remain restricted to
`main`, with production secrets scoped to that environment. A permanent
`SUPABASE_OPERATOR_APPROVED=yes` secret is intentionally not used because it is
not a per-deployment approval.

## Contract precision (from /checkpost review)
- Password login is removed from the **first-party UI**. Email/password remains
  **enabled in checked-in/local/CI config on purpose** — the E2E suite mints
  service tokens via `signInWithPassword`, so disabling it there breaks CI
  ("Email logins are disabled"). The production builder sets email signup false
  only in the generated deployment artifact. The operator must still disable
  the hosted Email provider's password sign-in in Supabase before rollout.
- Phone OTP in local/CI uses the `[auth.sms.test_otp]` map with the Twilio
  provider **enabled = true**. Test numbers short-circuit from the map and do not
  reach Twilio. Production receives real Twilio credentials through the
  `production` GitHub environment, and the fixed-OTP table is absent from the
  exact artifact passed between the gate and deploy jobs.
- Anonymous/guest sign-in is **retained and enabled**
  (`config.toml [auth].enable_anonymous_sign_ins = true`).
- Role is backend-authoritative: `mergeUser` no longer reads
  `user_metadata.role`; `verifyPhoneOtp` returns the backend-hydrated user, so
  the admin redirect can never be driven by client-writable metadata. (Touches
  `core/auth.py` — coordinate merge order with PR #775.)

## OPERATOR PENDING (cannot be completed from code inspection)
1. Provision Twilio and configure these production environment secrets: `SUPABASE_AUTH_SMS_TWILIO_ACCOUNT_SID`, `SUPABASE_AUTH_SMS_TWILIO_MESSAGE_SERVICE_SID`, `SUPABASE_AUTH_SMS_TWILIO_AUTH_TOKEN`.
2. Confirm the Twilio Messaging Service has an active sender and enable/configure the phone provider in hosted Supabase.
3. Existing email/password-only users without a phone (and **all admins**) must be migrated: seed their phone in `auth.users` or have them re-onboard via phone; Google users are unaffected.
4. **Disable email/password sign-in** in the hosted Supabase Auth dashboard so password auth is gone at the provider, not just the UI.
5. Live click-through: signup (phone+name+optional email → OTP), login (phone → OTP), admin login, Google + guest still work.
