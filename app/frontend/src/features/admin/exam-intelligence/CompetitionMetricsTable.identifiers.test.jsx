/**
 * I6 — identifier hygiene regression for CompetitionMetricsTable.
 *
 * Guards: raw exam_slug / exam UUID must not appear verbatim in rendered output.
 *
 * D4 note: The "Exam" column was removed (table is always pre-filtered by
 * exam.id in CompetitionPanel). Tests that previously asserted humanized exam
 * name / slug text appears in the table are updated to assert they are absent.
 */
import React from "react";
import { render, screen } from "@testing-library/react";

// eslint-disable-next-line global-require
const CompetitionMetricsTable = require("./CompetitionMetricsTable").default;

const SLUG = "upsc_cse_2026";
const UUID_EXAM = "550e8400-e29b-41d4-a716-446655440000";

const ROW_WITH_SLUG = {
  id: "row-uuid-0001",
  exam_slug: SLUG,
  exam: null,
  vacancy_total: 1000,
  applicant_count: 500000,
  selection_ratio: 0.002,
  competition_pressure_score: 87.5,
  source_basis: "official",
  confidence_score: 0.9,
  status: "draft",
};

const ROW_WITH_EXAM_NAME = {
  id: "row-uuid-0002",
  exam_slug: SLUG,
  exam: "UPSC Civil Services",
  vacancy_total: 800,
  applicant_count: 400000,
  selection_ratio: 0.002,
  competition_pressure_score: 85,
  source_basis: "official",
  confidence_score: 0.85,
  status: "reviewed",
};

test("raw exam_slug UUID is not rendered verbatim — humanizeToken applied", () => {
  const uuidSlugRow = { ...ROW_WITH_SLUG, exam_slug: UUID_EXAM };
  render(<CompetitionMetricsTable items={[uuidSlugRow]} />);
  // The full UUID must NOT appear in the document.
  expect(document.body.textContent).not.toContain(UUID_EXAM);
});

test("snake_case exam_slug is not shown — Exam column removed (D4)", () => {
  render(<CompetitionMetricsTable items={[ROW_WITH_SLUG]} />);
  // Raw slug with underscores must not appear verbatim.
  expect(document.body.textContent).not.toContain(SLUG);
  // D4: Exam column removed — humanized slug text no longer in table.
  expect(document.body.textContent).not.toContain("Upsc cse 2026");
});

test("exam name not shown — Exam column removed (D4)", () => {
  render(<CompetitionMetricsTable items={[ROW_WITH_EXAM_NAME]} />);
  // D4: Exam column removed — exam name no longer rendered in table.
  expect(document.body.textContent).not.toContain("UPSC Civil Services");
  // Raw slug must also not appear.
  expect(document.body.textContent).not.toContain(SLUG);
});

test("empty items renders empty state without any raw identifier", () => {
  render(<CompetitionMetricsTable items={[]} />);
  expect(screen.getByText("No competition metrics yet")).toBeTruthy();
  expect(document.body.textContent).not.toContain(UUID_EXAM);
  expect(document.body.textContent).not.toContain(SLUG);
});
