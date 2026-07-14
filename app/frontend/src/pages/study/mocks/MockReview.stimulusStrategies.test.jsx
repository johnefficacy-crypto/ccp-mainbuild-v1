import React from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { fireEvent, render, screen } from "@testing-library/react";
import MockReview from "./MockReview";

jest.mock("../../../lib/api", () => ({
  api: { get: jest.fn() },
}));

const SNAP = {
  question_type: "mcq_single",
  question_text: "Reasoning set question",
  options: [{ id: "o1", option_index: "A", option_text: "Alpha" }],
  correct_option_id: "o1",
};

function renderReview(payload) {
  const { api } = require("../../../lib/api");
  api.get.mockResolvedValue(payload);
  return render(
    <MemoryRouter initialEntries={["/app/study/mocks/attempts/att-set/review"]}>
      <Routes>
        <Route path="/app/study/mocks/attempts/:attemptId/review" element={<MockReview />} />
      </Routes>
    </MemoryRouter>,
  );
}

function strategy(id, name) {
  return {
    id,
    subject_family: "reasoning",
    name,
    strategy_type: "set_method",
    standard_method: `${name} method`,
  };
}

test("preserves one panel per stimulus when the active question has multiple stimuli", async () => {
  renderReview({
    attempt_id: "att-set",
    questions: [
      {
        question_id: "q1",
        attempt_order: 1,
        is_correct: false,
        selected_option_id: "o9",
        error_type: "concept_gap",
        question_snapshot: SNAP,
      },
      {
        question_id: "q2",
        attempt_order: 2,
        is_correct: true,
        selected_option_id: "o1",
        error_type: "correct",
        question_snapshot: SNAP,
      },
    ],
    stimulus_solution_strategies: [
      {
        pyq_stimulus_id: "stim-grid",
        question_ids: ["q1", "q2"],
        first_attempt_order: 1,
        strategies: [strategy("shared", "Build the seating grid")],
      },
      {
        pyq_stimulus_id: "stim-rules",
        question_ids: ["q1"],
        first_attempt_order: 1,
        // Deliberately reuse the same strategy id under a different canonical
        // stimulus. Flatten-and-dedupe would incorrectly collapse these groups.
        strategies: [strategy("shared", "Apply the condition table")],
      },
    ],
  });

  const panels = await screen.findAllByTestId("stimulus-solution-strategy-panel");
  expect(panels).toHaveLength(2);
  expect(panels[0]).toHaveTextContent("Build the seating grid");
  expect(panels[1]).toHaveTextContent("Apply the condition table");

  fireEvent.click(screen.getByTestId("review-next"));
  const q2Panels = screen.getAllByTestId("stimulus-solution-strategy-panel");
  expect(q2Panels).toHaveLength(1);
  expect(q2Panels[0]).toHaveTextContent("Build the seating grid");
  expect(screen.queryByText("Apply the condition table")).toBeNull();
});

test("missing additive stimulus strategy payload remains backward compatible", async () => {
  renderReview({
    attempt_id: "att-set",
    questions: [
      {
        question_id: "q1",
        attempt_order: 1,
        is_correct: true,
        selected_option_id: "o1",
        error_type: "correct",
        question_snapshot: SNAP,
      },
    ],
  });

  await screen.findByTestId("review-question");
  expect(screen.queryByTestId("stimulus-solution-strategy-panel")).toBeNull();
});
