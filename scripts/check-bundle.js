#!/usr/bin/env node
/**
 * Initial-bundle regression gate.
 *
 * Two independent assertions protect the public entry surface (the chunk(s)
 * downloaded on the very first paint of `/` and `/login`):
 *
 *   1. FORBIDDEN_IN_INITIAL — admin / prototype / heavy-report / large
 *      feature code must never enter the initial chunk. We answer "is module
 *      X in the initial chunk?" by walking the *static* import graph from the
 *      app entry (`src/index.js`). A `lazy(() => import('...'))` call is a
 *      dynamic import, so it is NOT followed — that is exactly what keeps a
 *      route out of the initial chunk. A plain `import X from '...'` (or
 *      `export ... from '...'`) IS followed, so re-adding admin/prototype via
 *      a static import is caught and the offending file + specifier reported.
 *
 *   2. SIZE_LIMITS_GZIPPED — the built entry chunk must stay under its gzip
 *      budget. Measured directly with zlib on the emitted file.
 *
 * source-map-explorer is wired as an opt-in byte-level cross-check (run with
 * `--sme` or CHECK_BUNDLE_SME=1). It is NOT part of the gate by default:
 * source-map-explorer 2.5.x trips on CRA's minified entry sourcemap
 * ("generated column Infinity"), so making the build depend on it would make
 * the gate itself flaky. The static graph walk is the reliable signal.
 */
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const FORBIDDEN_IN_INITIAL = [
  'pages/admin/',
  'pages/prototype/',
  'pages/study/Mocks.jsx', // user mocks page should be lazy
  'pages/StudyPlan.jsx',
  'features/community/',
  'recharts', // entire chart lib
  'react-day-picker',
];

const SIZE_LIMITS_GZIPPED = {
  'main.*.js': 220 * 1024, // 220KB initial chunk hard cap
};

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, '..');
const frontendDir = path.join(repoRoot, 'app', 'frontend');
const srcDir = path.join(frontendDir, 'src');
const buildDir = path.join(frontendDir, 'build');
const jsDir = path.join(buildDir, 'static', 'js');

const toPosix = (p) => p.split(path.sep).join('/');
const isPackage = (entry) => !entry.includes('/');
const PKG_FORBIDDEN = FORBIDDEN_IN_INITIAL.filter(isPackage);
const PATH_FORBIDDEN = FORBIDDEN_IN_INITIAL.filter((e) => !isPackage(e));

const failures = [];

// ── 1. static import-graph walk ──────────────────────────────────────────
function resolveRelative(fromFile, spec) {
  const base = path.resolve(path.dirname(fromFile), spec);
  const candidates = [
    base,
    `${base}.js`,
    `${base}.jsx`,
    `${base}.ts`,
    `${base}.tsx`,
    path.join(base, 'index.js'),
    path.join(base, 'index.jsx'),
    path.join(base, 'index.ts'),
    path.join(base, 'index.tsx'),
  ];
  for (const c of candidates) {
    if (fs.existsSync(c) && fs.statSync(c).isFile()) return c;
  }
  return null;
}

function walkInitialGraph() {
  const entry = path.join(srcDir, 'index.js');
  if (!fs.existsSync(entry)) {
    failures.push(`Could not find app entry at ${toPosix(path.relative(repoRoot, entry))}.`);
    return;
  }
  // Matches `import ... from '<spec>'`, side-effect `import '<spec>'`, and
  // `export ... from '<spec>'`. Does NOT match dynamic `import('<spec>')`
  // (no whitespace after `import`), so lazy() chunks are excluded by design.
  const importRe = /(?:import|export)\s+(?:[^"';]*?\sfrom\s+)?["']([^"']+)["']/g;
  const seen = new Set();
  const queue = [entry];

  while (queue.length) {
    const file = queue.pop();
    if (seen.has(file)) continue;
    seen.add(file);

    const text = fs.readFileSync(file, 'utf8');
    let m;
    while ((m = importRe.exec(text))) {
      const spec = m[1];
      const importer = toPosix(path.relative(repoRoot, file));

      const pkg = PKG_FORBIDDEN.find((p) => spec === p || spec.startsWith(`${p}/`));
      if (pkg) {
        failures.push(
          `forbidden package "${pkg}" reachable in the initial chunk:\n` +
            `    ${importer} statically imports "${spec}"\n` +
            `    → load it lazily (dynamic import()) so it splits into its own chunk.`,
        );
      }

      if (spec.startsWith('.')) {
        const resolved = resolveRelative(file, spec);
        if (!resolved) continue;
        const rel = toPosix(path.relative(srcDir, resolved));
        const hit = PATH_FORBIDDEN.find((p) => rel.includes(p));
        if (hit) {
          failures.push(
            `forbidden module "${hit}" reachable in the initial chunk:\n` +
              `    ${importer} statically imports "${spec}" (→ src/${rel})\n` +
              `    → wrap it in lazy(() => import("${spec}")) so it leaves the initial chunk.`,
          );
        }
        queue.push(resolved);
      }
    }
  }
}

// ── 2. gzip size budget ────────────────────────────────────────────────────
function globToRe(glob) {
  const escaped = glob.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*');
  return new RegExp(`^${escaped}$`);
}

function checkSizeBudgets() {
  if (!fs.existsSync(jsDir)) {
    failures.push(
      `No production build found at ${toPosix(path.relative(repoRoot, jsDir))}. Run \`npm run build\` first.`,
    );
    return;
  }
  const jsFiles = fs
    .readdirSync(jsDir)
    .filter((f) => f.endsWith('.js') && !f.endsWith('.LICENSE.txt'));

  for (const [glob, limit] of Object.entries(SIZE_LIMITS_GZIPPED)) {
    const re = globToRe(glob);
    const matches = jsFiles.filter((f) => re.test(f));
    if (matches.length === 0) {
      failures.push(`No built bundle matched size-budget pattern "${glob}".`);
      continue;
    }
    for (const f of matches) {
      const gz = zlib.gzipSync(fs.readFileSync(path.join(jsDir, f))).length;
      const kb = (n) => `${(n / 1024).toFixed(1)}KB`;
      if (gz > limit) {
        failures.push(
          `bundle "${f}" is ${gz} bytes gzipped (${kb(gz)}), over the "${glob}" budget of ${limit} bytes (${kb(limit)}).`,
        );
      } else {
        console.log(`  ok  ${f}: ${kb(gz)} gzip (budget ${kb(limit)})`);
      }
    }
  }
}

// ── 3. optional source-map-explorer cross-check ──────────────────────────────
function smeCrossCheck() {
  const manifestPath = path.join(buildDir, 'asset-manifest.json');
  if (!fs.existsSync(manifestPath)) return;
  const mainRel = JSON.parse(fs.readFileSync(manifestPath, 'utf8'))?.files?.['main.js'];
  if (!mainRel) return;
  const mainAbs = path.join(buildDir, mainRel.replace(/^\//, '').replace(/^static/, 'static'));
  const mainFile = fs.existsSync(mainAbs)
    ? mainAbs
    : path.join(buildDir, mainRel.replace(/^\//, ''));
  try {
    const out = execFileSync(
      process.platform === 'win32' ? 'npx.cmd' : 'npx',
      ['--yes', 'source-map-explorer', mainFile, '--json'],
      { encoding: 'utf8', cwd: frontendDir, maxBuffer: 64 * 1024 * 1024, stdio: ['ignore', 'pipe', 'ignore'] },
    );
    const report = JSON.parse(out);
    const result = (report.results || [])[0] || report;
    const modules = Object.keys(result.files || result || {});
    const offenders = modules.filter((mod) => {
      const norm = toPosix(mod);
      return (
        PATH_FORBIDDEN.some((p) => norm.includes(p)) ||
        PKG_FORBIDDEN.some((p) => norm.includes(`node_modules/${p}`))
      );
    });
    if (offenders.length) {
      for (const mod of offenders) {
        failures.push(`source-map-explorer: forbidden module in initial chunk: ${mod}`);
      }
    } else {
      console.log('  ok  source-map-explorer: no forbidden modules attributed to the entry chunk');
    }
  } catch (e) {
    console.warn(
      `  warn  source-map-explorer cross-check skipped (${(e.message || 'error').split('\n')[0]}). ` +
        'The static import-graph check above is the authoritative gate.',
    );
  }
}

console.log('Bundle regression gate');
console.log('  forbidden-in-initial + gzip size budget\n');

walkInitialGraph();
checkSizeBudgets();
if (process.argv.includes('--sme') || process.env.CHECK_BUNDLE_SME === '1') {
  smeCrossCheck();
}

if (failures.length) {
  console.error('\nBundle regression gate FAILED:\n');
  for (const f of failures) console.error(`- ${f}\n`);
  process.exit(1);
}
console.log('\nBundle regression gate passed.');
