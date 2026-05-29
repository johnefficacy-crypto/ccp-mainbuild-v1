import { test, expect } from "@playwright/test";
import { ensureSeededUser, loginViaUi } from "../fixtures/seedUser";
import { seedSubmittedAttempts } from "../fixtures/seedAttempt";

/**
 * Flow 3 — report → attempt drill:
 * a user with 5 submitted attempts sees a 5-point score trend, clicks a point,
 * lands on that attempt's result, then browser-back restores the progress page
 * client-side (no full reload).
 */
test.describe("Flow 3: report → attempt drill", () => {
  test.beforeAll(async () => {
    const user = await ensureSeededUser();
    await seedSubmittedAttempts(5, user.id);
  });

  test("trend renders 5 points → drill into a point → back restores chart", async ({ page }) => {
    await loginViaUi(page);

    await page.goto("/app/study/progress");
    await expect(page.getByTestId("study-progress-page")).toBeVisible();

    const points = page.locator('[data-testid^="score-trend-point-"]');
    await expect(points).toHaveCount(5);

    // Drilling into the third point navigates to that attempt's result page.
    await page.getByTestId("score-trend-point-2").click();
    await page.waitForURL(/\/attempts\/[^/]+\/result$/);
    await expect(page.getByTestId("result-summary")).toBeVisible();

    // Browser back returns to progress; the chart re-renders (client-side route
    // restore, not a fresh document load).
    let fullReload = false;
    page.once("load", () => {
      fullReload = true;
    });
    await page.goBack();
    await expect(page.getByTestId("study-progress-page")).toBeVisible();
    await expect(page.locator('[data-testid^="score-trend-point-"]')).toHaveCount(5);
    expect(fullReload).toBe(false);
  });
});
