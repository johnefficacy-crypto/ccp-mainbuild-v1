import React from "react";
import { MemoryRouter } from "react-router-dom";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

const mockGet = jest.fn();
const mockPost = jest.fn();
jest.mock("../../lib/api", () => ({
  __esModule: true,
  api: {
    get: (...args) => mockGet(...args),
    post: (...args) => mockPost(...args),
  },
}));

// env.js throws at module load without REACT_APP_BACKEND_URL; useApiCollection
// pulls ENABLE_DEMO_DATA from it. Stub so the suite is hermetic.
jest.mock("../../shared/config/env", () => ({
  __esModule: true,
  ENABLE_DEMO_DATA: false,
  BACKEND_URL: "http://test.local",
  API_TIMEOUT_MS: 15000,
}));

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => {
  const actual = jest.requireActual("react-router-dom");
  return { __esModule: true, ...actual, useNavigate: () => mockNavigate };
});

// Radar chart is heavy (recharts) and irrelevant to this page's behavior. Capture its
// `data` prop so we can assert what the mastery radar is (and is not) fed.
const radarData = [];
jest.mock("./components/reports", () => ({
  __esModule: true,
  TopicRadarChart: ({ data }) => {
    radarData.length = 0;
    (data || []).forEach((d) => radarData.push(d));
    return null;
  },
}));

import ToastProvider from "../../shared/ui/ToastProvider";
import Subjects from "./Subjects";

function renderPage() {
  return render(
    <MemoryRouter>
      <ToastProvider>
        <Subjects />
      </ToastProvider>
    </MemoryRouter>,
  );
}

const SUBJECTS = [
  {
    subject_id: "sub-english",
    subject: "English",
    progress: 62,
    trend: "up",
    weak_count: 3,
    locked_topics: 8,
    practice: {
      available: true,
      modes: [
        {
          type: "english_writing",
          label: "Sentence practice",
          target_topic_id: null,
          route_type: "server_launch",
          launch_mode: "english_writing",
        },
        {
          type: "error_lab",
          label: "Improvement Lab",
          target_topic_id: null,
          route_type: "client_route",
          route: "/app/study/improvement-lab",
        },
      ],
    },
  },
  {
    subject_id: "sub-quant",
    subject: "Quantitative Aptitude",
    progress: 40,
    trend: "flat",
    weak_count: 5,
    locked_topics: 12,
    practice: { available: false, modes: [] },
  },
  {
    subject_id: "00000000-0000-0000-0000-0000000000ca",
    subject: "Current Affairs",
    kind: "current_affairs",
    progress: 0,
    trend: "flat",
    weak_count: 0,
    locked_topics: 0,
    practice: {
      available: true,
      modes: [
        {
          type: "weekly_current_affairs",
          label: "Weekly current affairs",
          target_topic_id: null,
          route_type: "server_launch",
          launch_mode: "weekly_current_affairs",
        },
      ],
    },
  },
];

beforeEach(() => {
  mockGet.mockReset();
  mockPost.mockReset();
  mockNavigate.mockReset();
});

test("renders subject cards from the mocked /api/study/subjects", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  renderPage();

  expect(screen.getByTestId("subjects-page")).toBeTruthy();
  await waitFor(() => expect(screen.getByText("English")).toBeTruthy());
  expect(screen.getByText("Quantitative Aptitude")).toBeTruthy();
  // Mastery summary line preserved.
  expect(screen.getByText(/62% mastery · 3 weak · 8 topics/)).toBeTruthy();
});

test("a server_launch button POSTs the launch endpoint and navigates to the returned route", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  mockPost.mockResolvedValue({ kind: "english_writing", route: "/app/study/practice/english/abc" });
  renderPage();

  const btn = await screen.findByTestId("practice-sub-english-english_writing");
  fireEvent.click(btn);

  await waitFor(() =>
    expect(mockPost).toHaveBeenCalledWith(
      "/api/study/subjects/sub-english/practice/start",
      { mode: "english_writing", topic_id: null },
    ),
  );
  await waitFor(() =>
    expect(mockNavigate).toHaveBeenCalledWith("/app/study/practice/english/abc"),
  );
});

test("client_route mode renders a link (no POST)", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  renderPage();

  const link = await screen.findByTestId("practice-sub-english-error_lab");
  expect(link.tagName.toLowerCase()).toBe("a");
  expect(link.getAttribute("href")).toBe("/app/study/improvement-lab");
});

test("a subject with practice.available=false shows the calm no-practice copy", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  renderPage();

  await waitFor(() => expect(screen.getByText("Quantitative Aptitude")).toBeTruthy());
  expect(screen.getByTestId("practice-sub-quant-none").textContent).toMatch(
    /No verified practice set yet/,
  );
});

const CA_ID = "00000000-0000-0000-0000-0000000000ca";

test("current-affairs card shows a cadence subline, not a mastery line", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  renderPage();

  await screen.findByTestId(`subject-card-${CA_ID}`);
  const card = screen.getByTestId(`subject-card-${CA_ID}`);
  expect(card.textContent).toMatch(/current-affairs only, no mastery/);
  expect(card.textContent).not.toMatch(/% mastery/);
});

test("weekly current-affairs launch navigates to the returned CA attempt route", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  mockPost.mockResolvedValue({
    kind: "current_affairs",
    outcome: "ready",
    route: "/app/study/current-affairs/attempts/ca-1",
  });
  renderPage();

  const btn = await screen.findByTestId(`practice-${CA_ID}-weekly_current_affairs`);
  fireEvent.click(btn);

  await waitFor(() =>
    expect(mockPost).toHaveBeenCalledWith(
      `/api/study/subjects/${CA_ID}/practice/start`,
      { mode: "weekly_current_affairs", topic_id: null },
    ),
  );
  await waitFor(() =>
    expect(mockNavigate).toHaveBeenCalledWith("/app/study/current-affairs/attempts/ca-1"),
  );
});

test("weekly current-affairs no_bundle outcome shows a calm note and does not navigate", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  // no_bundle is returned as a 200 body with an outcome and NO route.
  mockPost.mockResolvedValue({ kind: "current_affairs", outcome: "no_bundle" });
  renderPage();

  const btn = await screen.findByTestId(`practice-${CA_ID}-weekly_current_affairs`);
  fireEvent.click(btn);

  await waitFor(() =>
    expect(screen.getByTestId(`practice-${CA_ID}-notice`).textContent).toMatch(
      /No current-affairs set is published/,
    ),
  );
  expect(mockNavigate).not.toHaveBeenCalled();
});

test("a CA integrity-conflict 409 surfaces an error, not the calm no-practice note", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  const err = new Error("bundle_set_mismatch");
  err.status = 409;
  err.code = "ca_integrity_conflict";
  mockPost.mockRejectedValue(err);
  renderPage();

  const btn = await screen.findByTestId(`practice-${CA_ID}-weekly_current_affairs`);
  fireEvent.click(btn);

  // Error toast fires (not the calm availability copy); no navigation, no calm note.
  expect(await screen.findByText(/Couldn't start practice/i)).toBeTruthy();
  expect(screen.queryByTestId(`practice-${CA_ID}-notice`)).toBeNull();
  expect(mockNavigate).not.toHaveBeenCalled();
});

test("the mastery radar excludes the current-affairs card", async () => {
  // The virtual CA card (progress:0) must never plot as a 0%-mastery subject.
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  renderPage();
  await screen.findByTestId(`subject-card-${CA_ID}`);
  await waitFor(() => expect(radarData.length).toBeGreaterThan(0));
  expect(radarData.some((d) => d.topic === "Current Affairs")).toBe(false);
  // Real mastery subjects still plot.
  expect(radarData.some((d) => d.topic === "English")).toBe(true);
});

test("a 409 on launch shows an inline notice and does not navigate", async () => {
  mockGet.mockResolvedValue({ items: SUBJECTS, count: SUBJECTS.length });
  const err = new Error("no_eligible_prompt");
  err.status = 409;
  mockPost.mockRejectedValue(err);
  renderPage();

  const btn = await screen.findByTestId("practice-sub-english-english_writing");
  fireEvent.click(btn);

  await waitFor(() =>
    expect(screen.getByTestId("practice-sub-english-notice").textContent).toMatch(
      /No verified practice set yet/,
    ),
  );
  expect(mockNavigate).not.toHaveBeenCalled();
});

// ─── Topic drill-down (PR #1032 endpoint wiring) ────────────────────────────

// One macro with a high-yield locked child + a null-coverage (not-yet-scored)
// child, plus a rollup 0-evidence macro — the three coverage states.
const TOPIC_TREE = [
  {
    topic_id: "m1", name: "Ancient India", level: "topic",
    is_rollup_zero_evidence: false,
    coverage: { exam_priority_score: 82, is_high_yield: true },
    children: [
      {
        topic_id: "c1", name: "Indus Valley", level: "microtopic",
        is_rollup_zero_evidence: false,
        coverage: { exam_priority_score: 60, is_high_yield: false }, children: [],
      },
      {
        topic_id: "c2", name: "Vedic Age", level: "microtopic",
        is_rollup_zero_evidence: false, coverage: null, children: [],
      },
    ],
  },
  {
    topic_id: "r1", name: "General mental ability", level: "topic",
    is_rollup_zero_evidence: true,
    coverage: { exam_priority_score: 30, is_high_yield: false }, children: [],
  },
];

// Route api.get by URL: the subjects list vs the per-subject topic tree.
function routeGet(treeResolver = async () => ({ subject_id: "sub-english", topics: TOPIC_TREE })) {
  mockGet.mockImplementation((url) =>
    String(url).includes("/topics")
      ? treeResolver(url)
      : Promise.resolve({ items: SUBJECTS, count: SUBJECTS.length }),
  );
}

test("expanding a subject fetches its topic tree and shows all three coverage states distinctly", async () => {
  routeGet();
  renderPage();

  const toggle = await screen.findByTestId("subject-topics-toggle-sub-english");
  fireEvent.click(toggle);

  await waitFor(() =>
    expect(mockGet).toHaveBeenCalledWith("/api/study/subjects/sub-english/topics"),
  );

  // Locked coverage → priority number + high-yield pill.
  await screen.findByTestId("topic-node-m1");
  expect(screen.getByTestId("topic-priority-m1").textContent).toMatch(/priority 82/);
  expect(screen.getByText("high-yield")).toBeTruthy();

  // Rollup 0-evidence → "not yet reliable", NOT a priority number, de-emphasized.
  expect(screen.getByTestId("topic-rollup-r1")).toBeTruthy();
  expect(screen.queryByTestId("topic-priority-r1")).toBeNull();
  // Its row is visually muted (opacity), never styled like a real ranked topic.
  const rollupRow = screen.getByTestId("topic-node-r1").querySelector("div");
  expect(rollupRow.className).toMatch(/opacity-55/);
});

test("macro → microtopic nesting expands and collapses; null-coverage child is 'not yet scored'", async () => {
  routeGet();
  renderPage();

  fireEvent.click(await screen.findByTestId("subject-topics-toggle-sub-english"));
  await screen.findByTestId("topic-node-m1");

  // Children hidden until the macro is expanded.
  expect(screen.queryByTestId("topic-node-c1")).toBeNull();

  fireEvent.click(screen.getByTestId("topic-toggle-m1"));
  await screen.findByTestId("topic-node-c1");
  // Locked child shows its priority; null-coverage child shows "not yet scored"
  // (no fake placeholder score), never conflated with the locked state.
  expect(screen.getByTestId("topic-priority-c1").textContent).toMatch(/priority 60/);
  expect(screen.getByTestId("topic-unscored-c2")).toBeTruthy();
  expect(screen.queryByTestId("topic-priority-c2")).toBeNull();

  // Collapse hides the children again.
  fireEvent.click(screen.getByTestId("topic-toggle-m1"));
  await waitFor(() => expect(screen.queryByTestId("topic-node-c1")).toBeNull());
});

test("topic tree shows a loading state then the tree", async () => {
  let resolveTree;
  routeGet(() => new Promise((res) => { resolveTree = res; }));
  renderPage();

  fireEvent.click(await screen.findByTestId("subject-topics-toggle-sub-english"));
  // Loading placeholder appears while the fetch is in flight.
  expect(await screen.findByTestId("topic-tree-loading")).toBeTruthy();

  resolveTree({ subject_id: "sub-english", topics: TOPIC_TREE });
  await screen.findByTestId("topic-tree");
  expect(screen.queryByTestId("topic-tree-loading")).toBeNull();
});

test("topic tree error state offers a retry that refetches", async () => {
  let calls = 0;
  routeGet(() => {
    calls += 1;
    return calls === 1
      ? Promise.reject(new Error("boom"))
      : Promise.resolve({ subject_id: "sub-english", topics: TOPIC_TREE });
  });
  renderPage();

  fireEvent.click(await screen.findByTestId("subject-topics-toggle-sub-english"));
  const retry = await screen.findByTestId("topic-tree-retry");

  fireEvent.click(retry);
  await screen.findByTestId("topic-tree");
  expect(screen.queryByTestId("topic-tree-error")).toBeNull();
});

test("the current-affairs card has no topic drill-down", async () => {
  routeGet();
  renderPage();
  await screen.findByTestId(`subject-card-${CA_ID}`);
  expect(screen.queryByTestId(`subject-topics-toggle-${CA_ID}`)).toBeNull();
  // Real subjects do have it.
  expect(screen.getByTestId("subject-topics-toggle-sub-english")).toBeTruthy();
});
