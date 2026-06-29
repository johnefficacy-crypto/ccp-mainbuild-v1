#!/usr/bin/env node
/**
 * Deployment gate: keep DEV/TEST-only Supabase auth config out of production.
 *
 * The checked-in app/supabase/config.toml carries a fixed-OTP test map and
 * email signup enabled for local/E2E use. The production workflow builds a
 * separate sanitized artifact, then this script validates that artifact before
 * it can be handed to the protected deployment job.
 *
 * Usage:
 *   SUPABASE_ENV=production \
 *   SUPABASE_CONFIG_PATH=/tmp/supabase-production/config.toml \
 *     node scripts/check-supabase-prod-gate.mjs
 *
 * SUPABASE_CONFIG_PATH may point at an alternate file for CI self-tests.
 *
 * Exit codes: 0 = clean (or not a production run), 1 = unsafe config detected.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const configPath =
  process.env.SUPABASE_CONFIG_PATH ||
  join(scriptDir, "..", "app", "supabase", "config.toml");

const env = (process.env.SUPABASE_ENV || process.env.NODE_ENV || "").toLowerCase();
const isProd = env === "production" || env === "prod";

if (!isProd) {
  console.log(
    `[supabase-prod-gate] SUPABASE_ENV=${env || "(unset)"} — not a production run, skipping.`
  );
  process.exit(0);
}

const toml = readFileSync(configPath, "utf8");
const violations = [];

function extractSection(content, sectionName) {
  const lines = content.split(/\r?\n/);
  const header = `[${sectionName}]`;
  const start = lines.findIndex((line) => line.trim() === header);
  if (start === -1) return "";

  let end = lines.length;
  for (let index = start + 1; index < lines.length; index += 1) {
    if (/^\s*\[/.test(lines[index])) {
      end = index;
      break;
    }
  }

  return lines.slice(start, end).join("\n");
}

// 1. Fixed test-OTP map must be absent in production.
if (/^\s*\[auth\.sms\.test_otp\]\s*$/m.test(toml)) {
  violations.push(
    "[auth.sms.test_otp] is present — fixed test OTPs must never reach a hosted project."
  );
}

// 2. At least one real SMS provider must be explicitly enabled.
const SMS_PROVIDERS = ["twilio", "twilio_verify", "messagebird", "textlocal", "vonage"];
const anyProviderEnabled = SMS_PROVIDERS.some((provider) => {
  const section = extractSection(toml, `auth.sms.${provider}`);
  return /^\s*enabled\s*=\s*true\s*(?:#.*)?$/m.test(section);
});
if (!anyProviderEnabled) {
  violations.push(
    "No real SMS provider has enabled = true — production needs a live OTP delivery channel."
  );
}

// 3. Email signup must be explicitly disabled in the production artifact.
const emailSection = extractSection(toml, "auth.email");
const emailSignupDisabled = /^\s*enable_signup\s*=\s*false\s*(?:#.*)?$/m.test(
  emailSection
);
if (!emailSignupDisabled) {
  violations.push(
    "[auth.email] enable_signup must be explicitly false in the production-bound config."
  );
}

if (violations.length > 0) {
  console.error(`[supabase-prod-gate] UNSAFE production config: ${configPath}`);
  for (const violation of violations) console.error(`  ✗ ${violation}`);
  console.error("\nResolve all violations before deploying to production.");
  process.exit(1);
}

console.log(`[supabase-prod-gate] OK — validated production config: ${configPath}`);
process.exit(0);
