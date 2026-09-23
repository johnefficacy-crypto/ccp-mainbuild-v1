import React from "react";
import { render, screen } from "@testing-library/react";
import PyqExplanationPanel from "../shared/PyqExplanationPanel";
import QuestionRenderer from "../QuestionRenderer";

// Frozen snapshot options as the review payload carries them: option_index is
// the only field the backend can line a rationale up on, because the projection
// gives each projected option a fresh uuid.
const options = [
  { id: "o1", option_index: 1, display_order: 1, option_text: "Repo rate" },
  { id: "o2", option_index: 2, display_order: 2, option_text: "Reverse repo" },
  { id: "o3", option_index: 3, display_order: 3, option_text: "Bank rate" },
];

const expl = (over = {}) => ({
  id: "e1",
  short_explanation: "Repo is the policy rate.",
  explanation_text: "The RBI lends to banks at the repo rate.",
  solution_steps: ["Identify the policy rate.", "Rule out reverse repo."],
  option_rationales: [
    { option_index: 1, rationale: "Correct — this is the policy rate." },
    { option_index: 2, rationale: "This is the absorption rate." },
  ],
  formula_used: [],
  common_traps: ["Confusing repo with reverse repo."],
  ...over,
});

const mcq = (over = {}) => ({
  id: "q1",
  question_type: "mcq_single",
  question_text: "Which is the policy rate?",
  options,
  correct_option_id: "o1",
  explanation: "flat snapshot explanation",
  ...over,
});

describe("PyqExplanationPanel", () => {
  test("renders every structured section in review mode", () => {
    render(<PyqExplanationPanel mode="review" explanation={expl()} options={options} />);
    expect(screen.getByTestId("pyq-explanation-panel")).toBeInTheDocument();
    expect(screen.getByTestId("pyq-explanation-short")).toHaveTextContent("Repo is the policy rate.");
    expect(screen.getByTestId("pyq-explanation-text")).toHaveTextContent("The RBI lends to banks");
    expect(screen.getByTestId("pyq-explanation-steps").querySelectorAll("li")).toHaveLength(2);
    expect(screen.getByTestId("pyq-explanation-traps")).toHaveTextContent("Confusing repo");
  });

  test("keeps steps as a list rather than flattening them into prose", () => {
    render(<PyqExplanationPanel mode="review" explanation={expl()} options={options} />);
    const items = [...screen.getByTestId("pyq-explanation-steps").querySelectorAll("li")];
    expect(items.map((li) => li.textContent)).toEqual([
      "Identify the policy rate.",
      "Rule out reverse repo.",
    ]);
  });

  test("lines each rationale up with the option it belongs to", () => {
    render(<PyqExplanationPanel mode="review" explanation={expl()} options={options} />);
    expect(screen.getByTestId("pyq-explanation-rationale-1")).toHaveTextContent(
      "Correct — this is the policy rate.",
    );
    expect(screen.getByTestId("pyq-explanation-rationale-2")).toHaveTextContent(
      "This is the absorption rate.",
    );
    // Printed against the option's own label, not a bare index.
    expect(screen.getByTestId("pyq-explanation-rationale-1").textContent).toMatch(/^A/);
    expect(screen.getByTestId("pyq-explanation-rationale-2").textContent).toMatch(/^B/);
    // An option with no rationale gets no row.
    expect(screen.queryByTestId("pyq-explanation-rationale-3")).toBeNull();
  });

  test("renders nothing outside review mode, so it stays invisible during an attempt", () => {
    const { container } = render(
      <PyqExplanationPanel mode="attempt" explanation={expl()} options={options} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  test("renders nothing when there is no verified explanation", () => {
    const { container: a } = render(
      <PyqExplanationPanel mode="review" explanation={null} options={options} />,
    );
    expect(a).toBeEmptyDOMElement();
    // An all-empty payload is the same as none — no empty panel shell.
    const { container: b } = render(
      <PyqExplanationPanel
        mode="review"
        options={options}
        explanation={{
          id: "e2",
          short_explanation: "",
          explanation_text: null,
          solution_steps: [],
          option_rationales: [],
          formula_used: [],
          common_traps: [],
        }}
      />,
    );
    expect(b).toBeEmptyDOMElement();
  });

  test("a section with no content renders no heading", () => {
    render(
      <PyqExplanationPanel
        mode="review"
        options={options}
        explanation={expl({ solution_steps: [], common_traps: [], option_rationales: [] })}
      />,
    );
    expect(screen.queryByText("Solution steps")).toBeNull();
    expect(screen.queryByText("Why each option")).toBeNull();
    expect(screen.queryByText("Watch out for")).toBeNull();
    expect(screen.queryByText("Formula used")).toBeNull();
  });

  test("tolerates malformed lists without throwing", () => {
    // The shapes below deliberately violate propTypes — that is the point of the
    // test — so the expected warning is silenced rather than left as CI noise.
    const warn = jest.spyOn(console, "error").mockImplementation(() => {});
    render(
      <PyqExplanationPanel
        mode="review"
        options={options}
        explanation={expl({
          solution_steps: "not a list",
          common_traps: null,
          option_rationales: undefined,
        })}
      />,
    );
    expect(screen.getByTestId("pyq-explanation-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("pyq-explanation-steps")).toBeNull();
    warn.mockRestore();
  });
});

describe("QuestionRenderer wiring", () => {
  test("mounts the panel once for every question type, including ones that never showed the flat explanation", () => {
    for (const question_type of ["mcq_single", "statement_based", "assertion_reason", "integer"]) {
      const { unmount } = render(
        <QuestionRenderer
          mode="review"
          showCorrect
          showExplanation
          question={mcq({ question_type, pyq_explanation: expl() })}
        />,
      );
      expect(screen.getByTestId("pyq-explanation-panel")).toBeInTheDocument();
      unmount();
    }
  });

  test("a payload with no pyq_explanation field renders exactly as before", () => {
    render(
      <QuestionRenderer mode="review" showCorrect showExplanation question={mcq()} />,
    );
    expect(screen.queryByTestId("pyq-explanation-panel")).toBeNull();
    // The flat snapshot explanation still renders.
    expect(screen.getByText("flat snapshot explanation")).toBeInTheDocument();
  });

  test("the flat explanation is not suppressed when a structured one is present", () => {
    render(
      <QuestionRenderer
        mode="review"
        showCorrect
        showExplanation
        question={mcq({ pyq_explanation: expl() })}
      />,
    );
    expect(screen.getByText("flat snapshot explanation")).toBeInTheDocument();
    expect(screen.getByTestId("pyq-explanation-panel")).toBeInTheDocument();
  });

  test("nothing renders during an active attempt", () => {
    render(
      <QuestionRenderer mode="attempt" question={mcq({ pyq_explanation: expl() })} />,
    );
    expect(screen.queryByTestId("pyq-explanation-panel")).toBeNull();
  });
});
