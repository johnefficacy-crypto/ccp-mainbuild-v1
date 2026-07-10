// Study Home Next-action CTA wiring for planner-shaped English writing tasks.
//
// Regression pin for the Mission Control launch-shaping fix: a planner task
// carrying launch_type === "english_writing_session" with a NULL
// launch_entity_id (no pre-existing session) must render the
// LaunchWritingPracticeButton — NOT the generic "Start → /app/study/plan"
// CTA. The button launches through POST /api/study/tasks/{id}/launch-writing,
// so it only needs task.id + launch_type, never a session id.
import React from "react";
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

const mockGet = jest.fn();
jest.mock("../../lib/api", () => ({
  __esModule: true,
  api: { get: (...a) => mockGet(...a), post: jest.fn() },
}));

// Data-layer hook behind the launch button: stub so no real network fires.
jest.mock(
  "../../features/study/english-practice/useEnglishPracticeSession",
  () => ({ __esModule: true, default: () => ({ launchWriting: jest.fn() }) }),
);

// Heavy sibling cards make their own fetches; stub to isolate NextActionCard.
jest.mock("../../features/study/components/ExamCycleTimeline", () => () => null);
jest.mock("../../features/study/components/ExamJourneyCard", () => () => null);
jest.mock("../../features/study/components/PlanChangeLogCard", () => () => null);
jest.mock("../../shared/components/HowItWorksHeaderButton", () => () => null);

// eslint-disable-next-line global-require
const StudyHome = require("./StudyHome").default;

// A planner-shaped writing task: launch_type set, launch_entity_id null,
// action_url null (mission_control shapes it this way before a session exists).
const MC_RESPONSE = {
  plan: { id: "plan-1", target: "Cover locked topics", theme: "Adaptive" },
  today_tasks: [
    {
      id: "task-eng",
      title: "Sentence practice",
      status: "planned",
      done: false,
      launch_type: "english_writing_session",
      launch_entity_id: null,
      action_url: null,
      action_label: "Start sentence practice",
    },
  ],
  focus: { total_hours_7d: 0, week: [] },
  exam_context: { high_yield_topics: [] },
  competition_context: {},
  plan_reasoning: {},
};

beforeEach(() => {
  mockGet.mockReset();
  mockGet.mockImplementation((url) => {
    if (url === "/api/study/mission-control") return Promise.resolve(MC_RESPONSE);
    if (url.startsWith("/api/study/report-card/history")) return Promise.resolve({ items: [] });
    if (url.startsWith("/api/study/report-card")) return Promise.resolve(null);
    return Promise.reject(new Error(`unexpected GET ${url}`));
  });
});

function renderPage() {
  return render(
    <MemoryRouter>
      <StudyHome />
    </MemoryRouter>,
  );
}

test("renders LaunchWritingPracticeButton for a planner task with null launch_entity_id", async () => {
  const { findByTestId, queryByTestId } = renderPage();
  const btn = await findByTestId("launch-writing-btn");
  expect(btn).toHaveTextContent("Start sentence practice");
  // The generic "Start → /app/study/plan" CTA must NOT render for a writing task.
  expect(queryByTestId("study-home-next-action-cta")).toBeNull();
});
