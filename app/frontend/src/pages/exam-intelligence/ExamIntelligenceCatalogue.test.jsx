import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

jest.mock("../../lib/api", () => ({ api: { get: jest.fn() } }));
const { api } = require("../../lib/api");
const ExamIntelligenceCatalogueModule = require("./ExamIntelligenceCatalogue");
const ExamIntelligenceCatalogue = ExamIntelligenceCatalogueModule.default;
const { examSearchHaystack } = ExamIntelligenceCatalogueModule;

const CATALOGUE = {
  verified_only: true,
  count: 2,
  items: [
    // Deployed name intentionally omits the "UPSC" acronym (mirrors production);
    // the acronym lives only in the slug.
    { id: "e1", slug: "upsc-cse", name: "Civil Services Examination", exam_type: "civil_services", default_difficulty_level: "hard" },
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

test("searching the acronym 'UPSC' matches upsc-cse even when the name omits it", async () => {
  renderPage();
  await screen.findByTestId("exam-intelligence-grid");
  fireEvent.change(screen.getByTestId("exam-intelligence-search"), { target: { value: "UPSC" } });
  // upsc-cse is found via its slug; ssc-cgl is filtered out.
  expect(screen.getByTestId("exam-intel-card-upsc-cse")).toBeTruthy();
  expect(screen.queryByTestId("exam-intel-card-ssc-cgl")).toBeNull();
  expect(screen.queryByTestId("exam-intelligence-no-match")).toBeNull();
});

test("examSearchHaystack indexes name, slug (separator-flattened), and exam_type", () => {
  const hay = examSearchHaystack({ name: "Civil Services Examination", slug: "upsc-cse", exam_type: "civil_services" });
  expect(hay).toContain("upsc"); // acronym from slug
  expect(hay).toContain("upsc cse"); // separators flattened to spaces
  expect(hay).toContain("upsccse"); // collapsed form
  expect(hay).toContain("civil services examination"); // name
  expect(examSearchHaystack({})).toBe(" "); // no fields → no crash
});

test("exam links target the top-level Exam Intelligence detail route", async () => {
  renderPage();
  await screen.findByTestId("exam-intelligence-grid");
  const link = screen.getByTestId("exam-intel-card-upsc-cse");
  expect(link.getAttribute("href")).toBe("/app/exam-intelligence/exams/upsc-cse");
  // Must NOT point back into the eligibility funnel.
  expect(link.getAttribute("href")).not.toContain("/app/eligibility/");
});
