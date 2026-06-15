#!/usr/bin/env bash
# Guarded applier for the E2E fixture seeds.
#
# The E2E seeds write test-only content (mock_question_bank rows tagged
# source_type='e2e_fixture', a seeded workspace, …) that must NEVER land in a
# production database. This wrapper mirrors the hard guard the Playwright
# harness already enforces on E2E_SUPABASE_URL (app/frontend/e2e/fixtures/env.ts
# assertNotProdSupabase): it REFUSES any database URL whose host ends with
# `.supabase.co` — the canonical hosted-Supabase pattern — and only then applies
# the seed SQL with psql.
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

# Extract the host from a postgres(ql)://[user[:pass]@]host[:port][/db] URL.
host="$(printf '%s' "$db_url" | sed -E 's#^[a-zA-Z+]+://([^@/]*@)?([^:/?]+).*#\2#')"

if [[ "$host" == *.supabase.co ]]; then
  printf '%s\n' \
    "──────────────────────────────────────────────────────────────────────" \
    "HARD STOP — refusing to apply E2E fixtures to a PRODUCTION Supabase host:" \
    "  host: ${host}" \
    "" \
    "The E2E seeds write test-only data (e.g. mock_question_bank rows tagged" \
    "source_type='e2e_fixture') and must only ever run against a local/E2E DB." \
    "" \
    "Fix: point at the local stack instead:" \
    "  supabase start          # in app/supabase/" \
    "  supabase status         # DB URL → postgresql://...@127.0.0.1:54322/postgres" \
    "See docs/testing/e2e.md." \
    "──────────────────────────────────────────────────────────────────────" >&2
  exit 1
fi

for seed in "$@"; do
  echo "Applying E2E seed: ${seed} → ${host}"
  psql "$db_url" -v ON_ERROR_STOP=1 -f "$seed"
done
