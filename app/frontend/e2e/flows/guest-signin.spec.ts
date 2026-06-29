import { test, expect } from "@playwright/test";

/**
 * Flow: guest (anonymous) sign-in.
 *
 * Regression guard for the phone-OTP migration: anonymous sign-in must remain
 * functional (config.toml enable_anonymous_sign_ins = true). The live entry
 * point is the discovery onboarding route — a guest landing on
 * /app/onboarding/chat triggers useProfileOnboarding.bootstrap(), which calls
 * signInAnonymously() (captcha is disabled in E2E, so no Turnstile token is
 * needed) and then loads the first profile question.
 *
 * The question card only renders after the anonymous JWT is minted AND the
 * backend accepts it (fetchNext → /api/profile/onboarding), so asserting the
 * card is a true end-to-end proof that anonymous auth works.
 */
test("guest sign-in: discovery onboarding mints an anonymous session and loads the first question", async ({
  page,
}) => {
  await page.goto("/app/onboarding/chat?mode=discovery");

  // The first question card only appears once the anonymous session exists and
  // the backend has served a question against the freshly minted JWT.
  await expect(page.getByTestId("onboarding-question-card")).toBeVisible({
    timeout: 90_000,
  });

  // Must not have fallen into the error state nor bounced the guest to /login.
  await expect(page).toHaveURL(/\/app\/onboarding\/chat/, { timeout: 10_000 });
  await expect(page.getByTestId("onboarding-question-text")).toBeVisible();
});
