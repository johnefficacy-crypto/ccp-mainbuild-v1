#!/usr/bin/env bash
#
# verify_mastery_fingerprint.sh — fail-closed verification of the v2 mastery
# shadow-gate validation fingerprint.
#
# Checks, all fail-closed:
#   1. manifest file count matches the attestation header
#   2. every listed file exists in the checkout
#   3. per-file SHA-256 set matches the committed attestation
#   4. the recomputed combined digest matches the attestation
#   5. the SAME combined digest is recorded in the manifest, pr7_shadow_gate_results.md,
#      and the career-copilot checklist (no cross-document drift)
#   6. (optional) the checkout SHA matches an expected/pinned SHA
#
# Run from the repo root:  bash scripts/verify_mastery_fingerprint.sh
# Pin the checkout (operator, at window_start / window_end):
#                          EXPECTED_SHA=<40-hex> bash scripts/verify_mastery_fingerprint.sh
#
# This is the operator's window_start / window_end verification tool. A change to
# any listed file resets the shadow observation clock and requires the attestation
# to be regenerated and the freeze hash re-approved.
set -euo pipefail

MANIFEST="docs/ops/mastery_validation_fingerprint_manifest_v2.txt"
ATTEST="docs/ops/mastery_validation_fingerprint_manifest_v2.attestation.txt"
PR7="docs/ops/pr7_shadow_gate_results.md"
CHECKLIST="docs/status/career-copilot-checklist.md"

[[ -f "$MANIFEST" ]] || { echo "ERROR: manifest not found: $MANIFEST" >&2; exit 1; }
[[ -f "$ATTEST"   ]] || { echo "ERROR: attestation not found: $ATTEST" >&2; exit 1; }

# 1) Resolve the manifest file list (comments and blanks stripped).
readarray -t _files < <(grep -v '^#' "$MANIFEST" | grep -v '^$')
_actual=${#_files[@]}

# 2) Cross-check the count against the attestation header.
_expected=$(awk -F': *' '/^# File count/ {print $2; exit}' "$ATTEST")
if [[ -z "${_expected:-}" || "$_actual" -ne "$_expected" ]]; then
  echo "ERROR: manifest has $_actual files; attestation expects ${_expected:-?}" >&2
  exit 1
fi

# 3) Every listed file must exist.
for _f in "${_files[@]}"; do
  [[ -f "$_f" ]] || { echo "ERROR: manifest file missing from checkout: $_f" >&2; exit 1; }
done

# 4) Recompute per-file hashes and diff against the attestation body.
_recomputed=$(sha256sum "${_files[@]}")
_attested=$(grep -vE '^#|^$' "$ATTEST")
if ! diff <(printf '%s\n' "$_attested") <(printf '%s\n' "$_recomputed") >/dev/null; then
  echo "ERROR: per-file SHA-256 attestation mismatch. Drift detected:" >&2
  diff <(printf '%s\n' "$_attested") <(printf '%s\n' "$_recomputed") >&2 || true
  exit 1
fi

# 5) Recompute the combined digest and compare to the attestation header.
_combined=$(printf '%s\n' "$_recomputed" | sha256sum | awk '{print $1}')
_attest_digest=$(awk -F': *' '/^# Combined digest/ {print $2; exit}' "$ATTEST")
if [[ "$_combined" != "$_attest_digest" ]]; then
  echo "ERROR: combined digest mismatch." >&2
  echo "  recomputed: $_combined" >&2
  echo "  attested:   $_attest_digest" >&2
  exit 1
fi

# 6) Cross-document consistency: the SAME digest must be recorded in the manifest,
#    pr7_shadow_gate_results.md, and the checklist. Catches doc/attestation drift.
for _doc in "$MANIFEST" "$PR7" "$CHECKLIST"; do
  if [[ -f "$_doc" ]] && ! grep -qF "$_combined" "$_doc"; then
    echo "ERROR: combined digest $_combined not recorded in $_doc (document drift)" >&2
    exit 1
  fi
done

# 7) Optional pinned-SHA assertion (operator supplies the window_start SHA).
if [[ -n "${EXPECTED_SHA:-}" ]]; then
  _head=$(git rev-parse HEAD 2>/dev/null || echo "")
  if [[ "$_head" != "$EXPECTED_SHA" ]]; then
    echo "ERROR: checkout SHA $_head does not match EXPECTED_SHA $EXPECTED_SHA" >&2
    exit 1
  fi
fi

echo "OK: ${_actual} files, combined freeze hash ${_combined}${EXPECTED_SHA:+ @ }${EXPECTED_SHA:-}"
