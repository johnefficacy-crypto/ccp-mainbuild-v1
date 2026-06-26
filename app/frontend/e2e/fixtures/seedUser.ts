import { createNodeSupabaseClient } from "./supabaseNodeClient";
import { expect, type Page } from "@playwright/test";
import { readEnv, E2E_TEST_OTP } from "./env";

/**
 * Seeded aspirant. Created idempotently against the (local) Supabase via the
 * admin API — re-running tests converges on the same confirmed user instead of
 * drifting. PR1's seed mock content (the IBPS PO Prelims E2E template) is
 * available to this user once app/supabase/seeds/e2e_fixtures.sql is applied.
 */
export async function ensureSeededUser(): Promise<{ id: string; email: string; password: string }> {
  const env = readEnv();
  const admin = createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);

  const { data: created, error } = await admin.auth.admin.createUser({
    email: env.user.email,
    password: env.user.password,
    email_confirm: true,
    // Phone is the login identifier now; confirm it so phone-OTP sign-in works.
    phone: env.user.phone,
    phone_confirm: true,
  });

  if (created?.user) {
    return { id: created.user.id, email: env.user.email, password: env.user.password };
  }

  // Already exists → find it and force the credential + phone so login is known.
  const alreadyExists = error && /already.*registered|exists/i.test(error.message || "");
  if (!alreadyExists) throw error;

  const { data: list } = await admin.auth.admin.listUsers();
  const existing = list?.users?.find((u) => u.email === env.user.email);
  if (!existing) throw new Error(`Could not locate seeded user ${env.user.email}`);
  await admin.auth.admin.updateUserById(existing.id, {
    password: env.user.password,
    email_confirm: true,
    phone: env.user.phone,
    phone_confirm: true,
  });
  return { id: existing.id, email: env.user.email, password: env.user.password };
}

/** Mint a real Supabase access token for direct backend API calls in fixtures. */
export async function getAccessToken(): Promise<string> {
  const env = readEnv();
  const client = createNodeSupabaseClient(env.supabaseURL, env.supabaseAnonKey);
  const { data, error } = await client.auth.signInWithPassword({
    email: env.user.email,
    password: env.user.password,
  });
  if (error || !data.session) throw error || new Error("No session for seeded user");
  return data.session.access_token;
}

/**
 * Log in through the real UI via phone OTP (the live auth path). The phone must
 * exist in [auth.sms.test_otp] so verifyOtp accepts E2E_TEST_OTP without SMS.
 */
export async function loginViaUiWithPhone(
  page: Page,
  phone: string,
  urlPattern: RegExp = /\/app(\/|$)/,
): Promise<void> {
  await page.goto("/login");
  await expect(page.getByTestId("login-phone")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("login-phone").fill(phone);
  await page.getByTestId("login-send-code").click();

  await expect(page.getByTestId("login-otp")).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("login-otp").fill(E2E_TEST_OTP);
  await Promise.all([
    page.waitForURL(urlPattern, { timeout: 90_000 }),
    page.getByTestId("login-verify").click(),
  ]);
}

/** Log the seeded aspirant in through the UI (phone OTP). */
export async function loginViaUi(page: Page): Promise<void> {
  const env = readEnv();
  await loginViaUiWithPhone(page, env.user.phone);
}

export async function gotoProtectedPage(
  page: Page,
  path: string,
  readyTestId: string,
): Promise<void> {
  await page.goto(path);

  await expect(page.getByTestId("auth-checking")).toBeHidden({ timeout: 90_000 });
  await expect(page.getByTestId("backend-sync-pending")).toBeHidden({ timeout: 90_000 });

  await expect(page.getByTestId(readyTestId)).toBeVisible({ timeout: 90_000 });
}
