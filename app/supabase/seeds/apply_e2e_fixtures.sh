#!/usr/bin/env bash
# Guarded applier for the E2E fixture seeds.
#
# The E2E seeds write test-only content (mock_question_bank rows tagged
# source_type='e2e_fixture', a seeded workspace, …) that must NEVER land in a
# production database. In the spirit of the Playwright harness guard on
# E2E_SUPABASE_URL (app/frontend/e2e/fixtures/env.ts assertNotProdSupabase),
# this wrapper enforces a LOCAL-ONLY ALLOWLIST: it applies the seed SQL only when
# the target DB host is local (127.0.0.1, localhost, ::1, [::1]) and HARD-STOPS
# on anything else. Failing closed (allowlist, not blacklist) means a new hosted
# pattern — e.g. a *.supabase.com pooler host — is refused by default.
#
# Usage:
#   apply_e2e_fixtures.sh <db_url> <seed.sql> [<seed.sql> ...]
#
# A local `supabase start` always binds 127.0.0.1, so legitimate local/E2E URLs
# are never blocked.
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <db_url> <seed.sql> [<seed.sql> ...]" >&2
  exit 2
fi

db_url="$1"
shift

# Extract the host from a postgres(ql)://[user[:pass]@]host[:port][/db] URL,
# handling the bracketed IPv6 form ([::1]).
authority="${db_url#*://}"      # drop scheme
authority="${authority%%[/?]*}" # drop /path and ?query
authority="${authority#*@}"     # drop userinfo (user[:pass]@), if present
if [[ "$authority" == \[* ]]; then
  host="${authority%%]*}]"      # [::1]:5432 -> [::1]
else
  host="${authority%%:*}"       # 127.0.0.1:5432 -> 127.0.0.1
fi

# ALLOWLIST: only local hosts may receive the test-only seeds. Anything else —
# including hosted Supabase (*.supabase.co) and pooler hosts (*.supabase.com) —
# is refused. Fail closed: an unrecognised host is treated as production.
case "$host" in
  127.0.0.1 | localhost | ::1 | "[::1]") ;;
  *)
    printf '%s\n' \
      "──────────────────────────────────────────────────────────────────────" \
      "HARD STOP — refusing to apply E2E fixtures to a NON-LOCAL host:" \
      "  host: ${host}" \
      "" \
      "The E2E seeds write test-only data (e.g. mock_question_bank rows tagged" \
      "source_type='e2e_fixture') and may ONLY run against a local/E2E DB" \
      "(allowed hosts: 127.0.0.1, localhost, ::1, [::1])." \
      "" \
      "Fix: point at the local stack instead:" \
      "  supabase start          # in app/supabase/" \
      "  supabase status         # DB URL → postgresql://...@127.0.0.1:54322/postgres" \
      "See docs/testing/e2e.md." \
      "──────────────────────────────────────────────────────────────────────" >&2
    exit 1
    ;;
esac

for seed in "$@"; do
  echo "Applying E2E seed: ${seed} → ${host}"
  psql "$db_url" -v ON_ERROR_STOP=1 -f "$seed"
done
