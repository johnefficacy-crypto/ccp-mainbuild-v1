#!/usr/bin/env node
/**
 * Deployment gate: keep DEV/TEST-only Supabase auth config out of production.
 *
 * The checked-in app/supabase/config.toml carries a fixed-OTP test map
 * ([auth.sms.test_otp]) and email signup enabled (for E2E token-minting).
 * If that config is pushed to a hosted project it becomes a sign-in backdoor
 * and exposes email/password login that should be phone-OTP-only.
 * This script fails the build when the production-bound config still contains
 * those dev-only markers.
 *
 * Usage (wire into the hosted-deploy pipeline, NOT the local/CI test run):
 *   SUPABASE_ENV=production SUPABASE_OPERATOR_APPROVED=yes \
 *     node scripts/check-supabase-prod-gate.mjs
 *
 * SUPABASE_CONFIG_PATH may point at an alternate file for CI self-tests.
 *
 * Exit codes: 0 = clean (or not a production run), 1 = unsafe config detected.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
// Allow tests to supply an alternate config path so CI can verify both the
// "blocked" and "allowed" code paths against controlled fixtures.
const CONFIG_PATH =
  process.env.SUPABASE_CONFIG_PATH ||
  join(__dirname, "..", "app", "supabase", "config.toml");

const env = (process.env.SUPABASE_ENV || process.env.NODE_ENV || "").toLowerCase();
const isProd = env === "production" || env === "prod";

if (!isProd) {
  console.log(
    `[supabase-prod-gate] SUPABASE_ENV=${env || "(unset)"} — not a production run, skipping.`
  );
  process.exit(0);
}

const toml = readFileSync(CONFIG_PATH, "utf8");
const violations = [];

// 1. Fixed test-OTP map must be absent in production.
if (/^\[auth\.sms\.test_otp\]/m.test(toml)) {
  violations.push(
    "[auth.sms.test_otp] is present — fixed test OTPs must never reach a hosted project."
  );
}

// 2. At least one real SMS provider must be enabled.
//    Section content is bounded to the range \n[ ... next \n[ (or EOF) so that
//    bracket text inside comment lines (e.g. `# [auth.sms.test_otp]`) cannot
//    cause a false positive or false negative.
const SMS_PROVIDERS = ["twilio", "twilio_verify", "messagebird", "textlocal", "vonage"];

function extractSection(content, header) {
  // Match from the section header up to the next section header line (\n[) or EOF.
  // \n[ only appears at the START of section headers — never inside comment text.
  const m = content.match(
    new RegExp(`\\[${header.replace(/[.[\]]/g, "\\$&")}\\][\\s\\S]*?(?=\\n\\[|$)`)
  );
  return m ? m[0] : "";
}

const anyProviderEnabled = SMS_PROVIDERS.some((provider) => {
  const section = extractSection(toml, `auth.sms.${provider}`);
  return /^\s*enabled\s*=\s*true/m.test(section);
});
if (!anyProviderEnabled) {
  violations.push(
    "No real SMS provider has enabled = true — production needs a live OTP delivery channel."
  );
}

// 3. Email/password signup must be disabled in production.
//    The checked-in config keeps it enabled for E2E token-minting only.
const emailSection = extractSection(toml, "auth.email");
const emailSignupEnabled = /^\s*enable_signup\s*=\s*true/m.test(emailSection);
if (emailSignupEnabled) {
  violations.push(
    "[auth.email] enable_signup = true — email/password login must be disabled before " +
      "production rollout. Set enable_signup = false in the production-bound config."
  );
}

// 4. Operator approval hard stop — requires explicit acknowledgement that the
//    production pre-flight checklist has been completed:
//      • Email provider disabled in Supabase dashboard
//      • Real SMS delivery validated end-to-end
//      • Admin/user phone migration completed
//    See docs/status/Phone-OTP-Login-2026-06-26.md §"OPERATOR PENDING".
const approved = (process.env.SUPABASE_OPERATOR_APPROVED || "").toLowerCase().trim();
if (approved !== "yes") {
  violations.push(
    "SUPABASE_OPERATOR_APPROVED is not set to 'yes' — set this after completing the " +
      "operator pre-flight checklist in docs/status/Phone-OTP-Login-2026-06-26.md."
  );
}

if (violations.length > 0) {
  console.error("[supabase-prod-gate] UNSAFE production config:");
  for (const v of violations) console.error(`  ✗ ${v}`);
  console.error("\nResolve all violations before deploying to production.");
  process.exit(1);
}

console.log("[supabase-prod-gate] OK — production-bound config.toml is deployment-safe.");
process.exit(0);
