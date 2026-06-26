import { test, expect } from "@playwright/test";

/**
 * Flow: guest (anonymous) sign-in.
 *
 * Regression guard for the phone-OTP migration: anonymous sign-in must remain
 * functional (config.toml enable_anonymous_sign_ins = true). This executes the
 * StartFreeButton → signInAnonymously → onboarding path without any seeded user.
 *
 * Captcha is not enabled in E2E (REACT_APP_TURNSTILE_SITE_KEY unset), so
 * signInAnonymously runs without a captchaToken — matches local/CI config.
 */
test("guest sign-in: StartFreeButton creates anonymous session and lands on onboarding", async ({
  page,
}) => {
  await page.goto("/");

  const startBtn = page.getByTestId("hero-start-button");
  await expect(startBtn).toBeVisible({ timeout: 30_000 });

  await Promise.all([
    page.waitForURL(/\/app\/onboarding\/chat/, { timeout: 60_000 }),
    startBtn.click(),
  ]);

  // Auth context must settle — anonymous session should be established.
  await expect(page.getByTestId("auth-checking")).toBeHidden({ timeout: 90_000 });
  await expect(page.getByTestId("backend-sync-pending")).toBeHidden({ timeout: 90_000 });

  // Must stay on onboarding (not redirected to /login), confirming the
  // anonymous session was accepted by the backend.
  await expect(page).toHaveURL(/\/app\/onboarding\/chat/, { timeout: 10_000 });
});
