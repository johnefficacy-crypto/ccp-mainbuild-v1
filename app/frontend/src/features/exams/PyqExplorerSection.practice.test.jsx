import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({ useNavigate: () => mockNavigate }));
jest.mock("../../lib/api", () => ({ api: { get: jest.fn(), post: jest.fn() } }));
const { api } = require("../../lib/api");
const PyqExplorerSection = require("./PyqExplorerSection").default;

const EXAM_ID = "11111111-1111-1111-1111-111111111111";
const PAPER_ID = "44444444-4444-4444-4444-444444444444";

const listPayload = {
  exam_id: EXAM_ID,
  total: 1,
  items: [
    { id: "q1", paper_id: PAPER_ID, paper_year: 2024, question_text: "A question", options: [] },
  ],
};

beforeEach(() => {
  api.get.mockReset();
  api.post.mockReset();
  mockNavigate.mockReset();
  api.get.mockResolvedValue(listPayload);
});

test("starts paper practice and navigates to the attempt shell", async () => {
  api.post.mockResolvedValue({ outcome: "ready", attempt_id: "att-1" });
  render(<PyqExplorerSection examSlug="upsc-cse" />);

  const btn = await screen.findByTestId("pyq-practice-paper-btn");
  fireEvent.click(btn);

  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith("/api/study/mocks/practice/start", {
      mode: "paper",
      target_id: PAPER_ID,
      exam_id: EXAM_ID,
    })
  );
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/app/study/mocks/attempts/att-1"));
});

test("shows a graceful message when the paper has no projected questions (409)", async () => {
  const err = new Error("empty pool");
  err.status = 409;
  api.post.mockRejectedValue(err);
  render(<PyqExplorerSection examSlug="upsc-cse" />);

  fireEvent.click(await screen.findByTestId("pyq-practice-paper-btn"));

  const banner = await screen.findByTestId("pyq-practice-error");
  expect(banner.textContent).toMatch(/isn't available for practice yet/i);
  expect(mockNavigate).not.toHaveBeenCalled();
});

test("no practice button when a row has no paper_id", async () => {
  api.get.mockResolvedValue({ exam_id: EXAM_ID, total: 1, items: [{ id: "q2", paper_year: 2024, question_text: "No paper", options: [] }] });
  render(<PyqExplorerSection examSlug="upsc-cse" />);

  await screen.findByTestId("pyq-question-card");
  expect(screen.queryByTestId("pyq-practice-paper-btn")).toBeNull();
});
