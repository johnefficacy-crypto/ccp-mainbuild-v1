'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');

const {
  touchesUserFacing,
  clickThroughSection,
  checkboxStats,
  getLabels,
} = require('../check-click-through.js');

test('touchesUserFacing matches only frontend / api prefixes', () => {
  const files = [
    'app/frontend/src/App.jsx',
    'app/backend/app/api/routes.py',
    'app/backend/app/services/thing.py',
    'scripts/validate-pr-body.js',
    'docs/readme.md',
  ];
  assert.deepEqual(touchesUserFacing(files), [
    'app/frontend/src/App.jsx',
    'app/backend/app/api/routes.py',
  ]);
});

test('clickThroughSection extracts body up to the next heading; null when absent', () => {
  const body = [
    '## Summary',
    'stuff',
    '## Click-through verification',
    '- [x] clicked through',
    '### Flow walked',
    'login then submit',
    '## Manual Test Checklist',
    '- [ ] later',
  ].join('\n');
  const section = clickThroughSection(body);
  assert.ok(section.includes('- [x] clicked through'));
  // Stops at the next level-1/2/3 heading.
  assert.ok(!section.includes('login then submit'));
  assert.equal(clickThroughSection('## Summary\nno section here'), null);
});

test('checkboxStats counts total and checked items', () => {
  assert.deepEqual(checkboxStats('- [x] a\n- [ ] b\n- [X] c\nnot a box'), { total: 3, checked: 2 });
  assert.deepEqual(checkboxStats('no boxes at all'), { total: 0, checked: 0 });
});

test('getLabels parses JSON arrays, object arrays and comma fallback', () => {
  process.env.PR_LABELS = JSON.stringify(['click-through-na', 'other']);
  assert.deepEqual(getLabels(), ['click-through-na', 'other']);

  process.env.PR_LABELS = JSON.stringify([{ name: 'a' }, { name: 'b' }]);
  assert.deepEqual(getLabels(), ['a', 'b']);

  process.env.PR_LABELS = 'x, y, z';
  assert.deepEqual(getLabels(), ['x', 'y', 'z']);

  delete process.env.PR_LABELS;
  assert.deepEqual(getLabels(), []);
});
