import { test, expect } from "@playwright/test";
import { WORKSPACE, ensureAdminUser, getAdminAccessToken, resetTopicAliases, ensureWorkspaceSeed } from "../fixtures/seedWorkspace";
import { readEnv } from "../fixtures/env";

/**
 * Flow: topic-edit drawer — highest-risk regressions from PR #548.
 *
 * The drawer opens from TopicTreePanel's Edit button, which only renders when
 * proposals are present. Since the NLP/Tesseract pipeline is not available in
 * CI containers (Issue #537), UI-path tests that depend on proposals are marked
 * fixme and will auto-run once Tesseract is installed.
 *
 * The CMS API contract tests below exercise the same backend endpoints the
 * drawer calls (PATCH /topics, POST /topic-aliases, DELETE /topic-aliases/{id})
 * using a real Supabase-backed backend and the seeded admin user.  These are
 * genuine E2E tests — they prove the full auth → permission → DB write path
 * works, which is what broke the "403 on alias delete" regression.
 */

type ApiHelper = (method: string, path: string, body?: unknown) => Promise<Response>;

async function makeApi(): Promise<ApiHelper> {
  const token = await getAdminAccessToken();
  const env = readEnv();
  return (method, path, body) =>
    fetch(`${env.backendURL}${path}`, {
      method,
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
}

const CMS = "/api/admin/exam-intelligence-cms";

test.describe("Flow: topic-edit CMS API contract", () => {
  test.beforeAll(async () => {
    await ensureWorkspaceSeed();
    await ensureAdminUser();
    await resetTopicAliases();
  });

  test.afterAll(async () => {
    await resetTopicAliases();
  });

  test("PATCH /topics/{id} updates name and records audit entry", async () => {
    const api = await makeApi();
    const res = await api("PATCH", `${CMS}/topics/${WORKSPACE.topicId}`, {
      reason: "E2E regression: update topic name",
      payload: { name: "E2E Federalism Updated" },
    });
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.row.name).toBe("E2E Federalism Updated");
    expect(typeof data.audit_id).toBe("string");

    // Restore
    const restore = await api("PATCH", `${CMS}/topics/${WORKSPACE.topicId}`, {
      reason: "E2E regression: restore topic name",
      payload: { name: "E2E Federalism" },
    });
    expect(restore.status).toBe(200);
  });

  test("PATCH /topics/{id} rejects reason shorter than 8 chars with 422", async () => {
    const api = await makeApi();
    const res = await api("PATCH", `${CMS}/topics/${WORKSPACE.topicId}`, {
      reason: "short",
      payload: { name: "Bad" },
    });
    expect(res.status).toBe(422);
  });

  test("POST /topic-aliases creates alias and appears in GET list", async () => {
    const api = await makeApi();
    const res = await api("POST", `${CMS}/topic-aliases`, {
      reason: "E2E regression: add alias",
      payload: {
        topic_id: WORKSPACE.topicId,
        alias: "E2E Centre-State Relations",
      },
    });
    expect(res.status).toBe(200);
    const data = await res.json();
    expect(data.ok).toBe(true);
    expect(data.row.alias).toBe("E2E Centre-State Relations");
    expect(data.row.topic_id).toBe(WORKSPACE.topicId);

    // Verify it appears in the list endpoint
    const list = await api("GET", `${CMS}/topic-aliases?topic_id=${WORKSPACE.topicId}`);
    expect(list.status).toBe(200);
    const listData = await list.json();
    const found = listData.items?.find((a: { alias: string }) => a.alias === "E2E Centre-State Relations");
    expect(found).toBeTruthy();
  });

  test("DELETE /topic-aliases/{id} removes alias (reason via query param)", async () => {
    const api = await makeApi();

    // Create an alias to delete
    const create = await api("POST", `${CMS}/topic-aliases`, {
      reason: "E2E regression: alias to delete",
      payload: { topic_id: WORKSPACE.topicId, alias: "E2E Temp Alias" },
    });
    expect(create.status).toBe(200);
    const { row } = await create.json();

    // Delete with reason as a QUERY PARAMETER (not body — this is the backend contract)
    const del = await api(
      "DELETE",
      `${CMS}/topic-aliases/${row.id}?reason=${encodeURIComponent("E2E regression: remove alias")}`,
    );
    expect(del.status).toBe(200);
    const delData = await del.json();
    expect(delData.ok).toBe(true);
    expect(delData.id).toBe(row.id);

    // Verify removed from list
    const list = await api("GET", `${CMS}/topic-aliases?topic_id=${WORKSPACE.topicId}`);
    const listData = await list.json();
    const still = listData.items?.find((a: { id: string }) => a.id === row.id);
    expect(still).toBeFalsy();
  });

  test("GET /topics returns the seeded topic", async () => {
    const api = await makeApi();
    const res = await api("GET", `${CMS}/topics?limit=200&subject_id=${WORKSPACE.subjectId}`);
    expect(res.status).toBe(200);
    const data = await res.json();
    const found = data.items?.find((t: { id: string }) => t.id === WORKSPACE.topicId);
    expect(found).toBeTruthy();
    expect(found.slug).toBe("e2e-federalism");
  });
});

// ---------------------------------------------------------------------------
// UI path — requires NLP pipeline (Tesseract). Skipped in CI until #537 resolved.
// ---------------------------------------------------------------------------
test.describe("Flow: topic-edit drawer UI (requires Tesseract)", () => {
  test("Edit button opens drawer and dirty-check blocks close without reason", async () => {
    // test.skip inside the test is valid in all Playwright versions
    test.skip(
      !process.env.E2E_TESSERACT_AVAILABLE,
      "Requires Tesseract + syllabus document — enable with E2E_TESSERACT_AVAILABLE=1",
    );
    // Skeleton — fill in once Tesseract is available in CI.
    // Full flow: login as admin → workspace → Syllabus Mapper tab → run propose
    // → Edit button appears in TopicTreePanel → drawer opens → dirty field →
    // Cancel shows confirm dialog → Save with reason + dirty closes drawer.
    throw new Error("Skeleton: implement when Tesseract available");
  });
});
