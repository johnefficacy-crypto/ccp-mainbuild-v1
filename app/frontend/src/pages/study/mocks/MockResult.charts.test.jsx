import React from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { render, screen, fireEvent } from "@testing-library/react";
import MockResult from "./MockResult";

jest.mock("../../../lib/api", () => ({ api: { get: jest.fn() } }));

// Capture the props the distribution charts receive so we can assert they are
// fed real data (heatmap cells / dwell buckets), not the old empty placeholders.
jest.mock("../components/reports/AccuracyHeatmap", () => ({
  __esModule: true,
  default: ({ topics, cells }) => (
    <div
      data-testid="heatmap-mock"
      data-names={(topics || []).map((t) => t.topic_name).join("|")}
      data-cells={(cells || [])
        .map((c) => `${c.topic_id}:${c.difficulty}=${Math.round(c.accuracy_pct)}`)
        .join("|")}
    />
  ),
}));
jest.mock("../components/reports/TimeDistributionChart", () => ({
  __esModule: true,
  default: ({ data }) => (
    <div
      data-testid="timedist-mock"
      data-buckets={(data || []).map((d) => `${d.bucket}=${d.count}`).join("|")}
    />
  ),
}));

const RESULT = {
  score_percentage: 50,
  total_correct: 2,
  total_wrong: 1,
  time_used_sec: 200,
  avg_time_per_q_sec: 40,
  section_breakdown: [],
  per_question: [
    { question_id: "q1", time_spent_sec: 15 }, // 0–30s
    { question_id: "q2", time_spent_sec: 45 }, // 30–60s
    { question_id: "q3", time_spent_sec: 140 }, // 2–3m
    { question_id: "q4", time_spent_sec: 0 }, // skipped → excluded
  ],
};

const ANALYTICS = {
  topic_breakdown: [
    {
      topic_id: "topic-a",
      topic_name: "Algebra",
      difficulty_breakdown: {
        easy: { att: 2, corr: 2 },
        medium: { att: 4, corr: 2 },
        hard: { att: 0, corr: 0 },
      },
    },
  ],
};

function renderResult() {
  const { api } = require("../../../lib/api");
  api.get.mockImplementation((url) => {
    if (url.endsWith("/result")) return Promise.resolve(RESULT);
    if (url.endsWith("/analytics")) return Promise.resolve(ANALYTICS);
    return Promise.resolve({});
  });
  render(
    <MemoryRouter initialEntries={["/app/study/mocks/attempts/att1/result"]}>
      <Routes>
        <Route path="/app/study/mocks/attempts/:attemptId/result" element={<MockResult />} />
      </Routes>
    </MemoryRouter>,
  );
}

test("Topic tab feeds real names and per-difficulty accuracy cells (not empty)", async () => {
  renderResult();
  await screen.findByTestId("result-page");
  fireEvent.click(screen.getByTestId("result-tab-topic"));

  const heatmap = await screen.findByTestId("heatmap-mock");
  // Real topic name, never the raw topic UUID.
  expect(heatmap).toHaveAttribute("data-names", "Algebra");
  const cells = heatmap.getAttribute("data-cells");
  // easy 2/2=100, medium 2/4=50; hard has 0 attempts → no cell.
  expect(cells).toContain("topic-a:easy=100");
  expect(cells).toContain("topic-a:medium=50");
  expect(cells).not.toContain("hard");
});

test("Time tab feeds a real dwell histogram, excluding 0s questions", async () => {
  renderResult();
  await screen.findByTestId("result-page");
  fireEvent.click(screen.getByTestId("result-tab-time"));

  const chart = await screen.findByTestId("timedist-mock");
  const buckets = chart.getAttribute("data-buckets");
  expect(buckets).toContain("0–30s=1");
  expect(buckets).toContain("30–60s=1");
  expect(buckets).toContain("2–3m=1");
  // The 0s (skipped) question is excluded, so 3m+ stays empty.
  expect(buckets).toContain("3m+=0");
});
