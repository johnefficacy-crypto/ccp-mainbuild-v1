import { createNodeSupabaseClient } from "./supabaseNodeClient";
import { readEnv } from "./env";

/**
 * Fixed UUIDs that mirror app/supabase/seeds/e2e_workspace_fixtures.sql.
 * Import these constants in specs so the tests never hard-code raw strings.
 */
export const WORKSPACE = {
  examId:   "e2ew0000-0000-4000-8000-000000000002",
  subjectId:"e2ew0000-0000-4000-8000-000000000003",
  topicId:  "e2ew0000-0000-4000-8000-000000000004",
  paperId:  "e2ew0000-0000-4000-8000-000000000005",
  examSlug: "e2e-workspace-exam",
  topicSlug:"e2e-federalism",
};

/**
 * Ensure the seeded admin user exists with super_admin role.
 *
 * super_admin bypasses all require_permission() checks, so one user
 * covers both exam_intelligence.review (workspace context) and
 * exam_intelligence.cms (topic/alias/PYQ CMS endpoints).
 */
export async function ensureAdminUser(): Promise<{ id: string; email: string; password: string }> {
  const env = readEnv();
  const email    = process.env.E2E_ADMIN_EMAIL    || "e2e-admin@example.com";
  const password = process.env.E2E_ADMIN_PASSWORD || "E2e-admin-passw0rd!";

  const client = createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);

  const { data: created } = await client.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
    app_metadata: { role: "super_admin" },
  });

  if (created?.user) return { id: created.user.id, email, password };

  // Already exists — find and patch
  const { data: list } = await client.auth.admin.listUsers();
  const existing = list?.users?.find((u) => u.email === email);
  if (!existing) throw new Error(`Could not locate seeded admin ${email}`);

  await client.auth.admin.updateUserById(existing.id, {
    password,
    email_confirm: true,
    app_metadata: { role: "super_admin" },
  });
  return { id: existing.id, email, password };
}

/** Sign in as the seeded admin and return the access token. */
export async function getAdminAccessToken(): Promise<string> {
  const env = readEnv();
  const email    = process.env.E2E_ADMIN_EMAIL    || "e2e-admin@example.com";
  const password = process.env.E2E_ADMIN_PASSWORD || "E2e-admin-passw0rd!";

  const client = createNodeSupabaseClient(env.supabaseURL, env.supabaseAnonKey);
  const { data, error } = await client.auth.signInWithPassword({ email, password });
  if (error || !data.session) throw error || new Error("No session for seeded admin");
  return data.session.access_token;
}

/** Verify the workspace seed rows are present (fail fast with a clear message). */
export async function verifyWorkspaceSeed(): Promise<void> {
  const env = readEnv();
  const client = createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);

  const { data: exam } = await client
    .from("exams")
    .select("id")
    .eq("id", WORKSPACE.examId)
    .maybeSingle();

  if (!exam) {
    throw new Error(
      `E2E workspace exam "${WORKSPACE.examId}" missing.\n` +
      "Apply the seed first:\n" +
      "  psql \"$DATABASE_URL\" -f app/supabase/seeds/e2e_workspace_fixtures.sql\n" +
      "See docs/testing/e2e.md.",
    );
  }
}

/** Clean up any topic-aliases the tests may have created for the E2E topic. */
export async function resetTopicAliases(): Promise<void> {
  const env = readEnv();
  const client = createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);
  await client.from("topic_aliases").delete().eq("topic_id", WORKSPACE.topicId);
}
