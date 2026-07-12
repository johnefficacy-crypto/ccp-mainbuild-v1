import { test, expect } from "@playwright/test";
import { ensureSeededUser, loginViaUi, gotoProtectedPage } from "../fixtures/seedUser";
import {
  ensureProjectedPyqPool,
  resetPyqPracticeAttempts,
  PYQ_PRACTICE,
} from "../fixtures/seedProjectedPyq";

/**
 * Flow: projected-PYQ practice → submit → review (PR-5 exit gate).
 *
 * Closes the deferred half of the PR-5 exit gate — "aspirant can complete and
 * review a verified previous-year paper" — which PR #946 could not exercise
 * because the workspace seed had no projected verified-PYQ pool.
 *
 * Drives the real learner path end-to-end: open the top-level Exam Intelligence
 * detail surface → PYQ Explorer intelligence overview + practice-by-paper cards
 * (`/pyq-summary`) → launch practice from a launch-accurate paper card
 * (`POST /practice/start` → generated-blueprint attempt) → answer every question
 * on the shared attempt shell → submit → result → review with the projected
 * question's printed correct answer. This also validates the live schema path
 * (migration 231 blueprint source, 183/229 projection bridge) that unit tests
 * with mocked Supabase cannot.
 */
test.describe("Flow: projected-PYQ practice → submit → review", () => {
  test.beforeAll(async () => {
    await ensureProjectedPyqPool();
    const user = await ensureSeededUser();
    await resetPyqPracticeAttempts(user.id);
  });

  test("verified paper card → practice attempt → submit → review", async ({ page }) => {
    await loginViaUi(page);
    await expect(page.getByTestId("auth-checking")).toBeHidden({ timeout: 90_000 });
    await expect(page.getByTestId("backend-sync-pending")).toBeHidden({ timeout: 90_000 });

    // Exam Intelligence detail → PYQ Explorer surface renders (not the no-cycle stub).
    await gotoProtectedPage(
      page,
      "/app/exam-intelligence/exams/e2e-workspace-exam",
      "pyq-explorer",
    );

    // Intelligence overview comes from /pyq-summary (verified-only distributions).
    await expect(page.getByTestId("pyq-summary-charts")).toBeVisible({ timeout: 30_000 });

    // Practice-by-paper: our verified, actively-projected paper offers a Practice CTA.
    const practiceBtn = page.getByTestId("pyq-paper-practice-btn").first();
    await expect(practiceBtn).toBeEnabled({ timeout: 30_000 });

    const startResponse = page.waitForResponse(
      (res) =>
        res.url().includes("/api/study/mocks/practice/start") &&
        res.request().method() === "POST",
      { timeout: 60_000 },
    );
    await practiceBtn.click();
    const started = await startResponse;
    expect(started.ok(), await started.text()).toBeTruthy();

    // Lands on the shared attempt shell for the practice attempt.
    await page.waitForURL(/\/app\/study\/mocks\/attempts\/[^/]+$/, { timeout: 60_000 });
    await expect(page.getByTestId("attempt-shell")).toBeVisible();

    // Practice is a single un-locked "Practice" section — answer every question.
    const total = PYQ_PRACTICE.questionCount;
    for (let i = 0; i < total; i += 1) {
      await expect(page.getByTestId("attempt-option-0")).toBeEnabled({ timeout: 30_000 });
      await page.getByTestId("attempt-option-0").click();

      const isLast = i === total - 1;
      if (!isLast) {
        await expect(page.getByTestId("attempt-save-next")).toBeEnabled({ timeout: 30_000 });
        await page.getByTestId("attempt-save-next").click();
        // Answer saves are debounced; hosted Supabase can be slow to settle.
        await page.waitForTimeout(1_000);
      }
    }

    // Submit → confirm (pending saves flush before the confirm button enables).
    await expect(page.getByTestId("attempt-submit")).toBeEnabled({ timeout: 120_000 });
    await page.getByTestId("attempt-submit").click();
    await expect(page.getByTestId("attempt-confirm-dialog")).toBeVisible({ timeout: 30_000 });

    const submitResponse = page.waitForResponse(
      (res) => res.url().includes("/api/study/mocks/attempts/") && res.url().endsWith("/submit"),
      { timeout: 120_000 },
    );
    await page.getByTestId("attempt-confirm-submit").click();
    const submitted = await submitResponse;
    expect(submitted.ok(), await submitted.text()).toBeTruthy();

    // Result → review.
    await page.waitForURL(/\/attempts\/[^/]+\/result$/, { timeout: 60_000 });
    await expect(page.getByTestId("result-page")).toBeVisible();

    await page.getByTestId("result-review-btn").click();
    await page.waitForURL(/\/attempts\/[^/]+\/review$/, { timeout: 60_000 });
    await expect(page.getByTestId("review-page")).toBeVisible();
    await expect(page.getByTestId("review-result-count")).toContainText(String(total));

    // Review renders the projected PYQ's correct option as its printed source
    // label + text (never a raw option UUID) — proving the frozen projection
    // snapshot flows through the shared review surface.
    await page.getByTestId("review-palette-item-1").click();
    await expect(page.getByTestId("review-question")).toBeVisible();
    const correctAnswer = page.getByTestId("review-correct-answer");
    await expect(correctAnswer).toContainText("Correct answer:");
    // The projected printed source_label survived (a positional fallback would
    // render "A", not "(a)"), and so did the projected option text.
    await expect(correctAnswer).toContainText(PYQ_PRACTICE.firstQuestion.correctSourceLabel);
    await expect(correctAnswer).toContainText(PYQ_PRACTICE.firstQuestion.correctOptionText);
    // A raw option UUID must never reach the learner.
    await expect(correctAnswer).not.toContainText(PYQ_PRACTICE.uuidPattern);
  });
});
