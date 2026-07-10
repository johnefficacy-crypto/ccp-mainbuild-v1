'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');

const {
  normalize,
  parseSections,
  isEmptyOrPlaceholder,
  validate,
  loadTemplateSections,
  REQUIRED_SECTIONS,
} = require('../validate-pr-body.js');

// The real PR template is the placeholder baseline the gate uses in CI.
const TEMPLATE = loadTemplateSections();

// A body that fills in every required section with real content.
function goodBody(overrides = {}) {
  const base = {
    Summary: 'Rewrote the PR-body validator and added self-tests.',
    'Problem / Gap Addressed': 'Placeholder detection accepted untouched boilerplate.',
    'Implemented in This PR': '- [x] single-pass section parser\n- [ ] follow-up',
    'Remaining Work / Intentionally Deferred': 'Nothing deferred.',
    'Files Changed': '| `scripts/validate-pr-body.js` | rewrite |',
    'API Contracts Touched': 'None.',
    'UI States Covered': 'N/A — tooling only.',
    'Accessibility Checklist': '- [x] N/A tooling change',
    'E2E Impact': 'None.',
    'Manual Test Checklist': '- [x] ran node --test',
    'Commands Run': '```bash\nnode --test scripts/__tests__/\n```',
  };
  const merged = { ...base, ...overrides };
  return REQUIRED_SECTIONS.map((s) => `## ${s}\n${merged[s] ?? ''}`).join('\n\n');
}

test('normalize strips scaffolding, whitespace and emoji', () => {
  assert.equal(normalize('  ## Loading state: ✅ / ❌ '), 'loadingstate');
  assert.equal(normalize(''), '');
  assert.equal(normalize(null), '');
});

test('parseSections splits level-2 sections in one pass and ignores ### subheadings', () => {
  const s = parseSections('## A\nalpha\n### Sub\nstill A\n## B\nbeta');
  assert.deepEqual([...s.keys()], ['a', 'b']);
  assert.equal(s.get('a').content, 'alpha\n### Sub\nstill A');
  assert.equal(s.get('b').content, 'beta');
});

test('a fully filled body passes', () => {
  assert.deepEqual(validate(goodBody(), TEMPLATE), []);
});

test('a missing section is reported', () => {
  const body = goodBody().replace('## Summary\nRewrote the PR-body validator and added self-tests.', '');
  const errors = validate(body, TEMPLATE);
  assert.ok(errors.some((e) => e === 'Missing required section: Summary'));
});

test('untouched template boilerplate is rejected (the bug this rewrite fixes)', () => {
  assert.ok(TEMPLATE, 'template file should be readable in-repo');
  const untouchedSummary = TEMPLATE.get('summary').content;
  const body = goodBody({ Summary: untouchedSummary });
  const errors = validate(body, TEMPLATE);
  assert.ok(errors.some((e) => e === 'Section is empty or placeholder-only: Summary'));
});

test('empty section content is rejected', () => {
  const errors = validate(goodBody({ Summary: '   ' }), TEMPLATE);
  assert.ok(errors.some((e) => e.includes('empty or placeholder-only: Summary')));
});

test('bare N/A is rejected everywhere except API Contracts Touched', () => {
  assert.ok(isEmptyOrPlaceholder('N/A', 'Summary', TEMPLATE));
  assert.ok(!isEmptyOrPlaceholder('N/A', 'API Contracts Touched', TEMPLATE));
});

test('Implemented in This PR requires at least one checked item', () => {
  const errors = validate(goodBody({ 'Implemented in This PR': '- [ ] not done\n- [ ] also not done' }), TEMPLATE);
  assert.ok(errors.some((e) => e.includes('at least one checked item')));
});

test('Commands Run rejects comment-only content but keeps inline comments', () => {
  const commentOnly = validate(goodBody({ 'Commands Run': '```bash\n# nothing real here\n```' }), TEMPLATE);
  assert.ok(commentOnly.some((e) => e.includes('real command/result content')));

  const inlineComment = validate(goodBody({ 'Commands Run': '```bash\nnpm test # runs suite\n```' }), TEMPLATE);
  assert.deepEqual(inlineComment, []);
});

test('fallback placeholder path works without a template', () => {
  const untouchedSummary = '- What changed at a high level?\n- Why this PR exists now?';
  assert.ok(isEmptyOrPlaceholder(untouchedSummary, 'Summary', null));
  assert.ok(!isEmptyOrPlaceholder('Real summary of the change.', 'Summary', null));
});
