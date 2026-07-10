#!/usr/bin/env node
'use strict';
// PR body gate. Fails when a required section is missing, left empty, or left as
// untouched template boilerplate. The PR template file is the single source of
// truth for what "untouched boilerplate" looks like — the checker derives its
// placeholder baseline from it, so the two never drift.
//
// Inputs (first match wins): argv[2] (file path), PR_BODY_FILE, PR_BODY.
const fs = require('fs');
const path = require('path');

const REQUIRED_SECTIONS = [
  'Summary',
  'Problem / Gap Addressed',
  'Implemented in This PR',
  'Remaining Work / Intentionally Deferred',
  'Files Changed',
  'API Contracts Touched',
  'UI States Covered',
  'Accessibility Checklist',
  'E2E Impact',
  'Manual Test Checklist',
  'Commands Run',
];

const TEMPLATE_PATH = path.join(__dirname, '..', '.github', 'pull_request_template.md');

// Only used when the template file cannot be read (isolated local runs). CI
// always checks out the repo, so the template file — not this list — is the
// real baseline.
const FALLBACK_PLACEHOLDERS = [
  'what changed at a high level?',
  'why this pr exists now?',
  'what was broken, risky, inconsistent, or missing before this pr?',
  'which user/admin flow was impacted?',
  'item 1', 'item 2', 'item 3',
  'what is explicitly *not* covered in this pr?',
  'why is it deferred (scope/risk/dependency)?',
  'path/to/file', 'why it changed',
  'scenario 1', 'scenario 2', 'scenario 3',
  'paste exact commands and outcome markers',
  'where?',
];

function getBody() {
  const p = process.argv[2] || process.env.PR_BODY_FILE;
  if (p && fs.existsSync(p)) return fs.readFileSync(p, 'utf8');
  if (process.env.PR_BODY) return process.env.PR_BODY;
  throw new Error('No PR body provided. Use argv[2], PR_BODY_FILE, or PR_BODY.');
}

// Collapse to comparable content: lowercase, drop every non-alphanumeric char so
// whitespace, markdown scaffolding, and emoji never cause spurious mismatches.
function normalize(text) {
  return (text || '').toLowerCase().replace(/[^a-z0-9]+/g, '');
}

// Split markdown into level-2 (`## `) sections in a single pass.
// Returns Map<lowercaseTitle, { title, content }>. `### x` subheadings stay
// inside their parent section (the `\s+` after `##` rejects a third hash).
function parseSections(markdown) {
  const sections = new Map();
  if (!markdown) return sections;
  const lines = markdown.replace(/\r\n/g, '\n').split('\n');
  let current = null;
  for (const line of lines) {
    const m = line.match(/^##\s+(.+?)\s*$/);
    if (m) {
      current = { title: m[1].trim(), lines: [] };
      sections.set(current.title.toLowerCase(), current);
    } else if (current) {
      current.lines.push(line);
    }
  }
  for (const s of sections.values()) s.content = s.lines.join('\n').trim();
  return sections;
}

function isEmptyOrPlaceholder(content, section, templateSections) {
  if (!content) return true;
  const norm = normalize(content);
  if (!norm) return true;

  // A bare "N/A" is only acceptable for API Contracts (None/N/A is a real
  // answer there); everywhere else it is a non-answer.
  if (section !== 'API Contracts Touched' && /^n\/?a\.?$/i.test(content.trim())) return true;

  const tmpl = templateSections && templateSections.get(section.toLowerCase());
  if (tmpl) {
    // Untouched if it still matches the template's boilerplate verbatim.
    return norm === normalize(tmpl.content);
  }

  // No template available: strip known placeholder phrases; boilerplate-only
  // sections collapse to nothing.
  let residue = content.toLowerCase();
  for (const ph of FALLBACK_PLACEHOLDERS) residue = residue.split(ph).join(' ');
  return normalize(residue) === '';
}

function validate(body, templateSections) {
  const errors = [];
  const sections = parseSections(body);

  for (const section of REQUIRED_SECTIONS) {
    const entry = sections.get(section.toLowerCase());
    if (!entry) {
      errors.push(`Missing required section: ${section}`);
      continue;
    }
    if (isEmptyOrPlaceholder(entry.content, section, templateSections)) {
      errors.push(`Section is empty or placeholder-only: ${section}`);
      continue;
    }

    if (section === 'Implemented in This PR') {
      const hasChecked = entry.content.split('\n').some((l) => /^\s*-\s*\[[xX]\]/.test(l));
      if (!hasChecked) errors.push('"Implemented in This PR" must include at least one checked item.');
    }

    if (section === 'Commands Run') {
      // Drop code-fence delimiters and comment-only lines (leading `#`), then
      // require some real command/result text to remain.
      const cleaned = entry.content
        .replace(/^\s*```.*$/gm, '')
        .replace(/^\s*#.*$/gm, '')
        .trim();
      if (!/[a-z0-9]/i.test(cleaned)) errors.push('"Commands Run" must include real command/result content.');
    }
  }
  return errors;
}

function loadTemplateSections() {
  try {
    if (fs.existsSync(TEMPLATE_PATH)) return parseSections(fs.readFileSync(TEMPLATE_PATH, 'utf8'));
  } catch {
    /* fall back to embedded placeholder list */
  }
  return null;
}

function run() {
  const body = getBody().replace(/\r\n/g, '\n');
  const errors = validate(body, loadTemplateSections());
  if (errors.length) {
    for (const e of errors) console.error(`❌ ${e}`);
    process.exitCode = 1;
    return errors;
  }
  console.log('✅ PR body validation passed.');
  return errors;
}

module.exports = {
  REQUIRED_SECTIONS,
  normalize,
  parseSections,
  isEmptyOrPlaceholder,
  validate,
  loadTemplateSections,
};

if (require.main === module) {
  run();
  if (process.exitCode) process.exit(process.exitCode);
}
