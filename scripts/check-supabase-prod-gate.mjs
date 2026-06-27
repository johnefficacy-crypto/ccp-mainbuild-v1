#!/usr/bin/env node
/**
 * Deployment gate: keep DEV/TEST-only Supabase auth config out of production.
 *
 * The checked-in app/supabase/config.toml carries a fixed-OTP test map
 * ([auth.sms.test_otp]) and a disabled Twilio provider so local + CI sign-in
 * works without a live SMS gateway. If that config is ever pushed to a hosted
 * project it becomes a sign-in backdoor (a known phone + "123456" authenticates
 * as that user). This script fails the build when the production-bound config
 * still contains those dev-only markers.
 *
 * Usage (wire into the hosted-deploy pipeline, NOT the local/CI test run):
 *   SUPABASE_ENV=production node scripts/check-supabase-prod-gate.mjs
 *
 * Exit codes: 0 = clean (or not a production run), 1 = unsafe config detected.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
// Allow tests to supply an alternate config path so CI can verify both the
// "blocked" (test_otp present) and "allowed" (stripped) code paths.
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

if (/^\s*\[auth\.sms\.test_otp\]/m.test(toml)) {
  violations.push(
    "[auth.sms.test_otp] is present — fixed test OTPs must never reach a hosted project."
  );
}

// The Twilio (or another real) provider must be enabled in production, otherwise
// OTP delivery silently falls back to the test map / fails.
const twilioEnabled = /\[auth\.sms\.twilio\][\s\S]*?^\s*enabled\s*=\s*true/m.test(toml);
const anyProviderEnabled =
  twilioEnabled ||
  /\[auth\.sms\.(twilio_verify|messagebird|textlocal|vonage)\][\s\S]*?^\s*enabled\s*=\s*true/m.test(
    toml
  );
if (!anyProviderEnabled) {
  violations.push(
    "No real SMS provider has enabled = true — production needs a live OTP delivery channel."
  );
}

if (violations.length > 0) {
  console.error("[supabase-prod-gate] UNSAFE production config:");
  for (const v of violations) console.error(`  ✗ ${v}`);
  console.error(
    "\nRemove the dev-only [auth.sms.test_otp] block and enable a real SMS provider " +
      "in the hosted Supabase project before deploying."
  );
  process.exit(1);
}

console.log("[supabase-prod-gate] OK — no dev-only auth config in production-bound config.toml.");
process.exit(0);
