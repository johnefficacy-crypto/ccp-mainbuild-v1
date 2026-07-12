import { readEnv } from "./env";
import { createNodeSupabaseClient } from "./supabaseNodeClient";
import { ensureWorkspaceSeed, ensureAdminUser, WORKSPACE } from "./seedWorkspace";

/**
 * Projected-PYQ practice pool fixture.
 *
 * Closes the PR-5 exit gate's missing half: the workspace seed had no projected
 * verified-PYQ pool, so the full "aspirant completes and reviews a verified
 * previous-year paper" flow could never be exercised end-to-end (PR #946
 * Remaining Work).
 *
 * The projection bridge table `pyq_mock_question_projections` is deliberately
 * RPC-only — migration 183 revokes direct DML and grants only the SECURITY
 * DEFINER `project_pyq_question_to_mock_bank(pyq_question_id, actor_id, reason)`
 * to service_role. So this fixture seeds the CANONICAL side (verified paper +
 * verified `pyq_questions` + verified `pyq_options` + one primary verified topic
 * tag per question) and then calls the REAL projection RPC — the same path the
 * admin CMS uses (`app/backend/app/admin/pyq_mock_projection.py`). That makes the
 * E2E validate the genuine projection bridge (183/229) rather than a hand-forged
 * `mock_question_bank`/projection, and the RPC's own trust gates (verified paper,
 * verified question, exactly one verified correct option, one primary verified
 * subject-bearing tag) are exercised for free.
 *
 * Fixed UUIDs + service-role upserts on PK → idempotent; the RPC returns
 * `unchanged` on re-run and leaves the projection `active`.
 */

const PP = "e2e0e2e0-0000-4000-8000-";
const uid = (n: number): string => PP + n.toString(16).padStart(12, "0");

const QUESTION_COUNT = 3;
const OPTIONS_PER_Q = 4;
const OPTION_LABELS = ["(a)", "(b)", "(c)", "(d)"];
const PROJECTION_REASON = "e2e projected-PYQ practice pool seed";

export const PYQ_PRACTICE = {
  // A verified paper distinct from seedWorkspace's pending `paperId`, so the
  // pending paper keeps driving pyq_workbench "partial" readiness elsewhere.
  paperId: uid(0xf0),
  year: 2023,
  questionCount: QUESTION_COUNT,
  pyqQuestionId: (q: number): string => uid(0x1a0 + q), // q in 1..3
  optionId: (q: number, o: number): string => uid(0x1c00 + q * 16 + o),
  // The printed-order-first question (question_number 1) and its correct option
  // as seeded below. The review E2E asserts these survive the projection snapshot
  // into the shared review surface. Kept here so the spec can't drift from the seed.
  firstQuestion: {
    correctSourceLabel: OPTION_LABELS[0], // "(a)"
    correctOptionText: "PYQ Q1 option 1 CORRECT",
  },
  // A generic UUID: the review must render the printed label + text, never a raw
  // option id.
  uuidPattern: /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i,
};

const ACCEPTED_OUTCOMES = new Set(["created", "updated", "unchanged"]);

/**
 * Idempotently ensure the projected-PYQ practice pool exists. Seeds the canonical
 * PYQ rows (via service-role upsert) then projects each question through the real
 * bridge RPC. Depends on the workspace exam/subject/topic, so it ensures those
 * first.
 */
export async function ensureProjectedPyqPool(): Promise<void> {
  await ensureWorkspaceSeed();
  const actor = await ensureAdminUser();

  const env = readEnv();
  const db = createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);

  // 1) Verified PYQ paper on the workspace exam.
  const { error: paperErr } = await db.from("pyq_papers").upsert(
    {
      id: PYQ_PRACTICE.paperId,
      exam_id: WORKSPACE.examId,
      year: PYQ_PRACTICE.year,
      source_type: "community",
      trust_status: "verified",
      metadata: { seed: "e2e_fixture" },
    },
    { onConflict: "id" },
  );
  if (paperErr) throw new Error(`pyq_papers upsert: ${paperErr.message}`);

  // 2) Verified canonical PYQ questions (printed order via question_number).
  const questions = Array.from({ length: QUESTION_COUNT }, (_, i) => {
    const q = i + 1;
    return {
      id: PYQ_PRACTICE.pyqQuestionId(q),
      pyq_paper_id: PYQ_PRACTICE.paperId,
      question_number: q,
      display_order: q,
      source_question_ref: `Q${q}`,
      question_text: `PYQ practice question ${q} — projected verified previous-year item.`,
      question_type: "mcq",
      // Left null: pyq_questions.correct_option_id FKs pyq_options(id), which FKs
      // back to pyq_questions(id) — a circular insert order. The projection RPC
      // only checks correct_option_id when set and otherwise derives the correct
      // option from pyq_options.is_correct (exactly one verified correct, seeded
      // as option "(a)" below), so leaving it null is sufficient and correct.
      correct_option_id: null,
      observed_difficulty: "medium",
      reviewer_status: "verified",
      language: "en",
      metadata: { seed: "e2e_fixture" },
    };
  });
  const { error: pqErr } = await db.from("pyq_questions").upsert(questions, { onConflict: "id" });
  if (pqErr) throw new Error(`pyq_questions upsert: ${pqErr.message}`);

  // 3) Verified canonical options — 4 per question, printed source_label + order,
  //    label "(a)" correct. option_text keeps the printed label OUT of the text so
  //    the review assertion on the label proves the projected source_label survived.
  const options = questions.flatMap((_, i) => {
    const q = i + 1;
    return Array.from({ length: OPTIONS_PER_Q }, (__, j) => {
      const o = j + 1;
      return {
        id: PYQ_PRACTICE.optionId(q, o),
        question_id: PYQ_PRACTICE.pyqQuestionId(q),
        option_label: OPTION_LABELS[j],
        source_label: OPTION_LABELS[j],
        display_order: o,
        option_text: `PYQ Q${q} option ${o}${o === 1 ? " CORRECT" : ""}`,
        is_correct: o === 1,
        reviewer_status: "verified",
      };
    });
  });
  const { error: optErr } = await db
    .from("pyq_options")
    .upsert(options, { onConflict: "question_id,option_label" });
  if (optErr) throw new Error(`pyq_options upsert: ${optErr.message}`);

  // 4) Exactly one primary verified topic tag per question (RPC requires it, and
  //    the topic must resolve to a subject) → drives by_subject too.
  const tags = questions.map((qn) => ({
    question_id: qn.id,
    topic_id: WORKSPACE.topicId,
    tag_role: "primary",
    tagging_source: "manual",
    reviewer_status: "verified",
    metadata: { seed: "e2e_fixture" },
  }));
  const { error: tagErr } = await db
    .from("pyq_question_topic_tags")
    .upsert(tags, { onConflict: "question_id,topic_id,tag_role" });
  if (tagErr) throw new Error(`pyq_question_topic_tags upsert: ${tagErr.message}`);

  // 5) Project each question through the real bridge RPC (creates the mock bank
  //    row + options + the ACTIVE projection). Fail loudly on a blocked/error
  //    outcome so a seed misconfiguration never yields a silently empty pool.
  for (const qn of questions) {
    const { data, error } = await db.rpc("project_pyq_question_to_mock_bank", {
      p_pyq_question_id: qn.id,
      p_actor_id: actor.id,
      p_audit_reason: PROJECTION_REASON,
    });
    if (error) throw new Error(`project_pyq_question_to_mock_bank(${qn.id}): ${error.message}`);
    const result = Array.isArray(data) ? data[0] : data;
    const outcome = result?.outcome;
    if (!ACCEPTED_OUTCOMES.has(outcome)) {
      throw new Error(
        `projection of ${qn.id} did not succeed: ${JSON.stringify(result)}`,
      );
    }
  }
}

/**
 * Delete the seeded user's PYQ-practice attempts so each run starts clean.
 * Practice attempts are generated-blueprint attempts (template_id null,
 * generated_blueprint_id set) with a `pyq_practice_*` blueprint source; FK
 * children are removed before parents, mirroring resetAttempts().
 */
export async function resetPyqPracticeAttempts(userId: string): Promise<void> {
  const env = readEnv();
  const db = createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);

  const { data: bps, error: bpErr } = await db
    .from("mock_generated_blueprints")
    .select("id")
    .eq("user_id", userId)
    .in("source", ["pyq_practice_paper", "pyq_practice_section", "pyq_practice_topic"]);
  if (bpErr) throw new Error(`resetPyqPracticeAttempts: blueprint fetch: ${bpErr.message}`);
  const blueprintIds = (bps ?? []).map((b) => b.id);
  if (blueprintIds.length === 0) return;

  const { data: atts, error: attErr } = await db
    .from("mock_attempts")
    .select("id")
    .eq("user_id", userId)
    .in("generated_blueprint_id", blueprintIds);
  if (attErr) throw new Error(`resetPyqPracticeAttempts: attempt fetch: ${attErr.message}`);
  const attemptIds = (atts ?? []).map((a) => a.id);

  if (attemptIds.length > 0) {
    // mock_tests compat rows (FK child) first, then the attempts (responses cascade).
    const { error: mtErr } = await db
      .from("mock_tests")
      .delete()
      .in("mock_attempt_id", attemptIds);
    if (mtErr) throw new Error(`resetPyqPracticeAttempts: mock_tests delete: ${mtErr.message}`);
    const { error: maErr } = await db.from("mock_attempts").delete().in("id", attemptIds);
    if (maErr) throw new Error(`resetPyqPracticeAttempts: mock_attempts delete: ${maErr.message}`);
  }

  const { error: delBpErr } = await db
    .from("mock_generated_blueprints")
    .delete()
    .in("id", blueprintIds);
  if (delBpErr) throw new Error(`resetPyqPracticeAttempts: blueprint delete: ${delBpErr.message}`);
}
