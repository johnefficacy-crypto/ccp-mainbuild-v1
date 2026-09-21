/**
 * The catalogue picker, against the payload the fixed API returns.
 *
 * What broke was visible here and caused elsewhere: thematic compilations
 * arrived in `papers` and were rendered under "Sat papers, in question order",
 * a claim the thematic half cannot keep — its question_number is NULL by
 * design. These pin the rendering half of that contract.
 */
import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";

import CatalogPicker from "../CatalogPicker";

const PSIR = "Political Science and International Relations";

const CATALOG = {
  exam_id: "exam-1",
  subject: PSIR,
  subjects: [
    { subject: PSIR, question_count: 140 },
    { subject: "Anthropology", question_count: 96 },
    { subject: "General Studies", question_count: 1 },
  ],
  papers: [
    { id: "p1", label: "2025 · P1", year: 2025, paper_slot: "P1", question_count: 10 },
    { id: "p2", label: "2025 · P2", year: 2025, paper_slot: "P2", question_count: 8 },
    { id: "p3", label: "2024 · P1", year: 2024, paper_slot: "P1", question_count: 9 },
  ],
  themes: [{ theme: "The State", question_count: 12 }],
  years: [{ year: 2025, question_count: 18 }],
  total_questions: 27,
};

const SELECTION = { subject: PSIR, paper_id: null, theme: null, year: null };

const renderPicker = (props = {}) =>
  render(
    <CatalogPicker
      catalog={CATALOG}
      selection={SELECTION}
      onSelect={jest.fn()}
      {...props}
    />,
  );

test("papers are labelled year then paper number, in that order", () => {
  renderPicker();
  // The trailing count lives in its own span; the label is the text before it.
  const labels = screen
    .getAllByTestId("descriptive-paper")
    .map((b) => Array.from(b.childNodes)
      .filter((n) => n.nodeType === Node.TEXT_NODE)
      .map((n) => n.textContent)
      .join("")
      .trim());
  expect(labels).toEqual(["2025 · P1", "2025 · P2", "2024 · P1"]);
});

test("the question-order claim is made only when there are papers", () => {
  renderPicker();
  expect(screen.getByTestId("descriptive-papers-hint")).toHaveTextContent(
    "Sat papers, in question order.",
  );
});

test("no question-order claim when the papers list is empty", () => {
  // A subject with only thematic questions. The old picker still printed
  // "Sat papers, in question order." over whatever had leaked into the list.
  renderPicker({ catalog: { ...CATALOG, papers: [] } });
  expect(screen.queryByTestId("descriptive-papers-hint")).not.toBeInTheDocument();
  expect(screen.getByText("No papers for this subject yet.")).toBeInTheDocument();
});

test("themes always keep their own no-order wording", () => {
  renderPicker();
  expect(
    screen.getByText("Topic-wise compilations. No paper order, no year."),
  ).toBeInTheDocument();
});

test("every count says what it counts", () => {
  renderPicker();
  const subject = screen
    .getAllByTestId("descriptive-subject")
    .find((b) => b.textContent.startsWith(PSIR));
  expect(subject).toHaveAttribute("title", "140 questions");
  expect(screen.getAllByTestId("descriptive-paper")[0]).toHaveAttribute(
    "title",
    "10 questions",
  );
  expect(screen.getByTestId("descriptive-theme")).toHaveAttribute("title", "12 questions");
});

test("a count of one is singular", () => {
  renderPicker();
  const gs = screen
    .getAllByTestId("descriptive-subject")
    .find((b) => b.textContent.startsWith("General Studies"));
  expect(gs).toHaveAttribute("title", "1 question");
});

test("choosing a subject clears the paper and theme below it", () => {
  const onSelect = jest.fn();
  renderPicker({
    onSelect,
    selection: { ...SELECTION, subject: "Anthropology", paper_id: "p9" },
  });
  const psir = screen
    .getAllByTestId("descriptive-subject")
    .find((b) => b.textContent.startsWith(PSIR));
  fireEvent.click(psir);

  expect(onSelect).toHaveBeenCalledWith({
    subject: PSIR,
    paper_id: null,
    theme: null,
    year: null,
  });
});

test("with no subject chosen the lists say why they are empty", () => {
  renderPicker({
    catalog: { ...CATALOG, subject: null, papers: [], themes: [] },
    selection: { subject: null, paper_id: null, theme: null, year: null },
  });
  expect(screen.getByText("Pick a subject to see its papers.")).toBeInTheDocument();
  expect(screen.getByText("Pick a subject to see its themes.")).toBeInTheDocument();
});
