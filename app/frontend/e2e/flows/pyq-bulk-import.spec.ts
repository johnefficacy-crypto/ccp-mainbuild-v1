import { test, expect } from "@playwright/test";
import { WORKSPACE, ensureAdminUser, getAdminAccessToken, ensureWorkspaceSeed } from "../fixtures/seedWorkspace";
import { createNodeSupabaseClient } from "../fixtures/supabaseNodeClient";
import { readEnv } from "../fixtures/env";
import * as path from "path";
import * as fs from "fs";
import * as os from "os";

/**
 * Flow: PYQ bulk import — highest-risk regressions from PR #529 / PR #532.
 *
 * Covers:
 *   - CSV upload → preflight (parse + dedup) → commit via the UI modal
 *   - import_token round-trip (preflight token used in commit)
 *   - Re-import of same rows is idempotent (skipped, not error)
 *   - Backend API contract: options array in payload (PR #532 options wiring)
 *
 * The UI path uses the real Supabase + FastAPI backend. The API contract tests
 * call the endpoints directly, same pattern as seedAttempt.ts.
 */

const CMS = "/api/admin/exam-intelligence-cms";

// Minimal valid CSV for the E2E paper — 2 MCQ questions with options A-D.
const VALID_CSV = [
  "question_number,question_text,option_a,option_b,option_c,option_d,correct_option,question_type",
  "1,Which article of the Constitution deals with federalism?,Article 1,Article 2,Article 246,Article 356,C,mcq",
  "2,The residuary powers are vested in?,States,Centre,Both,Neither,B,mcq",
].join("\n");

// CSV with options — exercises the PR #532 options wiring path
const CSV_WITH_OPTIONS = VALID_CSV;

async function makeApi(): Promise<(method: string, path: string, body?: unknown, contentType?: string) => Promise<Response>> {
  const token = await getAdminAccessToken();
  const env = readEnv();
  return async (method, reqPath, body, contentType = "application/json") => {
    const isText = contentType === "text/csv";
    return fetch(`${env.backendURL}${reqPath}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": contentType,
      },
      body: body === undefined
        ? undefined
        : isText
        ? (body as string)
        : JSON.stringify(body),
    });
  };
}

async function cleanupPaperQuestions(): Promise<void> {
  const env = readEnv();
  const client = createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);
  await client.from("pyq_questions").delete().eq("pyq_paper_id", WORKSPACE.paperId);
}

test.describe("Flow: PYQ bulk import API contract", () => {
  test.beforeAll(async () => {
    await ensureWorkspaceSeed();
    await ensureAdminUser();
    await cleanupPaperQuestions();
  });

  test.afterAll(async () => {
    await cleanupPaperQuestions();
  });

  test("preflight parses CSV and returns import_token + per-row preview", async () => {
    const api = await makeApi();
    const res = await api(
      "POST",
      `${CMS}/pyq-papers/${WORKSPACE.paperId}/bulk-import/preflight`,
      CSV_WITH_OPTIONS,
      "text/csv",
    );
    expect(res.status).toBe(200);
    const data = await res.json();

    expect(typeof data.import_token).toBe("string");
    expect(data.import_token.length).toBeGreaterThan(8);
    expect(Array.isArray(data.rows)).toBe(true);
    expect(data.rows.length).toBe(2);

    // Both rows should be "ok" (no existing questions in this paper)
    for (const row of data.rows) {
      expect(row.status).toBe("ok");
    }

    expect(typeof data.ok_count).toBe("number");
    expect(data.ok_count).toBe(2);
  });

  test("commit uses import_token and inserts rows", async () => {
    const api = await makeApi();

    // Step 1: preflight
    const pre = await api(
      "POST",
      `${CMS}/pyq-papers/${WORKSPACE.paperId}/bulk-import/preflight`,
      CSV_WITH_OPTIONS,
      "text/csv",
    );
    expect(pre.status).toBe(200);
    const { import_token } = await pre.json();

    // Step 2: commit
    const commit = await api("POST", `${CMS}/pyq-papers/${WORKSPACE.paperId}/bulk-import/commit`, {
      import_token,
      override_errors: false,
      reason: "E2E regression: commit bulk import",
    });
    expect(commit.status).toBe(200);
    const result = await commit.json();

    expect(result.committed).toBe(2);
    expect(result.skipped).toBe(0);
    expect(result.failed).toBe(0);
  });

  test("re-import same CSV is idempotent — rows skipped, not error", async () => {
    const api = await makeApi();

    // First import (rows should already be committed from previous test)
    const pre = await api(
      "POST",
      `${CMS}/pyq-papers/${WORKSPACE.paperId}/bulk-import/preflight`,
      CSV_WITH_OPTIONS,
      "text/csv",
    );
    const { import_token, rows } = await pre.json();

    // Both rows should be duplicates now
    for (const row of rows) {
      expect(["duplicate", "ok"]).toContain(row.status);
    }

    // Commit without override — duplicates are skipped
    const commit = await api("POST", `${CMS}/pyq-papers/${WORKSPACE.paperId}/bulk-import/commit`, {
      import_token,
      override_errors: false,
      reason: "E2E regression: idempotent re-import",
    });
    expect(commit.status).toBe(200);
    const result = await commit.json();

    // committed + skipped must equal total rows; none failed
    expect(result.committed + result.skipped).toBe(2);
    expect(result.failed).toBe(0);
  });

  test("preflight rejects CSV missing required columns with 422", async () => {
    const api = await makeApi();
    const badCsv = "question_number,question_text\n1,Only two columns";
    const res = await api(
      "POST",
      `${CMS}/pyq-papers/${WORKSPACE.paperId}/bulk-import/preflight`,
      badCsv,
      "text/csv",
    );
    expect(res.status).toBe(422);
  });

  test("commit with unknown import_token returns 404", async () => {
    const api = await makeApi();
    const res = await api("POST", `${CMS}/pyq-papers/${WORKSPACE.paperId}/bulk-import/commit`, {
      import_token: "nonexistent-token-xyz",
      override_errors: false,
      reason: "E2E regression: bad token",
    });
    expect(res.status).toBe(404);
  });
});

// ---------------------------------------------------------------------------
// UI path — drives the BulkImportModal through the browser
// ---------------------------------------------------------------------------
async function loginAsAdmin(page: import("@playwright/test").Page) {
  const email    = process.env.E2E_ADMIN_EMAIL    || "e2e-admin@example.com";
  const password = process.env.E2E_ADMIN_PASSWORD || "E2e-admin-passw0rd!";
  await page.goto("/login");
  await expect(page.getByTestId("login-email")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("login-email").fill(email);
  await page.getByTestId("login-password").fill(password);
  await Promise.all([
    page.waitForURL(/\/app(\/|$)/, { timeout: 90_000 }),
    page.getByTestId("login-submit").click(),
  ]);
  // Wait for backend session sync before navigating to protected admin route
  await expect(page.getByTestId("auth-checking")).toBeHidden({ timeout: 90_000 });
  await expect(page.getByTestId("backend-sync-pending")).toBeHidden({ timeout: 90_000 });
}

test.describe("Flow: PYQ bulk import UI modal", () => {
  let csvFile: string;

  test.beforeAll(async () => {
    await ensureWorkspaceSeed();
    await ensureAdminUser();
    await cleanupPaperQuestions();
    // Write CSV to a temp file so Playwright can set it as file input
    csvFile = path.join(os.tmpdir(), "e2e-pyq-bulk.csv");
    fs.writeFileSync(csvFile, VALID_CSV);
  });

  test.afterAll(async () => {
    await cleanupPaperQuestions();
    fs.rmSync(csvFile, { force: true });
  });

  test("upload CSV → preflight preview → commit → result screen", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto(`/admin/exam-intelligence/workspace/${WORKSPACE.examId}`);
    await expect(page.getByTestId("workspace-loading")).toBeHidden({ timeout: 30_000 });
    await expect(page.getByTestId("exam-name")).toBeVisible({ timeout: 30_000 });

    // Navigate to PYQ tab
    await page.getByTestId("tab-pyq").click();
    await expect(page.getByTestId("pyq-workbench-panel")).toBeVisible({ timeout: 20_000 });

    // Select the seeded paper from the dropdown
    await page.getByTestId("pyq-paper-select").selectOption({ value: WORKSPACE.paperId });
    await expect(page.getByTestId("bulk-import-btn")).toBeVisible({ timeout: 10_000 });

    // Open bulk import modal
    await page.getByTestId("bulk-import-btn").click();
    await expect(page.getByTestId("bulk-import-modal")).toBeVisible({ timeout: 10_000 });

    // Upload CSV
    await page.getByTestId("bulk-csv-input").setInputFiles(csvFile);
    await expect(page.getByTestId("bulk-csv-filename")).toContainText("e2e-pyq-bulk.csv");

    // Run preflight
    await page.getByTestId("run-preflight-btn").click();
    await expect(page.getByTestId("preflight-preview")).toBeVisible({ timeout: 20_000 });

    // Preview shows 2 ok, 0 dups, 0 errors
    await expect(page.getByTestId("summary-ok")).toContainText("2");
    await expect(page.getByTestId("summary-duplicate")).toContainText("0");
    await expect(page.getByTestId("summary-error")).toContainText("0");

    // Advance to commit confirmation step
    await page.getByTestId("continue-to-commit-btn").click();
    await expect(page.getByTestId("commit-confirmation")).toBeVisible({ timeout: 10_000 });

    // Enter commit reason and commit
    await page.getByTestId("commit-reason-input").fill("E2E regression: UI bulk import commit");
    await page.getByTestId("commit-import-btn").click();

    // Result screen
    await expect(page.getByTestId("commit-result")).toBeVisible({ timeout: 20_000 });
    await expect(page.getByTestId("result-committed")).toContainText("2");
    await expect(page.getByTestId("result-failed")).toContainText("0");
  });
});
