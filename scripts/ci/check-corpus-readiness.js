#!/usr/bin/env node
'use strict';
/**
 * CORPUS-READINESS-01 — the staleness gate.
 *
 * A PR that changes the SHAPE of the corpus must either regenerate
 * docs/status/corpus-readiness.md or say, in the PR body, that it could not.
 * Silence is the failure mode this exists to stop: the doc's numbers go stale
 * without anyone noticing they have.
 *
 * Needs no database and no secrets. It reads two things: the list of changed
 * paths, and the PR body. That is deliberate — a check that needed credentials
 * could not run on a fork, and this must.
 *
 * Inputs (first match wins):
 *   argv[2] / CHANGED_FILES_FILE  a file with one changed path per line
 *   CHANGED_FILES                 the same, newline-separated
 *   PR_BODY_FILE / PR_BODY        the pull request description
 *
 * Exit 0 = satisfied (or not triggered). Exit 1 = a trigger path changed and
 * neither escape was taken.
 */
const fs = require('fs');

const DOC = 'docs/status/corpus-readiness.md';

// Paths that change what the report would say. Kept narrow on purpose: a gate
// that fires on everything gets opted out of by reflex and stops meaning
// anything.
const TRIGGERS = [
  { label: 'corpus split script', test: (p) => /^scripts\/split/.test(p) },
  { label: 'corpus import script', test: (p) => /^scripts\/import/.test(p) },
  { label: 'projection script', test: (p) => /^scripts\/project/.test(p) },
  {
    label: 'projection code',
    test: (p) => p === 'app/backend/app/admin/pyq_mock_projection.py',
  },
  {
    // Only migrations that touch the topic/subject shape. A migration that
    // adds an unrelated column is not a corpus-shape change.
    label: 'topics/subjects migration',
    test: (p) =>
      /^app\/supabase\/migrations\/.*\.sql$/.test(p) &&
      /(topic|subject)/i.test(p),
  },
];

// The opt-out must carry a REASON — a bare "not regenerated" would let the
// gate be silenced without saying anything a reviewer can weigh.
const OPT_OUT = /^corpus-readiness: not regenerated (.+)$/m;

function readFirst(...candidates) {
  for (const c of candidates) {
    if (c === undefined || c === null) continue;
    if (typeof c === 'object' && c.file) {
      if (c.file && fs.existsSync(c.file)) return fs.readFileSync(c.file, 'utf8');
      continue;
    }
    return c;
  }
  return '';
}

function parseChanged(text) {
  return (text || '')
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean);
}

function triggersFor(changed) {
  const hit = [];
  for (const t of TRIGGERS) {
    const files = changed.filter(t.test);
    if (files.length) hit.push({ label: t.label, files });
  }
  return hit;
}

function check(changed, body) {
  const fired = triggersFor(changed);
  if (!fired.length) return { ok: true, fired, reason: 'no trigger path changed' };
  if (changed.includes(DOC)) {
    return { ok: true, fired, reason: 'the doc is in the diff' };
  }
  const m = OPT_OUT.exec(body || '');
  // The spec's shape is `(.+)$`, but `.` matches a space, so a line ending in
  // whitespace would technically capture a "reason" of nothing at all. A blank
  // reason is the same silence the gate exists to prevent, so it does not count.
  if (m && m[1].trim()) {
    return { ok: true, fired, reason: `opted out: ${m[1].trim()}` };
  }
  return { ok: false, fired, reason: 'neither regenerated nor opted out' };
}

function main() {
  const changed = parseChanged(
    readFirst(
      { file: process.argv[2] },
      { file: process.env.CHANGED_FILES_FILE },
      process.env.CHANGED_FILES,
    ),
  );
  const body = readFirst(
    { file: process.env.PR_BODY_FILE },
    process.env.PR_BODY,
  );

  const res = check(changed, body);
  if (res.ok) {
    if (res.fired.length) {
      console.log(`✅ corpus-readiness gate satisfied — ${res.reason}.`);
    } else {
      console.log('✅ corpus-readiness gate not triggered.');
    }
    return 0;
  }

  console.error('❌ This PR changes the shape of the corpus but does not update');
  console.error(`   ${DOC}.`);
  console.error('');
  for (const f of res.fired) {
    console.error(`   ${f.label}:`);
    for (const p of f.files) console.error(`     - ${p}`);
  }
  console.error('');
  console.error('   Either regenerate the doc:');
  console.error('     python scripts/corpus_readiness_report.py --live --source prod');
  console.error('   or, if this PR has no database access, add one line to the PR body:');
  console.error('     corpus-readiness: not regenerated <why, and who will>');
  return 1;
}

module.exports = { check, triggersFor, TRIGGERS, OPT_OUT, DOC };

if (require.main === module) process.exit(main());
