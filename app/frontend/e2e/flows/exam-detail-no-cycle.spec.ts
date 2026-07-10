import { test, expect } from "@playwright/test";
import { ensureWorkspaceSeed, WORKSPACE } from "../fixtures/seedWorkspace";
import { ensureSeededUser, loginViaUi, gotoProtectedPage } from "../fixtures/seedUser";

/**
 * Flow: exam-detail with no published recruitment cycle (PR #939).
 *
 * Regression guard for the fix that removed ExamDetail's early full-page
 * `exam-no-cycle` stub. The seeded workspace exam (`e2e-workspace-exam`) is
 * `is_active` but has NO recruitment mapped to it, so `/api/exams/:slug`
 * resolves while `/api/recruitments` yields no match — the exam-only render
 * path. Exam-level intelligence (PYQ Explorer et al.) must still render, and
 * recruitment-only actions must be absent.
 *
 * `/app/eligibility/exams/:slug` is a public aspirant route, so this drives a
 * normal seeded user, not the admin.
 */
test.describe("Flow: exam-detail — no recruitment cycle", () => {
  test.beforeAll(async () => {
    await ensureWorkspaceSeed();
    await ensureSeededUser();
  });

  test("exam-level intelligence renders and recruitment-only actions are hidden", async ({
    page,
  }) => {
    await loginViaUi(page);
    await expect(page.getByTestId("auth-checking")).toBeHidden({ timeout: 90_000 });
    await expect(page.getByTestId("backend-sync-pending")).toBeHidden({ timeout: 90_000 });

    // PYQ Explorer is the target regression surface — its presence proves the
    // page did not short-circuit into the old no-cycle stub.
    await gotoProtectedPage(page, "/app/eligibility/exams/e2e-workspace-exam", "pyq-explorer");

    // A single no-active-cycle banner replaces the repeated recruitment panels.
    await expect(page.getByTestId("no-cycle-banner")).toBeVisible();
    await expect(page.getByText("No active recruitment cycle right now.")).toBeVisible();
    // Recruitment-only sections are hidden entirely in the no-cycle path.
    await expect(page.getByTestId("eligibility-panel")).toHaveCount(0);

    // Recruitment-only actions must not render without a mapped recruitment.
    await expect(page.getByTestId("detail-save-btn")).toHaveCount(0);
    await expect(page.getByTestId("detail-track-btn")).toHaveCount(0);
    await expect(page.getByTestId("detail-official-link")).toHaveCount(0);

    // The exam-only render path still keys the page container off the exam id.
    await expect(page.getByTestId(`exam-detail-${WORKSPACE.examId}`)).toBeVisible();
  });
});
