#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..');
const REGISTRY_REL = 'docs/operator-validation/registry.json';
const DEFAULT_INDEX_REL = 'docs/operator-validation/INDEX.md';

const ALLOWED_STATUSES = new Set([
  'planned',
  'code_present',
  'validation_pending',
  'operator_pending',
  'in_progress',
  'partial_pass',
  'passed',
  'failed',
  'blocked',
  'cancelled',
  'superseded',
]);
const TERMINAL_STATUSES = new Set(['passed', 'failed', 'cancelled', 'superseded']);
const EVIDENCE_REQUIRED_STATUSES = new Set(['partial_pass', 'passed', 'failed']);
const ID_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

function normalizeRepoPath(value) {
  if (typeof value !== 'string' || !value.trim()) return null;
  const normalized = value.replace(/\\/g, '/').replace(/^\.\//, '');
  if (path.isAbsolute(normalized) || normalized.split('/').includes('..')) return null;
  return normalized;
}

function isIsoDate(value) {
  if (typeof value !== 'string' || !DATE_PATTERN.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function todayUtc(env = process.env) {
  if (env.OPERATOR_VALIDATION_TODAY) return env.OPERATOR_VALIDATION_TODAY;
  return new Date().toISOString().slice(0, 10);
}

function validatePathExists(repoRoot, repoPath, label, errors) {
  const normalized = normalizeRepoPath(repoPath);
  if (!normalized) {
    errors.push(`${label} must be a non-empty repository-relative path without '..': ${JSON.stringify(repoPath)}`);
    return null;
  }
  if (!fs.existsSync(path.join(repoRoot, normalized))) {
    errors.push(`${label} does not exist: ${normalized}`);
  }
  return normalized;
}

function validateRegistry(registry, options = {}) {
  const repoRoot = options.repoRoot || REPO_ROOT;
  const today = options.today || todayUtc();
  const errors = [];

  if (!registry || typeof registry !== 'object' || Array.isArray(registry)) {
    return ['registry root must be an object'];
  }
  if (registry.schema_version !== 1) errors.push('schema_version must equal 1');

  const generatedIndex = normalizeRepoPath(registry.generated_index || DEFAULT_INDEX_REL);
  if (!generatedIndex) errors.push('generated_index must be a safe repository-relative path');
  if (!Array.isArray(registry.tracks) || registry.tracks.length === 0) {
    errors.push('tracks must be a non-empty array');
    return errors;
  }

  const trackIds = new Set();
  const gateIds = new Set();
  const dependencyChecks = [];

  for (const [trackIndex, track] of registry.tracks.entries()) {
    const trackLabel = `tracks[${trackIndex}]`;
    if (!track || typeof track !== 'object' || Array.isArray(track)) {
      errors.push(`${trackLabel} must be an object`);
      continue;
    }
    if (!ID_PATTERN.test(track.id || '')) errors.push(`${trackLabel}.id must be kebab-case`);
    else if (trackIds.has(track.id)) errors.push(`duplicate track id: ${track.id}`);
    else trackIds.add(track.id);

    if (typeof track.name !== 'string' || !track.name.trim()) errors.push(`${trackLabel}.name is required`);
    if (typeof track.owner !== 'string' || !track.owner.trim()) errors.push(`${trackLabel}.owner is required`);
    if (!Array.isArray(track.gates) || track.gates.length === 0) {
      errors.push(`${trackLabel}.gates must be a non-empty array`);
      continue;
    }

    for (const [gateIndex, gate] of track.gates.entries()) {
      const gateLabel = `${trackLabel}.gates[${gateIndex}]`;
      if (!gate || typeof gate !== 'object' || Array.isArray(gate)) {
        errors.push(`${gateLabel} must be an object`);
        continue;
      }
      if (!ID_PATTERN.test(gate.id || '')) errors.push(`${gateLabel}.id must be kebab-case`);
      else if (gateIds.has(gate.id)) errors.push(`duplicate gate id: ${gate.id}`);
      else gateIds.add(gate.id);

      if (typeof gate.title !== 'string' || !gate.title.trim()) errors.push(`${gateLabel}.title is required`);
      if (!ALLOWED_STATUSES.has(gate.status)) {
        errors.push(`${gateLabel}.status is invalid: ${JSON.stringify(gate.status)}`);
      }
      if (typeof gate.summary !== 'string' || !gate.summary.trim()) errors.push(`${gateLabel}.summary is required`);
      if (typeof gate.next_action !== 'string' || !gate.next_action.trim()) errors.push(`${gateLabel}.next_action is required`);
      if (!isIsoDate(gate.updated_at)) errors.push(`${gateLabel}.updated_at must be YYYY-MM-DD`);

      if (!TERMINAL_STATUSES.has(gate.status)) {
        if (!isIsoDate(gate.review_by)) {
          errors.push(`${gateLabel}.review_by must be YYYY-MM-DD for non-terminal status ${gate.status}`);
        } else if (isIsoDate(today) && gate.review_by < today) {
          errors.push(`stale gate ${gate.id}: review_by ${gate.review_by} is before ${today}`);
        }
      } else if (gate.review_by != null && !isIsoDate(gate.review_by)) {
        errors.push(`${gateLabel}.review_by must be null or YYYY-MM-DD`);
      }

      if (!Array.isArray(gate.implementation_refs) || gate.implementation_refs.length === 0) {
        errors.push(`${gateLabel}.implementation_refs must contain at least one path`);
      } else {
        gate.implementation_refs.forEach((repoPath, refIndex) => {
          validatePathExists(repoRoot, repoPath, `${gateLabel}.implementation_refs[${refIndex}]`, errors);
        });
      }

      if (gate.runbook != null) validatePathExists(repoRoot, gate.runbook, `${gateLabel}.runbook`, errors);
      if (['validation_pending', 'operator_pending', 'in_progress'].includes(gate.status) && !gate.runbook) {
        errors.push(`${gateLabel}.runbook is required for status ${gate.status}`);
      }

      if (!Array.isArray(gate.evidence)) errors.push(`${gateLabel}.evidence must be an array`);
      const evidence = Array.isArray(gate.evidence) ? gate.evidence : [];
      if (EVIDENCE_REQUIRED_STATUSES.has(gate.status) && evidence.length === 0) {
        errors.push(`${gateLabel}.evidence is required for status ${gate.status}`);
      }
      evidence.forEach((entry, evidenceIndex) => {
        const evidenceLabel = `${gateLabel}.evidence[${evidenceIndex}]`;
        if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
          errors.push(`${evidenceLabel} must be an object`);
          return;
        }
        validatePathExists(repoRoot, entry.path, `${evidenceLabel}.path`, errors);
        if (!isIsoDate(entry.recorded_at)) errors.push(`${evidenceLabel}.recorded_at must be YYYY-MM-DD`);
        if (!ALLOWED_STATUSES.has(entry.result)) errors.push(`${evidenceLabel}.result is invalid: ${JSON.stringify(entry.result)}`);
      });

      if (gate.blockers != null && (!Array.isArray(gate.blockers) || gate.blockers.some((item) => typeof item !== 'string' || !item.trim()))) {
        errors.push(`${gateLabel}.blockers must be an array of non-empty strings`);
      }
      if (gate.depends_on != null && (!Array.isArray(gate.depends_on) || gate.depends_on.some((item) => !ID_PATTERN.test(item)))) {
        errors.push(`${gateLabel}.depends_on must be an array of gate ids`);
      }
      for (const dependency of gate.depends_on || []) dependencyChecks.push({ gate: gate.id, dependency });
    }
  }

  for (const { gate, dependency } of dependencyChecks) {
    if (!gateIds.has(dependency)) errors.push(`gate ${gate} depends on unknown gate ${dependency}`);
    if (gate === dependency) errors.push(`gate ${gate} cannot depend on itself`);
  }

  return errors;
}

function markdownEscape(value) {
  return String(value ?? '').replace(/\|/g, '\\|').replace(/\r?\n/g, ' ');
}

function repoLink(repoPath, label) {
  const normalized = normalizeRepoPath(repoPath);
  if (!normalized) return '—';
  return `[${markdownEscape(label || path.basename(normalized))}](../../${normalized})`;
}

function statusLabel(status) {
  return status.replace(/_/g, ' ').toUpperCase();
}

function renderIndex(registry) {
  const lines = [
    '# Operator validation index',
    '',
    '<!-- GENERATED by scripts/operator-validation.js from registry.json. DO NOT EDIT. -->',
    '',
    'This is the generated operator-validation view. Update `registry.json`, then run `node scripts/operator-validation.js --write`.',
    '',
    'Statuses: `PLANNED`, `CODE PRESENT`, `VALIDATION PENDING`, `OPERATOR PENDING`, `IN PROGRESS`, `PARTIAL PASS`, `PASSED`, `FAILED`, `BLOCKED`, `CANCELLED`, `SUPERSEDED`.',
    '',
  ];

  for (const track of registry.tracks) {
    lines.push(`## ${track.name} \`${track.id}\``, '', `Owner: ${track.owner}`, '');
    lines.push('| Gate | Status | Updated | Review by | Next action | Runbook | Evidence |');
    lines.push('|---|---|---:|---:|---|---|---|');
    for (const gate of track.gates) {
      const evidence = (gate.evidence || []).length
        ? gate.evidence.map((entry) => repoLink(entry.path, `${entry.recorded_at} ${statusLabel(entry.result)}`)).join('<br>')
        : '—';
      lines.push(
        `| **${markdownEscape(gate.title)}**<br>\`${gate.id}\` | **${statusLabel(gate.status)}** | ${gate.updated_at} | ${gate.review_by || '—'} | ${markdownEscape(gate.next_action)} | ${gate.runbook ? repoLink(gate.runbook) : '—'} | ${evidence} |`,
      );
    }
    lines.push('');
  }

  lines.push('## Update rule', '');
  lines.push('Do not mirror operator status into per-track checklists. Keep implementation contracts where they are, keep runbooks reusable, append immutable evidence records, and change status only in `registry.json`.');
  lines.push('');
  return `${lines.join('\n')}\n`;
}

function collectTrackedPaths(registry) {
  const paths = new Set();
  for (const track of registry.tracks || []) {
    for (const gate of track.gates || []) {
      for (const repoPath of gate.implementation_refs || []) {
        const normalized = normalizeRepoPath(repoPath);
        if (normalized) paths.add(normalized);
      }
      const runbook = normalizeRepoPath(gate.runbook);
      if (runbook) paths.add(runbook);
      for (const entry of gate.evidence || []) {
        const evidencePath = normalizeRepoPath(entry.path);
        if (evidencePath) paths.add(evidencePath);
      }
    }
  }
  return paths;
}

function validateChangedFiles(changedFiles, registry) {
  const changed = new Set((changedFiles || []).map(normalizeRepoPath).filter(Boolean));
  if (changed.size === 0) return [];

  const errors = [];
  const indexRel = normalizeRepoPath(registry.generated_index || DEFAULT_INDEX_REL) || DEFAULT_INDEX_REL;
  const registryChanged = changed.has(REGISTRY_REL);
  const indexChanged = changed.has(indexRel);
  const tracked = collectTrackedPaths(registry);
  const touchedTrackedSource = [...changed].some((repoPath) => tracked.has(repoPath));
  const touchedEvidenceArea = [...changed].some((repoPath) => repoPath.startsWith('docs/operator-validation/evidence/'));

  if ((touchedTrackedSource || touchedEvidenceArea) && !registryChanged) {
    errors.push(`operator-validation source/evidence changed without ${REGISTRY_REL}`);
  }
  if (registryChanged && !indexChanged) {
    errors.push(`${REGISTRY_REL} changed without regenerated ${indexRel}`);
  }
  if (indexChanged && !registryChanged) {
    errors.push(`${indexRel} is generated and must not change without ${REGISTRY_REL}`);
  }
  return errors;
}

function parseArgs(argv) {
  const result = { mode: 'check', changedFilesPath: null };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--write') result.mode = 'write';
    else if (arg === '--check') result.mode = 'check';
    else if (arg === '--changed-files') result.changedFilesPath = argv[++i];
    else throw new Error(`Unknown argument: ${arg}`);
  }
  return result;
}

function run(argv = process.argv.slice(2), env = process.env) {
  const args = parseArgs(argv);
  const registryPath = path.join(REPO_ROOT, REGISTRY_REL);
  const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
  const errors = validateRegistry(registry, { repoRoot: REPO_ROOT, today: todayUtc(env) });
  const rendered = renderIndex(registry);
  const indexRel = normalizeRepoPath(registry.generated_index || DEFAULT_INDEX_REL) || DEFAULT_INDEX_REL;
  const indexPath = path.join(REPO_ROOT, indexRel);

  if (args.mode === 'write') {
    if (errors.length === 0) {
      fs.writeFileSync(indexPath, rendered, 'utf8');
      console.log(`✅ wrote ${indexRel}`);
    }
  } else if (!fs.existsSync(indexPath)) {
    errors.push(`generated index is missing: ${indexRel}`);
  } else if (fs.readFileSync(indexPath, 'utf8') !== rendered) {
    errors.push(`${indexRel} is stale; run: node scripts/operator-validation.js --write`);
  }

  if (args.changedFilesPath) {
    const changedFiles = fs.existsSync(args.changedFilesPath)
      ? fs.readFileSync(args.changedFilesPath, 'utf8').split(/\r?\n/).filter(Boolean)
      : [];
    errors.push(...validateChangedFiles(changedFiles, registry));
  }

  if (errors.length) {
    for (const error of errors) console.error(`❌ ${error}`);
    process.exitCode = 1;
  } else {
    console.log('✅ operator-validation registry is valid and synchronized.');
  }
  return errors;
}

module.exports = {
  ALLOWED_STATUSES,
  REGISTRY_REL,
  DEFAULT_INDEX_REL,
  normalizeRepoPath,
  isIsoDate,
  validateRegistry,
  renderIndex,
  collectTrackedPaths,
  validateChangedFiles,
  parseArgs,
  run,
};

if (require.main === module) run();
