const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const API_TIMEOUT_MS = Number(process.env.REACT_APP_API_TIMEOUT_MS || 15000);

// Cloudflare Turnstile SITE key (public). The matching SECRET key lives
// only in Supabase dashboard → Auth → CAPTCHA Protection. If the site
// key is set we assume Supabase has CAPTCHA enabled, so anonymous
// sign-ins must carry a Turnstile token — no token = 400 from
// /auth/v1/signup. Empty string when unset so consumers can treat it as
// a plain boolean check.
const TURNSTILE_SITE_KEY = process.env.REACT_APP_TURNSTILE_SITE_KEY || "";
const CAPTCHA_REQUIRED_FOR_ANON = Boolean(TURNSTILE_SITE_KEY);

// Seed/demo fixtures are only shown in non-prod demo environments.
// Production builds must never render fake data to users.
const ENABLE_DEMO_DATA = process.env.REACT_APP_ENABLE_DEMO_DATA === "true";

if (!BACKEND_URL) {
  throw new Error(
    "Missing REACT_APP_BACKEND_URL. Set it in app/frontend/.env (for local dev) or CI environment variables before running the frontend."
  );
}

// Prototype routes expose internal scaffolding. They must never ship in prod.
if (process.env.NODE_ENV === "production" && process.env.REACT_APP_ENABLE_PROTOTYPE === "true") {
  throw new Error(
    "REACT_APP_ENABLE_PROTOTYPE must not be true in production builds. Remove it from your production environment variables."
  );
}

export {
  BACKEND_URL,
  API_TIMEOUT_MS,
  TURNSTILE_SITE_KEY,
  CAPTCHA_REQUIRED_FOR_ANON,
  ENABLE_DEMO_DATA,
};
