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

const mcq = {
  id: "q1", question_type: "mcq_single", question_text: "Pick one",
  options: [{ id: "o1", option_index: "A", option_text: "One" }],
  correct_option_id: "o1", explanation: "ok",
};

describe("SolutionStrategyPanel", () => {
  test("renders in review mode with learner labels and the formula through MathRenderer", () => {
    render(<SolutionStrategyPanel mode="review" strategies={[strat()]} />);
    expect(screen.getByTestId("solution-strategy-panel")).toBeInTheDocument();
    expect(screen.getByText("Base-100 percentage method")).toBeInTheDocument();
    expect(screen.getByText("Standard method")).toBeInTheDocument();
    expect(screen.getByText("Faster method")).toBeInTheDocument();
    expect(screen.getByText("Watch out for")).toBeInTheDocument();
    expect(screen.getByTestId("solution-strategy-s1-formula")).toHaveTextContent("x =");
    // A null field renders no row.
    expect(screen.queryByTestId("solution-strategy-s1-key_observation")).toBeNull();
  });

  test("renders a Reasoning strategy's key observation (GQR-S4, same panel)", () => {
    const reasoning = strat({
      id: "r1", subject_family: "reasoning", name: "Fixed-pivot elimination",
      strategy_type: "elimination", formula_latex: null,
      key_observation: "anchor the person who never moves", faster_method: "eliminate impossible seats",
    });
    render(<SolutionStrategyPanel mode="review" strategies={[reasoning]} />);
    expect(screen.getByText("Fixed-pivot elimination")).toBeInTheDocument();
    expect(screen.getByText("Key observation")).toBeInTheDocument();
    expect(screen.getByTestId("solution-strategy-r1-key_observation"))
      .toHaveTextContent("anchor the person who never moves");
    // No formula row when formula_latex is null.
    expect(screen.queryByTestId("solution-strategy-r1-formula")).toBeNull();
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
  test("mounts the panel once after the type renderer in review mode", () => {
    render(
      <QuestionRenderer
        mode="review"
        showCorrect
        showExplanation
        question={{ ...mcq, solution_strategies: [strat()] }}
      />,
    );
    expect(screen.getAllByTestId("solution-strategy-panel")).toHaveLength(1);
    expect(screen.getByText("Base-100 percentage method")).toBeInTheDocument();
  });

  test.each([
    ["statement_based", { ...mcq, question_type: "statement_based" }],
    [
      "numerical_answer",
      {
        id: "q-num",
        question_type: "numerical_answer",
        question_text: "Enter a number",
        numeric_answer: 10,
        correct_numeric_answer: 10,
        numeric_tolerance: 0,
        explanation: "numeric explanation",
      },
    ],
  ])("uses the shared panel for %s review questions", (_type, question) => {
    render(
      <QuestionRenderer
        mode="review"
        showCorrect
        showExplanation
        question={{ ...question, solution_strategies: [strat()] }}
      />,
    );
    expect(screen.getAllByTestId("solution-strategy-panel")).toHaveLength(1);
  });

  test("no panel during an attempt even when strategies are present", () => {
    render(
      <QuestionRenderer
        mode="attempt"
        question={{ ...mcq, solution_strategies: [strat()] }}
        value={{}}
        onChange={jest.fn()}
      />,
    );
    expect(screen.queryByTestId("solution-strategy-panel")).toBeNull();
  });
});
