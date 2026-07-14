import React from "react";
import { render, screen } from "@testing-library/react";
import SolutionStrategyPanel from "../shared/SolutionStrategyPanel";
import QuestionRenderer from "../QuestionRenderer";

const strat = (over = {}) => ({
  id: "s1", subject_family: "quant", name: "Base-100 percentage method",
  strategy_type: "shortcut", formula_latex: "x = \\frac{a}{b}",
  standard_method: "the long division way", faster_method: "scale to 100",
  key_observation: null, worked_example: "40% of 250 = 100", common_traps: "off-by-base",
  relevance: "primary", ...over,
});

describe("SolutionStrategyPanel", () => {
  test("renders in review mode with learner labels and the formula", () => {
    render(<SolutionStrategyPanel mode="review" strategies={[strat()]} />);
    expect(screen.getByTestId("solution-strategy-panel")).toBeInTheDocument();
    expect(screen.getByText("Base-100 percentage method")).toBeInTheDocument();
    expect(screen.getByText("Standard method")).toBeInTheDocument();
    expect(screen.getByText("Faster method")).toBeInTheDocument();
    expect(screen.getByText("Watch out for")).toBeInTheDocument();
    expect(screen.getByTestId("solution-strategy-s1-formula")).toBeInTheDocument();
    // A null field renders no row.
    expect(screen.queryByTestId("solution-strategy-s1-key_observation")).toBeNull();
  });

  test("is absent during an active attempt", () => {
    render(<SolutionStrategyPanel mode="attempt" strategies={[strat()]} />);
    expect(screen.queryByTestId("solution-strategy-panel")).toBeNull();
  });

  test("renders nothing for missing or empty strategy arrays", () => {
    const { rerender } = render(<SolutionStrategyPanel mode="review" strategies={[]} />);
    expect(screen.queryByTestId("solution-strategy-panel")).toBeNull();
    rerender(<SolutionStrategyPanel mode="review" strategies={undefined} />);
    expect(screen.queryByTestId("solution-strategy-panel")).toBeNull();
  });
});

describe("QuestionRenderer solution-strategy wiring", () => {
  const q = {
    id: "q1", question_type: "mcq_single", question_text: "Pick one",
    options: [{ id: "o1", option_index: "A", option_text: "One" }],
    correct_option_id: "o1", explanation: "ok",
  };

  test("mounts the panel once after the type renderer in review mode", () => {
    render(
      <QuestionRenderer
        mode="review"
        showCorrect
        showExplanation
        question={{ ...q, solution_strategies: [strat()] }}
      />,
    );
    expect(screen.getAllByTestId("solution-strategy-panel")).toHaveLength(1);
    expect(screen.getByText("Base-100 percentage method")).toBeInTheDocument();
  });

  test("no panel during an attempt even when strategies are present", () => {
    render(
      <QuestionRenderer
        mode="attempt"
        question={{ ...q, solution_strategies: [strat()] }}
        value={{}}
        onChange={jest.fn()}
      />,
    );
    expect(screen.queryByTestId("solution-strategy-panel")).toBeNull();
  });
});
