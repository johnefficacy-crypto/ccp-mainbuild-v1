import { test, expect, type Page } from "@playwright/test";
import { WORKSPACE, ensureAdminUser } from "../fixtures/seedWorkspace";
import { readEnv } from "../fixtures/env";

/**
 * Flow: workspace shell — highest-risk regressions from PR #529 / PR #548.
 *
 * Covers:
 *   - Admin user can log in and reach the workspace URL
 *   - Workspace context endpoint returns the seeded exam (exam-name visible)
 *   - All tab buttons render in the tab-strip
 *   - PYQ Workbench tab is enabled (seed has a pyq_paper → readiness "partial")
 *   - Clicking PYQ tab renders pyq-workbench-panel
 *
 * Does NOT require the NLP/Tesseract pipeline — syllabus tab stays disabled,
 * which is the expected state given no syllabus documents.
 */

async function loginAsAdmin(page: Page): Promise<void> {
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
}

/**
 * Navigate to a workspace URL and wait for the shell to finish loading.
 * Mirrors the gotoProtectedPage pattern from seedUser.ts: waits for
 * auth-checking and backend-sync-pending to clear before asserting content.
 */
async function gotoWorkspace(page: Page): Promise<void> {
  await page.goto(`/admin/exam-intelligence/workspace/${WORKSPACE.examId}`);
  await expect(page.getByTestId("auth-checking")).toBeHidden({ timeout: 90_000 });
  await expect(page.getByTestId("backend-sync-pending")).toBeHidden({ timeout: 90_000 });
  await expect(page.getByTestId("workspace-loading")).toBeHidden({ timeout: 30_000 });
}

test.describe("Flow: workspace shell", () => {
  test.beforeAll(async () => {
    await ensureAdminUser();
  });

  test("workspace loads exam name and tab strip", async ({ page }) => {
    await loginAsAdmin(page);
    await gotoWorkspace(page);

    await expect(page.getByTestId("exam-name")).toContainText("E2E Workspace Exam", {
      timeout: 30_000,
    });
    await expect(page.getByTestId("tab-strip")).toBeVisible();
  });

  test("all workspace tabs are rendered", async ({ page }) => {
    await loginAsAdmin(page);
    await gotoWorkspace(page);
    await expect(page.getByTestId("exam-name")).toBeVisible({ timeout: 30_000 });

    for (const tabId of ["setup", "documents", "syllabus", "pyq", "updates", "competition", "review"]) {
      await expect(page.getByTestId(`tab-${tabId}`)).toBeVisible();
    }
  });

  test("PYQ Workbench tab is enabled when pyq_paper exists", async ({ page }) => {
    await loginAsAdmin(page);
    await gotoWorkspace(page);
    await expect(page.getByTestId("exam-name")).toBeVisible({ timeout: 30_000 });

    // PYQ tab must NOT be disabled — seed has 1 paper → readiness "partial" != "empty"
    const pyqTab = page.getByTestId("tab-pyq");
    await expect(pyqTab).toBeVisible();
    await expect(pyqTab).not.toBeDisabled();
  });

  test("clicking PYQ tab renders pyq-workbench-panel", async ({ page }) => {
    await loginAsAdmin(page);
    await gotoWorkspace(page);
    await expect(page.getByTestId("exam-name")).toBeVisible({ timeout: 30_000 });

    await page.getByTestId("tab-pyq").click();
    await expect(page.getByTestId("pyq-workbench-panel")).toBeVisible({ timeout: 20_000 });
  });

  test("non-admin user is redirected away from workspace", async ({ page }) => {
    const env = readEnv();
    await page.goto("/login");
    await expect(page.getByTestId("login-email")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("login-email").fill(env.user.email);
    await page.getByTestId("login-password").fill(env.user.password);
    await Promise.all([
      page.waitForURL(/\/app(\/|$)/, { timeout: 90_000 }),
      page.getByTestId("login-submit").click(),
    ]);
    await expect(page.getByTestId("auth-checking")).toBeHidden({ timeout: 90_000 });
    await expect(page.getByTestId("backend-sync-pending")).toBeHidden({ timeout: 90_000 });

    await page.goto(`/admin/exam-intelligence/workspace/${WORKSPACE.examId}`);
    // ProtectedRoute redirects non-admin users back to /app
    await expect(page).toHaveURL(/\/app(\/|$)/, { timeout: 20_000 });
  });
});
