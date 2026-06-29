#!/usr/bin/env bash
#
# verify_mastery_fingerprint.sh — fail-closed verification of the v2 mastery
# shadow-gate validation fingerprint.
#
# Recomputes the per-file SHA-256 set and the combined digest from the manifest
# file list, then checks them against the committed attestation. Any drift —
# changed file, added/removed manifest entry, or a digest that no longer matches
# the recorded freeze hash — exits non-zero.
#
# Run from the repo root:  bash scripts/verify_mastery_fingerprint.sh
#
# This is the operator's window_start / window_end verification tool. A change
# to any listed file resets the shadow observation clock and requires the
# attestation to be regenerated and the freeze hash re-approved.
set -euo pipefail

MANIFEST="docs/ops/mastery_validation_fingerprint_manifest_v2.txt"
ATTEST="docs/ops/mastery_validation_fingerprint_manifest_v2.attestation.txt"

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

# 5) Recompute the combined digest and compare to the recorded freeze hash.
_combined=$(printf '%s\n' "$_recomputed" | sha256sum | awk '{print $1}')
_recorded=$(awk -F': *' '/^# Combined digest/ {print $2; exit}' "$ATTEST")
if [[ "$_combined" != "$_recorded" ]]; then
  echo "ERROR: combined digest mismatch." >&2
  echo "  recomputed: $_combined" >&2
  echo "  attested:   $_recorded" >&2
  exit 1
fi

echo "OK: ${_actual} files, combined freeze hash ${_combined}"
