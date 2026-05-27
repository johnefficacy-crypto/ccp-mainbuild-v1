#!/usr/bin/env node
// Advisory gate for the click-through review discipline (see
// docs/process/click_through_review.md). When a PR touches user-facing surface
// area, it must document a manual click-through in the PR body.
//
// Surface area = any changed file under app/frontend/ or app/backend/app/api/.
//
// Fails (or warns, see mode below) when the PR touches that surface area AND the
// "Click-through verification" section is missing OR has no checked boxes.
//
// Overrides (label on the PR):
//   click-through-na           backend lib / docs / tooling / migration — exempt
//   hotfix-skip-click-through  emergency hotfix — exempt (needs follow-up audit)
//
// Mode (CLICK_THROUGH_ENFORCE):
//   "warn"  (default) advisory — prints a warning but exits 0
//   "block"           blocking — exits 1 on violation
// The check ships advisory and flips to "block" after the agreed two-sprint
// soak (see the process doc for the cutover date).
//
// Inputs (env, all optional for local runs):
//   PR_BODY            the pull request description
//   PR_LABELS          JSON array of label names, e.g. ["click-through-na"]
//   CHANGED_FILES_FILE path to a newline-delimited list of changed files
//   CHANGED_FILES      newline-delimited list of changed files (alt to the file)
//   CLICK_THROUGH_ENFORCE  "warn" | "block"
const fs = require('fs');

const USER_FACING_PREFIXES = ['app/frontend/', 'app/backend/app/api/'];
const SECTION_HEADING = 'Click-through verification';
const NA_LABEL = 'click-through-na';
const HOTFIX_LABEL = 'hotfix-skip-click-through';

function getBody() {
  const path = process.env.PR_BODY_FILE;
  if (path && fs.existsSync(path)) return fs.readFileSync(path, 'utf8');
  return process.env.PR_BODY || '';
}

function getLabels() {
  const raw = process.env.PR_LABELS;
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed.map((l) => (typeof l === 'string' ? l : l && l.name)).filter(Boolean);
    }
  } catch {
    // Allow a plain comma/space separated fallback.
    return raw.split(/[,\n]/).map((s) => s.trim()).filter(Boolean);
  }
  return [];
}

function getChangedFiles() {
  const file = process.env.CHANGED_FILES_FILE;
  let raw = '';
  if (file && fs.existsSync(file)) raw = fs.readFileSync(file, 'utf8');
  else if (process.env.CHANGED_FILES) raw = process.env.CHANGED_FILES;
  return raw.split('\n').map((l) => l.trim()).filter(Boolean);
}

function touchesUserFacing(files) {
  return files.filter((f) => USER_FACING_PREFIXES.some((p) => f.startsWith(p)));
}

// Extracts the body of the click-through section: the lines after the
// "## Click-through verification" heading, up to (but not including) the next
// level-1/2/3 heading. Line-based to stay robust against markdown content.
function clickThroughSection(body) {
  const lines = body.split('\n');
  const headingRe = new RegExp(
    `^#{1,3}\\s+${SECTION_HEADING.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`,
    'i'
  );
  const start = lines.findIndex((l) => headingRe.test(l));
  if (start === -1) return null;
  const collected = [];
  for (let i = start + 1; i < lines.length; i += 1) {
    if (/^#{1,3}\s+\S/.test(lines[i])) break;
    collected.push(lines[i]);
  }
  return collected.join('\n');
}

function checkboxStats(sectionBody) {
  const lines = sectionBody.split('\n');
  let total = 0;
  let checked = 0;
  for (const line of lines) {
    const m = line.match(/^\s*-\s*\[( |x|X)\]/);
    if (!m) continue;
    total += 1;
    if (m[1].toLowerCase() === 'x') checked += 1;
  }
  return { total, checked };
}

function emit(level, msg) {
  // GitHub Actions annotation when running in CI; plain prefix otherwise.
  if (process.env.GITHUB_ACTIONS === 'true') {
    console.log(`::${level}::${msg}`);
  } else {
    console.log(`[${level}] ${msg}`);
  }
}

function main() {
  const mode = (process.env.CLICK_THROUGH_ENFORCE || 'warn').toLowerCase();
  const body = getBody();
  const labels = getLabels();
  const changed = getChangedFiles();

  if (labels.includes(HOTFIX_LABEL)) {
    console.log(`✅ "${HOTFIX_LABEL}" label present — emergency hotfix exempt. A follow-up click-through audit issue is mandatory.`);
    return 0;
  }
  if (labels.includes(NA_LABEL)) {
    console.log(`✅ "${NA_LABEL}" label present — click-through review not applicable.`);
    return 0;
  }

  const userFacing = touchesUserFacing(changed);
  if (userFacing.length === 0) {
    console.log('✅ No user-facing surface area touched (app/frontend/, app/backend/app/api/). Click-through not required.');
    return 0;
  }

  const section = clickThroughSection(body);
  const problems = [];
  if (section === null) {
    problems.push(`PR body is missing the "## ${SECTION_HEADING}" section.`);
  } else {
    const { total, checked } = checkboxStats(section);
    if (total === 0) {
      problems.push(`The "${SECTION_HEADING}" section has no checklist items.`);
    } else if (checked === 0) {
      problems.push(`The "${SECTION_HEADING}" section has ${total} item(s) but none are checked.`);
    }
  }

  if (problems.length === 0) {
    console.log(`✅ Click-through documentation present for ${userFacing.length} user-facing file(s).`);
    return 0;
  }

  const summary = [
    'This PR touches user-facing surface area but does not document a manual click-through.',
    `User-facing files (${userFacing.length}): ${userFacing.slice(0, 10).join(', ')}${userFacing.length > 10 ? ', …' : ''}`,
    ...problems,
    `Fix: complete the "${SECTION_HEADING}" checklist in the PR body, or apply the "${NA_LABEL}" label if this PR has no user-facing surface. See docs/process/click_through_review.md.`,
  ].join(' ');

  if (mode === 'block') {
    emit('error', summary);
    return 1;
  }
  emit('warning', `[advisory] ${summary}`);
  console.log('Advisory mode: not failing the build. This becomes blocking after the two-sprint soak.');
  return 0;
}

process.exit(main());
