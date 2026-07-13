import React from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import MockReview from "./MockReview";

jest.mock("../../../lib/api", () => ({
  api: { get: jest.fn() },
}));

const SNAP = {
  question_type: "mcq_single",
  question_text: "Q",
  options: [{ id: "o1", option_index: "A", option_text: "Alpha" }],
  correct_option_id: "o1",
};

const REVIEW = {
  attempt_id: "att1",
  questions: [
    { question_id: "q1", attempt_order: 1, is_correct: true, selected_option_id: "o1", error_type: "correct", question_snapshot: SNAP },
    { question_id: "q2", attempt_order: 2, is_correct: false, selected_option_id: "o9", error_type: "silly_mistake", question_snapshot: SNAP },
    { question_id: "q3", attempt_order: 3, is_correct: false, selected_option_id: null, error_type: "time_pressure_unattempted", question_snapshot: SNAP },
  ],
};

function renderReview(payload = REVIEW) {
  const { api } = require("../../../lib/api");
  api.get.mockResolvedValue(payload);
  return render(
    <MemoryRouter initialEntries={["/app/study/mocks/attempts/att1/review"]}>
      <Routes>
        <Route path="/app/study/mocks/attempts/:attemptId/review" element={<MockReview />} />
      </Routes>
    </MemoryRouter>,
  );
}

test("shows learner-friendly error labels, never raw codes", async () => {
  renderReview();
  // Default view starts on q1 (correct).
  expect(await screen.findByTestId("review-error-label")).toHaveTextContent("Correct");
  fireEvent.click(screen.getByTestId("review-next"));
  expect(screen.getByTestId("review-error-label")).toHaveTextContent("Careless mistake");
  expect(screen.queryByText("silly_mistake")).toBeNull();
});

test("Unattempted filter follows is_correct (null), not raw answer presence", async () => {
  const payload = {
    attempt_id: "att1",
    questions: [
      // Wrong MCQ — is_correct false → NOT unattempted (even with a null option).
      { question_id: "qA", attempt_order: 1, is_correct: false, selected_option_id: null, error_type: "concept_gap", question_snapshot: SNAP },
      // Integer typed-but-ungradeable: carries a numeric_answer yet is_correct is
      // null → must still count as unattempted (the raw-answer filter would drop it).
      { question_id: "qB", attempt_order: 2, is_correct: null, numeric_answer: 42, error_type: null, question_snapshot: { ...SNAP, question_type: "integer" } },
      // Genuinely blank MCQ — is_correct null → unattempted.
      { question_id: "qC", attempt_order: 3, is_correct: null, selected_option_id: null, error_type: null, question_snapshot: SNAP },
    ],
  };
  renderReview(payload);
  await screen.findByTestId("review-palette");
  fireEvent.click(screen.getByTestId("review-filter-unattempted"));
  await waitFor(() => {
    // qB (order 2) + qC (order 3) are unattempted; the wrong qA is excluded.
    expect(screen.getByTestId("review-palette-item-0")).toHaveTextContent("2");
    expect(screen.getByTestId("review-palette-item-1")).toHaveTextContent("3");
    expect(screen.queryByTestId("review-palette-item-2")).toBeNull();
  });
});

test("filtered palette preserves the original question number", async () => {
  renderReview();
  await screen.findByTestId("review-palette");
  // Filter to just the wrong question (originally Q2).
  fireEvent.click(screen.getByTestId("review-filter-wrong"));
  await waitFor(() => {
    // One palette item, and it must read "2" (original number), not "1".
    expect(screen.getByTestId("review-palette-item-0")).toHaveTextContent("2");
  });
  expect(screen.getByTestId("review-question")).toHaveTextContent("Q2 · Careless mistake");
});

test("uses backend attempt_order, not array/filter position, for the number", async () => {
  // Payload deliberately arrives out of attempt order (the wrong question is
  // first in the array but is attempt #3).
  const shuffled = {
    attempt_id: "att1",
    questions: [
      { question_id: "qb", attempt_order: 3, is_correct: false, selected_option_id: "o9", error_type: "concept_gap", question_snapshot: SNAP },
      { question_id: "qa", attempt_order: 1, is_correct: true, selected_option_id: "o1", error_type: "correct", question_snapshot: SNAP },
    ],
  };
  renderReview(shuffled);
  await screen.findByTestId("review-palette");
  fireEvent.click(screen.getByTestId("review-filter-wrong"));
  await waitFor(() => {
    // The only wrong question is attempt #3 — palette must show "3", not "1".
    expect(screen.getByTestId("review-palette-item-0")).toHaveTextContent("3");
  });
  expect(screen.getByTestId("review-question")).toHaveTextContent("Q3 · Concept gap");
});

test("has a sticky footer with prev/next actions", async () => {
  renderReview();
  const footer = await screen.findByTestId("review-footer");
  expect(footer).toBeTruthy();
  // Prev/Next live inside the footer.
  expect(footer.contains(screen.getByTestId("review-prev"))).toBe(true);
  expect(footer.contains(screen.getByTestId("review-next"))).toBe(true);
});

test("keyboard ArrowRight / ArrowLeft move between reviewed questions", async () => {
  renderReview();
  await screen.findByTestId("review-question");
  expect(screen.getByTestId("review-error-label")).toHaveTextContent("Correct"); // q1
  fireEvent.keyDown(window, { key: "ArrowRight" });
  expect(screen.getByTestId("review-error-label")).toHaveTextContent("Careless mistake"); // q2
  fireEvent.keyDown(window, { key: "ArrowLeft" });
  expect(screen.getByTestId("review-error-label")).toHaveTextContent("Correct");
});

test("renders a source-aware back link when a return context is stored", async () => {
  window.sessionStorage.setItem(
    "cc.attempt.return.att1",
    JSON.stringify({ return_to: "/app/eligibility/exams/upsc-cse#pyq-explorer", source_label: "Back to UPSC CSE PYQs" }),
  );
  renderReview();
  const back = await screen.findByTestId("review-back-source");
  expect(back).toHaveTextContent("Back to UPSC CSE PYQs");
  expect(back.getAttribute("href")).toContain("/app/eligibility/exams/upsc-cse");
  window.sessionStorage.clear();
});
