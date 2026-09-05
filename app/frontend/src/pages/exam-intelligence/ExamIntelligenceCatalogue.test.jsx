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

// ── search predicate: mirrors app/backend/app/exam_intelligence/lookup.py ──

const { examMatchesQuery } = ExamIntelligenceCatalogueModule;

test("a slug pasted verbatim matches — the query is normalized too, not just the text", () => {
  const exam = { name: "IFSCA Grade A Officer", slug: "ifsca-grade-a", exam_type: "recruitment" };
  for (const q of ["ifsca", "IFSCA", "ifsca-grade-a", "IFSCA Grade A", "ifsca_grade_a", "ifscagradea"]) {
    expect(examMatchesQuery(exam, q)).toBe(true);
  }
});

test("a body-specific query excludes the other bodies", () => {
  const rbi = { name: "RBI Grade B Officer", slug: "rbi-grade-b", exam_type: "recruitment" };
  const sebi = { name: "SEBI Grade A Officer", slug: "sebi-grade-a", exam_type: "recruitment" };
  expect(examMatchesQuery(rbi, "rbi")).toBe(true);
  expect(examMatchesQuery(sebi, "rbi")).toBe(false);
  expect(examMatchesQuery(rbi, "nabard")).toBe(false);
});

test("a blank query means no filter, never no results", () => {
  const exam = { name: "PFRDA Grade A Officer", slug: "pfrda-grade-a" };
  for (const q of ["", "   ", null, undefined]) {
    expect(examMatchesQuery(exam, q)).toBe(true);
  }
});

test("searching a regulatory slug finds its card and does not report no-match", async () => {
  api.get.mockResolvedValue({
    items: [
      { id: "1", slug: "rbi-grade-b", name: "RBI Grade B Officer", exam_type: "recruitment" },
      { id: "2", slug: "ifsca-grade-a", name: "IFSCA Grade A Officer", exam_type: "recruitment" },
    ],
  });
  renderPage();
  await screen.findByTestId("exam-intel-card-ifsca-grade-a");
  fireEvent.change(screen.getByTestId("exam-intelligence-search"), { target: { value: "ifsca-grade-a" } });
  expect(screen.getByTestId("exam-intel-card-ifsca-grade-a")).toBeTruthy();
  expect(screen.queryByTestId("exam-intel-card-rbi-grade-b")).toBeNull();
  expect(screen.queryByTestId("exam-intelligence-no-match")).toBeNull();
});
