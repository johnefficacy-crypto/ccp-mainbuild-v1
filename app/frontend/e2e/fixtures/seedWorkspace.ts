import { expect, type Page } from "@playwright/test";
import { createNodeSupabaseClient } from "./supabaseNodeClient";
import { readEnv } from "./env";
import { loginViaUiWithPhone } from "./seedUser";

/**
 * Fixed UUIDs for workspace E2E rows. These are stable across runs so specs
 * can reference them by constant rather than querying the DB.
 */
export const WORKSPACE = {
  examId:         "e2e0e2e0-0000-4000-8000-000000000002",
  subjectId:      "e2e0e2e0-0000-4000-8000-000000000003",
  topicId:        "e2e0e2e0-0000-4000-8000-000000000004",
  paperId:        "e2e0e2e0-0000-4000-8000-000000000005",
  topicSlug:      "e2e-federalism",
  syllabusDocId:  "e2e0e2e0-0000-4000-8000-000000000006",
  mentionId:      "e2e0e2e0-0000-4000-8000-000000000007",
};

const FAMILY_ID = "e2e0e2e0-0000-4000-8000-000000000001";
const DEFAULT_ADMIN_EMAIL = "e2e-admin@example.com";
const DEFAULT_ADMIN_PASSWORD = "E2e-admin-passw0rd!";
// Must be present in app/supabase/config.toml [auth.sms.test_otp]; login is phone-OTP.
const DEFAULT_ADMIN_PHONE = "+919999900002";

/**
 * Ensure FK-backed admin audit tables can reference the seeded auth user.
 * The committed schema defines profiles(id, email, full_name, ...); keep this
 * minimal so the helper remains safe on stale local databases with only the
 * baseline profile columns applied.
 */
async function ensureAdminProfileRow(args: { id: string; email: string }): Promise<void> {
  const env = readEnv();
  const client = createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);
  const { error } = await client.from("profiles").upsert(
    {
      id: args.id,
      email: args.email,
      full_name: "E2E Admin",
    },
    { onConflict: "id" },
  );
  if (error) throw new Error(`profiles upsert for E2E admin: ${error.message}`);
}

/**
 * Idempotently ensure all workspace seed rows exist. Uses the Supabase
 * service-role client (bypasses RLS) and upserts on primary key.
 *
 * Called from each workspace spec's beforeAll so a failure only affects
 * that spec, not the entire suite.
 */
export async function ensureWorkspaceSeed(): Promise<void> {
  const env = readEnv();
  const db = createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);

  // 1) Exam family
  const { error: efErr } = await db.from("exam_families").upsert(
    { id: FAMILY_ID, slug: "e2e-workspace-family", name: "E2E Workspace Family", is_active: true },
    { onConflict: "id" },
  );
  if (efErr) throw new Error(`exam_families upsert: ${efErr.message}`);

  // 2) Exam
  const { error: exErr } = await db.from("exams").upsert(
    {
      id: WORKSPACE.examId,
      exam_family_id: FAMILY_ID,
      slug: "e2e-workspace-exam",
      name: "E2E Workspace Exam",
      exam_type: "recruitment",
      is_active: true,
    },
    { onConflict: "id" },
  );
  if (exErr) throw new Error(`exams upsert: ${exErr.message}`);

  // 3) Subject
  const { error: subErr } = await db.from("subjects").upsert(
    {
      id: WORKSPACE.subjectId,
      name: "E2E Polity",
      slug: "e2e-polity",
      subject_group: "social_science",
      is_active: true,
    },
    { onConflict: "id" },
  );
  if (subErr) throw new Error(`subjects upsert: ${subErr.message}`);

  // 4) Topic
  const { error: topErr } = await db.from("topics").upsert(
    {
      id: WORKSPACE.topicId,
      subject_id: WORKSPACE.subjectId,
      parent_topic_id: null,
      slug: WORKSPACE.topicSlug,
      name: "E2E Federalism",
      level: "topic",
      default_difficulty_level: "medium",
      is_active: true,
      metadata: {},
    },
    { onConflict: "id" },
  );
  if (topErr) throw new Error(`topics upsert: ${topErr.message}`);

  // 5) PYQ paper — presence makes pyq_workbench readiness "partial", enabling the tab
  const { error: ppErr } = await db.from("pyq_papers").upsert(
    {
      id: WORKSPACE.paperId,
      exam_id: WORKSPACE.examId,
      year: 2024,
      source_type: "community",
      trust_status: "pending",
      metadata: {},
    },
    { onConflict: "id" },
  );
  if (ppErr) throw new Error(`pyq_papers upsert: ${ppErr.message}`);
}

/**
 * Ensure the seeded admin user exists with super_admin role.
 * super_admin bypasses all require_permission() checks.
 */
export async function ensureAdminUser(): Promise<{ id: string; email: string; password: string }> {
  const env = readEnv();
  const email    = process.env.E2E_ADMIN_EMAIL    || DEFAULT_ADMIN_EMAIL;
  const password = process.env.E2E_ADMIN_PASSWORD || DEFAULT_ADMIN_PASSWORD;

  const client = createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);

  const phone = process.env.E2E_ADMIN_PHONE || DEFAULT_ADMIN_PHONE;
  const { data: created } = await client.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
    phone,
    phone_confirm: true,
    app_metadata: { role: "super_admin" },
  });

  if (created?.user) {
    await ensureAdminProfileRow({ id: created.user.id, email });
    return { id: created.user.id, email, password };
  }

  // Already exists — find and patch
  const { data: list } = await client.auth.admin.listUsers();
  const existing = list?.users?.find((u) => u.email === email);
  if (!existing) throw new Error(`Could not locate seeded admin ${email}`);

  await client.auth.admin.updateUserById(existing.id, {
    password,
    email_confirm: true,
    phone,
    phone_confirm: true,
    app_metadata: { role: "super_admin" },
  });
  await ensureAdminProfileRow({ id: existing.id, email });
  return { id: existing.id, email, password };
}

/** Sign in through the UI as the seeded admin and wait for auth sync to settle. */
export async function loginAsAdmin(page: Page): Promise<void> {
  const phone = process.env.E2E_ADMIN_PHONE || DEFAULT_ADMIN_PHONE;
  await loginViaUiWithPhone(page, phone, /\/(?:app|admin)(\/|$)/);
  await expect(page.getByTestId("auth-checking")).toBeHidden({ timeout: 90_000 });
  await expect(page.getByTestId("backend-sync-pending")).toBeHidden({ timeout: 90_000 });
}

/** Sign in as the seeded admin and return a Bearer access token. */
export async function getAdminAccessToken(): Promise<string> {
  const env = readEnv();
  const email    = process.env.E2E_ADMIN_EMAIL    || DEFAULT_ADMIN_EMAIL;
  const password = process.env.E2E_ADMIN_PASSWORD || DEFAULT_ADMIN_PASSWORD;

  const client = createNodeSupabaseClient(env.supabaseURL, env.supabaseAnonKey);
  const { data, error } = await client.auth.signInWithPassword({ email, password });
  if (error || !data.session) throw error || new Error("No session for seeded admin");
  return data.session.access_token;
}

/** Clean up any topic-aliases the tests may have created for the E2E topic. */
export async function resetTopicAliases(): Promise<void> {
  const env = readEnv();
  const client = createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);
  await client.from("topic_aliases").delete().eq("topic_id", WORKSPACE.topicId);
}

/**
 * Seed a syllabus_documents row and a syllabus_topic_mention so that the
 * Syllabus Mapper tab is enabled (readiness != "empty").  Uses fixed UUIDs
 * so rows can be torn down deterministically.
 */
export async function ensureSyllabusMapperSeed(): Promise<void> {
  const env = readEnv();
  const client = createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);

  // 1) syllabus_documents row — required FK for syllabus_topic_mentions
  const { error: sdErr } = await client.from("syllabus_documents").upsert(
    {
      id:            WORKSPACE.syllabusDocId,
      exam_id:       WORKSPACE.examId,
      document_type: "syllabus_pdf",
      title:         "E2E Syllabus Doc",
      trust_status:  "verified",
      metadata:      {},
    },
    { onConflict: "id" },
  );
  if (sdErr) throw new Error(`syllabus_documents upsert: ${sdErr.message}`);

  // 2) syllabus_topic_mention — makes readiness status "partial" → tab enabled
  const { error: smErr } = await client.from("syllabus_topic_mentions").upsert(
    {
      id:                   WORKSPACE.mentionId,
      exam_id:              WORKSPACE.examId,
      syllabus_document_id: WORKSPACE.syllabusDocId,
      topic_id:             WORKSPACE.topicId,
      normalized_text:      "e2e-federalism-seed",
      mention_type:         "explicit",
      confidence_score:     1.0,
      reviewer_status:      "pending",
      metadata:             {},
    },
    { onConflict: "id" },
  );
  if (smErr) throw new Error(`syllabus_topic_mentions upsert: ${smErr.message}`);
}

/** Remove syllabus_topic_mentions and syllabus_documents for the E2E exam. */
export async function cleanupSyllabusMapperSeed(): Promise<void> {
  const env = readEnv();
  const client = createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);
  // mentions first (FK child), then document
  await client.from("syllabus_topic_mentions").delete().eq("exam_id", WORKSPACE.examId);
  await client.from("syllabus_documents").delete().eq("id", WORKSPACE.syllabusDocId);
}
