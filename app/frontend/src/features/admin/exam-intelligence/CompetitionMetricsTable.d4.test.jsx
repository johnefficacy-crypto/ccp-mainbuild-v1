/**
 * D4 regression — "Exam" column must be absent from CompetitionMetricsTable.
 *
 * The table is pre-filtered by exam.id in CompetitionPanel so a repeated
 * "Exam" column is redundant. This test guards against re-introduction.
 */
import React from "react";
import { render, screen } from "@testing-library/react";

const CompetitionMetricsTable = require("./CompetitionMetricsTable").default;

const ROWS = [
  {
    id: "row-d4-001",
    exam_slug: "upsc_cse_2026",
    exam: "UPSC Civil Services",
    vacancy_total: 1000,
    applicant_count: 500000,
    selection_ratio: 0.002,
    competition_pressure_score: 87.5,
    source_basis: "official",
    confidence_score: 0.9,
    status: "reviewed",
  },
];

test("D4: no 'Exam' column header in CompetitionMetricsTable", () => {
  render(<CompetitionMetricsTable items={ROWS} />);
  // The <th>Exam</th> header must not be present.
  const headers = screen.queryAllByRole("columnheader");
  const examHeader = headers.find(
    (th) => th.textContent.trim().toLowerCase() === "exam"
  );
  expect(examHeader).toBeUndefined();
});

test("D4: exam name is not rendered in any table cell", () => {
  render(<CompetitionMetricsTable items={ROWS} />);
  // With the Exam column removed, neither the exam name nor slug should appear
  // as a table cell value.
  expect(document.body.textContent).not.toContain("UPSC Civil Services");
  expect(document.body.textContent).not.toContain("upsc_cse_2026");
});

test("D4: table still renders other data without Exam column", () => {
  render(<CompetitionMetricsTable items={ROWS} />);
  // Core data columns should still be present. J3 OD-9 added a "Vacancy by
  // category" column alongside "Vacancy", so this now matches >1 header —
  // assert on the exact "Vacancy" header instead of a loose regex.
  expect(screen.getByRole("columnheader", { name: "Vacancy" })).toBeTruthy();
  expect(screen.getByRole("columnheader", { name: /applicants/i })).toBeTruthy();
  expect(document.body.textContent).toContain("1000");
  expect(document.body.textContent).toContain("500000");
});
