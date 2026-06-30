#!/usr/bin/env bash
#
# verify_mastery_fingerprint.sh — fail-closed verification of the v2 mastery
# shadow-gate validation fingerprint.
#
# Hashes canonical Git blobs rather than platform-specific working-tree bytes.
# This keeps verification stable across LF and CRLF checkouts while still
# failing if any fingerprinted file has staged or unstaged changes.
set -euo pipefail

MANIFEST="docs/ops/mastery_validation_fingerprint_manifest_v2.txt"
ATTEST="docs/ops/mastery_validation_fingerprint_manifest_v2.attestation.txt"
PR7="docs/ops/pr7_shadow_gate_results.md"
CHECKLIST="docs/status/career-copilot-checklist.md"

_repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || {
  echo "ERROR: not inside a Git repository" >&2
  exit 1
}
cd "$_repo_root"

for _control in "$MANIFEST" "$ATTEST" "$PR7" "$CHECKLIST"; do
  [[ -f "$_control" ]] || {
    echo "ERROR: required control file not found: $_control" >&2
    exit 1
  }

  if ! git diff --quiet -- "$_control"; then
    echo "ERROR: unstaged control-file changes detected: $_control" >&2
    exit 1
  fi

  if ! git diff --cached --quiet -- "$_control"; then
    echo "ERROR: staged control-file changes detected: $_control" >&2
    exit 1
  fi
done

# Normalize CRLF only while parsing control records. Fingerprinted source files
# are hashed directly from canonical HEAD blobs.
readarray -t _files < <(
  tr -d '\r' < "$MANIFEST" |
    grep -v '^#' |
    sed '/^[[:space:]]*$/d'
)

_actual=${#_files[@]}

_expected=$(
  tr -d '\r' < "$ATTEST" |
    awk -F': *' '/^# File count/ {print $2; exit}'
)

if [[ -z "${_expected:-}" || "$_actual" -ne "$_expected" ]]; then
  echo "ERROR: manifest has $_actual files; attestation expects ${_expected:-?}" >&2
  exit 1
fi

_recomputed_file=$(mktemp)
_attested_file=$(mktemp)
trap 'rm -f "$_recomputed_file" "$_attested_file"' EXIT

for _f in "${_files[@]}"; do
  [[ -n "$_f" ]] || {
    echo "ERROR: empty path in manifest" >&2
    exit 1
  }

  [[ -f "$_f" ]] || {
    echo "ERROR: manifest file missing from checkout: $_f" >&2
    exit 1
  }

  if ! git cat-file -e "HEAD:${_f}" 2>/dev/null; then
    echo "ERROR: manifest path does not exist as a blob in HEAD: $_f" >&2
    exit 1
  fi

  if ! git diff --quiet -- "$_f"; then
    echo "ERROR: unstaged drift detected in fingerprinted file: $_f" >&2
    exit 1
  fi

  if ! git diff --cached --quiet -- "$_f"; then
    echo "ERROR: staged drift detected in fingerprinted file: $_f" >&2
    exit 1
  fi

  _hash=$(
    git cat-file blob "HEAD:${_f}" |
      sha256sum |
      awk '{print $1}'
  )

  printf '%s  %s\n' "$_hash" "$_f" >> "$_recomputed_file"
done

tr -d '\r' < "$ATTEST" |
  grep -vE '^#|^[[:space:]]*$' \
  > "$_attested_file"

if ! diff -u "$_attested_file" "$_recomputed_file" >/dev/null; then
  echo "ERROR: per-file SHA-256 attestation mismatch. Drift detected:" >&2
  diff -u "$_attested_file" "$_recomputed_file" >&2 || true
  exit 1
fi

_combined=$(sha256sum "$_recomputed_file" | awk '{print $1}')

_attest_digest=$(
  tr -d '\r' < "$ATTEST" |
    awk -F': *' '/^# Combined digest/ {print $2; exit}'
)

if [[ "$_combined" != "$_attest_digest" ]]; then
  echo "ERROR: combined digest mismatch." >&2
  echo "  recomputed: $_combined" >&2
  echo "  attested:   $_attest_digest" >&2
  exit 1
fi

for _doc in "$MANIFEST" "$PR7" "$CHECKLIST"; do
  if ! grep -qF "$_combined" < <(tr -d '\r' < "$_doc"); then
    echo "ERROR: combined digest $_combined not recorded in $_doc" >&2
    exit 1
  fi
done

if [[ -n "${SKIP_SHA:-}" ]]; then
  :
elif [[ -n "${EXPECTED_SHA:-}" ]]; then
  _head=$(git rev-parse HEAD 2>/dev/null || echo "")
  if [[ "$_head" != "$EXPECTED_SHA" ]]; then
    echo "ERROR: checkout SHA $_head does not match EXPECTED_SHA $EXPECTED_SHA" >&2
    exit 1
  fi
else
  echo "ERROR: pass EXPECTED_SHA=<40-hex> to pin the checkout," >&2
  echo "       or SKIP_SHA=1 for a content-only check." >&2
  exit 1
fi

echo "OK: ${_actual} files, combined freeze hash ${_combined}${EXPECTED_SHA:+ @ }${EXPECTED_SHA:-}"
