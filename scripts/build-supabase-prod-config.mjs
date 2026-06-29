#!/usr/bin/env node
/**
 * Build the Supabase config that is allowed to reach production.
 *
 * The checked-in config intentionally contains local/E2E-only settings. This
 * script creates a separate artifact by removing the fixed SMS test-OTP table
 * and disabling email signup. The source file is never modified.
 *
 * Usage:
 *   SUPABASE_PROD_CONFIG_PATH=/tmp/supabase-production/config.toml \
 *     node scripts/build-supabase-prod-config.mjs
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(scriptDir, "..");
const sourcePath = resolve(
  process.env.SUPABASE_SOURCE_CONFIG_PATH ||
    join(repoRoot, "app", "supabase", "config.toml")
);
const outputValue = process.env.SUPABASE_PROD_CONFIG_PATH || process.argv[2];

if (!outputValue) {
  throw new Error(
    "SUPABASE_PROD_CONFIG_PATH (or an output path argument) is required."
  );
}

const outputPath = resolve(outputValue);
if (outputPath === sourcePath) {
  throw new Error("Production output must not overwrite the checked-in config.toml.");
}

function sectionBounds(lines, sectionName) {
  const header = `[${sectionName}]`;
  const start = lines.findIndex((line) => line.trim() === header);
  if (start === -1) {
    throw new Error(`Required TOML section ${header} was not found.`);
  }

  let end = lines.length;
  for (let index = start + 1; index < lines.length; index += 1) {
    if (/^\s*\[/.test(lines[index])) {
      end = index;
      break;
    }
  }

  return { start, end };
}

function removeSection(lines, sectionName) {
  const { start, end } = sectionBounds(lines, sectionName);
  const before = lines.slice(0, start);
  const after = lines.slice(end);

  while (before.length > 0 && before.at(-1).trim() === "") before.pop();
  while (after.length > 0 && after[0].trim() === "") after.shift();

  return [...before, "", ...after];
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function setSectionKey(lines, sectionName, key, value) {
  const { start, end } = sectionBounds(lines, sectionName);
  const keyPattern = new RegExp(`^(\\s*)${escapeRegExp(key)}\\s*=`);
  const matches = [];

  for (let index = start + 1; index < end; index += 1) {
    const match = lines[index].match(keyPattern);
    if (match) matches.push({ index, indentation: match[1] });
  }

  if (matches.length !== 1) {
    throw new Error(
      `Expected exactly one ${key} key in [${sectionName}], found ${matches.length}.`
    );
  }

  const [{ index, indentation }] = matches;
  const updated = [...lines];
  updated[index] = `${indentation}${key} = ${value}`;
  return updated;
}

const source = readFileSync(sourcePath, "utf8");
let lines = source.split(/\r?\n/);
lines = removeSection(lines, "auth.sms.test_otp");
lines = setSectionKey(lines, "auth.email", "enable_signup", "false");

const productionConfig = `${lines.join("\n").replace(/\n*$/, "")}\n`;
mkdirSync(dirname(outputPath), { recursive: true });
writeFileSync(outputPath, productionConfig, "utf8");

console.log(`[supabase-prod-config] source: ${sourcePath}`);
console.log(`[supabase-prod-config] wrote:  ${outputPath}`);
