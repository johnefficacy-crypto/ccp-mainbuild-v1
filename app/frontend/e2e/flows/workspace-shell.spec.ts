import { test, expect, type Page } from "@playwright/test";
import {
  WORKSPACE,
  ensureAdminUser,
  ensureWorkspaceSeed,
  ensureSyllabusMapperSeed,
  cleanupSyllabusMapperSeed,
  loginAsAdmin,
} from "../fixtures/seedWorkspace";
import { ensureSeededUser, loginViaUi } from "../fixtures/seedUser";

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
    await ensureWorkspaceSeed();
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
    await ensureSeededUser();
    await loginViaUi(page);
    await expect(page.getByTestId("auth-checking")).toBeHidden({ timeout: 90_000 });
    await expect(page.getByTestId("backend-sync-pending")).toBeHidden({ timeout: 90_000 });

    await page.goto(`/admin/exam-intelligence/workspace/${WORKSPACE.examId}`);
    // ProtectedRoute redirects non-admin users back to /app
    await expect(page).toHaveURL(/\/app(\/|$)/, { timeout: 20_000 });
  });

  test("cycle picker is present (URLSearchParams.size regression guard)", async ({ page }) => {
    await loginAsAdmin(page);
    await gotoWorkspace(page);
    await expect(page.getByTestId("exam-name")).toBeVisible({ timeout: 30_000 });
    // Regression: ExamWorkspace must render cycle-picker regardless of cycles count.
    // A URLSearchParams.size bug previously caused a crash before the tab strip rendered.
    await expect(page.getByTestId("cycle-picker")).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Syllabus tab enabled when mentions exist
// ---------------------------------------------------------------------------

test.describe("Flow: workspace shell — Syllabus tab (PR8)", () => {
  test.beforeAll(async () => {
    await ensureWorkspaceSeed();
    await ensureAdminUser();
    await ensureSyllabusMapperSeed();
  });

  test.afterAll(async () => {
    await cleanupSyllabusMapperSeed();
  });

  test("Syllabus Mapper tab is enabled when syllabus_topic_mentions exist", async ({ page }) => {
    await loginAsAdmin(page);
    await gotoWorkspace(page);
    await expect(page.getByTestId("exam-name")).toBeVisible({ timeout: 30_000 });

    const syllabusTab = page.getByTestId("tab-syllabus");
    await expect(syllabusTab).toBeVisible();
    await expect(syllabusTab).not.toBeDisabled();
  });
});
