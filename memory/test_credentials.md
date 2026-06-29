# Career Copilot · Test Credentials (Phase 1.5 + Phase 2)

Authentication is handled by **Supabase Auth**. There are no seeded
demo accounts on the backend — every account is a real Supabase
Auth user.

## Test admin / payments user

> **SECURITY:** A real `super_admin` password used to live here in
> plaintext. It has been removed from the repo. **Rotate that Supabase
> account's password (or delete the account) if it still exists** — a
> committed credential must be treated as compromised. Never commit a
> working password for any account, least of all a privileged one.

Provision a fresh test admin via the Supabase admin API instead of
sharing a static credential (see the snippets below). Keep the password
in your local `backend/.env` / a secret manager, not in version control.

```
email:    <provision-your-own>@example.com
password: <store-in-.env-or-secret-manager>
role:     super_admin
user_id:  <returned-by-admin-api>
```

## How to sign in for testing

1. Open the app at `/signup` and create an account with a real email
   provider (Supabase rejects disposable TLDs like `.test`).
2. The Supabase project requires email confirmation, so either
   - confirm the email via the link Supabase sends, or
   - create a pre-confirmed user via the admin API:

```bash
curl -X POST "$SUPABASE_URL/auth/v1/admin/users" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "YourPass@2026",
    "email_confirm": true,
    "user_metadata": {"name": "Tester"}
  }'
```

3. Sign in at `/login` — the frontend calls `supabase.auth.signInWithPassword`,
   stores the session in localStorage, and attaches the access token as
   `Authorization: Bearer <jwt>` on backend requests.

## Granting admin role

Admin/super_admin routes resolve `role` **only** from `app_metadata.role`,
which is writable solely via the service-role admin API (below). It is
**never** read from `user_metadata` — `user_metadata` is client-writable
(`supabase.auth.updateUser({ data: ... })`), so trusting it for role would
let any user self-promote. Set roles only through this admin call:

```bash
curl -X PUT "$SUPABASE_URL/auth/v1/admin/users/<user_id>" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"app_metadata": {"role": "super_admin"}}'
```

Allowed auth roles: `user` (default), `admin`, `super_admin`. `mentor` is
a domain capability (`profiles.is_mentor`), **not** an auth role.

## Razorpay test cards (Razorpay Checkout)

Test mode keys are already wired into `backend/.env` and
`NEXT_PUBLIC_RAZORPAY_KEY_ID`. Use any of:

- Card: `4111 1111 1111 1111` · CVV `123` · any future expiry
- UPI:  `success@razorpay`
- Netbanking: pick any test bank → "Success"

The webhook secret is intentionally a placeholder
(`XXXXXXXXXXXXXXXXXXXXXXXX`); set a real one in `backend/.env` and
register `${REACT_APP_BACKEND_URL}/api/payments/webhook` in the
Razorpay dashboard before going live.

## Auth endpoints

- Frontend → Supabase Auth: signUp, signInWithPassword, signOut,
  resetPasswordForEmail, updateUser({ password }), onAuthStateChange
- Backend → `GET /api/auth/me` (Supabase Bearer token validates the user)

The legacy `/api/auth/{register,login,logout,refresh,forgot-password,reset-password}`
endpoints from Phase 1 have been removed along with MongoDB.
