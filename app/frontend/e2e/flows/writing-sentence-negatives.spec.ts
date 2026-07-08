import { test, expect } from "@playwright/test";
import { ensureSeededUser, getAccessToken } from "../fixtures/seedUser";
import { ensureAdminUser, getAdminAccessToken } from "../fixtures/seedWorkspace";
import {
  resolveEnglishScope,
  ensureExamPhaseFixture,
  createStudyTask,
  createPrompt,
  getPrompt,
  verifyPrompt,
  proposeTarget,
  reviewTarget,
  activatePromptRaw,
  seedActiveSentencePrompt,
  createSession,
  launchWriting,
} from "../fixtures/seedWriting";

/**
 * EWP-SP5 negatives — every case asserts the correct FAIL-CLOSED behavior against
 * the real backend/DB. These are API-level assertions (the fail-closed gates live
 * server-side; the browser is not where they are enforced), which is exactly the
 * determinism/verified-only contract EWP guards.
 *
 * Two cases are visibly test.skip-gated because they cannot be driven end-to-end
 * in the e2e stack — each with a precise reason (see the skip blocks). Nothing
 * asserts "nothing": skipped cases are skipped loudly, not silently green.
 */

test.describe("EWP-SP5 negatives: fail-closed launch/activation gates", () => {
  let adminToken = "";
  let learnerToken = "";
  let userId = "";
  let scope: { subjectId: string; sentenceTopicId: string; grammarTopicId: string };

  test.beforeAll(async () => {
    const user = await ensureSeededUser();
    userId = user.id;
    await ensureAdminUser();
    adminToken = await getAdminAccessToken();
    learnerToken = await getAccessToken();
    scope = await resolveEnglishScope();
    await ensureExamPhaseFixture();
  });

  test("unverified prompt is not launchable (create-session gate 404)", async () => {
    const { id } = await createPrompt(adminToken, {
      subject_id: scope.subjectId,
      topic_id: scope.sentenceTopicId,
      exercise_type: "sentence_construction",
      prompt_text: "An unverified sentence prompt.",
      required_sentence_count: 1,
      difficulty_level: 2,
      min_words: 3,
      max_words: 40,
    });
    // reviewer_status=pending, is_active=false → shared create path denies.
    const res = await createSession(learnerToken, { prompt_id: id });
    expect(res.status).toBe(404);
  });

  test("verified-but-inactive prompt is not launchable (create-session gate 404)", async () => {
    const { id } = await createPrompt(adminToken, {
      subject_id: scope.subjectId,
      topic_id: scope.sentenceTopicId,
      exercise_type: "sentence_construction",
      prompt_text: "A verified but inactive sentence prompt.",
      required_sentence_count: 1,
      difficulty_level: 2,
      min_words: 3,
      max_words: 40,
    });
    await verifyPrompt(adminToken, id);
    // is_active still false (never activated) → not launchable.
    const res = await createSession(learnerToken, { prompt_id: id });
    expect(res.status).toBe(404);
  });

  test("no eligible prompt for the task scope → launch 409 no_eligible_prompt", async () => {
    // Task pinned to the 'grammar' topic, for which no active prompt exists.
    const taskId = await createStudyTask({
      userId,
      subjectId: scope.subjectId,
      topicId: scope.grammarTopicId,
    });
    const res = await launchWriting(learnerToken, taskId);
    expect(res.status).toBe(409);
    expect(JSON.stringify(res.body)).toContain("no_eligible_prompt");
  });

  test("excluded phase is not applicable → launch 409 (exclusion beats global)", async () => {
    const exam = await ensureExamPhaseFixture();
    // Active global prompt (so activation succeeds), then an excluded phase carve-out.
    const promptId = await seedActiveSentencePrompt(adminToken, {
      subjectId: scope.subjectId,
      topicId: scope.sentenceTopicId,
    });
    const excl = await proposeTarget(adminToken, promptId, { exam_phase_id: exam.phaseId });
    await reviewTarget(adminToken, excl.id, excl.updatedAt, "excluded");

    // Task pinned to that excluded phase → most-specific matching band is the
    // excluded phase → default-deny → no eligible prompt.
    const taskId = await createStudyTask({
      userId,
      subjectId: scope.subjectId,
      topicId: scope.sentenceTopicId,
      examId: exam.examId,
      phaseId: exam.phaseId,
    });
    const res = await launchWriting(learnerToken, taskId);
    expect(res.status).toBe(409);
    expect(JSON.stringify(res.body)).toContain("no_eligible_prompt");
  });

  test("stale operator CAS on activate → 409", async () => {
    const { id } = await createPrompt(adminToken, {
      subject_id: scope.subjectId,
      topic_id: scope.sentenceTopicId,
      exercise_type: "sentence_construction",
      prompt_text: "A prompt for the stale-CAS activation check.",
      required_sentence_count: 1,
      difficulty_level: 2,
      min_words: 3,
      max_words: 40,
    });
    await verifyPrompt(adminToken, id);
    const t = await proposeTarget(adminToken, id, { is_global: true });
    await reviewTarget(adminToken, t.id, t.updatedAt, "active");
    // A stale/mismatched CAS token is a HARD error (not a blocker) → 409.
    const stale = await activatePromptRaw(adminToken, id, "2000-01-01T00:00:00+00:00");
    expect(stale.status).toBe(409);
  });

  test("source-dependent type activation is gated (semantic evaluator not live)", async () => {
    // sentence_correction is source-dependent AND not in the runtime allowlist;
    // the semantic-evaluator gate is CLOSED. Activation must fail CLOSED with a
    // 200 {eligible:false, blockers:[...]} verdict and write NOTHING — this is
    // the "semantic adapter unavailable → not activatable" fail-closed behavior.
    const { id } = await createPrompt(adminToken, {
      subject_id: scope.subjectId,
      topic_id: scope.grammarTopicId,
      exercise_type: "sentence_correction",
      prompt_text: "Correct the following sentence.",
      source_text: "He go to school every day.",
      required_sentence_count: 1,
      difficulty_level: 3,
      min_words: 3,
      max_words: 40,
    });
    await verifyPrompt(adminToken, id);
    const t = await proposeTarget(adminToken, id, { is_global: true });
    await reviewTarget(adminToken, t.id, t.updatedAt, "active");
    const p = await getPrompt(adminToken, id);
    const res = await activatePromptRaw(adminToken, id, p.updated_at);
    expect(res.status).toBe(200);
    expect(res.body.result.eligible).toBe(false);
    const blockers = res.body.result.blockers || [];
    expect(
      blockers.includes("exercise_type_not_runtime_ready") ||
        blockers.includes("semantic_evaluator_not_live"),
    ).toBe(true);
    // Fail-closed: it stayed inactive, so it remains not launchable.
    const launchable = await createSession(learnerToken, { prompt_id: id });
    expect(launchable.status).toBe(404);
  });

  // OPERATOR/VERIFY-DB skip: driving the SP1 source-comparison → needs_human_review
  // runtime path requires an ACTIVE source-dependent prompt, but activation of
  // source-dependent types is GATED (semantic_evaluator_not_live) and cannot be
  // opened at test time (opening the gate is a future migration, never a runtime
  // write). The deterministic fail-closed evaluator behavior is covered by the
  // SP1 backend unit suite (test_writing_language_evaluator.py). The e2e-observable
  // half of this contract — that such prompts never activate, so no session/
  // mastery can arise — IS asserted above. Re-enable when the semantic gate opens.
  test.skip("source-comparison uncertain routes to needs_human_review (semantic gate closed)", () => {});

  // Environment skip: the worker retry/backoff path (ewp_fail_evaluation_job) fires
  // only on an evaluator error/timeout. The e2e stack has no deterministic fault-
  // injection hook to force one (the mock evaluator is pure and always succeeds),
  // and adding a product fault path solely for e2e is out of scope. Covered by the
  // backend unit suite (test_writing_evaluation_worker.py — retry, terminal_partial,
  // corrupt-version fail-closed). Re-enable if a test-only fault toggle is added.
  test.skip("worker timeout + retry path (no deterministic fault hook in e2e stack)", () => {});
});
