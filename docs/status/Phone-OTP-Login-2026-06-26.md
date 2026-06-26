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

## OPERATOR PENDING (cannot be done from code)
1. Provision an SMS provider in Supabase (Twilio): set `SUPABASE_AUTH_SMS_TWILIO_ACCOUNT_SID`, `SUPABASE_AUTH_SMS_TWILIO_MESSAGE_SERVICE_SID`, `SUPABASE_AUTH_SMS_TWILIO_AUTH_TOKEN`; enable the phone provider in the Supabase dashboard. Until then real codes don't send — use the `test_otp` map for dev.
2. Existing email/password-only users without a phone (and admins) must be migrated: seed their phone in `auth.users` (Supabase) or have them re-onboard via phone; Google users are unaffected.
3. Live click-through: signup (phone+name+optional email → OTP), login (phone → OTP), admin login, Google + guest still work.
