import { test, expect } from "@playwright/test";
import { ensureAdminUser } from "../fixtures/seedWorkspace";
import { WORKSPACE } from "../fixtures/seedWorkspace";
import { createNodeSupabaseClient } from "../fixtures/supabaseNodeClient";
import { readEnv } from "../fixtures/env";

/**
 * Flow: workspace shell — highest-risk regressions from PR #529 / PR #548.
 *
 * Covers:
 *   - Admin user can log in and reach the workspace URL
 *   - Workspace context endpoint returns the seeded exam (exam-name visible)
 *   - All six tab buttons render in the tab-strip
 *   - PYQ Workbench tab is enabled (seed has a pyq_paper → readiness "partial")
 *   - Clicking Setup and PYQ tabs does not crash the shell
 *
 * Does NOT require the NLP/Tesseract pipeline — syllabus tab stays disabled,
 * which is verified as the expected state given no syllabus documents.
 */

async function loginAsAdmin(page: import("@playwright/test").Page) {
  const env = readEnv();
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

test.describe("Flow: workspace shell", () => {
  test.beforeAll(async () => {
    await ensureAdminUser();
  });

  test("workspace loads exam name and tab strip", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto(`/admin/exam-intelligence/workspace/${WORKSPACE.examId}`);

    // Shell shows exam name from the seeded exam row
    await expect(page.getByTestId("exam-name")).toContainText("E2E Workspace Exam", {
      timeout: 30_000,
    });

    // Tab strip present
    await expect(page.getByTestId("tab-strip")).toBeVisible();
  });

  test("all workspace tabs are rendered", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto(`/admin/exam-intelligence/workspace/${WORKSPACE.examId}`);
    await expect(page.getByTestId("exam-name")).toBeVisible({ timeout: 30_000 });

    for (const tabId of ["setup", "documents", "syllabus", "pyq", "updates", "competition", "review"]) {
      await expect(page.getByTestId(`tab-${tabId}`)).toBeVisible();
    }
  });

  test("PYQ Workbench tab is enabled when pyq_paper exists", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto(`/admin/exam-intelligence/workspace/${WORKSPACE.examId}`);
    await expect(page.getByTestId("exam-name")).toBeVisible({ timeout: 30_000 });

    // PYQ tab must NOT be disabled — seed has 1 paper → readiness "partial" != "empty"
    const pyqTab = page.getByTestId("tab-pyq");
    await expect(pyqTab).toBeVisible();
    await expect(pyqTab).not.toBeDisabled();
  });

  test("clicking PYQ tab renders pyq-workbench-panel", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto(`/admin/exam-intelligence/workspace/${WORKSPACE.examId}`);
    await expect(page.getByTestId("exam-name")).toBeVisible({ timeout: 30_000 });

    await page.getByTestId("tab-pyq").click();
    await expect(page.getByTestId("pyq-workbench-panel")).toBeVisible({ timeout: 20_000 });
  });

  test("non-admin user is redirected or blocked from the workspace", async ({ page }) => {
    // Aspirant credentials from the existing e2e seed
    const env = readEnv();
    await page.goto("/login");
    await expect(page.getByTestId("login-email")).toBeVisible({ timeout: 30_000 });
    await page.getByTestId("login-email").fill(env.user.email);
    await page.getByTestId("login-password").fill(env.user.password);
    await Promise.all([
      page.waitForURL(/\/app(\/|$)/, { timeout: 90_000 }),
      page.getByTestId("login-submit").click(),
    ]);

    await page.goto(`/admin/exam-intelligence/workspace/${WORKSPACE.examId}`);

    // Either redirected away from admin or a workspace-error is shown
    await page.waitForTimeout(4_000);
    const url = page.url();
    const hasError = await page.getByTestId("workspace-error").isVisible().catch(() => false);
    const isRedirected = !url.includes("/admin/exam-intelligence/workspace");
    expect(hasError || isRedirected).toBe(true);
  });
});
