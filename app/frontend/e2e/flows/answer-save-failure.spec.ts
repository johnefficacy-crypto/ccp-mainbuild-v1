import { test, expect } from "@playwright/test";
import { ensureSeededUser, loginViaUi } from "../fixtures/seedUser";
import { resetAttempts } from "../fixtures/seedAttempt";

/**
 * PR-fix-7 — answer-save failure UX (AC10).
 *
 * Drives the real stack offline mid-attempt: answer a question while the
 * network is down → the save retries with backoff and lands in `failed`, submit
 * is blocked → restore the network and retry → the save lands in `saved` and
 * submit is unblocked. Proves the UI never lets a submit proceed on an answer
 * the server hasn't acknowledged.
 */
test.describe("Flow 4: answer-save failure → recovery", () => {
  test.beforeAll(async () => {
    const user = await ensureSeededUser();
    await resetAttempts(user.id);
  });

  test("offline answer retries, blocks submit, recovers on retry", async ({ page, context }) => {
    await loginViaUi(page);

    await page.goto("/app/study/mocks");
    await expect(page.getByTestId("mocks-page")).toBeVisible();
    await page.getByTestId("start-ibps-mock-btn").click();

    await page.waitForURL(/\/app\/study\/mocks\/attempts\/[^/]+$/);
    await expect(page.getByTestId("attempt-shell")).toBeVisible();

    // Go offline, then answer — the debounced POST will fail and enter retry.
    await context.setOffline(true);
    await page.getByTestId("attempt-option-0").click();

    // Sync state becomes visible: saving/retrying, then failed after backoff.
    await expect(page.getByTestId("attempt-sync-status")).toHaveAttribute(
      "data-state",
      /saving|retrying/,
    );

    // Submit is disabled while the save is pending, with a counting tooltip.
    await expect(page.getByTestId("attempt-submit")).toBeDisabled();
    await expect(page.getByTestId("attempt-submit")).toHaveAttribute(
      "title",
      /Waiting for 1 answer to save/,
    );

    // Retries exhaust (1s + 2s + 4s) → failed. Palette marks the question.
    await expect(page.getByTestId("attempt-nav-0")).toHaveAttribute("data-sync", "failed", {
      timeout: 20_000,
    });
    await expect(page.getByTestId("attempt-sync-status")).toHaveAttribute("data-state", "failed");
    await expect(page.getByTestId("attempt-sync-retry")).toBeVisible();

    // A failed answer hard-blocks submit with a modal — no bypass.
    await page.getByTestId("attempt-submit").click();
    await expect(page.getByTestId("attempt-failed-modal")).toBeVisible();
    await expect(page.getByTestId("attempt-failed-modal")).toContainText("failed to save");
    await page.getByTestId("attempt-failed-modal-close").click();
    await expect(page.getByTestId("attempt-failed-modal")).toBeHidden();

    // Restore the network and retry — the save now succeeds.
    await context.setOffline(false);
    await page.getByTestId("attempt-sync-retry").click();

    await expect(page.getByTestId("attempt-nav-0")).toHaveAttribute("data-sync", "saved", {
      timeout: 10_000,
    });

    // Submit is unblocked: clicking now opens the confirm dialog, not the block.
    await expect(page.getByTestId("attempt-submit")).toBeEnabled();
    await page.getByTestId("attempt-submit").click();
    await expect(page.getByTestId("attempt-confirm-dialog")).toBeVisible();
    await expect(page.getByTestId("attempt-failed-modal")).toBeHidden();
  });
});
