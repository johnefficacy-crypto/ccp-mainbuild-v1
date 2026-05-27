#!/usr/bin/env node
// Creates/updates the repository labels declared in .github/labels.json using
// the GitHub REST API. Self-contained: relies only on Node 20's global fetch.
// Never deletes labels — only creates missing ones and patches color/description.
//
// Required env:
//   GITHUB_TOKEN      token with `issues: write` on the repo
//   GITHUB_REPOSITORY "owner/repo" (provided by GitHub Actions)
// Optional env:
//   GITHUB_API_URL    defaults to https://api.github.com
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const token = process.env.GITHUB_TOKEN;
const repository = process.env.GITHUB_REPOSITORY;
const apiUrl = process.env.GITHUB_API_URL || 'https://api.github.com';

if (!token) throw new Error('GITHUB_TOKEN is required.');
if (!repository || !repository.includes('/')) {
  throw new Error('GITHUB_REPOSITORY (owner/repo) is required.');
}
const [owner, repo] = repository.split('/');

const here = path.dirname(fileURLToPath(import.meta.url));
const labelsPath = path.resolve(here, '..', '.github', 'labels.json');
const labels = JSON.parse(fs.readFileSync(labelsPath, 'utf8'));

const headers = {
  Authorization: `Bearer ${token}`,
  Accept: 'application/vnd.github+json',
  'X-GitHub-Api-Version': '2022-11-28',
  'Content-Type': 'application/json',
};

async function ghJson(res) {
  const text = await res.text();
  try {
    return text ? JSON.parse(text) : {};
  } catch {
    return { raw: text };
  }
}

async function upsertLabel(label) {
  const getRes = await fetch(
    `${apiUrl}/repos/${owner}/${repo}/labels/${encodeURIComponent(label.name)}`,
    { headers }
  );

  if (getRes.status === 200) {
    const res = await fetch(
      `${apiUrl}/repos/${owner}/${repo}/labels/${encodeURIComponent(label.name)}`,
      {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ new_name: label.name, color: label.color, description: label.description }),
      }
    );
    if (!res.ok) throw new Error(`Failed to update label "${label.name}": ${res.status} ${JSON.stringify(await ghJson(res))}`);
    console.log(`updated  ${label.name}`);
    return;
  }

  if (getRes.status === 404) {
    const res = await fetch(`${apiUrl}/repos/${owner}/${repo}/labels`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ name: label.name, color: label.color, description: label.description }),
    });
    if (!res.ok) throw new Error(`Failed to create label "${label.name}": ${res.status} ${JSON.stringify(await ghJson(res))}`);
    console.log(`created  ${label.name}`);
    return;
  }

  throw new Error(`Unexpected status reading label "${label.name}": ${getRes.status} ${JSON.stringify(await ghJson(getRes))}`);
}

for (const label of labels) {
  await upsertLabel(label);
}
console.log(`✅ Synced ${labels.length} label(s).`);
