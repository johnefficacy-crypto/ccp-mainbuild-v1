# End-to-end tests (Playwright)

E2E coverage for the three critical study flows that unit/RTL tests cannot
catch — route lazy-loading, suspense boundaries, and cross-page state:

| Flow | Spec | What it proves |
|---|---|---|
| Attempt happy path | `e2e/flows/attempt-happy-path.spec.ts` | Start → section-locked answering → Save & Next → submit → result; charts code-split (chunk fetched on tab click) |
| Submit → review | `e2e/flows/submit-review-navigation.spec.ts` | Result → review; filter reduces list + reflects in URL; palette navigation; review-mode shows correct option + explanation |
| Report → attempt drill | `e2e/flows/report-attempt-drill.spec.ts` | 5-point score trend → click a point → attempt result → browser back restores the chart client-side |

Everything lives under `app/frontend/e2e/`:

```
e2e/
  fixtures/
    env.ts            reads + validates E2E_* env
    seedUser.ts       idempotent seeded aspirant (Supabase admin API) + UI login
    seedAttempt.ts    attempt factory via the real backend API + truncate-and-seed reset
    globalSetup.ts    ensures the user + verifies the mock content seed is present
  flows/              the three specs above
  playwright.config.ts
```

## What the suite drives

The flows run against the **real stack**, not mocks: a production build of the
SPA, the FastAPI backend, and a local Supabase. That is the only way to catch
lazy-chunk and suspense regressions.

Test data discipline (per the spec): fixtures never touch prod data.

- **Content** (the `ibps-po-prelims-mock-1` template: 3 sections × 5 questions,
  section locks on, option 1 always correct) is seeded by
  `app/supabase/seeds/e2e_fixtures.sql` — idempotent upserts on fixed UUIDs,
  rows tagged `source_type = 'e2e_fixture'`.
- **User** is created idempotently via the Supabase admin API in `globalSetup`.
- **Attempts** are created at test time through the real backend API
  (`seedAttempt.ts`), and `resetAttempts()` deletes the user's attempts before
  each seeding pass — so re-runs never drift and never trip the
  "one active attempt per (user, template)" guard.

## Run it locally

Prereqs: Docker, the [Supabase CLI](https://supabase.com/docs/guides/cli),
Node 20, Python 3.12.

```bash
# 1. Local Supabase (applies migrations) + content seed
cd app/supabase
supabase start
psql "$(supabase status -o json | jq -r '.DB_URL')" -f seeds/e2e_fixtures.sql

# capture connection details (printed by `supabase status`)
export SB_API_URL=$(supabase status -o json | jq -r '.API_URL')
export SB_ANON_KEY=$(supabase status -o json | jq -r '.ANON_KEY')
export SB_SERVICE_ROLE_KEY=$(supabase status -o json | jq -r '.SERVICE_ROLE_KEY')

# 2. Backend
cd ../backend
pip install -r requirements.txt
NEXT_PUBLIC_SUPABASE_URL=$SB_API_URL \
NEXT_PUBLIC_SUPABASE_ANON_KEY=$SB_ANON_KEY \
SUPABASE_SERVICE_ROLE_KEY=$SB_SERVICE_ROLE_KEY \
DATABASE_URL=$(cd ../supabase && supabase status -o json | jq -r '.DB_URL') \
uvicorn server:app --host 127.0.0.1 --port 8000 &

# 3. Frontend build (Playwright serves it on :3000 automatically)
cd ../frontend
cp e2e/.env.example e2e/.env   # then fill SB_* values into the E2E_* vars
REACT_APP_SUPABASE_URL=$SB_API_URL \
REACT_APP_SUPABASE_ANON_KEY=$SB_ANON_KEY \
REACT_APP_BACKEND_URL=http://127.0.0.1:8000 \
npm run build

# 4. Run
npx playwright install --with-deps chromium
npm run e2e
```

`npm run e2e` reads `app/frontend/e2e/.env` (gitignored). Beyond filling in
credentials, no manual setup is required — the user, content check, and
attempts are all seeded automatically.

Useful variants:

```bash
npm run e2e:ui                       # Playwright UI mode (watch/inspect)
npm run e2e -- --headed              # watch a real browser
npm run e2e -- flows/report-attempt-drill.spec.ts
npm run e2e:report                   # open the last HTML report
E2E_NO_WEBSERVER=1 npm run e2e       # reuse a server you started yourself
```

## In CI

`.github/workflows/e2e.yml` runs on every PR: starts Supabase, applies the
seed, boots the backend, builds the SPA, installs Chromium, and runs the suite.
The HTML report is uploaded as an artifact; on failure the backend log is dumped.

Tuning for the acceptance budget (< 5 min wall, < 2% flake): one worker + serial
flows (the shared seeded user + the active-attempt guard make parallelism a flake
source), and CI retries to absorb rare cold-chunk/network blips (a pass-only-on-retry
test is reported as flaky, so retries don't hide real failures).

## Adding a flow

1. Add `e2e/flows/<name>.spec.ts`.
2. Reuse `fixtures/seedUser` (login) and `fixtures/seedAttempt` (data). Add a new
   factory there rather than hand-writing DB rows — go through the backend API so
   scoring/derivation stays realistic.
3. Select by `data-testid`. If the markup lacks one, add it in the component (the
   attempt/result/review/progress surfaces are already instrumented).
4. Keep flows independent and serial-safe: reset state in `beforeAll`.

## Debugging failures

- **Report/trace**: `npm run e2e:report`; traces are captured on first retry
  (`use.trace`). Open a trace with `npx playwright show-trace <trace.zip>`.
- **Watch it**: `npm run e2e -- --headed --debug` or `npm run e2e:ui`.
- **"Template … not found"** from `globalSetup`/`resetAttempts`: the content seed
  wasn't applied — re-run the `psql … e2e_fixtures.sql` step.
- **Auth/redirect hangs**: confirm `REACT_APP_SUPABASE_URL/ANON_KEY` used for the
  build match the running Supabase, and `REACT_APP_BACKEND_URL` points at the
  backend. A mismatch leaves the app stuck on the auth-checking screen.
- **No options / empty attempt**: the template needs `mock_template_sections`
  rows with a `fixed` selector; the seed creates these.

## Bundle regression gate

Related guard (not Playwright): `scripts/check-bundle.js`, run in CI after the
production build via `npm run check:bundle-budget`. It keeps admin/prototype/
heavy-report/large-feature code and chart libs out of the initial chunk and
enforces the gzip budget. See `BUNDLE_BUDGET.md`.
