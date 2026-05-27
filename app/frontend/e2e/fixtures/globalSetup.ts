import { createClient } from "@supabase/supabase-js";
import { readEnv } from "./env";
import { ensureSeededUser } from "./seedUser";

/**
 * Runs once before the suite. Ensures the seeded aspirant exists and sanity
 * checks that the mock content seed has been applied — failing here with a
 * clear message beats every flow timing out against missing data.
 *
 * The mock CONTENT (template + questions) is applied out-of-band by
 * `app/supabase/seeds/e2e_fixtures.sql` (CI applies it during DB setup; locally
 * see docs/testing/e2e.md). We only verify it is present.
 */
export default async function globalSetup() {
  const env = readEnv();
  await ensureSeededUser();

  const admin = createClient(env.supabaseURL, env.supabaseServiceRoleKey, {
    auth: { autoRefreshToken: false, persistSession: false },
  });
  const { data: tmpl, error } = await admin
    .from("mock_templates")
    .select("id, slug, total_questions")
    .eq("slug", env.templateSlug)
    .maybeSingle();

  if (error) throw error;
  if (!tmpl) {
    throw new Error(
      `Mock content template "${env.templateSlug}" is missing. Apply the seed first:\n` +
        `  psql "$DATABASE_URL" -f app/supabase/seeds/e2e_fixtures.sql\n` +
        "See docs/testing/e2e.md.",
    );
  }
}
