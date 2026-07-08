import { randomUUID } from "crypto";
import { createNodeSupabaseClient } from "./supabaseNodeClient";
import { readEnv } from "./env";

/**
 * EWP-SP5 fixtures — seed the ENTIRE sentence-practice governance chain through
 * the REAL backend APIs / RPCs at test time, so the e2e job never depends on a
 * pre-seeded live prompt bank (live prompt seeding/activation is OPERATOR
 * PENDING — see the EWP-SP2/SP3 checklist rows).
 *
 * Governance writes go through the Content Studio HTTP surface as the seeded
 * super_admin (which bypasses require_permission incl. content_studio.activate —
 * app/backend/app/core/auth.py::require_permission), i.e. the real router +
 * SECURITY DEFINER RPCs (migrations 214/215/226). Learner reads/writes go
 * through the real learner runtime as the seeded aspirant. Taxonomy/exam-scope
 * rows are read/created with the service-role client (bypasses RLS), exactly as
 * the existing workspace fixtures do.
 *
 * Only `sentence_construction` is runtime-ready (cms_writing_runtime_ready_types),
 * so the happy path activates that type; source-dependent types are used only to
 * assert the fail-closed activation gate.
 */

// Fixed fixture UUIDs (distinct band from seedWorkspace's ...0001-0007).
export const EWP = {
  familyId: "e2e0e2e0-0000-4000-8000-000000000020",
  examId: "e2e0e2e0-0000-4000-8000-000000000021",
  phaseId: "e2e0e2e0-0000-4000-8000-000000000022",
  // Fixture-unique topics that isolate the 409 no_eligible_prompt negatives from
  // any prompt seeded on the shared 'sentence-construction' topic by other specs.
  excludedPhaseTopicId: "e2e0e2e0-0000-4000-8000-000000000023",
  noEligibleScopeTopicId: "e2e0e2e0-0000-4000-8000-000000000024",
};

const REASON = "e2e sentence-practice journey fixture setup (EWP-SP5)";

function db() {
  const env = readEnv();
  return createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);
}

/** Resolve canonical English-language taxonomy seeded by migration 205. */
export async function resolveEnglishScope(): Promise<{
  subjectId: string;
  sentenceTopicId: string;
  grammarTopicId: string;
}> {
  const client = db();
  const { data: subject } = await client
    .from("subjects")
    .select("id")
    .eq("slug", "english-language")
    .maybeSingle();
  if (!subject?.id) {
    throw new Error(
      "english-language subject missing — migration 205 seed not applied to the e2e DB.",
    );
  }
  const { data: topics } = await client
    .from("topics")
    .select("id,slug")
    .eq("subject_id", subject.id)
    .in("slug", ["sentence-construction", "grammar"])
    .eq("level", "topic");
  const sentence = (topics || []).find((t) => t.slug === "sentence-construction");
  const grammar = (topics || []).find((t) => t.slug === "grammar");
  if (!sentence?.id || !grammar?.id) {
    throw new Error("English 'sentence-construction'/'grammar' topics missing (migration 205 seed).");
  }
  return { subjectId: subject.id, sentenceTopicId: sentence.id, grammarTopicId: grammar.id };
}

/**
 * Idempotent, fixture-unique English topic. Because `_select_launch_prompt`
 * narrows candidates by `.eq("topic_id", ...)`, seeding BOTH a negative's
 * prompt-under-test and its study_task under a dedicated topic guarantees the
 * candidate set contains only that test's prompt(s) — so a 409 no_eligible_prompt
 * assertion is deterministic and immune to prompts other specs seed on the shared
 * `sentence-construction` topic (serial-safe, re-run-safe; no global mutation).
 *
 * Deterministic: caller passes a fixed `id` (stable UUID) and `slug`; the upsert
 * on the primary key makes repeated runs converge on the same row. No random or
 * time-based identifiers.
 */
export async function seedUniqueTopic(args: {
  id: string;
  slug: string;
  name: string;
  subjectId: string;
}): Promise<string> {
  const client = db();
  const { error } = await client.from("topics").upsert(
    {
      id: args.id,
      subject_id: args.subjectId,
      parent_topic_id: null,
      slug: args.slug,
      name: args.name,
      level: "topic",
      is_active: true,
    },
    { onConflict: "id" },
  );
  if (error) throw new Error(`topics upsert (${args.slug}): ${error.message}`);
  return args.id;
}

/** Idempotent exam family / exam / phase for exam-scoped applicability negatives. */
export async function ensureExamPhaseFixture(): Promise<{
  familyId: string;
  examId: string;
  phaseId: string;
}> {
  const client = db();
  const { error: fErr } = await client.from("exam_families").upsert(
    { id: EWP.familyId, slug: "e2e-ewp-family", name: "E2E EWP Family", is_active: true },
    { onConflict: "id" },
  );
  if (fErr) throw new Error(`exam_families upsert: ${fErr.message}`);
  const { error: eErr } = await client.from("exams").upsert(
    {
      id: EWP.examId,
      exam_family_id: EWP.familyId,
      slug: "e2e-ewp-exam",
      name: "E2E EWP Exam",
      exam_type: "recruitment",
      is_active: true,
    },
    { onConflict: "id" },
  );
  if (eErr) throw new Error(`exams upsert: ${eErr.message}`);
  const { error: pErr } = await client.from("exam_phases").upsert(
    {
      id: EWP.phaseId,
      exam_id: EWP.examId,
      phase_name: "E2E EWP Phase",
      phase_slug: "e2e-ewp-phase",
      phase_order: 1,
      status: "active",
    },
    { onConflict: "id" },
  );
  if (pErr) throw new Error(`exam_phases upsert: ${pErr.message}`);
  return { familyId: EWP.familyId, examId: EWP.examId, phaseId: EWP.phaseId };
}

/** Create a planner study_task owned by `userId`, pinned to an exam context. */
export async function createStudyTask(args: {
  userId: string;
  subjectId: string;
  topicId: string | null;
  examId?: string | null;
  phaseId?: string | null;
  title?: string;
}): Promise<string> {
  const client = db();
  const id = randomUUID();
  const { error } = await client.from("study_tasks").insert({
    id,
    user_id: args.userId,
    title: args.title || "E2E sentence practice",
    status: "pending",
    subject_id: args.subjectId,
    topic_id: args.topicId,
    exam_id: args.examId ?? null,
    exam_phase_id: args.phaseId ?? null,
  });
  if (error) throw new Error(`study_tasks insert: ${error.message}`);
  return id;
}

// --------------------------------------------------------------------------- //
// Real-backend HTTP helpers                                                    //
// --------------------------------------------------------------------------- //

export type ApiResult = { status: number; body: any };

async function api(
  path: string,
  opts: { method?: string; token: string; body?: unknown },
): Promise<ApiResult> {
  const env = readEnv();
  const res = await fetch(`${env.backendURL}/api${path}`, {
    method: opts.method || "GET",
    headers: {
      Authorization: `Bearer ${opts.token}`,
      "Content-Type": "application/json",
    },
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
  });
  let body: any = null;
  const text = await res.text();
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  return { status: res.status, body };
}

const CS = "/admin/content-studio";

export async function createPrompt(
  adminToken: string,
  payload: Record<string, unknown>,
): Promise<{ id: string; updatedAt: string }> {
  const r = await api(`${CS}/writing-prompts`, {
    method: "POST",
    token: adminToken,
    body: { reason: REASON, payload },
  });
  if (r.status !== 200) throw new Error(`createPrompt ${r.status}: ${JSON.stringify(r.body)}`);
  const row = r.body.row;
  return { id: row.id, updatedAt: row.updated_at };
}

export async function getPrompt(adminToken: string, promptId: string): Promise<any> {
  const r = await api(`${CS}/writing-prompts/${promptId}`, { token: adminToken });
  if (r.status !== 200) throw new Error(`getPrompt ${r.status}: ${JSON.stringify(r.body)}`);
  return r.body;
}

export async function verifyPrompt(adminToken: string, promptId: string): Promise<void> {
  const p = await getPrompt(adminToken, promptId);
  const r = await api(`${CS}/writing-prompts/${promptId}/review`, {
    method: "POST",
    token: adminToken,
    body: {
      status: "verified",
      expected_status: p.reviewer_status,
      expected_updated_at: p.updated_at,
      reason: REASON,
    },
  });
  if (r.status !== 200) throw new Error(`verifyPrompt ${r.status}: ${JSON.stringify(r.body)}`);
}

export async function proposeTarget(
  adminToken: string,
  promptId: string,
  scope: {
    is_global?: boolean;
    exam_family_id?: string | null;
    exam_id?: string | null;
    exam_phase_id?: string | null;
  },
): Promise<{ id: string; updatedAt: string }> {
  const r = await api(`${CS}/writing-prompts/${promptId}/targets`, {
    method: "POST",
    token: adminToken,
    body: { reason: REASON, ...scope },
  });
  if (r.status !== 200) throw new Error(`proposeTarget ${r.status}: ${JSON.stringify(r.body)}`);
  const row = r.body.result;
  return { id: row.id, updatedAt: row.updated_at };
}

export async function reviewTarget(
  adminToken: string,
  targetId: string,
  expectedUpdatedAt: string,
  status: "active" | "excluded",
): Promise<void> {
  const r = await api(`${CS}/writing-prompt-targets/${targetId}/review`, {
    method: "POST",
    token: adminToken,
    body: {
      reason: REASON,
      applicability_status: status,
      expected_updated_at: expectedUpdatedAt,
    },
  });
  if (r.status !== 200) throw new Error(`reviewTarget ${r.status}: ${JSON.stringify(r.body)}`);
}

/** Raw activate call (returns the API result so negatives can assert status/blockers). */
export async function activatePromptRaw(
  adminToken: string,
  promptId: string,
  expectedUpdatedAt: string,
): Promise<ApiResult> {
  return api(`${CS}/writing-prompts/${promptId}/activate`, {
    method: "POST",
    token: adminToken,
    body: { reason: REASON, expected_updated_at: expectedUpdatedAt },
  });
}

/** Activate + assert eligible:true; throws on any blocker (happy-path helper). */
export async function activatePrompt(adminToken: string, promptId: string): Promise<void> {
  const p = await getPrompt(adminToken, promptId);
  const r = await activatePromptRaw(adminToken, promptId, p.updated_at);
  if (r.status !== 200) throw new Error(`activatePrompt ${r.status}: ${JSON.stringify(r.body)}`);
  const result = r.body.result;
  if (result?.eligible !== true) {
    throw new Error(`activatePrompt not eligible: ${JSON.stringify(result?.blockers)}`);
  }
}

/**
 * Full happy-path seed: verified + active sentence_construction prompt with an
 * active GLOBAL applicability target. Returns the prompt id.
 */
export async function seedActiveSentencePrompt(
  adminToken: string,
  args: { subjectId: string; topicId: string; sourceText?: string },
): Promise<string> {
  const { id } = await createPrompt(adminToken, {
    subject_id: args.subjectId,
    topic_id: args.topicId,
    exercise_type: "sentence_construction",
    prompt_text: "Write one grammatically correct sentence about your daily routine.",
    source_text: args.sourceText,
    required_sentence_count: 1,
    difficulty_level: 3,
    min_words: 3,
    max_words: 40,
  });
  await verifyPrompt(adminToken, id);
  const target = await proposeTarget(adminToken, id, { is_global: true });
  await reviewTarget(adminToken, target.id, target.updatedAt, "active");
  await activatePrompt(adminToken, id);
  return id;
}

// Learner runtime helpers.

export async function launchWriting(learnerToken: string, taskId: string): Promise<ApiResult> {
  return api(`/study/tasks/${taskId}/launch-writing`, { method: "POST", token: learnerToken });
}

export async function createSession(
  learnerToken: string,
  body: { prompt_id: string; study_task_id?: string; mode?: string },
): Promise<ApiResult> {
  return api(`/study/practice/english/sessions`, {
    method: "POST",
    token: learnerToken,
    body,
  });
}

export async function getErrorLab(learnerToken: string): Promise<ApiResult> {
  return api(`/study/practice/english/error-lab`, { token: learnerToken });
}

/** Drive the async evaluation worker synchronously (scheduler is off in CI). */
export async function runWritingEvaluator(adminToken: string): Promise<ApiResult> {
  return api(`/admin/jobs/run/writing:evaluate`, { method: "POST", token: adminToken });
}

export async function runWritingMasteryOutbox(adminToken: string): Promise<ApiResult> {
  return api(`/admin/jobs/run/writing:mastery_outbox`, { method: "POST", token: adminToken });
}
