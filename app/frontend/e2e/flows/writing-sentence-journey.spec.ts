import { test, expect } from "@playwright/test";
import { ensureSeededUser, loginViaUi, getAccessToken } from "../fixtures/seedUser";
import { ensureAdminUser, getAdminAccessToken } from "../fixtures/seedWorkspace";
import {
  resolveEnglishScope,
  createStudyTask,
  seedActiveSentencePrompt,
  launchWriting,
  getErrorLab,
  runWritingEvaluator,
  runWritingMasteryOutbox,
} from "../fixtures/seedWriting";

/**
 * EWP-SP5 — English sentence-practice journey, real browser + real backend/DB.
 *
 * Governance chain (operator → reviewer → manager → reviewer → release authority)
 * is driven through the REAL Content Studio APIs as the seeded super_admin, so
 * the flow is self-seeding and does not depend on the OPERATOR-PENDING live
 * prompt bank. The learner half is driven through the REAL SPA:
 *   launch (server-owned) → practice route → source_text visible → compose +
 *   submit (version CAS) → async worker → issue shown → mandatory rewrite →
 *   unit completes → Error Lab receives the issue lineage.
 *
 * The async EWP-2B evaluation worker is normally APScheduler-driven; the e2e job
 * runs the backend with ENABLE_SCHEDULER=false, so the spec ticks the worker
 * deterministically via the existing admin manual-trigger endpoint
 * (POST /api/admin/jobs/run/writing:evaluate) — the SAME code path the scheduler
 * calls. This is a test control tick, not a product route.
 *
 * Mock evaluator rules (language_evaluator.py) make the flow deterministic:
 *   "They is going to the market."  -> subject_verb_agreement (must_fix)
 *                                      => unit transitions to rewrite_required
 *   "The students are going to the market." -> no issues => ready/completed
 */

const SOURCE_TEXT = "Context: describe a routine using the present tense.";
const FLAWED = "They is going to the market.";
const CLEAN = "The students are going to the market.";

async function waitWorker(adminToken: string): Promise<void> {
  // The claim/run RPC processes at most one job per pass; a fresh submit enqueues
  // exactly one language_evaluation job, so a single pass drains it. Retry a few
  // times to absorb claim/lease races without hiding a real stall.
  //
  // `POST /admin/jobs/run/{job_id}` returns HTTP 200 even when the job records an
  // operational failure (encoded as `ok:false` in the body), so assert `ok===true`
  // — an HTTP-status-only check would go green on a broken worker.
  let last: { status: number; body: any } | null = null;
  for (let i = 0; i < 5; i += 1) {
    const r = await runWritingEvaluator(adminToken);
    last = r;
    expect(r.status, JSON.stringify(r.body)).toBe(200);
    expect(r.body?.ok, JSON.stringify(r.body)).toBe(true);
    if ((r.body?.result?.processed ?? 0) >= 1) return;
    await new Promise((res) => setTimeout(res, 500));
  }
  throw new Error(`writing:evaluate never processed a job: ${JSON.stringify(last?.body)}`);
}

test.describe("EWP-SP5: sentence-practice journey (real backend/DB)", () => {
  let adminToken = "";
  let learnerToken = "";
  let userId = "";
  let taskId = "";
  let sessionRoute = "";

  test.beforeAll(async () => {
    const user = await ensureSeededUser();
    userId = user.id;
    await ensureAdminUser();
    adminToken = await getAdminAccessToken();
    learnerToken = await getAccessToken();

    // (1) operator import → reviewer verify → manager propose target → reviewer
    // activate target → release authority activates the prompt (content_studio.activate).
    const scope = await resolveEnglishScope();
    const promptId = await seedActiveSentencePrompt(adminToken, {
      subjectId: scope.subjectId,
      topicId: scope.sentenceTopicId,
      sourceText: SOURCE_TEXT,
    });
    expect(promptId).toBeTruthy();

    // (2) a planner writing task pinned to the English sentence-construction scope.
    taskId = await createStudyTask({
      userId,
      subjectId: scope.subjectId,
      topicId: scope.sentenceTopicId,
    });

    // (3) learner launches via the server-owned endpoint (SP3 shipped backend
    // only — no learner "launch" button yet), then the browser navigates to the
    // returned practice route. No new frontend routing/nav is added.
    const launch = await launchWriting(learnerToken, taskId);
    expect(launch.status, JSON.stringify(launch.body)).toBe(200);
    expect(launch.body.session_id).toBeTruthy();
    sessionRoute = launch.body.practice_route;
    expect(sessionRoute).toBe(`/app/study/practice/english/${launch.body.session_id}`);
  });

  test("launch → source visible → submit → worker → issue → rewrite → complete → Error Lab", async ({
    page,
  }) => {
    await loginViaUi(page);
    await page.goto(sessionRoute);

    // Practice shell renders the launched session.
    await expect(page.getByTestId("english-practice-shell")).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId("unit-1")).toBeVisible();

    // (4) source_text (present on this prompt's snapshot) is shown read-only.
    await expect(page.getByTestId("sentence-builder")).toBeVisible();
    await expect(page.getByTestId("source-context")).toBeVisible();
    await expect(page.getByTestId("source-context-text")).toContainText(SOURCE_TEXT);
    await expect(page.getByTestId("source-context")).toHaveAttribute("data-readonly", "true");

    // (5) compose + submit version 1 (the composer sends version_number=1 CAS).
    await page.getByTestId("sentence-input").fill(FLAWED);
    await page.getByTestId("sentence-submit").click();

    // Unit moves to evaluation_pending; the async worker has not run yet.
    await expect(page.getByTestId("unit-1-pending")).toBeVisible({ timeout: 30_000 });

    // (6) drive the async language-evaluation worker (scheduler off in CI).
    await waitWorker(adminToken);

    // (7) the must_fix issue surfaces and the unit demands a rewrite.
    await expect(page.getByTestId("issue-card")).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId("rewrite-editor")).toBeVisible();

    // (8) Error Lab receives the issue lineage while the flawed answer is the
    // current state (assert BEFORE the rewrite supersedes it — the rewrite
    // resolves the must_fix, dropping it from affects_current_state).
    const errorLab = await getErrorLab(learnerToken);
    expect(errorLab.status, JSON.stringify(errorLab.body)).toBe(200);
    const allIssues = (errorLab.body.items || []).flatMap((g: any) => g.issues || []);
    expect(allIssues.some((i: any) => i.issue_type === "subject_verb_agreement")).toBe(true);

    // (9) rewrite cleanly → submit next version (CAS derived from server latest).
    await page.getByTestId("rewrite-input").fill(CLEAN);
    await page.getByTestId("rewrite-submit").click();
    await expect(page.getByTestId("unit-1-pending")).toBeVisible({ timeout: 30_000 });
    await waitWorker(adminToken);

    // (10) unit (and single-unit session) completes.
    await expect(page.getByTestId("unit-1-done")).toBeVisible({ timeout: 30_000 });

    // Mastery outbox drains without error (shadow/gated — no assertion on
    // mastery magnitude, only that the pass is operationally clean).
    const outbox = await runWritingMasteryOutbox(adminToken);
    expect(outbox.status).toBe(200);
    // job-run returns 200 even on an operational failure — require ok:true.
    expect(outbox.body?.ok, JSON.stringify(outbox.body)).toBe(true);

    // Error Lab entry point is reachable from the shell (no sidebar surface).
    await expect(page.getByTestId("error-lab-link")).toBeVisible();
  });
});
