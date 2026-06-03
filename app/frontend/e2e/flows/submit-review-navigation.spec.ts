import { test, expect } from "@playwright/test";
import { ensureSeededUser, loginViaUi } from "../fixtures/seedUser";
import { resetAttempts, seedSubmittedAttempt } from "../fixtures/seedAttempt";

/**
 * Flow 2 — submit → review navigation:
 * a completed attempt with a mix of correct / wrong / marked answers, then the
 * review surface: filtering (with the filter state reflected in the URL),
 * palette navigation, and review-mode rendering (correct option + explanation).
 */
test.describe("Flow 2: submit → review navigation", () => {
  let attemptId: string;

  test.beforeAll(async () => {
    const user = await ensureSeededUser();
    await resetAttempts(user.id);
    // 15 questions cycling correct/wrong/unattempted → ~5 wrong, every 4th marked.
    attemptId = await seedSubmittedAttempt({
      plan: ["correct", "wrong", "unattempted"],
      markEvery: 4,
    });
  });

  test("result → review → filter (URL state) → palette → review-mode content", async ({ page }) => {
    await loginViaUi(page);

    await page.goto(`/app/study/mocks/attempts/${attemptId}/result`);
    await expect(page.getByTestId("result-page")).toBeVisible();

    await page.getByTestId("result-review-btn").click();
    await page.waitForURL(/\/attempts\/[^/]+\/review$/);
    await expect(page.getByTestId("review-page")).toBeVisible();
    await expect(page.getByTestId("review-result-count")).toContainText("15");

    // Filter to wrong answers: the list reduces and the URL reflects the filter.
    await page.getByTestId("review-filter-wrong").click();
    await expect(page).toHaveURL(/[?&]filter=wrong/);
    await expect(page.getByTestId("review-filter-wrong")).toHaveAttribute("aria-pressed", "true");
    await expect(page.getByTestId("review-result-count")).toContainText("5");

    const wrongItems = page
      .getByTestId("review-palette")
      .locator('[data-testid^="review-palette-item-"]');
    await expect(wrongItems).toHaveCount(5);

    const wrongCount = await wrongItems.count();
    expect(wrongCount).toBeLessThan(15);

    // option_trap is a derived classification (may be empty), but the filter
    // state must still round-trip through the URL.
    await page.getByTestId("review-filter-option_trap").click();
    await expect(page).toHaveURL(/[?&]filter=option_trap/);

    // Back to all, then navigate question-by-question via the palette.
    await page.getByTestId("review-filter-all").click();
    await expect(page).not.toHaveURL(/filter=/);
    await page.getByTestId("review-palette-item-1").click();
    await expect(page.getByTestId("review-question")).toBeVisible();
    await page.getByTestId("review-next").click();
    await expect(page.getByTestId("review-question")).toBeVisible();

    // Review mode shows the correct option + explanation (seed fixture text).
    await expect(page.getByTestId("review-question")).toContainText("Correct:");
    await expect(page.getByTestId("review-question")).toContainText("E2E fixture explanation");
  });
});
