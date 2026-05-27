import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for the three critical study-flow journeys.
 *
 * The suite drives the REAL stack: a production build of the SPA served
 * statically, talking to the FastAPI backend, talking to a (local) Supabase.
 * See docs/testing/e2e.md for how to bring that stack up locally and in CI.
 *
 * Tuning notes (acceptance: < 5 min wall, < 2% flake):
 *  - One worker, serial flows. The flows share a single seeded user and the
 *    backend enforces "one active attempt per (user, template)", so parallel
 *    attempts would collide. Serial execution removes that whole class of flake.
 *  - Retries in CI absorb the rare cold-chunk / network hiccup without hiding
 *    real failures (a test that only passes on retry is reported as "flaky").
 */
const BASE_URL = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";

export default defineConfig({
  testDir: "./flows",
  outputDir: "./test-results",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  globalSetup: "./fixtures/globalSetup.ts",
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  // Serve the production build unless a server is already running (or the
  // caller opts out, e.g. when pointing E2E_BASE_URL at a deployed preview).
  webServer: process.env.E2E_NO_WEBSERVER
    ? undefined
    : {
        command: "npx --yes serve -s ../build -l 3000",
        url: BASE_URL,
        timeout: 120_000,
        reuseExistingServer: !process.env.CI,
      },
});
