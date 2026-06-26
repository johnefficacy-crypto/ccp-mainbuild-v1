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
- `supabase/config.toml`: `[auth.sms]` enabled + `[auth.sms.twilio] enabled = true` (creds via env); dev `[auth.sms.test_otp]` map.
- No DB migration: `profiles.phone` already exists; Supabase stores phone + confirmation on `auth.users`.

## Tests
- Frontend: 44 auth tests (Login/Signup OTP flow, authContext requestPhoneOtp/verifyPhoneOtp, removed-method guard, phone normalizer).
- Backend: `test_auth_phone.py` (serialized `phone` from user object / JWT claim / absent).

## ⛔ DEPLOYMENT GATE (do NOT roll out before all are done)
Password UI is removed for **every** user including admins. Deploying before the
steps below locks out all email/password-only accounts. This branch must NOT be
deployed to production until the operator completes:
1. **SMS provider provisioned** (below) and a live OTP verified end-to-end.
2. **Admin + user phone migration** done (below) — at least every admin has a
   confirmed phone, verified by a real admin phone-OTP login.
3. **Email/password provider disabled** in hosted Supabase (below).
A reviewer/operator owns flipping this gate; "merge now, provision later" is unsafe
for the only admin login path.

## Contract precision (from /checkpost review)
- Password login is removed from the **first-party UI**. Email/password remains
  **enabled in checked-in/local/CI config on purpose** — the E2E suite mints
  service tokens via `signInWithPassword`, so disabling it there breaks CI
  ("Email logins are disabled"). Removing password auth at the provider is the
  operator's production gate: disable the Email provider's password sign-in in
  the hosted Supabase dashboard (gate step 3). Phone OTP in local/CI uses the
  `[auth.sms.test_otp]` map with the Twilio provider **disabled**; the operator
  enables Twilio + creds in hosted (gate step 1).
- Anonymous/guest sign-in is **retained and enabled**
  (`config.toml [auth].enable_anonymous_sign_ins = true`).
- Role is backend-authoritative: `mergeUser` no longer reads
  `user_metadata.role`; `verifyPhoneOtp` returns the backend-hydrated user, so
  the admin redirect can never be driven by client-writable metadata. (Touches
  `core/auth.py` — coordinate merge order with PR #775.)

## OPERATOR PENDING (cannot be done from code)
1. Provision an SMS provider in Supabase (Twilio): set `SUPABASE_AUTH_SMS_TWILIO_ACCOUNT_SID`, `SUPABASE_AUTH_SMS_TWILIO_MESSAGE_SERVICE_SID`, `SUPABASE_AUTH_SMS_TWILIO_AUTH_TOKEN`; enable the phone provider in the Supabase dashboard. Until then real codes don't send — use the `test_otp` map for dev/E2E.
2. Existing email/password-only users without a phone (and **all admins**) must be migrated: seed their phone in `auth.users` (Supabase) or have them re-onboard via phone; Google users are unaffected.
3. **Disable email/password sign-in** in the hosted Supabase Auth dashboard (Email provider → disable password sign-in) so password auth is gone at the provider, not just the UI.
4. Live click-through: signup (phone+name+optional email → OTP), login (phone → OTP), admin login, Google + guest still work.
