import React from "react";
import { MemoryRouter } from "react-router-dom";
import { render, screen } from "@testing-library/react";
import StudyLearningHub from "./StudyLearningHub";

jest.mock("../../lib/api", () => ({
  api: { get: jest.fn() },
}));

// Default: no tracked exams
beforeEach(() => {
  const { api } = require("../../lib/api");
  api.get.mockResolvedValue({ items: [] });
});

function renderHub() {
  return render(
    <MemoryRouter>
      <StudyLearningHub />
    </MemoryRouter>,
  );
}

test("exam intelligence card links to #competition when no slug", () => {
  renderHub();
  const card = screen.getByTestId("learning-card-exam-intelligence");
  expect(card.getAttribute("href")).toBe("/app/eligibility/exams");
});

test("exam intelligence card links to #competition anchor when slug resolves", async () => {
  const { api } = require("../../lib/api");
  api.get.mockResolvedValueOnce({ items: [{ slug: "upsc-cse", is_primary: true }] });
  renderHub();
  const card = await screen.findByTestId("learning-card-exam-intelligence");
  expect(card.getAttribute("href")).toContain("#competition");
});

test("exam intelligence card does not use #intelligence", async () => {
  const { api } = require("../../lib/api");
  api.get.mockResolvedValueOnce({ items: [{ slug: "ssc-cgl", is_primary: true }] });
  renderHub();
  const card = await screen.findByTestId("learning-card-exam-intelligence");
  expect(card.getAttribute("href")).not.toContain("#intelligence");
});
