import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

jest.mock("../../lib/api", () => ({ api: { get: jest.fn() } }));
const { api } = require("../../lib/api");
const ExamIntelligenceCatalogue = require("./ExamIntelligenceCatalogue").default;

const CATALOGUE = {
  verified_only: true,
  count: 2,
  items: [
    { id: "e1", slug: "upsc-cse", name: "UPSC CSE", exam_type: "civil_services", default_difficulty_level: "hard" },
    { id: "e2", slug: "ssc-cgl", name: "SSC CGL", exam_type: "staff_selection", default_difficulty_level: "medium" },
  ],
};

beforeEach(() => {
  api.get.mockReset();
  api.get.mockResolvedValue(CATALOGUE);
});

function renderPage() {
  return render(
    <MemoryRouter>
      <ExamIntelligenceCatalogue />
    </MemoryRouter>
  );
}

test("reads the exam-intelligence catalogue, not the eligibility summary", async () => {
  renderPage();
  await screen.findByTestId("exam-intelligence-grid");
  const urls = api.get.mock.calls.map((c) => c[0]);
  expect(urls).toContain("/api/exam-intelligence/exams");
  expect(urls.some((u) => u.includes("eligibility-summary"))).toBe(false);
});

test("is the intelligence surface, not the eligibility funnel (item-13 IA split)", async () => {
  renderPage();
  await screen.findByTestId("exam-intelligence-page");
  // The old eligibility landing must not be reused here.
  expect(screen.queryByTestId("eligibility-exams-page")).toBeNull();
  expect(screen.queryByText("Exam eligibility")).toBeNull();
  expect(screen.queryByText(/See open recruitments/i)).toBeNull();
});

test("exam links target the top-level Exam Intelligence detail route", async () => {
  renderPage();
  await screen.findByTestId("exam-intelligence-grid");
  const link = screen.getByTestId("exam-intel-card-upsc-cse");
  expect(link.getAttribute("href")).toBe("/app/exam-intelligence/exams/upsc-cse");
  // Must NOT point back into the eligibility funnel.
  expect(link.getAttribute("href")).not.toContain("/app/eligibility/");
});
