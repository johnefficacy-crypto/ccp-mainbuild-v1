import React from "react";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";

import StrategyFeedSection from "./StrategyFeedSection";
import useStrategyFeed from "./useStrategyFeed";

jest.mock("./useStrategyFeed", () => ({ __esModule: true, default: jest.fn() }));

afterEach(() => jest.clearAllMocks());

const item = (over = {}) => ({
  id: "h1", subject_family: "quant", name: "Base-100 percentage method",
  strategy_type: "shortcut", formula_latex: "x = \\frac{a}{b}",
  standard_method: "the long way", faster_method: "scale to 100",
  key_observation: null, common_traps: "off-by-base", relevance: "primary",
  times_seen: 4, wrong_count: 3, correct_count: 1, last_seen_at: "2026-07-12T00:00:00Z",
  source_question_ids: ["q1"], ...over,
});

function renderSection(feed) {
  useStrategyFeed.mockReturnValue({ refresh: jest.fn(), ...feed });
  return render(
    <StrategyFeedSection
      subject="quant"
      testId="improvement-lab-quant"
      eyebrow="Quantitative Aptitude"
      title="Methods & Shortcuts"
      sub="Faster methods and shortcuts"
      emptyDescription="Attempt more Quant to see this."
    />,
  );
}

test("live: renders a card with evidence and DTO fields; hides null fields", () => {
  renderSection({ items: [item()], status: "live" });
  expect(screen.getByTestId("improvement-lab-quant-list")).toBeInTheDocument();
  expect(screen.getByTestId("strategy-feed-card-h1")).toBeInTheDocument();
  expect(screen.getByText("Base-100 percentage method")).toBeInTheDocument();
  const evidence = screen.getByTestId("strategy-feed-evidence-h1");
  expect(evidence).toHaveTextContent("Seen 4");
  expect(evidence).toHaveTextContent("Missed 3");
  expect(evidence).toHaveTextContent("Correct 1");
  expect(screen.getByText("Standard method")).toBeInTheDocument();
  expect(screen.getByText("Faster method")).toBeInTheDocument();
  expect(screen.getByText("Watch out for")).toBeInTheDocument();
  // key_observation is null → no row.
  expect(screen.queryByTestId("strategy-feed-h1-key_observation")).toBeNull();
});

test("empty: renders the section's empty state (testid contract preserved)", () => {
  renderSection({ items: [], status: "empty" });
  expect(screen.getByTestId("improvement-lab-quant-empty")).toBeInTheDocument();
  expect(screen.queryByTestId("improvement-lab-quant-list")).toBeNull();
});

test("error: renders a retryable error card scoped to this section", () => {
  renderSection({ items: [], status: "error" });
  expect(screen.getByTestId("improvement-lab-quant-error")).toBeInTheDocument();
  expect(screen.getByText("Methods & Shortcuts unavailable")).toBeInTheDocument();
});

test("loading: renders an accessible loading state", () => {
  renderSection({ items: [], status: "loading" });
  const loading = screen.getByTestId("improvement-lab-quant-loading");
  expect(loading).toBeInTheDocument();
  expect(loading).toHaveAttribute("role", "status");
});
