import { readEnv } from "./env";
import { createNodeSupabaseClient } from "./supabaseNodeClient";
import { ensureWorkspaceSeed, WORKSPACE } from "./seedWorkspace";

/**
 * Projected-PYQ practice pool fixture.
 *
 * Closes the PR-5 exit gate's missing half: the workspace seed had no projected
 * verified-PYQ pool, so the full "aspirant completes and reviews a verified
 * previous-year paper" flow could never be exercised end-to-end (PR #946
 * Remaining Work). This seeds exactly what `start_pyq_practice(mode='paper')`
 * requires to assemble a launchable attempt, mirroring the real projection
 * bridge (migration 183/229) without invoking the CMS projection RPC:
 *
 *   - a VERIFIED `pyq_papers` row on the E2E workspace exam (so `/pyq-summary`
 *     counts it and `ExamIntelligenceCatalogue`/`PyqExplorerSection` surface it),
 *   - VERIFIED `pyq_questions` on that paper (printed order via question_number),
 *   - a primary VERIFIED `pyq_question_topic_tags` row per question (drives the
 *     `by_subject` distribution),
 *   - `mock_question_bank` rows (reviewer_status='verified', pyq_question_id +
 *     pyq_paper_id set, a valid MCQ snapshot: 4 options + correct_option_id),
 *   - 4 `mock_question_options` per bank row with printed `source_label`/
 *     `display_order`, option_index 1 always correct,
 *   - an ACTIVE `pyq_mock_question_projections` row per bank row — the guard the
 *     launch predicate and `practice_ready_counts_by_paper` both require.
 *
 * All rows use fixed UUIDs and service-role upserts so re-runs converge without
 * drift. `mock_reviewer_status` only admits draft/reviewed/locked/verified/live
 * (no 'published'), so bank rows are seeded 'verified'.
 */

const PP = "e2e0e2e0-0000-4000-8000-";
const uid = (n: number): string => PP + n.toString(16).padStart(12, "0");

const QUESTION_COUNT = 3;
const OPTIONS_PER_Q = 4;

export const PYQ_PRACTICE = {
  // A verified paper distinct from seedWorkspace's pending `paperId`, so the
  // pending paper keeps driving pyq_workbench "partial" readiness elsewhere.
  paperId: uid(0xf0),
  year: 2023,
  questionCount: QUESTION_COUNT,
  pyqQuestionId: (q: number): string => uid(0x1a0 + q), // q in 1..3
  bankId: (q: number): string => uid(0x1b0 + q),
  optionId: (q: number, o: number): string => uid(0x1c00 + q * 16 + o),
};

const SOURCE_TYPE = "e2e_fixture";
const PRACTICE_SOURCES = [
  "pyq_practice_paper",
  "pyq_practice_section",
  "pyq_practice_topic",
];
const OPTION_LABELS = ["(a)", "(b)", "(c)", "(d)"];

/**
 * Idempotently ensure the projected-PYQ practice pool exists. Depends on the
 * workspace exam/subject/topic, so it calls ensureWorkspaceSeed() first (also
 * idempotent). Uses the service-role client (bypasses RLS) and upserts on PK.
 */
export async function ensureProjectedPyqPool(): Promise<void> {
  await ensureWorkspaceSeed();

  const env = readEnv();
  const db = createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);
  const nowIso = new Date().toISOString();

  // 1) Verified PYQ paper on the workspace exam.
  const { error: paperErr } = await db.from("pyq_papers").upsert(
    {
      id: PYQ_PRACTICE.paperId,
      exam_id: WORKSPACE.examId,
      year: PYQ_PRACTICE.year,
      source_type: "community",
      trust_status: "verified",
      metadata: { seed: SOURCE_TYPE },
    },
    { onConflict: "id" },
  );
  if (paperErr) throw new Error(`pyq_papers upsert: ${paperErr.message}`);

  // 2) Verified canonical PYQ questions (printed order via question_number).
  const pyqQuestions = Array.from({ length: QUESTION_COUNT }, (_, i) => {
    const q = i + 1;
    return {
      id: PYQ_PRACTICE.pyqQuestionId(q),
      pyq_paper_id: PYQ_PRACTICE.paperId,
      question_number: q,
      display_order: q,
      source_question_ref: `Q${q}`,
      question_text: `PYQ practice question ${q} — projected verified previous-year item.`,
      question_type: "mcq",
      observed_difficulty: "medium",
      reviewer_status: "verified",
      language: "en",
      metadata: { seed: SOURCE_TYPE },
    };
  });
  const { error: pqErr } = await db
    .from("pyq_questions")
    .upsert(pyqQuestions, { onConflict: "id" });
  if (pqErr) throw new Error(`pyq_questions upsert: ${pqErr.message}`);

  // 3) Primary verified topic tag per question → drives by_subject.
  const tags = pyqQuestions.map((pq) => ({
    question_id: pq.id,
    topic_id: WORKSPACE.topicId,
    tag_role: "primary",
    tagging_source: "manual",
    reviewer_status: "verified",
    metadata: { seed: SOURCE_TYPE },
  }));
  const { error: tagErr } = await db
    .from("pyq_question_topic_tags")
    .upsert(tags, { onConflict: "question_id,topic_id,tag_role" });
  if (tagErr) throw new Error(`pyq_question_topic_tags upsert: ${tagErr.message}`);

  // 4) Mock bank rows — verified, PYQ-linked, with a launch-ready MCQ snapshot.
  const bankRows = Array.from({ length: QUESTION_COUNT }, (_, i) => {
    const q = i + 1;
    return {
      id: PYQ_PRACTICE.bankId(q),
      exam_id: WORKSPACE.examId,
      subject_id: WORKSPACE.subjectId,
      topic_id: WORKSPACE.topicId,
      question_text: `PYQ practice question ${q} — projected verified previous-year item.`,
      question_type: "mcq",
      difficulty: "medium",
      correct_option_id: PYQ_PRACTICE.optionId(q, 1), // option_index 1 is correct
      explanation: `E2E fixture explanation for projected PYQ Q${q}.`,
      source_type: SOURCE_TYPE,
      reviewer_status: "verified",
      pyq_question_id: PYQ_PRACTICE.pyqQuestionId(q),
      pyq_paper_id: PYQ_PRACTICE.paperId,
      pyq_year: PYQ_PRACTICE.year,
    };
  });
  const { error: bankErr } = await db
    .from("mock_question_bank")
    .upsert(bankRows, { onConflict: "id" });
  if (bankErr) throw new Error(`mock_question_bank upsert: ${bankErr.message}`);

  // 5) Options — 4 per bank row, printed source_label + display_order, index 1 correct.
  const options = bankRows.flatMap((_, i) => {
    const q = i + 1;
    return Array.from({ length: OPTIONS_PER_Q }, (__, j) => {
      const o = j + 1;
      return {
        id: PYQ_PRACTICE.optionId(q, o),
        question_id: PYQ_PRACTICE.bankId(q),
        option_text: `PYQ Q${q} option ${OPTION_LABELS[j]}${o === 1 ? " (correct)" : ""}`,
        option_index: o,
        is_correct: o === 1,
        source_label: OPTION_LABELS[j],
        display_order: o,
      };
    });
  });
  const { error: optErr } = await db
    .from("mock_question_options")
    .upsert(options, { onConflict: "question_id,option_index" });
  if (optErr) throw new Error(`mock_question_options upsert: ${optErr.message}`);

  // 6) Active projection bridge rows — the guard the launch predicate requires.
  const projections = bankRows.map((row) => ({
    pyq_question_id: row.pyq_question_id,
    mock_question_id: row.id,
    source_content_hash: `e2e-fixture-hash-${row.id}`,
    sync_status: "active",
    last_sync_result: { seed: SOURCE_TYPE },
    projected_at: nowIso,
    updated_at: nowIso,
  }));
  const { error: projErr } = await db
    .from("pyq_mock_question_projections")
    .upsert(projections, { onConflict: "pyq_question_id" });
  if (projErr) throw new Error(`pyq_mock_question_projections upsert: ${projErr.message}`);
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
    .in("source", PRACTICE_SOURCES);
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
