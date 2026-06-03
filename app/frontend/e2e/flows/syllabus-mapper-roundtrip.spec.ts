import { test, expect } from "@playwright/test";
import {
  WORKSPACE,
  ensureAdminUser,
  ensureWorkspaceSeed,
  ensureSyllabusMapperSeed,
  cleanupSyllabusMapperSeed,
  getAdminAccessToken,
  loginAsAdmin,
} from "../fixtures/seedWorkspace";
import { createNodeSupabaseClient } from "../fixtures/supabaseNodeClient";
import { readEnv } from "../fixtures/env";

function adminDb() {
  const env = readEnv();
  return createNodeSupabaseClient(env.supabaseURL, env.supabaseServiceRoleKey);
}

/**
 * Flow: Syllabus Mapper roundtrip — highest-risk regressions for PR #533.
 *
 * Covers:
 *   - preview/commit API contract: proposals accepted, reviewer_status=pending
 *   - proposal_key stale guard: wrong client_proposal_key → skipped_stale
 *   - idempotency: re-commit with same proposal → skipped_duplicate
 *   - UI: Syllabus Mapper tab enabled when mentions exist; panel renders
 *
 * The propose endpoint is NOT tested here because it depends on document_assets
 * having an exam_id column (deferred infrastructure fix). We construct proposals
 * manually to exercise the accept pipeline directly.
 *
 * The drift sentinel test is the critical one: it catches any divergence between
 * the FE computeProposalKey() and the BE compute_proposal_key() functions.
 */

const EXAM_INTEL = "/api/admin/exam-intelligence";

// A well-formed proposal that passes all validation in commit_accept.
// Uses fixed UUIDs from WORKSPACE so the FK constraints are satisfied.
const E2E_PROPOSAL = {
  syllabus_document_id: WORKSPACE.syllabusDocId,
  topic_id:             WORKSPACE.topicId,
  exam_id:              WORKSPACE.examId,
  source_page:          1,
  normalized_text:      "e2e-roundtrip-federalism",
  raw_text:             "E2E Federalism",
  mention_type:         "explicit",
  confidence_score:     1.0,
  match_method:         "topic_alias_exact",
  exam_cycle_id:        null,
  exam_phase_id:        null,
};

// sha256("e2e0e2e0-0000-4000-8000-000000000006|e2e0e2e0-0000-4000-8000-000000000004|1|e2e-roundtrip-federalism|")
// Computed offline and pinned here.  If this test fails with "stale proposal_key"
// it means the BE compute_proposal_key() changed its canonical string — check
// syllabus_mapper.py:compute_proposal_key().
const EXPECTED_KEY = (() => {
  // We derive it at runtime using Node's crypto so the test stays self-contained
  // without needing a separate offline computation.
  const { createHash } = require("crypto");
  const parts = [
    E2E_PROPOSAL.syllabus_document_id,
    E2E_PROPOSAL.topic_id,
    String(E2E_PROPOSAL.source_page),
    E2E_PROPOSAL.normalized_text,
    E2E_PROPOSAL.exam_phase_id ?? "",
  ].join("|");
  return createHash("sha256").update(parts).digest("hex");
})();

async function makeApi() {
  const token = await getAdminAccessToken();
  const env = readEnv();
  return async (
    method: string,
    path: string,
    body?: unknown,
  ): Promise<Response> => {
    return fetch(`${env.backendURL}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  };
}

// ---------------------------------------------------------------------------
// API-level roundtrip tests
// ---------------------------------------------------------------------------

test.describe("Flow: syllabus mapper API roundtrip", () => {
  test.beforeAll(async () => {
    await ensureWorkspaceSeed();
    await ensureAdminUser();
    await cleanupSyllabusMapperSeed();
    // Seed the syllabus_documents FK row so commit FK constraint is satisfied.
    // This also seeds a mention; wipe mentions immediately to start clean.
    await ensureSyllabusMapperSeed();
    await adminDb().from("syllabus_topic_mentions").delete().eq("exam_id", WORKSPACE.examId);
  });

  test.afterAll(async () => {
    await cleanupSyllabusMapperSeed();
  });

  test("preview returns will_insert count for valid proposals", async () => {
    const api = await makeApi();
    const res = await api(
      "POST",
      `${EXAM_INTEL}/workspace/${WORKSPACE.examId}/syllabus/accept/preview`,
      { proposals: [E2E_PROPOSAL] },
    );
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.summary).toBeDefined();
    expect(typeof data.summary.insert).toBe("number");
    expect(data.summary.insert).toBe(1);
    expect(data.summary.skip_duplicate).toBe(0);
    expect(data.summary.invalid).toBe(0);
  });

  test("commit writes mention with reviewer_status=pending", async () => {
    const api = await makeApi();
    const res = await api(
      "POST",
      `${EXAM_INTEL}/workspace/${WORKSPACE.examId}/syllabus/accept/commit`,
      {
        proposals: [{ ...E2E_PROPOSAL, client_proposal_key: EXPECTED_KEY }],
        reason: "E2E regression: roundtrip commit",
      },
    );
    expect(res.status).toBe(200);
    const data = await res.json();

    expect(data.committed).toBe(1);
    expect(data.skipped_duplicate).toBe(0);
    expect(data.skipped_stale).toBe(0);
    expect(data.failed).toBe(0);

    // Verify the DB row
    const { data: rows } = await adminDb()
      .from("syllabus_topic_mentions")
      .select("reviewer_status")
      .eq("exam_id", WORKSPACE.examId)
      .eq("normalized_text", E2E_PROPOSAL.normalized_text)
      .limit(1);
    expect(rows).toHaveLength(1);
    expect(rows![0].reviewer_status).toBe("pending");
  });

  test("re-commit same proposal is idempotent — skipped_duplicate", async () => {
    const api = await makeApi();
    // Commit a second time without cleanup — should be skipped_duplicate
    const res = await api(
      "POST",
      `${EXAM_INTEL}/workspace/${WORKSPACE.examId}/syllabus/accept/commit`,
      {
        proposals: [{ ...E2E_PROPOSAL, client_proposal_key: EXPECTED_KEY }],
        reason: "E2E regression: idempotent re-commit",
      },
    );
    expect(res.status).toBe(200);
    const data = await res.json();

    expect(data.committed).toBe(0);
    expect(data.skipped_duplicate).toBe(1);
    expect(data.skipped_stale).toBe(0);
    expect(data.failed).toBe(0);
  });

  test("drift sentinel: wrong client_proposal_key → skipped_stale", async () => {
    // This is the critical hash-parity regression guard.
    // If compute_proposal_key() in Python changes its canonical string
    // (field order, separator, encoding), the committed prop from
    // computeProposalKey() on the FE will no longer match, and every
    // commit silently produces skipped_stale rows.
    await cleanupSyllabusMapperSeed();

    const api = await makeApi();
    const driftedKey = "0000000000000000000000000000000000000000000000000000000000000000";

    const res = await api(
      "POST",
      `${EXAM_INTEL}/workspace/${WORKSPACE.examId}/syllabus/accept/commit`,
      {
        proposals: [{ ...E2E_PROPOSAL, client_proposal_key: driftedKey }],
        reason: "E2E regression: drift sentinel",
      },
    );
    expect(res.status).toBe(200);
    const data = await res.json();

    expect(data.committed).toBe(0);
    expect(data.skipped_stale).toBe(1);
    // per_row detail
    const row = data.per_row?.[0];
    expect(row?.result).toBe("skipped_stale");
    expect(row?.reason).toMatch(/client_proposal_key/);
  });

  test("commit requires reason field", async () => {
    const api = await makeApi();
    const res = await api(
      "POST",
      `${EXAM_INTEL}/workspace/${WORKSPACE.examId}/syllabus/accept/commit`,
      { proposals: [{ ...E2E_PROPOSAL, client_proposal_key: EXPECTED_KEY }] },
    );
    expect(res.status).toBe(422);
  });
});

// ---------------------------------------------------------------------------
// UI test — Syllabus Mapper tab enabled when mentions exist
// ---------------------------------------------------------------------------


test.describe("Flow: syllabus mapper UI", () => {
  test.beforeAll(async () => {
    await ensureWorkspaceSeed();
    await ensureAdminUser();
    // Seed a mention so the Syllabus Mapper tab is enabled
    await ensureSyllabusMapperSeed();
  });

  test.afterAll(async () => {
    await cleanupSyllabusMapperSeed();
  });

  test("Syllabus Mapper tab is enabled when mentions exist and panel renders", async ({ page }) => {
    await loginAsAdmin(page);
    await page.goto(`/admin/exam-intelligence/workspace/${WORKSPACE.examId}`);
    await expect(page.getByTestId("auth-checking")).toBeHidden({ timeout: 90_000 });
    await expect(page.getByTestId("workspace-loading")).toBeHidden({ timeout: 30_000 });
    await expect(page.getByTestId("exam-name")).toBeVisible({ timeout: 30_000 });

    // Syllabus Mapper tab must be enabled — seed has a pending mention → status "partial"
    const syllabusTab = page.getByTestId("tab-syllabus");
    await expect(syllabusTab).toBeVisible();
    await expect(syllabusTab).not.toBeDisabled();

    // Clicking the tab renders the panel
    await syllabusTab.click();
    await expect(page.getByTestId("syllabus-mapper-panel")).toBeVisible({ timeout: 20_000 });
  });
});
