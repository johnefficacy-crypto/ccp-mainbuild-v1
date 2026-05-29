/**
 * Central place that reads + validates the environment the E2E suite needs.
 * Fail loud and early with an actionable message rather than letting a test
 * mysteriously time out against a missing backend.
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
  return {
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:3000",
    backendURL: required("E2E_BACKEND_URL"),
    supabaseURL: required("E2E_SUPABASE_URL"),
    supabaseAnonKey: required("E2E_SUPABASE_ANON_KEY"),
    supabaseServiceRoleKey: required("E2E_SUPABASE_SERVICE_ROLE_KEY"),
    templateSlug: process.env.E2E_TEMPLATE_SLUG || "ibps-po-prelims-mock-1",
    user: {
      email: process.env.E2E_USER_EMAIL || "e2e-aspirant@example.com",
      password: process.env.E2E_USER_PASSWORD || "E2e-passw0rd!",
    },
  };
}
