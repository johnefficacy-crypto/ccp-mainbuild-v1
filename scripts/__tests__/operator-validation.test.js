'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');

const {
  normalizeRepoPath,
  isIsoDate,
  isIsoTimestamp,
  validateRegistry,
  renderIndex,
  validateChangedFiles,
} = require('../operator-validation.js');

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'operator-validation-'));
  const files = [
    'docs/status/track.md',
    'docs/runbooks/gate.md',
    'docs/operator-validation/evidence/result.md',
  ];
  for (const file of files) {
    fs.mkdirSync(path.dirname(path.join(root, file)), { recursive: true });
    fs.writeFileSync(path.join(root, file), `${file}\n`, 'utf8');
  }
  const registry = {
    schema_version: 2,
    generated_index: 'docs/operator-validation/INDEX.md',
    tracks: [
      {
        id: 'study-track',
        name: 'Study Track',
        owner: 'Study OS',
        gates: [
          {
            id: 'study-live-gate',
            title: 'Study live gate',
            status: 'validation_pending',
            summary: 'Code is present and live validation remains.',
            updated_at: '2026-07-15',
            review_by: '2099-01-01T09:30:00Z',
            next_action: 'Execute the runbook.',
            implementation_refs: ['docs/status/track.md'],
            runbook: 'docs/runbooks/gate.md',
            evidence: [],
            defects_found: [{ id: 'study-01', summary: 'A live-path defect was found.' }],
            defects_fixed: [{ id: 'study-01', summary: 'Code remediation landed; revalidation remains.' }],
            blockers: [],
            depends_on: [],
          },
        ],
      },
    ],
  };
  return { root, registry };
}

test('path, date, and timestamp helpers reject unsafe or invalid values', () => {
  assert.equal(normalizeRepoPath('./docs/a.md'), 'docs/a.md');
  assert.equal(normalizeRepoPath('../secret'), null);
  assert.equal(normalizeRepoPath('/absolute/path'), null);
  assert.equal(isIsoDate('2026-07-15'), true);
  assert.equal(isIsoDate('2026-02-30'), false);
  assert.equal(isIsoTimestamp('2026-07-15T09:30:00Z'), true);
  assert.equal(isIsoTimestamp('2026-07-15'), false);
  assert.equal(isIsoTimestamp('2026-07-15T09:30:00+05:30'), false);
});

test('valid non-terminal gate passes with an existing runbook and future review timestamp', () => {
  const { root, registry } = fixture();
  assert.deepEqual(validateRegistry(registry, { repoRoot: root, now: '2026-07-15T09:00:00Z' }), []);
});

test('duplicate gate IDs are rejected across tracks', () => {
  const { root, registry } = fixture();
  registry.tracks.push({ id: 'other-track', name: 'Other', owner: 'Other owner', gates: [{ ...registry.tracks[0].gates[0] }] });
  const errors = validateRegistry(registry, { repoRoot: root, now: '2026-07-15T09:00:00Z' });
  assert.ok(errors.some((error) => error === 'duplicate gate id: study-live-gate'));
});

test('partial pass requires an immutable evidence record', () => {
  const { root, registry } = fixture();
  const gate = registry.tracks[0].gates[0];
  gate.status = 'partial_pass';
  gate.runbook = null;
  const errors = validateRegistry(registry, { repoRoot: root, now: '2026-07-15T09:00:00Z' });
  assert.ok(errors.some((error) => error.includes('evidence is required for status partial_pass')));

  gate.evidence.push({ path: 'docs/operator-validation/evidence/result.md', recorded_at: '2026-07-15', result: 'partial_pass' });
  assert.deepEqual(validateRegistry(registry, { repoRoot: root, now: '2026-07-15T09:00:00Z' }), []);
});

test('overdue review timestamps fail at the exact instant', () => {
  const { root, registry } = fixture();
  registry.tracks[0].gates[0].review_by = '2026-07-15T08:59:59Z';
  const errors = validateRegistry(registry, { repoRoot: root, now: '2026-07-15T09:00:00Z' });
  assert.ok(errors.some((error) => error.includes('stale gate study-live-gate')));
});

test('review_by rejects date-only values', () => {
  const { root, registry } = fixture();
  registry.tracks[0].gates[0].review_by = '2099-01-01';
  const errors = validateRegistry(registry, { repoRoot: root, now: '2026-07-15T09:00:00Z' });
  assert.ok(errors.some((error) => error.includes('RFC3339 UTC timestamp')));
});

test('defect lists are required and fixed IDs must refer to found IDs', () => {
  const { root, registry } = fixture();
  const gate = registry.tracks[0].gates[0];
  delete gate.defects_found;
  let errors = validateRegistry(registry, { repoRoot: root, now: '2026-07-15T09:00:00Z' });
  assert.ok(errors.some((error) => error.includes('defects_found must be an array')));

  gate.defects_found = [];
  errors = validateRegistry(registry, { repoRoot: root, now: '2026-07-15T09:00:00Z' });
  assert.ok(errors.some((error) => error.includes('defects_fixed id must also exist in defects_found')));
});

test('missing referenced files fail closed', () => {
  const { root, registry } = fixture();
  registry.tracks[0].gates[0].implementation_refs = ['docs/status/missing.md'];
  const errors = validateRegistry(registry, { repoRoot: root, now: '2026-07-15T09:00:00Z' });
  assert.ok(errors.some((error) => error.includes('does not exist: docs/status/missing.md')));
});

test('generated index is deterministic and includes defect columns', () => {
  const { registry } = fixture();
  const first = renderIndex(registry);
  const second = renderIndex(JSON.parse(JSON.stringify(registry)));
  assert.equal(first, second);
  assert.match(first, /Defects found/);
  assert.match(first, /Defects fixed/);
  assert.match(first, /study-01/);
  assert.match(first, /VALIDATION PENDING/);
  assert.ok(first.endsWith('\n'));
  assert.ok(!first.endsWith('\n\n'));
});

test('registered source or evidence changes require a registry update', () => {
  const { registry } = fixture();
  const sourceErrors = validateChangedFiles(['docs/runbooks/gate.md'], registry);
  assert.ok(sourceErrors.some((error) => error.includes('changed without docs/operator-validation/registry.json')));
  const evidenceErrors = validateChangedFiles(['docs/operator-validation/evidence/new-run.md'], registry);
  assert.ok(evidenceErrors.some((error) => error.includes('changed without docs/operator-validation/registry.json')));
});

test('registry and generated index must change together', () => {
  const { registry } = fixture();
  assert.ok(validateChangedFiles(['docs/operator-validation/registry.json'], registry).some((error) => error.includes('without regenerated')));
  assert.ok(validateChangedFiles(['docs/operator-validation/INDEX.md'], registry).some((error) => error.includes('must not change without')));
  assert.deepEqual(validateChangedFiles([
    'docs/operator-validation/registry.json',
    'docs/operator-validation/INDEX.md',
    'docs/runbooks/gate.md',
  ], registry), []);
});
