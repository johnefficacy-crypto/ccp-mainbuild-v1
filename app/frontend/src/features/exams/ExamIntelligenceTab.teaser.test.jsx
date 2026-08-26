import React from "react";
import { render, screen, waitFor, within } from "@testing-library/react";

jest.mock("react-router-dom", () => ({ useNavigate: () => jest.fn() }));
jest.mock("../../lib/api", () => ({ api: { get: jest.fn(), post: jest.fn() } }));
const { api } = require("../../lib/api");
const ExamIntelligenceTab = require("./ExamIntelligenceTab").default;

// Verified-only intelligence payload with more than one paper and more than one
// heatmap row, so the OLD teaser would have rendered "Verified papers" (2) and
// "Covered subjects" (2) cards. The trimmed teaser must show ONLY the headline
// "Verified tagged questions" card.
const payload = {
  available: true,
  competition_series: [],
  cutoff_series: {},
  vacancy_series: { total: [], by_category: {} },
  topics: [],
  verified_pyq_counts: {},
  pyq_papers: [{ id: "p1" }, { id: "p2" }],
  difficulty_heatmap: {
    verified_question_count: 1234,
    buckets: ["easy", "medium", "hard", "unknown"],
    rows: [
      { subject_id: "s1", subject_name: "Polity", counts: {}, total: 0 },
      { subject_id: "s2", subject_name: "History", counts: {}, total: 0 },
    ],
  },
};

beforeEach(() => {
  api.get.mockReset();
  api.get.mockResolvedValue(payload);
});

async function renderTeaser() {
  render(<ExamIntelligenceTab examSlug="upsc-cse" />);
  return within(await screen.findByTestId("pyq-practice-summary"));
}

test("teaser renders a single verified-questions card, not the redundant 3-card grid", async () => {
  const box = await renderTeaser();

  // The one headline card: verified tagged questions, formatted en-IN.
  expect(box.getByText("Verified tagged questions")).toBeInTheDocument();
  expect(box.getByTestId("verified-question-count")).toHaveTextContent("1,234");

  // The two removed cards must be gone from THIS teaser (Verified papers lives
  // in PyqExplorerSection's own summary a scroll below; Covered subjects was a
  // bare count with no subject names).
  expect(box.queryByText("Verified papers")).not.toBeInTheDocument();
  expect(box.queryByText("Covered subjects")).not.toBeInTheDocument();
});

test("teaser keeps the Browse & practice PYQs CTA pointing at #pyq-explorer", async () => {
  const box = await renderTeaser();

  const cta = box.getByTestId("intel-start-pyq-cta");
  expect(cta).toHaveAttribute("href", "#pyq-explorer");
  expect(cta).toHaveTextContent(/Browse & practice PYQs/);
});
