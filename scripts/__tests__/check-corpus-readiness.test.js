'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { check, DOC } = require('../ci/check-corpus-readiness.js');

const OK = 'corpus-readiness: not regenerated no DB access in CI; operator regenerates on Monday';

test('fires on a corpus split script', () => {
  const r = check(['scripts/split_optional_buckets.py'], '');
  assert.equal(r.ok, false);
  assert.equal(r.fired[0].label, 'corpus split script');
});

test('fires on an import script', () => {
  assert.equal(check(['scripts/import_gs_papers.py'], '').ok, false);
});

test('fires on a projection script', () => {
  assert.equal(check(['scripts/project_mock_bank.py'], '').ok, false);
});

test('fires on the projection code itself', () => {
  const r = check(['app/backend/app/admin/pyq_mock_projection.py'], '');
  assert.equal(r.ok, false);
  assert.equal(r.fired[0].label, 'projection code');
});

test('fires on a migration touching topics or subjects', () => {
  for (const p of [
    'app/supabase/migrations/301_topics_reparent.sql',
    'app/supabase/migrations/302_subject_slug_backfill.sql',
  ]) {
    assert.equal(check([p], '').ok, false, p);
  }
});

test('does NOT fire on a migration unrelated to the corpus shape', () => {
  const r = check(['app/supabase/migrations/303_add_billing_column.sql'], '');
  assert.equal(r.ok, true);
  assert.deepEqual(r.fired, []);
});

test('does NOT fire on unrelated paths', () => {
  const r = check(
    ['app/frontend/src/pages/StudyPlan.jsx', 'README.md', 'docs/status/other.md'],
    '',
  );
  assert.equal(r.ok, true);
});

test('satisfied when the regenerated doc is in the diff', () => {
  const r = check(['scripts/split_optional_buckets.py', DOC], '');
  assert.equal(r.ok, true);
  assert.match(r.reason, /in the diff/);
});

test('satisfied by a well-formed opt-out line', () => {
  const r = check(['scripts/split_optional_buckets.py'], `## Summary\nstuff\n${OK}\n`);
  assert.equal(r.ok, true);
  assert.match(r.reason, /opted out/);
});

test('the opt-out reason is carried into the output, not just matched', () => {
  const r = check(['scripts/split_optional_buckets.py'], OK);
  assert.match(r.reason, /operator regenerates on Monday/);
});

test('a malformed opt-out line does NOT satisfy the gate', () => {
  const bad = [
    'corpus-readiness: not regenerated',            // no reason
    'corpus-readiness: not regenerated   ',         // whitespace only
    'corpus readiness: not regenerated because x',  // no hyphen
    'corpus-readiness not regenerated because x',   // no colon
    '  corpus-readiness: not regenerated because x',// indented, not line-start
    'Corpus-Readiness: not regenerated because x',  // wrong case
  ];
  for (const body of bad) {
    assert.equal(check(['scripts/split_optional_buckets.py'], body).ok, false, body);
  }
});

test('the opt-out is found on any line of a long body', () => {
  const body = `## Summary\n\nlots of text\n\n${OK}\n\n## Files Changed\n- a\n`;
  assert.equal(check(['scripts/split_optional_buckets.py'], body).ok, true);
});

test('an empty or missing body cannot satisfy a fired gate', () => {
  for (const body of ['', undefined, null]) {
    assert.equal(check(['scripts/split_optional_buckets.py'], body).ok, false);
  }
});

test('no trigger plus no body passes — forks and doc-only PRs are not blocked', () => {
  assert.equal(check(['README.md'], undefined).ok, true);
  assert.equal(check([], undefined).ok, true);
});
