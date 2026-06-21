/**
 * I6 — identifier hygiene regression for CompetitionMetricsTable.
 *
 * Guards: raw exam_slug must not appear verbatim in rendered output.
 * humanizeToken is applied, so slug text is transformed (underscores →
 * spaces, leading uppercase) before display.
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

test("snake_case exam_slug is transformed — raw slug not shown verbatim", () => {
  render(<CompetitionMetricsTable items={[ROW_WITH_SLUG]} />);
  // Raw slug with underscores must not appear verbatim.
  expect(document.body.textContent).not.toContain(SLUG);
  // Humanized form (underscores → spaces) should be present.
  expect(screen.getByText("Upsc cse 2026")).toBeTruthy();
});

test("when exam name is present it takes priority over slug and is rendered via humanizeToken", () => {
  render(<CompetitionMetricsTable items={[ROW_WITH_EXAM_NAME]} />);
  // exam name is passed through humanizeToken — no underscores in name here
  // so it renders as-is (leading cap already present).
  expect(screen.getByText("UPSC Civil Services")).toBeTruthy();
  // Raw slug must still not appear.
  expect(document.body.textContent).not.toContain(SLUG);
});

test("empty items renders empty state without any raw identifier", () => {
  render(<CompetitionMetricsTable items={[]} />);
  expect(screen.getByText("No competition metrics yet")).toBeTruthy();
  expect(document.body.textContent).not.toContain(UUID_EXAM);
  expect(document.body.textContent).not.toContain(SLUG);
});
