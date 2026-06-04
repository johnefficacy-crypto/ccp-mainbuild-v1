/**
 * Central place that reads + validates the environment the E2E suite needs.
 * Fail loud and early with an actionable message rather than letting a test
 * mysteriously time out against a missing backend.
 *
 * Hard guard: refuses to run if E2E_SUPABASE_URL points at a production
 * Supabase host (*.supabase.co). The suite creates and deletes rows — it must
 * only ever talk to a local Supabase instance.
 */
export type E2EEnv = {
  baseURL: string;
  backendURL: string;
  supabaseURL: string;
  supabaseAnonKey: string;
  supabaseServiceRoleKey: string;
  templateSlug: string;
  user: { email: string; password: string };
};

/**
 * Reject URLs whose hostname ends with `.supabase.co` — that is the canonical
 * pattern for every hosted Supabase project. Local `supabase start` always
 * binds to 127.0.0.1, so legitimate local URLs are never blocked.
 */
function assertNotProdSupabase(url: string): void {
  let hostname: string;
  try {
    hostname = new URL(url).hostname;
  } catch {
    // The `required()` check will surface a clearer error; skip here.
    return;
  }
  if (hostname.endsWith(".supabase.co")) {
    throw new Error(
      `\n${"─".repeat(70)}\n` +
        `HARD STOP — E2E_SUPABASE_URL points at a PRODUCTION Supabase host:\n` +
        `  ${url}\n\n` +
        `The E2E suite writes test data (users, attempts, workspaces) and\n` +
        `must only run against a local Supabase instance.\n\n` +
        `Fix: start the local stack and use its URL instead:\n` +
        `  supabase start                 # in app/supabase/\n` +
        `  supabase status                # shows API URL → http://127.0.0.1:54321\n` +
        `  E2E_SUPABASE_URL=http://127.0.0.1:54321 ...\n\n` +
        `See docs/testing/e2e.md for the full local setup.\n` +
        `${"─".repeat(70)}\n`,
    );
  }
}

function required(name: string): string {
  const v = process.env[name];
  if (!v) {
    throw new Error(
      `Missing env var ${name}. See docs/testing/e2e.md — copy app/frontend/e2e/.env.example and fill it in.`,
    );
  }
  return v;
}

export function readEnv(): E2EEnv {
  const supabaseURL = required("E2E_SUPABASE_URL");
  assertNotProdSupabase(supabaseURL);

  return {
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:3000",
    backendURL: required("E2E_BACKEND_URL"),
    supabaseURL,
    supabaseAnonKey: required("E2E_SUPABASE_ANON_KEY"),
    supabaseServiceRoleKey: required("E2E_SUPABASE_SERVICE_ROLE_KEY"),
    templateSlug: process.env.E2E_TEMPLATE_SLUG || "ibps-po-prelims-mock-1",
    user: {
      email: process.env.E2E_USER_EMAIL || "e2e-aspirant@example.com",
      password: process.env.E2E_USER_PASSWORD || "E2e-passw0rd!",
    },
  };
}
