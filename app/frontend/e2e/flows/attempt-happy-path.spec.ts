import { test, expect, Page } from "@playwright/test";
import { ensureSeededUser, loginViaUi, gotoProtectedPage } from "../fixtures/seedUser";
import { resetAttempts } from "../fixtures/seedAttempt";

/**
 * Flow 1 — full attempt happy path:
 * login → start IBPS PO Prelims → answer with section lock → submit → result
 * with a lazily-loaded analytics chart.
 *
 * The seed (app/supabase/seeds/e2e_fixtures.sql) gives 3 sections × 5 questions,
 * section locks on, and option_index 1 (the first rendered option) is always
 * correct — so clicking the first option yields a deterministic, non-zero score.
 */
const SECTION_SIZE = 5;

async function answerSection(page: Page, opts: { marks?: number; advance: boolean }) {
  const marks = opts.marks ?? 0;

  for (let i = 0; i < SECTION_SIZE; i += 1) {
    await expect(page.getByTestId("attempt-option-0")).toBeEnabled({ timeout: 30_000 });
    await page.getByTestId("attempt-option-0").click();

    if (i < marks) {
      await expect(page.getByTestId("attempt-mark-review")).toBeEnabled({ timeout: 30_000 });
      await page.getByTestId("attempt-mark-review").check();
    }

    // `advance` clicks Save & Next after every question, including the last
    // question of a section, which crosses into the next section. For the final
    // section we leave the last question in place, wait for saves, then submit.
    const isLastOfSection = i === SECTION_SIZE - 1;
    if (opts.advance || !isLastOfSection) {
      await expect(page.getByTestId("attempt-save-next")).toBeEnabled({ timeout: 30_000 });
      await page.getByTestId("attempt-save-next").click();

      // The app debounces answer saves and section boundary transitions flush
      // pending saves before entering the next section. Hosted Supabase can make
      // this visibly slower than local Supabase, so give the UI time to settle.
      await page.waitForTimeout(1_200);
    }
  }
}

test.describe("Flow 1: attempt happy path", () => {
  test.beforeAll(async () => {
    const user = await ensureSeededUser();
    await resetAttempts(user.id);
  });

  test("start → section-locked answering → submit → lazy-loaded result", async ({ page }) => {
    await loginViaUi(page);

    await gotoProtectedPage(page, "/app/study/mocks", "mocks-page");
    await page.getByTestId("start-ibps-mock-btn").click();

    await page.waitForURL(/\/app\/study\/mocks\/attempts\/[^/]+$/, { timeout: 60_000 });
    await expect(page.getByTestId("attempt-shell")).toBeVisible();
    await expect(page.getByTestId("attempt-section-label")).toContainText("Section 1 of 3");
    await expect(page.getByTestId("attempt-section-label")).toContainText("locked");

    // Section 1: answer 5, mark 2 for review, Save & Next across the boundary.
    await answerSection(page, { marks: 2, advance: true });
    await expect(page.getByTestId("attempt-section-label")).toContainText("Section 2 of 3", {
      timeout: 60_000,
    });

    // Section lock: you cannot jump back to a Section 1 question.
    await expect(page.getByTestId("attempt-nav-0")).toBeDisabled();
    await expect(page.getByTestId("attempt-nav-4")).toBeDisabled();
    // ...but the current section's questions are navigable.
    await expect(page.getByTestId("attempt-nav-5")).toBeEnabled();

    // Section 2, then Section 3.
    await answerSection(page, { advance: true });
    await expect(page.getByTestId("attempt-section-label")).toContainText("Section 3 of 3", {
      timeout: 60_000,
    });
    await answerSection(page, { advance: false });

    // Submit → confirm.
    await expect(page.getByTestId("attempt-submit")).toBeEnabled({ timeout: 120_000 });
    await page.getByTestId("attempt-submit").click();

    await expect(page.getByTestId("attempt-confirm-dialog")).toBeVisible({ timeout: 30_000 });

    const submitResponsePromise = page.waitForResponse(
      (res) => res.url().includes("/api/study/mocks/attempts/") && res.url().endsWith("/submit"),
      { timeout: 120_000 },
    );

    await page.getByTestId("attempt-confirm-submit").click();

    const submitResponse = await submitResponsePromise;
    expect(submitResponse.ok(), await submitResponse.text()).toBeTruthy();

    // Result page with a non-zero score summary.
    await page.waitForURL(/\/attempts\/[^/]+\/result$/, { timeout: 60_000 });
    await expect(page.getByTestId("result-summary")).toBeVisible();
    const score = Number(await page.getByTestId("result-summary").getAttribute("data-score"));
    expect(Number.isFinite(score)).toBe(true);
    expect(score).toBeGreaterThan(0);

    // Charts are code-split: activating a chart tab must fetch a JS chunk.
    const chunkRequest = page.waitForRequest(/static\/js\/.*\.chunk\.js/);
    await page.getByTestId("result-tab-error").click();
    await chunkRequest;
    await expect(page.getByTestId("result-chart-error")).toBeVisible();
  });
});
