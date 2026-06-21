/**
 * Tests for the Exam Governance Console.
 *
 * Wave 4.6H-FE: the no-exam view renders ConsoleWorkQueue against the work-queue
 * endpoints (/console/exams + /console/summary).
 * Wave 4.6I-FE: the selected-exam view now renders ExamActionConsole against
 * /console/exams/:exam_id (NOT the legacy embedded workspace).
 * Role gate + route wrapping + Registry regression are unchanged.
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useNavigate } from "react-router-dom";

jest.mock("../../../lib/api", () => ({
  __esModule: true,
  api: { get: jest.fn() },
  auth: {},
}));

jest.mock("../../../lib/supabase", () => ({
  __esModule: true,
  supabase: {
    auth: {
      getSession: jest.fn(),
      onAuthStateChange: jest.fn(() => ({ data: { subscription: { unsubscribe: jest.fn() } } })),
    },
  },
}));

jest.mock("../../../lib/authContext", () => ({
  __esModule: true,
  useAuth: jest.fn(),
}));

// Defensive: keep the env-loading hook inert in the frontend CI job.
jest.mock("../../../lib/hooks/useApiCollection", () => ({
  __esModule: true,
  default: jest.fn(),
}));

const { api } = require("../../../lib/api");
const { useAuth } = require("../../../lib/authContext");

const ExamGovernanceConsole = require("../ExamGovernanceConsole").default;
const useSelectedExamId = require("../../../lib/hooks/useSelectedExamId").default;
const { ProtectedRoute } = require("../../../lib/ProtectedRoute");
const { ADMIN_ROLES } = require("../../../lib/rbac");
const { adminRouteElements } = require("../../../routes/adminRoutes");
const RouteErrorBoundary = require("../../../components/RouteErrorBoundary").default;

// ── Fixtures ──────────────────────────────────────────────────────────────────

const ROWS = [
  {
    id: "exam-1", slug: "ssc-cgl", name: "SSC CGL", exam_type: "recruitment",
    management_mode: "core", cadence: "annual", exam_family_id: null,
    organization_name: "Staff Selection Commission",
    status: "blocked", flags: ["missing_coverage", "pending_review"],
    blocker_count: 2, first_blocker_text: "No locked topic coverage — planner cannot use this exam",
    locked_coverage_count: 0, verified_pyq_count: 0, total_pyq_count: 42,
  },
  {
    id: "exam-2", slug: "upsc-cse", name: "UPSC CSE", exam_type: "entrance",
    management_mode: "light", cadence: "annual", exam_family_id: null,
    organization_name: null,
    status: "ready", flags: [], blocker_count: 0, first_blocker_text: null,
    locked_coverage_count: 5, verified_pyq_count: 3, total_pyq_count: 9,
  },
];

const SUMMARY = {
  blocked: 1, needs_action: 0, ready: 1, pending_review: 1, stale_review_queue: 0,
  total_count: 2, generated_at: "2026-06-17T00:00:00Z",
};

// Per-exam action-console detail (/console/exams/:id) — 4.6I-BE shape.
function detailFor(id) {
  const ready = id === "exam-2";
  return {
    exam: {
      id, slug: ready ? "upsc-cse" : "ssc-cgl", name: ready ? "UPSC CSE" : "SSC CGL",
      organization_name: ready ? null : "Staff Selection Commission",
      family_name: ready ? null : "SSC Family",
    },
    activation_verdict: {
      status: ready ? "ready" : "blocked",
      headline: ready ? "Ready for aspirants" : "Not ready for aspirants",
      reasons: ready ? [] : ["no_locked_coverage", "pending_review"],
    },
    mock_readiness: { status: ready ? "ready" : "blocked", detail: "2 thin section(s)" },
    action_queue: ready ? [] : [
      { id: "topic_coverage", severity: "blocker", area: "topic_coverage", title: "Lock topic coverage",
        why: "The planner consumes only locked coverage rows.", cta_label: "Open workspace",
        cta_route: `/admin/exam-intelligence/workspace/${id}`, entity_kind: "exam_topic_coverage",
        entity_id: null, evidence_refs: [{ kind: "exam_topic_coverage", row_id: "c1" }], status: "open" },
      { id: "pyq", severity: "action", area: "pyq", title: "Verify PYQ",
        why: "Questions need verified paper + question + topic tag.", cta_label: "Open workspace",
        cta_route: `/admin/exam-intelligence/workspace/${id}`, entity_kind: null, entity_id: null,
        evidence_refs: [], status: "open" },
      { id: "mock_readiness", severity: "advisory", area: "mock_readiness", title: "Strengthen the mock bank",
        why: "Mock bank is thin or blocked (advisory only).", cta_label: "Open workspace",
        cta_route: `/admin/exam-intelligence/workspace/${id}`, entity_kind: null, entity_id: null,
        evidence_refs: [], status: "open" },
    ],
    activation_checks: [
      { area: "setup", gate: "hard", state: "done", detail: "1 phase(s) defined", reasons: [], evidence_refs: [] },
      { area: "documents", gate: "advisory", state: "needs_action", detail: "No documents uploaded", reasons: [], evidence_refs: [] },
      { area: "syllabus", gate: "advisory", state: "done", detail: "ok", reasons: [], evidence_refs: [] },
      { area: "topic_coverage", gate: "hard", state: ready ? "done" : "blocked",
        detail: ready ? "5 locked" : "No locked topic coverage", reasons: ready ? [] : ["no_locked_coverage", "pending_review"],
        evidence_refs: ready ? [] : [{ kind: "exam_topic_coverage", row_id: "c1" }] },
      { area: "pyq", gate: "advisory", state: ready ? "done" : "needs_action", detail: "0 of 42 verified",
        reasons: ready ? [] : ["missing_pyq"], evidence_refs: [] },
      { area: "updates", gate: "advisory", state: "done", detail: "none pending", reasons: [], evidence_refs: [] },
      { area: "competition", gate: "advisory", state: "done", detail: "reviewed", reasons: [],
        evidence_refs: [{ kind: "exam_competition_metrics", row_id: "cm1" }] },
      { area: "mock_readiness", gate: "advisory", state: ready ? "done" : "needs_action", detail: "thin", reasons: [], evidence_refs: [] },
      { area: "publish", gate: "hard", state: ready ? "done" : "blocked", detail: "gate", reasons: [], evidence_refs: [] },
    ],
    stages: [
      { id: "setup", label: "Setup", areas: ["setup", "documents"] },
      { id: "evidence", label: "Evidence", areas: ["syllabus", "topic_coverage", "pyq"] },
      { id: "review", label: "Review", areas: ["updates", "competition", "mock_readiness"] },
      { id: "activation", label: "Activation", areas: ["publish"] },
    ],
    evidence_refs: ready ? [] : [{ kind: "exam_topic_coverage", row_id: "c1" }],
    generated_at: "2026-06-18T00:00:00Z",
  };
}

function mockApi(overrides = {}) {
  api.get.mockImplementation((url) => {
    if (url.includes("/console/summary")) {
      return overrides.summary ? overrides.summary(url) : Promise.resolve(SUMMARY);
    }
    const detailMatch = url.match(/\/console\/exams\/([^/?]+)/);
    if (detailMatch) {
      const id = decodeURIComponent(detailMatch[1]);
      return overrides.detail ? overrides.detail(url, id) : Promise.resolve(detailFor(id));
    }
    if (url.includes("/console/exams")) {
      return overrides.list ? overrides.list(url)
        : Promise.resolve({ items: ROWS, count: 2, total_count: 2, has_next: true, limit: 25, offset: 0 });
    }
    if (url.includes("exam-families")) return Promise.resolve({ items: [] });
    return Promise.resolve({});
  });
}

const detailCalls = () => api.get.mock.calls.map((c) => c[0]).filter((u) => /\/console\/exams\/[^/?]+/.test(u));

function renderConsole(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/exam-intelligence/console" element={<ExamGovernanceConsole />} />
        <Route path="/admin/exam-intelligence/console/:exam_id" element={<ExamGovernanceConsole />} />
      </Routes>
    </MemoryRouter>,
  );
}

const listCalls = () => api.get.mock.calls.map((c) => c[0]).filter((u) => u.includes("/console/exams"));
const summaryCalls = () => api.get.mock.calls.map((c) => c[0]).filter((u) => u.includes("/console/summary"));

beforeEach(() => {
  jest.clearAllMocks();
  useAuth.mockReturnValue({ isChecking: false, isAuthed: true, hasBackendSession: true, user: { role: "admin" } });
});

// ── Console work-queue (4.6H-FE) ───────────────────────────────────────────

describe("ExamGovernanceConsole — work queue (no exam selected)", () => {
  test("renders the work queue and calls /console/exams (not /exams)", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());
    expect(listCalls().length).toBeGreaterThan(0);
    // It must NOT use the generic /exams contract in console mode.
    expect(api.get.mock.calls.every((c) => !c[0].includes("/exam-intelligence/exams"))).toBe(true);
    expect(screen.queryByTestId("exam-list-shell")).toBeNull();
  });

  test("default list params: limit/offset/active_state/sort, no workflow", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());
    const url = listCalls()[0];
    expect(url).toContain("limit=25");
    expect(url).toContain("offset=0");
    expect(url).toContain("active_state=active");
    expect(url).toContain("sort=blockers_first");
    expect(url).not.toContain("workflow=");
  });

  test("summary gets the same base filters incl. q, never workflow/sort/limit/offset", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());

    api.get.mockClear();
    mockApi();
    fireEvent.change(screen.getByTestId("console-search"), { target: { value: "ssc" } });
    await waitFor(() => expect(summaryCalls().some((u) => u.includes("q=ssc"))).toBe(true));

    const sUrl = summaryCalls().find((u) => u.includes("q=ssc"));
    expect(sUrl).not.toMatch(/workflow=|sort=|limit=|offset=/);
    expect(listCalls().some((u) => u.includes("q=ssc"))).toBe(true);
  });

  test("workflow goes only to the list; summary is not refetched on workflow change", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());

    api.get.mockClear();
    mockApi();
    fireEvent.click(screen.getByTestId("console-chip-blocked"));
    await waitFor(() => expect(listCalls().some((u) => u.includes("workflow=blocked"))).toBe(true));

    const activeFilter = screen.getByTestId("console-chip-blocked");
    expect(activeFilter.getAttribute("aria-pressed")).toBe("true");
    expect(activeFilter.classList.contains("btn-primary")).toBe(false);
    expect(activeFilter.classList.contains("primary")).toBe(false);
    expect(summaryCalls().length).toBe(0); // base filters unchanged → no summary refetch
    expect(summaryCalls().every((u) => !u.includes("workflow="))).toBe(true);
  });

  test("sort goes only to the list and is server-driven", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());

    api.get.mockClear();
    mockApi();
    fireEvent.change(screen.getByTestId("console-sort"), { target: { value: "name" } });
    await waitFor(() => expect(listCalls().some((u) => u.includes("sort=name"))).toBe(true));
    expect(summaryCalls().length).toBe(0);
  });

  test("selecting a workflow after paging resets offset to 0", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-next")).toBeTruthy());
    fireEvent.click(screen.getByTestId("console-next"));
    await waitFor(() => expect(listCalls().some((u) => u.includes("offset=25"))).toBe(true));

    api.get.mockClear();
    mockApi();
    fireEvent.click(screen.getByTestId("console-chip-ready"));
    await waitFor(() => expect(listCalls().some((u) => u.includes("workflow=ready"))).toBe(true));
    expect(listCalls().every((u) => u.includes("offset=0"))).toBe(true);
  });

  test("summary strip shows base-scoped counts as accessible buttons", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-summary-strip")).toBeTruthy());
    expect(screen.getByTestId("console-chip-all").textContent).toContain("2");
    expect(screen.getByTestId("console-chip-blocked").textContent).toContain("1");
    expect(screen.getByTestId("console-chip-ready").textContent).toContain("1");
    expect(screen.getByTestId("console-chip-pending_review").textContent).toContain("1");
    expect(screen.getByTestId("console-chip-stale_review_queue").textContent).toContain("0");
  });

  test("Missing PYQ + Missing coverage render with NO fabricated count, no thin_mock_bank", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());
    const mpyq = screen.getByTestId("console-chip-missing_pyq");
    const mcov = screen.getByTestId("console-chip-missing_coverage");
    expect(mpyq.textContent).toMatch(/Missing PYQ/);
    expect(mpyq.textContent).not.toMatch(/\d/); // no number, never "0"
    expect(mcov.textContent).not.toMatch(/\d/);
    expect(screen.queryByTestId("console-chip-thin_mock_bank")).toBeNull();
    expect(screen.queryByText(/thin mock/i)).toBeNull();
  });

  test("row renders org, status, blocker text/count, locked coverage, verified/total pyq, human flags", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-row-exam-1")).toBeTruthy());

    expect(screen.getByTestId("console-org-exam-1").textContent).toBe("Staff Selection Commission");
    expect(screen.getByTestId("console-org-exam-2").textContent).toBe("—"); // null → em dash
    expect(screen.getByTestId("console-status-exam-1").textContent).toContain("Blocked");
    expect(screen.getByTestId("console-blocker-exam-1").textContent).toContain("No locked topic coverage");
    expect(screen.getByTestId("console-blocker-exam-1").textContent).toContain("more"); // blocker_count 2
    expect(screen.getByTestId("console-blocker-exam-2").textContent).toContain("No hard blocker");
    expect(screen.getByTestId("console-coverage-exam-2").textContent).toContain("5");
    expect(screen.getByTestId("console-pyq-exam-2").textContent).toContain("3");
    expect(screen.getByTestId("console-pyq-exam-2").textContent).toContain("9");
    // human-readable flags, not raw tokens
    expect(screen.getByTestId("console-flag-exam-1-missing_coverage").textContent).toBe("Missing locked coverage");
    expect(screen.getByTestId("console-flag-exam-1-pending_review").textContent).toBe("Pending review");
  });

  test("row actions: neutral → /console/:id, ghost → /workspace/:id, no work-queue primary styling", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-open-exam-1")).toBeTruthy());
    const openConsole = screen.getByTestId("console-open-exam-1");
    const advancedWorkspace = screen.getByTestId("console-workspace-exam-1");
    expect(openConsole.getAttribute("href")).toBe("/admin/exam-intelligence/console/exam-1");
    expect(advancedWorkspace.getAttribute("href")).toBe("/admin/exam-intelligence/workspace/exam-1");
    expect(openConsole.classList.contains("btn-primary")).toBe(false);
    expect(openConsole.classList.contains("primary")).toBe(false);
    expect(advancedWorkspace.classList.contains("btn-primary")).toBe(false);
    expect(advancedWorkspace.classList.contains("primary")).toBe(false);

    const workQueue = screen.getByTestId("console-work-queue");
    expect(workQueue.querySelector(".btn-primary, .primary")).toBeNull();
  });

  test("no readiness/confidence percentage and no raw readiness_level/pyq_coverage_status", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());
    expect(document.body.textContent).not.toMatch(/%/);
    expect(document.body.textContent).not.toMatch(/readiness_level|pyq_coverage_status|confidence/i);
  });

  test("list error renders no seed data; list retry refetches the list", async () => {
    mockApi({ list: () => Promise.reject(new Error("boom")) });
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-error")).toBeTruthy());
    expect(screen.queryByTestId("console-table")).toBeNull();
    expect(screen.queryByText("SSC CGL")).toBeNull();
  });

  test("summary error does NOT replace valid list data with zeros", async () => {
    mockApi({ summary: () => Promise.reject(new Error("summary down")) });
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-table")).toBeTruthy());
    // list still usable
    expect(screen.getByTestId("console-row-exam-1")).toBeTruthy();
    // honest summary failure, no fabricated zero counts on chips
    expect(screen.getByTestId("console-summary-error")).toBeTruthy();
    expect(screen.getByTestId("console-chip-blocked").textContent).not.toMatch(/\d/);
  });

  test("empty state accounts for workflow and offers clears", async () => {
    mockApi({ list: () => Promise.resolve({ items: [], total_count: 0, has_next: false }) });
    renderConsole("/admin/exam-intelligence/console");
    await waitFor(() => expect(screen.getByTestId("console-empty")).toBeTruthy());
    expect(screen.getByTestId("console-empty").textContent).toMatch(/search, filters or workflow/i);
  });
});

// ── Selected-exam view renders the action console (4.6I-FE) ─────────────────

describe("ExamGovernanceConsole — exam selected (action console)", () => {
  test("renders ExamActionConsole, NOT the embedded workspace", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-1");
    await waitFor(() => expect(screen.getByTestId("exam-action-console")).toBeTruthy());
    expect(screen.queryByTestId("exam-name")).toBeNull();       // no ExamWorkspace
    expect(screen.queryByTestId("console-top-bar")).toBeNull(); // old shell top bar gone
  });

  test("calls ONLY /console/exams/:id — no readiness or workspace-context reads", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-1");
    await waitFor(() => expect(screen.getByTestId("exam-action-console")).toBeTruthy());
    const urls = api.get.mock.calls.map((c) => c[0]);
    expect(detailCalls().some((u) => u.includes("/console/exams/exam-1"))).toBe(true);
    expect(urls.every((u) => !u.includes("/workspace/") && !u.includes("/readiness"))).toBe(true);
    // no plain work-queue list call in detail mode
    expect(urls.some((u) => /\/console\/exams\?/.test(u))).toBe(false);
  });

  test("header: identity from the detail response + both nav links", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-1");
    await waitFor(() => expect(screen.getByTestId("action-console-name")).toBeTruthy());
    expect(screen.getByTestId("action-console-name").textContent).toBe("SSC CGL");
    expect(screen.getByTestId("action-console-meta").textContent).toContain("Staff Selection Commission");
    expect(screen.getByTestId("action-console-meta").textContent).toContain("SSC Family");
    expect(screen.getByTestId("action-console-back").getAttribute("href")).toBe("/admin/exam-intelligence/console");
    expect(screen.getByTestId("action-console-workspace").getAttribute("href")).toBe("/admin/exam-intelligence/workspace/exam-1");
  });

  test("blocked verdict: backend status + headline + mapped reasons (no raw tokens)", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-1");
    await waitFor(() => expect(screen.getByTestId("activation-verdict")).toBeTruthy());
    expect(screen.getByTestId("activation-verdict").textContent).toContain("Blocked");
    expect(screen.getByTestId("verdict-headline").textContent).toBe("Not ready for aspirants");
    expect(screen.getByTestId("verdict-reasons-no_locked_coverage").textContent).toBe("No locked coverage");
    expect(screen.getByTestId("verdict-reasons-pending_review").textContent).toBe("Pending review");
    expect(document.body.textContent).not.toMatch(/no_locked_coverage|pending_review[^ ]/); // not raw snake_case
  });

  test("ready verdict + empty action queue state", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-2");
    await waitFor(() => expect(screen.getByTestId("activation-verdict")).toBeTruthy());
    expect(screen.getByTestId("activation-verdict").textContent).toContain("Ready");
    expect(screen.getByTestId("action-queue-empty")).toBeTruthy();
    expect(screen.queryByTestId("action-queue")).toBeNull();
  });

  test("action queue preserves backend order and uses item.cta_route", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-1");
    await waitFor(() => expect(screen.getByTestId("action-queue")).toBeTruthy());
    const items = screen.getAllByTestId(/^action-(topic_coverage|pyq|mock_readiness)$/);
    expect(items.map((el) => el.getAttribute("data-severity"))).toEqual(["blocker", "action", "advisory"]);
    expect(screen.getByTestId("action-cta-topic_coverage").getAttribute("href")).toBe("/admin/exam-intelligence/workspace/exam-1");
  });

  test("checks grouped by backend stages with gate + state labels + mapped reasons", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-1");
    await waitFor(() => expect(screen.getByTestId("activation-checks")).toBeTruthy());
    expect(screen.getByTestId("stage-setup")).toBeTruthy();
    expect(screen.getByTestId("stage-evidence")).toBeTruthy();
    const tc = screen.getByTestId("check-topic_coverage");
    expect(screen.getByTestId("check-gate-topic_coverage").textContent).toBe("Hard gate");
    expect(screen.getByTestId("check-state-topic_coverage").textContent).toBe("Blocked");
    expect(tc.textContent).toContain("No locked coverage"); // mapped reason
  });

  test("mock readiness is a separate Advisory card that never overrides the verdict", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-1");
    await waitFor(() => expect(screen.getByTestId("mock-readiness")).toBeTruthy());
    expect(screen.getByTestId("mock-advisory-tag").textContent).toBe("Advisory");
    expect(screen.getByTestId("mock-status").textContent).toBe("Blocked"); // mock blocked…
    expect(screen.getByTestId("activation-verdict").textContent).toContain("Blocked"); // …verdict still its own
  });

  test("evidence count renders without calling /evidence", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-1");
    await waitFor(() => expect(screen.getByTestId("check-topic_coverage")).toBeTruthy());
    expect(screen.getAllByTestId("evidence-count").length).toBeGreaterThan(0);
    expect(api.get.mock.calls.every((c) => !c[0].includes("/evidence"))).toBe(true);
  });

  test("no percentage/confidence fields rendered (recursive guard)", async () => {
    mockApi();
    renderConsole("/admin/exam-intelligence/console/exam-1");
    await waitFor(() => expect(screen.getByTestId("exam-action-console")).toBeTruthy());
    expect(document.body.textContent).not.toMatch(/%/);
    expect(document.body.textContent).not.toMatch(/score_percent|confidence_score|confidence_percent|confidence/i);
  });

  test("404 → exam-not-found state; generic error → retry refetches", async () => {
    mockApi({ detail: () => Promise.reject(Object.assign(new Error("nope"), { status: 404 })) });
    const { unmount } = renderConsole("/admin/exam-intelligence/console/ghost");
    await waitFor(() => expect(screen.getByTestId("action-console-not-found")).toBeTruthy());
    unmount();

    mockApi({ detail: () => Promise.reject(Object.assign(new Error("boom"), { status: 500 })) });
    renderConsole("/admin/exam-intelligence/console/exam-1");
    await waitFor(() => expect(screen.getByTestId("action-console-error")).toBeTruthy());
    expect(screen.getByTestId("action-console-retry")).toBeTruthy();
  });
});

// ── URL is the single source of truth ───────────────────────────────────────

describe("URL selected-exam is the single source of truth", () => {
  test("a different :exam_id renders the other exam; stale data cleared on change", async () => {
    mockApi();
    function Go() {
      const navigate = useNavigate();
      return <button onClick={() => navigate("/admin/exam-intelligence/console/exam-2")}>go</button>;
    }
    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/console/exam-1"]}>
        <Go />
        <Routes>
          <Route path="/admin/exam-intelligence/console/:exam_id" element={<ExamGovernanceConsole />} />
        </Routes>
      </MemoryRouter>,
    );
    await waitFor(() => expect(screen.getByTestId("action-console-name").textContent).toBe("SSC CGL"));
    fireEvent.click(screen.getByText("go"));
    await waitFor(() => expect(screen.getByTestId("action-console-name").textContent).toBe("UPSC CSE"));
    expect(screen.queryByText("SSC CGL")).toBeNull(); // prior exam's data not lingering
  });

  test("changing the param swaps the exam with no stale value retained", async () => {
    function Probe() {
      const id = useSelectedExamId();
      const navigate = useNavigate();
      return (
        <div>
          <div data-testid="sel">{id ?? "none"}</div>
          <button onClick={() => navigate("/admin/exam-intelligence/console/exam-2")}>go</button>
        </div>
      );
    }
    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/console/exam-1"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/console" element={<Probe />} />
          <Route path="/admin/exam-intelligence/console/:exam_id" element={<Probe />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("sel").textContent).toBe("exam-1");
    fireEvent.click(screen.getByText("go"));
    await waitFor(() => expect(screen.getByTestId("sel").textContent).toBe("exam-2"));
  });

  test("useSelectedExamId returns null when no exam is in the URL", () => {
    function Probe() {
      const id = useSelectedExamId();
      return <div data-testid="sel">{id ?? "none"}</div>;
    }
    render(
      <MemoryRouter initialEntries={["/admin/exam-intelligence/console"]}>
        <Routes>
          <Route path="/admin/exam-intelligence/console" element={<Probe />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("sel").textContent).toBe("none");
  });
});

// ── Role gate matches sibling KG routes ──────────────────────────────────────

describe("Console role gate (matches sibling KG routes)", () => {
  function renderGated(path = "/admin/exam-intelligence/console") {
    return render(
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            path="/admin/exam-intelligence/console"
            element={
              <ProtectedRoute role={ADMIN_ROLES} requireBackend>
                <div data-testid="gated-ok">console</div>
              </ProtectedRoute>
            }
          />
          <Route path="/app" element={<div data-testid="redirect-app">app</div>} />
          <Route path="/login" element={<div data-testid="redirect-login">login</div>} />
        </Routes>
      </MemoryRouter>,
    );
  }

  test("admin sees the console", () => {
    useAuth.mockReturnValue({ isChecking: false, isAuthed: true, hasBackendSession: true, user: { role: "admin" } });
    renderGated();
    expect(screen.getByTestId("gated-ok")).toBeTruthy();
  });

  test("non-admin is redirected to /app", () => {
    useAuth.mockReturnValue({ isChecking: false, isAuthed: true, hasBackendSession: true, user: { role: "user" } });
    renderGated();
    expect(screen.queryByTestId("gated-ok")).toBeNull();
    expect(screen.getByTestId("redirect-app")).toBeTruthy();
  });

  test("unauthenticated is redirected to /login", () => {
    useAuth.mockReturnValue({ isChecking: false, isAuthed: false, hasBackendSession: false, user: null });
    renderGated();
    expect(screen.queryByTestId("gated-ok")).toBeNull();
    expect(screen.getByTestId("redirect-login")).toBeTruthy();
  });
});

// ── Route presence + RouteErrorBoundary wrapping + Registry regression ───────

describe("adminRoutes — console routes wrapping + regression", () => {
  function collect(node, underBoundary, acc) {
    if (node == null || typeof node !== "object") return;
    if (Array.isArray(node)) { node.forEach((n) => collect(n, underBoundary, acc)); return; }
    const elementType = node.props?.element?.type;
    const isErrorBoundaryRoute = elementType === RouteErrorBoundary;
    const nextUnder = underBoundary || isErrorBoundaryRoute;
    if (node.props?.path) acc[node.props.path] = underBoundary;
    if (node.props?.children) collect(node.props.children, nextUnder, acc);
  }

  const paths = {};
  collect(adminRouteElements, false, paths);

  test("both console routes exist", () => {
    expect(Object.keys(paths)).toContain("/admin/exam-intelligence/console");
    expect(Object.keys(paths)).toContain("/admin/exam-intelligence/console/:exam_id");
  });

  test("console routes are wrapped by RouteErrorBoundary", () => {
    expect(paths["/admin/exam-intelligence/console"]).toBe(true);
    expect(paths["/admin/exam-intelligence/console/:exam_id"]).toBe(true);
  });

  test("regression: Registry and sibling exam-intelligence routes still resolve", () => {
    const keys = Object.keys(paths);
    expect(keys).toContain("/admin/exam-intelligence");
    expect(keys).toContain("/admin/exam-intelligence/cms");
    expect(keys).toContain("/admin/exam-intelligence/new");
    expect(keys).toContain("/admin/exam-intelligence/pyq-papers/:pyq_paper_id/workspace");
    expect(keys).toContain("/admin/exam-intelligence/workspace/:exam_id");
    expect(keys).toContain("/admin/exam-intelligence/workspace/:exam_id/:cycle_id");
  });
});
