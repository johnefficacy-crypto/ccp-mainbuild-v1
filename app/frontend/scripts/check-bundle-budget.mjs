#!/usr/bin/env node
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const MAX_MAIN_GZIP_BYTES = 200 * 1024;
const FORBIDDEN_PATTERNS = [/\/pages\/admin\//, /\/pages\/prototype\//, /\/src\/prototype\//];
const LOGIN_ROOT_MARKERS = [
  /\/pages\/auth\/Login\.(jsx?|tsx?)$/,
  /\/pages\/Landing\.(jsx?|tsx?)$/,
  /\/routes\/publicRoutes\.(jsx?|tsx?)$/,
  /\/App\.(jsx?|tsx?)$/,
];

const rootDir = process.cwd();
const buildDir = path.join(rootDir, 'build');
const jsDir = path.join(buildDir, 'static', 'js');
const manifestPath = path.join(buildDir, 'asset-manifest.json');

if (!fs.existsSync(manifestPath)) {
  throw new Error('Missing build/asset-manifest.json. Run `npm run build` first.');
}

const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const mainJsRel = manifest?.files?.['main.js'];
if (!mainJsRel) {
  throw new Error('asset-manifest.json does not contain files["main.js"].');
}

const jsFiles = fs
  .readdirSync(jsDir)
  .filter((f) => f.endsWith('.js') && !f.endsWith('.js.LICENSE.txt'))
  .map((f) => path.join(jsDir, f));

if (jsFiles.length === 0) {
  throw new Error('No JS bundles found in build/static/js.');
}

const smeOut = execFileSync(
  process.platform === 'win32' ? 'npx.cmd' : 'npx',
  ['source-map-explorer', ...jsFiles, '--json'],
  { encoding: 'utf8', cwd: rootDir, maxBuffer: 64 * 1024 * 1024 },
);

const report = JSON.parse(smeOut);
const reportEntries = Object.entries(report);

function normalize(p) {
  return p.replaceAll('\\\\', '/');
}

const mainJsAbs = normalize(path.join(rootDir, mainJsRel.replace(/^\//, '')));
const mainEntry = reportEntries.find(([bundlePath]) => normalize(bundlePath).endsWith(mainJsAbs) || normalize(bundlePath) === mainJsAbs || normalize(bundlePath).endsWith(normalize(mainJsRel)));

if (!mainEntry) {
  throw new Error(`Could not find main bundle (${mainJsRel}) in source-map-explorer output.`);
}

const [mainBundlePath, mainBundleData] = mainEntry;
const mainGzip = mainBundleData?.gzipSize ?? 0;
const failures = [];

if (mainGzip > MAX_MAIN_GZIP_BYTES) {
  failures.push(`main chunk gzip ${mainGzip} bytes exceeds ${MAX_MAIN_GZIP_BYTES} bytes (${mainBundlePath}).`);
}

for (const [bundlePath, bundleData] of reportEntries) {
  const modules = Object.keys(bundleData ?? {});
  const containsLoginOrRoot = modules.some((m) => LOGIN_ROOT_MARKERS.some((pattern) => pattern.test(normalize(m))));
  if (!containsLoginOrRoot) continue;

  const forbidden = modules.filter((m) => FORBIDDEN_PATTERNS.some((pattern) => pattern.test(normalize(m))));
  if (forbidden.length > 0) {
    failures.push(
      `bundle ${bundlePath} is reachable from / or /login and includes forbidden modules:\n${forbidden.map((m) => `  - ${m}`).join('\n')}`,
    );
  }
}

if (failures.length > 0) {
  console.error('Bundle budget check failed:\n');
  for (const f of failures) console.error(`- ${f}`);
  process.exit(1);
}

console.log(`Bundle budget check passed. main gzip: ${mainGzip} bytes (limit ${MAX_MAIN_GZIP_BYTES}).`);
